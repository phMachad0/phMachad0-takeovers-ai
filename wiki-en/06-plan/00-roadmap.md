---
type: plan
tags: [roadmap, scope, time]
status: draft
updated: 2026-09-15
---

# Roadmap

Budget stated by the brief: **6 to 8 hours**, and the scope is deliberately larger than
that. So the roadmap isn't a list of everything that would be nice to have — it's an
**order of attack with an explicit cutting policy**.

## Principles that order the stages

1. **Whatever is the oracle for everything else, goes first.** The coordinate conversion
   (E1) and the verifiers (E7) validate everything that comes after. Building them early
   makes the rest testable.
2. **The deterministic path goes first.** It costs €0.00/page and is auditable. The VLM is
   an escalation rung, not the foundation.
3. **Always deliverable.** From E8 onward there is a valid `results.json`. Every later
   stage improves an artifact that already exists, rather than completing one that doesn't
   exist yet.
4. **README time is reserved up front.** It is never the variable that gets squeezed.

## The two tracks

### Track A — required · ~6.5 h

| E | stage | h | deliverable |
|---|---|---|---|
| **E0** | Project scaffold | 0.4 | `pytest` green, `.env.example`, locked deps |
| **E1** | Corpus + geometry | 0.8 | bbox conversion **validated against their own code** |
| **E2** | Page routing | 0.6 | `reports/routing.json` — 415 pages classified |
| **E3** | Row reconstruction | 0.9 | deskewed rows, with an A/B measurement |
| **E4** | Number parsing | 0.7 | reassembly + sign, covering the F003/F004 cases |
| **E5** | Liasse extractor | 1.1 | values for the 8 liasse documents |
| **E6** | Units | 0.3 | EUR/kEUR with scope and `rejected_markers` |
| **E7** | Verifiers | 1.0 | `reports/verification.json` — **the accuracy metric** |
| **E8** | Emit `results.json` | 0.4 | validates against the company's schema |
| **E9** | Cost measurement | 0.3 | derived `run` block, not guessed |

By the end of E9 there is a complete submission: 12 fields × 8 documents, with provenance,
resolved units, measured accuracy, and derived cost. **Coverage: 53% of the documents.**

### Non-negotiable reserve

| | | h |
|---|---|---|
| **README** + final `.env.example` + `results.json` review | | **0.8** |

**Track A + reserve = 7.3 h.** Already inside the ceiling, with no slack.

### Track B — in order of value, if time is left

| E | stage | h | what it buys |
|---|---|---|---|
| **E10** | Plaquette extractor | 1.0 | **53% → 100% of documents**, and unlocks the cross-validation pair from [[F007-the-n-1-chain-has-holes]] |
| **E11** | VLM escalation | 0.8 | the cost×accuracy **curve** instead of a single point |
| **E12** | Hard fields (`META_AVG_WORKFORCE` outside form 2058-C) | 0.5 | 1 field across ~7 documents |

**E10 before E11.** Without the plaquette, **two of the five companies are left with zero
values** — and the brief says the five were chosen to be different from each other, so a
2-company gap is visible. The cost curve is a nicer story, but coverage is a better result.

## The clock rule

**At 6 hours of work, stop building and start writing**, whatever state things are in. A
pipeline stuck at E7 with an honest README beats one at E11 with a rushed README — the
brief says this in so many words:

> *"If you run short, cut scope and say so — that is a better outcome than a wide,
> half-wired submission."*

---

## The stages, in detail

Each stage has an **input → output**, a verifiable **exit criterion**, and the **tests**
that close it. Nothing moves forward until the criterion is met.
See [[testing-strategy]] for the test taxonomy and the oracles.

Broken down across three pages:

- [[phase-1-foundation]] — **E0 to E4**: scaffold, geometry, routing, rows, numbers
- [[phase-2-extraction]] — **E5 to E9**: extractor, units, verifiers, deliverable, cost
- [[phase-3-coverage]] — **E10 to E12** + the README

## Dependency order

```
E0 scaffold
 └─ E1 corpus + geometry ───────────────┐
     ├─ E2 routing                      │
     │   └─ E3 rows (deskew)            │
     │       └─ E4 numbers              │
     │           └─ E5 liasse extractor─┤
     │               ├─ E6 units        │
     │               └─ E7 verifiers ───┤
     │                   └─ E8 emit ────┴─ E9 cost
     │                       │
     │                       ├─ E10 plaquette  (reuses E3, E4, E6, E7, E8)
     │                       └─ E11 VLM        (reuses E7 as trigger)
     └─ README (starts at E7, once there are numbers to cite)
```

The right-hand column is why [[modular-architecture]] matters in practical terms: **E10
reuses five stages and only adds one anchoring strategy.** If rows, numbers, units, and
verifiers were coupled to the liasse format, E10 would go from 1 hour to 3 and blow the
budget. Modularity here isn't aesthetic — it's what keeps full coverage inside the
deadline.

## What's already decided before starting

Open items from the [[index|backlog]] that need to be closed before E5, because the
extractor depends on them:

- [ ] confirm the still-unverified codes in the corpus: `CO`, `CF`, `CD`, `EE`, `HK`,
      `YP`, `FS`, `FT`, `FU`, `FV`, `FW` ([[liasse-codes]]) — **~30 min, it's E1.5**
- [ ] decide the schema's 5 ambiguities ([[the-12-fields]]) — **Pedro's decision**, becomes
      an ADR

Already resolved: `fiscal_year_end` comes from the meta
([[F006-the-meta-json-hands-over-the-closing-date]]), and the N−1 chain is mapped
([[F007-the-n-1-chain-has-holes]]).

## Links

- [[modular-architecture]] · [[testing-strategy]] · [[the-bilan-challenge]] · [[00-overview]]
