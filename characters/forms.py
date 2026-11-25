from difflib import SequenceMatcher

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Character, DisplayOption, Source, ValueOption
from .normalize import normalize_name

SIMILARITY = 0.85  # names at least this similar (after normalizing) are shown before saving


class ReasonForm(forms.Form):
    reason = forms.CharField(
        label="Reason for this change", required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Optional. Shown in the public edit history.",
    )


class TrackedForm(forms.ModelForm):
    """Adds a per-change reason and the duplicate / similar-name check."""

    dup_field = "name"
    reason = ReasonForm.base_fields["reason"]
    confirm_similar = forms.BooleanField(
        required=False, label="Save anyway: this is not the same as the similar names listed above",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.similar = []
        for name in ("source", "display_option", "part", "observation_method", "fungus_type", "source_type"):
            if name in self.fields and hasattr(self.fields[name].queryset.model, "is_hidden"):
                self.fields[name].queryset = self.fields[name].queryset.filter(is_hidden=False)

    def candidates(self):
        return self._meta.model.objects.all()

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get(self.dup_field)
        if not value:
            return cleaned
        norm = normalize_name(value)
        if not norm:
            self.add_error(self.dup_field, "Must contain at least one letter or number.")
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
            listed = "; ".join(f"“{getattr(o, self.dup_field)}” (ID {o.pk})" for o in exact)
            self.add_error(self.dup_field, f"Already exists, ignoring case, spacing and punctuation: {listed}.")
        elif self.similar and not cleaned.get("confirm_similar"):
            self.add_error(None, "Similar names already exist (listed below). Check they are not the same, then tick “Save anyway”.")
        return cleaned


class CharacterForm(TrackedForm):
    class Meta:
        model = Character
        fields = [
            "name", "name_scientific", "description", "part", "observation_method",
            "display_option", "fungus_type", "source", "comments",
        ]
        labels = {"display_option": "Value type"}
        help_texts = {
            "display_option": "The kind of value: a number in mm, text, color, a list of value options, …",
            "comments": "Notes kept with the character.",
        }


class ValueOptionForm(TrackedForm):
    class Meta:
        model = ValueOption
        fields = ["name", "name_scientific", "description", "source", "sort_order", "comments"]
        labels = {"name": "Value option", "sort_order": "Position in list"}

    def candidates(self):
        return ValueOption.objects.filter(character=self.instance.character)


class DisplayOptionForm(TrackedForm):
    class Meta:
        model = DisplayOption
        fields = ["name", "description", "comments"]
        labels = {"name": "Value type"}


class SourceForm(TrackedForm):
    dup_field = "title"

    class Meta:
        model = Source
        fields = ["title", "author", "ref", "item_code", "source_type", "comments"]


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is taken.")
        return username
