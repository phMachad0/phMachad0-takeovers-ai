"""Turning a routing run into the numbers the README quotes.

Builds a plain dict and writes no files: the caller decides where it lands. That keeps
the layer free of I/O and makes the report testable without a filesystem.
"""

from __future__ import annotations

from collections import Counter

from liasse.routing.classifier import RoutedDocument


def document_summary(routed: RoutedDocument) -> dict:
    return {
        "siren": routed.document.siren,
        "doc_id": routed.document.doc_id,
        "denomination": routed.document.denomination,
        "fiscal_year_end": routed.document.fiscal_year_end,
        "format": routed.format,
        "income_statement_confidential": routed.income_statement_confidential,
        "n_pages": len(routed.pages),
        "n_relevant_pages": len(routed.relevant_pages),
        "kinds": dict(Counter(p.kind for p in routed.pages)),
        "relevant": [
            {
                "page": p.page,
                "kind": p.kind,
                "form": p.form,
                "statement": p.statement,
                "low_confidence": bool(p.signals.get("low_confidence")),
                "signals": p.signals,
            }
            for p in routed.relevant_pages
        ],
    }


def build_report(routed_documents: list[RoutedDocument]) -> dict:
    documents = [document_summary(r) for r in routed_documents]
    total_pages = sum(d["n_pages"] for d in documents)
    relevant_pages = sum(d["n_relevant_pages"] for d in documents)

    return {
        "about": (
            "Page routing over the 15 documents in scope. 'relevant' pages are those "
            "carrying at least one of the 12 fields. Everything else is court "
            "certificates, minutes, audit reports and annexe schedules."
        ),
        "totals": {
            "documents": len(documents),
            "pages": total_pages,
            "relevant_pages": relevant_pages,
            "relevant_share": round(relevant_pages / total_pages, 4) if total_pages else 0.0,
            "reduction_factor": round(total_pages / relevant_pages, 2) if relevant_pages else None,
            "kinds": dict(
                Counter(k for d in documents for k, n in d["kinds"].items() for _ in range(n))
            ),
            "statements": dict(Counter(r["statement"] for d in documents for r in d["relevant"])),
            "documents_with_confidential_income_statement": sum(
                1 for d in documents if d["income_statement_confidential"]
            ),
            "documents_carrying_both_formats": sum(
                1
                for d in documents
                if {r["kind"] for r in d["relevant"]} >= {"liasse", "plaquette"}
            ),
        },
        "documents": documents,
    }
