---
type: finding
id: F010
tags: [scope, coverage, critical]
status: draft
updated: 2026-09-15
---

# F010 — actual field coverage: two documents without an income statement, and workforce present in 8 of 15

**Impact: high. Defines what's honestly deliverable.**

## A · Two of the eight liasse documents have no compte de résultat

Already known for `401009741/68f0a715f28d8aaf48046416`
([[F001-half-the-corpus-is-not-liasse]]). A second one confirmed:

`504304205/66cd893cedec9b09d50191e8` (filed 2024-08-06) contains:

```
p2  2065-SD     IS declaration
p3  2065 bis-SD annexe
p4  2050        BILAN - ACTIF        68 codes
p5  2051        BILAN - PASSIF       36 codes
p6  2054        IMMOBILISATIONS     104 codes
p7  2054 bis    écarts de réévaluation
p8  2055        AMORTISSEMENTS      116 codes
p9  2056        PROVISIONS           48 codes
p10 2057        ÉCHÉANCES            37 codes
```

**No 2052, no 2053.** The filing brings the balance sheet and the analytical schedules, but
not the income statement.

Consequence: **6 of the 12 fields (all the `PL_*` ones) don't exist in these two
documents.** The right answer is to omit them — `financial_fields.json` is explicit:
*"If a field is genuinely absent from a document, omit it rather than reporting 0."* And to
say in the README that they were omitted because the source doesn't have them, not because
the pipeline failed. The distinction matters.

## B · `META_AVG_WORKFORCE` is present in 8 of 15 documents, in three different places

Searching for `effectif`, `salarié`, `nombre moyen` across the 15 documents:

| siren | docs with the datum | where | form |
|---|---|---|---|
| `504304205` | **3 / 3** | liasse **2058-C**, code `YP` | canonical ✅ |
| `328024377` | **3 / 3** | annexe, running text | `Effectif moyen du personnel 43 personnes` |
| `445070311` | **2 / 3** | *rapport de gestion*, p5 | `L'effectif salarié moyen à la clôture … 33 personnes` |
| `401009741` | 0 / 3 | — | only `Participation des salariés`, which is something else |
| `820561470` | 0 / 3 | — | only `masse salariale` in a comment |

**8 of 15.** And of those 8, only 3 in the canonical location with a code.

### A semantic trap in `445070311`

The text says *"effectif salarié moyen **à la clôture de l'exercice**"* — average workforce
**as of the closing date**. The requested field is *"Average number of employees **over the
period**"*. These are different concepts: a point-in-time average and a period average.

Proposed decision: **report the value**, because it's the best evidence available in the
document, **with the discrepancy declared** in an extra field:

```json
{"field_key": "META_AVG_WORKFORCE_FRGAAP", "value": 33, "unit": "count",
 "confidence": 0.6,
 "semantic_note": "source says 'à la clôture de l'exercice', not 'moyen sur l'exercice'"}
```

Omitting it would lose information; reporting it without a note would assert something the
source doesn't say.

## C · What this means for the deliverable

Availability matrix, **before** any question of extraction quality:

| | 6 `PL_*` fields | 4 `BS_*` fields | `META_AVG_WORKFORCE` |
|---|---|---|---|
| `401009741` (3 liasse) | 2 of 3 docs | 3 of 3 | **0 of 3** |
| `504304205` (3 liasse) | 2 of 3 docs | 3 of 3 | **3 of 3** ✅ |
| `328024377` (2 liasse + 1 plaq.) | 3 of 3 | 3 of 3 | **3 of 3** |
| `445070311` (3 plaquette) | needs E10 | needs E10 | 2 of 3 |
| `820561470` (3 plaquette) | needs E10 | needs E10 | **0 of 3** |

This is a **ceiling**, not a forecast. No pipeline, however good, extracts what isn't on
the page. Knowing this before coding avoids chasing fields that don't exist and avoids
mistaking absence for a bug.

It's also direct material for the README: the difference between *"couldn't extract this"*
and *"not in the document"* is a distinction worth documenting on its own — it's exactly
the honesty a pipeline like this should be judged on.

## Links

- [[the-12-fields]] · [[F001-half-the-corpus-is-not-liasse]] · [[corpus-and-scope]]
- [[phase-3-coverage]]
