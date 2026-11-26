"""Open read-only API (docs/DECISIONS.md: "open read-only API"). JSON, no sign-in, CC0 data.

    GET /api/v1/characters/?q=&part=&fungus_type=&updated_since=YYYY-MM-DD&page=
    GET /api/v1/characters/<FCC code>
    GET /api/v1/value-options/<FCV code>
    GET /api/v1/releases/

Hidden items never appear. Fair-use limit per visitor (API_LIMIT_PER_MINUTE); over it: 429 with Retry-After.
"""
import datetime
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from .models import (
    CHARACTER_TYPE, VALUE_TYPE, Character, CharacterFungusType, Label, Release, ValueOption,
)

API_LIMIT_PER_MINUTE = 120
PAGE_SIZE = 100
META = {"license": "CC0 1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "cite": "Fungal Characters, https://fungalcharacters.org/", "docs": "https://fungalcharacters.org/api/"}


def _json(data, status=200, **headers):
    resp = JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})
    resp["Access-Control-Allow-Origin"] = "*"          # public data: any website may read it
    resp["Cache-Control"] = "public, max-age=300"
    for k, v in headers.items():
        resp[k.replace("_", "-")] = v
    return resp


def _limited(request):
    from allauth.core.internal.httpkit import get_client_ip
    key = "api:" + hashlib.sha256((settings.SECRET_KEY + str(get_client_ip(request))).encode()).hexdigest()[:32]
    cache.add(key, 0, timeout=60)
    try:
        return cache.incr(key) > API_LIMIT_PER_MINUTE
    except ValueError:
        cache.set(key, 1, timeout=60)
        return False


def api_view(func):
    def wrapper(request, *args, **kwargs):
        if request.method != "GET":
            return _json({"error": "Read-only API: use GET."}, status=405, Allow="GET")
        if _limited(request):
            return _json({"error": f"Fair-use limit: {API_LIMIT_PER_MINUTE} requests a minute. Please slow down, "
                                   "or download a release instead."}, status=429, Retry_After="60")
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def _visible(model):
    from .views import hidden_ids
    qs = model.objects.exclude(pk__in=hidden_ids(model))
    if model is ValueOption:
        qs = qs.exclude(character_id__in=hidden_ids(Character))
    return qs


def _labels(item_type, ids):
    out = {}
    for l in Label.objects.filter(labelable_type=item_type, labelable_id__in=list(ids)).order_by("language", "label_type"):
        out.setdefault(l.labelable_id, []).append({"language": l.language, "type": l.label_type, "text": l.text})
    return out


def _value(v, labels):
    return {"code": v.code, "url": f"https://fungalcharacters.org/id/{v.code}", "name": v.name,
            "definition": v.description or None, "labels": labels.get(v.pk, []),
            "source": v.source.title if v.source_id and v.source else None}


def _character(c, labels, applies, values=None, value_labels=None):
    p = c.props
    d = {"code": c.code, "url": f"https://fungalcharacters.org/id/{c.code}", "name": c.name,
         "scientific_name": p.get("name_scientific"), "definition": c.description or None, "unit": p.get("unit"),
         "part": str(c.part) if c.part_id else None,
         "observation_method": str(c.observation_method) if c.observation_method_id else None,
         "value_type": str(c.display_option) if c.display_option_id else None,
         "applies_to_fungus_types": applies.get(c.pk, []), "source": c.source.title if c.source_id and c.source else None,
         "labels": labels.get(c.pk, []), "updated_at": c.updated_at.isoformat()}
    if values is not None:
        d["value_options"] = [_value(v, value_labels) for v in values]
    return d


def _applies(ids):
    out = {}
    for t in CharacterFungusType.objects.filter(character_id__in=list(ids)).select_related("fungus_type"):
        out.setdefault(t.character_id, []).append(str(t.fungus_type))
    return out


@api_view
def characters(request):
    qs = _visible(Character).select_related("part", "observation_method", "display_option", "source").order_by("code")
    q = request.GET.get("q", "").strip()
    if q:
        in_labels = Label.objects.filter(labelable_type=CHARACTER_TYPE, text__icontains=q).values("labelable_id")
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(code__iexact=q) | Q(pk__in=in_labels))
    if request.GET.get("part"):
        qs = qs.filter(part__name__iexact=request.GET["part"])
    if request.GET.get("fungus_type"):
        qs = qs.filter(fungus_type_tags__fungus_type__name__iexact=request.GET["fungus_type"])
    if request.GET.get("updated_since"):
        try:
            since = datetime.date.fromisoformat(request.GET["updated_since"])
        except ValueError:
            return _json({"error": "updated_since must be a date like 2026-11-26."}, status=400)
        qs = qs.filter(updated_at__date__gte=since)
    paginator = Paginator(qs, PAGE_SIZE)
    try:
        page = paginator.page(int(request.GET.get("page", "1")))
    except Exception:
        return _json({"error": "No such page."}, status=404)
    items = list(page)
    ids = [c.pk for c in items]
    labels, applies = _labels(CHARACTER_TYPE, ids), _applies(ids)
    base = request.build_absolute_uri(request.path)
    params = request.GET.copy()

    def link(n):
        params["page"] = n
        return f"{base}?{params.urlencode()}"
    return _json({**META, "count": paginator.count, "page": page.number, "pages": paginator.num_pages,
                  "next": link(page.next_page_number()) if page.has_next() else None,
                  "previous": link(page.previous_page_number()) if page.has_previous() else None,
                  "results": [_character(c, labels, applies) for c in items]})


@api_view
def character(request, code):
    c = _visible(Character).select_related("part", "observation_method", "display_option", "source").filter(code=code).first()
    if c is None:
        return _json({"error": "No such character (or it is hidden).", "code": code}, status=404)
    values = list(_visible(ValueOption).filter(character=c).select_related("source").order_by("id"))
    return _json({**META, **_character(c, _labels(CHARACTER_TYPE, [c.pk]), _applies([c.pk]), values,
                                       _labels(VALUE_TYPE, [v.pk for v in values]))})


@api_view
def value_option(request, code):
    v = _visible(ValueOption).select_related("character", "source").filter(code=code).first()
    if v is None:
        return _json({"error": "No such value option (or it is hidden).", "code": code}, status=404)
    return _json({**META, **_value(v, _labels(VALUE_TYPE, [v.pk])),
                  "character": {"code": v.character.code, "name": v.character.name,
                                "url": f"https://fungalcharacters.org/id/{v.character.code}"}})


@api_view
def releases(request):
    return _json({**META, "results": [
        {"version": r.version, "released": r.released_at.isoformat(), "notes": r.notes,
         "downloads": request.build_absolute_uri("/downloads/")} for r in Release.objects.order_by("-released_at", "-id")]})
