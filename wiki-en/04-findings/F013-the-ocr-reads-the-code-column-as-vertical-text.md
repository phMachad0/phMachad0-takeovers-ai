---
type: finding
id: F013
tags: [ocr, codes, trap, critical]
status: draft
updated: 2026-09-15
---

# F013 — the OCR reads the code column as a single line of vertical text

**Impact: high. Explains the code loss in [[F009-measured-code-loss]], corrects an error of
mine, and gives a cheap filter that avoids it.**

## How it surfaced

I had recorded that `BZ` would mean `Production stockée` on form 2052 and `Autres créances`
on 2050 — a code collision between forms — and carried that into the COGS formula in
[[ADR-002-schema-ambiguities]].

**That was wrong.** While rendering the page with `tools/bbox_viewer.py` to demonstrate
visual box checking, the row `Production stockée*` shows up with code **`FM`**, not `BZ`.

Checked across the 6 documents that have form 2052:

```
63e8ebbb p4:  FM=YES   BZ=no
63e13943 p6:  FM=YES   BZ=no
65784e5d p6:  FM=no    BZ=YES     <- the only one, and precisely where FM wasn't read
```

`BZ` exists on form 2052 in **one** document, and only in the one where `FM` wasn't read.
It's not a collision: it's a misread.

## The cause

The `BZ` token on page 006 of `65784e5da67d84faf4042736`:

```json
{"text": "BZ", "score": 0.37, "orientation_angle": 1,
 "polygon": [[1913,801],[1991,801],[1991,1168],[1913,1168]]}
```

78 px wide by **367 px tall**. Rendering exactly that region, what's inside is the **stacked
code column**:

```
FM
FN
FO
FP
FQ
FR
```

The text detector saw a narrow, tall column and classified it as **a single, rotated line of
text** — hence `orientation_angle: 1`. The recognizer then read that vertical rectangle as
`BZ`, at 37% confidence.

It isn't a character confusion (`M` → `Z` isn't plausible). It's a **detection** failure,
not a recognition one.

## Why this is good news, not just bad

Because the OCR **flagged it**, via three independent signals already sitting in the JSON:

| signal | legitimate code (`FL`, `FJ`) | the false `BZ` |
|---|---|---|
| `score` | 0.998 – 0.999 | **0.370** |
| `orientation_angle` | 0 | **1** |
| height | 52 – 57 px | **367 px** |

> **Correction (2026-09-16, during E5).** `orientation_angle` **doesn't** work as a filter.
> Measured across the whole corpus, **12 of 18** two-letter tokens with a non-zero angle are
> ordinary liasse codes — `IH`, `TH`, `CO`, `GQ` — with full score and normal height, and
> rejecting them would cost real fields. The false `BZ` is already caught twice over, by
> score and by height, so the angle never carried its own weight. It's now recorded as
> evidence, not used as a veto. See [[E5-liasse-extractor]].

## Consequences for the extractor

**Sanity filter for liasse code candidates**, in E5 — all three, because they're
independent and cost nothing:

```python
def is_code_candidate(token, page_median_height) -> bool:
    return (
        CODE_RE.fullmatch(token.text)
        and token.score >= 0.80                      # F013: the false BZ scored 0.37
        and token.height <= 3 * page_median_height   # F008: and was 367 px
    )
```

**This would have prevented the entire error.** The false `BZ` is rejected by all three
criteria.

**And it explains [[F009-measured-code-loss]].** The codes "missing" in a contiguous block
(`FM`…`FX`) weren't always lost: on one page they were **swallowed by a single vertical
detection**. The ordinal rung is still needed, but there's a second, cheap recovery path —
detect the vertical box and recover the codes it covers by row position.

**And `Token` needs to carry `orientation_angle`.** Today our loader from
[[E1-corpus-and-geometry|E1]] drops that field. A small, necessary fix.

## Method note

This error survived a full sweep of the corpus, made it into a concept page and an ADR, and
fell apart the **first time a page was rendered and looked at**. That's the argument for
oracle **O6** in [[testing-strategy]] — visual spot-checking — and it's worth stating in the
README: text analysis of OCR output alone doesn't see what the OCR didn't see.

The question that triggered the investigation came from Pedro: *"how did code FM get read
as BZ? That doesn't look like a very plausible confusion to me."* He was right — it isn't a
character confusion at all.

## Links

- [[F008-degenerate-boxes-and-top-edge-banding]] · [[F009-measured-code-loss]]
- [[liasse-codes]] · [[ADR-002-schema-ambiguities]] · [[idea-01-code-anchoring]]
- [[testing-strategy]]
