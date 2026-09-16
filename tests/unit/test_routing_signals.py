"""Layer-2 routing signals. Pure where possible: tokens are built by hand."""

from __future__ import annotations

import pytest

from liasse.corpus.models import Token
from liasse.routing import signals
from liasse.text.numbers import looks_numeric, numeric_ratio


def tok(
    text: str, *, x: float = 100, y: float = 100, h: float = 40, score: float = 0.99, angle: int = 0
) -> Token:
    return Token(
        text=text,
        polygon=((x, y), (x + 50, y), (x + 50, y + h), (x, y + h)),
        score=score,
        orientation_angle=angle,
    )


# --- signal A: the printed header ------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("DGFiP N° 2052 2023", "2052"),
        ("DGFiP N°2051 2022", "2051"),
        ("DGFiP N° 2058 - C", "2058-C"),
        ("N° 2050-S", "2050-S"),
        ("DGFiP N* 2053 2021", "2053"),  # the OCR mangles the degree sign
        ("Compte de résultat", None),
    ],
)
def test_header_form(text, expected):
    assert signals.header_form([tok(text)]) == expected


def test_header_is_only_looked_for_at_the_top_of_the_page():
    """A form number mentioned in body text must not be read as this page's header."""
    body = [tok("x") for _ in range(signals.HEADER_SEARCH_DEPTH)]
    assert signals.header_form([*body, tok("voir tableau N° 2053")]) is None


# --- signal B: the code fingerprint ----------------------------------------------------


def test_fingerprint_identifies_the_form_from_codes_alone():
    codes = {"FA", "FB", "FE", "FG", "FH", "FJ", "FK", "GV"}
    form, overlap = signals.form_from_codes(codes)
    assert form == "2052"
    assert overlap == 8


def test_fingerprint_refuses_to_guess_from_too_few_codes():
    form, overlap = signals.form_from_codes({"FA", "FB"})
    assert form is None
    assert overlap == 2


def test_signatures_do_not_overlap_between_forms():
    """The signatures are what tells the four forms apart; sharing a code breaks that."""
    seen: dict[str, str] = {}
    for form, codes in signals.FORM_SIGNATURES.items():
        for code in codes:
            assert code not in seen, f"{code} is in both {seen.get(code)} and {form}"
            seen[code] = form


# --- signal C: plaquette titles --------------------------------------------------------
# Title recognition itself is tested in test_routing_titles.py. What belongs here is the
# guard this signal adds on top of it.

NUMBERS = [tok("1 234"), tok("5 678"), tok("910"), tok("11 121")]


def test_a_page_with_a_title_and_numbers_is_a_statement():
    assert signals.plaquette_statement([tok("Bilan Actif"), *NUMBERS]) == "BS_ASSETS"


def test_a_divider_page_with_a_matching_title_is_not_a_statement():
    """`BILAN & COMPTE DE RESULTAT` on an otherwise empty page is a section divider.

    Two of these exist in the corpus and both were routed as statement pages before the
    numeric-density guard was added.
    """
    divider = [tok("COMPTE DE RESULTAT"), tok("Page"), tok("Exercice"), tok("Societe")]
    assert signals.plaquette_statement(divider) is None


# --- signal D: the registry's confidentiality flag -------------------------------------


def test_confidential_income_statement_is_read_from_meta():
    confidential = {"confidentiality": "Partiellement confidentiel"}
    assert signals.income_statement_is_confidential(confidential)
    assert not signals.income_statement_is_confidential({"confidentiality": "Public"})
    assert not signals.income_statement_is_confidential({})


# --- numeric density -------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1 805 459", True),
        ("459", True),
        ("(52 814)", True),
        ("-45 440", True),
        ("FL", False),
        ("Chiffres d'affaires nets", False),
        ("", False),
        ("- ", False),  # punctuation with no digit is not a number
    ],
)
def test_looks_numeric(text, expected):
    assert looks_numeric(text) is expected


def test_numeric_ratio_of_an_empty_page_is_zero():
    assert numeric_ratio([]) == 0.0
