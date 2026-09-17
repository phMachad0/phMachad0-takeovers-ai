"""Edit-distance matching.

The tolerance this module allows is only safe against a vocabulary whose words are far
enough apart, and `minimum_separation` is what measures that. The check itself lives with
the vocabulary it constrains, in tests/unit/test_routing_titles.py - a tolerance chosen
because it worked on the sample is a tuned parameter; one provably below half the
vocabulary's own separation is a bound.
"""

from __future__ import annotations

import pytest

from liasse.text.fuzzy import (
    MAX_EDITS,
    is_close,
    levenshtein,
    matches_any,
    minimum_separation,
    tolerance_for,
)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("", "", 0),
        ("abc", "abc", 0),
        ("passif", "passit", 1),
        ("resultat", "resuitat", 1),
        ("actif", "passif", 3),
        ("", "abc", 3),
    ],
)
def test_levenshtein(a, b, expected):
    assert levenshtein(a, b) == expected


def test_levenshtein_gives_up_once_the_bound_is_exceeded():
    """The early exit must never report a distance below the true one."""
    assert levenshtein("actif", "passif", max_distance=1) > 1
    assert levenshtein("passif", "passit", max_distance=1) == 1


def test_short_words_must_match_exactly():
    """A single edit is a large share of a four-letter word, and short words are not
    discriminative enough to spend tolerance on."""
    assert tolerance_for("de") == 0
    assert tolerance_for("bilan") == MAX_EDITS


# --- the corruptions observed, and corruptions that were not ---------------------------


@pytest.mark.parametrize("observed,canonical", [("passit", "passif"), ("resuitat", "resultat")])
def test_the_two_corruptions_actually_in_the_corpus(observed, canonical):
    assert is_close(observed, canonical)


@pytest.mark.parametrize(
    "observed,canonical",
    [
        ("pasif", "passif"),  # deletion
        ("passlf", "passif"),  # l/i confusion
        ("pa5sif", "passif"),  # s/5 confusion
        ("resulta", "resultat"),  # truncation
        ("resu1tat", "resultat"),  # l/1 confusion
        ("actlf", "actif"),
        ("bi1an", "bilan"),
    ],
)
def test_corruptions_that_are_not_in_the_corpus_are_handled_too(observed, canonical):
    """The regexes this replaced encoded the two corruptions we happened to see. These
    are the ones we did not, and the brief is explicit that fitting the sample is what
    the five deliberately different companies are there to expose."""
    assert is_close(observed, canonical)


@pytest.mark.parametrize(
    "observed,canonical",
    [("actif", "passif"), ("bilan", "partie"), ("compte", "comptes annuels")],
)
def test_genuinely_different_words_are_not_matched(observed, canonical):
    assert not is_close(observed, canonical)


def test_minimum_separation_of_a_vocabulary():
    assert minimum_separation({"actif", "passif"}) == 3
    assert minimum_separation({"bilan"}) == 0


def test_matches_any_takes_the_first_acceptable_spelling():
    assert matches_any("deuxieme", {"seconde", "deuxieme"})
    assert not matches_any("premiere", {"seconde", "deuxieme"})
