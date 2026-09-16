---
type: plan
tags: [roadmap, stages]
status: draft
updated: 2026-09-15
---

# Phase 2 — extraction and verification (E5 → E9)

Where the submission comes into existence. By the end of E9 there's a valid
`results.json`, with measured accuracy and derived cost.

---

## E5 · Liasse extractor · 1.1 h

**Input** `LinedDoc` + catalogue  →  **Output** `[RawValue]`

Implements [[idea-01-code-anchoring]] with the anchor ladder:

1. code read from the OCR
2. **ordinal position in the template** — recovers `FS`…`FW`, lost by the OCR
   ([[F005-the-ocr-loses-part-of-the-code-column]])
3. fuzzy-matched label

Plus a declarative `fields/catalog.py`, with derived fields (`FY+FZ`, the COGS from
[[cogs-a-la-francaise]]) carrying their `components` for auditable provenance.

**Tests**

| layer | test |
|---|---|
| L2 golden | on page 006, `PL_REVENUE` = `1 805 459` via rung 1, code `FL` |
| **L2 golden** | `PL_EXT_SERVICES_COSTS` = `329 158` via **rung 2**, even though `FW` isn't present in the OCR |
| L2 golden | `PL_PERSONNEL_COSTS` = `499 659 + 162 521 = 662 180`, with two `components` |
| L4 | every `RawValue` has a non-empty `tokens_used` and a recorded `tier` |
| L6 negative | a field whose code is absent and whose label doesn't match returns **absence**, not `0` — the `financial_fields.json` requires: *"omit it rather than reporting 0"* |

**Exit criterion:** extraction run across the 8 liasse documents, with the **tier
distribution** reported. If rung 2 never fires, it isn't really implemented — E5 doesn't
close.

---

## E6 · Units · 0.3 h

**Input** `[RawValue]`  →  **Output** `[TypedValue]`

Implements [[idea-06-unit-with-scope]]: scoped markers, form defaults, and the **internal
capital anchor**.

**Tests**

| layer | test |
|---|---|
| **L2 golden** | `328024377`: balance sheet resolved as `EUR`, with the page-12 marker in `rejected_markers` — [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] |
| L2 golden | the capital anchor matches across the 5 companies: `152 500` / `10 000` / `300 000` / … |
| L6 negative | if the anchor and the marker disagree, the value is flagged for escalation, not silently resolved |

**Exit criterion:** no value leaves without `unit_evidence`. A unit with no justification
is a typed guess.

---

## E7 · Verifiers · 1.0 h — *the central stage*

**Input** `[TypedValue]`  →  **Output** `[VerifiedValue]` + `reports/verification.json`

Implements [[idea-05-verifier-as-router]] with the decorator-based registry:

- **V1** balance-sheet identity `CO == EE`
- **V2** form arithmetic: `FJ+FK=FL`, `GP−GU=GV`, `ΣD*=DL`, `GG+(GH−GI)+GV=GW`
- **V3** N−1 cross-check — limited to the **7 pairs** mapped in
  [[F007-the-n-1-chain-has-holes]]
- **V0** (cheap, a bonus) meta `dateCloture` vs the printed `Exercice N clos le`

Plus confidence aggregation: `confidence` derived from how many independent verifiers
passed, **not** from the OCR's `score`.

**Tests**

| layer | test |
|---|---|
| L5 acceptance | per-verifier pass rates, with a versioned floor that can't regress |
| **L6 negative** | inject `/1000` into `BS_TOTAL_ASSETS` → **V1 must fail** |
| **L6 negative** | flip the sign of `PL_FINANCIAL_RESULTS` → **V2 must fail** |
| L6 negative | swap column N for N−1 in a document → **V3 must fail** |
| L1 | the aggregator only counts verifiers that *apply*: a field with no N−1 pair isn't penalized for V3 not running |

**Exit criterion:** `reports/verification.json` with the field × document × verifier
matrix, and the three negative tests green. **A verifier that never fails anything is a
verifier that isn't wired up** — the L6 tests are what proves otherwise.

This is where the README number is born: *"N% of values pass at least one independent
verifier; M% pass V3, which cross-checks against a second document."*

And this is also where **E3's A/B** gets run: turn off deskew and measure the drop.

---

## E8 · Emitting `results.json` · 0.4 h

**Input** `[VerifiedValue]`  →  **Output** `results.json` at the repo root

- assembles `documents[]` with `pdf`, `siren`, `fiscal_year_end` (from the meta), `fields[]`
- `bbox` = union of `tokens_used`, converted and normalized
- `snippet` = concatenation of the tokens' texts
- extra fields the schema allows: `unit_evidence`, `extraction.tier`, `components`,
  variants for the ambiguities in [[the-12-fields]]
- **omits** missing fields instead of emitting `0`

**Tests**

| layer | test |
|---|---|
| **L5 schema** | validates against `challenges/bilan/schema/results.schema.json` with `jsonschema` (already installed) |
| L4 | every `bbox` in `[0,1]`; every `field_key` belongs to the 12; `unit` is `count` **only** for `META_AVG_WORKFORCE` |
| L4 | no `0` value emitted for a missing field |
| L2 | `pdf` matches the real path on disk |

**Exit criterion:** the JSON validates. *"A submission we cannot parse is a submission we
cannot score."* From here on, the submission exists.

---

## E9 · Cost measurement · 0.3 h

**Input** the run itself  →  **Output** `run` block + `reports/cost.json`

Implements [[cost-per-page]]: `time.perf_counter()` per stage, a count of pages processed,
and — if E11 happens — an accumulator of input/output tokens with the published price and
the date it was checked.

Without a VLM, the honest answer is:

```json
"run": {
  "cost_eur_per_page": 0.0,
  "seconds_per_page": 0.0,
  "pages_processed": 415,
  "model": "provided OCR + rules",
  "notes": "No API calls made. Time measured with perf_counter over N runs..."
}
```

The schema explicitly accepts `"provided OCR + rules"` as a value for `model`.

**Tests**

| layer | test |
|---|---|
| L4 | `pages_processed` matches the routing count |
| L1 | the token meter accumulates correctly across simulated calls |

**Exit criterion:** the `run` block is filled in by **measurement**, not a hand-written
constant. A test that fails if any number in the block is a literal in the code.

---

## Links

- [[00-roadmap]] · [[phase-1-foundation]] · [[phase-3-coverage]] · [[testing-strategy]]
