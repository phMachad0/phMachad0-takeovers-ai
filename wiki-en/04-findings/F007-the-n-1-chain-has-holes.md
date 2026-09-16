---
type: finding
id: F007
tags: [verification, corpus, limitation]
status: draft
updated: 2026-09-15
---

# F007 — the N−1 chain has holes, and needs measuring before it's promised

**Impact: high for planning. Limits the reach of verifier V3.**

## Claim

Verifier V3 in [[idea-05-verifier-as-router]] depends on two documents from the same
company covering **consecutive fiscal years**. Across the 15 in-scope documents that holds
for **7 of the 10 possible pairs**, and only **3 pairs** link two liasses.

## Evidence

Closing dates per company, from [[F006-the-meta-json-hands-over-the-closing-date]]:

| siren | closing dates | consecutive pairs | pair formats |
|---|---|---|---|
| `820561470` | 2021-08-31 · 2022-08-31 · 2023-08-31 | **2** ✅ | plaq→plaq, plaq→plaq |
| `328024377` | 2020-06-30 · 2021-06-30 · 2022-06-30 | **2** ✅ | **plaq→liasse**, liasse→liasse |
| `445070311` | 2020-06-30 · ~~2021~~ · 2022-06-30 · 2023-06-30 | **1** | plaq→plaq |
| `504304205` | 2016-12-31 · 2017-12-31 · ~~2018–2019~~ · 2020-12-31 | **1** | liasse→liasse |
| `401009741` | 2022-04-30 · 2023-04-30 · ~~2024~~ · 2025-04-30 | **1** | liasse→liasse |

**7 pairs out of 10.** Three companies have a one- or more-year gap in the middle.

This confirms the brief's warning — *"The deposit dates are not evenly spaced — some filed
late, or twice in a year"* — but what matters isn't the deposit, it's the **clôture**, and
the brief doesn't say there are gaps in it.

## Consequences for the plan

1. **V3 doesn't cover everything.** The accuracy metric can't be announced as "cross-checked
   against the prior year" without qualification. The honest phrasing is: *"N values were
   cross-checked against a second, independent document; the rest were verified only by V1
   and V2."*
2. **The `328024377` 2020→2021 pair is the most valuable one in the corpus.** It links a
   plaquette to a liasse: the same fiscal year (2020-06-30) appears as column N in the
   plaquette and as column N−1 in the liasse. It's **cross-validation between the two
   extractors** — if both read the same number, both paths are right at the same time. No
   other pair does that.
3. This is a **strong argument for building the plaquette extractor** and not just the
   liasse one: without it, this pair is lost and V3 drops to 3 pairs.
4. If coverage runs short, the brief allows pulling extra documents from data.inpi.fr to
   close the gaps. The cost/benefit is questionable within 6–8h — worth recording as "not
   done, and why."

## Pending

- Measure how many of the 12 fields × 7 pairs actually produce a cross-check (depends on
  column N−1 being present and legible in both).

## Links

- [[idea-05-verifier-as-router]] · [[F006-the-meta-json-hands-over-the-closing-date]]
- [[plaquette-vs-liasse]] · [[corpus-and-scope]]
