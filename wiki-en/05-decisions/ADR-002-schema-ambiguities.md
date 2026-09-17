---
type: decision
id: ADR-002
tags: [schema, fields, decision]
status: draft
updated: 2026-09-15
---

# ADR-002 — the five ambiguities in `financial_fields.json`

**Date:** 2026-09-15 · **Status:** accepted · **Approved by:** Pedro

## Context

`challenges/bilan/schema/financial_fields.json` defines each field with a `label_fr` and a
`notes`. In **five** of the twelve fields the two contradict each other, and the difference
changes the value — sometimes by orders of magnitude. See [[the-12-fields]].

There is no answer key and no one to ask. The decision has to be made and defended.

## General principle

Applied to all five:

1. Pick the more defensible reading, with a written reason.
2. Emit the chosen value in the schema's required fields.
3. **Emit the alternative reading in an extra field** — `results.schema.json` declares
   `additionalProperties: true` on `fields[]`, so this is allowed.
4. State the choice in the README in one line.

This turns each ambiguity from a risk of being wrong into evidence that the schema was read
closely. Emitting both figures makes the disagreement visible instead of silently picking
one — whichever reading someone expects, it's in the same JSON object.

Extra-field format:

```json
{
  "field_key": "PL_DEPRECIATION_AMORTIZATION_FRGAAP",
  "value": 149350, "unit": "EUR", "page": 4, "bbox": [...],
  "schema_ambiguity": {
    "reading_used": "GA+GB — depreciation charges on fixed assets",
    "conflict": "label_fr suggests all operating charges; notes says 'depreciation and amortisation'",
    "alternative": {"reading": "GA+GB+GC+GD", "value": 150019}
  }
}
```

---

## Decision 1 · `PL_COGS_FRGAAP` — `production stockée` is added

**Conflict.** `label_fr` says `Achats marchandises + matières + variations stocks +
production stockée`. Accounting logic says `production stockée` (`BZ`) should be
**subtracted**: it sits on the *produits* side of the form, and represents production cost
that hasn't yet become cost of sale. See [[cogs-a-la-francaise]].

**Decision.** Follow `label_fr` and **add** it:

```
COGS = FS + FT + FU + FV + FM(2052)
```

with the `cogs_excl_production_stockee` variant emitted in an extra field.

**Why.** `label_fr` is the only operational specification the company gave, and it is
explicit about the sign. It's probably what's in their own ledger. The economically correct
reading stays available alongside it, and the disagreement goes in the README.

**2026-09-15 correction.** This decision previously read
`COGS = FS + FT + FU + FV + BZ(2052)`, justified by a supposed collision between the `BZ`
on the 2050 form (`Autres créances`) and a `BZ` on the 2052 form (`Production stockée`).

**The collision doesn't exist.** The code for `Production stockée` on the 2052 form is
**`FM`**, correctly read in 3 of the 8 liasse documents. The only `BZ` seen on a 2052 page
is a false OCR read, where the entire code column got detected as a single line of vertical
text and recognized as `BZ` at 37% confidence. Full evidence in
[[F013-the-ocr-reads-the-code-column-as-vertical-text]].

What changes and what doesn't:

- the formula now uses **`FM`**;
- the anchor is still `(form, code, column)` — the real, confirmed collision is `CO`, which
  exists on both the 2050 and the 2054 with different meanings;
- `FM` is available in 3 of 8 documents, better than the 1 of 8 previously recorded for
  `BZ`, but still far from universal;
- when `FM` can't be recovered even by the ordinal fallback step, COGS is emitted
  **without it**, with `components` listing what went in and `confidence` reduced. Omitting
  a component and saying which one is better than silently assuming zero;
- the extractor needs the **sanity filter** from
  [[F013-the-ocr-reads-the-code-column-as-vertical-text]] (`score ≥ 0.80`,
  `orientation_angle == 0`, height ≤ 3× the page median) before accepting any token as a
  code. All three reject the false `BZ`.

---

## Decision 2 · `PL_DEPRECIATION_AMORTIZATION_FRGAAP` — `GA + GB`

**Conflict.** `label_fr`: `Dotations d'exploitation (amort. + prov.)` → suggests
`GA+GB+GC+GD`. `notes`: *"Depreciation and amortisation charged for the period"* →
suggests just `GA`.

**Decision.** `GA + GB` — charges **on fixed assets**. Variant `dna_incl_all_dotations`
(`GA+GB+GC+GD`) in an extra field.

**Why.** `GC` is a charge on current assets (roughly, estimated losses on doubtful
receivables) and `GD` is a provision for risks and charges. Neither is depreciation or
amortization under any usual definition, and including them would distort any EBITDA
calculation built from the field. `GA+GB` honors the `(amort. + prov.)` in `label_fr` by
including provisions, while restricting to fixed assets, which is what the `field_key`
names.

Both confirmed in the corpus in 3 of 8 documents ([[liasse-codes]]). `GB` is usually empty
— many companies don't provision against fixed assets — which in practice makes the field
equal to `GA` in most cases.

---

## Decision 3 · `BS_CAPITAL_EQUITY_FRGAAP` — `DA` alone

**Conflict.** `label_fr`: `Capital social + primes + réserves` → `DA+DB+DD+DE+DF+DG`.
`notes`: *"Called-up share capital (capital social)"* → just `DA`. This is the most direct
contradiction of the five.

**Decision.** `DA`. Variant `capital_equity_incl_reserves` in an extra field.

**Why.** Three converging reasons:

1. `notes` is more specific and uses the exact technical term (*called-up share capital*).
2. The aggregate `DA+DB+…+DG` is nearly `BS_TOTAL_EQUITY` (`DL`), which is already another
   one of the 12 fields — having two fields measure almost the same thing doesn't make
   sense in a 12-field schema.
3. **`DA` can be verified independently.** It's the value that the internal capital anchor
   from [[idea-06-unit-with-scope]] confirms: `au capital de 152 500 euros` on the legal
   cover page, a French statutory disclosure present in all 5 companies. No other reading
   has a second source within the document itself.

The third reason is decisive: a choice that can be verified beats one that can't.

---

## Decision 4 · `BS_CASH_CURRENT_ASSET_FRGAAP` — `CG + CE`, **Net** columns

**Conflict.** `label_fr`: `Disponibilités + VMP`. `notes`: *"Cash and cash equivalents
(disponibilités)"* → disponibilités only.

**Decision.** Sum disponibilités and VMP, **using the Net column codes**:

```
BS_CASH = CG (disponibilités, Net) + CE (valeurs mobilières de placement, Net)
```

**Why.** `label_fr` is explicit about summing, and VMP are short-term investments —
cash equivalents under most definitions, including IFRS. `notes` reads like a shorthand
gloss, not a restriction.

**Adjusted at E1.5 — and here the evidence changed the decision twice.**

*First:* the plan was `CF + CD`. But E1.5 showed that **each 2050 line has two codes**, one
per column:

```
Valeurs mobilières de placement | CD | 465 358 | CE | 465 358
Disponibilités                  | CF | 1 515 838 | CG | 1 515 838
```

`CD` and `CF` are the **Brut** (gross) cells; `CE` and `CG` are **Net**. The requested field
is the Net figure — for cash the two coincide, but VMP can carry a write-down and then they
diverge. Using `CE`/`CG` is correct by construction and doesn't depend on positional column
selection.

*Second:* there was a flagged risk that `CD` was only read in 3 of 8 documents, which could
produce `CF+CD` in one document and `CF` alone in another with nothing marking the
difference. **Checked, and the risk doesn't materialize.** In `401009741`, where `CD` is
missing, the VMP line exists, carries the code `CE`, and **has no value at all**:

```
DIVERS | Valeurs mobilières de placement | (empty) | CE
```

The company simply has no VMP. The absence is in the **value**, not the read. So:

- VMP absent ⇒ `BS_CASH = CG` alone, **correct**, no loss;
- the distinction that matters isn't "was the code read?" but "does the cell have a
  value?" — and that's directly observable;
- still, `components` records what went into the sum, so the difference between one
  document and another is explicit in the deliverable instead of implicit.

---

## Decision 5 · `META_AVG_WORKFORCE_FRGAAP` — three sources, in preference order

**Conflict.** Not a schema contradiction; an absence of a canonical source.
[[F010-actual-field-coverage]] measured: the data exists in **8 of 15** documents, in three
different places, and only 3 on the 2058-C form under code `YP`.

**Decision.** A source ladder, with decreasing `confidence` and provenance always carrying
where the value came from:

| order | source | form | `confidence` |
|---|---|---|---|
| 1 | liasse **2058-C**, code `YP` | table | 0.95 |
| 2 | annex, prose | `Effectif moyen du personnel 43 personnes` | 0.80 |
| 3 | *rapport de gestion* | `L'effectif salarié moyen à la clôture … 33 personnes` | **0.60** |
| — | not found | | **omit** |

`unit` is always `count`, never `EUR` — `financial_fields.json` is explicit: *"Not a
monetary value — do not attach a currency to it."*

**Source 3's semantic mismatch, stated plainly.** In `445070311` the text says *"effectif
salarié moyen **à la clôture de l'exercice**"* — average **at closing date**. The field
asks for *"Average number of employees **over the period**"* — average **over the period**.
These are different concepts.

Decision: **report it, with the mismatch written into the object itself.**

```json
{"field_key": "META_AVG_WORKFORCE_FRGAAP", "value": 33, "unit": "count",
 "page": 5, "bbox": [...], "confidence": 0.6,
 "snippet": "L'effectif salarié moyen à la clôture de l'exercice s'élève à 33 personnes",
 "semantic_note": "source says 'à la clôture de l'exercice'; the field asks for the period average"}
```

Omitting it would lose information that exists in the document. Reporting it without a note
would assert something the source doesn't say. The third path — report with the caveat —
is the only one that doesn't misstate anything in either direction.

**Where the data doesn't exist** (`401009741` and `820561470`, 6 documents), the field is
**omitted** and the README says this is because the source lacks it, not because the
pipeline failed. `financial_fields.json` mandates it: *"If a field is genuinely absent from
a document, omit it rather than reporting 0."*

---

## Consequences

1. **`fields/catalog.py` needs a `variant` type** alongside `Direct` and `Derived`, so the
   alternative reading is computed and emitted through the same path, without scattered
   conditional code. Adjust [[modular-architecture]].
2. **The anchor is `(form, code, column)`** — decisions 1 and 4 depend on this. `CO`
   collides between the 2050 and 2054; `CD`/`CE` and `CF`/`CG` distinguish Brut from Net.
3. **`Token` needs to carry `orientation_angle`**, which the E1 loader currently discards —
   it's one of the three signals in the sanity filter.
4. **`confidence` now has two sources**: verifier agreement
   ([[idea-05-verifier-as-router]]) and source quality (decision 5). The aggregation needs
   to combine both, and the README needs to explain the chosen semantics.
5. **The README gets a short section** listing all five choices in one line each, with the
   name of the extra field carrying the alternative.

## Accepted risks

- Whoever reads the results and expected the aggregate reading in decision 3 will see the
  primary value diverge from that expectation. Mitigated by the extra-field variant, but the
  primary field is what gets read first.
- Decision 1 emits an economically wrong number by choice. It's stated plainly, but it's a
  contestable choice and would be the first thing to revisit given any feedback.
- The ladder in decision 5 mixes three definitions under one `field_key`. Comparing
  `META_AVG_WORKFORCE` across companies in the corpus **is not valid** without checking
  `confidence` and `semantic_note`. That needs to be written in the README, not just here.

## Links

- [[the-12-fields]] · [[liasse-codes]] · [[cogs-a-la-francaise]]
- [[F013-the-ocr-reads-the-code-column-as-vertical-text]] ·
  [[F009-measured-code-loss]] · [[F010-actual-field-coverage]] ·
  [[F011-v1-confirmed-and-the-column-structure]]
- [[ADR-001-track-choice]] · [[phase-2-extraction]]
