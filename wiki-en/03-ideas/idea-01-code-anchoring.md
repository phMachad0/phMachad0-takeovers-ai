---
type: idea
tags: [extraction, liasse, core]
status: draft
updated: 2026-09-16
---

# ❶ Anchoring by liasse code

## The problem

The instinctive path to extract "Montant net du chiffre d'affaires" is to search for that
string in the OCR and grab the nearest number. Call this **label anchoring**.

Four reasons, all observed in the corpus, why that's fragile:

**1. OCR corrupts French.** On the same page 006 of `65784e5da67d84faf4042736` the OCR
produced `du Code géñéral des impôts` and `article S3 A`. Field labels run 30 to 60
characters, with many chances to go wrong. Fuzzy matching fixes part of this and
introduces a new problem: what threshold? Too high and you miss the label; too low and
`Achats de marchandises` matches `Achats de matières premières`.

> **Correction (2026-09-16).** This objection holds for **discriminating between ~50 long,
> similar-looking labels inside a table**, which is the problem at step 3 of this ladder.
> It does not hold for classifying a page among **four** distinct titles — there, fuzzy
> matching is the right answer, and the tolerance can be derived from the vocabulary's
> separation instead of hand-tuned. See [[ADR-003-title-matching]]. I had generalized the
> objection past its actual reach.

**2. One label designates several cells.** `Chiffres d'affaires nets` is a single row with
three values — France (`FJ`), Exports (`FK`), and Total (`FL`). The challenge wants the
total. Finding the label doesn't tell you which column to take; you'd have to infer the
column from horizontal position, which is one more heuristic to calibrate and get wrong.

**3. The label breaks mid-word.** Observed: `Avances et acomptes sur immobilisa` on one
line and `tions incorporelles` on the next, because the cell is narrow. No reasonable
fuzzy match reconstructs that.

**4. The plaquette uses a different label.** `Autres achats et charges externes` in the
liasse becomes `Autres achats & charges externes` or `Services extérieurs` depending on
the software.

## The idea

**The two-letter code is the field's stable identifier. Anchor on it.**

`FL` means "chiffres d'affaires nets, total" in every French liasse, always — it's fixed
by law, printed by the form rather than typed by the accountant, and has **two
characters** for the OCR to get wrong instead of sixty.

Extraction becomes a dictionary lookup against a known format:

```python
FIELD_MAP = {
    "PL_REVENUE_FRGAAP":        Anchor(code="FL", form="2052"),
    "BS_CAPITAL_EQUITY_FRGAAP": Anchor(code="DA", form="2051"),
    "BS_TOTAL_EQUITY_FRGAAP":   Anchor(code="DL", form="2051"),
    "BS_TOTAL_ASSETS_FRGAAP":   Anchor(code="CO", form="2050"),
    "PL_PERSONNEL_COSTS_FRGAAP":  Derived(codes=["FY","FZ"], op="sum"),
    "PL_COGS_FRGAAP":             Derived(codes=["FS","FT","FU","FV"], op="sum"),
    ...
}
```

## Why this is more than "use an identifier"

What actually changes isn't match robustness. It's that **the mapping table becomes an
explicit, reviewable domain artifact**, separate from the code that walks it.

A label-based pipeline embeds business knowledge in scattered regexes. A code-based
pipeline has a declarative map that a French financial analyst — who doesn't know
Python — can read and correct. In a company that sells exactly this kind of knowledge,
that's the difference between a script and a product.

## The fallback ladder (the part that can't be skipped)

Anchoring on code **doesn't work alone**, for two measured reasons:

- **7 of the 15 documents have no codes at all** — they're plaquettes. See
  [[F001-half-the-corpus-is-not-liasse]].
- **Even in liasses, the OCR drops codes.** On the verified page 006, `FS`, `FT`, `FU`,
  `FV`, `FW`, and `FX` were not read, even though the labels and values on those same
  rows were. See [[F005-the-ocr-loses-part-of-the-code-column]].

So anchoring is **rung 1 of a ladder**, and each rung records which one was used:

| rung | method | when | confidence |
|---|---|---|---|
| 1 | code read directly from OCR | liasse, code present | high |
| 2 | **ordinal position in the template** | liasse, code missing | medium-high |
| 3 | label with tolerant fuzzy match | plaquette, or rungs 1-2 failed | medium |
| 4 | VLM on the page image | everything failed or the verifier rejected it | variable |

**Rung 2 is the interesting part, and it's what nobody does.** Form 2052 has a row order
fixed by law. If you've read `FY` and `FZ`, you know where they sit on the page, and you
know `FW` is exactly 3 rows above `FY` in the template — so you can **infer the row
position of `FW`** and read the value in the right column, even without ever having seen
the token `FW`. The template is a coordinate system, and two known anchors are enough to
locate the rest.

This is interpolation over a known grid — exactly the kind of reasoning that comes from
working with fixed-layout record formats.

## How to measure whether it worked

For each of the 12 fields × 15 documents, record which rung produced the value:

```json
{"field_key": "PL_EXT_SERVICES_COSTS_FRGAAP", "value": 329158,
 "extraction": {"tier": 2, "anchor": "ordinal_from_FY", "code_read": false}}
```

And report the distribution. A table showing "62% of values came from rung 1, 18% from
rung 2, 14% from rung 3, 6% from rung 4" **is** the answer to the cost/accuracy question,
because each rung has a different cost and a different error rate — measured by
[[idea-05-verifier-as-router]].

## Links

- [[liasse-codes]] · [[plaquette-vs-liasse]] · [[F005-the-ocr-loses-part-of-the-code-column]]
- [[idea-05-verifier-as-router]] · [[ADR-003-title-matching]]
