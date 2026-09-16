---
type: finding
id: F014
tags: [corpus, meta, scope, critical]
status: draft
updated: 2026-09-15
---

# F014 — the registry announces when the income statement is confidential, and the correlation is exact

**Impact: high. Explains the cause behind [[F010-actual-field-coverage]] and makes the
absence of the 6 income-statement fields predictable before opening the PDF.**

## Claim

`meta/*.json` carries a `confidentiality` field. When it reads
`"Partiellement confidentiel"`, the filing **does not contain the compte de résultat**.
Across the 15 in-scope documents the correlation is **5 of 5, no exception in either
direction**.

## Evidence

| document | `confidentiality` | has an income statement? |
|---|---|---|
| `820561470/6493e437` | **Partiellement confidentiel** | **no** |
| `820561470/6543d3fd` | **Partiellement confidentiel** | **no** |
| `820561470/67458f18` | **Partiellement confidentiel** | **no** |
| `328024377/63e8ebbb…7c` | Public | yes (plaquette p4) |
| `328024377/63e8ebbb…7d` | Public | yes (2052 p4) |
| `328024377/63e8ebbb…7e` | Public | yes (2052 p4) |
| `445070311/63e2481c` | Public | yes (plaquette p16, p17) |
| `445070311/65a4095d` | Public | yes (plaquette p27, p29) |
| `445070311/6860f28c` | Public | yes (plaquette p11) |
| `504304205/63e13943…b5` | Public | yes (2052 p6) |
| `504304205/63e13943…b6` | Public | yes (2052 p6) |
| `504304205/66cd893c` | **Partiellement confidentiel** | **no** |
| `401009741/63e88115` | Public | yes (2052 p4) |
| `401009741/65784e5d` | Public | yes (2052 p6) |
| `401009741/68f0a715` | **Partiellement confidentiel** | **no** |

In `820561470/6493e437` the filing goes straight from `Bilan Passif` (p7) to
`Annexes aux comptes annuels` (p8). There is no compte de résultat on any page.

## What it is

The **déclaration de confidentialité du compte de résultat** (art. L. 232-25 of the *Code de
commerce*). A small or medium-sized company can file its annual accounts declaring that the
income statement **not be made public**. The document is still submitted to the registry,
but the published copy ships without it, and the RNE flags the filing.

Note that `typeBilan` stays `"C"` (*complet*) across all 15 — it describes the accounting
regime, not the publicity level. See [[F006-the-meta-json-hands-over-the-closing-date]].

## Why this is worth so much

Because it turns a data gap into a **legally grounded statement**, available for free and
before any processing.

Without this finding, the README would say: *"in five documents I couldn't extract the
income-statement fields."* With it, it says:

> *"In five of the fifteen documents the six `PL_*` fields are **legally absent**: the
> company exercised the confidentiality option under art. L. 232-25 and the registry marks
> the filing as `Partiellement confidentiel`. The correlation between the flag and the
> absence is 5 of 5. The pipeline omits these fields because they're absent from the
> source, not because extraction failed, and it records which of the two cases applies."*

That's exactly the kind of distinction worth stating outright. And it's cheap: one lookup
against a metadata field.

## Consequences for the pipeline

1. **Routing signal D**, zero-cost and available before the PDF is even opened.
2. **Field ceiling per document**: `confidentiality == "Partiellement confidentiel"` ⇒ the
   6 `PL_*` fields will be omitted, with reason `legally_absent`.
3. **Inverted sanity guard**: if the pipeline *does* extract income-statement fields from a
   document flagged as confidential, something's wrong — probably an annexe page misread as
   the statement itself. That becomes a cheap verifier.
4. Lowers the honest denominator for the coverage calculation: 12 fields × 15 documents =
   180 isn't the target. The target is 180 − (6 × 5) = **150**, before even subtracting
   [[F010-actual-field-coverage|the average workforce missing in 7 documents]].

## Links

- [[F010-actual-field-coverage]] · [[F006-the-meta-json-hands-over-the-closing-date]]
- [[idea-04-page-routing]] · [[E2-page-routing]] · [[the-12-fields]]
