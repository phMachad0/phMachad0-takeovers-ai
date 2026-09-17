"""What every extractor produces, whatever format it read.

A value is never just a number. It carries the tokens it was read from, which is what the
bbox and the snippet in the deliverable are built from, and it carries how it was found,
which is what makes the accuracy figures in the README decomposable instead of a single
unexplained percentage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum

from liasse.geometry.boxes import BBox, union
from liasse.text.lines import PositionedToken


class Tier(IntEnum):
    """How a value was located. Lower is stronger evidence."""

    CODE = 1  # the liasse line code was read straight from the OCR
    LABEL = 2  # the code was missing; the printed label identified the row
    VLM = 4  # a vision model was asked (not built; see the E5 notes)


@dataclass(frozen=True, slots=True)
class Anchoring:
    """How one row was found."""

    tier: Tier
    form: str
    code: str
    matched_label: str | None = None


@dataclass(frozen=True, slots=True)
class Component:
    """One term of a derived field, kept so the arithmetic can be audited."""

    code: str
    value: int | Decimal
    page: int
    tokens: tuple[PositionedToken, ...]
    anchoring: Anchoring
    # The row was found and its cell is blank. On a French form that means zero, not
    # unknown, and the distinction matters: an unread row is a gap in the extraction, a
    # blank one is a fact about the company.
    blank: bool = False

    @property
    def bbox(self) -> BBox:
        return union(t.bbox for t in self.tokens)


@dataclass(frozen=True, slots=True)
class RawValue:
    """A field read off a document, before units and verification."""

    field_key: str
    value: int | Decimal
    page: int
    unit: str
    components: tuple[Component, ...] = field(default_factory=tuple)
    # Terms of a derived field that no anchor resolved. The sum is reported without them
    # and this says which: assuming zero for an unread term would be inventing a figure,
    # and silently dropping it would make the total look complete.
    missing_components: tuple[str, ...] = ()

    @property
    def tokens(self) -> tuple[PositionedToken, ...]:
        return tuple(t for c in self.components for t in c.tokens)

    @property
    def bbox(self) -> BBox:
        """Union of every token that contributed. Provenance is a consequence of never
        throwing away where the number came from, not a field filled in at the end."""
        return union(c.bbox for c in self.components)

    @property
    def snippet(self) -> str:
        return " ".join(t.text for t in self.tokens)

    @property
    def is_complete(self) -> bool:
        return not self.missing_components

    @property
    def tier(self) -> Tier:
        """The weakest link: a sum is only as well grounded as its worst term."""
        return max(c.anchoring.tier for c in self.components)


@dataclass(frozen=True, slots=True)
class MissingValue:
    """A field that could not be read, and why. Absence is reported, never silently 0."""

    field_key: str
    reason: str
