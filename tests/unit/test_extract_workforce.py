"""The headcount, which is the one field that is not in a table."""

from __future__ import annotations

import pytest

from liasse.corpus.loader import iter_pages, load_document
from liasse.corpus.scope import SCOPE
from liasse.extract.workforce import MAX_PLAUSIBLE_HEADCOUNT, PHRASINGS, find


def _find(prefix: str):
    entry = next(e for e in SCOPE if e.doc_id.startswith(prefix))
    return find(iter_pages(load_document(entry)))


# --- the patterns, without the corpus -----------------------------------------------------


def _matches(text: str) -> int | None:
    from liasse.extract.workforce import _match_text

    found = _match_text(text)
    return None if found is None else found[1]


def test_the_plain_heading_is_read():
    assert _matches("Effectif moyen du personnel 43 personnes") == 43


def test_a_misspelled_heading_is_still_read():
    """One filing has the OCR reading "personnal"."""
    assert _matches("Effectif moyen du personnal . 47 personnes.") == 47


def test_a_heading_that_goes_on_to_qualify_itself_gives_the_headcount():
    text = "Effectif moyen du personnel : 47 personnes dont 9 apprentis et 2 handicapés."
    assert _matches(text) == 47


def test_the_sentence_that_names_two_years_gives_this_one():
    """The trap this module is a list of phrasings for, rather than a nearest-digit search.

    Both 33 and 38 are real headcounts printed in the same breath, and which one a loose
    pattern returns depends on which end it starts from.
    """
    text = (
        "L'effectif salarié moyen à la clôture de l'exercice s'élève à 33 personnes "
        "contre 38 personnes à la clôture de l'exercice précédent."
    )
    assert _matches(text) == 33


def test_the_form_row_is_not_matched_by_the_prose_patterns():
    """"Effectif moyen du personnel * : YP 0" is a form row, read by the code anchor."""
    assert _matches("Effectif moyen du personnel * (dont: apprentis: handicapés): YP 9 9") is None
    assert _matches("DECLARATION DES EFFECTIFS Effectif moyen du personnel * : YP 0") is None


def test_an_unrelated_sentence_about_staff_yields_nothing():
    assert _matches("Personnel mis à disposition de l'entreprise : 3 personnes") is None
    assert _matches("L'effectif a augmenté cette année.") is None


def test_an_implausible_headcount_is_refused():
    assert _matches(f"Effectif moyen du personnel {MAX_PLAUSIBLE_HEADCOUNT + 1} personnes") is None


def test_every_phrasing_says_what_it_rests_on():
    for phrasing in PHRASINGS:
        assert phrasing.note, "a pattern without a note is a pattern nobody can review"
        assert phrasing.pattern.groups == 1


# --- against the corpus --------------------------------------------------------------------


@pytest.mark.corpus
@pytest.mark.parametrize(
    ("prefix", "expected", "page"),
    [
        ("63e8ebbb54febda17c19ee7c", 43, 19),
        ("63e8ebbb54febda17c19ee7d", 47, 43),
        ("63e8ebbb54febda17c19ee7e", 47, 42),
        ("63e2481c", 33, 5),
        ("65a4095d", 36, 5),
    ],
)
def test_the_headcount_is_read_off_the_annexe(prefix: str, expected: int, page: int):
    value = _find(prefix)
    assert value is not None
    assert value.value == expected
    assert value.page == page
    assert value.unit == "count", "a headcount must never carry a currency"
    assert value.components[0].tokens, "the value has to carry where it was read"


@pytest.mark.corpus
@pytest.mark.parametrize("prefix", ["6493e437", "68f0a715", "6860f28c"])
def test_a_filing_that_never_states_it_reports_nothing(prefix: str):
    assert _find(prefix) is None
