---
type: concept
tags: [geometry, skew, ocr]
status: draft
updated: 2026-09-14
---

# Skew: why a tilted scan breaks parsing

## What skew is

**Skew** is the document's tilt in the scanner. The sheet went in 1 degree crooked, and the
whole image is rotated 1 degree. The OCR reads the text correctly (modern engines handle
this fine) but the **coordinates** rotate along with it.

Takeovers' OCR delivers the estimated angle on every page:

```json
{ "page": 7, "skew_angle": -0.9353581957571454, ... }
```

Values observed in the corpus: `0.0` for most pages, `±0.9` to `±1.0` in `820561470` and
`445070311`, and one `4.88` on a cover page. The brief confirms it: `820561470` has *"mean
skew 0.7°, with rotated pages"*.

## Why one degree matters

One degree sounds negligible. On a page, it isn't.

An A4 page at 300 dpi is **2,479 px wide**. The accumulated vertical offset from the left
edge to the right edge of the page, for an angle θ:

```
Δy = width × tan(θ)

θ = 0.5°  →  Δy =  22 px
θ = 1.0°  →  Δy =  43 px
θ = 4.9°  →  Δy = 212 px
```

And the **height of a line of text** on a liasse at 300 dpi is on the order of **30 to 40
px** — the table rows are spaced roughly 70 px apart (measured: bands at y=1239, 1309,
1379, 1450 on page 006 of `65784e5da67d84faf4042736`).

**At 1° of tilt, the vertical offset between the page's left and right edges is larger than
an entire line of text.**

Concrete consequence: the label `Autres achats et charges externes` sits on the left of the
page; the code `FW` and the value sit on the right. If you group by raw `y`, they land in
**different bands**, and the label gets matched with the value from the line **above or
below**.

The result isn't an error that blows up. It's a plausible number, in the wrong field. It's
the worst category of bug for a financial-data pipeline — exactly what the brief calls
*"three of them silently wrong"*.

## What's already observable in the corpus even without skew

Even on pages with `skew_angle = 0.0`, vertical alignment isn't exact. On page 006 of
`65784e5da67d84faf4042736`:

```
[283, 1666] Salaires et traitements*      ← label at y=1666
[1923, 1651] FY                            ← code at y=1651   (Δ = 15 px)
[2175, 1666] 499   [2275, 1666] 659        ← value at y=1666
```

```
[283, 1735] Charges sociales (10)          ← label at y=1735
[1921, 1723] FZ                            ← code at y=1723   (Δ = 12 px)
[2177, 1736] 162   [2274, 1736] 521        ← value at y=1736
```

The code sits consistently **12 to 15 px above** the label and the value. It's not skew — it's
that the code is printed in a smaller font and at a slightly different vertical position
within the cell. This means **any grouping by `y` needs tolerance**, and the tolerance needs
to be calibrated, not guessed.

## The fix

Un-rotate the coordinates before grouping. See
[[idea-03-row-banding-with-skew]] for the math and the measurement plan.

## Links

- [[takeovers-ocr-json]] · [[bbox-and-normalization]] · [[idea-03-row-banding-with-skew]]
