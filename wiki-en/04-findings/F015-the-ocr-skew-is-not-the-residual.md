---
type: finding
id: F015
tags: [ocr, geometry, skew, critical]
status: draft
updated: 2026-09-16
---

# F015 — the OCR's `skew_angle` is not the residual in the coordinates

**Impact: high. Inverts [[idea-03-row-banding-with-skew|idea ❸]] as I had originally
specified it, and contradicts a premise from the brief.**

## The premise I had

[[idea-03-row-banding-with-skew]] said: the OCR delivers a `skew_angle` per page, almost
nobody uses it, and rotating the coordinates by `−skew_angle` before grouping rows corrects
the misalignment between label and value. The brief reinforces this, describing
`820561470` as *"a crooked scan — mean skew 0.7°, with rotated pages"*.

## What happened when implementing it

On page 7 of `820561470/6493e437` (`skew_angle = −0.9354`), applying the rotation **broke**
rows that had been correct:

```
with the reported skew        with the measured skew
─────────────────────────     ────────────────────────────────────────────
Capital social ou individuel  Capital social ou individuel | 10 000 | 10 000
Primes d'émission | 10 000 | 10 000    Primes d'émission, de fusion ...
```

The `10 000` values belong to the share capital row and got pushed onto the next row.

## The measurement

For every pair of tokens that plausibly share a printed row — tops within 60 px of each
other, separated by more than 800 px horizontally — the slope is `Δy / Δx`. The **median**
of these pairs is the slope that actually exists in the coordinates. Median, not
regression: the page has many pairs that aren't on the same row, and a least-squares line
would follow them too.

| | reported skew | skew **measured from the coordinates** |
|---|---|---|
| 14 pages with `skew_angle` > 0.3 | median **−0.997°** | median **−0.170°** |
| 195 pages with `skew_angle` = 0 | 0.000 | median **+0.000°** |

**The reported value is roughly six times what's actually there.** And where it reports
zero, the measurement also comes out zero — which validates the measurement method.

## The explanation

Takeovers' OCR pipeline **already straightens the image** before detecting text. The
`skew_angle` field records **how much was corrected**, not what's left over. It's a
provenance value, not a correction to apply.

That makes sense: a text detector works better on a straightened image, and recording the
angle used is what any serious pipeline would do.

A residual of 0.17° on a 2470 px page = **7 px of drift**, well under the ~24 px band
tolerance. In other words: **the coordinates are already close to level.**

## A/B, measured

Criterion: on label→value pairs read by eye on the rendered page, do the two land on the
same row?

| angle applied | correct pairs |
|---|---|
| **reported `skew_angle`** | **3 of 5** |
| zero | 5 of 5 |
| **measured from the coordinates** | **5 of 5** |

Applying the reported value is **worse than doing nothing**.

## The decision

Keep the mechanism, swap the source of the angle:

```python
def effective_skew(page):
    measured = estimate_skew(t.polygon for t in page.tokens if t.text.strip())
    return measured if measured is not None else 0.0
```

- **Never** apply `page.geometry.skew_deg`. It's still kept as provenance.
- Measure the residual from the coordinates themselves, which is by definition what needs
  correcting.
- When there aren't enough pairs to measure, don't rotate. Refusing beats guessing, and
  zero is the right default on a corpus whose coordinates already arrive level.

On this corpus the correction is nearly a no-op — 7 px against a 24 px tolerance. The
mechanism would still matter on a genuinely crooked corpus; the difference is that it's now
driven by a measurement instead of by a field that means something else.

## What this means for the brief

The brief describes `820561470` as *"a crooked scan — mean skew 0.7°"*. The pages do report
0.9–1.0°, so the description is faithful to the **metadata**. But the OCR's coordinates
carry only ~0.17° of that.

Worth reporting as a discrepancy between sources, which is what the parent README asks for:

> *"Cross-checking one source against another sometimes helps, and sometimes tells you the
> sources disagree — which is itself a finding worth reporting."*

## Method note

This is the second time an idea recorded in the wiki didn't survive contact with
measurement — the first was the nonexistent `BZ` collision
([[F013-the-ocr-reads-the-code-column-as-vertical-text]]). In both cases the idea was
plausible, was written down with confidence, and was wrong.

What caught it was the same thing both times: **implementing and measuring, instead of
reasoning further.**

## Links

- [[idea-03-row-banding-with-skew]] · [[skew-and-geometry]] · [[E3-row-reconstruction]]
- [[F008-degenerate-boxes-and-top-edge-banding]] · [[takeovers-ocr-json]]
