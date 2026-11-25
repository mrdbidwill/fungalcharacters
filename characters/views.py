from itertools import chain

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    CharacterForm, DisplayOptionForm, ReasonForm, SignupForm, SourceForm, ValueOptionForm,
)
from .models import Character, DisplayOption, Part, Source, ValueOption
from .permissions import can_edit, delete_blockers, is_admin

# URL name for each kind of item, used by the history pages.
KINDS = {
    "character": Character,
    "option": ValueOption,
    "value-type": DisplayOption,
    "source": Source,
}
KIND_OF = {model: kind for kind, model in KINDS.items()}
HISTORY_HIDDEN_FIELDS = ["updated_at", "name_normalized"]


def visible(model, user):
    qs = model.objects.all()
    if is_admin(user):
        return qs
    qs = qs.filter(is_hidden=False)
    if model is ValueOption:
        qs = qs.filter(character__is_hidden=False)
    return qs


def item_url(obj):
    if isinstance(obj, Character):
        return obj.get_absolute_url()
    if isinstance(obj, ValueOption):
        return obj.character.get_absolute_url()
    if isinstance(obj, DisplayOption):
        return reverse("characters:value_type_detail", args=[obj.pk])
    return reverse("characters:source_detail", args=[obj.pk])


# ---------- generic create / edit / delete ----------

def _save(request, form, title, cancel_url):
    """Shared POST handling for create and edit forms."""
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if obj.pk is None:
            obj.created_by = request.user
        obj._change_reason = form.cleaned_data.get("reason", "")
        obj.save()
        messages.success(request, "Saved.")
        return redirect(item_url(obj))
    return render(request, "characters/form.html", {"form": form, "title": title, "cancel_url": cancel_url})


def _edit(request, model, form_class, pk, label):
    obj = get_object_or_404(visible(model, request.user), pk=pk)
    if not can_edit(request.user, obj):
        raise PermissionDenied("You can edit only your own work.")
    form = form_class(request.POST or None, instance=obj)
    return _save(request, form, f"Edit {label}: {obj}", item_url(obj))


def _delete(request, model, pk, label, after_url):
    obj = get_object_or_404(visible(model, request.user), pk=pk)
    if not can_edit(request.user, obj):
        raise PermissionDenied("You can delete only your own work.")
    blockers = delete_blockers(request.user, obj)
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and not blockers and form.is_valid():
        reason = form.cleaned_data["reason"]
        with transaction.atomic():
            if isinstance(obj, Character):
                for child in chain(obj.value_options.all(), obj.core_sequences.all()):
                    child._change_reason = f"Deleted with character {obj.pk}. {reason}".strip()
                    child.delete()
            obj._change_reason = reason
            obj.delete()
        messages.success(request, f"Deleted {label} “{obj}”.")
        return redirect(after_url(obj))
    extra = obj.value_options.count() if isinstance(obj, Character) else 0
    return render(request, "characters/confirm_delete.html", {
        "obj": obj, "label": label, "blockers": blockers, "form": form,
        "cancel_url": item_url(obj), "extra_options": extra,
    })


# ---------- characters ----------

def character_list(request):
    q = request.GET.get("q", "").strip()
    part = request.GET.get("part", "")
    qs = (
        visible(Character, request.user)
        .select_related("part", "observation_method", "display_option", "created_by")
        .annotate(n_options=Count("value_options"))
        .order_by("name", "id")
    )
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if part.isdigit():
        qs = qs.filter(part_id=int(part))
    page = Paginator(qs, 100).get_page(request.GET.get("page"))
    return render(request, "characters/list.html", {
        "page": page, "q": q, "part": part, "parts": Part.objects.order_by("name"),
        "total": visible(Character, request.user).count(),
    })


def character_detail(request, pk):
    c = get_object_or_404(
        visible(Character, request.user).select_related(
            "part", "observation_method", "display_option", "fungus_type", "source", "created_by"
        ),
        pk=pk,
    )
    return render(request, "characters/detail.html", {
        "c": c,
        "options": visible(ValueOption, request.user).filter(character=c).select_related("source", "created_by"),
        "core_sequences": c.core_sequences.select_related("fungus_type"),
        "duplicates": visible(Character, request.user).filter(name_normalized=c.name_normalized).exclude(pk=c.pk),
        "last_change": c.history.select_related("history_user").order_by("-history_date").first(),
    })


@login_required
def character_create(request):
    return _save(request, CharacterForm(request.POST or None), "Add a character", reverse("characters:list"))


@login_required
def character_edit(request, pk):
    return _edit(request, Character, CharacterForm, pk, "character")


@login_required
def character_delete(request, pk):
    return _delete(request, Character, pk, "character", lambda o: reverse("characters:list"))


# ---------- value options ----------

@login_required
def option_create(request, pk):
    character = get_object_or_404(visible(Character, request.user), pk=pk)
    next_pos = (character.value_options.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0) + 1
    form = ValueOptionForm(
        request.POST or None,
        instance=ValueOption(character=character, sort_order=next_pos),
    )
    return _save(request, form, f"Add a value option to “{character}”", character.get_absolute_url())


@login_required
def option_edit(request, pk):
    return _edit(request, ValueOption, ValueOptionForm, pk, "value option")


@login_required
def option_delete(request, pk):
    return _delete(request, ValueOption, pk, "value option", lambda o: o.character.get_absolute_url())


# ---------- value types ----------

def value_type_list(request):
    items = visible(DisplayOption, request.user).select_related("created_by").annotate(n=Count("characters")).order_by("name")
    return render(request, "characters/value_type_list.html", {"items": items})


def value_type_detail(request, pk):
    obj = get_object_or_404(visible(DisplayOption, request.user).select_related("created_by"), pk=pk)
    return render(request, "characters/value_type_detail.html", {
        "obj": obj, "characters": visible(Character, request.user).filter(display_option=obj).order_by("name"),
    })


@login_required
def value_type_create(request):
    return _save(request, DisplayOptionForm(request.POST or None), "Add a value type", reverse("characters:value_type_list"))


@login_required
def value_type_edit(request, pk):
    return _edit(request, DisplayOption, DisplayOptionForm, pk, "value type")


@login_required
def value_type_delete(request, pk):
    return _delete(request, DisplayOption, pk, "value type", lambda o: reverse("characters:value_type_list"))


# ---------- sources ----------

def source_list(request):
    items = (
        visible(Source, request.user).select_related("source_type", "created_by")
        .annotate(n=Count("characters", distinct=True)).order_by("title")
    )
    return render(request, "characters/source_list.html", {"items": items})


def source_detail(request, pk):
    obj = get_object_or_404(visible(Source, request.user).select_related("source_type", "created_by"), pk=pk)
    return render(request, "characters/source_detail.html", {
        "obj": obj, "characters": visible(Character, request.user).filter(source=obj).order_by("name"),
    })


@login_required
def source_create(request):
    return _save(request, SourceForm(request.POST or None), "Add a source", reverse("characters:source_list"))


@login_required
def source_edit(request, pk):
    return _edit(request, Source, SourceForm, pk, "source")


@login_required
def source_delete(request, pk):
    return _delete(request, Source, pk, "source", lambda o: reverse("characters:source_list"))


# ---------- history ----------

def _display(model, field_name, value):
    """Human-readable value for a history diff (foreign keys shown by name)."""
    if value in (None, ""):
        return "—"
    field = model._meta.get_field(field_name)
    if field.is_relation:
        related = field.related_model.objects.filter(pk=value).first()
        return f"{related} (ID {value})" if related else f"ID {value}"
    return value


def history(request, kind, pk):
    model = KINDS.get(kind)
    if model is None:
        raise Http404
    current = model.objects.filter(pk=pk).first()
    if current is not None and not visible(model, request.user).filter(pk=pk).exists():
        raise Http404
    records = list(model.history.filter(id=pk).select_related("history_user").order_by("history_date", "history_id"))
    if not records:
        raise Http404
    rows = []
    for i, rec in enumerate(records):
        changes = []
        if i and rec.history_type == "~":
            diff = rec.diff_against(records[i - 1], excluded_fields=HISTORY_HIDDEN_FIELDS)
            changes = [
                (model._meta.get_field(c.field).verbose_name, _display(model, c.field, c.old), _display(model, c.field, c.new))
                for c in diff.changes
            ]
        rows.append({"rec": rec, "changes": changes})
    rows.reverse()
    return render(request, "characters/history.html", {
        "rows": rows, "current": current, "title": str(current or records[-1].instance),
        "kind_label": model._meta.verbose_name, "current_url": item_url(current) if current else None,
    })


def recent_changes(request):
    per_model = []
    for kind, model in KINDS.items():
        qs = model.history.select_related("history_user").order_by("-history_date")
        if not is_admin(request.user):
            # Hide every history entry of an item that is hidden now, including entries from before it was hidden.
            qs = qs.exclude(id__in=model.objects.exclude(pk__in=visible(model, request.user)).values("pk"))
        for rec in qs[:100]:
            per_model.append({"rec": rec, "kind": kind, "label": model._meta.verbose_name,
                              "name": getattr(rec, "name", None) or getattr(rec, "title", "")})
    rows = sorted(per_model, key=lambda r: r["rec"].history_date, reverse=True)[:100]
    return render(request, "characters/recent_changes.html", {"rows": rows})


# ---------- accounts ----------

def signup(request):
    if request.user.is_authenticated:
        return redirect("characters:list")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome, {user.username}. You are signed in.")
        return redirect("characters:list")
    return render(request, "characters/form.html", {"form": form, "title": "Sign up", "submit": "Sign up"})
