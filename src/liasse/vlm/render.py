"""Turning one page of a PDF into the image a model would be sent.

Rendered at the resolution the cost report says is the ceiling. Above roughly 193 dpi an
A4 page either gets downscaled by the provider or hits the per-image token limit, so a
higher render is paid for in time and bought nothing - see wiki E9. Below it, detail is
lost for a saving that the same report prices at a fraction of a cent.
"""

from __future__ import annotations

from dataclasses import dataclass

from liasse.corpus.models import Document
from liasse.cost.vlm import DEFAULT_RENDER_DPI

MEDIA_TYPE = "image/png"


@dataclass(frozen=True, slots=True)
class PageImage:
    doc_id: str
    page: int
    dpi: int
    png: bytes

    @property
    def kilobytes(self) -> float:
        return len(self.png) / 1024


def render(document: Document, page: int, dpi: int = DEFAULT_RENDER_DPI) -> PageImage:
    """One 1-indexed page as PNG bytes. Nothing is written to disk."""
    import pymupdf

    with pymupdf.open(document.pdf_path) as pdf:
        if not 1 <= page <= pdf.page_count:
            raise ValueError(f"page {page} out of range for {document.doc_id}")
        pixmap = pdf[page - 1].get_pixmap(dpi=dpi)
        return PageImage(document.doc_id, page, dpi, pixmap.tobytes("png"))
