---
type: plan
tags: [roadmap, stages, cuts]
status: draft
updated: 2026-09-15
---

# Phase 3 — coverage and delivery (E10 → E12 + README)

Everything here is **track B**: it improves a deliverable that already exists and is
already valid. If the clock runs out, each of these can be cut without invalidating the
submission — as long as the cut is stated.

---

## E10 · Plaquette extractor · 1.0 h — *the highest-value one*

**Input** `LinedDoc` for pages classified as plaquette  →  **Output** `[RawValue]`

A new class implementing the same `Extractor` Protocol as E5. **Reuses E3 (rows), E4
(numbers), E6 (units), E7 (verifiers), and E8 (emission) unchanged** — this is exactly the
return on the investment made in [[modular-architecture]].

What changes: anchoring is by label, not by code, and column selection has to handle the
plaquette's extra columns (`%`, `Variation absolue`) that the liasse doesn't have. See
[[plaquette-vs-liasse]].

**What it buys**

- document coverage: **8/15 → 15/15**; company coverage: **3/5 → 5/5**
- unlocks the corpus's most valuable pair: `328024377` 2020→2021, the only one that links
  a plaquette to a liasse, letting the **two extractors validate each other** on the same
  fiscal year ([[F007-the-n-1-chain-has-holes]])
- V3 goes from 3 to 7 pairs

**Tests**

| layer         | test                                                                                                             |                                       |
| -------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| L2 golden      | `820561470` p7: `Capital social ou individuel                                                                     | 10 000` → `BS_CAPITAL_EQUITY` = 10000 |
| **L5 cross-check** | the 2020-06-30 fiscal year of `328024377` read from the plaquette (column N) **matches** the one read from the liasse (column N−1) |                                       |
| L6 negative    | the plaquette's `%` and `Variation` columns are **not** mistaken for values                                     |                                       |

The cross-check test is the strongest in the whole suite: two independent extractors, two
independent documents, one number.

---

## E11 · VLM escalation · 0.8 h

**Input** values that failed E7  →  **Output** corrected values + real cost

Only the relevant page, only the field that failed, image rendered at the lowest
resolution that still works — and **mandatory re-verification** on the way back. A value
that comes out of the VLM and fails again is **omitted**, not reported.

**What it buys:** the [[cost-per-page]] curve instead of a single point. The most
persuasive line in the table is the one showing that sending all 415 pages costs 5.5×
more and buys no extra accuracy.

**Tests**

| layer | test |
|---|---|
| L1 | the cost meter accumulates tokens from simulated calls; no real calls in tests |
| L6 | a VLM value that fails re-verification is omitted, not emitted |
| L4 | no real key shows up in logs, artifacts, or `results.json` |

**Security note:** `.env` is already in `.gitignore`. `.env.example` lists names only. The
brief is explicit: *"If you commit a live credential we will tell you so you can revoke
it, and it counts against you."*

---

## E12 · Hard fields · 0.5 h

`META_AVG_WORKFORCE` only appears on form 2058-C in `504304205`. In the others it shows up
in the **annexe's running prose**:

```
data/328024377/bilans/ocr/63e8ebbb54febda17c19ee7c/page_019.json
   Effectif ¦ Effectif moyen du personnel 43 personnes
```

That's free-text extraction, not table extraction — a short path of its own: a regex over
`effectif moyen`, or VLM escalation if E11 exists. Unit `count`, no currency.

---

## README · 0.8 h — *reserved, never cut*

Starts being written at E7, once there are numbers to cite. Structure:

| section | source |
|---|---|
| how to run | `make` |
| **the trade-off** | [[cost-per-page]] + `reports/cost.json` + `reports/verification.json` |
| what I measured and how | the oracles from [[testing-strategy]]; the verifiers measure **consistency, not truth** |
| **where I disagree with the brief** | [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] (the kEUR) and [[F001-half-the-corpus-is-not-liasse]] (half is plaquette) |
| schema decisions | the 5 ambiguities from [[the-12-fields]], with the alternative variant emitted as an extra field |
| **how I used AI** | [[how-i-used-ai]] — including where the tool got it wrong |
| **what I cut, and why** | the track-B stages that didn't fit |

The *"where I disagree with the brief"* section is what most sets the submission apart.
The top-level README asks for exactly this:

> *"Cross-checking one source against another sometimes helps, and sometimes tells you the
> sources disagree — which is itself a finding worth reporting."*

---

## Cutting policy

If the clock hits 6 h before E9:

1. **Never cut** the README or the `results.json` schema validation.
2. Cut **fields** before cutting **verification**. Six verified fields beat twelve
   unverified ones: *"A pipeline that does 6 fields well and says so beats one that
   reports all 12 with three of them silently wrong."*
3. Cut **documents** before cutting **provenance**. A wrong box is worse than a missing
   document: *"a number without a provenance is not something we can sell."*
4. Anything cut goes into the README **by name**, with the reason and what it would take
   to do it.

## Links

- [[00-roadmap]] · [[phase-2-extraction]] · [[how-i-used-ai]] · [[the-bilan-challenge]]
