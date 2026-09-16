---
type: finding
id: F011
tags: [verification, columns, positive]
status: draft
updated: 2026-09-15
---

# F011 — V1 confirmed live, and the column structure it revealed

**Impact: high, and it's good news.** The first finding in this project that confirms
something instead of complicating it.

## The test

Naive extraction of the value to the right of codes `CO` (2050, total assets) and `EE`
(2051, total liabilities) across three documents, compared against each other — verifier
**V1** from [[idea-05-verifier-as-router]].

```
328024377 / 63e8ebbb  CO = [8 754 311, 2 520 565, 6 233 746]   EE = [6 233 746]        ✅
401009741 / 65784e5d  CO = [1 781 360,   767 254, 1 014 105]   EE = [1 014 105]        ✅
504304205 / 63e13943  CO = [2 031 391,   223 533, 1 807 858,   EE = [1 807 858,
                            1 748 987]                               1 748 987]         ✅
```

**3 of 3.** The balance-sheet identity holds on every document tested, with a three-line
extractor run before any pipeline existed.

This serves as validation of two things at once: codes `CO` and `EE` are correctly mapped,
and V1 is implementable and discriminating.

## The column structure that surfaced

The test exposed something that needs to go into the extractor's design: **the number of
columns varies by form and by document.**

**Form 2050 (Actif) — three columns per fiscal year:**

```
TOTAL GÉNÉRAL (I à VI) | CO | 8 754 311 | IA | 2 520 565 | 6 233 746
                         ↑ Brut          ↑ Amortissements   ↑ Net
```

**Important correction, found later:** `CO` is not the code for total assets — it's the
code for the **Brut** cell. Field `BS_TOTAL_ASSETS_FRGAAP` is the third cell, the **Net**
one, and in this corpus it **has no code read against it**. Taking the value to the right of
`CO` returns gross assets: larger, plausible, and wrong. An error V1 catches immediately —
the argument for having V1.

The same two-codes-per-row pattern holds for the other 2050 accounts: `CD` Brut / `CE` Net
for marketable securities, `CF` Brut / `CG` Net for disponibilités.

So: **the code anchors the ROW; the column is chosen by position.**

**Form 2051 (Passif) — one column per fiscal year**, but the documents differ in how many
years they print: `328024377` and `401009741` show only N; `504304205` shows N and N−1
(`1 807 858` and `1 748 987`).

## Consequences for the architecture

1. **Column selection is an explicit step**, not an indexing detail. It needs to be part
   of `fields/catalog.py`:
   ```python
   "BS_TOTAL_ASSETS_FRGAAP": Direct(code="CO", form="2050", column="NET")
   "PL_REVENUE_FRGAAP":      Direct(code="FL", form="2052", column="TOTAL")
   ```
   Just as `FL` needs the *Total* column rather than *France* or *Exportations*
   ([[liasse-codes]]).
2. **The N−1 column comes for free in some documents** — it's the input to verifier V3
   ([[F007-the-n-1-chain-has-holes]]). In `504304205` it's on the same row, right next to
   it. Capturing it costs almost nothing and feeds the year-over-year cross-check.
3. **Column detection has to be positional, not ordinal by token count.** In `504304205`
   the numbers come broken apart (`'2','031','391'`) and in `328024377` intact
   (`'8 754 311'`) — counting tokens gives different results for the same structure.
   Anchoring on the `x` ranges of the column headers is the way to go.

## Links

- [[idea-05-verifier-as-router]] · [[liasse-codes]] · [[F003-the-ocr-breaks-numbers-apart]]
- [[F007-the-n-1-chain-has-holes]] · [[phase-2-extraction]]
