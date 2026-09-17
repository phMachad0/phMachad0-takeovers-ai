"""Statement titles, as the OCR actually returns them."""

from __future__ import annotations

import pytest

from liasse.corpus.models import Token
from liasse.routing.titles import VOCABULARY, match_title, words_of
from liasse.text.fuzzy import MAX_EDITS, levenshtein, minimum_separation


def tok(text: str) -> Token:
    return Token(text=text, polygon=((0, 0), (1, 0), (1, 1), (0, 1)), score=0.99)


def title(*texts: str) -> str | None:
    return match_title([tok(t) for t in texts])


# --- titles as printed ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Bilan Actif", "BS_ASSETS"),
        ("BILAN - ACTIF", "BS_ASSETS"),  # the DGFiP form's own spelling
        ("Bilan Passif", "BS_LIABILITIES"),
        ("BILAN PASSIF", "BS_LIABILITIES"),
        ("Compte de Résultat", "PL"),
        ("COMPTE DE RESULTAT", "PL"),
        ("Compte de Résultat (Première Partie)", "PL"),
        ("Compte de Résultat (Seconde Partie)", "PL_CONT"),
    ],
)
def test_clean_titles(text, expected):
    assert title(text) == expected


# --- titles the OCR corrupted -----------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Bilan Passit", "BS_LIABILITIES"),  # real, 328024377
        ("Compte de Résuitat (Première Partie)", "PL"),  # real, 445070311
        ("Bi1an Pasif", "BS_LIABILITIES"),  # invented
        ("Compte de Resultot", "PL"),  # invented
        ("BlLAN ACTlF", "BS_ASSETS"),  # invented, I/l confusion twice
    ],
)
def test_corrupted_titles(text, expected):
    assert title(text) == expected


def test_a_title_split_across_tokens_is_still_found():
    """The OCR splits lines wherever it likes; a whole-string similarity ratio would
    score the bare token PASSIF at 0.667 and reject it."""
    assert title("Bilan", "Passif") == "BS_LIABILITIES"
    assert title("SAS SOMEPROD", "Bilan", "Actif") == "BS_ASSETS"


# --- what must NOT match ----------------------------------------------------------------


@pytest.mark.parametrize(
    "texts",
    [
        ("Notes sur le compte de résultat",),  # annexe schedule, contains every PL word
        ("Notes sur le bilan", "Actif immobilisé"),  # real, 328024377 p8
        ("Notes sur le bilan", "Actif circulant"),  # real, 401009741 p14
        ("Règles et Méthodes Comptables",),
        ("Tableau des filiales et participations",),
        ("Variations des Capitaux Propres",),
    ],
)
def test_text_that_merely_contains_the_words_is_not_a_title(texts):
    """A printed title does not contain its words, it begins with them."""
    assert title(*texts) is None


def test_the_more_specific_title_wins():
    """ "(Seconde Partie)" must not be claimed by the plain "Compte de Résultat" spec."""
    assert title("Compte de Résultat (Seconde Partie)") == "PL_CONT"


def test_a_title_below_the_search_depth_is_ignored():
    """Titles head the page. A mention further down is prose, not a heading."""
    filler = [f"ligne {i}" for i in range(14)]
    assert title(*filler, "Bilan Actif") is None


def test_words_of_folds_accents_and_punctuation():
    assert words_of("Compte de Résultat (Seconde Partie)") == [
        "compte",
        "de",
        "resultat",
        "seconde",
        "partie",
    ]


# --- the property that makes the one-edit tolerance a bound rather than a guess -------


def test_the_vocabulary_separation_justifies_the_tolerance():
    """No corrupted word within tolerance of one title word can be within tolerance of
    another. This is what makes a one-edit allowance safe, and it is a property of the
    vocabulary - so adding a word that breaks it fails here rather than in production.
    """
    separation = minimum_separation(VOCABULARY)
    assert separation >= 2 * MAX_EDITS + 1, (
        f"the two closest words in the title vocabulary are {separation} edits apart; "
        f"a tolerance of {MAX_EDITS} can map a corruption onto the wrong word"
    )


def test_the_closest_pair_is_the_one_we_think_it_is():
    """Documents the binding constraint: actif and passif are three edits apart."""
    assert minimum_separation(VOCABULARY) == 3
    assert levenshtein("actif", "passif") == 3
