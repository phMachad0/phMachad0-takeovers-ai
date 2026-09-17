"""Rotation arithmetic, and measuring the skew that is actually in the coordinates."""

from __future__ import annotations

import math

import pytest

from liasse.geometry.deskew import (
    deskewed_top_left,
    estimate_skew,
    rotate_point,
    vertical_drift,
)


def test_rotating_about_the_centre_leaves_the_centre_alone():
    assert rotate_point(100, 100, 1.0, 100, 100) == (100, 100)


def test_rotating_by_zero_changes_nothing():
    assert rotate_point(37, 91, 0.0, 100, 100) == (37, 91)


def test_a_point_to_the_right_of_centre_rises_when_a_positive_skew_is_undone():
    """A closed arithmetic check rather than a fixture: at one degree, a point 1000 px to
    the right of centre moves up by 1000*tan(1 deg) = 17.5 px."""
    _, y = rotate_point(1100, 500, 1.0, 100, 500)
    assert y == pytest.approx(500 - 1000 * math.tan(math.radians(1.0)), abs=0.01)


def test_rotation_is_reversible():
    x, y = rotate_point(1900, 740, -0.9, 1235, 1754)
    back = rotate_point(x, y, 0.9, 1235, 1754)
    assert back == pytest.approx((1900, 740), abs=1e-9)


@pytest.mark.parametrize(
    "degrees,expected_px",
    [(0.5, 22), (0.9, 39), (1.0, 43), (4.9, 212)],
)
def test_vertical_drift_across_an_a4_page(degrees, expected_px):
    """The number that says whether a skew matters at all: a liasse row is ~35 px tall."""
    assert vertical_drift(2479, degrees) == pytest.approx(expected_px, abs=1)


def test_deskewed_top_left_uses_the_top_edge_not_the_centre():
    """wiki F008: a degenerate box hundreds of px tall must not report a centre."""
    tall = ((1913, 801), (1991, 801), (1991, 1168), (1913, 1168))
    _, top = deskewed_top_left(tall, 0.0, 1235, 1754)
    assert top == 801


# --- measuring the real skew ------------------------------------------------------------


# x positions far enough apart to produce qualifying pairs (SAME_ROW_MIN_DX = 800).
COLUMNS = [200.0, 1100.0, 1600.0, 2200.0]


def _row(y: float, tilt: float = 0.0, xs: list[float] | None = None) -> list[tuple]:
    """Boxes along one printed row, optionally tilted by a slope."""
    boxes = []
    for x in xs if xs is not None else COLUMNS:
        top = y + x * tilt
        boxes.append(((x, top), (x + 60, top), (x + 60, top + 40), (x, top + 40)))
    return boxes


def _page(tilt: float = 0.0) -> list[tuple]:
    return _row(500, tilt) + _row(600, tilt) + _row(700, tilt)


def test_estimate_skew_reports_zero_on_level_coordinates():
    assert estimate_skew(_page()) == pytest.approx(0.0, abs=0.01)


@pytest.mark.parametrize("degrees", [0.5, 1.0, -1.0, 2.0])
def test_estimate_skew_recovers_a_tilt_that_is_really_there(degrees):
    tilt = math.tan(math.radians(degrees))
    assert estimate_skew(_page(tilt)) == pytest.approx(degrees, abs=0.05)


def test_estimate_skew_declines_when_there_is_not_enough_evidence():
    """Refusing beats guessing: too few same-row pairs and the median means nothing."""
    assert estimate_skew(_row(500, xs=[200.0, 1200.0])) is None
    assert estimate_skew([]) is None


def test_degenerate_boxes_do_not_contribute_a_baseline():
    """A 367 px tall box spans several rows; its top edge is not a baseline (wiki F008)."""
    tall = [((1913, 801), (1991, 801), (1991, 1168), (1913, 1168))]
    assert estimate_skew(_page() + tall) == pytest.approx(estimate_skew(_page()), abs=0.01)
