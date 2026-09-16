---
type: meta
tags: [index]
status: draft
updated: 2026-09-15
---

# Index

Wiki for the **Takeovers — Data / ML Engineer, Bilan track** technical challenge.
Start with [[reading-guide]].

## 00 · Meta

| page | what it is |
|---|---|
| [[reading-guide]] | suggested reading order and wiki conventions |

## 01 · The challenge

| page | what it is |
|---|---|
| [[the-bilan-challenge]] | what was asked, how it's evaluated, the brief's hints |
| [[the-12-fields]] | the 12 fields, mapped to codes, with the schema's 5 ambiguities |
| [[corpus-and-scope]] | the 15 documents, 415 pages, the 5 companies |

## 02 · Concepts

| page                         | what it is                                                           |
| ------------------------------ | ----------------------------------------------------------------- |
| [[french-accounting-101]] | **domain entry point** — bilan, compte de résultat, annexe, SIREN |
| [[liasse-fiscale]]             | the standardized tax form: 2050, 2051, 2052, 2053, 2058-C   |
| [[liasse-codes]]          | **the most important page** — the two-letter codes, with a table |
| [[plaquette-vs-liasse]]        | the corpus's two formats; defines the architecture                  |
| [[cogs-a-la-francaise]]        | why COGS doesn't exist in the document and how to assemble it              |
| [[units-eur-vs-keur]]       | the factor-of-1000 trap                                     |
| [[takeovers-ocr-json]]      | the supplied OCR format, and what to trust in it                  |
| [[bbox-and-normalization]]        | the 3 coordinate systems and the conversion from 300 dpi to 0–1    |
| [[skew-and-geometry]]          | why 1° of tilt breaks parsing                      |
| [[cost-per-page]]           | how to derive €/page instead of guessing it              |
| [[french-glossary]]          | French → English, by document section                              |

## 03 · The six ideas

| page | in one line |
|---|---|
| [[00-overview]] | **how the six fit together** — start here |
| [[idea-01-code-anchoring]] | anchor on `FL`, not on "Montant net du chiffre d'affaires" |
| [[idea-02-digit-reassembly]] | `1`+`805`+`459` → 1,805,459, with validation and sign |
| [[idea-03-row-banding-with-skew]] | de-rotate before grouping rows |
| [[idea-04-page-routing]] | 415 pages → the 75 that matter |
| [[idea-05-verifier-as-router]] | **the key idea** — the verifier measures accuracy and drives the cost decision |
| [[idea-06-unit-with-scope]] | unit is a property of the block, not of the document |

## 04 · Findings

| id | finding | impact |
|---|---|---|
| [[F001-half-the-corpus-is-not-liasse]] | 7 of the 15 documents have no liasse codes | high |
| [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] | Bernachon's `K€` governs the annexe, not the balance sheet | high |
| [[F003-the-ocr-breaks-numbers-apart]] | the OCR splits numbers at the thousands separators | high |
| [[F004-negatives-are-printed-in-parentheses]] | `GV`'s sign inverted by a lost parenthesis | high |
| [[F005-the-ocr-loses-part-of-the-code-column]] | `FS`…`FX` missing on an otherwise clean liasse page | medium-high |
| [[F006-the-meta-json-hands-over-the-closing-date]] | `fiscal_year_end` comes free from `meta/`; `typeBilan` isn't a usable signal | medium |
| [[F007-the-n-1-chain-has-holes]] | only 7 of 10 N−1 pairs exist; 3 link liasses | high for planning |
| [[F008-degenerate-boxes-and-top-edge-banding]] | 3.5% of tokens have a degenerate box; **band by the top edge, not the center** | high |
| [[F009-measured-code-loss]] | code coverage on the 2052 ranges from 55% to 92%; the ordinal fallback is mandatory | high |
| [[F010-actual-field-coverage]] | 2 docs with no income statement; average headcount present in only 8 of 15 | high |
| [[F011-v1-confirmed-and-the-column-structure]] | **V1 closes 3/3**; the 2050 has 3 columns and the field is **Net** | high |
| [[F012-blank-pages-and-page-sizes]] | 10% of pages have no OCR; **only 21% are A4** — assuming A4 misses by 2 lines | high |
| [[F013-the-ocr-reads-the-code-column-as-vertical-text]] | the false `BZ`: the OCR read the code column as vertical text. Corrects an error of mine | high |
| [[F014-the-registry-announces-the-confidential-income-statement]] | `confidentiality` in `meta/` predicts the missing income statement — **5 of 5**. A legal absence, not a failure | high |
| [[F015-the-ocr-skew-is-not-the-residual]] | `skew_angle` is what the OCR **already corrected**, not what's left over. Applying it makes things worse | high |

## 06 · Execution plan

| page | what it is |
|---|---|
| [[00-roadmap]] | **the roadmap** — two tracks, 13 steps, the cut policy |
| [[modular-architecture]] | layers, typed contracts, the 4 extension points |
| [[testing-strategy]] | the 6 oracles and the 7 test layers |
| [[phase-1-foundation]] | E0–E4: scaffold, geometry, routing, rows, numbers |
| [[phase-2-extraction]] | E5–E9: extractor, units, verifiers, deliverable, cost |
| [[phase-3-coverage]] | E10–E12 + README, and the cut policy |

## 07 · Implementation

| step | page | state |
|---|---|---|
| **E0** | [[E0-scaffold]] | done — 23 tests, `ruff` clean |
| **E1** | [[E1-corpus-and-geometry]] | done — 100 tests; the diff matches on 2,729 tokens |
| **E2** | [[E2-page-routing]] | done — 200 tests; **60 of 415 pages**, a 6.9× reduction |
| **E3** | [[E3-row-reconstruction]] | done — 231 tests; tokens grouped into rows |
| **E4** | [[E4-number-parsing]] | done — 262 tests; numbers reassembled, sign and rejection |
| **E5** | [[E5-liasse-extractor]] | done — 278 tests; **75 fields**, V1 closes 7/7 |
| **E6** | [[E6-units]] | done — 298 tests; everything in EUR, 14 kEUR markers rejected |
| **E7** | [[E7-verifiers]] | done — 322 tests; V1 8/8, V2 17/17, **V3 caught a €423 error** |
| **E8** | [[E8-emitting-results-json]] | done — 340 tests; **`results.json` validates** |
| **E9** | [[E9-cost-measurement]] | done — 370 tests; **`run` block measured**, VLM curve derived |
| **E10** | [[E10-plaquette-extractor]] | done — 396 tests; **14/15 documents, 117 values**; V4 compares the two formats |
| **E11** | [[E11-vlm-escalation]] | done — 453 tests; full path wired, **never invoked** (no credential) |
| **E12** | [[E12-workforce-in-prose]] | done — `META_AVG_WORKFORCE` from 1 to **6 of 15** documents, from running text |

## 05 · Decisions

| id | decision |
|---|---|
| [[ADR-001-track-choice]] | Bilan track over Actes |
| [[ADR-002-schema-ambiguities]] | the 5 contradictions in `financial_fields.json`, closed |
| [[ADR-003-title-matching]] | word-level fuzzy matching instead of wildcards tuned to the sample |

## 99 · AI

| page | what it is |
|---|---|
| [[how-i-used-ai]] | living draft of the README's mandatory section |

---

## Open questions

Collected from the pages. Each one is a question that still has no evidence.

- [ ] `445070311/6860f28c`: OCR with scrambled reading order and no headings. Recovered
      by labels, but value extraction there is questionable ([[E2-page-routing]])
- [ ] Is there any bilan in kEUR anywhere in the corpus, outside the 15 in scope?
      ([[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]])
- [ ] How many of the 12 fields × 7 pairs actually produce an N−1 cross-check? ([[F007-the-n-1-chain-has-holes]])

---

*Resolved:* **where the income statement is for documents with no 2052** — legally absent
([[F014-the-registry-announces-the-confidential-income-statement]]) · **plaquette
signature** ([[E2-page-routing]]) · **E0 — scaffold** ([[E0-scaffold]]) · `pymupdf`
installed · **the 5 schema ambiguities** ([[ADR-002-schema-ambiguities]]) · **E1.5 — the 11
codes confirmed in the corpus** ([[liasse-codes]]) ·
measured loss rate ([[F009-measured-code-loss]]) · closing date ([[F006-the-meta-json-hands-over-the-closing-date]]) · identity
of `504304205` (`denomination` in the meta) · N−1 chain mapped ([[F007-the-n-1-chain-has-holes]]).
