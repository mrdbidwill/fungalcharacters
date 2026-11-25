"""Data model for fungal characters.

Every record has:
- a permanent ID (database primary key; IDs are never reused, and records
  imported from MRDBID keep their old MRDBID ID),
- a creator (user account) and created/updated times,
- free-text comments,
- full edit history (django-simple-history: who changed what, and when,
  with an optional reason for each change).
"""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords

from .normalize import normalize_name


class Tracked(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="User account that created this record.",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now, editable=False)
    comments = models.TextField(blank=True)
    is_hidden = models.BooleanField(
        default=False, help_text="Hidden by the admin as inappropriate."
    )
    legacy_mrdbid_id = models.BigIntegerField(
        null=True, blank=True, unique=True, editable=False,
        help_text="ID in the old MRDBID database, if imported from it.",
    )
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class Named(Tracked):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta(Tracked.Meta):
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Part(Named):
    """Part of the fungus a character describes (Cap, Gills, Stem, ...)."""


class ObservationMethod(Named):
    """How a character is observed (Macro, Micro, DNA, ...)."""


class FungusType(Named):
    """Broad morphological group (Boletes, Polypores, ...)."""


class DisplayOption(Named):
    """Value type: the kind of value a character takes (radio, drop-down, number in mm, ...).

    Named DisplayOption after the old MRDBID table; shown on the site as "value type".
    """

    class Meta(Named.Meta):
        verbose_name = "value type"


class SourceType(Named):
    """Kind of published source (Book, Website, Paper, ...)."""


class Source(Tracked):
    """A published source. A shared list anyone can cite or add to."""

    title = models.CharField(max_length=500)
    author = models.CharField(max_length=500, blank=True)
    ref = models.CharField("reference / URL", max_length=500, blank=True)
    item_code = models.CharField(max_length=255, blank=True)
    source_type = models.ForeignKey(
        SourceType, on_delete=models.PROTECT, null=True, blank=True, related_name="sources"
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Character(Named):
    """A fungal character, e.g. "Cap Shape"."""

    name_scientific = models.CharField(
        "scientific / Latin name", max_length=255, blank=True
    )
    name_normalized = models.CharField(max_length=255, db_index=True, editable=False)
    part = models.ForeignKey(Part, on_delete=models.PROTECT, null=True, blank=True, related_name="characters")
    observation_method = models.ForeignKey(
        ObservationMethod, on_delete=models.PROTECT, null=True, blank=True, related_name="characters"
    )
    display_option = models.ForeignKey(
        DisplayOption, on_delete=models.PROTECT, null=True, blank=True, related_name="characters",
        verbose_name="value type",
    )
    fungus_type = models.ForeignKey(
        FungusType, on_delete=models.PROTECT, null=True, blank=True, related_name="characters"
    )
    source = models.ForeignKey(Source, on_delete=models.PROTECT, null=True, blank=True, related_name="characters")
    is_core = models.BooleanField(default=False, help_text="Marked core in MRDBID.")

    def save(self, *args, **kwargs):
        self.name_normalized = normalize_name(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("characters:detail", args=[self.pk])

    def possible_duplicates(self):
        return Character.objects.filter(name_normalized=self.name_normalized).exclude(pk=self.pk)


class ValueOption(Tracked):
    """One allowed value of a character (shown as a radio button or select-menu entry)."""

    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name="value_options")
    name = models.CharField(max_length=255)
    name_scientific = models.CharField("scientific / Latin name", max_length=255, blank=True)
    name_normalized = models.CharField(max_length=255, editable=False)
    description = models.TextField(blank=True)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, null=True, blank=True, related_name="value_options")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["character", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["character", "name_normalized"], name="unique_value_option_per_character"
            )
        ]

    def save(self, *args, **kwargs):
        self.name_normalized = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CoreSequence(Tracked):
    """Order of core characters for a fungus type (from MRDBID core_character_sequences)."""

    fungus_type = models.ForeignKey(FungusType, on_delete=models.PROTECT, related_name="core_sequence")
    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name="core_sequences")
    sequence = models.PositiveIntegerField()

    class Meta:
        ordering = ["fungus_type", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["fungus_type", "character"], name="unique_core_character_per_type")
        ]

    def __str__(self):
        return f"{self.fungus_type} #{self.sequence}: {self.character}"
