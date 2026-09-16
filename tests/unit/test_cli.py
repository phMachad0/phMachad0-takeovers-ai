from __future__ import annotations

import ast

import pytest

from liasse import paths
from liasse.cli import main


def test_doctor_reports_a_healthy_environment(capsys):
    assert main(["doctor"]) == 0
    assert "environment OK" in capsys.readouterr().out


def test_unknown_command_exits_nonzero():
    with pytest.raises(SystemExit):
        main(["nonsense"])


# --- every declared subcommand is actually wired up --------------------------------------


def _declared_and_dispatched_commands() -> tuple[set[str], set[str]]:
    """What argparse knows about, and what main()'s if-chain actually handles.

    Parsed from the source rather than exercised by calling every command, because several
    of them need the full corpus and a clean run order to succeed - the gap this test
    exists to catch is at the wiring level, before any of that matters. `run` and `report`
    were declared subparsers with no dispatch branch at all: `liasse run` printed "not
    implemented yet" and exited 2, which `make run` - the first command in this README -
    would have hit on a clean checkout.
    """
    import inspect

    import liasse.cli as cli_module

    tree = ast.parse(inspect.getsource(cli_module))
    main_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )

    declared = {
        call.args[0].value
        for call in ast.walk(main_fn)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "add_parser"
        and call.args
        and isinstance(call.args[0], ast.Constant)
    }
    dispatched = {
        compare.comparators[0].value
        for node in ast.walk(main_fn)
        if isinstance(node, ast.If)
        for compare in ast.walk(node.test)
        if isinstance(compare, ast.Compare)
        and isinstance(compare.left, ast.Attribute)
        and compare.left.attr == "command"
        and compare.comparators
        and isinstance(compare.comparators[0], ast.Constant)
    }
    return declared, dispatched


def test_every_declared_subcommand_has_a_dispatch_branch():
    declared, dispatched = _declared_and_dispatched_commands()
    assert declared, "no subcommands found: this guard is checking nothing"
    missing = declared - dispatched
    assert not missing, (
        f"{sorted(missing)} are registered with argparse but main() never checks for "
        f"them, so calling them falls through to 'not implemented yet' and exit code 2"
    )


# --- run and report, against the corpus ---------------------------------------------------


@pytest.mark.corpus
def test_run_chains_every_stage_and_writes_the_deliverable(capsys):
    """`make run`'s command, and the one this README's "How to run it" promises."""
    assert main(["run"]) == 0
    out = capsys.readouterr().out
    assert paths.RESULTS_JSON.exists()
    for report in ("routing.json", "extraction.json", "verification.json", "cost.json"):
        assert (paths.REPORTS_DIR / report).exists(), f"run did not produce reports/{report}"
    # Every stage's own summary line should have printed, not just the last one's.
    assert "pages carry fields" in out
    assert "values from" in out
    assert "wrote reports/cost.json" in out


@pytest.mark.corpus
def test_report_regenerates_reports_without_touching_results_json(capsys):
    main(["run"])
    before = paths.RESULTS_JSON.read_text(encoding="utf-8")

    assert main(["report"]) == 0
    assert paths.RESULTS_JSON.read_text(encoding="utf-8") == before
