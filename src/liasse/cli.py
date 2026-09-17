"""Command line entry point.

Subcommands are added as stages land. Today only ``doctor`` does real work; it is the
E0 acceptance check, and it stays useful afterwards as a environment smoke test.
"""

from __future__ import annotations

import argparse
import sys

from liasse import __version__, paths


def _doctor() -> int:
    """Report whether the environment can run the pipeline. Returns a process exit code."""
    problems: list[str] = []

    try:
        import pymupdf  # noqa: F401
    except ImportError:
        problems.append("pymupdf is not installed; page geometry cannot be read")

    try:
        import jsonschema  # noqa: F401
    except ImportError:
        problems.append("jsonschema is not installed; results.json cannot be validated")

    for label, path in (
        ("corpus", paths.DATA_DIR),
        ("results schema", paths.RESULTS_SCHEMA),
        ("field definitions", paths.FIELD_DEFS),
        ("bbox_viewer reference", paths.BBOX_VIEWER),
    ):
        if not path.exists():
            problems.append(f"{label} not found at {path}")

    from liasse.vlm.client import unavailable_because

    print(f"liasse {__version__}")
    print(f"repo root: {paths.REPO_ROOT}")
    # Not a problem: the deterministic pipeline is the whole deliverable and needs no
    # credential. Escalation is the optional extra, and doctor says whether it could run.
    blocked = unavailable_because()
    print(f"escalation: {'unavailable - ' + blocked if blocked else 'available'}")
    if problems:
        print("\nproblems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("environment OK")
    return 0


def _route() -> int:
    """Classify every page in scope and write the routing report."""
    import json

    from liasse.corpus.loader import iter_pages, iter_scope
    from liasse.routing.classifier import classify_document
    from liasse.routing.report import build_report

    routed = [classify_document(d, list(iter_pages(d))) for d in iter_scope()]
    report = build_report(routed)

    paths.REPORTS_DIR.mkdir(exist_ok=True)
    out = paths.REPORTS_DIR / "routing.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    totals = report["totals"]
    print(
        f"{totals['relevant_pages']} of {totals['pages']} pages carry fields "
        f"({totals['relevant_share']:.0%}, a {totals['reduction_factor']}x reduction)"
    )
    print(f"wrote {out.relative_to(paths.REPO_ROOT)}")
    return 0


def _extract() -> int:
    """Read the twelve fields off every liasse document in scope."""
    import json

    from liasse.corpus.loader import iter_pages, iter_scope
    from liasse.extract.base import RawValue
    from liasse.extract.liasse import extract
    from liasse.extract.plaquette import extract as extract_plaquette
    from liasse.extract.report import build_report, document_summary
    from liasse.extract.workforce import FIELD_KEY as WORKFORCE_KEY
    from liasse.extract.workforce import find as find_workforce
    from liasse.routing.classifier import classify_document

    summaries = []
    for document in iter_scope():
        pages = list(iter_pages(document))
        routed = classify_document(document, pages)
        forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
        statements = {
            p.page: p.statement
            for p in routed.relevant_pages
            if p.kind == "plaquette" and p.statement
        }
        if not (forms or statements):
            continue

        values = extract([p for p in pages if p.page in forms], forms) if forms else []
        # Same precedence as the verifier: where a filing carries both, the liasse reading
        # is the one reported and the plaquette only fills what the liasse did not give.
        read = {v.field_key for v in values if isinstance(v, RawValue)}
        if statements:
            for value in extract_plaquette([p for p in pages if p.page in statements], statements):
                if isinstance(value, RawValue) and value.field_key not in read:
                    values.append(value)
                    read.add(value.field_key)

        # The headcount stated in prose, when no form printed it. Searched over every page,
        # not the routed ones: it lives in the annexe, among pages the router discards.
        if WORKFORCE_KEY not in read:
            prose = find_workforce(pages)
            if prose is not None:
                values.append(prose)

        summaries.append(document_summary(document, values, routed.income_statement_confidential))

    report = build_report(summaries)
    paths.REPORTS_DIR.mkdir(exist_ok=True)
    out = paths.REPORTS_DIR / "extraction.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    totals = report["totals"]
    print(
        f"{totals['fields_read']} fields read from {totals['documents']} liasse documents; "
        f"{totals['fields_legally_absent']} legally absent, "
        f"{totals['fields_unresolved']} unresolved"
    )
    print(f"tiers: {totals['tiers']}")
    print(f"wrote {out.relative_to(paths.REPO_ROOT)}")
    return 0


def _verify() -> int:
    """Run every check over every liasse document and write the verification report."""
    import json

    from liasse.verify.report import build_report
    from liasse.verify.runner import run

    report = build_report(run())
    paths.REPORTS_DIR.mkdir(exist_ok=True)
    out = paths.REPORTS_DIR / "verification.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for check_id, stats in report["pass_rates"].items():
        print(f"  {check_id}: {stats['passed']}/{stats['ran']} = {stats['rate']:.0%}")
    totals = report["totals"]
    print(
        f"{totals['verified_by_at_least_one_check']} of {totals['fields']} values agree "
        f"with an independent check ({totals['share_verified']:.0%}); "
        f"{totals['contradicted']} contradicted, {totals['unverified']} unverified"
    )
    print(f"wrote {out.relative_to(paths.REPO_ROOT)}")
    return 0


def _emit() -> int:
    """Run the pipeline end to end and write the deliverable."""
    import json

    import jsonschema

    from liasse.cost.meter import Meter, pages_in_scope
    from liasse.emit.results import build, build_documents
    from liasse.verify.runner import run

    meter = Meter()
    with meter.stage("count_pages"):
        pages = pages_in_scope()
    with meter.stage("route_extract_verify"):
        verified = run()
    with meter.stage("build_documents"):
        documents = build_documents(verified)

    # The router's own count of pages carrying fields, when it has been run. It is not
    # recomputed here: doing the work twice to report how long the work took would put the
    # measurement inside the thing being measured.
    routing_path = paths.REPORTS_DIR / "routing.json"
    carrying = (
        json.loads(routing_path.read_text(encoding="utf-8"))["totals"]["relevant_pages"]
        if routing_path.exists()
        else 0
    )
    meter.count(pages, carrying)

    run_block = meter.run_block(
        model="provided OCR + rules",
        notes=(
            "No API is called and no credential is read: the pipeline reads the OCR "
            "shipped with the corpus and anchors on the liasse's own line codes. The cost "
            "per page is therefore a sum over zero recorded API calls divided by a counted "
            "number of pages, not a zero typed into the file. Seconds per page is wall "
            "clock over a full run divided by every page in scope, including the ones the "
            "router discards; the per-stage split is under 'measured'. What a vision model "
            "would cost on the same pages is derived - no call was made - in "
            "reports/cost.json."
        ),
    )

    document = build(verified, run_block, documents)
    paths.RESULTS_JSON.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    schema = json.loads(paths.RESULTS_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(document, schema)

    values = sum(len(d["fields"]) for d in document["documents"])
    print(f"{values} values from {len(document['documents'])} filings")
    print(f"validates against {paths.RESULTS_SCHEMA.relative_to(paths.REPO_ROOT)}")
    print(f"wrote {paths.RESULTS_JSON.relative_to(paths.REPO_ROOT)}")
    return 0


def _escalate(dpi: int) -> int:
    """Re-read what the checks could not settle, and keep only what a check then confirms.

    A superset of ``emit``: it runs the whole deterministic pipeline, escalates the gaps,
    and writes results.json with the measured API cost in the run block. Without a
    credential it changes nothing and says why.
    """
    import dataclasses
    import json

    import jsonschema

    from liasse.cost.meter import Meter, pages_in_scope
    from liasse.emit.results import build, build_documents
    from liasse.verify.confidence import for_field
    from liasse.verify.runner import run as verify_run
    from liasse.vlm.client import AnthropicTransport, Settings, unavailable_because
    from liasse.vlm.escalate import run as escalate_run
    from liasse.vlm.report import build_report

    blocked = unavailable_because()
    if blocked:
        print(f"escalation is not available: {blocked}", file=sys.stderr)
        print("nothing was changed; `liasse emit` writes the deterministic results.json")
        return 0

    settings = Settings.from_environment()
    meter = Meter()
    with meter.stage("count_pages"):
        pages = pages_in_scope()
    with meter.stage("route_extract_verify"):
        verified = verify_run()
    with meter.stage("escalate"):
        escalation = escalate_run(verified, AnthropicTransport(settings), settings, dpi)

    merged = []
    for document_result in verified:
        accepted = escalation.accepted.get(document_result.document.doc_id)
        if not accepted:
            merged.append(document_result)
            continue
        values = {**document_result.values, **accepted}
        results = escalation.results[document_result.document.doc_id]
        merged.append(
            dataclasses.replace(
                document_result,
                values=values,
                results=results,
                confidence={key: for_field(key, results) for key in values},
            )
        )

    with meter.stage("build_documents"):
        documents = build_documents(merged)

    routing_path = paths.REPORTS_DIR / "routing.json"
    carrying = (
        json.loads(routing_path.read_text(encoding="utf-8"))["totals"]["relevant_pages"]
        if routing_path.exists()
        else 0
    )
    meter.count(pages, carrying)
    # The ledger the escalation filled. cost_eur_per_page stops being a sum over nothing
    # the moment this runs, which is the property the E9 tests pin down.
    meter.ledger = escalation.ledger

    run_block = meter.run_block(
        model=f"provided OCR + rules, with {settings.model} on the gaps",
        notes=(
            "Cost per page is the tokens of the calls this run actually made, priced at the "
            "published rate on the date in reports/cost.json and divided by every page in "
            "scope. Values re-read by the model are emitted only where a check computed "
            "from other figures on other pages agreed with them; reports/escalation.json "
            "lists every question asked, including the ones whose answer was paid for and "
            "discarded."
        ),
    )

    document = build(merged, run_block, documents)
    paths.RESULTS_JSON.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    jsonschema.validate(document, json.loads(paths.RESULTS_SCHEMA.read_text(encoding="utf-8")))

    paths.REPORTS_DIR.mkdir(exist_ok=True)
    out = paths.REPORTS_DIR / "escalation.json"
    report = build_report(escalation, settings.model, dpi)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    totals = report["totals"]
    print(
        f"{totals['questions_asked']} questions asked, {totals['accepted']} accepted; "
        f"{report['cost']['eur']:.6f} EUR over {report['cost']['api_calls']} calls"
    )
    print(f"wrote {out.relative_to(paths.REPO_ROOT)} and results.json")
    return 0


def _run() -> int:
    """The whole deterministic pipeline, one stage after another: route, extract, verify,
    emit, cost. What ``make run`` and the README's "How to run it" promise.

    Each stage already writes its own report and prints its own summary; this only chains
    them and stops at the first failure, so a broken stage is reported by that stage's own
    message rather than by a second, vaguer one here.
    """
    for stage in (_route, _extract, _verify, _emit):
        code = stage()
        if code != 0:
            return code
    return _cost(_render_dpi(None))


def _report() -> int:
    """Regenerate reports/ from the last run, without re-emitting results.json.

    Route, extract and verify are independent of results.json and safe to redo any time.
    Cost is not: it reads the already-emitted results.json rather than the values in
    memory, specifically so results.json and reports/cost.json can never disagree about
    the same run - so this is where that dependency shows up. Run `liasse emit` (or
    `liasse run`) first if results.json does not exist yet; `liasse cost` says so.
    """
    for stage in (_route, _extract, _verify):
        code = stage()
        if code != 0:
            return code
    return _cost(_render_dpi(None))


def _render_dpi(requested: int | None) -> int:
    """--dpi, else LIASSE_VLM_DPI, else the default. The only env var this pipeline reads.

    Named in .env.example, as the brief requires: "your cost-per-page claim only means
    something if we can see which provider and model produced it".
    """
    import os

    from liasse.cost.vlm import DEFAULT_RENDER_DPI

    if requested is not None:
        return requested
    return int(os.environ.get("LIASSE_VLM_DPI") or DEFAULT_RENDER_DPI)


def _cost(dpi: int) -> int:
    """Write reports/cost.json: what the run cost, and what a vision model would cost.

    Reads the measured half out of results.json rather than running the pipeline again,
    so the two files can never disagree about the same run.
    """
    import json
    import math

    from liasse.cost.report import build_report
    from liasse.cost.vlm import (
        answer_characters,
        build_scenarios,
        measure_pages,
        prompt_characters,
        tokens_from_characters,
    )

    routing_path = paths.REPORTS_DIR / "routing.json"
    if not routing_path.exists() or not paths.RESULTS_JSON.exists():
        print("run `liasse route` and `liasse emit` first", file=sys.stderr)
        return 2

    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    results = json.loads(paths.RESULTS_JSON.read_text(encoding="utf-8"))
    field_defs = json.loads(paths.FIELD_DEFS.read_text(encoding="utf-8"))

    pages = measure_pages(routing, dpi)
    answering = sum(1 for p in pages if p.carries_fields)
    if not answering:
        print("the routing report lists no page carrying a field", file=sys.stderr)
        return 2

    prompt_tokens = tokens_from_characters(prompt_characters(field_defs))
    output_tokens = math.ceil(tokens_from_characters(answer_characters(results)) / answering)
    scenarios = build_scenarios(pages, prompt_tokens, output_tokens)
    report = build_report(
        results["run"], pages, scenarios, prompt_tokens, output_tokens, dpi
    )

    paths.REPORTS_DIR.mkdir(exist_ok=True)
    out = paths.REPORTS_DIR / "cost.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    measured = report["measured"]
    print(
        f"measured: {measured['cost_eur_per_page']} EUR/page, "
        f"{measured['seconds_per_page']} s/page over {measured['pages_processed']} pages "
        f"({measured['api_calls']} API calls)"
    )
    print(f"derived at {dpi} dpi, EUR per page of the corpus (no call was made):")
    models = list(report["derived"]["scenarios"][0]["by_model"])
    print(f"  {'scenario':<24} {'pages':>6}  " + "  ".join(f"{m:>16}" for m in models))
    for scenario in report["derived"]["scenarios"]:
        row = "  ".join(
            f"{scenario['by_model'][m]['eur_per_page_of_corpus']:>16.6f}" for m in models
        )
        print(f"  {scenario['name']:<24} {scenario['pages_sent']:>6}  {row}")
    headline = report["derived"]["headline"]
    if headline:
        print(
            f"routing the pages costs {headline['waste_factor']}x less than sending all "
            f"{headline['pages_if_not']}, for the same answer"
        )
    print(f"wrote {out.relative_to(paths.REPO_ROOT)}")
    return 0


def _check_boxes(sample_size: int, seed: int) -> int:
    """Draw sampled values onto their pages, using the challenge's own viewer.

    The oracle no automated check replaces. Every other check in this pipeline compares
    numbers with numbers, so a value that is consistently wrong in the same way passes them
    all; the only thing that catches a box pointing at the wrong row is looking at it. A
    wrong code interpretation survived a whole-corpus scan and two written pages here
    before a single rendered page exposed it.
    """
    import json
    import random
    import subprocess

    if not paths.RESULTS_JSON.exists():
        print("run `liasse emit` first", file=sys.stderr)
        return 2

    document = json.loads(paths.RESULTS_JSON.read_text(encoding="utf-8"))
    candidates = [(record, field) for record in document["documents"] for field in record["fields"]]
    if not candidates:
        print("nothing to check", file=sys.stderr)
        return 2

    chosen = random.Random(seed).sample(candidates, min(sample_size, len(candidates)))
    out_dir = paths.ARTIFACTS_DIR / "boxes"
    out_dir.mkdir(parents=True, exist_ok=True)

    for index, (record, field) in enumerate(chosen):
        pdf = paths.REPO_ROOT / record["pdf"]
        ocr = pdf.parent.parent / "ocr" / pdf.stem.rsplit("_", 1)[1]
        out = out_dir / f"{index:02d}_{record['siren']}_{field['field_key']}.png"
        subprocess.run(
            [
                sys.executable,
                str(paths.BBOX_VIEWER),
                "--pdf",
                str(pdf),
                "--page",
                str(field["page"]),
                "--ocr",
                str(ocr),
                "--bbox",
                ",".join(str(v) for v in field["bbox"]),
                "--dpi",
                "200",
                "-o",
                str(out),
            ],
            check=True,
            capture_output=True,
        )
        print(f"  {field['field_key']:<38} {field['value']:>14}  p{field['page']:<3} {out.name}")

    print(f"wrote {len(chosen)} renders to {out_dir.relative_to(paths.REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="liasse", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check that the environment can run the pipeline")
    sub.add_parser("route", help="classify every page in scope and write reports/routing.json")
    sub.add_parser("extract", help="read the twelve fields and write reports/extraction.json")
    sub.add_parser("verify", help="run the checks and write reports/verification.json")
    sub.add_parser("emit", help="write results.json at the repository root")
    cost = sub.add_parser("cost", help="write reports/cost.json: measured run, derived VLM curve")
    cost.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="render resolution for the derived VLM curve; defaults to $LIASSE_VLM_DPI",
    )
    escalate = sub.add_parser(
        "escalate", help="re-read the gaps with a vision model, keeping only what a check confirms"
    )
    escalate.add_argument("--dpi", type=int, default=None, help="defaults to $LIASSE_VLM_DPI")
    boxes = sub.add_parser(
        "check-boxes", help="render sampled values onto their pages, to check by eye"
    )
    boxes.add_argument("--n", type=int, default=12, help="how many values to sample")
    boxes.add_argument("--seed", type=int, default=0)
    sub.add_parser("run", help="run the pipeline over the challenge scope")
    sub.add_parser("report", help="regenerate reports/ from the last run")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    if args.command == "route":
        return _route()
    if args.command == "extract":
        return _extract()
    if args.command == "verify":
        return _verify()
    if args.command == "emit":
        return _emit()
    if args.command == "cost":
        return _cost(_render_dpi(args.dpi))
    if args.command == "escalate":
        return _escalate(_render_dpi(args.dpi))
    if args.command == "check-boxes":
        return _check_boxes(args.n, args.seed)
    if args.command == "run":
        return _run()
    if args.command == "report":
        return _report()
    print(f"'{args.command}' is not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
