---
type: implementation
stage: E3
tags: [code, geometry, rows, tests]
status: draft
updated: 2026-09-16
---

# E3 — row reconstruction

**State:** done · 231 green tests, 4 skipped · `ruff` clean
**Exit criterion:** ✅ the golden cases pass **and fail** when the reported skew is
applied — the correction is being exercised.

## What was created

```
src/liasse/geometry/deskew.py   rotation + estimate of the REAL skew   (layer 0)
src/liasse/text/lines.py        PositionedToken · Line · banding       (layer 1)
tests/unit/test_geometry_deskew.py · test_text_lines.py
```

Here the page stops being a bag of text boxes and becomes something a value can be read
from: label on the left, code in the middle, number on the right, all knowably on the same
row.

```
Chiffres d'affaires nets * | FJ | 1 | 802 | 935 | FK | 2 524 | FL | 1 | 805 | 459
Salaires et traitements*   | FY | 499 | 659
Capital social ou individuel | 10 000 | 10 000
```

## This stage knocked down the very idea that motivated it

[[idea-03-row-banding-with-skew|Idea ❸]] said: the OCR delivers `skew_angle`, almost
nobody uses it, rotating by it fixes alignment. I implemented it, and it **broke rows that
were already correct**.

Measuring the tilt that actually exists in the coordinates — the median skew between
pairs of tokens that plausibly share a printed row:

| | reported | **measured** |
|---|---|---|
| pages with `skew_angle` > 0.3 | −0.997° | **−0.170°** |
| pages with `skew_angle` = 0 | 0.000 | +0.000° |

The OCR **already straightens the image** before detection. `skew_angle` records how much
was corrected, not what's left over. Full detail in
[[F015-the-ocr-skew-is-not-the-residual]].

A/B test on label→value pairs read by eye:

| angle applied | correct pairs |
|---|---|
| reported `skew_angle` | **3 of 5** |
| zero | 5 of 5 |
| **measured from coordinates** | **5 of 5** |

**Decision:** keep the mechanism, swap the source of the angle. Measure the residual from
the coordinates themselves; when there aren't enough pairs, don't rotate.

## The three design decisions

### 1 · Band by the top edge, not the center

From [[F008-degenerate-boxes-and-top-edge-banding]]. The false `BZ` is 367 px tall: its
center falls four rows below the text, its top edge sits 11 px from the correct row.
Tokens taller than 3x the page's median height are dropped from banding — they're stamps,
watermarks, and merged columns, and they span several rows.

### 2 · Fixed band anchor, not a moving one

```python
if token.y - anchor <= tolerance:   # anchor is NOT updated
```

An anchor that tracks the running average **chains**: on a dense page there's almost
always another token within tolerance of the last one, and whole blocks collapse into a
single row. The anchor stays at the band's first token.

Adaptive tolerance: `max(12 px, 0.6 × median height)`. It needs to absorb the 12–15 px
that separate the code from the label in the liasse without reaching the next row, which
sits ~70 px away.

### 3 · Deskew is a working space; the reported box comes from the original

```python
@dataclass(frozen=True, slots=True)
class PositionedToken:
    token: Token   # untouched
    x: float       # deskewed position, only for grouping
    y: float

    @property
    def bbox(self) -> BBox:
        return bounds(self.token.polygon)   # ORIGINAL coordinates
```

The reviewer draws the box over the PDF exactly as tilted as it is. A test locks this in:
for every token in a row, `bbox.y0` must equal the top of the raw polygon.

## The architecture test caught a mistake of mine

`text/lines.py` needs `geometry`, and the two were in the **same layer**:

```
AssertionError: text/lines.py is layer 1 (text) but imports liasse.geometry,
which is layer 1. A layer may only import from layers below it.
```

I had anticipated this tension when designing the [[modular-architecture]] and forgot
about it. The test caught it immediately. `geometry` moved down to layer 0 — it's pure
math over numbers, with no dependency at all, and `corpus` (also layer 0) doesn't know
about it. Verified that the rule still catches a real violation.

A layering rule written as a document rots; written as a test, it collects.

## The tests

The cases are pairs a human reads off the rendered page: *this label belongs to this
number*. That's what this stage exists to reconstruct, so that's what gets asserted.

| test | what it protects |
|---|---|
| `test_label_and_value_land_on_the_same_row` | 6 golden pairs from 4 documents |
| **`test_applying_the_reported_skew_would_break_rows`** | **the exit criterion** — if it passes, the correction stopped being exercised |
| `test_the_code_sits_on_the_same_row_as_its_label_and_value` | the 12–15 px offset of the code |
| `test_the_three_tokens_of_a_split_number_stay_on_one_row` | F003 |
| `test_the_reported_bbox_comes_from_original_coordinates` | the deskew not leaking into the output |
| `test_a_degenerate_token_does_not_anchor_a_row` | F013 |
| `test_bands_do_not_chain_across_the_page` | the fixed anchor |
| `test_estimate_skew_declines_when_there_is_not_enough_evidence` | refusing rather than guessing |

The second one is the most unusual: it requires that applying the reported angle
**break** something. A test that asserts the wrong alternative is in fact worse.

## A case where the code was right and my test was wrong

I built a golden pair with `67458f18 p2 → Capital social = 10 000`. It failed under all
three angle options. I went to check: this company's capital is **150,000** — there was a
capital increase between fiscal years. My expectation was the one that was wrong.

Worth recording because it's the normal failure mode of this work: the data contradicts
the assumption more often than the code contradicts the data.

## Next

[[phase-1-foundation|E4 — number parsing]]. The test cases are already written with
coordinates in [[F003-the-ocr-breaks-numbers-apart]] and
[[F004-negatives-are-printed-in-parentheses]].

## Links

- [[E2-page-routing]] · [[idea-03-row-banding-with-skew]] · [[F015-the-ocr-skew-is-not-the-residual]]
- [[skew-and-geometry]] · [[modular-architecture]] · [[testing-strategy]]
