"""Undoing the rotation a scanner introduced, as a working space.

A page fed into the scanner at an angle produces an image rotated by that angle. The OCR
reads the text correctly but its coordinates are rotated with it, and that breaks grouping
tokens into rows: on a 2479 px wide page, one degree displaces the right edge 43 px
vertically against the left, while a row of a liasse is about 35 px tall. The label on the
left and its value on the right end up in different bands.

Rotating the coordinates back is a *working space*, never an output. What gets reported is
always built from the original polygons, because the box a reviewer draws on the PDF has
to land on the crooked page as it actually is.

Pure: no I/O, no knowledge of the corpus.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence

Point = tuple[float, float]


def rotate_point(x: float, y: float, degrees: float, cx: float, cy: float) -> Point:
    """Rotate one point by ``degrees`` about (cx, cy), origin top-left.

    Positive ``degrees`` is the skew the OCR reports; this rotates by its negative, which
    is what puts a crooked page back level.
    """
    radians = math.radians(-degrees)
    cos, sin = math.cos(radians), math.sin(radians)
    dx, dy = x - cx, y - cy
    return cx + dx * cos - dy * sin, cy + dx * sin + dy * cos


def vertical_drift(page_width_px: float, degrees: float) -> float:
    """How far the right edge of a page sits below its left edge, at this angle.

    The number that says whether a skew matters: compare it with the height of a row.
    """
    return abs(page_width_px * math.tan(math.radians(degrees)))


def deskew_polygon(
    polygon: Sequence[Point], degrees: float, cx: float, cy: float
) -> tuple[Point, ...]:
    return tuple(rotate_point(x, y, degrees, cx, cy) for x, y in polygon)


def deskewed_top_left(polygon: Sequence[Point], degrees: float, cx: float, cy: float) -> Point:
    """Left and top edges of a polygon after deskewing.

    The top edge rather than the centre: the OCR sometimes returns a box hundreds of
    pixels tall where it merged a vertical run of cells, and a centre computed from that
    lands several rows away from where the text is (wiki F008).
    """
    rotated = deskew_polygon(polygon, degrees, cx, cy)
    return min(p[0] for p in rotated), min(p[1] for p in rotated)


# --- measuring the skew that is actually in the coordinates ----------------------------

# Two tokens plausibly share a printed row when their tops are close and they are far
# apart horizontally. A whole degree of skew displaces only 35 px over 2000, so a 60 px
# window keeps same-row pairs while excluding neighbouring rows, which sit ~70 px apart.
SAME_ROW_MAX_DY = 60.0
# Below this horizontal separation the slope estimate is dominated by within-cell jitter.
SAME_ROW_MIN_DX = 800.0
# A token this tall is a detector artefact spanning several rows (wiki F008); its top edge
# says nothing about a baseline.
MAX_TOKEN_HEIGHT = 120.0
MIN_PAIRS = 10


def estimate_skew(polygons: Iterable[Sequence[Point]]) -> float | None:
    """Skew present in the coordinates, in degrees, or None if not measurable.

    Takes the median slope over pairs of tokens that plausibly share a printed row. The
    median rather than a fit: a page carries plenty of pairs that are not on the same row,
    and a least-squares line would follow them.

    This exists because the ``skew_angle`` the OCR ships is *not* the residual. Measured
    against it, pages reporting -1.0 degrees carry about -0.17 in their coordinates: the
    OCR deskewed the image before detecting, and the field records what it corrected. See
    wiki F015.
    """
    tops: list[Point] = []
    for polygon in polygons:
        ys = [p[1] for p in polygon]
        if max(ys) - min(ys) > MAX_TOKEN_HEIGHT:
            continue
        tops.append((min(p[0] for p in polygon), min(ys)))

    slopes = [
        (yb - ya) / (xb - xa)
        for i, (xa, ya) in enumerate(tops)
        for xb, yb in tops[i + 1 :]
        if abs(xb - xa) >= SAME_ROW_MIN_DX and abs(yb - ya) <= SAME_ROW_MAX_DY
    ]
    if len(slopes) < MIN_PAIRS:
        return None
    return math.degrees(math.atan(statistics.median(slopes)))
