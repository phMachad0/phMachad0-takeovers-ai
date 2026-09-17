"""The checks themselves.

Three families, and what matters is that they are independent of one another: one compares
two pages of the same filing, one compares a total with its own terms, and one compares two
filings deposited years apart. A value that survives all three was not read consistently
wrong three times in the same way.
"""

from __future__ import annotations

from liasse.verify.registry import (
    CheckResult,
    DocumentFacts,
    Scope,
    check,
    compare,
)


@check(
    "V1",
    Scope.DOCUMENT,
    "total assets on form 2050 equals total equity and liabilities on form 2051",
)
def balance_identity(facts: DocumentFacts) -> list[CheckResult]:
    """The check the brief points at: "it must reconcile against the other side".

    Two different pages, two different anchors, one number. It catches a misread digit, a
    column taken from the wrong place, and a unit applied to one side only - the last of
    which shows up as a factor of a thousand rather than as a small delta.
    """
    assets = facts.value("BS_TOTAL_ASSETS_FRGAAP")
    liabilities = facts.codes.get("EE")
    if assets is None or liabilities is None:
        return []
    return [
        compare(
            "V1",
            assets,
            liabilities,
            terms=1,
            detail="total assets vs total equity and liabilities",
            covers=("BS_TOTAL_ASSETS_FRGAAP",),
        )
    ]


@check("V2a", Scope.DOCUMENT, "domestic plus export revenue equals total revenue")
def revenue_split(facts: DocumentFacts) -> list[CheckResult]:
    france, export = facts.codes.get("FJ"), facts.codes.get("FK")
    total = facts.value("PL_REVENUE_FRGAAP")
    if france is None or export is None or total is None:
        return []
    return [
        compare(
            "V2a",
            france + export,
            total,
            terms=2,
            detail="FJ + FK vs FL",
            covers=("PL_REVENUE_FRGAAP",),
        )
    ]


@check("V2b", Scope.DOCUMENT, "financial income minus financial expense equals the result")
def financial_result(facts: DocumentFacts) -> list[CheckResult]:
    income, expense = facts.codes.get("GP"), facts.codes.get("GU")
    result = facts.value("PL_FINANCIAL_RESULTS_FRGAAP")
    if income is None or expense is None or result is None:
        return []
    return [
        compare(
            "V2b",
            income - expense,
            result,
            terms=2,
            detail="GP - GU vs GV",
            covers=("PL_FINANCIAL_RESULTS_FRGAAP",),
        )
    ]


@check("V2c", Scope.DOCUMENT, "the bottom line of form 2053 equals the result on form 2051")
def bottom_line(facts: DocumentFacts) -> list[CheckResult]:
    """`HN` is computed from every product and charge of the income statement; `DI` is
    carried onto the balance sheet. They meet only if both statements were read right."""
    profit_or_loss, on_balance = facts.codes.get("HN"), facts.codes.get("DI")
    if profit_or_loss is None or on_balance is None:
        return []
    return [compare("V2c", profit_or_loss, on_balance, terms=1, detail="HN vs DI")]


@check("V0", Scope.DOCUMENT, "the registry's closing date matches the one printed")
def closing_date(facts: DocumentFacts) -> list[CheckResult]:
    """Costs nothing and guards a required field of the deliverable.

    `fiscal_year_end` is taken from the registry's index entry rather than parsed out of
    the PDF, which is a saving worth having and a single point of failure worth checking:
    the form prints the same date, and the two were produced by different parties.
    """
    if not facts.fiscal_year_end or not facts.printed_closing_date:
        return []
    agree = facts.fiscal_year_end == facts.printed_closing_date
    return [
        CheckResult(
            check_id="V0",
            passed=agree,
            detail=f"registry says {facts.fiscal_year_end}, the form prints "
            f"{facts.printed_closing_date}",
        )
    ]


@check("V3", Scope.COMPANY, "the previous-year column restates the year before's filing")
def cross_year(earlier: DocumentFacts, later: DocumentFacts) -> list[CheckResult]:
    """The strongest of the three, and the one the brief hands over.

    Every filing restates the exercise before it in its own N-1 column, so two documents
    deposited a year apart state the same quantities twice - independently typed, scanned
    and read. Agreement here is not self-consistency; it is two sources meeting.
    """
    results = []
    for code, current in earlier.codes.items():
        restated = later.codes_previous.get(code)
        if restated is None:
            continue
        results.append(
            compare(
                "V3",
                current,
                restated,
                terms=1,
                detail=f"{code} in {earlier.fiscal_year_end} vs its restatement in "
                f"{later.fiscal_year_end}",
            )
        )
    return results


# The two formats round independently - the liasse is filled in whole euros, the plaquette
# prints figures rounded from centimes - so a term may legitimately differ by a unit in
# each. Measured across the three filings that carry both: every genuine agreement is
# exact or off by one, and the single real disagreement is off by 3 045.
def _format_tolerance(field_key: str, facts: DocumentFacts) -> int:
    typed = facts.fields.get(field_key)
    terms = len(typed.raw.components) if typed is not None else 1
    return max(1, terms)


@check("V4", Scope.DOCUMENT, "the liasse and the plaquette of one filing say the same thing")
def format_agreement(facts: DocumentFacts) -> list[CheckResult]:
    """Two extractors, two printings, one number.

    Three filings in scope carry both the DGFiP form and the accountant's own presentation
    of the same exercise. They were typeset by different software from the same ledger, and
    they are read here by two pipelines that share no anchoring logic: one follows the
    two-letter line codes, the other recovers a column grid from geometry and matches French
    labels. Nothing is common to both but the underlying fact.

    That makes this the strongest check in the suite. The others compare a document with
    itself - a total against its own terms, one page against another page of the same form.
    This one compares a document with an independent statement of the same thing, and it is
    the only check that can catch a value both pages of a form agree on and both get wrong.
    """
    results = []
    for field_key, plaquette in sorted(facts.fields_plaquette.items()):
        liasse = facts.value(field_key)
        if liasse is None:
            continue
        tolerance = _format_tolerance(field_key, facts)
        delta = liasse - plaquette.value
        results.append(
            CheckResult(
                check_id="V4",
                passed=abs(delta) <= tolerance,
                detail=(
                    f"{field_key}: liasse {liasse} vs plaquette {plaquette.value}"
                    + (f", off by {delta}" if delta else "")
                ),
                covers=(field_key,),
                delta=delta,
                tolerance=tolerance,
            )
        )
    return results


@check("V1b", Scope.DOCUMENT, "a plaquette's own two sides balance against each other")
def plaquette_balance(facts: DocumentFacts) -> list[CheckResult]:
    """V1 for the filings that have no line codes for V1 to use.

    The same identity the brief points at - total assets reconcile with the other side of
    the balance sheet - read off two different pages of the accountant's presentation,
    through two different column grids recovered independently. Without it the seven
    plaquette-only filings would carry values no check had ever looked at.
    """
    assets = facts.value("BS_TOTAL_ASSETS_FRGAAP")
    liabilities = facts.terms_plaquette.get("PQ_TOTAL_PASSIF")
    if assets is None or liabilities is None:
        return []
    return [
        compare(
            "V1b",
            assets,
            liabilities,
            terms=2,
            detail="total assets vs total liabilities and equity, both off the plaquette",
            covers=("BS_TOTAL_ASSETS_FRGAAP",),
        )
    ]
