"""The shared disclaimer rule (Claude_AI/shared_reference/disclaimer/, Will 2026-11-24):
"No advice about consumption." at the top and bottom of every page (base template), and beside any item whose
subject is eating, using or handling fungi — a book title, a rule, a value about chemistry or toxicity.

This module decides which items get the note beside them."""
import re

from .models import Character, Source

# Characters observed by chemical tests are "values about chemistry".
CHEMISTRY_METHODS = {"Chemosystematics and Laboratory Chemical Tests", "Field Chemical Test", "Micro Chemical Test"}
CHEMISTRY_PARTS = {"Chemosystematics"}
TOPIC_WORDS = re.compile(r"toxi|poison|edib|psilocyb|psilocin|amanitin|muscimol|ibotenic|hallucin|medicin|consum", re.I)
# Sources are judged by title only (comments mention topics in passing).
SOURCE_TITLE_WORDS = re.compile(r"edib|forag|healing|medicin|pharmac|psilocyb|culinar|cook", re.I)


def needs_consumption_note(obj):
    if isinstance(obj, Character):
        if obj.observation_method_id and obj.observation_method.name in CHEMISTRY_METHODS:
            return True
        if obj.part_id and obj.part.name in CHEMISTRY_PARTS:
            return True
        return bool(TOPIC_WORDS.search(f"{obj.name or ''} {obj.description or ''}"))
    if isinstance(obj, Source):
        return bool(SOURCE_TITLE_WORDS.search(obj.title or ""))
    return False
