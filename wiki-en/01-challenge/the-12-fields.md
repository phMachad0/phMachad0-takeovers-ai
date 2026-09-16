---
type: challenge
tags: [fields, schema]
status: draft
updated: 2026-09-15
---

# The 12 fields

Source: `challenges/bilan/schema/financial_fields.json`.

## Master table

`code` = proposed anchor in the liasse, see [[liasse-codes]].
`diff.` = estimated difficulty, 1 easy → 5 hard.

| # | field_key | EN | form | code | diff. |
|---|---|---|---|---|---|
| 1 | `PL_REVENUE_FRGAAP` | Net revenue | 2052 | `FL` | 1 |
| 2 | `PL_COGS_FRGAAP` | Cost of goods sold | 2052 | `FS+FT+FU+FV` ±`BZ` | **5** |
| 3 | `PL_PERSONNEL_COSTS_FRGAAP` | Personnel costs | 2052 | `FY+FZ` | 2 |
| 4 | `PL_EXT_SERVICES_COSTS_FRGAAP` | Third-party services | 2052 | `FW` | 2 |
| 5 | `PL_DEPRECIATION_AMORTIZATION_FRGAAP` | Depreciation and amortization | 2052 | `GA(+GB?)` | **4** |
| 6 | `PL_FINANCIAL_RESULTS_FRGAAP` | Financial result | 2052 | `GV` | **3** |
| 7 | `PL_INCOME_TAX_FRGAAP` | Income tax | 2053 | `HK` | 2 |
| 8 | `BS_TOTAL_ASSETS_FRGAAP` | Total assets | 2050 | line `CO`, **Net** column | 1 |
| 9 | `BS_TOTAL_EQUITY_FRGAAP` | Total equity | 2051 | `DL` | 1 |
| 10 | `BS_CAPITAL_EQUITY_FRGAAP` | Share capital | 2051 | `DA` | 1 |
| 11 | `BS_CASH_CURRENT_ASSET_FRGAAP` | Cash and equivalents | 2050 | `CG + CE` (Net) | **3** |
| 12 | `META_AVG_WORKFORCE_FRGAAP` | Average headcount | 2058-C | `YP` | **4** |

## The ambiguities — **decided in [[ADR-002-schema-ambiguities]]**

> All five were closed on 2026-09-15, with the adjustments brought by E1.5. Summary:
> COGS sums `BZ` · D&A = `GA+GB` · Capital = `DA` · Cash = `CG+CE` (**Net** columns) ·
> Workforce = a 3-source ladder with decreasing `confidence`.
> The sections below preserve the original reasoning; the ADR is the decision.

## The ambiguities that need a recorded decision

The schema is short, and in several places the `label_fr` and the `notes` **don't agree**.
Each divergence below needs to become a decision stated in the README.

### #2 COGS — does `production stockée` add or subtract?
`label_fr` says `+ production stockée`; accounting logic says subtract. Full discussion in
[[cogs-a-la-francaise]]. **Proposal:** follow the schema and emit the alternative variant
in an extra field.

### #5 D&A — fixed assets only, or all provisions?
`label_fr`: `Dotations d'exploitation (amort. + prov.)` — suggests `GA + GB + GC + GD`,
everything. `notes`: *"Depreciation and amortisation charged for the period"* — suggests
only `GA`. These are different things: `GC` is a provision on current assets (equivalent to
PECLD) and `GD` is a provision for risks, neither one is D&A in the usual sense.
**Proposal:** `GA + GB` (charges on fixed assets), record the choice, emit the full variant
in an extra field.

### #10 Capital — just `DA`, or capital + premiums + reserves?
`label_fr`: `Capital social + primes + réserves` — suggests `DA+DB+DD+DE+DF+DG`.
`notes`: *"Called-up share capital (capital social)"* — suggests only `DA`.
**The contradiction here is direct.** `notes` is more specific, and the `field_key` says
`CAPITAL_EQUITY`, which in financial taxonomies usually means paid-in capital.
**Proposal:** `DA`, with the aggregate variant in an extra field. And `DA` is the value that
the [[idea-06-unit-with-scope|capital anchor]] validates independently — which gives extra
confidence.

### #11 Cash — `disponibilités` only, or with VMP?
`label_fr`: `Disponibilités + VMP` → `CF + CD`.
`notes`: *"Cash and cash equivalents (disponibilités)"* → only `CF`.
**Proposal:** `CF + CD`, because VMP (short-term investments) are cash-equivalent under
most definitions, and the `label_fr` explicitly adds them. Record it.

### #12 Workforce — where to look when there's no 2058-C?
Only `504304205` has a 2058-C in scope. In the others, the number appears in the **annexe,
in running text**. Observed in `328024377/63e8ebbb54febda17c19ee7c/page_019.json`:
```
Effectif ¦ Effectif moyen du personnel 43 personnes
```
In other words: for this field the extraction is **from free text, not from a table**, and
needs its own path. It's a good candidate for VLM escalation, or for a regex over
`effectif moyen`.

## The pattern followed for every ambiguity

1. Choose the most defensible reading.
2. Emit the chosen value in the schema's required fields.
3. Emit the alternative reading in an extra field (`additionalProperties` is allowed).
4. Explain the choice in the README, in one line.

This turns each ambiguity from a risk of a silent error into a recorded, defensible
decision: whoever disagrees with the choice still finds the number they expected, in the
extra field.

## Links

- [[ADR-002-schema-ambiguities]] · [[liasse-codes]] · [[cogs-a-la-francaise]]
- [[units-eur-vs-keur]] · [[the-bilan-challenge]] · [[F010-actual-field-coverage]]
