"""Assembling the facts a check needs, and running every registered check over them."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from liasse.corpus.loader import iter_pages, iter_scope
from liasse.corpus.models import Document, OcrPage
from liasse.extract.base import RawValue
from liasse.extract.liasse import extract, read_codes
from liasse.extract.plaquette import extract as extract_plaquette
from liasse.extract.plaquette import read_terms
from liasse.fields.checks import CHECK_ANCHORS
from liasse.fields.plaquette import BS_LIABILITIES, TOTAL_LIABILITIES
from liasse.routing.classifier import classify_document
from liasse.units.resolver import TypedValue, resolve
from liasse.verify.confidence import Confidence, for_field
from liasse.verify.registry import CheckResult, DocumentFacts, Scope, checks_for

# Imported for its side effect: the checks register themselves on import, and without this
# the registry is empty and every run reports a clean sheet having verified nothing.
from liasse.verify import checks as _checks  # noqa: F401  (isort: skip)

# "Exercice N clos le  30/04/2023", "Exercice clos au : 30/06/2022".
_CLOSING = re.compile(r"clos\w*\s*(?:le|au)?\s*[,:.]?\s*(\d{2})[/.](\d{2})[/.](\d{4})", re.I)


def printed_closing_date(pages: list[OcrPage]) -> str | None:
    """The closing date the form prints, wherever the OCR split it.

    "Exercice N clos le," and "30/04/2023" arrive as two separate tokens, so the search
    runs over the page's text rather than over each token: the phrase and its date are one
    statement however the detector chose to cut them.
    """
    for page in pages:
        text = " ".join(t.text for t in page.tokens)
        match = _CLOSING.search(text)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}"
    return None


@dataclass(frozen=True, slots=True)
class VerifiedDocument:
    document: Document
    values: dict[str, TypedValue]
    results: list[CheckResult]
    confidence: dict[str, Confidence] = field(default_factory=dict)


def _facts(document: Document) -> tuple[DocumentFacts, dict[str, TypedValue]] | None:
    """Read one filing with whichever extractors its pages call for.

    A filing can carry both formats, and three in scope do. Where it does, the liasse
    reading is the one reported: it is anchored on line codes fixed by law rather than on
    printed words, and the arithmetic checks of the form apply to it. The plaquette reading
    is kept beside it and spent on V4 instead of being merged away. Where a filing carries
    only plaquette pages - seven of the fifteen - that reading is what there is, and it is
    reported.
    """
    pages = list(iter_pages(document))
    routed = classify_document(document, pages)
    forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
    statements = {
        p.page: p.statement
        for p in routed.relevant_pages
        if p.kind == "plaquette" and p.statement
    }
    if not (forms or statements):
        return None

    selected = [p for p in pages if p.page in forms]
    raw = [v for v in extract(selected, forms) if isinstance(v, RawValue)] if forms else []
    typed = {t.field_key: t for t in resolve(raw, document, pages)}

    plaquette_pages = [p for p in pages if p.page in statements]
    raw_plaquette = (
        [v for v in extract_plaquette(plaquette_pages, statements) if isinstance(v, RawValue)]
        if statements
        else []
    )
    typed_plaquette = {t.field_key: t for t in resolve(raw_plaquette, document, pages)}

    reported = dict(typed)
    for key, value in typed_plaquette.items():
        reported.setdefault(key, value)

    # Restricted to the liabilities pages on purpose: the asset page of the same filing
    # prints "TOTAL GENERAL" too, and reading that one would compare a number with itself.
    liabilities_pages = {p: s for p, s in statements.items() if s == BS_LIABILITIES}
    terms_plaquette = {
        k: c.value
        for k, c in read_terms(
            [p for p in pages if p.page in liabilities_pages],
            liabilities_pages,
            (TOTAL_LIABILITIES,),
        ).items()
    }

    codes = {k: c.value for k, c in read_codes(selected, forms, CHECK_ANCHORS).items()}
    previous = {
        k: c.value for k, c in read_codes(selected, forms, CHECK_ANCHORS, previous=True).items()
    }
    return (
        DocumentFacts(
            doc_id=document.doc_id,
            siren=document.siren,
            fiscal_year_end=document.fiscal_year_end,
            fields=reported,
            # Only where the filing carries both. On a plaquette-only filing the two
            # dictionaries are the same object's contents, and a check comparing a value
            # with itself passes every time while verifying nothing - which is the failure
            # E7 already walked into once.
            fields_plaquette=typed_plaquette if forms else {},
            codes=codes,
            terms_plaquette=terms_plaquette,
            codes_previous=previous,
            printed_closing_date=printed_closing_date(selected or plaquette_pages),
        ),
        reported,
    )


def run() -> list[VerifiedDocument]:
    """Run every check over every liasse document in scope."""
    prepared: list[tuple[Document, DocumentFacts, dict[str, TypedValue]]] = []
    for document in iter_scope():
        built = _facts(document)
        if built is not None:
            prepared.append((document, built[0], built[1]))

    per_document: dict[str, list[CheckResult]] = {f.doc_id: [] for _, f, _ in prepared}

    for _, facts, _ in prepared:
        for check in checks_for(Scope.DOCUMENT):
            per_document[facts.doc_id].extend(check.run(facts))

    # Cross-year checks belong to both filings: a disagreement does not say which of the
    # two is wrong, so neither gets to claim the check passed on its own.
    for _, earlier, _ in prepared:
        for _, later, _ in prepared:
            if earlier.siren != later.siren or earlier.doc_id == later.doc_id:
                continue
            if not (earlier.fiscal_year_end and later.fiscal_year_end):
                continue
            if int(later.fiscal_year_end[:4]) - int(earlier.fiscal_year_end[:4]) != 1:
                continue
            for check in checks_for(Scope.COMPANY):
                results = check.run(earlier, later)
                per_document[earlier.doc_id].extend(results)
                per_document[later.doc_id].extend(results)

    out = []
    for document, facts, typed in prepared:
        results = per_document[facts.doc_id]
        out.append(
            VerifiedDocument(
                document=document,
                values=typed,
                results=results,
                confidence={key: for_field(key, results) for key in typed},
            )
        )
    return out


def pass_rates(documents: list[VerifiedDocument]) -> dict[str, dict]:
    """Per check: how often it could run, and how often it agreed."""
    counts: dict[str, Counter] = {}
    for verified in documents:
        for result in verified.results:
            counts.setdefault(result.check_id, Counter())
            counts[result.check_id]["ran"] += 1
            counts[result.check_id]["passed"] += int(result.passed)
    return {
        check_id: {
            "ran": c["ran"],
            "passed": c["passed"],
            "rate": round(c["passed"] / c["ran"], 4) if c["ran"] else None,
        }
        for check_id, c in sorted(counts.items())
    }
