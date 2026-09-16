"""Read the shipped corpus into the containers in ``models``.

Reads only. Nothing in this module writes anywhere under data/.

Page size comes from the PDF and is cached per document, because opening a PDF is the
one genuinely slow operation here and every page of a document shares the same file.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

from liasse import paths
from liasse.corpus.models import Document, OcrPage, PageGeometry, Token
from liasse.corpus.scope import SCOPE, ScopeEntry


class CorpusError(RuntimeError):
    """The corpus is not laid out the way we expect."""


def _bilans_dir(siren: str) -> Path:
    return paths.DATA_DIR / siren / "bilans"


def load_document(entry: ScopeEntry) -> Document:
    """Join the three representations of one filing: meta, pdf, ocr."""
    base = _bilans_dir(entry.siren)

    meta_matches = sorted(base.glob(f"meta/*{entry.doc_id}.json"))
    if not meta_matches:
        raise CorpusError(f"no meta/ entry for {entry.siren}/{entry.doc_id}")
    meta = json.loads(meta_matches[0].read_text(encoding="utf-8"))

    pdf_matches = sorted(base.glob(f"pdf/*{entry.doc_id}.pdf"))
    if not pdf_matches:
        raise CorpusError(f"no pdf/ for {entry.siren}/{entry.doc_id}")

    return Document(
        siren=entry.siren,
        doc_id=entry.doc_id,
        pdf_path=pdf_matches[0],
        ocr_dir=base / "ocr" / entry.doc_id,
        deposit_date=meta.get("dateDepot", entry.deposit_date),
        # dateCloture is the fiscal_year_end the schema asks for. It ships with the
        # registry entry, so it never has to be parsed out of the PDF. See wiki F006.
        fiscal_year_end=meta.get("dateCloture"),
        denomination=meta.get("denomination"),
        meta=meta,
    )


def iter_scope():
    """Yield the 15 in-scope documents, in the order the brief lists them."""
    for entry in SCOPE:
        yield load_document(entry)


@functools.lru_cache(maxsize=32)
def _page_sizes_pt(pdf_path: Path) -> tuple[tuple[float, float], ...]:
    """(width_pt, height_pt) per page, read once per PDF.

    ``page.rect`` already accounts for the page's rotation, so a landscape page reports
    its width as the wide side. That is what the normalisation has to divide by.
    """
    import pymupdf

    with pymupdf.open(pdf_path) as doc:
        return tuple((page.rect.width, page.rect.height) for page in doc)


def page_geometry(document: Document, page: int, skew_deg: float = 0.0) -> PageGeometry:
    """Physical geometry of one 1-indexed page."""
    sizes = _page_sizes_pt(document.pdf_path)
    if not 1 <= page <= len(sizes):
        raise CorpusError(
            f"page {page} out of range for {document.doc_id}: PDF has {len(sizes)} pages"
        )
    width_pt, height_pt = sizes[page - 1]
    return PageGeometry(page=page, width_pt=width_pt, height_pt=height_pt, skew_deg=skew_deg)


def _ocr_path(document: Document, page: int) -> Path:
    return document.ocr_dir / f"page_{page:03d}.json"


def has_ocr(document: Document, page: int) -> bool:
    return _ocr_path(document, page).is_file()


def load_page(document: Document, page: int) -> OcrPage:
    """Load one page of OCR, paired with the page geometry read from the PDF."""
    path = _ocr_path(document, page)
    if not path.is_file():
        raise CorpusError(f"no OCR for {document.doc_id} page {page}")
    raw = json.loads(path.read_text(encoding="utf-8"))

    tokens = tuple(
        Token(
            text=line.get("text") or "",
            polygon=tuple((float(x), float(y)) for x, y in line["polygon"]),
            score=float(line.get("score", 1.0)),
            orientation_angle=int(line.get("orientation_angle") or 0),
        )
        for line in raw.get("ocr") or []
    )

    # The OCR reports the page number itself; trust the filename when they disagree,
    # but the two have matched everywhere in the corpus so far.
    geometry = page_geometry(document, page, skew_deg=float(raw.get("skew_angle") or 0.0))

    return OcrPage(geometry=geometry, tokens=tokens, layout=tuple(raw.get("layout") or ()))


def iter_pages(document: Document):
    """Yield every page of a document that has OCR, in order."""
    for path in sorted(document.ocr_dir.glob("page_*.json")):
        page = int(path.stem.split("_")[1])
        yield load_page(document, page)
