---
type: finding
id: F009
tags: [ocr, liasse, codes, critical]
status: draft
updated: 2026-09-15
---

# F009 — code loss, measured: the ordinal rung is mandatory

**Impact: high. Promotes refinement rung 2 to the main path.**

Generalizes [[F005-the-ocr-loses-part-of-the-code-column]], which had observed the
phenomenon on a single page.

## Method

A **data-derived** baseline, not external knowledge: for each form, the **union of codes
observed** across every page of that form in the 8 liasse documents. Then, each page's
coverage against that union.

The union underestimates the form's real total (a code the OCR never read in any document
never enters it), so **the percentages below are optimistic**. The real loss is higher.

## Result

| form | observed union | coverage per page |
|---|---|---|
| 2050 — Bilan Actif | 76 codes | 81% · 89% · 90% · 90% · 90% · 90% · 93% · 93% |
| 2051 — Bilan Passif | 41 codes | 87% · 87% · 87% · 90% · 90% · 90% · 90% · 92% |
| **2052 — Résultat** | 52 codes | **55% · 69% · 71% · 86% · 92% · 92%** |
| 2053 — Résultat suite | 37 codes | 67% · 70% · 75% · 78% · 78% |

**2052 is the worst-performing form, and it's the one carrying 6 of the 12 fields.**

## The codes that vanish are exactly the ones that matter

The `FS`–`FX` block — purchases of goods, inventory variations, purchases of raw materials,
**other external services** — is missing on **3 of the 6 pages of 2052** in scope:

```
63e8ebbb p4  (71%)  missing: BZ FM FN FO FP FQ FR FS FT FU FV FW FX RA
65784e5d p6  (69%)  missing:    FM FN FO FP FQ FR FS FT FU FV FW FX GK GL
63e88115 p4  (55%)  missing: BZ FC FF FI FL FM FN FO FP FQ FR FS FT FU …
```

The third row is the most serious: in `401009741/63e881158be6eb9f9d1ff975`, **code `FL` is
missing** — the code for net revenue, the most basic of the 12 fields.

## Consequences

1. **Rung 2 of the [[idea-01-code-anchoring]] ladder isn't a refinement; it's load-bearing.**
   Without it, `PL_EXT_SERVICES_COSTS` and all of COGS are unreachable in half the liasses,
   and revenue disappears entirely in one document.
2. **E5 can't close without rung 2 implemented and exercised.** This was already written
   into the exit criterion of [[phase-2-extraction]]; now there's a number backing it.
3. The loss pattern is **a contiguous block** (`FM`…`FX` disappears together). In at least
   one page the cause is identified and it isn't loss at all: the detector swallowed the
   entire block into a **single vertical box**
   ([[F013-the-ocr-reads-the-code-column-as-vertical-text]]). That opens a second recovery
   path beyond the ordinal rung — detect the vertical box and reassign the codes it covers
   by row position. This is good news for rung 2: surviving anchors bracket the lost block
   (`FL` above, `FY`/`FZ` below) and ordinal interpolation has both endpoints.
4. 2050 and 2051 sit at 81–93%, and the balance-sheet fields (`CO`, `EE`, `DA`, `DL`, `CF`,
   `CD`) were read on every page checked — the balance-sheet side is solid ground.

## Links

- [[F005-the-ocr-loses-part-of-the-code-column]] · [[idea-01-code-anchoring]]
- [[liasse-codes]] · [[phase-2-extraction]] · [[F013-the-ocr-reads-the-code-column-as-vertical-text]]
