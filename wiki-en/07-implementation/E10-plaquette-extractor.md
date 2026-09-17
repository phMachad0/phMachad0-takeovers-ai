---
type: implementation
stage: E10
tags: [code, plaquette, columns, verification, tests]
status: draft
updated: 2026-09-16
---

# E10 — plaquette extractor

**State:** done · 396 passing tests, 4 skipped · `ruff` clean

**What changed in the deliverable:**

| | before | after |
|---|---:|---:|
| documents read | 8 of 15 | **14 of 15** |
| companies | 3 of 5 | **5 of 5** |
| values emitted | 75 | **117** |
| values with at least one check | 36% | **36%** (42 of 117) |
| active verifiers | 6 | **8** (V1b and V4 are new) |

The 15th document (`6860f28c`) is still unreadable and **says so in the file**, instead of
showing up with an empty field list.

## What was created

```
src/liasse/text/columns.py         recovers the column grid from the page geometry
src/liasse/fields/plaquette.py     the 12 fields as plaquettes print them
src/liasse/extract/plaquette.py    label anchoring + column selection
src/liasse/verify/checks.py        V1b (plaquette balance) and V4 (cross-format agreement)
tests/unit/test_text_columns.py         8 tests
tests/unit/test_extract_plaquette.py   14 tests
```

**Nothing downstream changed shape.** Units (E6), verifiers (E7), confidence, and emission
(E8) operate on `RawValue` and don't know which extractor produced the value. That's the
return on the investment in [[modular-architecture]], and it's measurable: the new
extractor cost three modules and zero changes in five.

---

## The central decision: the column grid comes from the geometry

A liasse tells you which cell is which — the row carries its code and the value sits next
to it. A plaquette tells you nothing. It prints 2, 4, or 6 columns and names them in a
header the OCR frequently mangles: `31/08/2021.` with an extra period, `du 01/07/19 / au
30/06/20 / 12 mois` spread across three lines.

So the grid does **not** come from the header. It comes from repetition: every figure in a
column is printed at the same horizontal position, dozens of times per page. The header is
one line that has to survive; the positions are attested by every filled row.

Numbers are right-aligned in every plaquette in the corpus, so the **right edge** is the
stable extremity.

### The error this avoids

Reading a row left to right. A row whose second cell is empty — an asset with no
depreciation, an expense with no prior-year figure — shifts every following figure one
position to the left, and the third column's number comes back as if it were the second
column's. It's the right shape, the right order of magnitude, and completely wrong.

Belonging to a column is **positional**, so an empty cell contributes nothing instead of
shifting its neighbors.

### And a measurement error I made and fixed

I measured the distribution of distances between consecutive right edges and read a valley
between 124 px and 152 px. I set the threshold at 140, and the result pages went from 6
columns to 3.

The measurement was wrong. The 81–124 px band is **not** dispersion within a column: it's
the distance from a values column to the **percentage** column printed next to it. A
threshold above that merges the two — exactly the failure the module exists to prevent.

The real valley is at the other end of the distribution. Measured across 1,382 figures:

```
within one column      max 52 px between consecutive edges
between two columns     min 81 px
```

Threshold at **65 px**, in the gap. The two values differ by a factor of two, and the first
one only made it into the code because the result pages changed shape in a visible way.

## The second decision: which column is the current fiscal year

Almost always the first one — the plaquette puts the current fiscal year on the left and
whatever it adds (prior year, percentage, variation) on the right. The exception is
**assets**, which starts with Brut and Amortissements and prints the number you actually
want third.

I tried detecting this arithmetically: if `col0 − col1 = col2` for most rows, the page has
the Brut/Amort/Net shape. **It doesn't work alone.** A liabilities page that prints N, N−1,
and the variation between them satisfies the same identity, because the variation *is* the
difference — and on that page column 2 is the Ecart, not the value.

The fix: the **router already said which statement this is**
([[E2-page-routing]]). The identity is used to **confirm** a layout, never to discover it:

```python
if statement != BS_ASSETS or len(grid) < 3:
    return 0
return 2 if _looks_like_brut_amort_net(lines, grid) else None
```

And the `None` is deliberate: an assets page with three or more columns that does **not**
satisfy the identity is not read. An unread page is a gap; a page read one column off is a
set of plausible, wrong numbers.

## The third: an empty cell in a plaquette is **not** zero

In a liasse, an empty cell in an existing row means null, and E5 records it that way. Here
it can't: the plaquette prints section headers — `CAPITAUX PROPRES`, `DISPONIBILITÉS ET
DIVERS` — whose words match the row right below them and which carry no figure at all.

So a label only counts when the row it's on **actually prints something** in the column
being read. This same rule is also what makes it safe to accept a header as a label: one of
the dialects prints the total shareholders' equity **on the header row itself**.

## Three dialects, and the shape the catalogue had to take

| | liasse | dialect A | dialect B | dialect C |
|---|---|---|---|---|
| revenue | `Chiffres d'affaires nets` | *not printed* | `Chiffres d'affaires nets` | *not printed* |
| capital | `Capital social ou individuel` | same | same | `Capital (Dont versé : …)` |

Hence two shapes: a **term** is a row to find, with the spellings its wording can take; a
**reading** is a whole way of assembling the field from terms. Revenue has two readings,
because dialect A doesn't print a total row and the number has to be assembled from
`Ventes de marchandises + Production vendue`. Readings are tried in order and **the first
one that resolves fully wins** — a printed total always beats a sum we assemble ourselves.

Every spelling in the file was read off a corpus page. None was anticipated.

---

## Three real OCR defects that only showed up here

**Word split in half.** `Dispon bilités` — two tokens, neither one edit away from
`disponibilités`. Fixed by joining one token to the next and retrying, under the same edit
tolerance; it doesn't invent a match that wasn't already almost there. `BS_CASH` for one
document went from missing to 1,545,314.

**Minus sign glued to the digits.** `-76778`. The liasse prints negatives with
parentheses, so E4 never encountered this convention. Without the fix, the financial result
came out **positive** — and the same document's liasse says −76,778, which V4 now confirms.

**Loose parenthesis.** `365 359)` on a marketable securities line. A closing parenthesis
*is* how this corpus prints negatives, so the parser has no way to tell — and shouldn't try
to: I tried requiring the opening parenthesis, and that **broke the liasse**, where form
2052 prints `(76,778)` and the OCR delivers `76,778)`, with the arithmetic check confirming
it's negative. The reasoning was right and the conclusion was wrong.

The discrimination has to come from evidence the parser doesn't have. On the assets page it
does exist, and it's the same identity that identified the Net column: a Net whose sign
breaks `Brut − Amort = Net` and whose **magnitude** satisfies it wasn't negative. One
corpus line is fixed this way.

**A stray mark glued to the number.** `963 002 '`, `-97 957 :`. The whole token was
rejected, taking with it two terms of a cost-of-goods figure the document clearly prints.
Now a single trailing character from a small set is tolerated.

---

## V4 — the strongest check in the suite

Three documents in scope carry **both formats of the same fiscal year**. They're produced
by different software from the same ledger, and here they're read by two pipelines that
share no anchoring logic whatsoever: one follows two-letter codes, the other recovers a
column grid from geometry and matches French labels. Nothing is common to both beyond the
underlying fact.

The other checks compare a document **against itself** — a total against its own terms, one
page against another page of the same form. This one compares against an independent
statement, and it's the only one able to catch a value where both pages of a form agree and
both are wrong.

**Result: 21 of 23 agree** (91%). And the agreements are almost all *exact or off by €1* —
because the two formats round independently: the liasse is filled in whole euros and the
plaquette prints figures rounded from centimes. The same plaquette even prints
`Résultat de l'exercice exprimé en centimes | 164,172.52`.

The **two real disagreements** are not reading errors and are reported with confidence 0.30
and `checks_failed: ["V4"]`:

| field | liasse | plaquette | difference |
|---|---:|---:|---:|
| `PL_DEPRECIATION_AMORTIZATION` | 321,856 | 324,901 | **3,045** |
| `PL_EXT_SERVICES_COSTS` | 1,339,065 | 1,339,068 | 3 |

The first has an explanation: the plaquette condenses depreciation and provisions into a
single line, and the liasse separates them —
[[ADR-002-schema-ambiguities]] chose `GA+GB`, which excludes provisions on current assets.
**The two numbers measure slightly different things.** The second, €3 on a single printed
total, rounding doesn't explain and I don't know how to explain.

## V1b — the plaquette balance check

Without it, the 7 plaquette-only documents would carry values no check had ever looked at.
It's the same identity the brief points to — *"it must reconcile against the other side"* —
read from two different pages of the accountant's presentation, through two independently
recovered column grids. **Closes 7 of 7.**

## State of the verifiers

```
V0  5/5   100%      V2a 6/6   100%      V3  6/10   60%   (the €423 disagreement from E7)
V1  8/8   100%      V2b 6/6   100%      V4 21/23   91%   (the two above)
V1b 7/7   100%      V2c 5/5   100%
```

## What was left out, on purpose

- **The plaquette's N−1 column.** Only the current column is read, so a plaquette-to-
  plaquette pair doesn't run V3. Detecting which column is the prior year requires telling
  apart the `%` and `Variation` columns, and V4 delivers stronger evidence for the same
  effort.
- **`META_AVG_WORKFORCE`** doesn't appear on any routed plaquette page. Left for E12, which
  looks for it in the annexe's running text.
- **`6860f28c`.** The OCR returns this document's tables in scrambled reading order: the
  rows can't be reconstructed and there's no recoverable grid. It's the natural candidate
  for E11.
- **`TOTAL situation nette`** from `63e2481c` was **not** read as `BS_TOTAL_EQUITY`. Net
  equity position and shareholders' equity are close concepts, not identical ones;
  reporting one as the other would be a silent interpretation. The field is left absent.

## Links

- [[plaquette-vs-liasse]] · [[F001-half-the-corpus-is-not-liasse]] · [[modular-architecture]]
- [[E5-liasse-extractor]] · [[E7-verifiers]] · [[E9-cost-measurement]]
