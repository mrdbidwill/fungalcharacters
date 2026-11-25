from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    CharacterForm, DisplayOptionForm, ReasonForm, SignupForm, SourceForm, ValueOptionForm,
    ensure_history_baseline, item_type_of,
)
from .models import (
    CHARACTER_TYPE, VALUE_TYPE, Character, CharacterFungusType, CoreSequence, DisplayOption, FungusType, ItemMeta,
    Label, Part, Release, Source, ValueOption,
)
from .permissions import can_edit, delete_blockers, is_admin

# URL keyword for each kind of item (history and hide pages).
KINDS = {"character": Character, "value": ValueOption, "value-type": DisplayOption, "source": Source}
KIND_OF = {model: kind for kind, model in KINDS.items()}
HISTORY_HIDDEN_FIELDS = ["updated_at"]
LABEL_NAMES = {"name": "Name", "scientific_name": "Scientific name", "definition": "Definition"}


# ---------- helpers ----------

def hidden_ids(model):
    return ItemMeta.objects.filter(item_type=item_type_of(model()), is_hidden=True).values("item_id")


def visible(model, user):
    qs = model.objects.all()
    if is_admin(user):
        return qs
    qs = qs.exclude(pk__in=hidden_ids(model))
    if model is ValueOption:
        qs = qs.exclude(character_id__in=hidden_ids(Character))
    return qs


def is_hidden(obj):
    return ItemMeta.objects.filter(item_type=item_type_of(obj), item_id=obj.pk, is_hidden=True).exists()


def creators(model, ids):
    """{item id: username} for items created on the site."""
    return dict(
        ItemMeta.objects.filter(item_type=item_type_of(model()), item_id__in=list(ids), created_by__isnull=False)
        .values_list("item_id", "created_by__username")
    )


def labels_for(item_type, ids, label_type, language="en"):
    return dict(
        Label.objects.filter(labelable_type=item_type, labelable_id__in=list(ids),
                             label_type=label_type, language=language)
        .values_list("labelable_id", "text")
    )


def scientific_mode(request):
    return request.session.get("names") == "scientific"


def item_url(obj):
    if isinstance(obj, (Character, ValueOption)):
        return obj.get_absolute_url() if isinstance(obj, Character) else obj.character.get_absolute_url() + f"#{obj.code}"
    if isinstance(obj, DisplayOption):
        return reverse("characters:value_type_detail", args=[obj.pk])
    return reverse("characters:source_detail", args=[obj.pk])


def find_code(code):
    model = Character if code.startswith("FCC") else ValueOption
    return model, model.objects.filter(code=code).first()


# ---------- generic create / edit / delete ----------

def _save(request, form, title, cancel_url):
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, "Saved.")
        return redirect(item_url(obj))
    return render(request, "characters/form.html", {"form": form, "title": title, "cancel_url": cancel_url})


def _edit(request, obj, form_class, label):
    if not visible(type(obj), request.user).filter(pk=obj.pk).exists():
        raise Http404
    if not can_edit(request.user, obj):
        raise PermissionDenied("You can edit only your own work.")
    form = form_class(posted(request), instance=obj, user=request.user)
    return _save(request, form, f"Edit {label}: {obj}", item_url(obj))


def posted(request):
    """Form data if this is a POST (even an empty one), else None."""
    return request.POST if request.method == "POST" else None


def _delete_with_labels(obj, item_type, reason):
    for label in Label.objects.filter(labelable_type=item_type, labelable_id=obj.pk):
        ensure_history_baseline(label)
        label._change_reason = reason
        label.delete()
    ensure_history_baseline(obj)
    obj._change_reason = reason
    obj.delete()


def _delete(request, obj, label, after_url):
    if not visible(type(obj), request.user).filter(pk=obj.pk).exists():
        raise Http404
    if not can_edit(request.user, obj):
        raise PermissionDenied("You can delete only your own work.")
    blockers = delete_blockers(request.user, obj)
    form = ReasonForm(posted(request))
    if request.method == "POST" and not blockers and form.is_valid():
        reason = form.cleaned_data["reason"]
        after = after_url(obj)
        with transaction.atomic():
            if isinstance(obj, Character):
                child_reason = f"Deleted with character {obj.code}. {reason}".strip()
                for value in obj.value_options.all():
                    _delete_with_labels(value, VALUE_TYPE, child_reason)
                    ItemMeta.objects.filter(item_type=VALUE_TYPE, item_id=value.pk).delete()
                for tag in obj.fungus_type_tags.all():
                    ensure_history_baseline(tag)
                    tag._change_reason = child_reason
                    tag.delete()
                for seq in obj.core_sequences.all():
                    ensure_history_baseline(seq)
                    seq._change_reason = child_reason
                    seq.delete()
                _delete_with_labels(obj, CHARACTER_TYPE, reason)
            elif isinstance(obj, ValueOption):
                _delete_with_labels(obj, VALUE_TYPE, reason)
            else:
                ensure_history_baseline(obj)
                obj._change_reason = reason
                obj.delete()
            ItemMeta.objects.filter(item_type=item_type_of(obj), item_id=obj.pk).delete()
        messages.success(request, f"Deleted {label} “{obj}”.")
        return redirect(after)
    return render(request, "characters/confirm_delete.html", {
        "obj": obj, "label": label, "blockers": blockers, "form": form, "cancel_url": item_url(obj),
        "extra_values": obj.value_options.count() if isinstance(obj, Character) else 0,
    })


# ---------- home, thanks, downloads ----------

def home(request):
    return render(request, "characters/home.html", {
        "n_characters": visible(Character, request.user).count(),
        "n_values": visible(ValueOption, request.user).count(),
    })


def thanks(request):
    return render(request, "characters/thanks.html")


RELEASES_DIR = settings.BASE_DIR / "data" / "releases"
# What each release file is for (from the release README). Anything else is listed under "Other files".
DOWNLOAD_KINDS = [
    (".xlsx", "Excel workbook", "Browse in Excel or Numbers."),
    ("csv/characters_flat.csv", "CSV: characters", "One row per character."),
    ("csv/value_options_flat.csv", "CSV: value options", "One row per value option."),
    ("csv/values_flat.csv", "CSV: value options", "One row per value option (called “values” in this release)."),
    (".json", "JSON", "For programmers."),
    ("_postgresql.sql", "SQL for PostgreSQL 16/17", "Creates the tables and loads all data."),
    (".sql", "SQL for MySQL 8", "Creates the tables and loads all data."),
    ("_skos.ttl", "SKOS vocabulary (Turtle)", "For vocabulary tools (W3C SKOS)."),
    ("_sdd.xml", "SDD 1.1 (TDWG XML)", "For identification-key tools."),
    ("README.md", "Release notes", "What is in the release, and how to cite it."),
    ("CHANGELOG.md", "Changelog", "What changed in each release."),
]


def release_files(version):
    folder = RELEASES_DIR / version
    if not folder.is_dir():
        return {}
    return {p.relative_to(folder).as_posix(): p for p in folder.rglob("*") if p.is_file()}


def downloads(request):
    release = Release.objects.order_by("-released_at", "-id").first()
    main, other = [], []
    if release:
        files = release_files(release.version)
        used = set()
        for suffix, title, note in DOWNLOAD_KINDS:
            for name in sorted(files):
                if name not in used and name.endswith(suffix) and (suffix.startswith(("csv/", "README", "CHANGELOG")) or "/" not in name):
                    used.add(name)
                    main.append({"name": name, "title": title, "note": note, "size": files[name].stat().st_size})
        other = [{"name": n, "size": files[n].stat().st_size} for n in sorted(files) if n not in used]
    return render(request, "characters/downloads.html", {"release": release, "main": main, "other": other})


def download_file(request, version, name):
    path = release_files(version).get(name)
    if path is None:
        raise Http404
    return FileResponse(path.open("rb"), as_attachment=True, filename=path.name)


# ---------- characters and values ----------

def character_list(request):
    q = request.GET.get("q", "").strip()
    part = request.GET.get("part", "")
    fungus = request.GET.get("fungus", "")
    qs = (
        visible(Character, request.user)
        .select_related("part", "observation_method", "display_option")
        .annotate(n_values=Count("value_options"))
        .order_by("name", "id")
    )
    if q:
        sci_matches = Label.objects.filter(labelable_type=CHARACTER_TYPE, text__icontains=q).values("labelable_id")
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(code__iexact=q) | Q(pk__in=sci_matches))
    if part.isdigit():
        qs = qs.filter(part_id=int(part))
    if fungus == "all":
        qs = qs.filter(fungus_type_tags__isnull=True)
    elif fungus.isdigit():
        qs = qs.filter(fungus_type_tags__fungus_type_id=int(fungus))
    page = Paginator(qs, 100).get_page(request.GET.get("page"))
    ids = [c.pk for c in page]
    sci = labels_for(CHARACTER_TYPE, ids, "scientific_name")
    by = creators(Character, ids)
    for c in page:
        c.scientific = sci.get(c.pk, "")
        c.created_by_name = by.get(c.pk)
    return render(request, "characters/list.html", {
        "page": page, "q": q, "part": part, "fungus": fungus,
        "parts": Part.objects.order_by("name"), "fungus_types": FungusType.objects.order_by("name"),
        "total": visible(Character, request.user).count(), "scientific": scientific_mode(request),
    })


def by_code(request, code):
    model, obj = find_code(code)
    if obj is None:
        retired = model.history.filter(code=code).order_by("-history_date").first()
        if retired is None:
            raise Http404
        return render(request, "characters/retired.html", {"code": code, "rec": retired}, status=410)
    if isinstance(obj, ValueOption):
        return redirect(item_url(obj))
    return character_detail(request, obj)


def character_detail(request, c):
    if not visible(Character, request.user).filter(pk=c.pk).exists():
        raise Http404
    values = list(visible(ValueOption, request.user).filter(character=c).select_related("source"))
    value_by = creators(ValueOption, [v.pk for v in values])
    hidden_values = set(hidden_ids(ValueOption).values_list("item_id", flat=True)) if is_admin(request.user) else set()
    for v in values:
        v.created_by_name = value_by.get(v.pk)
        v.hidden = v.pk in hidden_values
    sci = labels_for(CHARACTER_TYPE, [c.pk], "scientific_name").get(c.pk, "")
    return render(request, "characters/detail.html", {
        "c": c, "scientific": sci, "values": values,
        "applies_to": c.applies_to.order_by("name"),
        "core_sequences": c.core_sequences.select_related("fungus_type"),
        "created_by_name": creators(Character, [c.pk]).get(c.pk),
        "hidden": is_hidden(c), "scientific_mode": scientific_mode(request),
    })


@login_required
def character_create(request):
    form = CharacterForm(posted(request), user=request.user)
    return _save(request, form, "Add a character", reverse("characters:list"))


@login_required
def edit_by_code(request, code):
    model, obj = find_code(code)
    if obj is None:
        raise Http404
    if model is Character:
        return _edit(request, obj, CharacterForm, "character")
    return _edit(request, obj, ValueOptionForm, "value option")


@login_required
def delete_by_code(request, code):
    model, obj = find_code(code)
    if obj is None:
        raise Http404
    if model is Character:
        return _delete(request, obj, "character", lambda o: reverse("characters:list"))
    return _delete(request, obj, "value option", lambda o: o.character.get_absolute_url())


@login_required
def value_create(request, code):
    character = get_object_or_404(visible(Character, request.user), code=code)
    form = ValueOptionForm(posted(request), instance=ValueOption(character=character), user=request.user)
    return _save(request, form, f"Add a value option to “{character}”", character.get_absolute_url())


# ---------- value types ----------

def value_type_list(request):
    items = list(visible(DisplayOption, request.user).annotate(n=Count("characters")).order_by("name"))
    by = creators(DisplayOption, [o.pk for o in items])
    for o in items:
        o.created_by_name = by.get(o.pk)
    return render(request, "characters/value_type_list.html", {"items": items})


def value_type_detail(request, pk):
    obj = get_object_or_404(visible(DisplayOption, request.user), pk=pk)
    return render(request, "characters/value_type_detail.html", {
        "obj": obj, "characters": visible(Character, request.user).filter(display_option=obj).order_by("name"),
        "created_by_name": creators(DisplayOption, [obj.pk]).get(obj.pk), "hidden": is_hidden(obj),
    })


@login_required
def value_type_create(request):
    form = DisplayOptionForm(posted(request), user=request.user)
    return _save(request, form, "Add a value type", reverse("characters:value_type_list"))


@login_required
def value_type_edit(request, pk):
    return _edit(request, get_object_or_404(DisplayOption, pk=pk), DisplayOptionForm, "value type")


@login_required
def value_type_delete(request, pk):
    return _delete(request, get_object_or_404(DisplayOption, pk=pk), "value type",
                   lambda o: reverse("characters:value_type_list"))


# ---------- sources ----------

def source_list(request):
    items = list(
        visible(Source, request.user).select_related("source_type")
        .annotate(n=Count("characters", distinct=True)).order_by("title")
    )
    by = creators(Source, [o.pk for o in items])
    for o in items:
        o.created_by_name = by.get(o.pk)
    return render(request, "characters/source_list.html", {"items": items})


def source_detail(request, pk):
    obj = get_object_or_404(visible(Source, request.user).select_related("source_type"), pk=pk)
    return render(request, "characters/source_detail.html", {
        "obj": obj, "characters": visible(Character, request.user).filter(source=obj).order_by("name"),
        "created_by_name": creators(Source, [obj.pk]).get(obj.pk), "hidden": is_hidden(obj),
    })


@login_required
def source_create(request):
    form = SourceForm(posted(request), user=request.user)
    return _save(request, form, "Add a source", reverse("characters:source_list"))


@login_required
def source_edit(request, pk):
    return _edit(request, get_object_or_404(Source, pk=pk), SourceForm, "source")


@login_required
def source_delete(request, pk):
    return _delete(request, get_object_or_404(Source, pk=pk), "source", lambda o: reverse("characters:source_list"))


# ---------- admin: hide / unhide ----------

@require_POST
def toggle_hidden(request, kind, pk):
    if not is_admin(request.user):
        raise PermissionDenied
    model = KINDS.get(kind)
    if model is None:
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    meta, _ = ItemMeta.objects.get_or_create(item_type=item_type_of(obj), item_id=obj.pk)
    meta.is_hidden = not meta.is_hidden
    meta.save()
    messages.success(request, f"{'Hidden' if meta.is_hidden else 'Shown again'}: {obj}.")
    return redirect(item_url(obj))


# ---------- history ----------

def _display(model, field_name, value):
    if value in (None, ""):
        return "—"
    field = model._meta.get_field(field_name)
    if field.is_relation:
        related = field.related_model.objects.filter(pk=value).first()
        return f"{related}" if related else f"ID {value}"
    return value


def _rows_for(model, records, describe=None):
    """Turn history records of one object into display rows with old → new changes."""
    rows = []
    for i, rec in enumerate(records):
        changes = []
        if describe:
            changes = describe(rec, records[i - 1] if i else None)
        elif i and rec.history_type == "~":
            diff = rec.diff_against(records[i - 1], excluded_fields=HISTORY_HIDDEN_FIELDS)
            for c in diff.changes:
                if c.field == "properties":
                    # Show changed keys (scientific name is listed with the labels).
                    old, new = c.old or {}, c.new or {}
                    for key in sorted(set(old) | set(new)):
                        if key != "name_scientific" and old.get(key) != new.get(key):
                            changes.append((key.replace("_", " ").capitalize(), old.get(key, "—"), new.get(key, "—")))
                    continue
                changes.append((str(model._meta.get_field(c.field).verbose_name),
                                _display(model, c.field, c.old), _display(model, c.field, c.new)))
        rows.append({"rec": rec, "changes": changes})
    return rows


def _label_rows(item_type, item_id):
    rows = []
    records = Label.history.filter(labelable_type=item_type, labelable_id=item_id).select_related("history_user")
    by_label = {}
    for rec in records.order_by("history_date", "history_id"):
        by_label.setdefault(rec.id, []).append(rec)
    for recs in by_label.values():
        for i, rec in enumerate(recs):
            name = LABEL_NAMES.get(rec.label_type, rec.label_type)
            if rec.language != "en":
                name += f" ({rec.language})"
            old = recs[i - 1].text if i else "—"
            new = "—" if rec.history_type == "-" else rec.text
            if rec.history_type == "+":
                old = "—"
            rows.append({"rec": rec, "changes": [(name, old, new)], "label_change": True})
    return rows


def _history_page(request, model, pk, current):
    records = list(model.history.filter(id=pk).select_related("history_user").order_by("history_date", "history_id"))
    rows = _rows_for(model, records)
    if model in (Character, ValueOption):
        # Name, scientific name and definition changes are stored as labels.
        label_rows = _label_rows(CHARACTER_TYPE if model is Character else VALUE_TYPE, pk)
        # A label written in the same save as the item itself is shown as part of that change.
        rows += label_rows
    if model is Character:
        for rec in CharacterFungusType.history.filter(character_id=pk).select_related("history_user", "fungus_type"):
            ft = FungusType.objects.filter(pk=rec.fungus_type_id).first()
            sign = "added" if rec.history_type == "+" else "removed" if rec.history_type == "-" else "changed"
            rows.append({"rec": rec, "changes": [("Applies to", "", f"{ft} {sign}")]})
        for rec in CoreSequence.history.filter(character_id=pk).select_related("history_user"):
            if rec.history_change_reason == "As released":
                continue
            ft = FungusType.objects.filter(pk=rec.fungus_type_id).first()
            sign = "added" if rec.history_type == "+" else "removed" if rec.history_type == "-" else "changed"
            rows.append({"rec": rec, "changes": [("Core order", "", f"{ft} #{rec.sequence} {sign}")]})
    if not rows and current is None:
        raise Http404
    rows.sort(key=lambda r: (r["rec"].history_date, r["rec"].history_id), reverse=True)
    title = str(current) if current else str(records[-1].instance) if records else ""
    return render(request, "characters/history.html", {
        "rows": rows, "current": current, "title": title,
        "kind_label": model._meta.verbose_name, "current_url": item_url(current) if current else None,
        "from_release": current is not None and not creators(model, [pk]),
    })


def history(request, kind, pk):
    model = KINDS.get(kind)
    if model is None:
        raise Http404
    current = model.objects.filter(pk=pk).first()
    if current is not None and not visible(model, request.user).filter(pk=pk).exists():
        raise Http404
    return _history_page(request, model, pk, current)


def history_by_code(request, code):
    model, obj = find_code(code)
    if obj is not None:
        if not visible(model, request.user).filter(pk=obj.pk).exists():
            raise Http404
        return _history_page(request, model, obj.pk, obj)
    rec = model.history.filter(code=code).first()
    if rec is None:
        raise Http404
    return _history_page(request, model, rec.id, None)


def recent_changes(request):
    rows = []
    for kind, model in KINDS.items():
        qs = model.history.select_related("history_user").order_by("-history_date")
        if not is_admin(request.user):
            qs = qs.exclude(id__in=model.objects.exclude(pk__in=visible(model, request.user)).values("pk"))
        for rec in qs[:100]:
            rows.append({"rec": rec, "kind": kind, "label": model._meta.verbose_name,
                         "name": getattr(rec, "name", None) or getattr(rec, "title", "") or "",
                         "code": getattr(rec, "code", None)})
    rows = sorted(rows, key=lambda r: r["rec"].history_date, reverse=True)[:100]
    return render(request, "characters/recent_changes.html", {"rows": rows})


# ---------- names toggle and accounts ----------

def set_name_mode(request, mode):
    if mode not in ("english", "scientific"):
        raise Http404
    request.session["names"] = mode
    back = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = "/"
    return redirect(back)


def signup(request):
    if request.user.is_authenticated:
        return redirect("characters:list")
    form = SignupForm(posted(request))
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome, {user.username}. You are signed in.")
        return redirect("characters:list")
    return render(request, "characters/form.html", {"form": form, "title": "Sign up", "submit": "Sign up"})
