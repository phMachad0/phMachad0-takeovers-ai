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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="liasse", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check that the environment can run the pipeline")
    sub.add_parser("route", help="classify every page in scope and write reports/routing.json")
    sub.add_parser("extract", help="read the twelve fields and write reports/extraction.json")
    sub.add_parser("run", help="run the pipeline over the challenge scope")
    sub.add_parser("report", help="regenerate reports/ from the last run")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    if args.command == "route":
        return _route()
    if args.command == "extract":
        return _extract()
    print(f"'{args.command}' is not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
