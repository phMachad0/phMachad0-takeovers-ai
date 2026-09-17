---
type: concept
tags: [ocr, format, data]
status: draft
updated: 2026-09-14
---

# The OCR that Takeovers provides

The company delivers the OCR already run, at `data/<siren>/<type>/ocr/<doc_id>/page_NNN.json`,
one file per page. The brief explains why: *"we would rather see how you turn text into
structured data than watch you install an OCR engine."*

## Format

```json
{
  "page": 4,
  "skew_angle": 0.31,
  "layout": [ { "label": "table", "bbox": [x1,y1,x2,y2], "cells": [ ... ] } ],
  "ocr":    [ { "polygon": [[x,y],[x,y],[x,y],[x,y]], "text": "...", "score": 0.98 } ]
}
```

| field        | what it is                                | reliability                                                                                                       |
| ------------ | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `page`       | page number, **1-indexed**                | total                                                                                                             |
| `skew_angle` | estimated scan tilt, in **degrees**       | good — see [[skew-and-geometry]]                                                                                 |
| `layout`     | table detector output                     | **irregular** — the brief admits: *"sometimes it finds the liasse grid cleanly, sometimes it finds nothing useful"* |
| `ocr`        | flat list of text lines                   | **always populated**; the practical source of truth                                                              |

**All coordinates are in pixels at 300 dpi.** What you deliver is normalized 0–1. See
[[bbox-and-normalization]].

## `polygon`, not `bbox`

Every OCR line comes as a **4-point quadrilateral**, not a rectangle. That's deliberate:
modern OCR engines (PaddleOCR, for instance) return the actual polygon of detected text,
which on a skewed scan **isn't axis-aligned**.

To get a rectangle:

```python
xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
```

But be careful: this conversion **loses information**, and on tilted text the resulting
rectangle is bigger than the text and can encroach on the neighboring line. That's the root
of the problem in [[idea-03-row-banding-with-skew]].

## The unit of granularity is the "line", and it's unpredictable

What the OCR calls one entry can be:

- an entire sentence: `"Le greffier du tribunal de commerce de AVIGNON atteste..."`
- a cell label: `"Chiffres d'affaires nets *"`
- a code: `"FL"`
- **a single group of three digits**: `"802"`
- a stray noise character: `"*"`, `"§"`, `"¦"`

There's no guarantee that a table cell corresponds to one OCR entry. In practice, in the
liasse's value column, **it almost never does** — see [[F003-the-ocr-breaks-numbers-apart]].

## `score`

Recognition confidence, 0–1. Useful for two things: filtering noise (`score < 0.5` on a
1-character token is usually scan dirt) and feeding the `confidence` field of
`results.json`. Don't conflate them: `score` is the **OCR's confidence about the pixels**;
`confidence` in the deliverable should be the **pipeline's confidence about the
interpretation**, which is a different thing and is better derived from the verifiers — see
[[idea-05-verifier-as-router]].

## Coverage

Uneven by design. Within the scope of the 15 bilan-challenge documents, coverage is
complete (verified). Outside the scope there are gaps. If OCR is ever missing, the options
are: run your own engine, or send the page image to a vision model — which changes the cost
per page, which is exactly the challenge's question. See [[cost-per-page]].

## Links

- [[bbox-and-normalization]] · [[skew-and-geometry]] · [[F003-the-ocr-breaks-numbers-apart]]
