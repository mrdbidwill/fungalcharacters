"""Data model.

Character data lives in the tables of the fungal_characters release
(data/releases/<version>/), loaded exactly as released. Django does not create
or alter those tables (managed = False); their structure comes only from the
release file.

Everything the website adds lives in its own tables, never in the release tables:
- ItemMeta: who created an item on the site, and whether the admin hid it.
- CodeCounter: the last FCC/FCV number issued, so codes are never reused.
- Historical* tables (django-simple-history): the public edit history.

Permanent public identifiers are the codes: FCC##### (characters) and
FCV##### (values). They are never changed or reused.
"""
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

# labels.labelable_type values used by the release.
CHARACTER_TYPE = "MrCharacter"
VALUE_TYPE = "LookupItem"
PART_TYPE = "Part"
OBSERVATION_METHOD_TYPE = "ObservationMethod"
# ItemMeta.item_type values for items that have no labels.
SOURCE_TYPE = "SourceData"
DISPLAY_OPTION_TYPE = "DisplayOption"


class UTCDateTimeField(models.DateTimeField):
    """The release stores times as `timestamp(6) without time zone`, in UTC."""

    def db_type(self, connection):
        return "timestamp(6) without time zone"

    def from_db_value(self, value, expression, connection):
        if value is not None and timezone.is_naive(value):
            value = timezone.make_aware(value, dt_timezone.utc)
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is not None and timezone.is_aware(value):
            value = timezone.make_naive(value, dt_timezone.utc)
        return value


class ReleaseTable(models.Model):
    created_at = UTCDateTimeField()
    updated_at = UTCDateTimeField()

    class Meta:
        abstract = True
        managed = False

    def save(self, *args, **kwargs):
        now = timezone.now()
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now
        super().save(*args, **kwargs)


class NamedReleaseTable(ReleaseTable):
    name = models.CharField(_("name"), max_length=255, null=True, blank=True)
    description = models.TextField(_("description"), null=True, blank=True)
    comments = models.TextField(_("comments"), null=True, blank=True)

    class Meta(ReleaseTable.Meta):
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name or ""


class Part(NamedReleaseTable):
    class Meta(NamedReleaseTable.Meta):
        db_table = "parts"


class ObservationMethod(NamedReleaseTable):
    class Meta(NamedReleaseTable.Meta):
        db_table = "observation_methods"


class DisplayOption(NamedReleaseTable):
    """Value type: the kind of value a character takes (radio list, number in mm, ...)."""

    history = HistoricalRecords(table_name="characters_history_display_options")

    class Meta(NamedReleaseTable.Meta):
        db_table = "display_options"
        verbose_name = _("value type")


class SourceType(NamedReleaseTable):
    class Meta(NamedReleaseTable.Meta):
        db_table = "source_data_types"


class FungusType(NamedReleaseTable):
    class Meta(NamedReleaseTable.Meta):
        db_table = "fungus_types"


class Source(ReleaseTable):
    """A published source. A shared list anyone can cite or add to."""

    title = models.CharField(_("title"), max_length=255, null=True, blank=True)
    author = models.CharField(_("author"), max_length=255, null=True, blank=True)
    ref = models.CharField(_("reference / URL"), max_length=255, null=True, blank=True)
    item_code = models.CharField(_("item code"), max_length=255, null=True, blank=True)
    source_type = models.ForeignKey(
        SourceType, on_delete=models.PROTECT, null=True, blank=True,
        db_column="source_data_type_id", related_name="sources", verbose_name=_("type"),
    )
    comments = models.TextField(_("comments"), null=True, blank=True)
    user_id = models.BigIntegerField(null=True, blank=True, editable=False)
    history = HistoricalRecords(table_name="characters_history_source_data")

    class Meta(ReleaseTable.Meta):
        db_table = "source_data"
        ordering = ["title"]
        verbose_name = _("source")

    def __str__(self):
        return self.title or ""


class Character(ReleaseTable):
    code = models.CharField(_("code"), max_length=16, unique=True, editable=False)
    name = models.CharField(_("name"), max_length=255, null=True, blank=True)
    description = models.TextField(_("definition"), null=True, blank=True)
    comments = models.TextField(_("comments"), null=True, blank=True)
    part = models.ForeignKey(Part, on_delete=models.PROTECT, null=True, blank=True, related_name="characters",
                             verbose_name=_("part"))
    observation_method = models.ForeignKey(
        ObservationMethod, on_delete=models.PROTECT, null=True, blank=True, related_name="characters",
        verbose_name=_("observation method"),
    )
    display_option = models.ForeignKey(
        DisplayOption, on_delete=models.PROTECT, null=True, blank=True, related_name="characters",
        verbose_name=_("value type"),
    )
    source = models.ForeignKey(
        Source, on_delete=models.PROTECT, null=True, blank=True, db_column="source_data_id", related_name="characters",
        verbose_name=_("source"),
    )
    fungus_type = models.ForeignKey(
        FungusType, on_delete=models.PROTECT, null=True, blank=True, related_name="primary_characters"
    )
    properties = models.JSONField(null=True, blank=True)
    needs_review = models.BooleanField(default=False)
    applies_to = models.ManyToManyField(FungusType, through="CharacterFungusType", related_name="characters")
    history = HistoricalRecords(table_name="characters_history_mr_characters", excluded_fields=["updated_at"])

    class Meta(ReleaseTable.Meta):
        db_table = "mr_characters"
        ordering = ["name", "id"]
        verbose_name = _("character")

    def __str__(self):
        return self.name or self.code

    def get_absolute_url(self):
        return reverse("characters:by_code", args=[self.code])

    @property
    def props(self):
        return self.properties or {}


class ValueOption(ReleaseTable):
    """Value option: one allowed choice for a character (release table lookup_items, code FCV#####).

    Shown as a radio button or select-menu entry. The release calls these "values".
    """

    code = models.CharField(max_length=16, unique=True, editable=False)
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, db_column="mr_character_id", related_name="value_options"
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    source = models.ForeignKey(
        Source, on_delete=models.PROTECT, null=True, blank=True, db_column="source_data_id", related_name="value_options"
    )
    history = HistoricalRecords(table_name="characters_history_lookup_items", excluded_fields=["updated_at"])

    class Meta(ReleaseTable.Meta):
        db_table = "lookup_items"
        ordering = ["character", "id"]
        verbose_name = _("value option")

    def __str__(self):
        return self.name or self.code

    def get_absolute_url(self):
        return reverse("characters:by_code", args=[self.code])


class CoreSequence(ReleaseTable):
    fungus_type = models.ForeignKey(FungusType, on_delete=models.PROTECT, related_name="core_sequence")
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, db_column="mr_character_id", related_name="core_sequences"
    )
    sequence = models.IntegerField(null=True, blank=True)
    history = HistoricalRecords(table_name="characters_history_core_character_sequences", excluded_fields=["updated_at"])

    class Meta(ReleaseTable.Meta):
        db_table = "core_character_sequences"
        ordering = ["fungus_type", "sequence"]


class Label(ReleaseTable):
    """Names, scientific names and definitions by language."""

    labelable_type = models.CharField(max_length=50)
    labelable_id = models.BigIntegerField()
    language = models.CharField(max_length=10)
    label_type = models.CharField(max_length=30)
    text = models.TextField()
    history = HistoricalRecords(table_name="characters_history_labels", excluded_fields=["updated_at"])

    class Meta(ReleaseTable.Meta):
        db_table = "labels"

    def __str__(self):
        return self.text


class CharacterFungusType(ReleaseTable):
    """'Applies to' tag. A character with no tags applies to all fungi."""

    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, db_column="mr_character_id", related_name="fungus_type_tags"
    )
    fungus_type = models.ForeignKey(FungusType, on_delete=models.PROTECT, related_name="character_tags")
    history = HistoricalRecords(table_name="characters_history_character_fungus_types", excluded_fields=["updated_at"])

    class Meta(ReleaseTable.Meta):
        db_table = "character_fungus_types"


class Release(ReleaseTable):
    version = models.CharField(max_length=20, unique=True)
    released_at = models.DateField()
    notes = models.TextField(null=True, blank=True)

    class Meta(ReleaseTable.Meta):
        db_table = "releases"
        ordering = ["-released_at", "-id"]

    def __str__(self):
        return self.version


# ---------- website tables (never part of a release) ----------

class ItemMeta(models.Model):
    """Who created an item on the website, and whether the admin hid it.

    Items from a release have no row here unless hidden: they are credited to the
    release, and only the admin edits them.
    """

    item_type = models.CharField(max_length=50)
    item_id = models.BigIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    is_hidden = models.BooleanField(default=False, help_text="Hidden by the admin as inappropriate.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["item_type", "item_id"], name="unique_item_meta")]

    def __str__(self):
        return f"{self.item_type} {self.item_id}"


class CodeCounter(models.Model):
    """Last number issued per code prefix (FCC, FCV). Only ever increases."""

    prefix = models.CharField(max_length=3, primary_key=True)
    last_number = models.PositiveIntegerField()

    @classmethod
    def next_code(cls, prefix, model):
        with transaction.atomic():
            counter = cls.objects.select_for_update().get(prefix=prefix)
            highest = max(
                (int(c[len(prefix):]) for c in model.objects.values_list("code", flat=True) if c.startswith(prefix)),
                default=0,
            )
            counter.last_number = max(counter.last_number, highest) + 1
            counter.save()
        return f"{prefix}{counter.last_number:05d}"


class Consent(models.Model):
    """A user's agreement to the contribution terms (docs/DECISIONS.md, "Contributions and privacy")."""

    CONTRIBUTIONS_CC0 = "contributions-cc0"
    CURRENT_VERSION = "2026-11-25"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=40)
    version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "kind", "version"], name="unique_consent")]

    @classmethod
    def has_current(cls, user):
        return user.is_authenticated and cls.objects.filter(
            user=user, kind=cls.CONTRIBUTIONS_CC0, version=cls.CURRENT_VERSION).exists()

    @classmethod
    def record(cls, user):
        cls.objects.get_or_create(user=user, kind=cls.CONTRIBUTIONS_CC0, version=cls.CURRENT_VERSION)


class ReviewRequest(models.Model):
    """A "Needs review" report from anyone, listed for the admin (docs/DECISIONS.md, Admin). No email is sent."""

    item_type = models.CharField(max_length=50)          # CHARACTER_TYPE, DISPLAY_OPTION_TYPE or SOURCE_TYPE
    item_id = models.BigIntegerField()
    item_label = models.CharField(max_length=300)        # name and code at the time of the report
    page = models.CharField(max_length=300)              # the page it was sent from
    note = models.TextField(blank=True, max_length=1000)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)
    resolved_note = models.TextField(blank=True)

    class Meta:
        ordering = ["resolved", "-created_at"]

    def __str__(self):
        return f"{self.item_label} ({self.created_at:%Y-%m-%d})"
