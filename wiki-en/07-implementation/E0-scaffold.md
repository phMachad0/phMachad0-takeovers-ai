---
type: implementation
stage: E0
tags: [code, scaffold, tests]
status: draft
updated: 2026-09-15
---

# E0 — the scaffold

**State:** done · 23 green tests · `ruff` clean · `liasse doctor` OK

> All code is written in **English** — identifiers, comments, docstrings, test names.

## What was created

```
pyproject.toml            package, dependencies, pytest and ruff config
Makefile                  make test / lint / fmt / run / report / clean
.env.example               variable names, zero values
src/liasse/
├── __init__.py           docstring with the layer map
├── layers.py             the layer map AS DATA
├── paths.py              every path derived from REPO_ROOT
├── cli.py                `liasse doctor` (+ run/report stubs)
├── __main__.py           enables `python -m liasse`
└── {corpus,geometry,text,routing,fields,extract,units,verify,cost,emit}/
                          one __init__.py per layer, declaring its role
tests/
├── conftest.py           repo_root and corpus_dir fixtures
├── architecture/         the test that protects the layering rule
└── unit/                 environment and CLI
```

## The three decisions that matter

### 1 · `layers.py` — the layering rule is data, not convention

The [[modular-architecture|dependency rule]] says a layer only imports from layers below
it. That usually lives in a document and rots. Here it lives in code:

```python
LAYERS: dict[str, int] = {
    "corpus": 0,
    "geometry": 1, "text": 1,
    "routing": 2,
    "fields": 3, "extract": 3,
    "units": 4,
    "verify": 5, "cost": 5,
    "emit": 6,
}
UNLAYERED = frozenset({"cli", "layers", "__init__", "__main__"})
```

It lives in the package rather than the test for two reasons: whoever reads the source
sees the rule, and the test has a single source of truth to check against instead of
duplicating the table.

### 2 · The architecture test reads imports with `ast`

`tests/architecture/test_layer_dependencies.py` parses every file in `src/liasse/`,
extracts the imported subpackages — catching both `import liasse.x` and
`from liasse.x import y` — and fails if a module imports from a layer equal to or above
its own.

There are three tests, and the third is what prevents erosion:

| test | what it protects |
|---|---|
| `test_there_is_source_to_check` | the suite passing by finding nothing to check |
| `test_module_only_imports_lower_layers` | the rule itself, one case per file |
| `test_every_subpackage_is_in_the_layer_map` | a new subpackage silently falling out of coverage |

**Verified to fail when it should.** I injected `from liasse.verify import …` inside
`geometry/` (layer 1 → layer 5):

```
AssertionError: geometry/_violation.py is layer 1 (geometry) but imports
liasse.verify, which is layer 5. A layer may only import from layers below it.
```

And created a `newthing/` subpackage without declaring it:

```
AssertionError: subpackages missing from layers.LAYERS: ['newthing']
```

This is layer **L6** of the [[testing-strategy]] applied to the scaffold itself: a test
that has never failed hasn't proven anything.

### 3 · `paths.py` — no path relative to the cwd

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
```

Everything derives from that: `DATA_DIR`, `RESULTS_SCHEMA`, `FIELD_DEFS`, `BBOX_VIEWER`,
`ARTIFACTS_DIR`, `REPORTS_DIR`, `RESULTS_JSON`. The pipeline runs from any directory and
no test depends on where pytest was invoked from.

`BBOX_VIEWER` already points at `tools/bbox_viewer.py` at this stage, because it is the
**O1 oracle** for E1's differential test — Takeovers' own code used as the reference.

## `liasse doctor`

E0's acceptance criterion, and it stays useful afterward as an environment check:

```bash
python3 -m liasse doctor
```

Checks `pymupdf`, `jsonschema`, and the presence of the corpus, the schema, the field
definitions, and `bbox_viewer`. Exits with code 1 and lists the problems if something is
missing.

## The four environment tests

They don't test our code; they test that the ground is solid. Each one exists because it
already caused, or would have caused, a detour:

| test                                            | why                                                                                                                 |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `test_repo_root_is_the_repository`               | `parents[2]` fails silently if the package is moved                                                                |
| `test_pymupdf_is_importable_and_reads_page_size` | it is the only reliable source of page size in points, and bbox conversion depends on it ([[bbox-and-normalization]]) |
| `test_results_schema_is_valid_json_schema`       | if the schema doesn't compile, E8 validates nothing                                                                |
| `test_field_definitions_list_twelve_fields`      | locks in the assumption that there are 12 fields                                                                |

## Environment notes

- **`pymupdf` 1.28.2** installed. It warns that `import fitz` is deprecated; the new code
  uses `import pymupdf`. Takeovers' own `tools/bbox_viewer.py` still uses `fitz` — it
  works, it just raises the warning. Not touched: it's an immutable source.
- `pytest` 9.1.1, `ruff` 0.16.7, `jsonschema` 4.23.0.
- `artifacts/` is in `.gitignore` (disposable); **`reports/` is versioned on purpose** —
  it's the evidence the README cites, and its `git diff` shows the effect of every change.

## `.env.example`

Written already, with a comment that is itself an answer to the brief:

> *The deterministic pipeline (E0–E9) needs no credentials at all: it reads the OCR that
> ships with the corpus. These variables are only read if vision-model escalation (E11) is
> turned on.*

Four names, no values: `ANTHROPIC_API_KEY`, `LIASSE_VLM_MODEL`,
`LIASSE_VLM_MAX_PAGES`, `LIASSE_VLM_DPI`. The third is a safety cap — it prevents a
routing bug from turning into an unexpected bill.

## Next

[[phase-1-foundation|E1 — corpus and geometry]], whose exit criterion is the **differential
test against `bbox_viewer.py`**.

## Links

- [[00-roadmap]] · [[modular-architecture]] · [[testing-strategy]] · [[phase-1-foundation]]
