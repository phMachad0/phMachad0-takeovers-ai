---
type: plan
tags: [roadmap, stages]
status: draft
updated: 2026-09-15
---

# Phase 1 — foundation (E0 → E4)

The five stages nobody sees in the deliverable, and without which nothing works. They end
with an OCR page turned into rows with correctly read numbers and correctly converted
boxes.

---

## E0 · Scaffold · 0.4 h

**Delivers** a project that runs and tests.

- `pyproject.toml`, package under `src/liasse/`, `pytest`, `ruff`
- **`pymupdf` needs to be installed** — it isn't in the environment (verified). It's the
  dependency page geometry relies on. `pillow` is already there.
- `Makefile`: `make test`, `make run`, `make report`
- `.env.example` from the first commit, with the names that *might* be used:
  ```dotenv
  # .env.example — names only, never values
  ANTHROPIC_API_KEY=
  VLM_MODEL=
  VLM_MAX_PAGES=
  ```
  If E11 gets cut, the file turns into just a comment saying the pipeline uses no key at
  all — the brief says that's *"a legitimate and interesting answer."*
- `.gitignore` already contains `.env` ✅

**Exit criterion:** `make test` green with a trivial test. `python -c "import fitz"` works.

---

## E1 · Corpus and geometry · 0.8 h

**Input** `data/`  →  **Output** `Document`, `Token`, `PageGeometry`, and the coordinate
conversion.

- `corpus/scope.py` — the 15 documents in scope, declarative, with siren + doc_id
- `corpus/loader.py` — joins `meta/` + `pdf/` + `ocr/`; exposes `dateCloture` as
  `fiscal_year_end` ([[F006-the-meta-json-hands-over-the-closing-date]])
- `geometry/coords.py` — px300 ↔ points ↔ normalized, **reading each page's actual width
  from the PDF** ([[bbox-and-normalization]])
- `geometry/boxes.py` — polygon union, invariants

**Tests**

| layer | test |
|---|---|
| **L3 differential** | conversion identical to `tools/bbox_viewer.py::polygon_to_norm` on 40 sampled pages — **oracle O1** |
| L4 invariant | every box in `[0,1]`, `x0 < x1`, `y0 < y1` |
| L1 unit | union of two boxes; landscape page; page re-rendered at 150 dpi |

**Exit criterion:** the differential test passes on all 15 documents. It's the most
important test of the phase — it validates against the company's own code the conversion
the brief calls *"a few lines, and it is on purpose."*

---

## E1.5 · Code confirmation · 0.5 h

Not code, reconnaissance — but it blocks E5.

Sweep the liasse pages of the 8 documents and confirm the code ↔ label ↔ column mapping
for the 11 codes still marked as unverified in [[liasse-codes]]: `CO`, `CF`, `CD`, `EE`,
`HK`, `YP`, `FS`, `FT`, `FU`, `FV`, `FW`.

**Exit criterion:** the [[liasse-codes]] table has no `verified: no` rows left among the
codes used by the 12 fields — or, for the ones that never show up, a note explaining where
the value will be sourced from instead.

---

## E2 · Page routing · 0.6 h

**Input** `Document`  →  **Output** `RoutedDoc` + `reports/routing.json`

Implements [[idea-04-page-routing]]: two independent signals (DGFiP header, code
fingerprint) plus a plaquette signature.

**Tests**

| layer | test |
|---|---|
| **L2 golden** | classification of the 15 documents matches the table in [[F001-half-the-corpus-is-not-liasse]] — 8 liasse, 7 plaquette, and the exact pages |
| L2 golden | `401009741/68f0a715…` is detected as a **partial** liasse (only 2050 and 2051) |
| L1 | near-empty pages (1–7 tokens) are classified as `blank`, not `prose` |

**Exit criterion:** `reports/routing.json` generated, with the number of relevant pages
per document and the signals that justified each decision. It's the README's first
number: *"75 of 415 pages carry content."*

---

## E3 · Row reconstruction · 0.9 h

**Input** `RoutedDoc`  →  **Output** `LinedDoc`

Implements [[idea-03-row-banding-with-skew]]: de-rotate, group into bands, detect the
values column. **The emitted `bbox` always comes from the original coordinates.**

**Tests**

| layer | test |
|---|---|
| L1 | `deskew()` at a 1° tilt returns the expected offset (closed-form arithmetic test) |
| **L2 golden** | on page 006 of `65784e5da67d84faf4042736`, `Salaires et traitements` / `FY` / `499` / `659` land **on the same row** — despite the code being 15 px above ([[skew-and-geometry]]) |
| **L2 golden** | on a page of `820561470` with a −0.98° skew, the label and value of the same row end up together |
| L5 A/B | **measurement with and without deskew** on the 3 documents of `820561470`, using the verifiers' pass rate as the metric |

**Exit criterion:** the skewed-page fixture passes **and fails with deskew turned off.**
If it passes both ways, the fix isn't being exercised and the fixture is poorly chosen.

The last row's A/B can only be run after E7 — it's logged as an open item for the stage,
and it's the number that justifies idea ❸ in the README.

---

## E4 · Number parsing · 0.7 h

**Input** the tokens of a row  →  **Output** `int | Decimal | None`, plus the tokens used.

Implements [[idea-02-digit-reassembly]]: right-to-left scanning, `GAP_MAX` adaptive to
glyph width, **syntactic validation of the groups**, and the three sign rules.

It's the densest stage in tests and the cheapest to test, since it has no I/O.

**Tests** — every case is already written in the wiki, with coordinates:

| layer | case | source |
|---|---|---|
| L2 | `"1"`,`"805"`,`"459"` → `1805459` | [[F003-the-ocr-breaks-numbers-apart]] |
| L2 | `"27"`,`"699"` → `27699` | F003 |
| L2 | `"2 524"` → `2524` (single token, preserved space) | F003 |
| L2 | `"243"` → `243` | F003 |
| L2 | `"-"`,`"45"`,`"440)"` → `-45440` | [[F004-negatives-are-printed-in-parentheses]] |
| L2 | `"("`,`"52"`,`"814)"` → `-52814` | F004 |
| **L2** | `"2"`,`"096)"` → `-2096` — **the `GV` case** | F004 |
| **L6 negative** | `"2 524"`,`"1"`,`"805"`,`"459"` → **`None`**, not `25241805459` | syntactic validation |
| L6 negative | `"12"`,`"34"` → `None` (a 2-digit group in the middle is invalid) | |
| L4 property | round-trip: `format(parse(t)) == "".join(t)` without punctuation | |
| L4 property | no return value is `float` | |

**Exit criterion:** all green, **including the negatives**. A parser that never returns
`None` is inventing numbers.

---

## Links

- [[00-roadmap]] · [[phase-2-extraction]] · [[testing-strategy]] · [[modular-architecture]]
