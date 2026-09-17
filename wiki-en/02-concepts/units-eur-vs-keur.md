---
type: concept
tags: [domain, units, trap]
status: draft
updated: 2026-09-14
---

# Units: EUR vs kEUR

The brief is blunt: *"A pipeline that ignores the units question is wrong by a factor of
1000 on some of these filings."* And the brief's table points a finger at one company:

> `328024377` — **reports in thousands of euros**, said in passing on a handful of lines

I investigated that claim against the corpus. **What I found doesn't confirm the obvious
reading.** See [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] for the full
evidence.

## Summary of the finding

Every mention of `K€` / `Kilo-euros` across the 15 in-scope documents is confined to **a
single table in the annexe**: the *Liste des filiales et participations* (list of
subsidiaries and equity investments). The phrase appears as a footnote to that table, and
its header explicitly says `Tableau réalisé en Kilo-euros`.

The balance sheet of the same company, in the same filing, is in **euros**:
`DA = 152 500`, `DL = 3 036 481`.

## The architectural lesson

The mistake this trap punishes is treating **unit as a property of the document**. It
isn't. Unit is a **property of a content block**, and the textual marker has a bounded
*scope of authority*.

```
document
 └── page 12
      └── block "Liste des filiales et participations"   ← unit = kEUR
           marker: "Tableau réalisé en Kilo-euros"
           marker: "Les montants sont indiqués en K€."
 └── page 3
      └── block "BILAN - PASSIF" (liasse 2051)           ← unit = EUR
           no marker ⇒ form's legal default
```

A blind `grep -i "K€"` across the whole document classifies Bernachon as kEUR and gets the
balance sheet wrong by 1000×. Exactly the error the brief describes — but by a different
path than the brief suggests.

## How to decide the unit with confidence

Three independent signals, and the value of using all three is that they can
**contradict each other in a detectable way**:

**1. Scoped textual marker.** Find `K€`, `en milliers d'euros`, `Kilo-euros`, but record
**where** it is (page, bbox) and **which block it governs** — the `layout` table's
rectangle, or the vertical distance to the next heading. If the marker is 30cm from the
value and there's a section title between them, it doesn't govern that value.

**2. Form default.** DGFiP forms 2050/2051/2052 are filled out **in euros** by legal
instruction. Absent a marker inside the block, euro is the default — and it's a strong
default, not a guess.

**3. Magnitude prior, cross-checked against another fact in the document.** This is the
tiebreaker. Take a value that appears **twice in the same document, in different places**,
and compare them. Bernachon: share capital appears on the balance sheet as `152 500`
(liasse 2051, `DA`) and on the legal cover page as `SA au capital de 152 500 euros` —
running text, with the word "euros" spelled out. Exact match ⇒ the balance sheet is in
euros, proven by the document itself.

This third signal is strong because it doesn't depend on outside knowledge or on a
heuristic like "this number looks too big". It's an **internal anchor**.

## What goes into `results.json`

The schema has `unit` per field, with enum `EUR | kEUR | count`. Since unit is a decision
backed by evidence, it's worth carrying that evidence along, in an extra field:

```json
{
  "field_key": "BS_CAPITAL_EQUITY_FRGAAP",
  "value": 152500, "unit": "EUR",
  "page": 3, "bbox": [...],
  "unit_evidence": {
    "rule": "form_default_plus_internal_anchor",
    "anchor_snippet": "SA au capital de 152 500 euros",
    "anchor_page": 1,
    "rejected_marker": {"text": "Les montants sont indiqués en K€.", "page": 12,
                        "reason": "scope limited to the 'Liste des filiales' block"}
  }
}
```

The `rejected_marker` field records that the marker was seen, weighed, and rejected, with
the reason — the difference between not noticing a trap and having judged it.

## Links

- [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] · [[idea-06-unit-with-scope]]
- [[the-12-fields]]
