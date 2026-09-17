"""Reading fields off a plaquette, where there are no line codes to anchor on.

Everything downstream of this module is unchanged: the same ``Component`` and ``RawValue``,
so units, the checks, the confidence aggregation and the emitted file all work on plaquette
values without knowing one was read. That reuse is what the layering was for.

Two things are genuinely different from the liasse extractor, and both are about columns.

*Which column holds the figure is not known in advance.* A liasse row says so by carrying
its code next to the cell. A plaquette prints two, four or six columns and names them in a
header row that the OCR often mangles. The grid is recovered from geometry instead - see
``liasse.text.columns`` - and which of its columns is the current exercise is decided here.

*A blank cell is not a zero.* On a liasse an empty cell on a row that exists means nil, and
the extractor records it as such. Here it cannot: a plaquette prints section headings -
"CAPITAUX PROPRES", "DISPONIBILITÉS ET DIVERS" - that match the words of the row underneath
them and carry no figure at all. So a match only counts when the row actually prints
something in the column being read, and a row that prints nothing is left unread rather than
recorded as zero. The same rule is what makes it safe to accept a heading as a label: one
dialect prints its equity total on the heading line itself.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from liasse.corpus.models import OcrPage
from liasse.fields.plaquette import PLAQUETTE_CATALOG, PlaquetteSpec, Reading, Term
from liasse.routing.titles import fold
from liasse.text.columns import ColumnGrid, build_grid, row_cells
from liasse.text.fuzzy import matches_any, matches_run
from liasse.text.lines import Line, lines_of
from liasse.text.numbers import ParsedNumber

from .base import Anchoring, Component, MissingValue, RawValue, Tier

# A balance sheet whose first three columns behave like Brut, Amortissements and Net over
# at least this share of the rows that fill all three. Measured: on the eight asset pages
# with a three-column block the identity holds on every row but the subtotals, which are
# off by one from the rounding of their own terms.
NET_CONFIRMATION_RATIO = 0.7

# Rounding slack when confirming that identity. A liasse-style form rounds each row to the
# euro, so a column of them can disagree with its own difference by a unit or two.
NET_TOLERANCE = 2

BS_ASSETS = "BS_ASSETS"


@dataclass(frozen=True, slots=True)
class PageColumns:
    """A page, its recovered grid, and which column carries the current exercise."""

    page: OcrPage
    statement: str
    lines: tuple[Line, ...]
    grid: ColumnGrid
    current: int | None


def _looks_like_brut_amort_net(lines: Sequence[Line], grid: ColumnGrid) -> bool:
    """Do the first three columns satisfy Brut - Amortissements = Net?

    Asked only of asset pages, and that restriction is load bearing. The same arithmetic
    holds on a liabilities page that prints N, N-1 and the variation between them, because
    the variation is defined as the difference - so a page shape cannot be inferred from
    the identity alone. The router has already said which statement this is; the identity
    is used to confirm a layout, never to discover one.
    """
    agree = total = 0
    for line in lines:
        cells = row_cells(line, grid)
        if not {0, 1, 2} <= cells.keys():
            continue
        total += 1
        if abs((cells[0].value - cells[1].value) - cells[2].value) <= NET_TOLERANCE:
            agree += 1
    return total > 0 and agree / total >= NET_CONFIRMATION_RATIO


def current_column(statement: str, lines: Sequence[Line], grid: ColumnGrid) -> int | None:
    """Which column of the grid holds this exercise's figures.

    Almost always the first: a plaquette puts the current exercise leftmost and whatever
    it adds - the prior year, a percentage, a variation - to the right of it. The exception
    is the asset side of the balance sheet, which leads with Brut and Amortissements and
    prints the figure wanted third.

    Returns None rather than guessing when an asset page has three or more columns and does
    not satisfy the identity that would confirm the layout. An unread page is a gap; a page
    read one column across is a set of plausible wrong numbers.
    """
    if not len(grid):
        return None
    if statement != BS_ASSETS or len(grid) < 3:
        return 0
    return 2 if _looks_like_brut_amort_net(lines, grid) else None


def page_columns(page: OcrPage, statement: str) -> PageColumns:
    lines = lines_of(page)
    grid = build_grid(lines)
    return PageColumns(
        page=page,
        statement=statement,
        lines=lines,
        grid=grid,
        current=current_column(statement, lines, grid),
    )


def _label_matches(line: Line, term: Term) -> bool:
    """Do this row's words spell the term's label, in order?

    The same presence-in-order test the liasse extractor uses on a row label, with the
    exclusions doing the work of telling near-identical rows apart: "Dotations aux
    amortissements" and "Dotations aux provisions" differ by one word out of three.
    """
    present = fold(" ".join(line.texts)).split()
    if any(any(matches_any(w, {bad}) for w in present) for bad in term.without):
        return False
    position = 0
    for spellings in term.label:
        for index in range(position, len(present)):
            consumed = matches_run(present, index, spellings)
            if consumed:
                position = index + consumed
                break
        else:
            return False
    return True


def _repair_sign(line: Line, columns: PageColumns, cell: ParsedNumber) -> ParsedNumber:
    """Undo a sign the row's own arithmetic contradicts.

    The OCR glues a stray closing bracket to a figure now and then, and a closing bracket
    is how this corpus prints a negative, so the figure comes back with its sign flipped.
    Nothing in the parser can tell that bracket from a real one - form 2052 genuinely loses
    the opening half of a real pair - so the discrimination has to come from evidence the
    parser does not have.

    On an asset page there is such evidence, and it is the same identity that identified
    the Net column in the first place: Brut minus Amortissements equals Net. A Net cell
    whose sign breaks the identity and whose magnitude satisfies it was not negative. One
    row in the corpus is repaired here - securities of 365 359 that came back as minus
    365 359, on a balance sheet that cannot hold negative securities.
    """
    if columns.current != 2 or cell.value >= 0 or cell.negative_marker is None:
        return cell
    cells = row_cells(line, columns.grid)
    if not {0, 1} <= cells.keys():
        # With no amortisation cell printed the identity reads Brut = Net, which is the
        # shape of every fully-owned asset row on the page.
        if 0 not in cells or abs(cells[0].value - abs(cell.value)) > NET_TOLERANCE:
            return cell
    elif abs((cells[0].value - cells[1].value) - abs(cell.value)) > NET_TOLERANCE:
        return cell
    return ParsedNumber(value=-cell.value, tokens=cell.tokens, negative_marker=None)


def _find_term(columns: PageColumns, term: Term) -> tuple[Line, ParsedNumber] | None:
    """The first row matching the term that actually prints a figure in our column.

    Requiring the figure is what lets a section heading be used as a label safely. On most
    dialects "CAPITAUX PROPRES" is a bare heading and is skipped here; on one it carries
    the total itself and is exactly the row wanted.
    """
    if columns.current is None:
        return None
    for line in columns.lines:
        if not _label_matches(line, term):
            continue
        cell = row_cells(line, columns.grid).get(columns.current)
        if cell is not None:
            return line, _repair_sign(line, columns, cell)
    return None


def _read_term(pages: Sequence[PageColumns], term: Term) -> Component | None:
    for columns in pages:
        found = _find_term(columns, term)
        if found is None:
            continue
        line, cell = found
        return Component(
            code=term.key,
            value=cell.value,
            page=columns.page.page,
            tokens=cell.tokens,
            anchoring=Anchoring(
                tier=Tier.LABEL,
                form=columns.statement,
                code=term.key,
                matched_label=" ".join(line.texts)[:80],
            ),
        )
    return None


def _read_reading(
    pages: Sequence[PageColumns], reading: Reading
) -> tuple[list[Component], list[str]]:
    components, missing = [], []
    for term in reading.terms:
        component = _read_term(pages, term)
        if component is None:
            missing.append(term.key)
        else:
            components.append(component)
    return components, missing


def _read_spec(pages: Sequence[PageColumns], spec: PlaquetteSpec) -> RawValue | MissingValue:
    """The first reading that resolves completely, or the fullest one that resolved at all.

    Preferring a complete reading is what keeps a single printed total ahead of a sum we
    assembled: where a filing prints "Chiffres d'affaires nets" that row is taken, and the
    ventes-plus-production reconstruction is only reached on the dialect that prints no
    such row.
    """
    eligible = [c for c in pages if c.statement in spec.statements]
    best: tuple[list[Component], list[str]] | None = None

    for reading in spec.readings:
        components, missing = _read_reading(eligible, reading)
        if components and not missing:
            best = (components, missing)
            break
        if components and (best is None or len(components) > len(best[0])):
            best = (components, missing)

    if best is None:
        return MissingValue(spec.key, reason="no row of any reading matched on a plaquette page")

    components, missing = best
    return RawValue(
        field_key=spec.key,
        value=sum((c.value for c in components), start=0),
        page=components[0].page,
        unit=spec.unit,
        components=tuple(components),
        missing_components=tuple(missing),
    )


def extract(
    pages: Iterable[OcrPage], statements: dict[int, str]
) -> list[RawValue | MissingValue]:
    """Read every field of the plaquette catalogue off one document's plaquette pages.

    ``statements`` maps page number to the statement the router assigned it.
    """
    prepared = [
        page_columns(page, statements[page.page]) for page in pages if page.page in statements
    ]
    return [_read_spec(prepared, spec) for spec in PLAQUETTE_CATALOG]


def read_terms(
    pages: Iterable[OcrPage], statements: dict[int, str], terms: Sequence[Term]
) -> dict[str, Component]:
    """Read a set of rows for the checks rather than for the deliverable."""
    prepared = [
        page_columns(page, statements[page.page]) for page in pages if page.page in statements
    ]
    out: dict[str, Component] = {}
    for term in terms:
        component = _read_term(prepared, term)
        if component is not None:
            out[term.key] = component
    return out


__all__ = ["extract", "read_terms", "page_columns", "current_column"]
