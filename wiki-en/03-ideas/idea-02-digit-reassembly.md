---
type: idea
tags: [extraction, parsing, numbers, core]
status: draft
updated: 2026-09-14
---

# ❷ Geometric digit reassembly

## The problem, with evidence

The OCR doesn't return `1 805 459`. It returns this, in
`data/401009741/bilans/ocr/65784e5da67d84faf4042736/page_006.json`:

```
[1925, 734] "FL"
[2125, 743] "1"      [2174, 741] "805"      [2275, 741] "459"
```

Three separate entries, because the French thousands separator is a **space**, and the
OCR's text detector splits on the wide spaces inside form cells.

A naive parser grabs the token closest to code `FL` and returns `1`. Or `459`, depending
on how it orders by proximity. In neither case does it *know* it got it wrong — the value
comes out with the right type, the right page, and a plausible bbox.

**This alone invalidates an entire pipeline**, and it's invisible to tests that only check
the schema.

And the splitting isn't uniform. On the same page:

```
[1749, 597] "2 524"          ← one token, space preserved
[2199, 812] "27"  [2275, 812] "699"   ← two tokens
[2274, 1095] "243"           ← one token (3-digit number, no separator)
```

Same document, same page, same column, three different behaviors. There's no single "OCR
format" to handle; there's a spectrum.

## The idea

Treat reading a number as a problem of **geometric clustering with syntactic
validation**, not as a string problem.

### The algorithm

```
input:  tokens on the row (same y-band), the x-range of the value column
output: numeric value + bbox covering all tokens used

1. filter to numeric tokens    — regex ^[\d.,()\-–—]+$  (accepts parentheses and sign)
2. sort by increasing x
3. sweep from RIGHT to LEFT, aggregating while:
      gap(token[i], token[i+1]) < GAP_MAX
   where GAP_MAX is derived from the row's average glyph width,
   not a constant in pixels
4. VALIDATE the syntax of the assembled group:
      - every group except the first (leftmost) has EXACTLY 3 digits
      - the first group has 1 to 3 digits
      - at most one decimal group, introduced by a comma
   if validation fails, the grouping is wrong → reject, don't guess
5. resolve the sign (see below)
6. bbox = union of the polygons of the accepted tokens
```

### Why sweep right to left

Because the structure of the number is anchored to the right. Groups of 3 digits form
starting from the units. Sweeping from the right, `459`, `805`, `1` assembles correctly;
sweeping from the left you can't tell whether `1` is the start of a number or the tail of
the previous one.

### Why step 4 is the important step

Step 4 is a **built-in error detector**. If the grouping merged two values from
neighboring columns, the result looks something like `[2 524][1][805][459]` — and the
middle group `1` violates "every non-first group has 3 digits." The pipeline **knows it
failed** and can reject instead of reporting `25241805459`.

A parser that doesn't validate group syntax has no way to tell a correct read from an
accidental concatenation. That's the difference between failing loudly and failing
silently — and the brief is explicit about which of the two it values.

### The adaptive `GAP_MAX`

A pixel constant breaks when the PDF's dpi changes, and `NOTICE.md` warns that some
documents were re-rendered at 150 dpi. The robust alternative:

```python
glyph_w = median(token_width / len(token_text) for token in numeric_tokens_on_line)
GAP_MAX = 1.8 * glyph_w        # the thousands gap is ~1 glyph; the gap between columns is ~10
```

Measured on the `FL` row: the tokens `1`(x=2125), `805`(x=2174), `459`(x=2275) have gaps
of ~20 px, while the gap to the previous column (`FK`, x=1748) is ~330 px. The separation
is more than an order of magnitude — the threshold isn't delicate, which is good news.

## The sign problem

French accounting writes negatives two different ways, and the OCR mangles both.
Observed on the same page 006:

```
Variation de stock (marchandises)
  [2110, 1314] "-"    [2201, 1313] "45"    [2271, 1307] "440)"
                                                       ↑ the closing paren stuck to the digit

Variation de stock (matières premières)
  [2108, 1457] "("    [2199, 1452] "52"    [2271, 1448] "814)"
                       ↑ the opening paren became an isolated token

RÉSULTAT FINANCIER (V - VI)     ← field PL_FINANCIAL_RESULTS!
  [1923, 3300] "GV"   [2136, 3306] " "   [2229, 3305] "2"   [2274, 3301] "096)"
                                                                          ↑ only the closing paren survived
```

The last case is the worst: `GV` is field `PL_FINANCIAL_RESULTS_FRGAAP`. The correct
value is **-2 096**. A parser that just strips punctuation reads **+2 096** and flips the
sign on one of the 12 requested fields, in a document where it's unambiguously negative
(the charges financières `GU = 2 096` and the produits financiers `GP` are blank).

**Sign rule, in order of precedence:**

1. A `)` stuck to the last token of the group, **or** a `(` as an isolated token to the
   left, inside the same column → **negative**.
2. A `-`, `−`, `–` token immediately to the left of the group and inside the column →
   **negative**.
3. Otherwise → positive, and the `sign` field of `financial_fields.json` rules: *"Report
   values as printed. Costs are positive unless the filing itself shows a negative."*

And the check that closes the case, without relying on any of these heuristics: **the
form's own arithmetic**. `GV = GP − GU`. If `GP` is blank and `GU = 2096`, then `GV` has
to be `−2096`. The sign doesn't need to be read — it can be **derived**. When the two
sources agree, confidence is high; when they disagree, it's a case to escalate. See
[[idea-05-verifier-as-router]].

## The bonus: the bbox comes for free

The union of the accepted tokens' polygons is exactly the rectangle bounding the printed
number — which is the `bbox` the schema asks for. Correctly reassembling the number and
getting the correct box are **the same problem, solved once**. See
[[bbox-and-normalization]].

## How to measure

Three cheap tests:

1. **Syntactic round-trip**: for every extracted value, reformat with the thousands
   separator and compare against the concatenation of the source tokens. Mismatch =
   grouping bug.
2. **Step 4 rejection rate**: how many groupings got rejected. If it's 0%, validation is
   probably too loose.
3. **N-1 cross-check**: see [[idea-05-verifier-as-router]]. A badly reassembled number
   almost never matches the same number read in the following year's document.

## Links

- [[takeovers-ocr-json]] · [[F003-the-ocr-breaks-numbers-apart]] · [[F004-negatives-are-printed-in-parentheses]]
- [[bbox-and-normalization]] · [[idea-05-verifier-as-router]]
