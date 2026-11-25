"""Pages kept on fungalcharacters.org for somebody else, exactly as they sent them.

Brian Hunt's Lumen Granuli Praecisi (v1.0) was served at mrdbid.com/documents/lumen-granuli-praecisi/ (since
2026-09-27), and gulfcoastfungi.com links to that address. Will, 2026-11-11: keep it working. When mrdbid.com
forwards to fungalcharacters.org (Will, 2026-11-25), mrdbid.com/documents/… forwards to the same path here, so the
page is served at the same path on this site. Files copied byte for byte from the MRDBID app's hosted/ folder on
2026-11-25 (including Will's 2026-09-28 "build on video" box). A small bar linking back to the site and the shared
disclaimer are added at the top and bottom as the page is served; the author's file is not edited.
"""
import mimetypes
import re

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.utils.html import escape
from django.utils.translation import gettext as _

HOSTED_DIR = settings.BASE_DIR / "hosted"
PAGES = {
    "lumen-granuli-praecisi": {
        "title": "Lumen Granuli Praecisi (v1.0)", "author": "Brian Hunt",
        "folder": "lumen_granuli_praecisi_v1_0", "page": "lumen_granuli_praecisi_v1_0.html",
        "note": "An LED-lit PCR tube rack for fungal DNA extractions, with build notes and photographs.",
    },
}
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*\.(jpe?g|png|gif|webp)$", re.IGNORECASE)
BODY_OPEN = re.compile(rb"<body\b[^>]*>", re.IGNORECASE)
BODY_CLOSE = re.compile(rb"</body\s*>", re.IGNORECASE)


def _bar():
    """Site bar and the shared disclaimer (Claude_AI/shared_reference/disclaimer/), in the reader's language."""
    from django.utils.translation import get_language
    bar = (f'<div lang="{escape(get_language() or "en")}" style="font:16px system-ui,sans-serif;background:#1F4D2E;color:#fff;padding:.5rem 1rem">'
           f'<a style="color:#fff" href="/">Fungal Characters</a> &middot; '
           f'<a style="color:#fff" href="/documents/">{escape(_("Documents"))}</a> &middot; '
           f'{escape(_("a page hosted for its author, shown exactly as sent"))}</div>'
           f'<p style="font:16px system-ui,sans-serif;background:#fff4e0;border-left:4px solid #8a4b00;color:#3b2a10;'
           f'padding:.4rem .7rem;margin:0"><strong>{escape(_("No advice about consumption."))}</strong> '
           f'{escape(_("fungalcharacters.org reports how sources describe fungi. It is not a guide to eating, using or handling any fungus, and nothing here says whether any fungus is safe. Values about chemistry or toxicity are reported only as their source states them."))}</p>')
    return bar.encode("utf-8")


def _page(slug):
    page = PAGES.get(slug)
    if page is None:
        raise Http404
    return page


def index(request):
    return render(request, "characters/documents.html", {"pages": [dict(slug=k, **v) for k, v in PAGES.items()]})


def page(request, slug):
    p = _page(slug)
    body = (HOSTED_DIR / p["folder"] / p["page"]).read_bytes()
    bar = _bar()
    m = BODY_OPEN.search(body)
    ends = list(BODY_CLOSE.finditer(body))
    if m and ends and ends[-1].start() > m.end():
        body = body[:m.end()] + bar + body[m.end():ends[-1].start()] + bar + body[ends[-1].start():]
    else:
        body = bar + body + bar
    return HttpResponse(body, content_type="text/html; charset=utf-8")


def image(request, slug, name):
    p = _page(slug)
    if not SAFE_NAME.match(name):
        raise Http404
    path = HOSTED_DIR / p["folder"] / "images_web" / name
    if not path.is_file():
        raise Http404
    resp = FileResponse(path.open("rb"), content_type=mimetypes.guess_type(name)[0] or "application/octet-stream")
    resp["Cache-Control"] = "public, max-age=86400"
    return resp
