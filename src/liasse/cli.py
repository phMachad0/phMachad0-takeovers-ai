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

    print(f"liasse {__version__}")
    print(f"repo root: {paths.REPO_ROOT}")
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
    from liasse.extract.liasse import extract
    from liasse.extract.report import build_report, document_summary
    from liasse.routing.classifier import classify_document

    summaries = []
    for document in iter_scope():
        pages = list(iter_pages(document))
        routed = classify_document(document, pages)
        forms = {p.page: p.form for p in routed.relevant_pages if p.kind == "liasse" and p.form}
        if not forms:
            continue
        values = extract([p for p in pages if p.page in forms], forms)
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
    import time

    import jsonschema

    from liasse.emit.results import build
    from liasse.verify.runner import run

    started = time.perf_counter()
    verified = run()
    elapsed = time.perf_counter() - started

    pages = json.loads((paths.REPORTS_DIR / "routing.json").read_text())["totals"]["pages"]
    run_block = {
        "cost_eur_per_page": 0.0,
        "seconds_per_page": round(elapsed / pages, 5),
        "pages_processed": pages,
        "model": "provided OCR + rules",
        "notes": (
            "No API is called and no credential is read, so the marginal cost is zero: "
            "the pipeline reads the OCR shipped with the corpus and resolves fields by "
            "the liasse's own line codes. Seconds per page is wall clock over a full run "
            "divided by every page in scope, including the 355 the router discards."
        ),
    }

    document = build(verified, run_block)
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
    if args.command == "check-boxes":
        return _check_boxes(args.n, args.seed)
    print(f"'{args.command}' is not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
