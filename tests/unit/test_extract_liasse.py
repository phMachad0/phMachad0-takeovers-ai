"""Reading the twelve fields off a liasse.

The strongest assertion here is not a golden value, it is V1: total assets read off form
2050 has to equal the total of form 2051, which is a different page read by a different
anchor. Seven of the eight liasse documents can be checked that way and all seven close.
"""

from __future__ import annotations

import pytest

from liasse.corpus.loader import iter_pages, iter_scope, load_document
from liasse.corpus.scope import SCOPE
from liasse.extract.base import MissingValue, RawValue, Tier
from liasse.extract.liasse import extract
from liasse.routing.classifier import classify_document

pytestmark = pytest.mark.corpus


def _read(doc_id: str) -> dict[str, RawValue | MissingValue]:
    entry = next(e for e in SCOPE if e.doc_id == doc_id)
    document = load_document(entry)
    pages = list(iter_pages(document))
    routed = classify_document(document, pages)
    forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
    selected = [p for p in pages if p.page in forms]
    return {r.field_key: r for r in extract(selected, forms)}


@pytest.fixture(scope="module")
def creamande():
    return _read("65784e5da67d84faf4042736")


@pytest.fixture(scope="module")
def everything():
    out = {}
    for document in iter_scope():
        pages = list(iter_pages(document))
        routed = classify_document(document, pages)
        forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
        if forms:
            selected = [p for p in pages if p.page in forms]
            out[document.doc_id] = {r.field_key: r for r in extract(selected, forms)}
    return out


# --- values read straight from the code -------------------------------------------------


def test_revenue_via_its_line_code(creamande):
    value = creamande["PL_REVENUE_FRGAAP"]
    assert value.value == 1_805_459
    assert value.tier is Tier.CODE
    assert value.components[0].code == "FL"


def test_a_negative_whose_bracket_the_ocr_destroyed(creamande):
    """`GV` arrives as `2` and `096)`. Reading it positive flips a filed figure."""
    assert creamande["PL_FINANCIAL_RESULTS_FRGAAP"].value == -2_096


def test_a_derived_field_keeps_its_terms(creamande):
    value = creamande["PL_PERSONNEL_COSTS_FRGAAP"]
    assert value.value == 662_180
    assert {c.code: c.value for c in value.components} == {"FY": 499_659, "FZ": 162_521}


# --- values the label had to rescue -----------------------------------------------------


def test_external_services_is_read_although_its_code_is_missing(creamande):
    """`FW` is one of the codes the OCR loses in a block (wiki F009). The printed label
    carries the row instead, and the tier records that it did."""
    value = creamande["PL_EXT_SERVICES_COSTS_FRGAAP"]
    assert value.value == 329_158
    assert value.tier is Tier.LABEL


def test_revenue_is_rescued_on_the_page_that_lost_the_FL_code(everything):
    """63e88115 page 4 has no FL. The siblings FJ and FK that survived say which cell of
    the row is the total."""
    value = everything["63e881158be6eb9f9d1ff975"]["PL_REVENUE_FRGAAP"]
    assert value.value == 1_800_826
    assert value.tier is Tier.LABEL


# --- column selection --------------------------------------------------------------------


def test_total_assets_is_the_net_column_not_the_gross(everything):
    """Form 2050 reads Brut | Amortissements | Net, and the middle column has its own
    code. Stopping at that code returns 8 754 311 - larger, plausible, and wrong."""
    value = everything["63e8ebbb54febda17c19ee7e"]["BS_TOTAL_ASSETS_FRGAAP"]
    assert value.value == 6_233_746


def test_the_current_exercise_is_read_not_the_previous_one(everything):
    """A filing that prints N and N-1 side by side puts N first."""
    assert everything["63e13943526e1f30cd100db5"]["BS_TOTAL_ASSETS_FRGAAP"].value == 1_807_858


# --- the check that matters ---------------------------------------------------------------


def test_v1_total_assets_equals_the_other_side_of_the_balance_sheet(everything):
    """Two different pages, two different anchors, one number. Seven documents can be
    checked and all seven must close - this is the acceptance test of the whole stage."""
    from liasse.extract.liasse import _cells_for, _find_by_code
    from liasse.fields.catalog import RowAnchor
    from liasse.text.codes import median_token_height
    from liasse.text.lines import lines_of

    total_liabilities = RowAnchor("2051", "EE")
    checked = 0
    for document in iter_scope():
        pages = list(iter_pages(document))
        routed = classify_document(document, pages)
        forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
        if not forms:
            continue
        assets = everything[document.doc_id].get("BS_TOTAL_ASSETS_FRGAAP")
        if isinstance(assets, MissingValue) or assets is None:
            continue
        for page in (p for p in pages if forms.get(p.page) == "2051"):
            lines = lines_of(page)
            median_height = median_token_height(page.tokens)
            found = _find_by_code(lines, total_liabilities, median_height)
            if not found:
                continue
            cells, _ = _cells_for(found[0], total_liabilities, found[1], median_height)
            if cells and cells[0]:
                assert assets.value == cells[0].value, (
                    f"{document.doc_id[:8]}: assets {assets.value} vs equity+liabilities "
                    f"{cells[0].value}"
                )
                checked += 1
    assert checked >= 7, f"only {checked} documents could be cross-checked"


# --- absence is reported, never invented --------------------------------------------------


def test_a_blank_cell_reads_as_zero_and_says_so(creamande):
    """On a French form a blank cell is nil. Keeping that apart from an unread row is what
    stops a real zero looking like a gap, and a gap looking like a zero."""
    cash = creamande["BS_CASH_CURRENT_ASSET_FRGAAP"]
    securities = next(c for c in cash.components if c.code == "CE")
    assert securities.blank
    assert securities.value == 0
    assert cash.is_complete


def test_no_derived_sum_silently_drops_a_term(everything):
    for fields in everything.values():
        for value in fields.values():
            if isinstance(value, RawValue):
                assert value.is_complete, f"{value.field_key} lost {value.missing_components}"


def test_the_confidential_filings_report_no_income_statement(everything):
    """wiki F014: those six fields are legally absent, not missed."""
    for doc_id in ("66cd893cedec9b09d50191e8", "68f0a715f28d8aaf48046416"):
        fields = everything[doc_id]
        assert isinstance(fields["PL_REVENUE_FRGAAP"], MissingValue)
        assert isinstance(fields["BS_TOTAL_ASSETS_FRGAAP"], RawValue)


def test_every_value_carries_the_tokens_it_was_read_from(everything):
    """The bbox and the snippet of the deliverable are built from these."""
    for fields in everything.values():
        for value in fields.values():
            if isinstance(value, RawValue):
                assert value.tokens
                assert value.bbox.x1 > value.bbox.x0
                assert not isinstance(value.value, float)
