---
type: implementation
stage: E6
tags: [code, units, trap, tests]
status: draft
updated: 2026-09-16
---

# E6 — units

**State:** done · 298 green tests, 4 skipped · `ruff` clean
**Exit criterion:** ✅ no value ships without `unit_evidence`.

```
all 8 liasse documents -> EUR
Bernachon: 8 markers found, 6 kEUR markers evaluated and REJECTED
```

## What was created

```
src/liasse/units/resolver.py   Marker · CapitalAnchor · UnitEvidence · TypedValue
                               find_markers · find_capital_anchor · compare_scales · resolve
tests/unit/test_units_resolver.py
```

## The trap, and why the right answer is the counterintuitive one

The brief warns that ignoring the question is off by 1000x and points at `328024377`.
Searching that company's filing for the kEUR marker **finds one** — and applying it is the
mistake, not the fix.

Every kEUR marker in the corpus belongs to **one annexe table**, the list of subsidiaries,
whose own header reads `Tableau réalisé en Kilo-euros`. The balance sheet in the same
filing is in euros: `DA` reads **152,500**, and the same document's legal cover page
spells out `au capital de 152 500 euros` in full. See
[[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]].

A `grep` for the marker across the whole document divides that balance sheet by a
thousand.

**Unit isn't a property of the document. It's a property of the block**, and a marker has
a governance scope — resolving one is a scoping question, like resolving a variable.

## The three signals

| signal | what it does |
|---|---|
| scoped marker | only governs the page it's on; measured: no marker in the corpus shares a page with a statement |
| form default | liasse ⇒ EUR, by legal instruction, not by guessing |
| **capital anchor** | `au capital de 300.000 Euros` on the cover — a second declaration of the same order of magnitude, with the currency spelled out |

The anchor is a French legal requirement, so it exists in almost every corporate document.
It works in **12 of 15**, across every separator style: `10 000`, `300.000`,
`1.000.000`, `1 000 000`.

### Where it doesn't exist, and why

`401009741` is an **SAS à capital variable** and so doesn't print a fixed figure on the
cover. The anchor's absence in these three documents is a fact about the company, not a
failure to find it. The test asserts exactly that.

### What the anchor validates — and what it doesn't

Found while measuring: in `820561470/6543d3fd` the cover says **150,000** and the balance
sheet says **10,000**.

Not an error. The cover declares capital **as of the filing date**; the balance sheet, at
**fiscal year-end**. There was a capital increase in between.

So the anchor corroborates **scale**, not equality. `compare_scales` splits the three
cases:

| relationship | reading |
|---|---|
| equal | strongest corroboration of the unit |
| different, same order of magnitude | capital increase between close and filing — **a note**, unit unchanged |
| three orders of magnitude apart | this is what a kEUR filing looks like from the outside — **flagged for human review** |

The third case doesn't occur in this corpus. It exists for when it does, and it
**doesn't auto-convert** — it flags.

## `rejected_markers` is the field that communicates

```json
"unit_evidence": {
  "rule": "form_default_eur",
  "anchor": {"amount": 152500, "currency": "euros", "page": 20,
             "snippet": "au capital de 152 500 euros"},
  "rejected_markers": [
    {"snippet": "Les montants sont indiqués en K€.", "page": 12,
     "reason": "outside every page carrying an extracted value"}
  ]
}
```

Two deliverables can share the same `value` and the same `unit`. Only one demonstrates
that the trap was **seen, weighed, and rejected**. That's this field's job.

## Proof that the tests catch the error

| mutant | result |
|---|---|
| marker applies to the whole document (the naive *grep*) | fails ✅ |
| loose scale threshold (1000x stops looking suspicious) | fails 2 tests ✅ |

And one test writes the avoided error out as a number:

```python
assert capital.value == 152_500
assert capital.value / 1000 == 152.5   # what applying the marker would have produced
```

## A ghost test I wrote and deleted

The first version had a test that asserted nothing:

```python
def test_a_cover_that_disagrees_in_amount_but_not_in_scale_is_only_a_note():
    typed, _ = _typed("6543d3fd…") if False else (None, None)
```

A test that asserts nothing is worse than no test: it counts as coverage without covering
anything. The fix was extracting the scale decision into a pure function,
`compare_scales`, and testing it with seven cases — which also improved the design.

## Next

[[phase-2-extraction|E7 — verifiers]], the central stage: V1 stops being a check script and
becomes the verifier that measures accuracy **and** routes cost.

## Links

- [[E5-liasse-extractor]] · [[idea-06-unit-with-scope]] · [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]]
- [[units-eur-vs-keur]] · [[ADR-002-schema-ambiguities]]
