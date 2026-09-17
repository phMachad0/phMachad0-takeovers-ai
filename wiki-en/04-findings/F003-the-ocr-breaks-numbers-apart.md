---
type: finding
id: F003
tags: [ocr, parsing, critical]
status: draft
updated: 2026-09-14
---

# F003 — the OCR breaks numbers apart at the thousands separator

**Impact: high. Invalidates any naive parser.**

## Claim

In the liasse's value column, a number with a thousands separator reaches the OCR as
**several independent tokens**, one per group of three digits. The behavior is
**inconsistent within the same page**.

## Evidence

All from `data/401009741/bilans/ocr/65784e5da67d84faf4042736/page_006.json` (liasse 2052),
coordinates in px at 300 dpi:

**Broken into 3 tokens** — `FL` = chiffre d'affaires nets total (field `PL_REVENUE`):
```
[1925,734] "FL"   [2125,743] "1"   [2174,741] "805"   [2275,741] "459"
```
Correct value: **1 805 459**. Naive parser: **1**.

**Broken into 2 tokens** — `BZ` = production stockée:
```
[1913,801] "BZ"   [2199,812] "27"   [2275,812] "699"
```
Correct value: **27 699**.

**NOT broken** — `FK`, same column, same page:
```
[1502,740] "FK"   [1748,736] "2 524"
```
The space was preserved inside the token.

**Single token, 3 digits:**
```
[2274,1095] "243"     (Autres produits)
```

Four behaviors, one page.

## Gap geometry

On the `FL` row:

```
token      x0      gap from previous
"1"      2125      —
"805"    2174       ~20 px   ← inside the number
"459"    2275       ~50 px   ← inside the number
```

And the gap to the previous column (`FK` at x=1748, token `2 524` ending around x=1870) is
**~255 px**. The intra-number vs. inter-column separation differs by more than an order of
magnitude — the grouping threshold isn't delicate.

## Consequence

Reading a number has to be a **geometric grouping step with syntactic validation**, not a
string read. See [[idea-02-digit-reassembly]].

And as a corollary: the value's correct `bbox` is the **union of the accepted tokens'
polygons** — number reassembly and provenance boxing are the same problem. See
[[bbox-and-normalization]].

## Links

- [[takeovers-ocr-json]] · [[idea-02-digit-reassembly]] · [[F004-negatives-are-printed-in-parentheses]]
