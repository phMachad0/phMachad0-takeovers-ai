---
type: idea
tags: [geometry, skew, extraction]
status: draft
updated: 2026-09-16
---

# ❸ Row grouping corrected for skew

## The problem

To match a label (left of the page) with a code (center-right) and a value (right), you
need to decide **which tokens belong to the same table row**. The obvious method: group
by `y` coordinate, with some tolerance.

That breaks on crooked scans, and it breaks in a specific, dangerous way.

An A4 page at 300 dpi is 2479 px wide. For an angle θ, the accumulated vertical offset
from the left edge to the right edge is `Δy = 2479 × tan(θ)`:

| θ | Δy |
|---|---|
| 0.5° | 22 px |
| **0.9°** (observed in `820561470` and `445070311`) | **39 px** |
| 1.0° | 43 px |
| 4.9° (observed on a cover page) | 212 px |

And a line of text in the liasse is ~35 px tall, with rows spaced ~70 px apart (measured:
bands at y = 1239, 1309, 1379, 1450 on page 006 of `65784e5da67d84faf4042736`).

**At 0.9° of tilt, the label on the left and the value on the right are separated by more
than half a row's vertical distance.** Widen the tolerance to compensate and you start
merging adjacent rows; tighten it and the label loses its value.

There's no tolerance that works. The problem isn't the threshold — it's the coordinate
system.

> ## ⚠️ Corrected by the implementation (2026-09-16)
>
> The central premise of this page — *"the OCR already gives you the angle, use it"* —
> **is wrong**. `skew_angle` records how much the OCR corrected in the image, not what's
> left in the coordinates: pages reporting −1.0° still carry −0.17°. Applying it is
> **worse than doing nothing** (3 of 5 pairs correct, against 5 of 5 with no correction).
>
> The mechanism is still right; the source of the angle changes to a **measurement of the
> coordinates themselves**. See [[F015-the-ocr-skew-is-not-the-residual]] and
> [[E3-row-reconstruction]]. The text below is left as it was, so the original reasoning
> stays legible.

## The idea

**The OCR already gives you the angle. De-skew before grouping.**

```json
{ "page": 7, "skew_angle": -0.9353581957571454, "ocr": [...] }
```

That field is present in every `page_NNN.json` in the corpus and is almost certainly
ignored by most submissions — it's not mentioned in the brief, only in the example JSON.

```python
import math

def deskew(x, y, theta_deg, cx, cy):
    """Rotate (x,y) by -theta around the page center."""
    t = math.radians(-theta_deg)
    dx, dy = x - cx, y - cy
    return (cx + dx*math.cos(t) - dy*math.sin(t),
            cy + dx*math.sin(t) + dy*math.cos(t))
```

Apply it to every token on the page, group into bands in the corrected space, and then —
the critical point — **emit the `bbox` in the ORIGINAL coordinates**, because the bbox
gets drawn on the original, crooked scan, not on a deskewed one. The rotation is an
internal working space, not the output.

```
OCR coordinates ──deskew──> working space ──group──> rows
        │                                              │
        └──────────── emitted bbox comes from here ◄───┘
                      (token ids, not rotated coordinates)
```

Practical implementation: load each token with `(x_raw, y_raw, x_deskew, y_deskew)`,
group by `y_deskew`, and build the bbox from the original `polygon` of the tokens in the
group.

## The refinement: estimate skew yourself

The OCR's `skew_angle` is an estimate and can be wrong. Observed in the corpus:
`820561470/6493e4372f502414800f8164` has `skew_angle = 0.0` on page 1 (11 tokens,
nearly empty) and `-0.98` on page 5 — the estimator needs text to work with.

On a liasse page there's a more direct alternative: **the code column is a known vertical
line.** Every isolated two-uppercase-letter token sits in the same column. A linear
regression of `x` on `y` over those tokens gives the column's tilt, which is the skew —
measured directly on the structure you're going to use, not on a global page estimate.

```python
codes = [t for t in tokens if re.fullmatch(r"[A-Z][A-Z0-9]", t.text)]
slope, _ = numpy.polyfit([t.y for t in codes], [t.x for t in codes], 1)
theta = math.degrees(math.atan(slope))
```

If the angle estimated this way diverges a lot from the OCR's `skew_angle`, that itself is
a signal that the page is difficult — another trigger for
[[idea-05-verifier-as-router]].

*(Only valid for liasses, which have a code column. For plaquettes, the right-aligned
value column serves the same purpose.)*

## Why this is worth the cost

Three reasons:

1. **It uses a field in the data the brief never mentions.** The `skew_angle` field only
   shows up if you actually look at the corpus rather than build against the field list
   alone.
2. **It's measurable in isolation.** Turning the correction on and off and measuring the
   verifiers' pass rate on the three `820561470` documents produces a before/after number.
   A table with that number is evidence, not assertion.
3. **The company picked `820561470` deliberately** — the brief calls it *"a crooked
   scan — mean skew 0.7°, with rotated pages."* It's a planted test. Solving it
   explicitly, and noting in the README that it was recognized as a planted test, answers
   the question they actually asked.

## Measurement plan

| configuration                       | `820561470` docs | `445070311` docs | docs without skew |
| ------------------------------------ | ------------------- | ------------------- | ------------- |
| raw `y`, fixed tolerance             | (baseline)          |                     |               |
| raw `y`, generous tolerance          |                     |                     |               |
| **deskew using the OCR's `skew_angle`** |                     |                     |               |
| **deskew using the column regression**  |                     |                     |               |

Fill in with the verifiers' pass rate. The empty table is already the experiment design;
filling it in is the work.

## Links

- [[skew-and-geometry]] · [[takeovers-ocr-json]] · [[idea-05-verifier-as-router]]
- [[F015-the-ocr-skew-is-not-the-residual]] · [[E3-row-reconstruction]]
