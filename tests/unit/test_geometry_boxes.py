"""Layer-1 geometry: pure, no corpus, fast."""

from __future__ import annotations

import pytest

from liasse.geometry.boxes import BBox, bounds, is_normalized, looks_suspicious, union


def test_bounds_of_an_axis_aligned_quad():
    poly = ((10, 20), (110, 20), (110, 50), (10, 50))
    assert bounds(poly) == BBox(10, 20, 110, 50)


def test_bounds_of_a_skewed_quad_is_the_enclosing_rectangle():
    """A rotated quad yields a box larger than the glyphs: lossy by construction."""
    poly = ((10, 22), (110, 20), (111, 50), (11, 52))
    assert bounds(poly) == BBox(10, 20, 111, 52)


def test_bounds_rejects_an_empty_polygon():
    with pytest.raises(ValueError):
        bounds([])


def test_union_builds_the_box_of_a_split_number():
    """`1 805 459` arrives as three tokens; the reported box is their union (wiki F003)."""
    parts = [BBox(2125, 740, 2160, 775), BBox(2174, 738, 2240, 773), BBox(2275, 738, 2340, 773)]
    assert union(parts) == BBox(2125, 738, 2340, 775)


def test_union_of_one_box_is_that_box():
    box = BBox(1, 2, 3, 4)
    assert union([box]) == box


def test_union_rejects_nothing():
    with pytest.raises(ValueError):
        union([])


@pytest.mark.parametrize(
    "box,expected",
    [
        (BBox(0.1, 0.2, 0.3, 0.4), True),
        (BBox(0.0, 0.0, 1.0, 1.0), True),
        (BBox(-0.01, 0.2, 0.3, 0.4), False),  # below zero: schema rejects the submission
        (BBox(0.1, 0.2, 1.03, 0.4), False),  # above one: same
        (BBox(0.3, 0.2, 0.3, 0.4), False),  # zero width
        (BBox(0.4, 0.2, 0.3, 0.4), False),  # inverted
    ],
)
def test_is_normalized(box, expected):
    assert is_normalized(box) is expected


def test_a_page_wide_box_is_flagged_as_suspicious():
    """Covering the sheet almost always means token grouping merged unrelated blocks."""
    assert looks_suspicious(BBox(0.0, 0.40, 0.99, 0.42))
    assert looks_suspicious(BBox(0.10, 0.05, 0.30, 0.80))
    assert not looks_suspicious(BBox(0.116, 0.610, 0.920, 0.626))  # a real liasse row
