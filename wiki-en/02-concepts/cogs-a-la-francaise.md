---
type: concept
tags: [domain, cogs, hard-field]
status: draft
updated: 2026-09-14
---

# COGS — the field that doesn't exist in the document

`PL_COGS_FRGAAP` is one of the two fields the brief calls "deliberately awkward". Worth
understanding why, because the difficulty is conceptual, not technical.

## Why it doesn't exist

There are two ways to organize an income statement:

- **by function** (Anglo-Saxon and IFRS standard): Revenue − COGS = Gross Profit −
  Operating Expenses…
- **by nature** (the standard of the
  [[french-accounting-101|Plan Comptable Général]]): Revenue, followed by every expense
  classified by *the type of thing purchased* — goods, raw materials, services, salaries,
  payroll taxes, depreciation.

The French compte de résultat is organized **by nature**. There's no line "Coût des
marchandises vendues". The value has to be constructed.

## The formula the schema asks for

`financial_fields.json` gives the field's French label, which in practice is the formula
itself:

> `label_fr`: **"Achats marchandises + matières + variations stocks + production stockée"**

Translated into [[liasse-codes]]:

```
COGS = FS  (achats de marchandises)
     + FT  (variation de stock — marchandises)
     + FU  (achats de matières premières et autres approvisionnements)
     + FV  (variation de stock — matières premières)
     − BZ? (production stockée)     ← see the sign discussion below
```

## Why "variation de stock" is added

Intuition: you want the cost of what **left** inventory, not what you **bought**.

```
consumption = purchases + (opening_stock − closing_stock)
```

And the French line `variation de stock` is defined precisely as
`opening_stock − closing_stock`. So:

- inventory **fell** in the period → `variation` positive → you sold more than you bought →
  add it to cost. ✓
- inventory **rose** → `variation` negative → part of what you bought is still sitting
  there → subtract it from cost. ✓

That's why the simple sum is correct, and why `variation de stock` frequently appears **in
parentheses** (negative) on the form. See [[F004-negatives-are-printed-in-parentheses]].

## The sign problem of `production stockée` (BZ)

Here's the decision that needs to be defended.

`BZ — Production stockée` is the change in inventory of **finished and in-progress goods**.
On form 2052 it sits on the **PRODUITS d'exploitation** side (revenue), not the charges
side. It's the accounting counterpart of the cost of producing something that hasn't been
sold yet.

- If `BZ` is positive, the company produced more than it sold, and the production costs of
  that inventory are already inside `FU`/`FV`/`FY`. To arrive at the cost **of what was
  sold**, you need to **subtract** `BZ`.
- The schema's label says `+ production stockée`, which suggests adding it.

**There's a conflict between the schema's label and the accounting logic.** Both readings
are defensible:

1. *Read it as the schema wrote it* — add `BZ`. Advantage: matches the schema's literal
   wording. Disadvantage: economically wrong.
2. *Read it as accounting requires* — subtract `BZ`. Advantage: correct. Disadvantage:
   diverges from the literal label.

**Proposed decision:** follow the schema (add it), and record the divergence explicitly in
the README and in an extra field of `results.json` (the schema allows
`additionalProperties`), for example `cogs_variant_excl_production_stockee`. Emitting both
figures makes the disagreement visible instead of silently picking one. This should become
an ADR under `wiki/05-decisoes/`.

## Provenance of a calculated value

The schema requires `page` + `bbox` for every value. But COGS is the sum of 4 to 5 cells.
What do you send?

Options:
- the `bbox` of the largest-magnitude cell (the one that "dominates" the value) — simple,
  defensible;
- the `bbox` that **encloses** all component cells (minimal bounding rectangle) — points to
  the right block of the page;
- the `bbox` of the main component, plus the full list of components in an extra field
  `components: [{code, value, page, bbox}]`.

**The third is clearly the best** and the schema allows it. A derived value with the full
arithmetic auditable is exactly the "number you can defend to a client" that the parent
Takeovers README describes.

## Links

- [[liasse-codes]] · [[the-12-fields]] · [[F004-negatives-are-printed-in-parentheses]]
