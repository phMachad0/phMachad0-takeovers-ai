"""Data containers for what the corpus ships.

Layer 0 holds no computation on purpose: these types describe the bytes on disk and
nothing else. Anything derived - bounding boxes, normalised coordinates, deskewed
positions - belongs to ``liasse.geometry``, which higher layers call on these values.
Keeping the split sharp is what lets the geometry be tested without touching data/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# A polygon as the OCR ships it: four [x, y] points, in pixels at 300 dpi.
Polygon = tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class Token:
    """One line of text as the OCR detector found it.

    ``polygon`` is kept verbatim rather than reduced to a rectangle. A skewed scan
    produces a quadrilateral that is not axis-aligned, and the reduction loses that;
    whoever needs a rectangle asks geometry for one.
    """

    text: str
    polygon: Polygon
    score: float
    # 0 for horizontal text. A non-zero value means the detector decided this box is
    # rotated, which on a liasse almost always means it swallowed a vertical run of
    # cells rather than reading one - see wiki F013. Kept because it is one of the three
    # signals that separate a real line-code token from a false one.
    orientation_angle: int = 0


@dataclass(frozen=True, slots=True)
class PageGeometry:
    """Physical size of one page, read from the PDF, plus the OCR's skew estimate.

    Size is in PDF points. It is read per page and never assumed: NOTICE.md says some
    documents were re-rendered at 150 dpi, and the corpus mixes portrait and landscape.
    """

    page: int  # 1-indexed, matching the OCR and the deliverable
    width_pt: float
    height_pt: float
    skew_deg: float


@dataclass(frozen=True, slots=True)
class OcrPage:
    """The OCR of a single page: its geometry, its text lines, its table layout."""

    geometry: PageGeometry
    tokens: tuple[Token, ...]
    layout: tuple[dict, ...] = ()

    @property
    def page(self) -> int:
        return self.geometry.page


@dataclass(frozen=True, slots=True)
class Document:
    """One filing: the PDF, the registry's index entry, and the OCR directory."""

    siren: str
    doc_id: str  # the 24-char INPI id, the key that joins pdf, meta and ocr
    pdf_path: Path
    ocr_dir: Path
    deposit_date: str  # dateDepot: the date in the filename, NOT the fiscal year end
    fiscal_year_end: str | None  # dateCloture, straight from meta/ - see wiki F006
    denomination: str | None
    meta: dict = field(default_factory=dict, repr=False)

    @property
    def n_ocr_pages(self) -> int:
        return len(list(self.ocr_dir.glob("page_*.json"))) if self.ocr_dir.is_dir() else 0
