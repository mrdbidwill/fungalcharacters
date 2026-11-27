from difflib import SequenceMatcher

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from .models import (
    DISPLAY_OPTION_TYPE, CHARACTER_TYPE, VALUE_TYPE, Character, CharacterFungusType, CodeCounter, DisplayOption,
    FungusType, ItemMeta, Label, Source, ValueOption,
)
from .normalize import normalize_name

AGREE_LABEL = _("I agree: everything I add to fungalcharacters.org is dedicated to the public domain (CC0 1.0), "
                "free for anyone to use in any way, and I have the right to share it.")
AGREE_HELP = mark_safe(_('Do not paste text copied from books or websites unless its license allows it. '
                         '<a href="/privacy/">Contributions and privacy</a>.'))

SIMILARITY = 0.85  # names at least this similar (after normalizing) are shown before saving


def item_type_of(obj):
    return {
        Character: CHARACTER_TYPE, ValueOption: VALUE_TYPE,
        Source: "SourceData", DisplayOption: "DisplayOption",
    }[type(obj)]


def make_value_type_key(text):
    """A permanent key in the existing style: lower case words joined by underscores; unique."""
    import re
    base = re.sub(r"[^a-z0-9]+", "_", (text or "").lower().replace("µ", "u")).strip("_") or "value_type"
    key, n = base, 2
    while DisplayOption.objects.filter(name=key).exists():
        key, n = f"{base}_{n}", n + 1
    return key


def ensure_history_baseline(obj):
    """Before the first site change to a release row, record its release version in the history,
    so the history can show what it was before."""
    model = type(obj)
    if obj.pk is None or model.history.filter(id=obj.pk).exists():
        return
    original = model.objects.filter(pk=obj.pk).first()
    if original is not None:
        model.history.bulk_history_create(
            [original], default_change_reason="As released", default_date=original.updated_at,
        )


def set_label(item_type, item_id, label_type, text, reason, language="en"):
    """Create, update or remove one label so it matches `text`. Returns (label or None, created)."""
    text = (text or "").strip()
    label = Label.objects.filter(
        labelable_type=item_type, labelable_id=item_id, language=language, label_type=label_type
    ).first()
    if label:
        ensure_history_baseline(label)
    if label and not text:
        label._change_reason = reason
        label.delete()
    elif label and label.text != text:
        label.text = text
        label._change_reason = reason
        label.save()
    elif not label and text:
        label = Label(labelable_type=item_type, labelable_id=item_id, language=language,
                      label_type=label_type, text=text)
        label._change_reason = reason
        label.save()
        return label, True
    return label if text else None, False


class ReasonForm(forms.Form):
    reason = forms.CharField(
        label=_("Reason for this change"), required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text=_("Optional. Shown in the public edit history."),
    )


class TrackedForm(forms.ModelForm):
    """Adds a per-change reason, the duplicate / similar-name check, and site bookkeeping."""

    dup_field = "name"
    reason = ReasonForm.base_fields["reason"]
    confirm_similar = forms.BooleanField(
        required=False, label=_("Save anyway: this is not the same as the similar names listed above"),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.similar = []
        self.fields[self.dup_field].required = True

    def candidates(self):
        return self._meta.model.objects.all()

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get(self.dup_field)
        if not value:
            return cleaned
        norm = normalize_name(value)
        if not norm:
            self.add_error(self.dup_field, _("Must contain at least one letter or number."))
            return cleaned
        # The instance still holds the old value here, so we can tell whether the name changed.
        changed = self.instance.pk is None or normalize_name(getattr(self.instance, self.dup_field)) != norm
        if not changed:
            return cleaned
        qs = self.candidates()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        exact = []
        for obj in qs:
            other = normalize_name(getattr(obj, self.dup_field))
            if other == norm:
                exact.append(obj)
            elif SequenceMatcher(None, other, norm).ratio() >= SIMILARITY:
                self.similar.append(obj)
        if exact:
            listed = "; ".join(f"“{getattr(o, self.dup_field)}” ({getattr(o, 'code', None) or 'ID ' + str(o.pk)})" for o in exact)
            self.add_error(self.dup_field, _("Already exists, ignoring case, spacing and punctuation: %(listed)s.") % {"listed": listed})
        elif self.similar and not cleaned.get("confirm_similar"):
            self.add_error(None, _("Similar names already exist (listed below). Check they are not the same, then tick “Save anyway”."))
        return cleaned

    def change_reason(self):
        return self.cleaned_data.get("reason", "")

    @transaction.atomic
    def save(self, commit=True):
        obj = super().save(commit=False)
        is_new = obj.pk is None
        ensure_history_baseline(obj)
        self.before_save(obj, is_new)
        obj._change_reason = self.change_reason()
        obj.save()
        if is_new:
            ItemMeta.objects.create(item_type=item_type_of(obj), item_id=obj.pk, created_by=self.user)
        self.after_save(obj)
        return obj

    def before_save(self, obj, is_new):
        pass

    def after_save(self, obj):
        pass


class CharacterForm(TrackedForm):
    name_scientific = forms.CharField(label=_("Scientific name"), max_length=255, required=False,
                                      help_text=_("e.g. Pileus Width for Cap Width."))
    unit = forms.CharField(label=_("Unit"), max_length=30, required=False, help_text=_("e.g. mm, µm. Leave blank if none."))
    applies_to = forms.ModelMultipleChoiceField(
        queryset=FungusType.objects.order_by("name"), required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Applies to"), help_text=_("Leave all unticked if the character applies to all fungi."),
    )

    class Meta:
        model = Character
        fields = [
            "name", "name_scientific", "description", "unit", "part", "observation_method",
            "display_option", "applies_to", "source", "comments",
        ]
        labels = {"name": _("Name"), "description": _("Definition"), "part": _("Part"),
                  "observation_method": _("Observation method"), "display_option": _("Value type"),
                  "source": _("Source"), "comments": _("Comments")}
        help_texts = {
            "display_option": _("The kind of value: a number in mm, text, color, a list of value options, …"),
            "comments": _("Notes kept with the character."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(self.Meta.fields)
        if self.instance.pk:
            props = self.instance.props
            self.initial.setdefault("name_scientific", props.get("name_scientific", ""))
            self.initial.setdefault("unit", props.get("unit", ""))
            self.initial.setdefault("applies_to", list(self.instance.applies_to.values_list("pk", flat=True)))

    def before_save(self, obj, is_new):
        if is_new:
            obj.code = CodeCounter.next_code("FCC", Character)
        props = dict(obj.properties or {})
        for key in ("name_scientific", "unit"):
            value = self.cleaned_data.get(key, "").strip()
            if value:
                props[key] = value
            else:
                props.pop(key, None)
        obj.properties = props

    def after_save(self, obj):
        reason = self.change_reason()
        set_label(CHARACTER_TYPE, obj.pk, "name", obj.name, reason)
        set_label(CHARACTER_TYPE, obj.pk, "scientific_name", self.cleaned_data.get("name_scientific"), reason)
        set_label(CHARACTER_TYPE, obj.pk, "definition", obj.description, reason)
        wanted = set(self.cleaned_data.get("applies_to") or [])
        for tag in obj.fungus_type_tags.select_related("fungus_type"):
            if tag.fungus_type not in wanted:
                ensure_history_baseline(tag)
                tag._change_reason = reason
                tag.delete()
            else:
                wanted.discard(tag.fungus_type)
        for ft in wanted:
            tag = CharacterFungusType(character=obj, fungus_type=ft)
            tag._change_reason = reason
            tag.save()

    def _save_m2m(self):
        pass  # "applies to" tags are saved in after_save (they have their own history).


class ValueOptionForm(TrackedForm):
    class Meta:
        model = ValueOption
        fields = ["name", "description", "source", "comments"]
        labels = {"name": _("Value option"), "description": _("Definition"), "source": _("Source"), "comments": _("Comments")}

    def candidates(self):
        return ValueOption.objects.filter(character=self.instance.character)

    def before_save(self, obj, is_new):
        if is_new:
            obj.code = CodeCounter.next_code("FCV", ValueOption)

    def after_save(self, obj):
        set_label(VALUE_TYPE, obj.pk, "name", obj.name, self.change_reason())
        set_label(VALUE_TYPE, obj.pk, "definition", obj.description, self.change_reason())


class DisplayOptionForm(TrackedForm):
    """People type a display name; a new value type gets a permanent key made from it (never changed later)."""
    dup_field = "label_text"
    label_text = forms.CharField(label=_("Value type"), max_length=255,
                                 help_text=_("The name people see, for example “Number (mm)”."))

    class Meta:
        model = DisplayOption
        fields = ["description", "comments"]
        labels = {"description": _("Description"), "comments": _("Comments")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(["label_text", "description", "comments", "reason", "confirm_similar"])
        if self.instance.pk:
            self.initial.setdefault("label_text", self.instance.display_name("en"))
            self.fields["label_text"].help_text = _("The name people see. Its permanent key, used by programs, stays “%(key)s”.") % {"key": self.instance.name}

    def before_save(self, obj, is_new):
        if is_new:
            obj.name = make_value_type_key(self.cleaned_data["label_text"])

    def after_save(self, obj):
        set_label(DISPLAY_OPTION_TYPE, obj.pk, "name", self.cleaned_data["label_text"], self.change_reason())
        obj._display_names = None


class SourceForm(TrackedForm):
    dup_field = "title"

    class Meta:
        model = Source
        fields = ["title", "author", "ref", "item_code", "source_type", "comments"]
        labels = {"title": _("Title"), "author": _("Author"), "ref": _("Reference / URL"), "item_code": _("Item code"),
                  "source_type": _("Type"), "comments": _("Comments")}


class SignupExtraForm(forms.Form):
    """Extra sign-up field (allauth ACCOUNT_SIGNUP_FORM_CLASS): agreement to the contribution terms."""

    agree = forms.BooleanField(required=True, label=AGREE_LABEL, help_text=AGREE_HELP)

    def signup(self, request, user):
        from .models import Consent
        Consent.record(user)


class AgreeForm(forms.Form):
    agree = forms.BooleanField(required=True, label=AGREE_LABEL, help_text=AGREE_HELP)

