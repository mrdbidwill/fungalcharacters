"""Build a dated data release from the live tables (docs/RELEASING.md).

    python manage.py make_release 1.1.0 --notes "..." [--date 2026-12-01] [--out /tmp/releases] [--record]

--record also adds the release to the site's releases table (footer, Downloads page). Without it nothing in the
database changes.
"""
import datetime
import json

from django.core.management.base import BaseCommand, CommandError

from characters.models import Release
from characters.release import build_release


class Command(BaseCommand):
    help = "Build a dated data release (Excel, CSV, JSON, SQL for PostgreSQL and MySQL, SKOS, SDD) from the live data."

    def add_arguments(self, parser):
        parser.add_argument("version")
        parser.add_argument("--date", default=datetime.date.today().isoformat())
        parser.add_argument("--notes", default="")
        parser.add_argument("--out", default=None, help="Folder to write <version>/ into (default: data/releases).")
        parser.add_argument("--record", action="store_true", help="Also add the release to the site's releases table.")
        parser.add_argument("--record-only", action="store_true",
                            help="Only add the release to the releases table (its files are already deployed).")

    def handle(self, version, date, notes, out, record, record_only, **_):
        if Release.objects.filter(version=version).exists():
            raise CommandError(f"Release {version} is already recorded.")
        if record_only:
            Release.objects.create(version=version, released_at=datetime.date.fromisoformat(date), notes=notes or None)
            self.stdout.write(self.style.SUCCESS(f"Release {version} recorded."))
            return
        try:
            summary = build_release(version, date, notes, out_root=out)
        except ValueError as e:
            raise CommandError(str(e))
        if record:
            Release.objects.create(version=version, released_at=datetime.date.fromisoformat(date), notes=notes or None)
        self.stdout.write(json.dumps(summary, indent=1, default=str))
        self.stdout.write(self.style.SUCCESS(f"Release {version} written to {summary['out']}" + (" and recorded." if record else ".")))
