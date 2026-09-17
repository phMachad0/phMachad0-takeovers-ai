"""The column grid, and the shift it exists to prevent."""

from __future__ import annotations

import pytest

from liasse.corpus.models import Token
from liasse.text.columns import (
    COLUMN_GAP_PX,
    MIN_COLUMN_MEMBERS,
    ColumnGrid,
    build_grid,
    row_cells,
)
from liasse.text.lines import Line, PositionedToken

# Roughly the printed size of a character in the corpus, so that the gap between two
# synthetic tokens is the gap the cell splitter would really see.
CHAR_WIDTH, HEIGHT = 30.0, 40.0


def token(text: str, right: float, top: float) -> PositionedToken:
    """A token whose right edge sits where we put it, sized by what it says."""
    left = right - CHAR_WIDTH * len(text)
    polygon = (
        (left, top),
        (right, top),
        (right, top + HEIGHT),
        (left, top + HEIGHT),
    )
    return PositionedToken(token=Token(text=text, polygon=polygon, score=1.0), x=left, y=top)


def line(*cells: tuple[str, float], top: float = 0.0) -> Line:
    return Line(tokens=tuple(token(t, r, top) for t, r in cells), top=top)


def column_at(*rights: float) -> list[Line]:
    """Enough rows to attest each column."""
    return [
        line(*[(f"{n}00", r) for r in rights], top=float(n * 100))
        for n in range(1, MIN_COLUMN_MEMBERS + 1)
    ]


# --- building the grid ------------------------------------------------------------------


def test_the_grid_is_the_repetition_of_the_figures():
    grid = build_grid(column_at(1000.0, 2000.0, 3000.0))
    assert len(grid) == 3
    assert grid.centers == pytest.approx((1000.0, 2000.0, 3000.0))
    assert grid.members == (MIN_COLUMN_MEMBERS,) * 3


def test_a_position_too_few_rows_attest_is_not_a_column():
    """Page numbers and footnote markers sit alone. A column is a repetition."""
    rows = column_at(1000.0, 2000.0)
    rows.append(line(("7", 300.0), top=9000.0))
    grid = build_grid(rows)
    assert len(grid) == 2
    assert grid.column_of(300.0) is None


def test_columns_closer_than_the_threshold_are_one_column():
    grid = build_grid(column_at(1000.0, 1000.0 + COLUMN_GAP_PX - 1))
    assert len(grid) == 1


def test_columns_further_apart_than_the_threshold_are_two():
    grid = build_grid(column_at(1000.0, 1000.0 + COLUMN_GAP_PX + 1))
    assert len(grid) == 2


def test_a_page_with_no_figures_has_no_grid():
    assert len(build_grid([line(("Bilan Passif", 800.0))])) == 0


# --- assigning a figure to a column -------------------------------------------------------


def test_a_figure_outside_every_column_belongs_to_none():
    grid = ColumnGrid(centers=(1000.0, 2000.0), members=(9, 9))
    assert grid.column_of(1000.0) == 0
    assert grid.column_of(2000.0) == 1
    assert grid.column_of(500.0) is None


def test_a_blank_cell_does_not_shift_the_row():
    """The whole reason this module exists.

    An asset carrying no amortisation prints Brut and Net with nothing between them. Read
    left to right, its Net figure is returned as the amortisation - the right shape, the
    right magnitude, and entirely wrong.
    """
    grid = build_grid(column_at(1000.0, 2000.0, 3000.0))
    full = row_cells(line(("111", 1000.0), ("22", 2000.0), ("89", 3000.0), top=50.0), grid)
    gapped = row_cells(line(("111", 1000.0), ("111", 3000.0), top=50.0), grid)

    assert [c.value for c in full.values()] == [111, 22, 89]
    assert set(gapped) == {0, 2}
    assert gapped[2].value == 111
    assert 1 not in gapped


def test_a_percentage_column_is_a_column_of_its_own():
    """An amount and the percentage printed beside it are 81 px apart in the corpus.

    An earlier threshold of 140 px merged them, which put a percentage one position away
    from being read as the previous exercise.
    """
    rows = [
        line(("3 794 380", 1400.0), ("97", 1520.0), ("4 262 139", 1900.0), top=float(n))
        for n in range(100, 100 + MIN_COLUMN_MEMBERS * 100, 100)
    ]
    grid = build_grid(rows)
    assert len(grid) == 3, "the percentage column was merged into the amount column"
    cells = row_cells(rows[0], grid)
    assert cells[0].value == 3794380
    assert cells[2].value == 4262139
