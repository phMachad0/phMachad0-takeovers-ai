---
type: finding
id: F001
tags: [format, corpus, critical]
status: draft
updated: 2026-09-14
---

# F001 — 7 of the 15 in-scope documents are not liasses

**Impact: high. Shapes the pipeline architecture.**

## Claim

Of the 15 documents in the bilan challenge's scope, only **8 contain DGFiP forms with the
two-letter code column**. The other **7 are plaquettes** produced by accounting software,
with no codes at all. The brief doesn't mention this split.

## Method

For every page of every in-scope document, two independent signals:

- **header**: regex `DGF[iI]P` against the page's concatenated text
- **codes**: count of distinct tokens matching `^[A-Z][A-Z0-9]$`, threshold ≥ 12

## Result

| siren / doc_id                           | pg. | pages with ≥12 codes | DGFiP header | format              |
| ---------------------------------------- | ---- | ----------------------- | --------------- | ------------------ |
| `820561470` / `6493e4372f502414800f8164` | 17   | —                       | —               | **plaquette**      |
| `820561470` / `6543d3fd08093cdace058668` | 15   | —                       | —               | **plaquette**      |
| `820561470` / `67458f18cea78a70070fa226` | 13   | —                       | —               | **plaquette**      |
| `328024377` / `63e8ebbb54febda17c19ee7c` | 29   | —                       | —               | **plaquette**      |
| `328024377` / `63e8ebbb54febda17c19ee7d` | 43   | 2,3,4,5                 | 2,3,4,5         | liasse             |
| `328024377` / `63e8ebbb54febda17c19ee7e` | 42   | 2,3,4,5                 | 2,3,4,5         | liasse             |
| `445070311` / `63e2481c916269756a09542b` | 28   | —                       | —               | **plaquette**      |
| `445070311` / `65a4095d5fd178b16b09b860` | 58   | —                       | —               | **plaquette**      |
| `445070311` / `6860f28ca0138eae340c7453` | 32   | —                       | —               | **plaquette**      |
| `504304205` / `63e13943526e1f30cd100db5` | 28   | 4…23 (12 pg.)          | 4…23            | full liasse    |
| `504304205` / `63e13943526e1f30cd100db6` | 30   | 4…23 (12 pg.)          | 4…23            | full liasse    |
| `504304205` / `66cd893cedec9b09d50191e8` | 33   | 4…19 (10 pg.)          | 4…21            | full liasse    |
| `401009741` / `63e881158be6eb9f9d1ff975` | 16   | 2,3,4,5                 | 2,3,4,5         | liasse             |
| `401009741` / `65784e5da67d84faf4042736` | 16   | 4,5,6,7                 | 4,5,6,7         | liasse             |
| `401009741` / `68f0a715f28d8aaf48046416` | 15   | **2,3 only**          | 2,3             | **partial** liasse |

Total: **415 pages**. The two signals agreed on all 15 documents.

## Textual evidence

Plaquette — `820561470/6493e4372f502414800f8164/page_007.json`:
```
SARL PAUTET ¦ Bilan Passif ¦ 31/08/2021. ¦ 31/08/2020 ¦
Capital social ou individuel ¦ 10 000 ¦ 10 000 ¦
```

Liasse — `328024377/63e8ebbb54febda17c19ee7e/page_003.json`:
```
[1884,34] DGFiP N° 2051 2022
[267,485] Capital social ou individuel (1)* (Dont versé :
[1953,473] DA   [2161,471] 152 500
```

## Consequences

1. The pipeline needs **two extractors** behind a format classifier. See
   [[plaquette-vs-liasse]].
2. A liasse-only pipeline covers 53% of the scope and **doesn't know it failed on the other
   47%** unless it's instrumented — which is the reason for
   [[idea-05-verifier-as-router]].
3. `401009741/68f0a715f28d8aaf48046416` only has 2050 and 2051. **The compte de résultat is
   not present in liasse form in this document** — probably it's a plaquette on another
   page, or wasn't filed. The 6 income-statement fields (`PL_*`) for this document need
   separate investigation. **Pending.**
4. This is the basis for the scoping decision: liasse first (deterministic and auditable),
   plaquette next, and saying so explicitly in the README.

## Reproduction

`scripts/recon/classify_formats.py` *(to be written — currently an ad hoc script in
scratchpad)*.

## Links

- [[plaquette-vs-liasse]] · [[idea-04-page-routing]] · [[idea-01-code-anchoring]]
