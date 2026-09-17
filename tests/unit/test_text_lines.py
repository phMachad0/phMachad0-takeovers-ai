"""Grouping tokens into rows, checked on rows whose right answer is known.

The cases are pairs a human can read off the rendered page: this label belongs with this
number. That is what the whole stage exists to reconstruct, so it is what is asserted.
"""

from __future__ import annotations

import pytest

from liasse.corpus.loader import iter_pages, load_document
from liasse.corpus.scope import SCOPE
from liasse.text.codes import median_token_height
from liasse.text.lines import (
    effective_skew,
    group_into_lines,
    lines_of,
    position_tokens,
)

pytestmark = pytest.mark.corpus


def _page(doc_id: str, page: int):
    entry = next(e for e in SCOPE if e.doc_id == doc_id)
    return next(p for p in iter_pages(load_document(entry)) if p.page == page)


def _line_with(lines, label: str):
    return next((ln for ln in lines if any(label in t for t in ln.texts)), None)


def _together(page, label: str, value: str, skew: float) -> bool:
    positioned = position_tokens(
        page.tokens,
        width_pt=page.geometry.width_pt,
        height_pt=page.geometry.height_pt,
        skew_deg=skew,
    )
    lines = group_into_lines(positioned, median_token_height(page.tokens))
    line = _line_with(lines, label)
    return line is not None and value in line.texts


# Label/value pairs read off the rendered pages by eye.
KNOWN_ROWS = [
    ("6493e4372f502414800f8164", 7, "Capital social ou individuel", "10 000"),
    ("6493e4372f502414800f8164", 7, "Autres réserves", "146 836"),
    ("6493e4372f502414800f8164", 7, "Total des capitaux propres", "322 009"),
    ("6543d3fd08093cdace058668", 4, "Capital social ou individuel", "10 000"),
    ("67458f18cea78a70070fa226", 2, "Capital social ou individuel", "150 000"),
    ("65784e5da67d84faf4042736", 6, "Salaires et traitements*", "499"),
]


@pytest.mark.parametrize("doc_id,page,label,value", KNOWN_ROWS)
def test_label_and_value_land_on_the_same_row(doc_id, page, label, value):
    assert _together(_page(doc_id, page), label, value, effective_skew(_page(doc_id, page)))


def test_applying_the_reported_skew_would_break_rows_that_currently_work():
    """The exit criterion of this stage, and the reason it is not the obvious one.

    wiki F015: ``skew_angle`` records what the OCR corrected on the image, not what
    remains in the coordinates. Rotating by it over-rotates. If this test ever passes,
    either the OCR changed or the correction stopped being exercised.
    """
    broken = [
        (doc_id, page, label, value)
        for doc_id, page, label, value in KNOWN_ROWS
        if not _together(_page(doc_id, page), label, value, _page(doc_id, page).geometry.skew_deg)
    ]
    assert broken, "the reported skew no longer breaks anything; re-check wiki F015"


def test_the_code_sits_on_the_same_row_as_its_label_and_value():
    """A liasse prints the code a little above the label - 12 to 15 px measured - so the
    band tolerance has to absorb that without reaching the next row 70 px away."""
    lines = lines_of(_page("65784e5da67d84faf4042736", 6))
    row = _line_with(lines, "Salaires et traitements")
    assert row is not None
    assert "FY" in row.texts
    assert "499" in row.texts and "659" in row.texts


def test_the_three_tokens_of_a_split_number_stay_on_one_row():
    """wiki F003: `1 805 459` arrives as three tokens."""
    lines = lines_of(_page("65784e5da67d84faf4042736", 6))
    row = _line_with(lines, "Chiffres d'affaires")
    assert row is not None
    assert ("FL", "1", "805", "459") == tuple(row.texts)[-4:]


def test_tokens_are_ordered_left_to_right_within_a_row():
    for line in lines_of(_page("65784e5da67d84faf4042736", 6)):
        assert list(line.tokens) == sorted(line.tokens, key=lambda t: t.x)


def test_the_reported_bbox_comes_from_original_coordinates():
    """Deskewing is a working space. What is reported has to land on the crooked page."""
    page = _page("6493e4372f502414800f8164", 7)
    row = _line_with(lines_of(page), "Capital social")
    assert row is not None
    for token in row.tokens:
        raw_top = min(p[1] for p in token.token.polygon)
        assert token.bbox.y0 == raw_top


def test_a_degenerate_token_does_not_anchor_a_row():
    """wiki F013: the false `BZ` is 367 px tall and would open a band of its own."""
    lines = lines_of(_page("65784e5da67d84faf4042736", 6))
    assert not any("BZ" in line.texts for line in lines)


def test_bands_do_not_chain_across_the_page():
    """A moving band anchor collapses dense pages into a handful of rows."""
    lines = lines_of(_page("65784e5da67d84faf4042736", 6))
    assert len(lines) >= 30
    assert max(len(line.tokens) for line in lines) <= 20
