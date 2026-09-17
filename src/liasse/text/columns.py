"""Recovering the column grid of a table that prints no line codes.

A DGFiP liasse says which cell is which: the row carries its two-letter code and the
extractor reads the cell beside it. A plaquette says nothing at all. There, which column a
figure belongs to is a fact about the page's geometry, and the page states that fact the
only way it can - by putting every figure of a column at the same horizontal position,
several dozen times over.

So the grid is recovered from that repetition rather than from the header row. The header
is a single line of OCR and it is mangled often: "31/08/2021." with a stray full stop, a
three-line stack reading "du 01/07/19 / au 30/06/20 / 12 mois", a "Amortissements / et
depreciations / (a deduire)" split across three bands. The column positions are attested by
every filled row on the page instead of by one line that has to survive.

Reading a plaquette row left to right is the mistake this module exists to prevent. A row
whose second cell is blank - an asset carrying no amortisation, a charge with no prior year
- shifts every figure after it one place left, and the third column's number is returned as
the second's. It is the right shape, the right magnitude and entirely wrong. Membership of
a column is positional, so a blank cell contributes nothing rather than displacing its
neighbours.

Measured over the 25 plaquette pages in scope whose reading order is sound, on 1 382
figures: consecutive right edges inside one column are never more than 52 px apart, and two
columns are never closer than 81 px. Nothing falls in between, so the threshold below sits
in an empty valley rather than on a judgement call.

The first attempt put it at 140 px, from a measurement that had read the 81-to-124 px band
as within-column scatter. It is not: that band is the distance from an amount column to the
percentage column printed beside it, and a threshold above it merges the two - which is the
exact failure this module is supposed to prevent. The valley is at the other end of the
distribution, and the two thresholds are a factor of two apart.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from liasse.text.lines import Line, PositionedToken
from liasse.text.numbers import ParsedNumber, looks_numeric, parse_cells

# Between 52 and 81 nothing was measured. See the module docstring.
COLUMN_GAP_PX = 65.0

# Columns attested by fewer rows than this are not columns. Measured: the sparsest real
# column in scope is the amortisation column of a balance sheet, which only the depreciated
# rows fill - 6 to 11 of them. The stray clusters are the France/export sub-cells of a
# revenue row and a page number, and all of those have 3.
MIN_COLUMN_MEMBERS = 5

# How far a figure may sit from a column's centre and still be one of its own. This is not
# what arbitrates between two adjacent columns - the nearest centre does, and over the 1 382
# figures measured it agrees with cluster membership every time. It exists to reject the
# figures that belong to no column at all: page numbers, footnote references, the sub-cells
# of a revenue row split into France and export. The widest legitimate deviation from a
# centre is 51 px.
COLUMN_RADIUS_PX = 60.0


@dataclass(frozen=True, slots=True)
class ColumnGrid:
    """Where the columns of one page are, and how many rows attested each."""

    centers: tuple[float, ...]
    members: tuple[int, ...]

    def __len__(self) -> int:
        return len(self.centers)

    def column_of(self, right_edge: float) -> int | None:
        """Which column a figure ending here belongs to, or None if it belongs to none.

        Returning None is a real answer: a figure printed outside every column of the
        grid is a footnote, a page number, or a sub-cell of a split row. Assigning it to
        the nearest column anyway is how a footnote becomes a balance sheet total.
        """
        if not self.centers:
            return None
        best = min(range(len(self.centers)), key=lambda i: abs(self.centers[i] - right_edge))
        return best if abs(self.centers[best] - right_edge) <= COLUMN_RADIUS_PX else None


def _cluster(values: Sequence[float], gap: float) -> list[list[float]]:
    ordered = sorted(values)
    groups: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - groups[-1][-1] > gap:
            groups.append([])
        groups[-1].append(value)
    return groups


def numeric_right_edges(lines: Iterable[Line]) -> list[float]:
    return [t.right for line in lines for t in line.tokens if looks_numeric(t.text)]


def build_grid(lines: Iterable[Line]) -> ColumnGrid:
    """The column grid of a page, from the figures it prints."""
    edges = numeric_right_edges(lines)
    if not edges:
        return ColumnGrid((), ())
    groups = [g for g in _cluster(edges, COLUMN_GAP_PX) if len(g) >= MIN_COLUMN_MEMBERS]
    return ColumnGrid(
        centers=tuple(sum(g) / len(g) for g in groups),
        members=tuple(len(g) for g in groups),
    )


def row_cells(line: Line, grid: ColumnGrid) -> dict[int, ParsedNumber]:
    """The figures of one row, keyed by the column each was printed in.

    A row that prints nothing in a column simply has no entry for it. The whole row is
    handed to the parser rather than the numeric tokens alone, because a minus sign or an
    opening bracket sitting to the left of a figure is what says it is negative.
    """
    cells: dict[int, ParsedNumber] = {}
    for parsed in parse_cells(line.tokens):
        if parsed is None:
            continue
        column = grid.column_of(_cell_right(parsed.tokens))
        if column is not None:
            cells.setdefault(column, parsed)
    return cells


def _cell_right(tokens: Sequence[PositionedToken]) -> float:
    return max(t.right for t in tokens)
