"""Deciding what each page is, and whether it is worth processing.

415 pages in scope, roughly 75 of which carry any of the 12 fields. Everything else is
court certificates, meeting minutes, audit reports, and annexe schedules. Classifying
first is what keeps the expensive paths off the other 340 - see
wiki/03-ideias/ideia-04-roteamento-de-paginas.md.

The classification is built from four independent signals, and the interesting cases are
where they disagree: a header with no codes means the code column was lost in the OCR,
which tells the extractor to fall back rather than report the field missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from liasse.corpus.models import Document, OcrPage
from liasse.routing import signals
from liasse.text.numbers import numeric_ratio

Kind = Literal["liasse", "plaquette", "prose", "blank"]
# Which financial statement a page carries, if any.
Statement = Literal["BS_ASSETS", "BS_LIABILITIES", "PL", "PL_CONT", "WORKFORCE"]

# Liasse forms that carry at least one of the 12 fields.
FORM_TO_STATEMENT: dict[str, Statement] = {
    "2050": "BS_ASSETS",
    "2051": "BS_LIABILITIES",
    "2052": "PL",
    "2053": "PL_CONT",
    "2058-C": "WORKFORCE",
}

# A page with fewer tokens than this carries no table: a cover sheet, a stamp, a scan of
# an empty verso. 10% of the pages in scope are entirely empty (wiki F012).
MAX_TOKENS_FOR_BLANK = 5


@dataclass(frozen=True, slots=True)
class PageClass:
    """What a page is, plus everything the decision was made from.

    ``signals`` is never discarded: it is what the routing report shows, and what makes a
    misclassification diagnosable without rerunning anything.
    """

    page: int
    kind: Kind
    form: str | None = None
    statement: Statement | None = None
    signals: dict = field(default_factory=dict)

    @property
    def carries_fields(self) -> bool:
        return self.statement is not None


@dataclass(frozen=True, slots=True)
class RoutedDocument:
    document: Document
    pages: tuple[PageClass, ...]
    # True when the registry marks the income statement as confidentially filed, in which
    # case the six PL_* fields are legally absent rather than missed (wiki F014).
    income_statement_confidential: bool = False

    @property
    def relevant_pages(self) -> tuple[PageClass, ...]:
        return tuple(p for p in self.pages if p.carries_fields)

    @property
    def format(self) -> Kind:
        """The document's dominant format, decided by its statement pages."""
        kinds = [p.kind for p in self.pages if p.carries_fields]
        if not kinds:
            # No statement page recognised: fall back to whatever the bulk of the
            # substantial pages look like, so the document is still labelled.
            kinds = [p.kind for p in self.pages if p.kind in ("liasse", "plaquette")]
        if not kinds:
            return "prose"
        return max(set(kinds), key=kinds.count)


def classify_page(page: OcrPage) -> PageClass:
    """Classify one page from its OCR alone."""
    tokens = page.tokens

    if len(tokens) <= MAX_TOKENS_FOR_BLANK:
        return PageClass(
            page=page.page,
            kind="blank",
            signals={"n_tokens": len(tokens)},
        )

    header = signals.header_form(tokens)
    codes = signals.code_fingerprint(tokens)
    fingerprint_form, overlap = signals.form_from_codes(codes)
    title = signals.plaquette_statement(tokens)

    evidence = {
        "n_tokens": len(tokens),
        "header_form": header,
        "n_codes": len(codes),
        "fingerprint_form": fingerprint_form,
        "fingerprint_overlap": overlap,
        "plaquette_title": title,
        "numeric_ratio": round(numeric_ratio(tokens), 3),
    }

    looks_like_liasse = header is not None or len(codes) >= signals.MIN_CODES_FOR_LIASSE
    if looks_like_liasse:
        # The header names the form precisely; the fingerprint only distinguishes the four
        # forms we hold signatures for. Prefer the header, fall back to the fingerprint.
        form = header or fingerprint_form
        if header and fingerprint_form and header != fingerprint_form:
            # Both spoke and disagreed. Keep the header but record the conflict: it means
            # one of the two is reading the wrong thing, and the report should show it.
            evidence["conflict"] = f"header={header} fingerprint={fingerprint_form}"
        if header and not codes:
            # The form is printed but the code column did not survive the OCR. The
            # extractor must not treat this as "no data" (wiki F009, F013).
            evidence["code_column_missing"] = True
        return PageClass(
            page=page.page,
            kind="liasse",
            form=form,
            statement=FORM_TO_STATEMENT.get(form or ""),
            signals=evidence,
        )

    if title is not None:
        evidence["statement_via"] = "title"
        return PageClass(page=page.page, kind="plaquette", statement=title, signals=evidence)

    return PageClass(page=page.page, kind="prose", signals=evidence)


def _recover_by_labels(pages: list[OcrPage], classified: list[PageClass]) -> list[PageClass]:
    """Last resort for a document whose section titles did not survive the OCR.

    Only one document in scope needs this: 445070311/6860f28c comes back with its reading
    order scrambled and no titles at all. Guessing from accounting labels is much weaker
    evidence than a printed title, and firing it on a document that already has titles
    would misread annexe schedules - a table of immobilisations mentions the same words a
    balance sheet does. So it runs only when nothing else found anything, and every page
    it produces is flagged low_confidence.
    """
    recovered: list[PageClass] = []
    for page, page_class in zip(pages, classified, strict=True):
        if page_class.carries_fields or page_class.kind == "blank":
            recovered.append(page_class)
            continue
        statement, hits = signals.statement_from_labels(page.tokens)
        if statement is None:
            recovered.append(page_class)
            continue
        evidence = dict(page_class.signals)
        evidence.update(statement_via="labels", label_hits=hits, low_confidence=True)
        recovered.append(
            PageClass(
                page=page_class.page,
                kind="plaquette",
                form=page_class.form,
                statement=statement,
                signals=evidence,
            )
        )
    return recovered


def classify_document(document: Document, pages: list[OcrPage]) -> RoutedDocument:
    classified = [classify_page(p) for p in pages]

    if not any(p.carries_fields for p in classified):
        classified = _recover_by_labels(pages, classified)

    return RoutedDocument(
        document=document,
        pages=tuple(classified),
        income_statement_confidential=signals.income_statement_is_confidential(document.meta),
    )
