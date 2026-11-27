"""Give every value type a readable display name and a short description (Will, 2026-11-27).

Keys stay as they are (they are permanent), except the one key written with a hyphen by mistake:
drop-down -> drop_down (no character uses it). Safe to run again: only missing or different text is changed.
Every change is recorded in the public history, credited to the admin account named with --as.

    python manage.py name_value_types --as will
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from characters.forms import ensure_history_baseline, set_label
from characters.models import DISPLAY_OPTION_TYPE, DisplayOption, Label

REASON = "Readable value type names (Will, 2026-11-27)"
RENAMES = {"drop-down": "drop_down"}
# key: (display name, description; None keeps the existing description)
NAMES = {
    "Do Not Display": ("Hidden (admin only)", None),
    "text_box_number_mm": ("Number (mm)", "A measurement in millimetres, such as cap width."),
    "text_box_number_um": ("Number (µm)", "A measurement in micrometres (µm), usually made under the microscope, such as spore length."),
    "text_box_number": ("Number", "A number without a unit, such as a count."),
    "text_box_range_um": ("Range (µm)", None),
    "text_box_string": ("Text", "Free text."),
    "color": ("Color", "A color, described in words or with a color chart."),
    "color_reaction": ("Color reaction", None),
    "taste": ("Taste", "A taste, recorded as the source describes it."),
    "odor": ("Odor", "An odor, recorded as the source describes it."),
    "texture": ("Texture", "A texture, described in words."),
    "abundance": ("Abundance", "How many or how much, such as few or many."),
    "radio": ("Choose one (list)", "One choice from the character's value options, shown as a list."),
    "drop_down": ("Choose one (drop-down menu)", "One choice from the character's value options, shown as a drop-down menu."),
    "checkbox": ("Choose any (checkboxes)", "Any number of choices from the character's value options."),
    "switch": ("On / Off", "On or off."),
    "boolean_yes_no": ("Yes / No", "Yes or no."),
    "boolean_true_false": ("True / False", "True or false."),
    "boolean_present_absent": ("Present / Absent", "Whether something is present or absent."),
    "state": ("State or province", "A state or province."),
    "country": ("Country", "A country."),
    "media": ("Photo or video", None),
    "dna_sequence": ("DNA sequence", None),
}


class Command(BaseCommand):
    help = "Give every value type a readable display name and description (keys stay permanent)."

    def add_arguments(self, parser):
        parser.add_argument("--as", dest="username", required=True, help="Admin account credited in the history.")

    @transaction.atomic
    def handle(self, username, **_):
        admin = get_user_model().objects.filter(username=username, is_superuser=True).first()
        if admin is None:
            raise CommandError(f"No admin account named {username}.")
        changed = []
        for old, new in RENAMES.items():
            vt = DisplayOption.objects.filter(name=old).first()
            if vt is not None:
                ensure_history_baseline(vt)
                vt.name, vt._history_user, vt._change_reason = new, admin, REASON + f"; key {old} -> {new}"
                vt.save()
                changed.append(f"key {old} -> {new}")
        for key, (label, description) in NAMES.items():
            vt = DisplayOption.objects.filter(name=key).first()
            if vt is None:
                self.stdout.write(self.style.WARNING(f"not found: {key}"))
                continue
            if description and (vt.description or "") != description:
                ensure_history_baseline(vt)
                vt.description, vt._history_user, vt._change_reason = description, admin, REASON
                vt.save()
                changed.append(f"{key}: description")
            current = Label.objects.filter(labelable_type=DISPLAY_OPTION_TYPE, labelable_id=vt.pk, label_type="name",
                                           language="en").first()
            if current is None or current.text != label:
                if current is not None:
                    current._history_user = admin
                label_obj, _created = set_label(DISPLAY_OPTION_TYPE, vt.pk, "name", label, REASON)
                if label_obj is not None:
                    h = label_obj.history.order_by("-history_date").first()
                    if h is not None and h.history_user_id is None:
                        h.history_user = admin
                        h.save(update_fields=["history_user"])
                changed.append(f"{key}: “{label}”")
        unnamed = [vt.name for vt in DisplayOption.objects.all()
                   if not Label.objects.filter(labelable_type=DISPLAY_OPTION_TYPE, labelable_id=vt.pk, label_type="name").exists()]
        self.stdout.write("\n".join(changed) or "nothing to change")
        self.stdout.write(self.style.SUCCESS(f"{len(changed)} change(s). Value types without a display name: {unnamed or 'none'}"))
