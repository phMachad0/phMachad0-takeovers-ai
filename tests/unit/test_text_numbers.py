"""Reading amounts out of tokens the OCR split, and refusing when they do not spell one.

Every positive case here is transcribed from the corpus with its coordinates, out of wiki
F003 and F004. The negative cases matter as much: a parser that always answers is
inventing values, and nothing else in the pipeline can tell the difference.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from liasse.corpus.models import Token
from liasse.text.lines import PositionedToken
from liasse.text.numbers import (
    ParsedNumber,
    looks_numeric,
    numeric_ratio,
    parse_amount,
)

DIGIT_WIDTH = 28.0  # close to the 26.7 px measured over the corpus


def piece(text: str, x: float) -> PositionedToken:
    """A token at a given left edge, sized as the corpus sizes digits."""
    digits = max(1, sum(c.isdigit() for c in text))
    width = digits * DIGIT_WIDTH
    return PositionedToken(
        token=Token(
            text=text,
            polygon=((x, 100), (x + width, 100), (x + width, 140), (x, 140)),
            score=0.99,
        ),
        x=x,
        y=100.0,
    )


def parse(*pairs: tuple[str, float]) -> ParsedNumber | None:
    return parse_amount([piece(text, x) for text, x in pairs])


def value_of(*pairs: tuple[str, float]):
    result = parse(*pairs)
    return None if result is None else result.value


# --- wiki F003: the OCR splits numbers on the thousands separator ----------------------


def test_the_revenue_that_arrives_as_three_tokens():
    """`FL = 1 805 459` on page 6 of 65784e5d. A naive parser reads 1."""
    assert value_of(("1", 2125), ("805", 2174), ("459", 2275)) == 1_805_459


def test_two_tokens():
    assert value_of(("27", 2199), ("699", 2275)) == 27_699


def test_a_single_token_that_kept_its_separator():
    """Same page, same column: the OCR is not consistent with itself."""
    assert value_of(("2 524", 1749)) == 2_524


def test_a_three_digit_amount_needs_no_assembly():
    assert value_of(("243", 2274)) == 243


def test_the_tokens_used_are_reported_for_provenance():
    """The bbox of the value is the union of these; assembling and locating are one job."""
    result = parse(("1", 2125), ("805", 2174), ("459", 2275))
    assert result is not None
    assert [t.text for t in result.tokens] == ["1", "805", "459"]


# --- wiki F004: three renderings of a negative, on one page ----------------------------


def test_a_bare_minus_to_the_left():
    assert value_of(("-", 2110), ("45", 2201), ("440)", 2271)) == -45_440


def test_an_opening_bracket_as_a_token_of_its_own():
    assert value_of(("(", 2108), ("52", 2199), ("814)", 2271)) == -52_814


def test_only_the_closing_bracket_survived():
    """`GV`, the net financial result, one of the twelve fields. A parser that strips
    punctuation reads +2096 and reports the wrong sign of a filed figure."""
    assert value_of(("2", 2229), ("096)", 2274)) == -2_096


def test_the_negative_marker_is_reported():
    result = parse(("2", 2229), ("096)", 2274))
    assert result is not None and result.negative_marker == "parenthesis"


def test_a_minus_belonging_to_something_else_is_not_claimed():
    """Only a marker directly to the left, with nothing in between, is ours."""
    assert value_of(("-", 1000), ("Total", 1400), ("459", 2275)) == 459


# --- refusing ---------------------------------------------------------------------------


def test_a_neighbouring_column_is_not_swallowed():
    """`2 524` sits in the export column, `1 805 459` in the total column, 264 px away.

    The scan stops on distance, not on shape, so this is the confident case: what was
    assembled is the whole of the rightmost cell.
    """
    assert value_of(("2 524", 1749), ("1", 2125), ("805", 2174), ("459", 2275)) == 1_805_459


def test_two_fragments_too_close_to_separate_are_refused():
    """Within one number the corpus never exceeds 0.70 digit widths. `12` and `34` at 16 px
    are inside that, and together they spell no amount, so the run is refused rather than
    reported as its rightmost fragment."""
    assert value_of(("12", 2100), ("34", 2172)) is None


def test_tokens_with_no_digits_yield_nothing():
    assert parse(("Total", 1400), ("(I)", 1700)) is None
    assert parse() is None


def test_a_lone_group_that_lost_its_separator_is_still_read():
    """`62614` and `509582` appear in the corpus: the OCR dropped the thousands space and
    the digits are unambiguous."""
    assert value_of(("62614", 2100)) == 62_614
    assert value_of(("509582", 2100)) == 509_582


def test_a_long_group_beside_others_is_refused():
    """Two cells merged into one token, not a lost separator. Escalate, do not guess.

    `1 476747` is printed as 1 476 747; the OCR kept one separator and lost the other.
    Reporting the 476747 fragment would be wrong by a million and undetectable.
    """
    assert value_of(("1", 2100), ("476747", 2160)) is None
    assert value_of(("4990", 2100), ("890", 2220)) is None


# --- decimals and types ------------------------------------------------------------------


def test_a_decimal_amount_uses_the_french_comma():
    assert value_of(("1 802,50", 2100)) == Decimal("1802.50")


def test_a_decimal_split_across_tokens():
    assert value_of(("1", 2100), ("802,50", 2136)) == Decimal("1802.50")


@pytest.mark.parametrize(
    "pairs",
    [
        (("1", 2125), ("805", 2174), ("459", 2275)),
        (("2", 2229), ("096)", 2274)),
        (("1 802,50", 2100),),
    ],
)
def test_money_is_never_a_float(pairs):
    """E7 compares amounts for exact equality; a float would need an arbitrary tolerance
    that hides real misreadings."""
    result = parse(*pairs)
    assert result is not None
    assert not isinstance(result.value, float)
    assert isinstance(result.value, int | Decimal)


def test_round_trip_through_the_tokens():
    """The digits reported must be exactly the digits read."""
    result = parse(("1", 2125), ("805", 2174), ("459", 2275))
    assert result is not None
    assert "".join(c for c in result.text if c.isdigit()) == str(result.value)


# --- the predicate the router uses ------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1 805 459", True),
        ("(52 814)", True),
        ("-45 440", True),
        ("FL", False),
        ("Chiffres d'affaires nets", False),
        ("", False),
        ("- ", False),
    ],
)
def test_looks_numeric(text, expected):
    assert looks_numeric(text) is expected


def test_numeric_ratio_of_an_empty_page_is_zero():
    assert numeric_ratio([]) == 0.0


# --- the gap threshold, and that it sits between two populations ------------------------


def test_the_gap_threshold_sits_between_the_measured_populations():
    """Measured over every row of the 28 liasse pages, in digit widths:

        within one number   median 0.27, worst 0.70
        between columns     median 6.76, tightest 2.80

    The threshold has to separate those. This pins the property rather than the number, so
    retuning stays honest - and it is what caught an earlier value of 4.0, taken from a
    biased sample, which merged 68 genuine column separations.
    """
    from liasse.text.numbers import GAP_IN_DIGIT_WIDTHS

    assert 0.70 < GAP_IN_DIGIT_WIDTHS < 2.80


def test_two_columns_at_the_tightest_measured_separation_are_kept_apart():
    """The tightest column gap in the corpus is 2.8 digit widths - 124 px at this size.
    `1 807 858` and `1 748 987` on a form 2050 total row sit exactly there."""
    assert value_of(("1 807", 1772), ("858", 1917), ("1 748", 2130), ("987", 2281)) == 1_748_987
