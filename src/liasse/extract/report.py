"""What the extraction produced, and how it was grounded.

Reports coverage against three separate denominators, because "75 of 96" on its own hides
the question the brief actually asks: a field that is not in the document is not a failure
of the pipeline, and saying which is which is most of the answer.
"""

from __future__ import annotations

from collections import Counter

from liasse.corpus.models import Document
from liasse.extract.base import MissingValue, RawValue


def document_summary(
    document: Document, values: list[RawValue | MissingValue], confidential_pl: bool
) -> dict:
    read = [v for v in values if isinstance(v, RawValue) and "__" not in v.field_key]
    missing = [v for v in values if isinstance(v, MissingValue) and "__" not in v.field_key]
    return {
        "siren": document.siren,
        "doc_id": document.doc_id,
        "denomination": document.denomination,
        "fiscal_year_end": document.fiscal_year_end,
        "income_statement_confidential": confidential_pl,
        "fields_read": len(read),
        "tiers": dict(Counter(v.tier.name for v in read)),
        "blank_cells_read_as_zero": sum(1 for v in read for c in v.components if c.blank),
        "values": [
            {
                "field_key": v.field_key,
                "value": float(v.value) if not isinstance(v.value, int) else v.value,
                "unit": v.unit,
                "page": v.page,
                "tier": v.tier.name,
                "components": [
                    {
                        "code": c.code,
                        "value": float(c.value) if not isinstance(c.value, int) else c.value,
                        "page": c.page,
                        "tier": c.anchoring.tier.name,
                        "blank": c.blank,
                    }
                    for c in v.components
                ],
                "snippet": v.snippet[:80],
            }
            for v in read
        ],
        "missing": [
            {
                "field_key": v.field_key,
                # A confidential filing is missing its income statement by law, not by
                # failure. Reporting the two the same way would be the dishonest answer.
                "reason": "legally_absent_confidential_income_statement"
                if confidential_pl and v.field_key.startswith("PL_")
                else v.reason,
            }
            for v in missing
        ],
    }


def build_report(documents: list[dict]) -> dict:
    read = sum(d["fields_read"] for d in documents)
    legal = sum(
        1 for d in documents for m in d["missing"] if m["reason"].startswith("legally_absent")
    )
    other = sum(len(d["missing"]) for d in documents) - legal
    expected = 12 * len(documents)
    return {
        "about": (
            "Field extraction over the liasse documents in scope. Coverage is reported "
            "against three denominators: fields read, fields absent from the filing by "
            "law, and fields the pipeline could not resolve."
        ),
        "totals": {
            "documents": len(documents),
            "fields_expected": expected,
            "fields_read": read,
            "fields_legally_absent": legal,
            "fields_unresolved": other,
            "coverage_of_available": round(read / (expected - legal), 4) if expected > legal else 0,
            "tiers": dict(
                Counter(tier for d in documents for tier, n in d["tiers"].items() for _ in range(n))
            ),
        },
        "documents": documents,
    }
