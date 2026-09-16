---
type: finding
id: F004
tags: [ocr, parsing, sign, critical]
status: draft
updated: 2026-09-14
---

# F004 — negatives are printed in parentheses, and the OCR mangles the parenthesis

**Impact: high. Directly affects `PL_FINANCIAL_RESULTS_FRGAAP`.**

## Claim

Negative values on the French form are printed in parentheses. The OCR breaks that
parenthesis apart in different ways, and in at least one case **only the closing
parenthesis survives**, erasing the sign for any parser that strips punctuation.

## Evidence

From `data/401009741/bilans/ocr/65784e5da67d84faf4042736/page_006.json`:

**Case A — minus sign as a standalone token, closing parenthesis glued to the digit:**
```
Variation de stock (marchandises)
[2110,1314] "-"    [2201,1313] "45"    [2271,1307] "440)"
```
Value: **−45 440**.

**Case B — opening parenthesis as a standalone token:**
```
Variation de stock (matières premières et approvisionnements)
[2108,1457] "("    [2199,1452] "52"    [2271,1448] "814)"
```
Value: **−52 814**.

**Case C — the bad one. Only the closing parenthesis survived:**
```
2 - RÉSULTAT FINANCIER (V - VI)
[1923,3300] "GV"   [2136,3306] " "   [2229,3305] "2"   [2274,3301] "096)"
```
Value: **−2 096**. A parser that strips punctuation and concatenates digits reads **+2 096**.

`GV` is the code for `PL_FINANCIAL_RESULTS_FRGAAP` — **one of the 12 requested fields.** The
error flips the sign of a deliverable field.

## Arithmetic confirmation

Same page:
```
[1925,2872] "GP"                          ← Total des produits financiers (V): empty
[1923,3227] "GU"   [2230,3233] "2"  [2275,3231] "096"   ← Total des charges financières (VI)
```

`GV = GP − GU = 0 − 2 096 = −2 096`. **The sign is derivable from the form's own
arithmetic**, without depending on reading the parenthesis. See
[[idea-05-verifier-as-router]], verifier V2.

This is the strongest argument for having verifiers: where reading pixels is fragile, the
form's own structure provides a second, independent source.

## Consequence

A three-tier sign rule, with arithmetic as the final arbiter. Detailed in
[[idea-02-digit-reassembly]].

**Pending:** measure how many of the 12 fields × 15 documents are affected by sign errors.
Suspects: `PL_FINANCIAL_RESULTS` almost always (financial result tends to be negative for
leveraged SMEs), `PL_COGS` via inventory variations, and `BS_TOTAL_EQUITY` when PL is
negative.

## Links

- [[F003-the-ocr-breaks-numbers-apart]] · [[idea-02-digit-reassembly]] · [[french-glossary]]
