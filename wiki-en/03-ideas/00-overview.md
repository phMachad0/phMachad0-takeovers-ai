---
type: idea
tags: [architecture, index]
status: draft
updated: 2026-09-14
---

# The six ideas — overview

Six engineering decisions that, together, form the pipeline. Each one exists because a
fact measured in the corpus demands it — none is a generic "best practice."

## The chain

```
PDF (13-58 pages)
   │
   │  ❹ ROUTING: which pages matter?                    ← 415 pages → ~75
   ▼
relevant page
   │
   │  ❸ GEOMETRY: de-skew, group into rows
   ▼
reconstructed rows
   │
   │  ❶ ANCHORING: liasse code → field   (or label, if plaquette)
   │  ❷ NUMBERS: reassemble split digits, resolve sign
   ▼
candidate value + bbox
   │
   │  ❻ UNIT: EUR or kEUR, with scope and evidence
   ▼
typed value
   │
   │  ❺ VERIFICATION: balance-sheet identity, sums, N-1 column
   ▼
   ├── passes  → goes into results.json at high confidence
   └── fails   → escalates to VLM  → re-verifies  → goes in with confidence flagged
                 (and this is where the €/page number comes from)
```

## The six, in one line each

| # | idea | the fact in the corpus that requires it |
|---|---|---|
| ❶ | [[idea-01-code-anchoring]] | OCR corrupts French labels, but not `FL` |
| ❷ | [[idea-02-digit-reassembly]] | `1 805 459` arrives as three separate tokens |
| ❸ | [[idea-03-row-banding-with-skew]] | 1° of skew shifts by 43 px; a row is 35 px tall |
| ❹ | [[idea-04-page-routing]] | 415 pages in scope, ~75 with content |
| ❺ | [[idea-05-verifier-as-router]] | no answer key, but three internal checks |
| ❻ | [[idea-06-unit-with-scope]] | Bernachon's `K€` governs a table, not the document |

## What ties them together

❺ is the keystone. Without it, the other five are improvements with no metric. With it:

- ❺ produces the **accuracy number** the challenge says there's no answer key to produce;
- ❺ decides **when to spend money** on the VLM, which produces the €/page number;
- ❺ turns each of the other ideas into a **measurable experiment** — flipping ❸ on and
  off and watching the pass rate change is evidence, not opinion.

## Links

- [[the-bilan-challenge]] · [[plaquette-vs-liasse]] · [[cost-per-page]]
