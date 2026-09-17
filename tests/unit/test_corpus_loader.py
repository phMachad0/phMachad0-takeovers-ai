"""Layer-0 corpus access. Marked ``corpus``: these need data/ on disk."""

from __future__ import annotations

import pytest

from liasse.corpus import loader
from liasse.corpus.scope import SCOPE, SIRENS

pytestmark = pytest.mark.corpus


def test_scope_is_the_fifteen_documents_the_brief_lists():
    assert len(SCOPE) == 15
    assert len(SIRENS) == 5
    assert len({e.doc_id for e in SCOPE}) == 15


def test_every_scope_document_loads():
    for document in loader.iter_scope():
        assert document.pdf_path.is_file()
        assert document.ocr_dir.is_dir()


def test_fiscal_year_end_comes_from_meta_and_differs_from_the_deposit_date():
    """wiki F006: dateCloture ships with the registry entry, so it is never parsed."""
    for document in loader.iter_scope():
        assert document.fiscal_year_end, f"{document.doc_id} has no dateCloture"
        assert len(document.fiscal_year_end) == 10
        assert document.fiscal_year_end < document.deposit_date


def test_page_geometry_is_read_per_page_not_assumed():
    entry = next(e for e in SCOPE if e.doc_id == "65784e5da67d84faf4042736")
    document = loader.load_document(entry)
    geometry = loader.page_geometry(document, 6)
    assert geometry.page == 6
    assert geometry.width_pt > 0 and geometry.height_pt > 0


def test_page_out_of_range_raises_rather_than_returning_nonsense():
    document = loader.load_document(SCOPE[0])
    with pytest.raises(loader.CorpusError):
        loader.page_geometry(document, 9999)


def test_skew_angle_is_carried_through_from_the_ocr():
    """It is the input to deskewing in E3, and easy to drop silently."""
    entry = next(e for e in SCOPE if e.doc_id == "6493e4372f502414800f8164")
    document = loader.load_document(entry)
    angles = {p.geometry.skew_deg for p in loader.iter_pages(document)}
    assert any(abs(a) > 0.5 for a in angles), "expected the known crooked scan to report skew"


def test_tokens_keep_the_polygon_verbatim():
    """Reducing to a rectangle at load time would throw away the skew information."""
    entry = next(e for e in SCOPE if e.doc_id == "65784e5da67d84faf4042736")
    page = loader.load_page(loader.load_document(entry), 6)
    assert page.tokens
    for token in page.tokens[:20]:
        assert len(token.polygon) == 4
        assert all(len(point) == 2 for point in token.polygon)


def test_pages_with_no_ocr_lines_load_as_empty_rather_than_failing():
    """10% of the pages in scope are blank scans - see wiki F012."""
    entry = next(e for e in SCOPE if e.doc_id == "6860f28ca0138eae340c7453")
    page = loader.load_page(loader.load_document(entry), 10)
    assert page.tokens == ()


def test_orientation_angle_is_carried_through():
    """wiki F013: a non-zero angle marks a box the detector read as vertical text.

    The false `BZ` on this page is a whole column of line codes swallowed by one
    detection. Dropping this field at load time would make the extractor unable to
    reject it.
    """
    entry = next(e for e in SCOPE if e.doc_id == "65784e5da67d84faf4042736")
    page = loader.load_page(loader.load_document(entry), 6)

    false_code = next(t for t in page.tokens if t.text.strip() == "BZ")
    assert false_code.orientation_angle == 1
    assert false_code.score < 0.5

    real_code = next(t for t in page.tokens if t.text.strip() == "FL")
    assert real_code.orientation_angle == 0
    assert real_code.score > 0.99
