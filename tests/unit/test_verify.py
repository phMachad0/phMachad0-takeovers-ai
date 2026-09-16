"""The checks, and the proof that they are not decorative.

The negative tests are the point of this file. A check that never fails anything is a check
that is not wired up, and on a corpus with no answer key nothing else would reveal that.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from liasse.verify import checks as _checks  # noqa: F401  registers them
from liasse.verify.confidence import for_field
from liasse.verify.registry import (
    REGISTRY,
    CheckResult,
    DocumentFacts,
    Scope,
    checks_for,
    rounding_tolerance,
)
from liasse.verify.runner import pass_rates, printed_closing_date, run

# --- the registry actually holds checks ---------------------------------------------------


def test_the_registry_is_populated():
    """Guards the failure that produced a clean sheet over nothing: checks register on
    import, so a missing import makes every run report perfect agreement."""
    assert len(REGISTRY) >= 5
    assert checks_for(Scope.DOCUMENT)
    assert checks_for(Scope.COMPANY)


def test_every_check_has_a_description():
    for check in REGISTRY:
        assert check.description.strip()


# --- the checks, on constructed facts -----------------------------------------------------


class _Typed:
    def __init__(self, value):
        self.value = value


def facts(**kwargs) -> DocumentFacts:
    fields = {k: _Typed(v) for k, v in kwargs.pop("fields", {}).items()}
    return DocumentFacts(
        doc_id=kwargs.pop("doc_id", "d"),
        siren=kwargs.pop("siren", "123456789"),
        fiscal_year_end=kwargs.pop("fiscal_year_end", "2023-04-30"),
        fields=fields,
        **kwargs,
    )


def test_v1_passes_when_the_two_sides_of_the_balance_sheet_meet():
    result = _checks.balance_identity(
        facts(fields={"BS_TOTAL_ASSETS_FRGAAP": 1_014_105}, codes={"EE": 1_014_105})
    )
    assert result[0].passed


def test_v1_catches_a_factor_of_a_thousand():
    """The error the units stage exists to avoid, seen from the other side."""
    result = _checks.balance_identity(
        facts(fields={"BS_TOTAL_ASSETS_FRGAAP": 1014}, codes={"EE": 1_014_105})
    )
    assert not result[0].passed


def test_v1_catches_the_gross_column_being_read_instead_of_the_net():
    """A real bug this caught: form 2050 reads Brut | Amortissements | Net."""
    result = _checks.balance_identity(
        facts(fields={"BS_TOTAL_ASSETS_FRGAAP": 8_754_311}, codes={"EE": 6_233_746})
    )
    assert not result[0].passed


def test_v2b_catches_an_inverted_sign():
    """`GV` arrives as `2` and `096)`; reading it positive flips a filed figure."""
    good = _checks.financial_result(
        facts(fields={"PL_FINANCIAL_RESULTS_FRGAAP": -2096}, codes={"GP": 0, "GU": 2096})
    )
    bad = _checks.financial_result(
        facts(fields={"PL_FINANCIAL_RESULTS_FRGAAP": 2096}, codes={"GP": 0, "GU": 2096})
    )
    assert good[0].passed and not bad[0].passed


def test_v3_catches_the_previous_year_column_being_read_as_the_current_one():
    earlier = facts(doc_id="a", fiscal_year_end="2016-12-31", codes={"EE": 1_807_858})
    later = facts(doc_id="b", fiscal_year_end="2017-12-31", codes_previous={"EE": 891_185})
    assert not _checks.cross_year(earlier, later)[0].passed


def test_a_check_that_cannot_run_reports_nothing_rather_than_passing():
    """Silence and agreement must never look the same."""
    assert _checks.balance_identity(facts(fields={}, codes={})) == []
    assert _checks.revenue_split(facts(fields={}, codes={"FJ": 1})) == []


# --- the rounding tolerance ----------------------------------------------------------------


def test_the_tolerance_is_a_rounding_budget_not_a_fudge_factor():
    """A real filing has FJ + FK = 5 564 580 against a printed FL of 5 564 581. Each figure
    is rounded to the euro on its own, so a two-term sum may sit one unit away - and never
    far enough to absorb a digit."""
    assert rounding_tolerance(2) == 1
    assert rounding_tolerance(1) == 1
    assert rounding_tolerance(11) == 5

    near = _checks.revenue_split(
        facts(fields={"PL_REVENUE_FRGAAP": 5_564_581}, codes={"FJ": 5_175_314, "FK": 389_266})
    )
    assert near[0].passed and near[0].delta == -1

    far = _checks.revenue_split(
        facts(fields={"PL_REVENUE_FRGAAP": 5_564_581}, codes={"FJ": 5_175_314, "FK": 389_166})
    )
    assert not far[0].passed


# --- confidence ------------------------------------------------------------------------------


def test_confidence_counts_only_the_checks_that_applied():
    """A field no check could reach is unverified, not wrong: it must not be penalised for
    a check that never ran."""
    results = [CheckResult("V1", True, "", covers=("A",))]
    assert for_field("A", results).score > for_field("B", results).score
    assert for_field("B", results).passed == ()


def test_more_independent_checks_raise_confidence():
    one = [CheckResult("V1", True, "", covers=("A",))]
    two = one + [CheckResult("V2a", True, "", covers=("A",))]
    assert for_field("A", two).score > for_field("A", one).score


def test_any_failure_dominates():
    mixed = [
        CheckResult("V1", True, "", covers=("A",)),
        CheckResult("V3", False, "", covers=("A",)),
    ]
    confidence = for_field("A", mixed)
    assert confidence.score < for_field("A", mixed[:1]).score
    assert not confidence.verified


# --- over the corpus ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def verified():
    return run()


@pytest.mark.corpus
class TestCorpus:
    def test_the_closing_date_the_form_prints_is_found(self, verified):
        from liasse.corpus.loader import iter_pages

        pages = list(iter_pages(verified[0].document))
        assert printed_closing_date(pages)

    def test_pass_rates_do_not_regress(self, verified):
        """A floor, versioned. Raising it is a result; lowering it needs a reason."""
        rates = pass_rates(verified)
        assert rates["V1"]["passed"] == rates["V1"]["ran"] >= 8
        assert rates["V2a"]["rate"] == 1.0
        assert rates["V2b"]["rate"] == 1.0
        assert rates["V2c"]["rate"] == 1.0
        assert rates["V3"]["ran"] >= 10

    def test_v3_reports_the_disagreement_between_two_filings(self, verified):
        """504304205 states total assets of 1 807 858 for the 2016 exercise and restates
        it as 1 807 435 a year later. Both filings are internally consistent; they
        disagree with each other by 423 euros."""
        failures = [
            r for doc in verified for r in doc.results if r.check_id == "V3" and not r.passed
        ]
        assert failures
        assert all(abs(r.delta) == 423 for r in failures)

    def test_no_value_is_contradicted_by_a_check_it_covers(self, verified):
        contradicted = [
            (doc.document.doc_id[:8], key)
            for doc in verified
            for key, c in doc.confidence.items()
            if c.failed
        ]
        assert not contradicted, f"contradicted values: {contradicted}"

    def test_money_never_became_a_float_anywhere(self, verified):
        for doc in verified:
            for typed in doc.values.values():
                assert isinstance(typed.value, int | Decimal)


def test_the_runner_imports_the_checks_itself():
    """The bug this encodes actually happened: `run()` returned a clean sheet over nothing
    because the decorators had never executed.

    It has to be checked statically. Any test that exercises `run()` has imported the
    checks itself by then, so the registry is populated in the test process whether or not
    the runner would have populated it in production.
    """
    import ast

    from liasse import paths

    source = (paths.REPO_ROOT / "src" / "liasse" / "verify" / "runner.py").read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert any(
        m.startswith("liasse.verify") and "checks" in m or m == "liasse.verify" for m in imported
    ), "runner.py must import liasse.verify.checks for the registry to be populated"
