"""Reading fields off a DGFiP liasse.

The ladder has two rungs, and their order is what the corpus asked for rather than what
seemed principled beforehand. Over the 121 field/page pairs in scope:

    code present and label present     91   75%
    code missing, label present        27   22%   <- the label carries these
    neither                             2    2%
    code present, label missing         1    1%

So the line code is the primary anchor and the printed label is the fallback that actually
does the work. A third rung - inferring a missing row from its ordinal position in the form
- was planned and is *not* built: it would serve the two remaining pairs, and on both of
those the OCR dropped the whole row, leaving nothing to interpolate between. See the E5
notes for the measurement.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from liasse.corpus.models import OcrPage
from liasse.fields.catalog import CATALOG, Column, FieldSpec, RowAnchor
from liasse.routing.titles import fold
from liasse.text.codes import is_code_candidate, median_token_height
from liasse.text.fuzzy import matches_any
from liasse.text.lines import Line, PositionedToken, lines_of
from liasse.text.numbers import ParsedNumber, looks_numeric, parse_cells

from .base import Anchoring, Component, MissingValue, RawValue, Tier


def _code_tokens(line: Line, median_height: float) -> list[PositionedToken]:
    return [t for t in line.tokens if is_code_candidate(t.token, median_height)]


def _find_by_code(
    lines: Sequence[Line], anchor: RowAnchor, median_height: float
) -> tuple[Line, PositionedToken] | None:
    for line in lines:
        for token in _code_tokens(line, median_height):
            if token.text == anchor.code:
                return line, token
    return None


def _label_matches(line: Line, anchor: RowAnchor) -> bool:
    """Do this row's words spell the anchor's printed label?

    Unlike a statement title, a row label is not anchored at the start of the line - the
    form indents and prefixes them - so presence in order is the right test here, with the
    exclusions doing the work of telling near-identical rows apart.
    """
    present = fold(" ".join(line.texts)).split()
    if any(any(matches_any(w, {bad}) for w in present) for bad in anchor.without):
        return False
    position = 0
    for spellings in anchor.label:
        for index in range(position, len(present)):
            if matches_any(present[index], spellings):
                position = index + 1
                break
        else:
            return False
    return True


def _find_by_label(lines: Sequence[Line], anchor: RowAnchor) -> tuple[Line, None] | None:
    if not anchor.has_label:
        return None
    for line in lines:
        if _label_matches(line, anchor):
            return line, None
    return None


def _cells_between(line: Line, start: float, end: float) -> list[ParsedNumber | None]:
    return parse_cells([t for t in line.tokens if start < t.x < end and looks_numeric(t.text)])


def _cells_for(
    line: Line, anchor: RowAnchor, code_token: PositionedToken | None, median_height: float
) -> tuple[list[ParsedNumber | None], int]:
    """The cells this anchor may read, and which of them is its own.

    Three shapes, because a liasse row is not one thing:

    *Anchored on its code, one cell.* The figure is the first cell to the right, bounded by
    the next code so that a neighbouring column is never read by mistake.

    *Anchored on its code, three columns.* On form 2050 a row reads Brut | Amortissements |
    Net and the middle column has its own code. Stopping at that code would return the
    gross figure - a larger, entirely plausible, wrong number (wiki F011).

    *Code missing.* The row is still identifiable by its label, and the sibling codes that
    did survive say which cell is ours: the revenue row prints FJ, FK, FL, so with FK read
    and FL lost, the total is the cell after FK's own.
    """
    codes = _code_tokens(line, median_height)

    if code_token is not None:
        start = code_token.x
        if anchor.column is Column.NET_OF_THREE:
            return _cells_between(line, start, 1e9), 2
        end = min((t.x for t in codes if t.x > start), default=1e9)
        return _cells_between(line, start, end), 0

    if anchor.siblings and anchor.code in anchor.siblings:
        position = anchor.siblings.index(anchor.code)
        present = [
            (anchor.siblings.index(t.text), t)
            for t in codes
            if t.text in anchor.siblings[:position]
        ]
        if present:
            index, token = max(present)
            return _cells_between(line, token.x, 1e9), position - index

    cells = _cells_between(line, -1e9, 1e9)
    return cells, (2 if anchor.column is Column.NET_OF_THREE else 0)


def _pick(cells: Sequence[ParsedNumber | None], index: int) -> ParsedNumber | None:
    """The cell at an index, or the last one when the row printed fewer columns.

    Falling back to the last cell covers filings that omit a column entirely - some print
    only the net - but never reaches past the end into another row.
    """
    if not cells:
        return None
    return cells[index] if index < len(cells) else cells[-1]


def _read_anchor(
    pages_by_form: dict[str, list[OcrPage]], anchor: RowAnchor, previous: bool = False
) -> Component | None:
    for page in pages_by_form.get(anchor.form, ()):
        lines = lines_of(page)
        median_height = median_token_height(page.tokens)

        found = _find_by_code(lines, anchor, median_height)
        tier, matched = Tier.CODE, None
        if found is None:
            found = _find_by_label(lines, anchor)
            tier, matched = Tier.LABEL, anchor.code
            if found is None:
                continue

        line, code_token = found
        if tier is Tier.LABEL:
            matched = " ".join(line.texts)[:80]
        anchoring = Anchoring(tier=tier, form=anchor.form, code=anchor.code, matched_label=matched)

        cells, index = _cells_for(line, anchor, code_token, median_height)
        if previous:
            # The exercise before this one, printed immediately to the right of the current
            # one when the filing shows both. Absent on filings that print only N, and the
            # caller treats that as "no comparison available" rather than as a zero.
            index += 1
            if index >= len(cells):
                return None
        if not cells:
            # The row is there and its cell is empty. On a liasse a blank cell is nil, so
            # this is a reading and not a gap: the company holds no securities, or charged
            # no provision on fixed assets. Recording it explicitly is what keeps a real
            # zero apart from a row the OCR failed to deliver.
            return Component(
                code=anchor.code,
                value=0,
                page=page.page,
                tokens=(line.tokens[0],),
                anchoring=anchoring,
                blank=True,
            )

        parsed = _pick(cells, index)
        if parsed is None:
            continue
        return Component(
            code=anchor.code,
            value=parsed.value,
            page=page.page,
            tokens=parsed.tokens,
            anchoring=anchoring,
        )
    return None


def _read_spec(
    pages_by_form: dict[str, list[OcrPage]], key: str, anchors: Sequence[RowAnchor], unit: str
) -> RawValue | MissingValue:
    components = [c for c in (_read_anchor(pages_by_form, a) for a in anchors) if c]
    if not components:
        return MissingValue(key, reason="no anchor resolved on any page of the right form")

    found = {c.code for c in components}
    return RawValue(
        field_key=key,
        value=sum((c.value for c in components), start=0),
        page=components[0].page,
        unit=unit,
        components=tuple(components),
        missing_components=tuple(a.code for a in anchors if a.code not in found),
    )


def extract(pages: Iterable[OcrPage], forms: dict[int, str]) -> list[RawValue | MissingValue]:
    """Read every field of the catalogue off one document's liasse pages.

    ``forms`` maps page number to form id, as the router decided.
    """
    pages_by_form: dict[str, list[OcrPage]] = {}
    for page in pages:
        form = forms.get(page.page)
        if form:
            pages_by_form.setdefault(form, []).append(page)

    results: list[RawValue | MissingValue] = []
    for spec in CATALOG:
        results.append(_read_spec(pages_by_form, spec.key, spec.anchors, spec.unit))
        if spec.variant_key:
            results.append(
                _read_spec(pages_by_form, spec.variant_key, spec.variant_anchors, spec.unit)
            )
    return results


def read_codes(
    pages: Iterable[OcrPage],
    forms: dict[int, str],
    anchors: Sequence[RowAnchor],
    *,
    previous: bool = False,
) -> dict[str, Component]:
    """Read a set of raw line codes, for the checks rather than for the deliverable."""
    pages_by_form: dict[str, list[OcrPage]] = {}
    for page in pages:
        form = forms.get(page.page)
        if form:
            pages_by_form.setdefault(form, []).append(page)

    out: dict[str, Component] = {}
    for anchor in anchors:
        if previous and not anchor.allows_previous:
            continue
        component = _read_anchor(pages_by_form, anchor, previous=previous)
        if component is not None:
            out[anchor.code] = component
    return out


__all__ = ["extract", "read_codes", "FieldSpec"]
