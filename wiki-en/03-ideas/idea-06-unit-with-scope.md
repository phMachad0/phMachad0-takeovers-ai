---
type: idea
tags: [units, pitfall, extraction]
status: draft
updated: 2026-09-14
---

# ❻ Unit as a block property, with evidence

## The problem, and the trap inside it

The brief warns: *"A pipeline that ignores the units question is wrong by a factor of
1000 on some of these filings."* And points at: `328024377` — *"reports in thousands of
euros, said in passing on a handful of lines."*

The natural reaction is to write this:

```python
if re.search(r"K€|en milliers|Kilo-euros", full_document_text, re.I):
    unit = "kEUR"
```

**This is wrong, and it's wrong by exactly 1000×.** See
[[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] for the evidence.

What actually exists in document `63e8ebbb54febda17c19ee7e` of `328024377` is:

```
page 12:  "Liste des filiales et participations"
          "Tableau réalisé en Kilo-euros"
          ... the subsidiaries table ...
          "Les montants sont indiqués en K€."
```

And, in the same filing:

```
page 3:   DGFiP N° 2051 2022 — BILAN PASSIF
          DA  152 500        ← share capital, in EUROS
          DL  3 036 481      ← total capitaux propres, in EUROS
```

The `K€` marker governs **one table in the annexe**, not the document. A naive regex
divides the entire balance sheet by 1000 and produces a share capital of €152.50.

Every occurrence of `K€` / `Kilo-euros` across the 15 in-scope documents is tied to that
same table. **I did not find a single balance sheet in kEUR within the scope.**

## The idea

**Unit is not a property of the document. It's a property of the content block, and the
text marker has a bounded scope of governance.**

```
document  ─┬─ page 3  ─── block "BILAN PASSIF (2051)"     → EUR   (form default)
           └─ page 12 ─── block "Liste des filiales"      → kEUR  (explicit marker)
```

Resolving the unit is then a **scope resolution** problem, like resolving a variable
binding: find the nearest marker that *contains* the value, not any marker in the file.

### How to bound the scope in practice

Three delimiters, in order of precision:

1. **The table's rectangle from `layout`.** If `layout` detected the table and the marker
   sits inside (or immediately below) the same rectangle, the scope is the table.
   Precise when `layout` works — and it doesn't always.
2. **The block between titles.** The vertical band between the previous section title and
   the next one. A marker on page 12 doesn't reach page 3 by construction.
3. **Form boundary.** A value read inside a 2050/2051/2052 liasse is **by legal
   instruction** in euros, unless the form itself states otherwise in a designated box. A
   marker outside the form's page doesn't reach it.

### The three decision signals

| signal | strength | note |
|---|---|---|
| text marker **inside the value's scope** | strong | the only case where kEUR should be declared |
| form default (liasse ⇒ EUR) | strong | not a guess, it's legal instruction |
| **internal magnitude anchor** | decisive | see below |

## The internal anchor — the part worth having

The third signal is the best because **it doesn't depend on any heuristic or external
knowledge**.

Certain values appear **twice in the same document, in different records**: once as a
number in a table, once as running text with the unit spelled out.

Observed in `328024377`:

- page 3, liasse 2051: `DA  152 500`
- page 20, legal cover: `BERNACHON S.A. ... au capital de 152 500 euros`
- page 24, auditor's report: `SA au capital de 152 500 €`

Three independent records, same amount, and two of them **spell out the unit**. The
balance sheet's unit is proven by the document itself.

The same pattern appears in `820561470` (`SARL au capital de 10 000 euros` on page 17,
against `Capital social ou individuel | 10 000` on page 7) and in `445070311`
(`SAS au capital de 300.000 Euros` on page 2, against `300 000` on page 15). In other
words: the anchor isn't a trick that works for one document — it's a **structural pattern
of the document genre**, because stating share capital on the cover page is a French
legal requirement.

This is generalizable, cheap, and verifiable. And the anchor value is
`BS_CAPITAL_EQUITY_FRGAAP`, which is one of the 12 requested fields — so the anchor
**validates a deliverable field at the same time it resolves the unit for everything
else.**

## What goes into `results.json`

The schema allows `additionalProperties`. The unit is a decision; carry the decision:

```json
{
  "field_key": "BS_CAPITAL_EQUITY_FRGAAP",
  "value": 152500, "unit": "EUR", "page": 3, "bbox": [...],
  "confidence": 0.97,
  "unit_evidence": {
    "rule": "form_default + internal_capital_anchor",
    "anchor": {"snippet": "au capital de 152 500 euros", "page": 20},
    "rejected_markers": [
      {"snippet": "Les montants sont indiqués en K€.", "page": 12,
       "reason": "scope limited to the 'Liste des filiales et participations' block"}
    ]
  }
}
```

The `rejected_markers` array is the part that communicates. It records that the marker
was seen, weighed, and rejected, with the reason — the difference between not noticing a
trap and having judged it. A document without this field and one with it can carry the
same `value`, but only one of them shows that the trap was recognized.

## A necessary note of honesty

The brief states that `328024377` reports in thousands. **I could not confirm this across
the three in-scope documents for that company** — the balance sheet is in euros in all
three, and every kEUR marker belongs to the annexe's shareholdings table.

Three possible readings, and I don't know which is correct:

1. the brief's mention refers precisely to those annexe rows, and the wording is
   ambiguous;
2. there's a kEUR document that isn't among the 15 listed as in scope;
3. it's a deliberate trap, meant to be caught exactly like this.

The README should state all three and show the evidence. If this reading turns out to be
wrong, the reasoning behind it is laid out clearly enough to show what would change. If
it's right, it's the strongest finding in this submission.

## Links

- [[units-eur-vs-keur]] · [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] · [[the-12-fields]]
