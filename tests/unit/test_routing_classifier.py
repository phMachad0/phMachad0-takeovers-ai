"""The classifier against the corpus, checked on what E1.5 measured by hand.

``scope.py`` carries a ``known_format`` per document, measured before any of this code
existed (wiki F001). That makes it a partial answer key we wrote ourselves, and the point
of these tests is that the router has to agree with it.
"""

from __future__ import annotations

import pytest

from liasse.corpus.loader import iter_pages, iter_scope, load_document
from liasse.corpus.scope import SCOPE
from liasse.routing.classifier import classify_document, classify_page

pytestmark = pytest.mark.corpus


@pytest.fixture(scope="module")
def routed():
    return {d.doc_id: classify_document(d, list(iter_pages(d))) for d in iter_scope()}


def test_router_agrees_with_the_format_measured_by_hand(routed):
    """The one check that matters: does it reproduce F001's 8 liasse / 7 plaquette?"""
    disagreements = [
        (e.doc_id, e.known_format, routed[e.doc_id].format)
        for e in SCOPE
        if routed[e.doc_id].format != e.known_format
    ]
    assert not disagreements, f"router disagrees with scope.py: {disagreements}"


def test_the_split_is_eight_liasse_and_seven_plaquette(routed):
    formats = [r.format for r in routed.values()]
    assert formats.count("liasse") == 8
    assert formats.count("plaquette") == 7


def test_every_document_yields_at_least_one_statement_page(routed):
    for doc_id, r in routed.items():
        assert r.relevant_pages, f"{doc_id[:8]} routed to zero statement pages"


def test_the_two_documents_without_an_income_statement_are_the_confidential_ones(routed):
    """wiki F014: the registry announces it, and the correlation is exact."""
    without_pl = {
        doc_id
        for doc_id, r in routed.items()
        if not any(p.statement in ("PL", "PL_CONT") for p in r.relevant_pages)
    }
    confidential = {doc_id for doc_id, r in routed.items() if r.income_statement_confidential}
    assert without_pl == confidential
    assert len(confidential) == 5


def test_a_liasse_page_is_identified_by_its_form(routed):
    page = next(p for p in routed["65784e5da67d84faf4042736"].pages if p.page == 6)
    assert page.kind == "liasse"
    assert page.form == "2052"
    assert page.statement == "PL"


def test_both_signals_agree_on_a_clean_liasse_page(routed):
    """Header and code fingerprint are independent; on a good page they must concur."""
    page = next(p for p in routed["65784e5da67d84faf4042736"].pages if p.page == 6)
    assert page.signals["header_form"] == "2052"
    assert page.signals["fingerprint_form"] == "2052"
    assert "conflict" not in page.signals


def test_documents_carrying_both_a_liasse_and_a_plaquette_are_detected(routed):
    """Three deposits file the same exercise twice, in both formats.

    That is not redundancy to discard: it is the same numbers rendered independently in
    one document, which is a cross-check between the two extractors that does not need
    the N-1 chain.
    """
    both = {
        doc_id
        for doc_id, r in routed.items()
        if {p.kind for p in r.relevant_pages} >= {"liasse", "plaquette"}
    }
    assert len(both) == 3


def test_blank_pages_are_classified_as_blank_not_prose(routed):
    """wiki F012: 10% of the pages in scope carry no OCR at all."""
    blanks = sum(1 for r in routed.values() for p in r.pages if p.kind == "blank")
    assert blanks >= 41


def test_a_low_confidence_recovery_is_flagged_as_such(routed):
    """445070311/6860f28c lost its titles in the OCR and is recovered from labels only."""
    r = routed["6860f28ca0138eae340c7453"]
    assert r.relevant_pages
    assert all(p.signals.get("low_confidence") for p in r.relevant_pages)
    assert all(p.signals["statement_via"] == "labels" for p in r.relevant_pages)


def test_documents_with_titles_never_fall_back_to_labels(routed):
    """The label fallback misreads annexe schedules, so it must stay a last resort."""
    for doc_id, r in routed.items():
        if doc_id == "6860f28ca0138eae340c7453":
            continue
        assert not any(p.signals.get("statement_via") == "labels" for p in r.pages)


def test_a_page_with_no_tokens_is_blank():
    entry = next(e for e in SCOPE if e.doc_id == "6860f28ca0138eae340c7453")
    page = next(p for p in iter_pages(load_document(entry)) if p.page == 10)
    assert classify_page(page).kind == "blank"


def test_routing_cuts_the_page_count_by_about_seven(routed):
    """The number the README quotes. A floor, not an equality: it may improve."""
    total = sum(len(r.pages) for r in routed.values())
    relevant = sum(len(r.relevant_pages) for r in routed.values())
    assert total == 415
    assert relevant <= 90, "routing stopped being selective"
    assert total / relevant >= 4.0
