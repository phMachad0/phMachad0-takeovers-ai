---
type: finding
id: F012
tags: [corpus, geometry, cost]
status: draft
updated: 2026-09-15
---

# F012 — 10% of pages are blank, and only 21% are genuinely A4

**Impact: high. Both halves came out of the same E1 differential test.**

## A · 41 of 415 pages have no OCR lines at all

| document | blank pages | of | pages |
|---|---|---|---|
| `445070311/65a4095d` | **26** | 58 | 2, 8, 10, 12, 14, …, 56 |
| `445070311/6860f28c` | **15** | 32 | 2, 4, 6, 8, …, 22, 26, 28, 30, 32 |
| all other 13 | 0 | — | — |

**41 of 415 = 9.9%.** And the pattern is almost entirely **even-numbered**: the signature of
a double-sided scan of originals that were only printed on one side. The back sides were
scanned and came out blank.

Another 12 pages have between 1 and 5 tokens — cover sheets, title pages, loose stamps.

**Consequences.** Routing classifies `tokens == 0` as `blank` with no further work, and
these 41 pages never need any processing at all. For the cost calculation in
[[cost-per-page]], the effective denominator isn't 415 — and 45% of an entire document's
pages (`65a4095d`) are pure waste if you send the whole PDF to a model.

An extractor that doesn't handle this will either throw an exception or, worse, produce an
empty extraction indistinguishable from a real failure.

## B · Only 21% of pages are exactly A4

Measuring `page.rect` across all 415 pages:

```
exactly 595.0 × 842.0 pt :  88 of 415  (21%)
distinct sizes            :  88
largest deviation from A4 :  1.87%  (820561470/6493e437 p14: 593.3 × 857.8 pt)
```

Almost every page has its own slightly different size, because each sheet went through the
scanner and the result is never identical. In `820561470` the pages measure ~593 × 856 pt —
**fifteen points taller than A4**.

**Why it matters.** A 1.87% deviation in height, on a page of 3508 px:

```
3508 px × 1.87% = 66 px of error
liasse line height ≈ 35 px
```

**Assuming A4 shifts the box by nearly two lines of text.** The box still stays inside
`[0,1]`, still validates against the schema, still points somewhere plausible on the page —
and points at the wrong line. It's exactly the kind of error that's hard to sell or defend
downstream, wrong in a way that still looks correct.

## How both surfaced

Both came out of the **differential test against `tools/bbox_viewer.py`** in E1, and neither
was being looked for:

- side A showed up as a test failure on four pages — investigated, it wasn't a conversion
  mismatch, it was a page with no OCR;
- side B showed up when injecting the mutant *"assume A4 instead of reading the page"* to
  prove the test catches errors. It did — and the extent of the failure revealed that the
  A4 assumption breaks on 79% of the corpus, not at an edge.

Worth recording in the README as a method argument: **oracle O1 paid for itself before the
first line of extraction existed.**

## Links

- [[bbox-and-normalization]] · [[E1-corpus-and-geometry]] · [[idea-04-page-routing]]
- [[cost-per-page]] · [[testing-strategy]]
