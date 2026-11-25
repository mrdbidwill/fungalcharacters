"""Import characters and related tables from an MRDBID export.

The export is made on the Mac by scripts/export_mrdbid.sh, which reads the old
MySQL database through the MySQL client only. This command reads the JSON files
it writes (mounted read-only at /import_data in Docker).

Records keep their MRDBID IDs as permanent IDs, keep their original
created/updated times, and are credited to the "mrdbid-import" account.
Each gets one history entry recording the import.
"""
import json
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from simple_history.utils import bulk_create_with_history

from characters.models import (
    Character, CoreSequence, DisplayOption, FungusType, ObservationMethod,
    Part, Source, SourceType, ValueOption,
)
from characters.normalize import normalize_name

IMPORT_USERNAME = "mrdbid-import"

# (MySQL table, Django model) in dependency order.
SIMPLE_TABLES = [
    ("source_data_types", SourceType),
    ("parts", Part),
    ("observation_methods", ObservationMethod),
    ("fungus_types", FungusType),
    ("display_options", DisplayOption),
]
ALL_MODELS = [CoreSequence, ValueOption, Character, Source] + [m for _, m in SIMPLE_TABLES]
TABLE_FOR_MODEL = {
    SourceType: "source_data_types", Part: "parts", ObservationMethod: "observation_methods",
    FungusType: "fungus_types", DisplayOption: "display_options", Source: "source_data",
    Character: "mr_characters", ValueOption: "lookup_items", CoreSequence: "core_character_sequences",
}


def ts(value):
    """MRDBID (Rails) stores times in UTC without a zone."""
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=dt_timezone.utc)


def text(value):
    return "" if value is None else value


class Command(BaseCommand):
    help = "Import characters and related tables from an MRDBID export (scripts/export_mrdbid.sh)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default="/import_data", help="Folder with the exported JSON files.")
        parser.add_argument(
            "--replace", action="store_true",
            help="Delete previously imported data (and its history) first.",
        )

    def load(self, name):
        path = self.dir / f"{name}.json"
        if not path.exists():
            raise CommandError(f"Missing {path}. Run scripts/export_mrdbid.sh on the Mac first.")
        return json.loads(path.read_text(encoding="utf-8"))

    @transaction.atomic
    def handle(self, *args, **opts):
        self.dir = Path(opts["dir"])
        rows = {t: self.load(t) for t in TABLE_FOR_MODEL.values()}
        auto_increment = self.load("auto_increment")

        existing = sum(m.objects.count() for m in ALL_MODELS)
        if existing and not opts["replace"]:
            raise CommandError(f"{existing} records already exist. Use --replace to re-import.")
        if opts["replace"]:
            for model in ALL_MODELS:
                model.history.all().delete()
                model.objects.all().delete()

        User = get_user_model()
        importer, created = User.objects.get_or_create(
            username=IMPORT_USERNAME,
            defaults={"first_name": "MRDBID", "last_name": "import", "is_active": False},
        )
        if created:
            importer.set_unusable_password()
            importer.save()

        reason = "Imported from MRDBID (mrdbid_development)"

        def tracked(r):
            return dict(
                id=r["id"], legacy_mrdbid_id=r["id"], created_by=importer,
                created_at=ts(r["created_at"]), updated_at=ts(r["updated_at"]),
                comments=text(r.get("comments")),
            )

        def bulk(model, objs):
            bulk_create_with_history(objs, model, default_user=importer, default_change_reason=reason)

        for table, model in SIMPLE_TABLES:
            bulk(model, [
                model(name=text(r["name"]), description=text(r["description"]), **tracked(r))
                for r in rows[table]
            ])

        bulk(Source, [
            Source(
                title=text(r["title"]), author=text(r["author"]), ref=text(r["ref"]),
                item_code=text(r["item_code"]), source_type_id=r["source_data_type_id"], **tracked(r),
            )
            for r in rows["source_data"]
        ])

        bulk(Character, [
            Character(
                name=text(r["name"]), name_normalized=normalize_name(r["name"]),
                description=text(r["description"]), part_id=r["part_id"],
                observation_method_id=r["observation_method_id"], display_option_id=r["display_option_id"],
                fungus_type_id=r["fungus_type_id"], source_id=r["source_data_id"],
                is_core=bool((r.get("properties") or {}).get("core")), **tracked(r),
            )
            for r in rows["mr_characters"]
        ])

        options = sorted(rows["lookup_items"], key=lambda r: (r["mr_character_id"], r["id"]))
        order = {}
        objs = []
        for r in options:
            order[r["mr_character_id"]] = order.get(r["mr_character_id"], 0) + 1
            objs.append(ValueOption(
                character_id=r["mr_character_id"], name=text(r["name"]),
                name_normalized=normalize_name(r["name"]), description=text(r["description"]),
                source_id=r["source_data_id"], sort_order=order[r["mr_character_id"]], **tracked(r),
            ))
        bulk(ValueOption, objs)

        bulk(CoreSequence, [
            CoreSequence(
                fungus_type_id=r["fungus_type_id"], character_id=r["mr_character_id"],
                sequence=r["sequence"], **tracked({**r, "comments": ""}),
            )
            for r in rows["core_character_sequences"]
        ])

        # New IDs start after the highest ID MRDBID ever issued, so IDs are never reused.
        with connection.cursor() as cur:
            for model, table in TABLE_FOR_MODEL.items():
                next_id = max(auto_increment[table], (max((r["id"] for r in rows[table]), default=0) + 1))
                cur.execute(
                    "SELECT setval(pg_get_serial_sequence(%s, 'id'), %s, false)",
                    [model._meta.db_table, next_id],
                )

        self.stdout.write("Table: MySQL rows -> imported rows")
        ok = True
        for model, table in TABLE_FOR_MODEL.items():
            n_src, n_dst = len(rows[table]), model.objects.count()
            ok &= n_src == n_dst
            self.stdout.write(f"  {table} -> {model.__name__}: {n_src} -> {n_dst}{'' if n_src == n_dst else '  MISMATCH'}")
        if not ok:
            raise CommandError("Row counts do not match; import rolled back.")
        self.stdout.write(self.style.SUCCESS("Import complete."))
