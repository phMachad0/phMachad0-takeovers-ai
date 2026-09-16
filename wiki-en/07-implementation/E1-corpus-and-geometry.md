---
type: implementation
stage: E1
tags: [code, corpus, geometry, tests]
status: draft
updated: 2026-09-15
---

# E1 — corpus and geometry

**State:** done · 99 green tests, 4 skipped · `ruff` clean
**Exit criterion:** ✅ coordinate conversion identical to `tools/bbox_viewer.py` across
**2,729 tokens** from 45 pages of the 15 documents in scope.

## What was created

```
src/liasse/corpus/          layer 0 — pure I/O, zero computation
├── models.py               Token · PageGeometry · OcrPage · Document
├── scope.py                the 15 documents, declared
└── loader.py               joins meta + pdf + ocr

src/liasse/geometry/        layer 1 — pure math, zero I/O
├── boxes.py                BBox · bounds · union · is_normalized · looks_suspicious
└── coords.py                px300 ↔ points ↔ normalized

tests/
├── differential/           the O1 oracle against Takeovers' code
└── unit/                   geometry (pure) + loader (marked `corpus`)
```

## The four decisions that matter

### 1 · Layer 0 computes nothing

`corpus/models.py` stores what's in the bytes and nothing more. `Token` carries the
**verbatim polygon**, not a rectangle:

```python
@dataclass(frozen=True, slots=True)
class Token:
    text: str
    polygon: Polygon   # 4 points, px @300dpi, exactly as the OCR delivered it
    score: float
```

Reducing it to a rectangle at load time would throw away the skew information that E3
needs. Whoever wants a rectangle asks geometry for it: `boxes.bounds(token.polygon)`.

The side effect is the point: **geometry ends up testable without touching `data/`.**
The 20 tests in `boxes.py` and `coords.py` run in milliseconds and have no idea a corpus
exists.

### 2 · Scope is declared, not discovered

`scope.py` lists the 15 documents by hand, with `siren`, `doc_id`, filing date, and the
**format measured during E1.5**. A new PDF showing up in `data/` doesn't silently widen the
run, and the table can be checked against the brief without reading any code.

The `known_format` field exists so E2 can claim that the router agrees with
[[F001-half-the-corpus-is-not-liasse]] — it's a partial answer key that I measured myself.

### 3 · `fiscal_year_end` comes from `meta/`, not from the PDF

```python
fiscal_year_end=meta.get("dateCloture")
```

One line, and it resolves a required schema field without parsing anything
([[F006-the-meta-json-hands-over-the-closing-date]]). The test locks in the property that
justifies the field's existence: `fiscal_year_end < deposit_date` across the 15 documents.

### 4 · Page size is read from the PDF, per page, with caching

```python
@functools.lru_cache(maxsize=32)
def _page_sizes_pt(pdf_path) -> tuple[tuple[float, float], ...]:
```

Opening the PDF is the only slow operation here, and every page of a document shares the
file, so the cache is per document. `page.rect` already accounts for rotation — a
landscape page reports its width as the long side, which is what normalization needs to
divide by.

**Why not assume A4:** see item B of [[F012-blank-pages-and-page-sizes]]. Only 21% of the
pages in scope are actually A4.

## The differential test — the exit criterion

`tests/differential/test_coordinate_conversion.py` loads `tools/bbox_viewer.py` **as a
module** (via the `bbox_viewer` fixture in `conftest.py`) and compares, token by token:

```python
theirs = bbox_viewer.polygon_to_norm(token.polygon, geom.width_pt, geom.height_pt)
ours   = coords.to_normalized(boxes.bounds(token.polygon), geom.width_pt, geom.height_pt)
assert ours.as_list() == pytest.approx(theirs, abs=1e-12)
```

Importing instead of copying the arithmetic is the entire point: a copy would drift, and
the test would end up comparing us against our own belief instead of against their actual
implementation.

Sample: 3 pages per document, fixed seed, **all 15 documents**. Two tests guard the
sample's validity:

| guard | against |
|---|---|
| `test_every_document_is_in_the_sample` | comparing only the easy documents |
| `test_enough_tokens_were_actually_compared` | passing by having compared nothing |

The second counts tokens actually compared (2,729) and enforces a floor. This matters
more than it looks: 10% of the pages in scope have **no OCR at all**, so "the sample was 45
pages" doesn't prove any comparison happened.

## Proof that the tests fail when they should

Three mutants injected into `coords.py`, all caught:

| mutant | result |
|---|---|
| assume A4 instead of reading the page | **fails on almost every sampled page** |
| `PIXELS_PER_POINT = 72/300` (inverted factor) | fails the differential test **and** 3 unit tests |
| transpose `x` and `y` during normalization | fails the differential test |

The first was the most informative. I expected it to fail at an edge, and it failed on
nearly everything. That's how item B of [[F012-blank-pages-and-page-sizes]] surfaced.

## What the test found without being asked to look

On the first run, **4 real failures** — and none of them were a conversion error:

```
AssertionError: 6860f28ca0138eae340c7453 page 10 has no OCR lines to compare
```

Pages with no OCR lines at all. Investigated instead of worked around, this became
[[F012-blank-pages-and-page-sizes]]: 41 blank pages (9.9% of scope), almost all
even-numbered — the versos of a double-sided scan.

The test now **skips** those pages with an explicit reason, and the token floor exists
precisely because silently skipping would have been the next mistake.

## Two fixes to my own code

- `ruff` flagged `SIM300` on `assert x == pytest.approx(y)`, reading it as a Yoda
  condition. It isn't, and the suggested rewrite makes it less readable — disabled
  per-file, with the reason recorded in `pyproject.toml`.
- One of my own tests was **tautological**: it compared `to_normalized(box)` against
  `to_normalized(box)`. Rewritten to check against a ratio computed independently of the
  module under test.

## A note on the layering rule

`geometry` (layer 1) imports nothing from `liasse` — not even `corpus`. It works on tuples
and floats. The [[modular-architecture|layering rule]] would allow `geometry → corpus`,
but full independence is stronger, and it's what keeps the geometry tests corpus-free.

## Next

[[phase-1-foundation|E2 — page routing]]. It already has two inputs ready: `known_format`
in `scope.py` as an answer key, and the `tokens == 0 ⇒ blank` rule from
[[F012-blank-pages-and-page-sizes]].

## Links

- [[E0-scaffold]] · [[bbox-and-normalization]] · [[testing-strategy]] · [[phase-1-foundation]]
