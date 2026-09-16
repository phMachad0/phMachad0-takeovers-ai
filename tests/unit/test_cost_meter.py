"""The meter, and the guarantee that the run block is measured rather than typed.

The exit criterion for this stage is unusual: it is not that a number is right, it is that
a number is *derived*. A correct constant passes every value assertion you can write, so
the tests here attack the shape of the code instead.

Two of them do it dynamically - the same code path is driven with two different clocks and
two different page counts, and no constant satisfies both - and two do it statically, by
parsing the source and refusing to let the three required keys of the run block be written
as literals.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from liasse import paths
from liasse.cost.meter import (
    FX,
    PRICES,
    Meter,
    NothingMeasured,
    TokenLedger,
    pages_in_scope,
)

SRC = paths.REPO_ROOT / "src" / "liasse"
REQUIRED_RUN_KEYS = ("cost_eur_per_page", "seconds_per_page", "pages_processed")


class FakeClock:
    """A clock the test controls, so the measurement can be made to say two things."""

    def __init__(self, *ticks: float) -> None:
        self._ticks = iter(ticks)

    def __call__(self) -> float:
        return next(self._ticks)


def _meter(seconds: float, pages: int, carrying: int = 0) -> Meter:
    meter = Meter(clock=FakeClock(0.0, seconds))
    with meter.stage("work"):
        pass
    meter.count(pages, carrying)
    return meter


# --- the run block follows the measurement ----------------------------------------------


def test_seconds_per_page_follows_the_clock_and_the_page_count():
    """The same code path, two measurements, two answers. A constant cannot do this."""
    assert _meter(4.0, 2).seconds_per_page == pytest.approx(2.0)
    assert _meter(4.0, 8).seconds_per_page == pytest.approx(0.5)
    assert _meter(1.0, 8).seconds_per_page == pytest.approx(0.125)


def test_stages_are_timed_separately_and_sum_to_the_total():
    meter = Meter(clock=FakeClock(0.0, 2.0, 2.0, 5.0))
    with meter.stage("route"):
        pass
    with meter.stage("verify"):
        pass
    assert [s.name for s in meter.stages] == ["route", "verify"]
    assert [s.seconds for s in meter.stages] == [2.0, 3.0]
    assert meter.seconds == pytest.approx(5.0)


def test_a_stage_is_timed_even_when_it_raises():
    meter = Meter(clock=FakeClock(0.0, 7.0))
    with pytest.raises(ValueError), meter.stage("verify"):
        raise ValueError("boom")
    assert meter.stages[0].seconds == pytest.approx(7.0)


def test_a_meter_that_counted_nothing_refuses_to_report_a_rate():
    """The failure mode this stage exists to prevent: a comfortable zero from no data."""
    meter = _meter(4.0, 0)
    with pytest.raises(NothingMeasured):
        _ = meter.seconds_per_page
    with pytest.raises(NothingMeasured):
        _ = meter.eur_per_page


# --- the ledger -------------------------------------------------------------------------


def test_the_ledger_accumulates_simulated_calls():
    ledger = TokenLedger()
    ledger.record("page 6", "claude-sonnet-5", 5_000, 200)
    ledger.record("page 7", "claude-sonnet-5", 4_000, 150)

    assert ledger.input_tokens == 9_000
    assert ledger.output_tokens == 350
    assert ledger.models == ["claude-sonnet-5"]

    price = PRICES["claude-sonnet-5"]
    expected = (9_000 * price.usd_per_mtok_input + 350 * price.usd_per_mtok_output) / 1_000_000
    assert ledger.usd() == pytest.approx(expected)
    assert ledger.eur() == pytest.approx(FX.to_eur(expected))


def test_an_empty_ledger_sums_to_zero_rather_than_being_special_cased():
    assert TokenLedger().usd() == pytest.approx(0.0)
    assert TokenLedger().input_tokens == 0


def test_a_model_with_no_price_on_file_is_refused():
    with pytest.raises(KeyError):
        TokenLedger().record("page 1", "some-unpriced-model", 10, 10)


def test_cost_per_page_is_a_sum_over_calls_not_a_constant():
    """Zero today, and no longer zero the moment a call is recorded.

    This is what separates "the cost is 0.0" from "the cost came out at 0.0": the same
    expression produces a different number as soon as there is something to divide.
    """
    meter = _meter(1.0, 10)
    assert meter.eur_per_page == pytest.approx(0.0)

    meter.ledger.record("one page", "claude-opus-5", 1_000_000, 0)
    price = PRICES["claude-opus-5"]
    assert meter.eur_per_page == pytest.approx(FX.to_eur(price.usd_per_mtok_input) / 10)
    assert meter.eur_per_page > 0


def test_prices_and_the_exchange_rate_carry_the_day_they_were_read():
    """A price without a date rots silently: it stays plausible long after it is wrong."""
    for price in PRICES.values():
        assert len(price.consulted) == 10 and price.consulted[4] == "-"
        assert price.source
    assert len(FX.date) == 10
    assert FX.source
    assert FX.usd_per_eur > 0


# --- the run block ----------------------------------------------------------------------


def test_run_block_reports_what_it_divided_as_well_as_the_ratio():
    meter = _meter(8.0, 4, carrying=1)
    block = meter.run_block(model="provided OCR + rules", notes="n/a")

    assert block["seconds_per_page"] == pytest.approx(2.0)
    assert block["pages_processed"] == 4
    assert block["cost_eur_per_page"] == pytest.approx(0.0)

    measured = block["measured"]
    assert measured["seconds_total"] == pytest.approx(8.0)
    assert measured["pages_in_scope"] == 4
    assert measured["pages_carrying_fields"] == 1
    assert measured["api_calls"] == 0
    assert measured["input_tokens"] == 0
    assert [s["name"] for s in measured["stages"]] == ["work"]
    # The ratio must be redoable from the parts printed beside it.
    assert measured["seconds_total"] / measured["pages_in_scope"] == pytest.approx(
        block["seconds_per_page"]
    )


# --- the static guard -------------------------------------------------------------------


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _run_block_dicts(tree: ast.AST) -> list[ast.Dict]:
    """Every dict literal in the source that is shaped like a run block."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if "cost_eur_per_page" in keys:
                out.append(node)
    return out


def test_no_run_block_number_is_written_as_a_literal():
    """The exit criterion of this stage, enforced by parsing rather than by inspection."""
    found = 0
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in _run_block_dicts(tree):
            found += 1
            for key, value in zip(node.keys, node.values, strict=True):
                if not isinstance(key, ast.Constant) or key.value not in REQUIRED_RUN_KEYS:
                    continue
                assert not (
                    isinstance(value, ast.Constant) and isinstance(value.value, int | float)
                ), (
                    f"{path.relative_to(SRC)} writes {key.value!r} as the literal "
                    f"{value.value!r}. The run block is a measurement; a constant there "
                    f"is a claim nobody made."
                )
    assert found, "no run block found in the source: this guard is checking nothing"


def test_the_entry_point_does_not_assemble_a_run_block_of_its_own():
    """Keeps the guard above honest: a second run block in cli.py would escape it."""
    tree = ast.parse((SRC / "cli.py").read_text(encoding="utf-8"), filename="cli.py")
    assert not _run_block_dicts(tree), (
        "cli.py builds a run block inline. It must come from Meter.run_block, which is "
        "the only place the numbers can be derived from a measurement."
    )


# --- against the corpus -----------------------------------------------------------------


@pytest.mark.corpus
def test_pages_in_scope_matches_what_the_router_counted():
    """Two independent counts of the same thing: files on disk, and pages the router saw."""
    report = paths.REPORTS_DIR / "routing.json"
    if not report.is_file():
        pytest.skip("reports/routing.json not present; run `liasse route`")
    routed = json.loads(report.read_text(encoding="utf-8"))["totals"]["pages"]
    assert pages_in_scope() == routed
