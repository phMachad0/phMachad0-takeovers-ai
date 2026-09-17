"""Matching words the OCR got slightly wrong.

The failure this exists for is a single-character substitution inside a word: the corpus
has ``Bilan Passif`` coming back as ``Bilan Passit`` and ``Compte de Resultat`` as
``Compte de Resuitat``. Both are one edit away from the truth.

The tolerance is not a tuned parameter. It is bounded by a property of the vocabulary it
is used against: if the closest two words in that vocabulary are N edits apart, then a
tolerance below N/2 cannot map a corrupted word onto the wrong neighbour. That property is
checkable, and ``tests/unit/test_text_fuzzy.py`` checks it rather than trusting it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

# Below this length a single edit is a large share of the word, and short words are not
# discriminative anyway. They must match exactly.
MIN_LENGTH_FOR_EDIT = 5
MAX_EDITS = 1


def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    """Edit distance, optionally abandoned once it is known to exceed ``max_distance``.

    The early exit matters: this runs over every n-gram of every page.
    """
    if a == b:
        return 0
    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1

    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b))
            )
        if max_distance is not None and min(current) > max_distance:
            return max_distance + 1
        previous = current
    return previous[-1]


def tolerance_for(word: str) -> int:
    """How many edits a word of this length may absorb."""
    return MAX_EDITS if len(word) >= MIN_LENGTH_FOR_EDIT else 0


def is_close(observed: str, canonical: str) -> bool:
    """Is ``observed`` the OCR's rendering of ``canonical``?"""
    tolerance = tolerance_for(canonical)
    return levenshtein(observed, canonical, max_distance=tolerance) <= tolerance


def matches_any(observed: str, canonical_words: Iterable[str]) -> bool:
    return any(is_close(observed, word) for word in canonical_words)


def minimum_separation(vocabulary: Iterable[str]) -> int:
    """Smallest edit distance between any two distinct words in a vocabulary.

    This is the number that justifies the tolerance. Computing it is what turns
    "1 edit felt about right" into "1 edit cannot be ambiguous over these words".
    """
    words = sorted(set(vocabulary))
    if len(words) < 2:
        return 0
    return min(levenshtein(a, b) for i, a in enumerate(words) for b in words[i + 1 :])


# A word the detector cut in two is still one word. "Disponibilités" arrives as "Dispon"
# and "bilités" on a balance sheet in scope, and neither half is within an edit of the
# whole. Joining a token to the one after it and trying again recovers it, and cannot
# invent a match that was not nearly there: the join is only accepted under the same edit
# tolerance as any other spelling.
MAX_TOKENS_PER_WORD = 2


def matches_run(words: Sequence[str], index: int, canonical_words: Iterable[str]) -> int:
    """How many tokens starting at ``index`` spell one of these words. 0 for none."""
    spellings = list(canonical_words)
    if matches_any(words[index], spellings):
        return 1
    joined = words[index]
    for length in range(2, MAX_TOKENS_PER_WORD + 1):
        if index + length > len(words):
            break
        joined += words[index + length - 1]
        if matches_any(joined, spellings):
            return length
    return 0
