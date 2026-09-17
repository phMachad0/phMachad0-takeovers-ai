---
type: concept
tags: [domain, liasse, form]
status: draft
updated: 2026-09-14
---

# The liasse fiscale

The **liasse fiscale** is the bundle of tax forms a French company files with the tax
administration (DGFiP) alongside its corporate income tax return. "Liasse" literally means
*bundle*, *sheaf of papers*.

The point that matters for this challenge: **these are official forms, of fixed layout,
defined by law** (article 53 A of the *Code général des impôts*). Every sheet has a DGFiP
number, every line has a fixed label and — crucially — **a two-letter code**. See
[[liasse-codes]].

## The sheets that matter

The **standard regime** (*régime réel normal*) uses this sequence:

| no. | French name | what it is | challenge fields |
|---|---|---|---|
| **2050** | Bilan — Actif | Balance sheet, Assets side | `BS_TOTAL_ASSETS`, `BS_CASH` |
| **2051** | Bilan — Passif | Balance sheet, Liabilities + equity | `BS_TOTAL_EQUITY`, `BS_CAPITAL_EQUITY` |
| **2052** | Compte de résultat (en liste) | Income statement, first half | revenue, COGS, personnel, services, D&A, financial result |
| **2053** | Compte de résultat, suite | Income statement, second half | `PL_INCOME_TAX` |
| 2054–2057 | fixed-asset, depreciation, provision and maturity schedules | analytical annexes | — |
| **2058-A/B/C** | tax profit determination, various reconciliations | book↔tax reconciliation | `META_AVG_WORKFORCE` |
| 2059-A…G | capital gains, allocation of results | — | — |

The **simplified regime** (*régime simplifié d'imposition*, RSI) uses a parallel family
numbered **2033-A to 2033-G**, and some companies file **2050-S, 2051-S, 2052-S, 2053-S**
variants. The line codes are **different**. In the corpus this shows up in
`data/328024377/bilans/ocr/694668d1887250a34b0508fa` (outside the scope of the 15, but proof
that the family exists and that the form classifier needs to tell them apart).

## How to recognize a liasse page

Two signatures, in order of reliability:

1. **Header** `DGFiP N° 2052 2023` in the top-right corner — form name + year.
2. **Code density**: a liasse page has dozens of isolated two-uppercase-letter tokens
   (`FL`, `DA`, `GV`…) in a narrow vertical column. Running text doesn't have that.

Both signatures were implemented and measured — see [[idea-04-page-routing]] and the
finding [[F001-half-the-corpus-is-not-liasse]].

## Why this is good news for the engineering

A liasse is, in practice, **a fixed-layout record format** — a struct serialized on paper.
The two-letter code is the field name; the cell to its right is the value. That turns
"document understanding" into "parsing a known format with geometric tolerance," which is a
much more tractable and much more testable problem.

The bad news is in [[F001-half-the-corpus-is-not-liasse]].

## Links

- [[liasse-codes]] · [[plaquette-vs-liasse]] · [[french-accounting-101]]
- [[idea-01-code-anchoring]] · [[idea-04-page-routing]]
