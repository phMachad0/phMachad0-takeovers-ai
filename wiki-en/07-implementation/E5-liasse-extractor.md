---
type: implementation
stage: E5
tags: [code, extraction, liasse, tests]
status: draft
updated: 2026-09-16
---

# E5 — liasse extractor

**State:** done · 278 green tests, 4 skipped · `ruff` clean
**Exit criterion:** ✅ tier distribution reported, and **V1 closes 7 of 7** verifiable
documents, with no discrepancies.

```
75 fields read from 8 liasse documents; 14 legally absent, 7 unresolved
tiers: {'CODE': 63, 'LABEL': 12}
```

**75 read + 14 legally absent + 7 missing from the source = 96. Zero unexplained gaps.**

## What was created

```
src/liasse/fields/catalog.py   the 12 fields, declared as data    (layer 3)
src/liasse/extract/base.py     RawValue · Component · Tier · MissingValue
src/liasse/extract/liasse.py   the anchor ladder and column selection
src/liasse/extract/report.py   coverage against three denominators
src/liasse/cli.py              `liasse extract`
```

## The catalog is data, not code

Every decision about *what* a field is lives in `catalog.py`: which form, which code names
the row, which printed cell of that row, and which words identify the row when the code
didn't survive OCR.

```python
FieldSpec("PL_PERSONNEL_COSTS_FRGAAP", (_WAGES, _SOCIAL))
FieldSpec(
    "BS_CAPITAL_EQUITY_FRGAAP", (_CAPITAL,),
    variant_key="BS_CAPITAL_EQUITY_FRGAAP__incl_reserves",
    variant_anchors=(_CAPITAL, _SHARE_PREMIUM, _LEGAL_RESERVE, _OTHER_RESERVES),
)
```

The extractor knows how to follow an anchor; it knows nothing about accounting. That
separation is what turns the five ambiguities from [[ADR-002-schema-ambiguities]] into a
**data-line** change rather than a conditional branch — and it makes the file readable by
someone who understands the domain and doesn't write code.

## Measurement inverted the ladder's order

The plan called for: code → **ordinal position in the template** → label. I measured
before building, over the 121 field×page liasse pairs:

| situation | cases | |
|---|---|---|
| code **and** label | 91 | 75% |
| **no code**, label present | 27 | **22%** |
| neither code nor label | 2 | 2% |
| code without label | 1 | 1% |

**The label rescues 27 of the 29 lost codes.** The ordinal fallback would only serve the
remaining 2 — and on both of them the OCR dropped the **entire row**, so there's nothing
to interpolate between.

Decision: a two-step ladder, **code → label**. The ordinal step stays **unbuilt and
documented**, with the measurement that justifies it. In the run: 63 values by code, 12 by
label.

## Column selection, which E4 made visible

A liasse row isn't a single thing, and each form needed its own rule:

**Anchored on the code, one cell.** The value is the first cell to the right, bounded by
the next code so it doesn't spill into the neighboring column.

**Anchored on the code, three columns.** On form 2050 the row reads
`Brut | Amortissements | Net`, and the middle column **has its own code** (`IA`). Stopping
there returns gross assets — 8,754,311 instead of 6,233,746: larger, plausible, and wrong.
This was a real bug, caught by V1.

**Missing code.** The row is still identifiable by its label, and the **sibling codes**
that survived say which cell is ours: the revenue row prints `FJ | FK | FL`, and with `FK`
read and `FL` lost, the total is the cell following `FK`'s. This recovered
`PL_REVENUE = 1,800,826` in a document where the most basic field was otherwise
unavailable.

## A blank cell is not a gap

On a French form, an empty cell means **zero**, not "unknown." The first version treated
the two the same and reported 16 incomplete derived sums — almost all legitimate: the
company has no marketable securities (`CE`), didn't provision for fixed assets (`GB`).

Now the distinction is explicit:

| situation | outcome |
|---|---|
| row found, cell empty | `Component(value=0, blank=True)` — a fact about the company |
| row not found | `MissingValue` — a gap in extraction |

Result: **0 incomplete sums, 24 blank cells read as zero.** Summing zero for an unread term
would be inventing data; silently dropping it would make the total look complete when it
isn't.

## Two of my own earlier measurements were wrong

Both were caught by real cases, and both were thresholds I had set myself.

### `orientation_angle` doesn't flag garbage

The sanity filter from
[[F013-the-ocr-reads-the-code-column-as-vertical-text|F013]] rejected any token with
`orientation_angle != 0`. Measuring the whole corpus: **12 of 18** two-letter tokens with
a nonzero angle are ordinary codes — `IH`, `TH`, `CO`, `GQ` — with full score and normal
height. Rejecting them cost real fields.

The false `BZ` is caught **twice over** by score (0.37) and height (367 px against a
median of 40). The angle never carried its own weight. Signal removed from the filter,
kept as evidence.

### The distance threshold was set too high

E4 calibrated `GAP_IN_DIGIT_WIDTHS = 4.0` over a biased sample — only the rows a faulty
detector had flagged. Measuring **every** row across the 28 liasse pages:

| | median | extreme |
|---|---|---|
| within one number | 0.27 | **0.70** |
| between columns | 6.76 | **2.80** |

The 4.0 threshold was **above 68 legitimate column separations**, merging them — and the
shape check then refused whole rows. Corrected to **1.5**, which sits between 0.70 and
2.80 with margin on both sides.

The test locks in the property, not the number:

```python
assert 0.70 < GAP_IN_DIGIT_WIDTHS < 2.80
```

## The test that stands in for all of them

```
document             TOTAL_ASSETS    EE (2051)   V1
328024377/63e8ebbb        4823303      4823303   OK
328024377/63e8ebbb        6233746      6233746   OK
504304205/63e13943        1807858      1807858   OK
504304205/66cd893c        1689390      1689390   OK
401009741/63e88115         945632       945632   OK
401009741/65784e5d        1014105      1014105   OK
401009741/68f0a715        1135864      1135864   OK
```

Two different pages, two different anchors, one number. **7 of 7, zero discrepancies.**

It's evidence of correctness, not of coverage — and it's the first number in the
submission that doesn't depend on taking our word for it.

## The 21 absences, explained

| field | docs | reason |
|---|---|---|
| `META_AVG_WORKFORCE` | 7 | in 2, the OCR dropped the row; in 5, the data is in running prose outside the liasse ([[F010-actual-field-coverage]]) |
| the 7 `PL_*` fields | 2 each = 14 | **income statement filed as confidential** ([[F014-the-registry-announces-the-confidential-income-statement]]) |

The report counts against **three denominators** — read, legally absent, unresolved —
because "75 of 96" hides the question the brief actually asks.

## Next

[[phase-2-extraction|E6 — units]], which is short, and then **E7**, where V1 stops being a
check script and becomes the verifier that also routes cost.

## Links

- [[E4-number-parsing]] · [[idea-01-code-anchoring]] · [[ADR-002-schema-ambiguities]]
- [[F009-measured-code-loss]] · [[F011-v1-confirmed-and-the-column-structure]] · [[F013-the-ocr-reads-the-code-column-as-vertical-text]]
