---
type: implementation
stage: E4
tags: [code, numbers, parsing, tests]
status: draft
updated: 2026-09-16
---

# E4 — number parsing

**State:** done · 262 green tests, 4 skipped · `ruff` clean
**Exit criterion:** ✅ every case from F003 and F004 passes, **including the negatives** —
the parser refuses rather than invents.

## What was created

```
src/liasse/text/numbers.py   ParsedNumber · parse_amount · _is_well_formed · _sign_of
tests/unit/test_text_numbers.py   26 cases, almost all transcribed from the corpus
```

```python
parse_amount([...])  # ['1', '805', '459']        -> 1805459
parse_amount([...])  # ['2', '096)']              -> -2096
parse_amount([...])  # ['1', '476747']            -> None   (refused)
```

## The three rules

### 1 · Scan right to left

A number's structure is anchored on the right: groups form starting from the units digit.
Reading left to right there's no way to know whether a leading `1` opens a new number or
closes the previous one.

### 2 · Syntactic validation — the real filter

A well-formed French value is a sequence of three-digit groups with a one-to-three-digit
group in front. If the grouping reaches into the neighboring column, the result violates
that shape and is **refused**.

```
2 524 | 1 | 805 | 459   ->   groups [2][524][1][805][459]
                             the middle "1" has 1 digit: no such value exists
```

Measured exception: an **isolated** group of any length is accepted. The OCR sometimes
loses the thousands separator (`62614`, `509582` in the corpus) and the digits are
unambiguous. What stays refused is a long group **next to others** — the signature of two
merged cells, not of a missing space. These make up 0.4% of digit groups.

### 3 · Sign, in three forms

All on the same page (F004):

```
-  | 45 | 440)     loose minus on the left         -> -45 440
(  | 52 | 814)     open paren as its own token     -> -52 814
2  | 096)          only the closing paren survived -> -2 096   <- the GV field
```

The third is the serious one: `GV` is `PL_FINANCIAL_RESULTS_FRGAAP`, one of the 12 fields.
A parser that strips punctuation reads **+2,096** and flips the sign of a filed value.

## The decision the test forced: why the scan stops

The first design returned the rightmost valid number whenever grouping failed. One of my
own tests exposed the problem: `1 | 476747` (printed `1 476 747`, with a missing
separator) returned **476747** — off by a million, silently.

The right distinction isn't *whether* the scan stopped, it's **why**:

| stopped because of | means | outcome |
|---|---|---|
| **distance** | the token to the left is another cell | confident: return what was assembled |
| **shape**, within distance | two merged cells, or a split beyond recovery | **`None`** |

Refusing is the point. A plausible-looking fragment is the one failure mode nothing
downstream can detect — not the schema, not the verifiers, not a visual check.

## Calibrating the distance threshold

Measured over the 28 liasse pages in scope, the two populations **don't overlap**:

| | gap | in digit widths |
|---|---|---|
| within one number | **1 – 12 px** | 0.04 – 0.45 |
| between columns | **173 – 195 px** | 6.5 – 7.3 |

Median digit width: 26.7 px. The **4.0-width** threshold sits in the middle of a gap
spanning more than an order of magnitude — any value between ~0.5 and ~6 behaves the same.
Above ~7 it reaches the neighboring column and the shape check then refuses entire rows:
correct behavior, but it loses values.

The test locks in the **property**, not the number:

```python
assert widest_within_a_number < GAP_IN_DIGIT_WIDTHS < narrowest_between_columns
```

## Two measurements that unraveled along the way

Worth recording because both were plausible and both were wrong.

**"Reading more values is better."** With the threshold tightened to 0.5 the parser read
535 values and refused zero — and it was reading **fragments**, silently. Counting values
read doesn't measure correctness. (This stopped being possible once the "why it stopped"
rule was in place.)

**"55 reads are fragments."** A detector I wrote flagged 55 cases where the parser
consumed fewer tokens than were available. I went to check: **all 55 are two adjacent
columns**, N and N−1, 173–195 px apart. The parser was right; the detector was the one
producing a false positive, because the digits of the two columns, concatenated,
happened to form a valid-looking sequence.

## Money is never `float`

`int` when there's no decimal part, `Decimal` when there is. E7's verifiers compare exact
equalities (`CO == EE`, `FJ + FK == FL`); with `float` an arbitrary tolerance would be
needed, which hides real reading errors. A test scans the results and fails if any of them
is a `float`.

## What this stage found and left for E5

Running the identity `FJ + FK == FL` across the 6 pages of form 2052:

```
FJ=4 982 166 + FK=358      = 4 982 524   FL=4 982 524   OK
FJ=1 802 935 + FK=2 524    = 1 805 459   FL=1 805 459   OK
FJ=5 175 314 + FK=389 266  = 5 564 580   FL=5 564 581   discrepancy of 1 EUR in the document
FJ=1 048 023 | FK empty | FL=1 048 023 | 891 185        two columns: N and N-1
FJ=1 770 709 | FK=30 117  | (no FL code) | 1 800 826    lost code (F009)
```

None of these is a parser error:

- the **1 € discrepancy** is in the document itself — subtotals rounded independently of
  the total. E7's verifiers will need a tolerance policy, and it has to be justified by
  this, not picked arbitrarily;
- the **two columns** are column selection, already anticipated in
  [[F011-v1-confirmed-and-the-column-structure]] as `Anchor(form, code, column)`;
- the **lost code** is the ordinal fallback from [[idea-01-code-anchoring]].

## Next

[[phase-2-extraction|E5 — liasse extractor]]: the declarative field catalog, the anchor
ladder, and the column selection this stage made visible.

## Links

- [[E3-row-reconstruction]] · [[idea-02-digit-reassembly]]
- [[F003-the-ocr-breaks-numbers-apart]] · [[F004-negatives-are-printed-in-parentheses]] · [[F011-v1-confirmed-and-the-column-structure]]
