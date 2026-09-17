"""Axis-aligned rectangles, and the invariants a submittable box must satisfy.

Pure: this module imports nothing from the rest of the package and touches no files.
Everything here works on plain numbers, so it is testable without the corpus.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import NamedTuple

Point = Sequence[float]


# A box is never a bare 4-tuple in our code: naming it stops x/y transpositions.
class BBox(NamedTuple):
    """[x0, y0, x1, y1] with origin top-left. Units depend on context - see coords."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def as_list(self) -> list[float]:
        """The shape results.json wants."""
        return [self.x0, self.y0, self.x1, self.y1]


def bounds(polygon: Iterable[Point]) -> BBox:
    """Smallest axis-aligned box containing a polygon.

    This is lossy by construction: on a skewed page the quadrilateral is not
    axis-aligned, so the enclosing rectangle is larger than the text and may overlap the
    neighbouring line. That is why line grouping deskews first rather than working on
    these rectangles - see wiki/03-ideias/ideia-03-row-banding-com-skew.md.
    """
    points = list(polygon)
    if not points:
        raise ValueError("cannot take the bounds of an empty polygon")
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return BBox(min(xs), min(ys), max(xs), max(ys))


def union(boxes: Iterable[BBox]) -> BBox:
    """Smallest box containing all of them.

    This is how the bbox of a value is built: the OCR splits `1 805 459` into three
    tokens, and the box we report is the union of the tokens actually used. Reassembling
    the number and locating it are the same operation - see wiki F003.
    """
    items = list(boxes)
    if not items:
        raise ValueError("cannot take the union of no boxes")
    return BBox(
        min(b.x0 for b in items),
        min(b.y0 for b in items),
        max(b.x1 for b in items),
        max(b.y1 for b in items),
    )


# A normalised box wider than this covers the whole page, which in practice means the
# token grouping merged blocks that do not belong together rather than that the value
# really spans the sheet.
SUSPICIOUS_WIDTH = 0.98
SUSPICIOUS_HEIGHT = 0.5


def is_normalized(box: BBox) -> bool:
    """Does this box satisfy what results.schema.json requires?

    The schema declares minimum 0 and maximum 1, so a box of 1.03 makes the whole
    submission fail validation - and an unparseable submission cannot be scored.
    """
    return 0.0 <= box.x0 < box.x1 <= 1.0 and 0.0 <= box.y0 < box.y1 <= 1.0


def looks_suspicious(box: BBox) -> bool:
    """True when a normalised box is so large it is probably a grouping bug."""
    return box.width >= SUSPICIOUS_WIDTH or box.height >= SUSPICIOUS_HEIGHT
