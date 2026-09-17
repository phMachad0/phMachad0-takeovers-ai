"""Layer-1 coordinate conversion: pure, no corpus, fast.

The differential test in tests/differential/ checks us against Takeovers' own code on
real pages. These tests pin the arithmetic and the edge cases that the sample may miss.
"""

from __future__ import annotations

import pytest

from liasse.geometry.boxes import BBox
from liasse.geometry.coords import (
    PIXELS_PER_POINT,
    page_size_px,
    to_normalized,
    to_pixels,
)

A4_PT = (595.0, 842.0)


def test_one_point_is_four_and_a_sixth_pixels():
    assert PIXELS_PER_POINT == pytest.approx(300 / 72)


def test_a4_page_size_in_ocr_pixels():
    w, h = page_size_px(*A4_PT)
    assert (round(w), round(h)) == (2479, 3508)


def test_normalizing_the_whole_page_gives_the_unit_square():
    w, h = page_size_px(*A4_PT)
    assert to_normalized(BBox(0, 0, w, h), *A4_PT) == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_round_trip_pixels_to_normalized_and_back():
    box = BBox(283.0, 738.0, 1096.0, 774.0)
    back = to_pixels(to_normalized(box, *A4_PT), *A4_PT)
    assert back == pytest.approx(tuple(box))


def test_landscape_page_uses_its_own_width():
    """Hard-coding A4 portrait is the bug this guards: the corpus mixes orientations."""
    landscape = (842.0, 595.0)
    box = BBox(0, 0, *page_size_px(*landscape))
    assert to_normalized(box, *landscape) == pytest.approx((0.0, 0.0, 1.0, 1.0))
    # The same pixel box read against portrait dimensions would overflow the unit square.
    assert to_normalized(box, *A4_PT).x1 > 1.0


def test_conversion_depends_only_on_page_points_not_on_render_resolution():
    """NOTICE.md: some scans were re-rendered at 150 dpi, page geometry unchanged.

    The OCR is always expressed at 300 dpi whatever the PDF was rendered at, so two
    documents with the same page size must normalise identically. The result is checked
    against a ratio computed independently of the module under test.
    """
    box = BBox(1000.0, 2000.0, 1100.0, 2040.0)
    got = to_normalized(box, *A4_PT)

    expected_x0 = 1000.0 / (595.0 * 300 / 72)
    expected_y0 = 2000.0 / (842.0 * 300 / 72)
    assert got.x0 == pytest.approx(expected_x0)
    assert got.y0 == pytest.approx(expected_y0)
    assert 0 < got.x0 < got.x1 < 1
    assert 0 < got.y0 < got.y1 < 1


def test_degenerate_page_size_is_rejected_rather_than_dividing_by_zero():
    with pytest.raises(ValueError):
        to_normalized(BBox(0, 0, 1, 1), 0.0, 842.0)
