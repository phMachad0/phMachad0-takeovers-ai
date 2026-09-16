"""Re-reading the values the deterministic path could not settle, and refusing most of them.

Escalation is cheap to start and expensive to get wrong, so the whole module is built around
one rule:

    **A value that came from a model is emitted only if a check that was computed from other
    figures, on other pages, agrees with it.**

That is stricter than "re-verify and drop what fails". It also drops what nothing could
check. The reason is that a vision model's failure mode is not a missing answer, it is a
well-formed plausible one, and the pipeline has no way to tell the two apart except by
confronting the answer with arithmetic the model did not see. A figure with no check behind
it is exactly the thing the rest of this project exists not to ship - it would arrive with a
provenance box and a confidence score and be indistinguishable from a reading.

The consequence is deliberate and worth stating: on this corpus, the filing whose OCR is
scrambled would need its total-liabilities row escalated as well before its total-assets
figure could be accepted, because V1b compares the two. One escalated value alone verifies
nothing. That is a limit of the check set, not of the model, and the report names it.

**Nothing here has ever made a real call.** No credential exists in this repository. The
path is exercised end to end against a stub transport, which is also how the suite can
assert that no test ever constructs the real client.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from liasse.corpus.loader import iter_pages, page_geometry
from liasse.corpus.models import Document, Token
from liasse.cost.meter import Call, TokenLedger
from liasse.cost.vlm import DEFAULT_RENDER_DPI
from liasse.extract.base import Anchoring, Component, RawValue, Tier
from liasse.fields.catalog import BY_KEY
from liasse.fields.plaquette import BY_KEY as PLAQUETTE_BY_KEY
from liasse.geometry.coords import to_pixels
from liasse.routing.classifier import classify_document
from liasse.text.lines import PositionedToken
from liasse.units.resolver import TypedValue, UnitEvidence
from liasse.verify.registry import CheckResult, Scope, checks_for
from liasse.verify.runner import VerifiedDocument
from liasse.vlm.client import Settings, Transport
from liasse.vlm.contract import Answer, Question, RefusedAnswer, parse
from liasse.vlm.render import MEDIA_TYPE, render

# The workforce is the one field with no plaquette catalogue entry, so its statement is
# named here rather than derived.
WORKFORCE_STATEMENT = "WORKFORCE"


def statements_for(field_key: str) -> tuple[str, ...]:
    """Which kind of page this field could be on, as the router labels pages."""
    spec = PLAQUETTE_BY_KEY.get(field_key)
    if spec is not None:
        return spec.statements
    return (WORKFORCE_STATEMENT,)


@dataclass(frozen=True, slots=True)
class Target:
    document: Document
    field_key: str
    page: int
    reason: str


@dataclass(frozen=True, slots=True)
class Outcome:
    """What happened to one question. Every one of these lands in the report."""

    target: Target
    accepted: bool
    why: str
    value: int | None = None
    call: Call | None = None


def targets_for(verified: VerifiedDocument, pages: Sequence) -> list[Target]:
    """The fields worth paying to re-read: the absent ones and the contradicted ones."""
    routed = classify_document(verified.document, pages)
    by_statement: dict[str, list[int]] = {}
    for page in routed.relevant_pages:
        if page.statement:
            by_statement.setdefault(page.statement, []).append(page.page)

    targets: list[Target] = []
    for field_key in BY_KEY:
        if "__" in field_key:
            continue
        typed = verified.values.get(field_key)
        if typed is None:
            reason = "absent: no anchor resolved on any routed page"
        elif verified.confidence[field_key].failed:
            failed = ", ".join(verified.confidence[field_key].failed)
            reason = f"contradicted by {failed}"
        else:
            continue

        for statement in statements_for(field_key):
            for page in by_statement.get(statement, []):
                targets.append(Target(verified.document, field_key, page, reason))
                break  # one page per statement; a null answer is what a wrong page costs
    return targets


def _as_typed(answer: Answer, document: Document, model: str) -> TypedValue | None:
    """A model's answer, in the same shape as a value read off the page.

    The synthetic token is the honest part: there is no OCR token behind this figure, so
    the box the model claimed becomes the box the value carries, converted from the
    normalised fractions it answered in into the pixel space every other component uses.
    Provenance that came from the model is labelled Tier.VLM wherever it travels.
    """
    if answer.value is None or answer.bbox is None:
        return None
    geometry = page_geometry(document, answer.page)
    pixels = to_pixels(answer.bbox, geometry.width_pt, geometry.height_pt)
    polygon = (
        (pixels.x0, pixels.y0),
        (pixels.x1, pixels.y0),
        (pixels.x1, pixels.y1),
        (pixels.x0, pixels.y1),
    )
    token = PositionedToken(
        token=Token(text=answer.snippet, polygon=polygon, score=1.0),
        x=pixels.x0,
        y=pixels.y0,
    )
    raw = RawValue(
        field_key=answer.field_key,
        value=answer.value,
        page=answer.page,
        unit=BY_KEY[answer.field_key].unit,
        components=(
            Component(
                code=f"VLM:{model}",
                value=answer.value,
                page=answer.page,
                tokens=(token,),
                anchoring=Anchoring(
                    tier=Tier.VLM,
                    form="VLM",
                    code=answer.field_key,
                    matched_label=answer.snippet,
                ),
            ),
        ),
    )
    return TypedValue(
        raw=raw,
        unit=raw.unit,
        evidence=UnitEvidence(
            rule="escalated to a vision model; the unit is the one the field is defined in",
        ),
    )


def _covering(results: Iterable[CheckResult], field_key: str) -> list[CheckResult]:
    return [r for r in results if field_key in r.covers]


def _verdict(results: Sequence[CheckResult], field_key: str) -> tuple[bool, str]:
    """Accept only on positive evidence."""
    covering = _covering(results, field_key)
    if not covering:
        return False, "no check covers this field, so nothing could confirm the reading"
    failed = [r for r in covering if not r.passed]
    if failed:
        return False, f"rejected by {', '.join(sorted({r.check_id for r in failed}))}"
    return True, f"confirmed by {', '.join(sorted({r.check_id for r in covering}))}"


@dataclass(slots=True)
class Escalation:
    """The result of a run: what was accepted, and what everything cost."""

    outcomes: list[Outcome] = field(default_factory=list)
    accepted: dict[str, dict[str, TypedValue]] = field(default_factory=dict)
    # The checks as they stood after the accepted values were substituted in, per document.
    # The caller needs them to give an escalated value the same confidence score as any
    # other: derived from how many independent checks agreed, never from the model.
    results: dict[str, list[CheckResult]] = field(default_factory=dict)
    ledger: TokenLedger = field(default_factory=TokenLedger)
    stopped_at_cap: bool = False


def run(
    verified: Sequence[VerifiedDocument],
    transport: Transport,
    settings: Settings,
    dpi: int = DEFAULT_RENDER_DPI,
) -> Escalation:
    """Ask, parse, re-check, and keep only what a check confirms."""
    escalation = Escalation()
    calls = 0

    for document_result in verified:
        if document_result.facts is None:
            continue
        pages = list(iter_pages(document_result.document))
        kept: dict[str, TypedValue] = {}

        for target in targets_for(document_result, pages):
            if calls >= settings.max_pages:
                escalation.stopped_at_cap = True
                break

            question = _question(target)
            image = render(target.document, target.page, dpi)
            completion = transport.ask(image.png, MEDIA_TYPE, question.prompt)
            calls += 1
            call = escalation.ledger.record(
                label=f"{target.document.doc_id[:8]} p{target.page} {target.field_key}",
                model=completion.model,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )

            try:
                answer = parse(completion.text, question)
            except RefusedAnswer as refusal:
                escalation.outcomes.append(
                    Outcome(target, False, f"answer refused: {refusal}", call=call)
                )
                continue

            typed = _as_typed(answer, target.document, completion.model)
            if typed is None:
                not_here = "the model said the figure is not on this page"
                escalation.outcomes.append(Outcome(target, False, not_here, call=call))
                continue

            facts = dataclasses.replace(
                document_result.facts,
                fields={**document_result.facts.fields, **kept, target.field_key: typed},
            )
            results = [r for check in checks_for(Scope.DOCUMENT) for r in check.run(facts)]
            accepted, why = _verdict(results, target.field_key)
            if accepted:
                kept[target.field_key] = typed
            escalation.outcomes.append(
                Outcome(target, accepted, why, value=answer.value, call=call)
            )

        if kept:
            doc_id = document_result.document.doc_id
            escalation.accepted[doc_id] = kept
            final = dataclasses.replace(
                document_result.facts,
                fields={**document_result.facts.fields, **kept},
            )
            escalation.results[doc_id] = [
                r for check in checks_for(Scope.DOCUMENT) for r in check.run(final)
            ]

    return escalation


def _question(target: Target) -> Question:
    labels = _LABELS.get(target.field_key, (target.field_key, target.field_key))
    return Question(
        field_key=target.field_key,
        label_fr=labels[0],
        label_en=labels[1],
        doc_id=target.document.doc_id,
        page=target.page,
        reason=target.reason,
    )


def _load_labels() -> dict[str, tuple[str, str]]:
    """The French and English labels the challenge itself ships, not ones invented here."""
    import json

    from liasse import paths

    definitions = json.loads(paths.FIELD_DEFS.read_text(encoding="utf-8"))
    return {f["field_key"]: (f["label_fr"], f["label_en"]) for f in definitions["fields"]}


_LABELS = _load_labels()
