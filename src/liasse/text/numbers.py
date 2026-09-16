"""Recognising and reading numbers in OCR tokens.

The OCR does not hand over `1 805 459`. It hands over `1`, `805`, `459` as three separate
tokens, because the French thousands separator is a space and the detector cuts on the wide
gaps of a form cell. A parser that takes the token nearest the line code reads **1**, with
the right type, the right page and a plausible box, and no way to know it is wrong. That
alone invalidates a pipeline (wiki F003).

So reading a number is a clustering problem with a syntactic check, not a string problem.
The check is what makes it safe: a well-formed French amount is a run of three-digit groups
with a one-to-three-digit group in front. If grouping accidentally swallows a neighbouring
column, the result violates that shape and is *refused* rather than reported.

Signs are their own trap. Negatives are printed in parentheses, and the OCR breaks the
parentheses in three different ways on one page - including one where only the closing
bracket survives, silently flipping the sign of a field the challenge asks for (wiki F004).
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from liasse.corpus.models import Token
from liasse.text.lines import PositionedToken

# French formatting: space as thousands separator, comma as decimal, parentheses or a
# leading minus for negatives. The OCR splits and mangles all of these, which is E4's
# problem; for a density count, "does this look like part of a number" is enough.
#
# One stray mark is allowed at the end. The detector glues an apostrophe or a colon to an
# amount here and there - "963 002 '", "-97 957 :" - and rejecting the whole token for it
# threw away two terms of a cost of goods sold, which then went absent for a document that
# prints both of them plainly. Only a single trailing character, and only from marks that
# never carry meaning in an amount.
_NUMERIC_RE = re.compile(r"^[\d\s.,()\u2212\u2013\u2014+-]+[\'\":;*\u00b0\u2022]?$")


def looks_numeric(text: str) -> bool:
    """True when a token is made only of digits and number punctuation."""
    stripped = text.strip()
    if not stripped or not any(c.isdigit() for c in stripped):
        return False
    return bool(_NUMERIC_RE.fullmatch(stripped))


def numeric_ratio(tokens: Iterable[Token]) -> float:
    """Share of tokens on a page that look numeric.

    A filed statement is mostly numbers; a section divider that merely says
    "COMPTE DE RESULTAT" is not. This is what stops a divider page being routed as a
    statement page.
    """
    tokens = list(tokens)
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if looks_numeric(t.text)) / len(tokens)


# --- reading a number out of a run of tokens -------------------------------------------

# Digits, optionally split into space-separated groups, optionally with a decimal part.
_DIGIT_GROUP = re.compile(r"\d+")
# Characters that may decorate a number without being part of its value.
_DECORATION = "()[]−–—+-. "

# Gap above which two numeric tokens are taken to be in different cells, expressed in
# median digit widths so it survives a change of render resolution.
#
# Measured over every row of the 28 liasse pages in scope, the two populations are far
# apart and do not overlap:
#
#     within one number    median 0.27,  worst 0.70 digit widths
#     between columns      median 6.76,  tightest 2.8
#
# 1.5 sits between them with room on both sides. An earlier value of 4.0 came from a
# biased sample - only the rows a faulty detector had flagged - and merged 68 genuine
# column separations, which then failed the shape check and cost whole fields.
GAP_IN_DIGIT_WIDTHS = 1.5
# Floor for pages whose digits are unusually narrow. The worst gap inside a number was
# 0.70 x 31 px, so this stays clear of it.
MIN_GAP_PX = 30.0


@dataclass(frozen=True, slots=True)
class ParsedNumber:
    """A value, and every token it was read from."""

    value: int | Decimal
    tokens: tuple[PositionedToken, ...]
    negative_marker: str | None = None  # "parenthesis" | "minus" | None

    @property
    def text(self) -> str:
        return " ".join(t.text for t in self.tokens)


def digit_width(tokens: Sequence[PositionedToken]) -> float:
    """Median width of one printed digit, measured on the tokens at hand."""
    widths = []
    for token in tokens:
        xs = [p[0] for p in token.token.polygon]
        digits = sum(c.isdigit() for c in token.text)
        if digits:
            widths.append((max(xs) - min(xs)) / digits)
    return statistics.median(widths) if widths else 0.0


def _x_range(token: PositionedToken) -> tuple[float, float]:
    xs = [p[0] for p in token.token.polygon]
    return min(xs), max(xs)


def _split_amount(text: str) -> tuple[list[str], str]:
    """Digit groups of the whole part, and the decimal part if there is one.

    The French decimal separator is a comma, so everything after the last comma followed
    by one or two digits is a fraction and is not subject to the three-digit grouping rule.
    """
    whole, separator, fraction = text.rpartition(",")
    fraction_digits = "".join(_DIGIT_GROUP.findall(fraction))
    if separator and 1 <= len(fraction_digits) <= 2 and _DIGIT_GROUP.search(whole):
        return _DIGIT_GROUP.findall(whole), fraction_digits
    return _DIGIT_GROUP.findall(text), ""


def _groups_of(text: str) -> list[str]:
    return _split_amount(text)[0]


def _is_well_formed(groups: Sequence[str]) -> bool:
    """Does this sequence of digit groups spell one French amount?

    With more than one group: every group but the leftmost is exactly three digits and the
    leftmost is one to three. This is what catches a grouping that reached into the next
    column - `2 524` followed by `1 805 459` yields a one-digit group in the middle, which
    no amount ever has.

    A *single* group of any length is accepted. The OCR sometimes loses a thousands
    separator (`62614`, `509582` in the corpus) and the digits are then unambiguous. What
    stays refused is a long group *next to* others, which is the signature of two cells
    merged into one token rather than of a lost space - measured at 0.4% of digit groups,
    and those go to escalation instead of being guessed at.
    """
    if not groups or len(groups) > 6:
        return False
    if len(groups) == 1:
        return len(groups[0]) <= 12
    if not 1 <= len(groups[0]) <= 3:
        return False
    return all(len(group) == 3 for group in groups[1:])


_MINUS_SIGNS = ("-", "−", "–", "—")


def _sign_of(
    accepted: Sequence[PositionedToken], preceding: Sequence[PositionedToken]
) -> str | None:
    """Which marker, if any, says this amount is negative.

    Five renderings, all seen in the corpus: an opening bracket as a token of its own, a
    closing bracket glued to the last digits, a bare minus to the left, a minus glued to
    the front of the digits, and a minus trailing them - the last being an accounting
    convention one of the three plaquette dialects uses throughout.

    A lone closing bracket is taken at face value even though it is half a pair, and that
    is a decision rather than an oversight. Requiring a matching opener was tried: it is
    correct reasoning and it is wrong here, because the liasse really does lose the opener
    - form 2052 prints "(76 778)" and the OCR delivers "76 778)" - and the arithmetic check
    on that row confirms the figure is negative. The cost is that a stray bracket elsewhere
    flips a sign, which happens once in the corpus; that one is caught where the evidence
    to catch it exists, on the page's own Brut - Amortissements = Net identity, rather than
    here where there is nothing to tell the two apart.
    """
    text = " ".join(t.text for t in accepted)
    if ")" in text:
        return "parenthesis"

    for token in reversed(preceding):
        stripped = token.text.strip()
        if stripped in {"(", "["}:
            return "parenthesis"
        if stripped in _MINUS_SIGNS:
            return "minus"
        if stripped:
            break  # anything else between means the marker is not ours

    first, last = accepted[0].text.strip(), accepted[-1].text.strip()
    if first.startswith(_MINUS_SIGNS) or last.endswith(_MINUS_SIGNS):
        return "minus"
    return None


def split_cells(tokens: Sequence[PositionedToken]) -> list[list[PositionedToken]]:
    """Cut a run of tokens into printed cells, on the gaps between columns.

    The two populations are far apart - within a number the corpus shows 1 to 12 px,
    between columns 173 to 195 - so this cut is not delicate. It exists because a row
    often carries the same figure for two exercises side by side, and which column a
    field wants is a decision the caller makes, not one this module may take by
    grabbing whichever end it reaches first.
    """
    numeric = sorted((t for t in tokens if looks_numeric(t.text)), key=lambda t: _x_range(t)[0])
    if not numeric:
        return []
    max_gap = max(MIN_GAP_PX, GAP_IN_DIGIT_WIDTHS * digit_width(numeric))

    cells: list[list[PositionedToken]] = [[numeric[0]]]
    for left, right in zip(numeric[:-1], numeric[1:], strict=True):
        if _x_range(right)[0] - _x_range(left)[1] > max_gap:
            cells.append([right])
        else:
            cells[-1].append(right)
    return cells


def parse_cells(tokens: Sequence[PositionedToken]) -> list[ParsedNumber | None]:
    """Read every printed cell of a run, left to right. None where a cell is unreadable."""
    return [_parse_one_cell(cell, tokens) for cell in split_cells(tokens)]


def _parse_one_cell(
    cell: Sequence[PositionedToken], row: Sequence[PositionedToken]
) -> ParsedNumber | None:
    """Read one cell, or refuse.

    Refusing is the point. A cell whose digit groups do not spell an amount is either two
    printed cells the OCR merged or one it split beyond repair; returning the fragment
    that happens to be well formed would be a plausible wrong answer, and a plausible
    wrong answer is the one outcome nothing downstream can detect.
    """
    if not cell:
        return None
    groups, fraction = _split_amount(" ".join(t.text for t in cell))
    if not _is_well_formed(groups):
        return None

    leftmost = _x_range(cell[0])[0]
    preceding = [t for t in row if _x_range(t)[1] <= leftmost]
    marker = _sign_of(cell, preceding)

    whole = "".join(groups)
    # Decimal, never float: the checks in E7 compare amounts for exact equality, and a
    # float would need an arbitrary tolerance that hides real misreadings.
    value: int | Decimal = Decimal(f"{whole}.{fraction}") if fraction else int(whole)
    if marker is not None:
        value = -value
    return ParsedNumber(value=value, tokens=tuple(cell), negative_marker=marker)


def parse_amount(tokens: Sequence[PositionedToken]) -> ParsedNumber | None:
    """Read the rightmost amount of a run of tokens, or refuse.

    Kept as the simple case; ``parse_cells`` is what the extractor uses, because which
    column a field wants is its decision to make.
    """
    cells = split_cells(tokens)
    return _parse_one_cell(cells[-1], tokens) if cells else None
