"""Reading the average workforce, which is the one field that is not a table.

Eleven of the twelve fields are amounts in a ruled grid. This one is a headcount, and the
brief says so: "not a monetary value at all". On a complete liasse it sits on a form and
carries the code YP, which the code-anchored extractor reads like any other row. But only
two filings in scope print that form, and the rest state the figure in a sentence in the
annexe - which is not extraction from a table at all, and needs its own short path.

The sentences are not the same sentence:

    Effectif moyen du personnel 43 personnes
    Effectif moyen du personnal . 47 personnes.
    Effectif moyen du personnel : 47 personnes dont 9 apprentis et 2 handicapés.
    L'effectif salarié moyen à la clôture de l'exercice s'élève à 33 personnes
        contre 38 personnes à la clôture de l'exercice précédent

The last one is the trap and the reason this is a list of phrasings rather than a search
for a number near the word "effectif". It names two headcounts, the exercise's and the year
before's, in that order and in the same breath. A pattern that reaches for the nearest digit
gets 33 or 38 depending on which side it starts from, and both are real numbers printed on
the page. So each phrasing captures its figure at a fixed position inside a phrase it has to
match in full, and a page that matches no phrasing yields nothing.

Every phrasing here was read off a page in the corpus.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from liasse.corpus.models import OcrPage
from liasse.routing.titles import fold
from liasse.text.lines import Line, PositionedToken, lines_of

from .base import Anchoring, Component, RawValue, Tier

FIELD_KEY = "META_AVG_WORKFORCE_FRGAAP"

# A headcount, not an amount. Nothing in the corpus is near this, and it keeps a stray
# match on a monetary figure from being reported as a number of people.
MAX_PLAUSIBLE_HEADCOUNT = 100_000


@dataclass(frozen=True, slots=True)
class Phrasing:
    """One way a filing states its average headcount in prose."""

    key: str
    pattern: re.Pattern[str]
    note: str


PHRASINGS: tuple[Phrasing, ...] = (
    Phrasing(
        "FT_EFFECTIF_MOYEN_PERSONNEL",
        # "personn\\w*" because one filing has the OCR reading "personnal".
        re.compile(r"effectif moyen du personn\w* (\d{1,6}) personnes?\b"),
        "the annexe's own heading, stated as a count of people",
    ),
    Phrasing(
        "FT_EFFECTIF_SALARIE_MOYEN",
        # The figure is pinned to "s'eleve a" rather than to proximity, because the same
        # sentence goes on to give the previous exercise's headcount the same way.
        re.compile(r"effectif salarie moyen .{0,80}?s eleve a (\d{1,6}) personnes?\b"),
        "a sentence that states this exercise and the one before it, in that order",
    ),
)


@dataclass(frozen=True, slots=True)
class Match:
    phrasing: Phrasing
    headcount: int
    tokens: tuple[PositionedToken, ...]
    snippet: str


def _match_text(text: str) -> tuple[Phrasing, int] | None:
    folded = fold(text)
    for phrasing in PHRASINGS:
        found = phrasing.pattern.search(folded)
        if found:
            headcount = int(found.group(1))
            if 0 <= headcount <= MAX_PLAUSIBLE_HEADCOUNT:
                return phrasing, headcount
    return None


def _search_page(page: OcrPage, lines: Sequence[Line]) -> Match | None:
    """One token first, then a whole row.

    The detector hands the sentence over as a single token on every page in scope, which
    gives the tightest possible box - the sentence itself rather than the row it sits on.
    The row is the fallback for a page where it did not.
    """
    for positioned in (t for line in lines for t in line.tokens):
        found = _match_text(positioned.text)
        if found:
            return Match(found[0], found[1], (positioned,), positioned.text[:120])

    for line in lines:
        text = " ".join(line.texts)
        found = _match_text(text)
        if found:
            return Match(found[0], found[1], line.tokens, text[:120])
    return None


def find(pages: Iterable[OcrPage]) -> RawValue | None:
    """The average workforce stated in prose, or nothing.

    Every page is searched, not only the routed ones: this sentence lives in the annexe,
    among pages the router correctly discards as prose because they carry no table. That
    is the point of routing being a decision about *tables* rather than about relevance.
    """
    for page in pages:
        match = _search_page(page, lines_of(page))
        if match is None:
            continue
        return RawValue(
            field_key=FIELD_KEY,
            value=match.headcount,
            page=page.page,
            unit="count",
            components=(
                Component(
                    code=match.phrasing.key,
                    value=match.headcount,
                    page=page.page,
                    tokens=match.tokens,
                    anchoring=Anchoring(
                        tier=Tier.LABEL,
                        form="ANNEXE",
                        code=match.phrasing.key,
                        matched_label=match.snippet,
                    ),
                ),
            ),
        )
    return None


__all__ = ["find", "PHRASINGS", "FIELD_KEY"]
