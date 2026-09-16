---
type: finding
id: F005
tags: [ocr, liasse, codes]
status: draft
updated: 2026-09-14
---

# F005 — the OCR loses part of the code column

**Impact: medium-high. Limits [[idea-01-code-anchoring]] and requires the fallback ladder.**

## Claim

Even on a well-recognized liasse page, the OCR reads a row's label and value but **fails
to read that same row's code**. The affected fields in the verified example include two of
the 12 requested ones.

## Evidence

`data/401009741/bilans/ocr/65784e5da67d84faf4042736/page_006.json`, liasse 2052.

**Codes read successfully** (34): `FA FB FC FD FE FF FG FH FI FJ FK FL BZ FY FZ GA GB GC
GD GE GF GG GH GI GJ GN GO GP GQ GR GS GT GU GV GW`.

**Codes missing, even though the label and value were read:**

| row (label read) | expected code | value read | challenge field |
|---|---|---|---|
| `Achats de marchandises (y compris droits de douane)*` | `FS` | 138 591 | component of `PL_COGS` |
| `Variation de stock (marchandises)*` | `FT` | −45 440 | component of `PL_COGS` |
| `Achats de matières premières et autres approvisionnements` | `FU` | 490 756 | component of `PL_COGS` |
| `Variation de stock (matières premières et approvisionnements)*` | `FV` | −52 814 | component of `PL_COGS` |
| `Autres achats et charges externes (3) (6 bis)*` | `FW` | 329 158 | **`PL_EXT_SERVICES_COSTS`** |
| `Impôts, taxes et versements assimilés*` | `FX` | 5 679 | — |

That is: **one of the 12 fields (`PL_EXT_SERVICES_COSTS`) and every component of a second
one (`PL_COGS`)** are unreachable by pure code anchoring on this page.

The missing codes are consecutive on the form (`FS`→`FX`) and sit in a contiguous block,
suggesting a local cause — a lighter band in the image, or the detector having suppressed
a region.

## Consequence

Code anchoring is **rung 1 of a ladder**, not the whole strategy:

1. code read from the OCR
2. **ordinal position on the form's template** — `FW` sits N rows from `FY`, which was
   read; the row's position is interpolable from the known anchors
3. fuzzy-matched label
4. VLM

Rung 2 applies precisely in this case: `FY` and `FZ` were read and sit right below the lost
block, and `BZ`, `FL` were read above. Two anchors bound the interval, and the row bands
between them are countable.

See [[idea-01-code-anchoring]].

## Pending

- Measure the code-loss rate across every liasse page in the 8 documents. If it stays
  consistently high, rung 2 stops being a refinement and becomes the main path.
- Check whether the expected positions of the lost codes have a low-`score` token (the OCR
  saw something and discarded it) or nothing at all (the detector saw nothing).

## Links

- [[liasse-codes]] · [[idea-01-code-anchoring]] · [[idea-04-page-routing]]
