"""Search-engine helpers (docs/DECISIONS.md, "Search engines"): one address per page, structured data, sitemap.

Honest by design: everything here describes what is already on the page; nothing is shown only to search engines.
"""
import json

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils.safestring import mark_safe

SITE_URL = getattr(settings, "SITE_URL", "https://fungalcharacters.org")
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
TERM_SET_ID = f"{SITE_URL}/#characters"


def absolute(path):
    return SITE_URL + path


def jsonld(data):
    """A <script type="application/ld+json"> block, escaped so data can never close the tag."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return mark_safe(f'<script type="application/ld+json">{text}</script>')


def describe(*parts, limit=158):
    """A plain one-line description for search results, cut at a word boundary."""
    pieces = [" ".join(p.split()) for p in parts if p and p.strip()]
    # Every piece ends with punctuation, so a definition without a full stop does not run into the next piece.
    pieces = [p if p[-1] in ".!?:;…" else p + "." for p in pieces]
    text = " ".join(pieces)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


# ---------- sitemap ----------

class StaticSitemap(Sitemap):
    protocol = "https"
    pages = ["characters:home", "characters:list", "characters:value_type_list", "characters:source_list",
             "characters:downloads", "characters:api_docs", "characters:documents", "characters:thanks",
             "characters:languages", "characters:accessibility", "characters:privacy"]

    def items(self):
        return self.pages

    def location(self, item):
        return reverse(item)

    def get_domain(self, site=None):
        return SITE_URL.split("://", 1)[1]


class _Visible(Sitemap):
    protocol = "https"
    model = None

    def get_domain(self, site=None):
        return SITE_URL.split("://", 1)[1]

    def items(self):
        from .views import hidden_ids
        return self.model.objects.exclude(pk__in=hidden_ids(self.model)).order_by("pk")

    def lastmod(self, obj):
        return obj.updated_at


class CharacterSitemap(_Visible):
    limit = 5000

    def __init__(self):
        from .models import Character
        self.model = Character

    def location(self, obj):
        return obj.get_absolute_url()


class ValueTypeSitemap(_Visible):
    def __init__(self):
        from .models import DisplayOption
        self.model = DisplayOption

    def location(self, obj):
        return reverse("characters:value_type_detail", args=[obj.pk])


class SourceSitemap(_Visible):
    def __init__(self):
        from .models import Source
        self.model = Source

    def location(self, obj):
        return reverse("characters:source_detail", args=[obj.pk])


class DocumentSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return SITE_URL.split("://", 1)[1]

    def items(self):
        from .hosted import PAGES
        return list(PAGES)

    def location(self, slug):
        return reverse("characters:hosted", args=[slug])


SITEMAPS = {"pages": StaticSitemap, "characters": CharacterSitemap, "value-types": ValueTypeSitemap,
            "sources": SourceSitemap, "documents": DocumentSitemap}
