---
type: finding
id: F008
tags: [ocr, geometry, banding, critical]
status: draft
updated: 2026-09-15
---

# F008 — degenerate boxes, and why banding must align on the top edge, not the center

**Impact: high. Settles a design parameter for stage E3.**

## How it surfaced

A prototype of the row-grouping logic matched code `BZ` to the label
`Subventions d'exploitation` on page 006 of `65784e5da67d84faf4042736`, when the correct
label is `Production stockée` — the row right above it. The value collected would have been
`3 390` instead of `27 699`.

It wasn't a skew error (the page has `skew_angle = 0`). It was the token's own polygon:

```
token 'BZ'                    y0=801  y1=1168   height = 367 px   center = 984
token 'Production stockée*'   y0=812  y1=848    height =  36 px   center = 830
token '27'                    y0=812  y1=860                      center = 836
token '699'                   y0=812  y1=858                      center = 835
```

The OCR returned a polygon **367 px tall** for `BZ` — ten times a normal line height.

> **Root cause identified later:** this box isn't a stretched token, it's the **entire code
> column** (`FM FN FO FP FQ FR`) detected as a single vertical line of text. `BZ` isn't
> even a valid code there. See
> [[F013-the-ocr-reads-the-code-column-as-vertical-text]]. The conclusion about top-edge
> banding still holds; the cause turned out more interesting than I'd assumed. Aligned on the
> **top edge**, `BZ` is 11 px from the label: same line. Aligned on the
**center**, it's 154 px away: four lines below.

## Measurement

| alignment reference | Δ between `BZ` and `Production stockée` | result |
|---|---|---|
| **top edge (`y0`)** | **11 px** | same line ✅ |
| center (`(y0+y1)/2`) | 154 px | different lines ❌ |

Frequency across the scope — tokens taller than 3× the page's own median:

```
966 of 27,878 tokens  =  3.47%,  spread across 173 pages
```

The worst offenders are stamps and vertical watermarks (`EXEMPLAIRE A CONSERVER`, 31× the
median; a `'2'` token at 51× in `66cd893c` p26). **Five of them are liasse code tokens** —
`C3`, `SZ`, `SK`, `SE`, and the `BZ` above — meaning the pathology hits exactly what
[[idea-01-code-anchoring|code anchoring]] relies on.

## Decisions this settles

1. **E3's banding aligns on the top edge (`y0`), not the center.** A measured decision, not
   a convention.
2. **Sanity filter:** any token whose height exceeds 3× the page median is degenerate. For
   code tokens, use the top edge and continue; for the rest (stamps, watermarks), drop them
   from banding — they're noise that crosses multiple lines.
3. The band tolerance is still needed because of the systematic 12–15 px offset between
   code and label already described in [[skew-and-geometry]]. Measured as adequate:
   **22 to 26 px**.

## Method note

This finding came out of a banding prototype run during E1.5's reconnaissance, not from
reading documentation. The prototype got it wrong, the error was investigated instead of
worked around, and the result became a justified parameter. Worth recording this way: **the
value of a throwaway prototype is the error it surfaces early.**

## Links

- [[skew-and-geometry]] · [[idea-03-row-banding-with-skew]] · [[phase-1-foundation]]
- [[takeovers-ocr-json]] · [[F013-the-ocr-reads-the-code-column-as-vertical-text]]
