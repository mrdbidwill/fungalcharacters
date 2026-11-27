from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language, get_language_info, gettext as _, gettext_lazy, pgettext_lazy
from django.views.decorators.http import require_POST

from .forms import (
    CharacterForm, DisplayOptionForm, ReasonForm, SourceForm, ValueOptionForm,
    ensure_history_baseline, item_type_of,
)
from .models import (
    Consent, CHARACTER_TYPE, VALUE_TYPE, Character, CharacterFungusType, CoreSequence, DisplayOption, FungusType, ItemMeta,
    Label, Part, Release, Source, ValueOption,
)
from .permissions import can_edit, delete_blockers, is_admin

# URL keyword for each kind of item (history and hide pages).
KINDS = {"character": Character, "value": ValueOption, "value-type": DisplayOption, "source": Source}
KIND_OF = {model: kind for kind, model in KINDS.items()}
HISTORY_HIDDEN_FIELDS = ["updated_at"]
LABEL_NAMES = {"name": gettext_lazy("Name"), "scientific_name": gettext_lazy("Scientific name"), "definition": gettext_lazy("Definition")}
# What each kind of item is called on pages.
KIND_LABELS = {"character": gettext_lazy("character"), "value option": gettext_lazy("value option"),
               "value type": gettext_lazy("value type"), "source": gettext_lazy("source")}


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


def data_language():
    """Language code used for data translations in the labels table (same codes as the interface)."""
    return (get_language() or "en").lower()


def language_name(code):
    try:
        return get_language_info(code)["name_local"]
    except KeyError:
        return code


TRANSLATION_LANGUAGES = [code for code, _name in settings.LANGUAGES if code != "en"]


NAMES_COOKIE = "names"  # remembers common or scientific names (a cookie, not a server-side session)


def scientific_mode(request):
    return request.COOKIES.get(NAMES_COOKIE) == "scientific"


def item_url(obj):
    if isinstance(obj, (Character, ValueOption)):
        return obj.get_absolute_url() if isinstance(obj, Character) else obj.character.get_absolute_url() + f"#{obj.code}"
    if isinstance(obj, DisplayOption):
        return reverse("characters:value_type_detail", args=[obj.pk])
    return reverse("characters:source_detail", args=[obj.pk])


def find_code(code):
    model = Character if code.startswith("FCC") else ValueOption
    return model, model.objects.filter(code=code).first()


def contributor_required(view):
    """Signed in, and agreed to the current contribution terms (asked once, then back to the page)."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not Consent.has_current(request.user):
            return redirect(reverse("characters:agree") + "?next=" + request.get_full_path())
        return view(request, *args, **kwargs)
    return wrapper


# ---------- generic create / edit / delete ----------

def _save(request, form, title, cancel_url):
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, _("Saved."))
        return redirect(item_url(obj))
    return render(request, "characters/form.html", {"form": form, "title": title, "cancel_url": cancel_url})


def _edit(request, obj, form_class, label):
    if not visible(type(obj), request.user).filter(pk=obj.pk).exists():
        raise Http404
    if not can_edit(request.user, obj):
        raise PermissionDenied(_("You can edit only your own work."))
    form = form_class(posted(request), instance=obj, user=request.user)
    return _save(request, form, _("Edit %(kind)s: %(name)s") % {"kind": KIND_LABELS.get(label, label), "name": obj}, item_url(obj))


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
        raise PermissionDenied(_("You can delete only your own work."))
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
        messages.success(request, _("Deleted %(kind)s “%(name)s”.") % {"kind": KIND_LABELS.get(label, label), "name": obj})
        return redirect(after)
    return render(request, "characters/confirm_delete.html", {
        "obj": obj, "label": KIND_LABELS.get(label, label), "blockers": blockers, "form": form, "cancel_url": item_url(obj),
        "extra_values": obj.value_options.count() if isinstance(obj, Character) else 0,
    })


# ---------- home, thanks, downloads ----------

def home(request):
    from .seo import LICENSE_URL, SITE_URL, TERM_SET_ID, jsonld
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{SITE_URL}/#website", "url": f"{SITE_URL}/", "name": "Fungal Characters",
         "description": "A free, publicly maintained list of the characters used to describe and identify fungi."},
        {"@type": "DefinedTermSet", "@id": TERM_SET_ID, "url": f"{SITE_URL}/characters/", "name": "Fungal Characters",
         "description": "Characters (observable features) used to describe and identify fungi, with definitions, "
                        "scientific names, value types and value options. Each has a permanent code.",
         "license": LICENSE_URL, "isAccessibleForFree": True},
    ]}
    return render(request, "characters/home.html", {
        "n_characters": visible(Character, request.user).count(),
        "n_values": visible(ValueOption, request.user).count(),
        "structured_data": jsonld(data),
    })


def thanks(request):
    return render(request, "characters/thanks.html")


RELEASES_DIR = settings.BASE_DIR / "data" / "releases"
# What each release file is for (from the release README). Anything else is listed under "Other files".
DOWNLOAD_KINDS = [
    (".xlsx", gettext_lazy("Excel workbook"), gettext_lazy("Browse in Excel or Numbers.")),
    ("csv/characters_flat.csv", gettext_lazy("CSV: characters"), gettext_lazy("One row per character.")),
    ("csv/value_options_flat.csv", gettext_lazy("CSV: value options"), gettext_lazy("One row per value option.")),
    ("csv/values_flat.csv", gettext_lazy("CSV: value options"), gettext_lazy("One row per value option (called “values” in this release).")),
    (".json", "JSON", gettext_lazy("For programmers.")),
    ("_postgresql.sql", gettext_lazy("SQL for PostgreSQL 16/17"), gettext_lazy("Creates the tables and loads all data.")),
    (".sql", gettext_lazy("SQL for MySQL 8"), gettext_lazy("Creates the tables and loads all data.")),
    ("_skos.ttl", gettext_lazy("SKOS vocabulary (Turtle)"), gettext_lazy("For vocabulary tools (W3C SKOS).")),
    ("_sdd.xml", gettext_lazy("SDD 1.1 (TDWG XML)"), gettext_lazy("For identification-key tools.")),
    ("README.md", gettext_lazy("Release notes"), gettext_lazy("What is in the release, and how to cite it.")),
    ("CHANGELOG.md", gettext_lazy("Changelog"), gettext_lazy("What changed in each release.")),
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
    structured = None
    if release:
        from .seo import LICENSE_URL, SITE_URL, TERM_SET_ID, jsonld
        formats = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".json": "application/json",
                   ".sql": "application/sql", ".ttl": "text/turtle", ".xml": "application/xml", ".csv": "text/csv",
                   ".md": "text/markdown"}
        structured = jsonld({
            "@context": "https://schema.org", "@type": "Dataset", "@id": f"{SITE_URL}/downloads/#dataset",
            "name": "Fungal Characters",
            "description": ("A free, publicly maintained list of the characters (observable features) used to describe "
                            "and identify fungi: names, scientific names, definitions, value types and value options, "
                            "each with a permanent code (FCC#####, FCV#####). Translations included."),
            "url": f"{SITE_URL}/downloads/", "version": release.version, "datePublished": release.released_at.isoformat(),
            "license": LICENSE_URL, "isAccessibleForFree": True,
            "creator": {"@type": "Organization", "name": "Fungal Characters", "url": f"{SITE_URL}/"},
            "keywords": ["fungi", "mycology", "mushrooms", "morphological characters", "character matrix",
                         "identification", "controlled vocabulary", "biodiversity data"],
            "sameAs": f"https://github.com/mrdbidwill/fungalcharacters/releases/tag/data-v{release.version}",
            "about": {"@id": TERM_SET_ID},
            "distribution": [{"@type": "DataDownload", "name": f["title"] if isinstance(f["title"], str) else str(f["title"]),
                              "contentUrl": f"{SITE_URL}/downloads/{release.version}/{f['name']}",
                              "encodingFormat": next((t for ext, t in formats.items() if f["name"].endswith(ext)), "application/octet-stream")}
                             for f in main],
        })
    return render(request, "characters/downloads.html", {"release": release, "main": main, "other": other,
                                                         "structured_data": structured})


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
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    ids = [c.pk for c in page]
    sci = labels_for(CHARACTER_TYPE, ids, "scientific_name")
    by = creators(Character, ids)
    lang = data_language()
    translated = labels_for(CHARACTER_TYPE, ids, "name", lang) if lang != "en" else {}
    for c in page:
        c.scientific = sci.get(c.pk, "")
        c.created_by_name = by.get(c.pk)
        c.display_name = translated.get(c.pk) or c.name
        c.name_lang = "en" if lang != "en" and c.pk not in translated else ""
    return render(request, "characters/list.html", {
        "noindex": bool(q or part or fungus),
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
    lang = data_language()
    translated_name = translated_definition = ""
    if lang != "en":
        translated_name = labels_for(CHARACTER_TYPE, [c.pk], "name", lang).get(c.pk, "")
        translated_definition = labels_for(CHARACTER_TYPE, [c.pk], "definition", lang).get(c.pk, "")
        v_names = labels_for(VALUE_TYPE, [v.pk for v in values], "name", lang)
        v_defs = labels_for(VALUE_TYPE, [v.pk for v in values], "definition", lang)
        for v in values:
            v.translated = v_names.get(v.pk, "")
            v.translated_definition = v_defs.get(v.pk, "")
    if scientific_mode(request) and sci:
        heading, heading_lang = sci, ""
    else:
        heading = translated_name or c.name
        heading_lang = "en" if lang != "en" and not translated_name else ""
    langs_with_name = (Label.objects.filter(labelable_type=CHARACTER_TYPE, labelable_id=c.pk, label_type="name")
                       .exclude(language="en").values_list("language", flat=True))
    from .seo import LICENSE_URL, TERM_SET_ID, absolute, describe, jsonld
    part_name = str(c.part) if c.part_id else ""
    value_type = str(c.display_option) if c.display_option_id else ""
    meta_description = describe(
        f"{c.name}" + (f" ({sci})" if sci and sci != c.name else "") + ":",
        c.description or _("A character used to describe fungi."),
        (_("Part: %(part)s.") % {"part": part_name}) if part_name else "",
        (_("Value type: %(type)s.") % {"type": value_type}) if value_type else "")
    term = {"@context": "https://schema.org", "@type": "DefinedTerm", "@id": absolute(c.get_absolute_url()),
            "url": absolute(c.get_absolute_url()), "name": c.name, "termCode": c.code,
            "inDefinedTermSet": TERM_SET_ID, "license": LICENSE_URL}
    if sci and sci != c.name:
        term["alternateName"] = sci
    if c.description:
        term["description"] = c.description
    related_qs = (visible(Character, request.user).filter(part_id=c.part_id).exclude(pk=c.pk).order_by("name", "id")
                  if c.part_id else Character.objects.none())
    return render(request, "characters/detail.html", {
        "meta_description": meta_description, "structured_data": jsonld(term),
        "page_title": f"{c.name}" + (f" ({sci})" if sci and sci != c.name else "") + f" — {c.code}",
        "related": related_qs[:12], "related_total": related_qs.count(),
        "c": c, "scientific": sci, "values": values,
        "heading": heading, "heading_lang": heading_lang, "not_english": lang != "en",
        "translated_name": translated_name, "translated_definition": translated_definition,
        "current_language_name": language_name(lang),
        "translations": [(code, language_name(code)) for code in sorted(set(langs_with_name))],
        "applies_to": c.applies_to.order_by("name"),
        "core_sequences": c.core_sequences.select_related("fungus_type"),
        "created_by_name": creators(Character, [c.pk]).get(c.pk),
        "hidden": is_hidden(c), "scientific_mode": scientific_mode(request),
    })


@contributor_required
def character_create(request):
    form = CharacterForm(posted(request), user=request.user)
    return _save(request, form, _("Add a character"), reverse("characters:list"))


@contributor_required
def edit_by_code(request, code):
    model, obj = find_code(code)
    if obj is None:
        raise Http404
    if model is Character:
        return _edit(request, obj, CharacterForm, "character")
    return _edit(request, obj, ValueOptionForm, "value option")


@contributor_required
def delete_by_code(request, code):
    model, obj = find_code(code)
    if obj is None:
        raise Http404
    if model is Character:
        return _delete(request, obj, "character", lambda o: reverse("characters:list"))
    return _delete(request, obj, "value option", lambda o: o.character.get_absolute_url())


@contributor_required
def value_create(request, code):
    character = get_object_or_404(visible(Character, request.user), code=code)
    form = ValueOptionForm(posted(request), instance=ValueOption(character=character), user=request.user)
    return _save(request, form, _("Add a value option to “%(name)s”") % {"name": character}, character.get_absolute_url())


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


@contributor_required
def value_type_create(request):
    form = DisplayOptionForm(posted(request), user=request.user)
    return _save(request, form, _("Add a value type"), reverse("characters:value_type_list"))


@contributor_required
def value_type_edit(request, pk):
    return _edit(request, get_object_or_404(DisplayOption, pk=pk), DisplayOptionForm, "value type")


@contributor_required
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


@contributor_required
def source_create(request):
    form = SourceForm(posted(request), user=request.user)
    return _save(request, form, _("Add a source"), reverse("characters:source_list"))


@contributor_required
def source_edit(request, pk):
    return _edit(request, get_object_or_404(Source, pk=pk), SourceForm, "source")


@contributor_required
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
    meta, _created = ItemMeta.objects.get_or_create(item_type=item_type_of(obj), item_id=obj.pk)
    meta.is_hidden = not meta.is_hidden
    meta.save()
    messages.success(request, (_("Hidden: %(name)s.") if meta.is_hidden else _("Shown again: %(name)s.")) % {"name": obj})
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
            sign = _("added") if rec.history_type == "+" else _("removed") if rec.history_type == "-" else _("changed")
            rows.append({"rec": rec, "changes": [(_("Applies to"), "", f"{ft} {sign}")]})
        for rec in CoreSequence.history.filter(character_id=pk).select_related("history_user"):
            if rec.history_change_reason == "As released":
                continue
            ft = FungusType.objects.filter(pk=rec.fungus_type_id).first()
            sign = _("added") if rec.history_type == "+" else _("removed") if rec.history_type == "-" else _("changed")
            rows.append({"rec": rec, "changes": [(_("Core order"), "", f"{ft} #{rec.sequence} {sign}")]})
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
    back = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = "/"
    response = redirect(back)
    response.set_cookie(NAMES_COOKIE, mode, max_age=365 * 24 * 3600, samesite="Lax",
                        secure=not settings.DEBUG, httponly=True)
    return response


@login_required
def account(request):
    """The signed-in user's account page: settings links and everything they added."""
    from allauth.account.models import EmailAddress
    from allauth.mfa.utils import is_mfa_enabled

    mine = ItemMeta.objects.filter(created_by=request.user)
    ids = lambda t: mine.filter(item_type=t).values("item_id")
    return render(request, "characters/account.html", {
        "emails": EmailAddress.objects.filter(user=request.user).order_by("-primary", "email"),
        "mfa_enabled": is_mfa_enabled(request.user),
        "my_characters": Character.objects.filter(pk__in=ids(CHARACTER_TYPE)).order_by("name"),
        "my_values": ValueOption.objects.filter(pk__in=ids(VALUE_TYPE)).select_related("character").order_by("character__name", "name"),
        "my_value_types": DisplayOption.objects.filter(pk__in=ids("DisplayOption")).order_by("name"),
        "my_sources": Source.objects.filter(pk__in=ids("SourceData")).order_by("title"),
        "my_changes": sum(model.history.filter(history_user=request.user).count() for model in KINDS.values()),
        "my_translations": mine.filter(item_type="Label").count(),
        "open_reviews": __import__("characters.models", fromlist=["ReviewRequest"]).ReviewRequest.objects.filter(resolved=False).count()
                        if request.user.is_superuser else None,
    })


# ---------- languages and translation ----------

LOCALE_DIRS = {"pt-br": "pt_BR"}


def website_words_progress(code):
    """(translated, total) messages in the website's translation file for this language."""
    import polib
    path = settings.BASE_DIR / "locale" / LOCALE_DIRS.get(code, code) / "LC_MESSAGES" / "django.po"
    if not path.exists():
        return 0, 0
    po = polib.pofile(str(path))
    entries = [e for e in po if not e.obsolete]
    return len([e for e in entries if e.translated()]), len(entries)


def languages(request):
    """Choose the site's language, and the starting point for translators."""
    total = visible(Character, request.user).count()
    rows = []
    for code, name in settings.LANGUAGES:
        if code == "en":
            continue
        done, words = website_words_progress(code)
        n_chars = (Label.objects.filter(labelable_type=CHARACTER_TYPE, label_type="name", language=code)
                   .values("labelable_id").distinct().count())
        rows.append({
            "code": code, "name": name, "published": code in settings.PUBLISHED_LANGUAGES,
            "words_done": done, "words_total": words, "words_pct": round(100 * done / words) if words else 0,
            "chars_done": n_chars, "chars_pct": round(100 * n_chars / total) if total else 0,
        })
    return render(request, "characters/languages.html", {
        "published": [(c, n) for c, n in settings.LANGUAGES if c in settings.PUBLISHED_LANGUAGES],
        "rows": rows, "total_characters": total, "platform_url": settings.TRANSLATION_PLATFORM_URL,
        "current": get_language(),
    })


def _label_owner_ids(item_type, ids, lang):
    """{(item_id, label_type): (label, owner id or None)} for one language."""
    labels = Label.objects.filter(labelable_type=item_type, labelable_id__in=list(ids), language=lang)
    owners = dict(ItemMeta.objects.filter(item_type="Label", item_id__in=[l.pk for l in labels])
                  .values_list("item_id", "created_by_id"))
    return {(l.labelable_id, l.label_type): (l, owners.get(l.pk)) for l in labels}


@contributor_required
def translate(request, code):
    """Translate one character (name, definition and its value options) into one language."""
    from .forms import set_label
    character = get_object_or_404(visible(Character, request.user), code=code)
    lang = request.GET.get("lang") or request.POST.get("lang") or data_language()
    if lang not in TRANSLATION_LANGUAGES:
        lang = TRANSLATION_LANGUAGES[0]
    values = list(visible(ValueOption, request.user).filter(character=character))
    existing = _label_owner_ids(CHARACTER_TYPE, [character.pk], lang)
    existing.update({("v", k[0], k[1]): v for k, v in _label_owner_ids(VALUE_TYPE, [v.pk for v in values], lang).items()})

    def field(key, item_type, item_id, label_type, english, multiline=False):
        label, owner = existing.get(key, (None, None))
        editable = label is None or is_admin(request.user) or owner == request.user.id
        return {"name": f"{item_type}-{item_id}-{label_type}", "item_type": item_type, "item_id": item_id,
                "label_type": label_type, "english": english or "", "value": label.text if label else "",
                "editable": editable, "multiline": multiline}

    fields = [field((character.pk, "name"), CHARACTER_TYPE, character.pk, "name", character.name),
              field((character.pk, "definition"), CHARACTER_TYPE, character.pk, "definition", character.description, True)]
    value_fields = []
    for v in values:
        value_fields.append((v, field(("v", v.pk, "name"), VALUE_TYPE, v.pk, "name", v.name),
                             field(("v", v.pk, "definition"), VALUE_TYPE, v.pk, "definition", v.description, True)))

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip() or f"Translation ({lang})"
        changed = 0
        with transaction.atomic():
            for f in fields + [f for _v, n, d in value_fields for f in (n, d)]:
                if not f["editable"]:
                    continue
                new = request.POST.get(f["name"], "").strip()
                if new == f["value"]:
                    continue
                label, created = set_label(f["item_type"], f["item_id"], f["label_type"], new, reason, language=lang)
                if created:
                    ItemMeta.objects.create(item_type="Label", item_id=label.pk, created_by=request.user)
                changed += 1
        messages.success(request, _("Saved %(n)d translation(s).") % {"n": changed} if changed else _("Nothing changed."))
        if request.POST.get("then") == "next":
            return redirect(reverse("characters:translate_next", args=[lang]))
        return redirect(reverse("characters:translate", args=[character.code]) + f"?lang={lang}")

    return render(request, "characters/translate.html", {
        "c": character, "lang": lang, "lang_name": language_name(lang),
        "languages": [(c, language_name(c)) for c in TRANSLATION_LANGUAGES],
        "fields": fields, "value_fields": value_fields,
    })


@contributor_required
def translate_next(request, lang):
    """Go to the next character that has no name yet in this language."""
    if lang not in TRANSLATION_LANGUAGES:
        raise Http404
    done = Label.objects.filter(labelable_type=CHARACTER_TYPE, label_type="name", language=lang).values("labelable_id")
    nxt = visible(Character, request.user).exclude(pk__in=done).order_by("name", "id").first()
    if nxt is None:
        messages.success(request, _("Every character has a name in this language. Thank you!"))
        return redirect("characters:languages")
    return redirect(reverse("characters:translate", args=[nxt.code]) + f"?lang={lang}")


# ---------- contributions and privacy ----------

def privacy(request):
    return render(request, "characters/privacy.html", {"current_version": Consent.CURRENT_VERSION})


@login_required
def agree(request):
    """Existing users agree to the contribution terms once before adding anything."""
    from .forms import AgreeForm
    next_url = request.GET.get("next") or request.POST.get("next") or reverse("characters:account")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse("characters:account")
    form = AgreeForm(posted(request))
    if request.method == "POST" and form.is_valid():
        Consent.record(request.user)
        return redirect(next_url)
    return render(request, "characters/agree.html", {"form": form, "next": next_url})


def _anonymize(user):
    """Delete a person's personal data but keep their contributions (CC0, in the public history)."""
    from allauth.account.models import EmailAddress
    from allauth.mfa.models import Authenticator
    from allauth.usersessions.models import UserSession
    from django.contrib.sessions.models import Session
    for us in UserSession.objects.filter(user=user):
        Session.objects.filter(session_key=us.session_key).delete()
        us.delete()
    EmailAddress.objects.filter(user=user).delete()
    Authenticator.objects.filter(user=user).delete()
    user.username = f"former-contributor-{user.pk}"
    user.email = ""
    user.first_name = user.last_name = ""
    user.set_unusable_password()
    user.is_active = False
    user.save()


@login_required
def delete_account(request):
    from allauth.account.decorators import reauthentication_required

    @reauthentication_required
    def inner(request):
        if request.user.is_superuser:
            messages.error(request, _("The admin account cannot be deleted here."))
            return redirect("characters:account")
        if request.method == "POST" and request.POST.get("confirm") == "delete":
            user = request.user
            with transaction.atomic():
                logout(request)
                _anonymize(user)
            messages.success(request, _("Your account has been deleted. Your contributions stay on the site, credited to a former contributor."))
            return redirect("characters:home")
        return render(request, "characters/delete_account.html")
    return inner(request)


# ---------- "Needs review" ----------

REVIEW_KINDS = {"character": Character, "value-type": DisplayOption, "source": Source}
REVIEW_LIMIT_PER_HOUR = 5


def _review_allowed(request):
    """Hidden per-visitor limit: at most REVIEW_LIMIT_PER_HOUR reports an hour. The visitor's address is only used,
    hashed with the site's secret, as a one-hour counter; it is not stored with the report."""
    import hashlib
    from allauth.core.internal.httpkit import get_client_ip
    from django.core.cache import cache
    who = f"user:{request.user.pk}" if request.user.is_authenticated else f"ip:{get_client_ip(request)}"
    key = "review:" + hashlib.sha256((settings.SECRET_KEY + who).encode()).hexdigest()[:32]
    cache.add(key, 0, timeout=3600)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=3600)
        count = 1
    return count <= REVIEW_LIMIT_PER_HOUR


def review_request(request, kind, pk):
    from .models import ReviewRequest
    model = REVIEW_KINDS.get(kind)
    if model is None:
        raise Http404
    obj = get_object_or_404(visible(model, request.user), pk=pk)
    label = f"{obj} ({obj.code})" if isinstance(obj, Character) else f"{obj} ({model._meta.verbose_name} {obj.pk})"
    if request.method == "POST":
        note = request.POST.get("note", "").strip()[:1000]
        if _review_allowed(request):
            ReviewRequest.objects.create(
                item_type=item_type_of(obj), item_id=obj.pk, item_label=str(label)[:300], page=item_url(obj)[:300],
                note=note, reporter=request.user if request.user.is_authenticated else None)
        # Same answer whether or not the hidden limit was reached.
        messages.success(request, _("Thank you. Your report has been added to the list for review."))
        return redirect(item_url(obj))
    return render(request, "characters/review_request.html", {"obj": obj, "label": label, "cancel_url": item_url(obj)})


def api_docs(request):
    from .api import API_LIMIT_PER_MINUTE, PAGE_SIZE
    return render(request, "characters/api_docs.html", {"limit": API_LIMIT_PER_MINUTE, "page_size": PAGE_SIZE})


ROBOTS_TXT = """# fungalcharacters.org — everything people read is open to crawlers.
# Please skip sign-in and account pages, edit forms and switches, report forms and the raw API
# (programs: see https://fungalcharacters.org/api/ ; complete copies: https://fungalcharacters.org/downloads/).
User-agent: *
Disallow: /accounts/
Disallow: /account/
Disallow: /admin/
Disallow: /i18n/
Disallow: /names/
Disallow: /review/
Disallow: /hide/
Disallow: /api/v1/
Disallow: /characters/new/
Disallow: /value-types/new/
Disallow: /sources/new/
Disallow: /languages/*/next/
Disallow: /*/edit/
Disallow: /*/delete/
Disallow: /*/translate/
Disallow: /*/values/new/

Sitemap: https://fungalcharacters.org/sitemap.xml
"""


def robots_txt(request):
    from django.http import HttpResponse
    return HttpResponse(ROBOTS_TXT, content_type="text/plain; charset=utf-8")


# ---------- accessibility help and reports ----------

ASSISTIVE_TECH = [
    ("", gettext_lazy("Not saying")),
    ("screen reader", gettext_lazy("Screen reader")),
    ("zoom or magnifier", gettext_lazy("Zoom or magnifier")),
    ("keyboard only", gettext_lazy("Keyboard only")),
    ("voice control", gettext_lazy("Voice control")),
    ("high contrast or colours", gettext_lazy("High contrast or my own colours")),
    ("other", gettext_lazy("Something else")),
]


def accessibility(request):
    """Accessibility statement, help for using the site, and a form to report a problem or ask for help.
    No account needed; reports go to the admin's "Needs review" list as item type "Accessibility"."""
    from .models import ReviewRequest
    page = request.POST.get("page") or request.GET.get("from") or ""
    if not url_has_allowed_host_and_scheme(page, allowed_hosts={request.get_host()}) or not page.startswith("/"):
        page = ""
    if request.method == "POST":
        note = request.POST.get("note", "").strip()[:1000]
        kind = "help" if request.POST.get("kind") == "help" else "problem"
        tech = request.POST.get("tech", "")
        tech = tech if tech in {k for k, _v in ASSISTIVE_TECH} else ""
        if note and _review_allowed(request):
            ReviewRequest.objects.create(
                item_type="Accessibility", item_id=0,
                item_label=f"Accessibility {kind}" + (f" ({tech})" if tech else ""),
                page=(page or "/")[:300], note=note,
                reporter=request.user if request.user.is_authenticated else None)
        if note:
            messages.success(request, _("Thank you. Your message has been added to the list the site's administrator works through."))
            return redirect(reverse("characters:accessibility") + "#report")
        messages.error(request, _("Please write a few words about the problem or what you need."))
    return render(request, "characters/accessibility.html", {"page": page, "tech_choices": ASSISTIVE_TECH})
