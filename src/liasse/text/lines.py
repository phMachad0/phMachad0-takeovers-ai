"""Grouping tokens into the rows of a printed table.

This is where a page stops being a bag of text boxes and becomes something you can read a
value out of: a label on the left, a line code in the middle, a number on the right, all
known to belong to the same row.

Two decisions drive it, and both were measured rather than assumed:

*Deskew first.* See ``liasse.geometry.deskew``.

*Band by the top edge, not the centre.* wiki F008: 3.5% of tokens in scope come back with a
degenerate polygon - one was 367 px tall where the detector merged a column of six cells.
Its centre sits four rows below its text; its top edge sits 11 px from the correct row.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from liasse.corpus.models import OcrPage, Token
from liasse.geometry.boxes import BBox, bounds, union
from liasse.geometry.coords import page_size_px
from liasse.geometry.deskew import deskewed_top_left, estimate_skew
from liasse.text.codes import median_token_height, token_height

# A token this much taller than the page median is a detector artefact: a stamp, a
# watermark, or a merged column. It spans several rows and must not anchor one.
MAX_HEIGHT_RATIO = 3.0

# Two tokens belong to the same row when their top edges are within this share of the
# median token height. Codes are printed slightly higher within their cell than labels
# are - 12 to 15 px measured - so the tolerance has to absorb that without reaching the
# next row, which sits about 70 px away.
BAND_TOLERANCE_RATIO = 0.6
MIN_BAND_TOLERANCE_PX = 12.0


@dataclass(frozen=True, slots=True)
class PositionedToken:
    """A token with its deskewed position. The token itself is untouched."""

    token: Token
    x: float  # left edge in the deskewed working space
    y: float  # top edge in the deskewed working space

    @property
    def text(self) -> str:
        return self.token.text.strip()

    @property
    def bbox(self) -> BBox:
        """The box in ORIGINAL coordinates - the only ones fit to report."""
        return bounds(self.token.polygon)

    @property
    def right(self) -> float:
        """Right edge in the deskewed working space.

        The end that matters for a printed amount: figures in a table column are
        right-aligned, so their left edges scatter with the length of the number while
        their right edges line up. Taken as the left edge plus the token's own width,
        because the deskew is a rotation of under a degree and does not change it.
        """
        x0, _, x1, _ = self.bbox
        return self.x + (x1 - x0)


@dataclass(frozen=True, slots=True)
class Line:
    """One row of a table, left to right."""

    tokens: tuple[PositionedToken, ...]
    top: float  # band anchor, deskewed working space

    @property
    def texts(self) -> tuple[str, ...]:
        return tuple(t.text for t in self.tokens)

    @property
    def bbox(self) -> BBox:
        """Box enclosing the whole row, in original coordinates."""
        return union(t.bbox for t in self.tokens)

    def right_of(self, x: float) -> tuple[PositionedToken, ...]:
        return tuple(t for t in self.tokens if t.x > x)

    def left_of(self, x: float) -> tuple[PositionedToken, ...]:
        return tuple(t for t in self.tokens if t.x < x)


def is_degenerate(token: Token, median_height: float) -> bool:
    return median_height > 0 and token_height(token) > MAX_HEIGHT_RATIO * median_height


def band_tolerance(median_height: float) -> float:
    return max(MIN_BAND_TOLERANCE_PX, BAND_TOLERANCE_RATIO * median_height)


def position_tokens(
    tokens: Sequence[Token], *, width_pt: float, height_pt: float, skew_deg: float
) -> list[PositionedToken]:
    """Place tokens in the deskewed working space, dropping detector artefacts."""
    width_px, height_px = page_size_px(width_pt, height_pt)
    cx, cy = width_px / 2, height_px / 2
    median_height = median_token_height(tokens)

    positioned = []
    for token in tokens:
        if not token.text.strip() or is_degenerate(token, median_height):
            continue
        x, y = deskewed_top_left(token.polygon, skew_deg, cx, cy)
        positioned.append(PositionedToken(token=token, x=x, y=y))
    return positioned


def group_into_lines(
    positioned: Iterable[PositionedToken], median_height: float
) -> tuple[Line, ...]:
    """Cluster tokens into rows by their deskewed top edge.

    The band anchor stays fixed at the first token of the band rather than following the
    running mean. A moving anchor chains: on a dense page there is nearly always another
    token within tolerance of the last one, and whole blocks collapse into one row.
    """
    ordered = sorted(positioned, key=lambda t: (t.y, t.x))
    if not ordered:
        return ()

    tolerance = band_tolerance(median_height)
    lines: list[Line] = []
    current: list[PositionedToken] = [ordered[0]]
    anchor = ordered[0].y

    for token in ordered[1:]:
        if token.y - anchor <= tolerance:
            current.append(token)
        else:
            lines.append(Line(tokens=tuple(sorted(current, key=lambda t: t.x)), top=anchor))
            current, anchor = [token], token.y
    lines.append(Line(tokens=tuple(sorted(current, key=lambda t: t.x)), top=anchor))
    return tuple(lines)


def effective_skew(page: OcrPage) -> float:
    """The angle to actually rotate by.

    Not ``page.geometry.skew_deg``. That field records what the OCR corrected on the
    image, not what remains in the coordinates, and applying it over-rotates by roughly
    six times (wiki F015). What the coordinates actually carry is measurable from the
    coordinates, so it is measured; when it cannot be, the page is left as it is, which is
    the correct default for a corpus whose coordinates are already close to level.
    """
    measured = estimate_skew(t.polygon for t in page.tokens if t.text.strip())
    return measured if measured is not None else 0.0


def lines_of(page: OcrPage) -> tuple[Line, ...]:
    """Rows of one page, deskewed and banded."""
    positioned = position_tokens(
        page.tokens,
        width_pt=page.geometry.width_pt,
        height_pt=page.geometry.height_pt,
        skew_deg=effective_skew(page),
    )
    return group_into_lines(positioned, median_token_height(page.tokens))
