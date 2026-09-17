---
type: concept
tags: [geometry, bbox, grounding]
status: draft
updated: 2026-09-14
---

# Bounding boxes and coordinate conversion

## Why Takeovers requires this

From the parent README:

> *"a number without a provenance is not something we can sell, defend to a client, or
> debug six months later."*

Every extracted value needs to say **in which document, on which page, and in which
rectangle of the page** it was read. That's *grounding*. It's what lets an analyst click
the number and see the piece of paper it came from.

## The three coordinate systems in play

Three, and confusing them is the cheapest mistake to make and the most expensive to find.

| system | unit | where it shows up |
|---|---|---|
| **PDF points** | 1 pt = 1/72 inch | native PDF geometry (`page.rect`) |
| **300 dpi pixels** | 1 px = 1/300 inch | **Takeovers' OCR** |
| **normalized** | fraction from 0 to 1 | **what you deliver** |

## The conversion

Straight from `tools/bbox_viewer.py`:

```python
DPI_OF_OCR    = 300
POINTS_PER_INCH = 72
scale = DPI_OF_OCR / POINTS_PER_INCH          # = 4.1666...

w_px = page_width_points  * scale
h_px = page_height_points * scale

x_norm = x_px / w_px
y_norm = y_px / h_px
```

The factor is **4.1667 px per point**. An A4 page (595 × 842 pt) becomes 2479 × 3508 px.

**The step that cannot be skipped:** the width in points needs to be read **from that
specific page of that specific PDF**. You can't assume A4 and apply 2479 px everywhere.
`NOTICE.md` warns that some PDFs were re-rendered at 150 dpi (keeping the geometry), and
the corpus mixes portrait and landscape pages. Hardcoding the constant produces an error
that only shows up in some documents — the worst kind.

```python
import fitz                      # pymupdf
doc  = fitz.open(pdf_path)
page = doc[page_number - 1]      # the OCR is 1-indexed, pymupdf is 0-indexed
w_pt, h_pt = page.rect.width, page.rect.height
```

## Top-left origin

The brief specifies a **top-left** origin, with `y` increasing downward. The OCR already
uses that convention, so there's no axis flip needed — but it's worth checking, because
native PDF uses a **bottom-left** origin, and pymupdf silently normalizes that for you. If a
value ever comes from a direct PDF extraction instead of the OCR, that's where the bug
enters.

## Cheap validation that avoids an invalid submission

The schema declares `minimum: 0, maximum: 1`. A `results.json` with a bbox of `1.03`
**doesn't validate** — and a submission that doesn't parse is a submission that doesn't get
scored.

Invariants worth checking before writing the JSON:

```python
assert 0 <= x0 < x1 <= 1
assert 0 <= y0 < y1 <= 1
assert (x1-x0) < 0.98 and (y1-y0) < 0.5    # page-sized box = grouping bug
```

The last one is the most useful: if the rectangle covers the entire page, it almost always
means the token grouping merged pieces from different blocks.

## The verification tool

```bash
python tools/bbox_viewer.py \
  --pdf data/401009741/bilans/pdf/bilan_2023-11-20_65784e5da67d84faf4042736.pdf \
  --page 6 --ocr data/401009741/bilans/ocr/65784e5da67d84faf4042736 \
  --grep "Chiffres d'affaires"
```

`--grep` prints the **already-converted** box. In other words: you can test your conversion
against theirs instead of trusting it blindly. An automated test that compares your
function's output against `bbox_viewer`'s on N sampled lines is cheap and eliminates an
entire class of error.

## Which box to send?

The schema asks for one box per value. Candidates, for the value `FL = 1 805 459` that the
OCR returned as three tokens:

- just the token `"1"` → points to a fragment of the number. Wrong.
- the union of the three tokens `1` + `805` + `459` → **the box of the complete number**.
  This is it.
- the entire line (label + code + value) → points to the right line but is imprecise.

The union of the number's tokens is the right answer, and it only exists once you've solved
[[idea-02-digit-reassembly]] — reassembling the number and getting the right box are the
same problem.

## Links

- [[takeovers-ocr-json]] · [[skew-and-geometry]] · [[idea-02-digit-reassembly]]
