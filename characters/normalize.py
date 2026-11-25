"""Name normalization used to detect duplicates and near-matches.

Two names that normalize to the same string are treated as the same name:
case, spacing, punctuation and Unicode compatibility forms are ignored.
Letters in any script (e.g. Greek alpha/beta) are kept, so "α-Amanitin" and
"β-Amanitin" stay distinct.
"""
import re
import unicodedata

_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKC", name or "").casefold()
    return _NON_WORD.sub("", text)
