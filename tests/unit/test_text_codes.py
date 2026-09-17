"""The sanity filter that separates real liasse line codes from false ones.

Every case here comes from wiki F013: the OCR read a whole vertical run of code cells as
one rotated line and recognised it as ``BZ`` with 37% confidence. Three signals reject it
independently, and each is tested on its own so that weakening any one of them fails.
"""

from __future__ import annotations

import pytest

from liasse.corpus.models import Token
from liasse.text.codes import codes_present, is_code_candidate

MEDIAN_HEIGHT = 40.0


def tok(text: str, *, h: float = 40, score: float = 0.99, angle: int = 0) -> Token:
    return Token(
        text=text,
        polygon=((100, 100), (150, 100), (150, 100 + h), (100, 100 + h)),
        score=score,
        orientation_angle=angle,
    )


def test_a_clean_code_is_accepted():
    assert is_code_candidate(tok("FL"), MEDIAN_HEIGHT)
    assert is_code_candidate(tok("B1"), MEDIAN_HEIGHT)


@pytest.mark.parametrize("text", ["F", "FLM", "fl", "12", "F-", "Chiffres"])
def test_things_that_are_not_two_character_codes_are_rejected(text):
    assert not is_code_candidate(tok(text), MEDIAN_HEIGHT)


def test_a_low_scoring_token_is_rejected():
    """The false BZ scored 0.37; genuine codes scored 0.998-0.999."""
    assert not is_code_candidate(tok("BZ", score=0.37), MEDIAN_HEIGHT)


def test_rotation_alone_does_not_disqualify_a_code():
    """Withdrawn signal, and why.

    The false BZ of wiki F013 carried orientation_angle 1, which looked decisive. Measured
    over the corpus, 12 of the 18 two-letter tokens with a non-zero angle are ordinary line
    codes - IH, TH, CO, GQ - with full scores and normal height. Rejecting on the angle
    cost real fields, so it is recorded as evidence and no longer used as a veto.
    """
    assert is_code_candidate(tok("CO", angle=1, score=0.88), MEDIAN_HEIGHT)


def test_an_over_tall_token_is_rejected():
    """The false BZ was 367 px tall against a median of about 40."""
    assert not is_code_candidate(tok("BZ", h=367), MEDIAN_HEIGHT)


def test_the_false_bz_is_rejected_twice_over():
    """Defence in depth on the two signals that survived measurement.

    Score and height each reject the known bad token on their own, so withdrawing the
    orientation rule did not weaken the guard that matters.
    """
    assert not is_code_candidate(tok("BZ", score=0.37, angle=1, h=367), MEDIAN_HEIGHT)
    assert not is_code_candidate(tok("BZ", score=0.37), MEDIAN_HEIGHT)
    assert not is_code_candidate(tok("BZ", h=367), MEDIAN_HEIGHT)


def test_codes_present_filters_the_page():
    page = [tok("FL"), tok("BZ", score=0.37, angle=1, h=367), tok("FY"), tok("Salaires")]
    assert codes_present(page) == {"FL", "FY"}


@pytest.mark.corpus
def test_the_real_false_bz_is_rejected_on_the_real_page():
    """The whole filter, on the page the failure actually happened on."""
    from liasse.corpus.loader import iter_pages, load_document
    from liasse.corpus.scope import SCOPE

    entry = next(e for e in SCOPE if e.doc_id == "65784e5da67d84faf4042736")
    page = next(p for p in iter_pages(load_document(entry)) if p.page == 6)

    assert any(t.text.strip() == "BZ" for t in page.tokens), "the false token should be there"
    assert "BZ" not in codes_present(page.tokens), "but it must not be taken for a code"
    assert "FL" in codes_present(page.tokens)
