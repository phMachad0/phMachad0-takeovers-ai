"""Deciding whether a filing's figures are euros or thousands of euros.

The brief is blunt about the stakes: "A pipeline that ignores the units question is wrong
by a factor of 1000 on some of these filings", and it points at one company. Searching that
company's deposit for a kEUR marker finds one - and applying it is the error, not the fix.

Every kEUR marker in the corpus belongs to a single annexe table, the list of subsidiaries,
whose own heading says "Tableau realise en Kilo-euros". The balance sheet of the same
deposit is in euros: DA reads 152 500, and the legal cover page of the same document spells
"au capital de 152 500 euros" in words. A grep for the marker over the whole document
divides that balance sheet by a thousand.

So a unit is not a property of a document. It is a property of a block, and a marker has a
scope of governance. Resolving one is a scope question, like resolving a variable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from liasse.corpus.models import Document, OcrPage
from liasse.extract.base import RawValue

# "Les montants sont indiques en K€", "Tableau realise en Kilo-euros", "en milliers d'euros".
_MARKER = re.compile(r"(k\s?€|kilo-?euros?|en\s+milliers\s+d.euros?|k\s?eur\b)", re.I)

# "SAS au capital de 300.000 Euros". A legal mention required on a French company's
# documents, which makes it a second, independent statement of the same order of magnitude
# as the balance sheet - written out, with its currency spelled in words.
_CAPITAL_ANCHOR = re.compile(
    r"capital\s+(?:social\s+)?(?:de\s+)?:?\s*([\d][\d\s., ]{2,}?)\s*(euros?|€|k\s?€)", re.I
)

# Above this ratio between the anchor and the figure read for share capital, the filing is
# stating the same quantity at two different scales, which is what a kEUR statement looks
# like. Well clear of the small differences a capital increase between the exercise close
# and the deposit produces.
SCALE_SUSPICION = 100


@dataclass(frozen=True, slots=True)
class Marker:
    text: str
    page: int


@dataclass(frozen=True, slots=True)
class CapitalAnchor:
    """The capital as stated in words on the document's legal cover."""

    amount: int
    currency: str
    page: int
    snippet: str


@dataclass(frozen=True, slots=True)
class UnitEvidence:
    """Why a value carries the unit it carries. Emitted with the value."""

    rule: str
    anchor: CapitalAnchor | None = None
    # Markers seen and deliberately not applied, with the reason. This field is the
    # difference between not having noticed the trap and having judged it.
    rejected_markers: tuple[dict, ...] = field(default_factory=tuple)
    note: str | None = None


@dataclass(frozen=True, slots=True)
class TypedValue:
    raw: RawValue
    unit: str
    evidence: UnitEvidence

    @property
    def field_key(self) -> str:
        return self.raw.field_key

    @property
    def value(self) -> int | Decimal:
        return self.raw.value


def compare_scales(
    anchor_amount: int | None, capital: int | Decimal | None
) -> tuple[bool, str | None]:
    """Does the capital stated in words agree, in scale, with the one read off the balance?

    Two ways they legitimately differ, and one way they do not:

    - identical: the ordinary case, and the strongest corroboration of the unit;
    - different amount, same order of magnitude: the cover states the capital on the day of
      filing and the balance sheet states it at the exercise close, so a capital increase
      in between separates them. The unit is unaffected;
    - three orders of magnitude apart: the document is stating one quantity at two scales,
      which is what a kEUR filing looks like from outside. Worth a human.
    """
    if anchor_amount is None or capital is None or not capital:
        return False, None
    ratio = anchor_amount / abs(float(capital))
    if ratio > SCALE_SUSPICION or ratio < 1 / SCALE_SUSPICION:
        return True, (
            f"cover states {anchor_amount}, balance sheet reads {capital}: "
            f"a factor of {max(ratio, 1 / ratio):.0f}"
        )
    if anchor_amount != capital:
        return False, (
            f"cover states {anchor_amount}, balance sheet {capital}: same order of "
            "magnitude, capital changed between the exercise close and the deposit"
        )
    return False, None


def _digits(text: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else None


def find_markers(pages: list[OcrPage]) -> list[Marker]:
    out = []
    for page in pages:
        for token in page.tokens:
            if _MARKER.search(token.text):
                out.append(Marker(text=token.text.strip()[:90], page=page.page))
    return out


def find_capital_anchor(pages: list[OcrPage]) -> CapitalAnchor | None:
    """The capital stated in words, if the company states one.

    A company with variable capital does not: CREAMANDE is a "SAS a capital variable" and
    prints no fixed figure, so three of the fifteen deposits have no anchor. That is a fact
    about the company, not a failure to find it.
    """
    for page in pages:
        for token in page.tokens:
            match = _CAPITAL_ANCHOR.search(token.text)
            if not match:
                continue
            amount = _digits(match.group(1))
            if amount:
                return CapitalAnchor(
                    amount=amount,
                    currency=match.group(2).strip(),
                    page=page.page,
                    snippet=token.text.strip()[:90],
                )
    return None


def resolve(values: list[RawValue], document: Document, pages: list[OcrPage]) -> list[TypedValue]:
    """Attach a unit and its justification to every extracted value."""
    markers = find_markers(pages)
    anchor = find_capital_anchor(pages)
    value_pages = {v.page for v in values}

    # A marker governs the block it sits in. Measured over the corpus, no marker ever
    # shares a page with a statement, so scoping it to its own page is already enough to
    # keep it away from the balance sheet - and being that explicit is what lets the
    # rejection be reported rather than merely happen.
    applicable = {m.page for m in markers} & value_pages
    rejected = tuple(
        {
            "snippet": m.text,
            "page": m.page,
            "reason": "outside every page carrying an extracted value",
        }
        for m in markers
        if m.page not in applicable
    )

    note = None
    if anchor is not None:
        capital = next((v for v in values if v.field_key == "BS_CAPITAL_EQUITY_FRGAAP"), None)
        if capital is not None and capital.value:
            ratio = anchor.amount / abs(float(capital.value))
            if ratio > SCALE_SUSPICION:
                note = (
                    f"the cover states {anchor.amount} {anchor.currency} while the balance "
                    f"sheet reads {capital.value}: a factor of {ratio:.0f}"
                )
            elif anchor.amount != capital.value:
                # Ordinary and expected: the cover states the capital on the day of filing,
                # the balance sheet states it at the exercise close, and a capital increase
                # in between makes them differ. Same scale, so the unit still holds.
                note = (
                    f"cover states {anchor.amount}, balance sheet {capital.value}: same "
                    "order of magnitude, capital changed between close and deposit"
                )

    out = []
    for value in values:
        if value.unit == "count":
            out.append(TypedValue(value, "count", UnitEvidence(rule="not_a_monetary_value")))
            continue
        in_scope = value.page in applicable
        out.append(
            TypedValue(
                raw=value,
                unit="kEUR" if in_scope else "EUR",
                evidence=UnitEvidence(
                    rule="marker_on_the_same_block" if in_scope else "form_default_eur",
                    anchor=anchor,
                    rejected_markers=rejected,
                    note=note,
                ),
            )
        )
    return out
