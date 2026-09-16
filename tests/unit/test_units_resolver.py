"""Euros or thousands of euros, and why.

The brief says a pipeline that ignores this is wrong by a factor of 1000 on some filings,
and names a company. The tests here assert the opposite conclusion to the obvious one: the
markers in that company's deposit are found, judged, and rejected - and the reason is
recorded with the value.
"""

from __future__ import annotations

import pytest

from liasse.corpus.loader import iter_pages, iter_scope, load_document
from liasse.corpus.scope import SCOPE
from liasse.extract.base import RawValue
from liasse.extract.liasse import extract
from liasse.routing.classifier import classify_document
from liasse.units.resolver import (
    compare_scales,
    find_capital_anchor,
    find_markers,
    resolve,
)

pytestmark = pytest.mark.corpus


def _typed(doc_id: str):
    entry = next(e for e in SCOPE if e.doc_id == doc_id)
    document = load_document(entry)
    pages = list(iter_pages(document))
    routed = classify_document(document, pages)
    forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
    values = [
        v
        for v in extract([p for p in pages if p.page in forms], forms)
        if isinstance(v, RawValue) and "__" not in v.field_key
    ]
    return {t.field_key: t for t in resolve(values, document, pages)}, pages


BERNACHON = "63e8ebbb54febda17c19ee7e"


def test_the_marker_is_there_and_is_not_applied():
    """wiki F002. Finding it is easy; the work is deciding it does not reach the balance
    sheet, and saying so."""
    typed, pages = _typed(BERNACHON)

    assert find_markers(pages), "the kEUR markers should still be in this deposit"

    capital = typed["BS_CAPITAL_EQUITY_FRGAAP"]
    assert capital.unit == "EUR"
    assert capital.value == 152_500
    assert capital.evidence.rejected_markers
    assert all(
        "K€" in m["snippet"] or "Kilo" in m["snippet"] for m in capital.evidence.rejected_markers
    )


def test_a_naive_whole_document_search_would_be_wrong_by_a_thousand():
    """The error this module exists to avoid, spelled out as a number."""
    typed, _ = _typed(BERNACHON)
    capital = typed["BS_CAPITAL_EQUITY_FRGAAP"]
    assert capital.value == 152_500
    assert capital.value / 1000 == 152.5  # what applying the marker would have produced


def test_the_cover_page_corroborates_the_scale():
    """`au capital de 152 500 euros`, in words, on the legal cover of the same document."""
    typed, _ = _typed(BERNACHON)
    anchor = typed["BS_CAPITAL_EQUITY_FRGAAP"].evidence.anchor
    assert anchor is not None
    assert anchor.amount == 152_500
    assert "euro" in anchor.currency.lower()


@pytest.mark.parametrize(
    "doc_id,expected",
    [
        ("6493e4372f502414800f8164", 10_000),
        ("63e2481c916269756a09542b", 300_000),  # printed 300.000, dots as separators
        ("63e13943526e1f30cd100db5", 1_000_000),  # printed 1.000.000
        ("66cd893cedec9b09d50191e8", 1_000_000),  # printed 1 000 000, spaces
    ],
)
def test_the_capital_anchor_survives_every_separator_style(doc_id, expected):
    entry = next(e for e in SCOPE if e.doc_id == doc_id)
    pages = list(iter_pages(load_document(entry)))
    anchor = find_capital_anchor(pages)
    assert anchor is not None and anchor.amount == expected


def test_a_company_with_variable_capital_states_none():
    """CREAMANDE is a SAS a capital variable and prints no fixed figure. Absence of the
    anchor is a fact about the company, not a failure to find it."""
    entry = next(e for e in SCOPE if e.doc_id == "65784e5da67d84faf4042736")
    pages = list(iter_pages(load_document(entry)))
    assert find_capital_anchor(pages) is None


def test_every_value_leaves_with_its_unit_justified():
    for document in iter_scope():
        pages = list(iter_pages(document))
        routed = classify_document(document, pages)
        forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
        if not forms:
            continue
        values = [
            v
            for v in extract([p for p in pages if p.page in forms], forms)
            if isinstance(v, RawValue)
        ]
        for typed in resolve(values, document, pages):
            assert typed.evidence.rule, f"{typed.field_key} has no unit justification"
            assert typed.unit in ("EUR", "kEUR", "count")


def test_the_workforce_carries_no_currency():
    """financial_fields.json: "Not a monetary value - do not attach a currency to it"."""
    typed, _ = _typed("63e13943526e1f30cd100db5")
    assert typed["META_AVG_WORKFORCE_FRGAAP"].unit == "count"


# --- the scale comparison, as a pure decision ------------------------------------------


@pytest.mark.parametrize(
    "anchor,capital,suspicious",
    [
        (152_500, 152_500, False),  # the ordinary case: exact agreement
        (150_000, 10_000, False),  # 820561470: capital raised after the exercise closed
        (300_000, 300_000, False),
        (152_500, 152, True),  # what applying a kEUR marker to the balance would produce
        (152, 152_500, True),  # and the same mistake in the other direction
        (None, 152_500, False),  # a company with variable capital states no anchor
        (152_500, 0, False),
    ],
)
def test_compare_scales(anchor, capital, suspicious):
    flagged, note = compare_scales(anchor, capital)
    assert flagged is suspicious
    if anchor is not None and capital and anchor != capital:
        assert note


def test_a_same_scale_difference_is_reported_without_changing_the_unit():
    flagged, note = compare_scales(150_000, 10_000)
    assert not flagged
    assert "capital changed between the exercise close and the deposit" in note
