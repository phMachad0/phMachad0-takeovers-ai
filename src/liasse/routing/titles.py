"""Recognising the printed title of a financial statement.

A plaquette has no line codes, so the title is the primary evidence of what a page is.
The OCR corrupts titles, and it corrupts them in the way OCR does: one character inside a
word. Two such corruptions exist in the corpus.

The design avoids two traps:

*Matching the whole string.* A title arrives split across tokens as often as not, and a
whole-string similarity ratio punishes that: the token ``PASSIF`` scores 0.667 against
``bilan passif``, below any threshold that would still reject unrelated text. Matching at
word level does not care how the line was split.

*Encoding the corruptions we happened to see.* Patterns like ``passi.`` and ``resu.?tat``
work on this corpus and on nothing else. What generalises is to declare the vocabulary the
titles are built from and allow each word one edit - a tolerance justified by the
vocabulary's own separation rather than by the sample.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from liasse.corpus.models import Token
from liasse.text.fuzzy import matches_any


@dataclass(frozen=True, slots=True)
class TitleSpec:
    """A statement title as the ordered words it is built from.

    Order and position both matter. Requiring only that the words be *present* is too
    weak: "Notes sur le compte de résultat" heads an annexe schedule and contains every
    word of "Compte de Résultat". A printed title does not contain its words, it *begins*
    with them - which is a structural property, not a threshold to tune.
    """

    statement: str
    # One entry per word, in the order they are printed; each lists accepted spellings.
    required: tuple[frozenset[str], ...]


# Ordered: the more specific title must be tried first, or "Compte de Résultat (Seconde
# Partie)" is claimed by the plain "Compte de Résultat" spec.
TITLE_SPECS: tuple[TitleSpec, ...] = (
    TitleSpec(
        "PL_CONT",
        (
            frozenset({"compte"}),
            frozenset({"resultat"}),
            frozenset({"seconde", "deuxieme"}),
            frozenset({"partie"}),
        ),
    ),
    TitleSpec("BS_ASSETS", (frozenset({"bilan"}), frozenset({"actif"}))),
    TitleSpec("BS_LIABILITIES", (frozenset({"bilan"}), frozenset({"passif"}))),
    TitleSpec("PL", (frozenset({"compte"}), frozenset({"resultat"}))),
)

VOCABULARY: frozenset[str] = frozenset(
    word for spec in TITLE_SPECS for group in spec.required for word in group
)

# How far into the page a title may sit, and how many consecutive tokens it may span.
# Titles arrive as one token ("Bilan Passif"), or split ("Bilan" then "Passif"), so the
# match runs over short runs of neighbouring tokens rather than over single tokens.
TITLE_SEARCH_DEPTH = 12
MAX_TITLE_TOKENS = 4

_NON_WORD = re.compile(r"[^a-z0-9]+")


def fold(text: str) -> str:
    """Lowercase, strip accents, reduce punctuation to spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _NON_WORD.sub(" ", without_accents.lower()).strip()


def words_of(text: str) -> list[str]:
    return fold(text).split()


# French articles and prepositions that may sit between the words of a title without being
# part of it: "Compte *de* Résultat". Words that carry meaning are never in here, so
# "Notes sur le compte de résultat" cannot be skipped into a match.
STOPWORDS: frozenset[str] = frozenset(
    {"de", "du", "des", "d", "la", "le", "les", "l", "et", "en", "au", "aux", "a"}
)


def _satisfies(spec: TitleSpec, words: list[str]) -> bool:
    """Do the words *begin* with this title, in order, ignoring stop words?"""
    index = 0
    for spellings in spec.required:
        while index < len(words) and words[index] in STOPWORDS:
            index += 1
        if index >= len(words) or not matches_any(words[index], spellings):
            return False
        index += 1
    return True


def match_title(tokens: Iterable[Token]) -> str | None:
    """Which statement the page announces in its title, or None.

    Scans short runs of neighbouring tokens near the top of the page, so a title split
    across tokens is found without letting words from unrelated parts of the page pair up.
    """
    head = list(tokens)[:TITLE_SEARCH_DEPTH]
    for size in range(1, MAX_TITLE_TOKENS + 1):
        for start in range(0, max(0, len(head) - size + 1)):
            words = words_of(" ".join(t.text for t in head[start : start + size]))
            if not words:
                continue
            for spec in TITLE_SPECS:
                if _satisfies(spec, words):
                    return spec.statement
    return None
