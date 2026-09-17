"""The plaquette extractor, against the corpus. Marked ``corpus``: these need data/."""

from __future__ import annotations

import pytest

from liasse.corpus.loader import iter_pages, iter_scope, load_document, load_page
from liasse.corpus.scope import SCOPE
from liasse.extract.base import RawValue
from liasse.extract.liasse import extract as extract_liasse
from liasse.extract.plaquette import current_column, extract, page_columns
from liasse.routing.classifier import classify_document

pytestmark = pytest.mark.corpus


def _document(prefix: str):
    entry = next(e for e in SCOPE if e.doc_id.startswith(prefix))
    return load_document(entry)


def _routed(prefix: str):
    document = _document(prefix)
    pages = list(iter_pages(document))
    routed = classify_document(document, pages)
    statements = {
        p.page: p.statement
        for p in routed.relevant_pages
        if p.kind == "plaquette" and p.statement
    }
    forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
    return document, pages, statements, forms


def _values(prefix: str) -> dict[str, RawValue]:
    _, pages, statements, _ = _routed(prefix)
    read = extract([p for p in pages if p.page in statements], statements)
    return {v.field_key: v for v in read if isinstance(v, RawValue)}


# --- golden values ----------------------------------------------------------------------


def test_share_capital_off_a_plaquette_balance_sheet():
    """820561470 p7 prints "Capital social ou individuel 10 000 10 000"."""
    value = _values("6493e437")["BS_CAPITAL_EQUITY_FRGAAP"]
    assert value.value == 10000
    assert value.page == 7
    assert value.tier.name == "LABEL"


def test_the_first_of_two_identical_columns_is_the_current_exercise():
    """Both columns of that row read 10 000, so the next year's filing is the real test.

    6543d3fd prints 150 000 for the exercise it reports and 10 000 for the year before,
    after a capital increase. Reading the wrong column returns last year's figure, which
    is a perfectly plausible number.
    """
    assert _values("6543d3fd")["BS_CAPITAL_EQUITY_FRGAAP"].value == 150000


def test_total_assets_is_the_net_column_not_the_gross_one():
    """6493e437 p6: TOTAL ACTIF reads 803 550 gross, 164 588 depreciation, 638 962 net.

    The gross figure is larger, entirely plausible, and wrong. It is also what reading the
    row left to right returns.
    """
    assert _values("6493e437")["BS_TOTAL_ASSETS_FRGAAP"].value == 638962


def test_cash_adds_the_two_rows_that_make_it_up():
    """DISPONIBILITES 307 199 plus VALEURS MOBILIERES DE PLACEMENT 525."""
    value = _values("6493e437")["BS_CASH_CURRENT_ASSET_FRGAAP"]
    assert value.value == 307724
    assert {c.code for c in value.components} == {"PQ_DISPONIBILITES", "PQ_VMP"}


def test_a_word_the_detector_cut_in_two_is_still_found():
    """63e8ebbb...7c p2 prints "Dispon bilités" - one word, two tokens, neither of which
    is within an edit of "disponibilités"."""
    value = _values("63e8ebbb54febda17c19ee7c")["BS_CASH_CURRENT_ASSET_FRGAAP"]
    assert value.value == 1545314  # 1 179 955 + 365 359
    assert {c.code for c in value.components} == {"PQ_DISPONIBILITES", "PQ_VMP"}


def test_a_stray_bracket_does_not_make_an_asset_negative():
    """63e8ebbb...7d p23 prints securities as "365 359)".

    The bracket is noise, but a bracket is also how this corpus prints a negative and the
    parser cannot tell the two apart. The row's own Brut - Amortissements = Net identity
    can, and does.
    """
    value = _values("63e8ebbb54febda17c19ee7d")["BS_CASH_CURRENT_ASSET_FRGAAP"]
    assert value.value == 2516919
    assert value.value > 0


def test_a_minus_glued_to_the_digits_is_read_as_a_minus():
    """63e8ebbb...7e p26 prints the financial result as "-76778", not "(76 778)"."""
    assert _values("63e8ebbb54febda17c19ee7e")["PL_FINANCIAL_RESULTS_FRGAAP"].value == -76778


def test_a_printed_total_is_preferred_to_one_we_assemble():
    """63e2481c prints "Chiffres d'affaires nets"; the reading that sums ventes and
    production vendue exists but must not be reached when the total is printed."""
    value = _values("63e2481c")["PL_REVENUE_FRGAAP"]
    assert value.value == 4978292
    assert [c.code for c in value.components] == ["PQ_CA_NET"]


def test_revenue_is_rebuilt_where_the_dialect_prints_no_total():
    """The condensed dialect has no net revenue line at all."""
    value = _values("63e8ebbb54febda17c19ee7c")["PL_REVENUE_FRGAAP"]
    assert value.value == 3875200  # 3 794 380 + 80 820
    assert {c.code for c in value.components} == {"PQ_VENTES", "PQ_PRODUCTION_VENDUE"}


# --- the negative cases -------------------------------------------------------------------


def test_the_percentage_column_is_never_read_as_a_value():
    """63e8ebbb p4 prints six columns: amount, %, amount N-1, %, variation, variation %.

    Revenue of 3 794 380 sits beside a 97,91 percentage, and the financial result of 357
    beside a 0,01 - so magnitude cannot tell them apart. What can: this dialect prints
    amounts in whole euros and percentages with a comma, so a value that came back with a
    fractional part came out of the wrong column.
    """
    values = _values("63e8ebbb54febda17c19ee7c")
    for key, value in values.items():
        assert isinstance(value.value, int), f"{key} read {value.value}, which is a percentage"
    assert values["PL_EXT_SERVICES_COSTS_FRGAAP"].value == 1182000
    assert values["PL_REVENUE_FRGAAP"].value == 3875200


def test_an_asset_page_that_cannot_be_confirmed_is_refused():
    """A three-column asset page whose columns do not satisfy Brut - Amort = Net gives no
    column at all, rather than the second-best guess."""
    document, pages, statements, _ = _routed("6860f28c")
    assets = [p for p, s in statements.items() if s == "BS_ASSETS"]
    assert assets, "expected this filing to have asset pages routed"
    refused = [
        page_columns(load_page(document, page), "BS_ASSETS").current is None for page in assets
    ]
    assert any(refused)


def test_the_filing_with_scrambled_reading_order_reports_nothing():
    """Absence over invention: this one is unreadable and says so."""
    assert _values("6860f28c") == {}


def test_a_liabilities_page_is_read_from_its_first_column():
    document, _, statements, _ = _routed("66cd893c")
    page = next(p for p, s in statements.items() if s == "BS_LIABILITIES")
    columns = page_columns(load_page(document, page), "BS_LIABILITIES")
    # Four columns: N, N-1, variation in euros, variation in percent. The variation
    # satisfies N - (N-1) = variation, which is the same arithmetic that identifies a Net
    # column on an asset page - so the statement, not the arithmetic, has to decide.
    assert len(columns.grid) == 4
    assert columns.current == 0
    assert current_column("BS_ASSETS", columns.lines, columns.grid) == 2


# --- the two extractors against each other -------------------------------------------------


def test_both_extractors_read_the_same_exercise_to_within_rounding():
    """The strongest evidence in the suite that either extractor is right.

    Three filings carry both the DGFiP form and the accountant's presentation of the same
    exercise. The two are read by pipelines sharing no anchoring logic - line codes on one
    side, geometry and French labels on the other - so agreement is not self-consistency.

    They round independently: the liasse is filled in whole euros and the plaquette prints
    figures rounded from centimes, so a term may differ by a unit. Anything wider is a real
    disagreement, and two of them are.
    """
    compared = agreed = 0
    wide: list[tuple[str, str, int]] = []

    for document in iter_scope():
        pages = list(iter_pages(document))
        routed = classify_document(document, pages)
        forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
        statements = {
            p.page: p.statement
            for p in routed.relevant_pages
            if p.kind == "plaquette" and p.statement
        }
        if not (forms and statements):
            continue

        left = {
            v.field_key: v
            for v in extract_liasse([p for p in pages if p.page in forms], forms)
            if isinstance(v, RawValue)
        }
        right = {
            v.field_key: v
            for v in extract([p for p in pages if p.page in statements], statements)
            if isinstance(v, RawValue)
        }
        for key in sorted(set(left) & set(right)):
            if "__" in key:
                continue
            compared += 1
            delta = left[key].value - right[key].value
            tolerance = max(1, len(left[key].components))
            if abs(delta) <= tolerance:
                agreed += 1
            else:
                wide.append((document.doc_id[:8], key, int(delta)))

    assert compared >= 20, f"only {compared} values could be compared across formats"
    assert agreed / compared >= 0.85, f"cross-format agreement fell to {agreed}/{compared}"
    assert sorted(k for _, k, _ in wide) == [
        "PL_DEPRECIATION_AMORTIZATION_FRGAAP",
        "PL_EXT_SERVICES_COSTS_FRGAAP",
    ], f"new cross-format disagreements: {wide}"
