"""Recognising liasse line codes in a page of OCR tokens.

A two-letter uppercase token is a *candidate*, not a code. The OCR produces false ones,
and it tells us so: the detector once read a whole vertical run of code cells as a single
rotated line and recognised it as ``BZ`` with 37% confidence (wiki F013). Three signals
separate the real ones, and they are independent, so all three are cheap insurance.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Iterable

from liasse.corpus.models import Token

CODE_RE = re.compile(r"^[A-Z][A-Z0-9]$")

# A genuine code token scored 0.998-0.999 in the corpus; the known false one scored 0.37.
MIN_SCORE = 0.80
# A code cell is one line tall. Anything much taller swallowed several rows (wiki F008).
MAX_HEIGHT_RATIO = 3.0


def token_height(token: Token) -> float:
    ys = [point[1] for point in token.polygon]
    return max(ys) - min(ys)


def median_token_height(tokens: Iterable[Token]) -> float:
    heights = [token_height(t) for t in tokens]
    return statistics.median(heights) if heights else 0.0


def is_code_candidate(token: Token, median_height: float) -> bool:
    """Does this token look like a real liasse line code?

    Two rejections:
      - low score: the recogniser itself was unsure
      - excessive height: the box spans several rows, so the detector merged a column of
        cells rather than reading one

    ``orientation_angle`` was a third rejection and has been withdrawn. It looked decisive
    on the false ``BZ`` of wiki F013, which carried angle 1 - but measuring the whole
    corpus, 12 of the 18 two-letter tokens with a non-zero angle are ordinary line codes
    (``IH``, ``TH``, ``CO``, ``GQ``) with full scores and normal height, and rejecting them
    cost real fields. The false BZ is caught twice over by score (0.37) and height (367 px
    against a 40 px median), so the angle never carried its own weight.
    """
    text = token.text.strip()
    if not CODE_RE.fullmatch(text):
        return False
    if token.score < MIN_SCORE:
        return False
    return not (median_height > 0 and token_height(token) > MAX_HEIGHT_RATIO * median_height)


def code_tokens(tokens: Iterable[Token]) -> list[Token]:
    """Every token that survives the sanity filter, in input order."""
    tokens = list(tokens)
    median_height = median_token_height(tokens)
    return [t for t in tokens if is_code_candidate(t, median_height)]


def codes_present(tokens: Iterable[Token]) -> set[str]:
    """The set of distinct codes on a page. This is the page's structural fingerprint."""
    return {t.text.strip() for t in code_tokens(tokens)}
