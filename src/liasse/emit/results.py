"""Building results.json, the file the challenge is actually read from.

Two rules govern what goes in it.

*Absence is reported, never invented.* financial_fields.json is explicit - "If a field is
genuinely absent from a document, omit it rather than reporting 0" - and the brief is
explicit about why it matters: a pipeline that reports all twelve with three silently wrong
is worth less than one that reports six and says so. So a field the pipeline could not read
is left out, and the reason it is missing travels with the document.

*Every value carries where it was read.* The bbox is the union of the tokens the value was
assembled from, converted to the normalised fractions the schema requires. It is not a
field filled in at the end; it is what is left over from never having discarded the tokens.
"""

from __future__ import annotations

from decimal import Decimal

from liasse import paths
from liasse.corpus.loader import iter_pages, load_document
from liasse.corpus.models import Document
from liasse.corpus.scope import SCOPE
from liasse.fields.catalog import BY_KEY
from liasse.geometry.boxes import BBox, union
from liasse.geometry.coords import to_normalized
from liasse.units.resolver import TypedValue
from liasse.verify.confidence import Confidence
from liasse.verify.runner import VerifiedDocument

# Boxes are rounded so the file stays readable. Four decimals on a 3500 px page is a third
# of a pixel - far below anything a reviewer could see, and it matches what the challenge's
# own bbox_viewer prints.
BBOX_DECIMALS = 4


def _number(value: int | Decimal) -> int | float:
    return value if isinstance(value, int) else float(value)


def _normalized_bbox(
    typed: TypedValue, geometry_by_page: dict[int, tuple[float, float]]
) -> BBox | None:
    """Union of every token that contributed, in the units the schema asks for.

    Tokens from more than one page cannot share a box, so the union is taken over the page
    the value is reported on; the others stay visible in `components`.
    """
    page = typed.raw.page
    size = geometry_by_page.get(page)
    if size is None:
        return None
    boxes = [c.bbox for c in typed.raw.components if c.page == page]
    if not boxes:
        return None
    return to_normalized(union(boxes), *size)


def _component_entry(component, geometry_by_page: dict[int, tuple[float, float]]) -> dict:
    size = geometry_by_page.get(component.page)
    entry = {
        "code": component.code,
        "value": _number(component.value),
        "page": component.page,
        "tier": component.anchoring.tier.name,
    }
    if component.blank:
        # The row was found and its cell is empty. On a French form that is nil, which is
        # a fact about the company rather than a gap in the reading.
        entry["blank"] = True
    if size:
        box = to_normalized(component.bbox, *size)
        entry["bbox"] = [round(v, BBOX_DECIMALS) for v in box]
    return entry


def _field_entry(
    typed: TypedValue,
    confidence: Confidence,
    geometry_by_page: dict[int, tuple[float, float]],
    variant: TypedValue | None,
) -> dict | None:
    box = _normalized_bbox(typed, geometry_by_page)
    if box is None:
        return None

    entry: dict = {
        "field_key": typed.field_key,
        "value": _number(typed.value),
        "unit": typed.unit,
        "page": typed.raw.page,
        "bbox": [round(v, BBOX_DECIMALS) for v in box],
        "snippet": typed.raw.snippet[:120],
        "confidence": confidence.score,
        # Extras, allowed by the schema. Each answers a question the required fields
        # cannot: how the row was found, what a derived value is made of, why the unit is
        # what it is, and which checks the figure survived.
        "extraction": {
            "tier": typed.raw.tier.name,
            "components": [_component_entry(c, geometry_by_page) for c in typed.raw.components],
        },
        "unit_evidence": {
            "rule": typed.evidence.rule,
            "rejected_markers": list(typed.evidence.rejected_markers),
        },
        "verification": {
            "checks_passed": list(confidence.passed),
            "checks_failed": list(confidence.failed),
        },
    }
    if typed.evidence.anchor is not None:
        entry["unit_evidence"]["anchor"] = {
            "amount": typed.evidence.anchor.amount,
            "currency": typed.evidence.anchor.currency,
            "page": typed.evidence.anchor.page,
            "snippet": typed.evidence.anchor.snippet,
        }
    if typed.evidence.note:
        entry["unit_evidence"]["note"] = typed.evidence.note

    spec = BY_KEY.get(typed.field_key)
    if spec is not None and spec.variant_key and variant is not None:
        # The schema's label_fr and notes disagree about what this field means, so both
        # readings are emitted and the disagreement is named. See ADR-002.
        entry["schema_ambiguity"] = {
            "reading_used": typed.field_key,
            "alternative_key": spec.variant_key,
            "alternative_value": _number(variant.value),
        }
    return entry


def _relative_pdf(document: Document) -> str:
    return str(document.pdf_path.relative_to(paths.REPO_ROOT))


def build_documents(verified: list[VerifiedDocument]) -> list[dict]:
    """One entry per filing in scope, processed or not."""
    processed = {v.document.doc_id: v for v in verified}
    out = []

    for entry in SCOPE:
        verified_doc = processed.get(entry.doc_id)
        document = verified_doc.document if verified_doc else load_document(entry)

        record: dict = {
            "pdf": _relative_pdf(document),
            "siren": document.siren,
            "fiscal_year_end": document.fiscal_year_end,
            "fields": [],
        }

        if verified_doc is None:
            # Listed rather than omitted: a reader of this file should see all fifteen and
            # be told which were left, instead of having to notice some are missing.
            record["not_processed"] = (
                "no page of this filing was routed to a statement either extractor could "
                "read."
            )
            out.append(record)
            continue

        geometry_by_page = {
            p.geometry.page: (p.geometry.width_pt, p.geometry.height_pt)
            for p in iter_pages(document)
        }
        values = verified_doc.values

        for key in BY_KEY:
            typed = values.get(key)
            if typed is None:
                continue
            spec = BY_KEY[key]
            variant = values.get(spec.variant_key) if spec.variant_key else None
            field = _field_entry(typed, verified_doc.confidence[key], geometry_by_page, variant)
            if field is not None:
                record["fields"].append(field)

        emitted = {f["field_key"] for f in record["fields"]}
        absent = [k for k in BY_KEY if k not in emitted]
        if absent:
            record["fields_absent"] = absent
        if not record["fields"]:
            # Routed, read, and nothing came back. Saying so is the point: a filing that
            # silently contributes an empty list looks identical to one that was never
            # reached, and the two are different failures.
            record["not_processed"] = (
                "pages were routed but no field could be read from them. The OCR returns "
                "this filing's tables in a scrambled reading order, so the rows do not "
                "reconstruct and no column grid is recoverable."
            )
        out.append(record)

    return out


def build(
    verified: list[VerifiedDocument], run_block: dict, documents: list[dict] | None = None
) -> dict:
    """The whole file, ready to write at the repository root.

    ``documents`` can be passed in already built. The caller that measures the run needs
    to time that work and then report the timing inside this file, which it cannot do if
    building the documents is hidden in here.
    """
    documents = build_documents(verified) if documents is None else documents
    processed = [d for d in documents if "not_processed" not in d]
    return {
        "documents": documents,
        "run": run_block,
        "notes": (
            f"{sum(len(d['fields']) for d in documents)} values from "
            f"{len(processed)} of {len(documents)} filings. Two formats are read: the "
            "DGFiP liasse, anchored on the two-letter line codes fixed by law, and the "
            "plaquette - the accountant's own presentation, which prints no codes and is "
            "read by recovering the column grid from the page geometry and matching the "
            "printed French labels. Where a filing carries both, the liasse reading is "
            "the one reported and the plaquette reading is spent on check V4, which "
            "compares them. Of the fields absent from the filings that were processed, "
            "the six PL_* fields of two deposits are absent by law: those companies filed "
            "under the L.232-25 confidentiality option and the registry marks the deposit "
            "'Partiellement confidentiel'. Every value carries the checks it survived; "
            "those checks measure agreement between statements the documents make more "
            "than once, not truth."
        ),
    }
