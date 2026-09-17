"""Converting between the three coordinate systems in play.

    PDF points    1 pt = 1/72 inch     the PDF's own geometry
    OCR pixels    1 px = 1/300 inch    what data/*/ocr/*.json ships
    normalised    fraction of 0 to 1   what results.json must carry

The conversion is four lines and the challenge says so on purpose. The trap is not the
arithmetic, it is assuming a page size: NOTICE.md records that some documents were
re-rendered at 150 dpi, and the corpus mixes portrait and landscape. Page size is always
read from the PDF, per page.

``tools/bbox_viewer.py`` ships a reference implementation of exactly this conversion.
``tests/differential/`` compares us against it rather than against our own expectations.
"""

from __future__ import annotations

from liasse.geometry.boxes import BBox

DPI_OF_OCR = 300
POINTS_PER_INCH = 72
# 4.1666...: one PDF point is this many OCR pixels.
PIXELS_PER_POINT = DPI_OF_OCR / POINTS_PER_INCH


def page_size_px(width_pt: float, height_pt: float) -> tuple[float, float]:
    """Page size in OCR pixels. A4 (595 x 842 pt) becomes 2479 x 3508 px."""
    return width_pt * PIXELS_PER_POINT, height_pt * PIXELS_PER_POINT


def to_normalized(box_px: BBox, width_pt: float, height_pt: float) -> BBox:
    """OCR pixels -> fractions of the page, origin top-left.

    Both coordinate systems already put the origin at the top-left, so there is no axis
    flip here. Values read straight from the PDF instead of from the OCR would need one,
    because PDF space is bottom-left; pymupdf hides that, which is where such a bug would
    enter unnoticed.
    """
    w_px, h_px = page_size_px(width_pt, height_pt)
    if w_px <= 0 or h_px <= 0:
        raise ValueError(f"degenerate page size: {width_pt} x {height_pt} pt")
    return BBox(box_px.x0 / w_px, box_px.y0 / h_px, box_px.x1 / w_px, box_px.y1 / h_px)


def to_pixels(box_norm: BBox, width_pt: float, height_pt: float) -> BBox:
    """The inverse. Used to draw our own boxes back onto a page when checking by eye."""
    w_px, h_px = page_size_px(width_pt, height_pt)
    return BBox(box_norm.x0 * w_px, box_norm.y0 * h_px, box_norm.x1 * w_px, box_norm.y1 * h_px)
