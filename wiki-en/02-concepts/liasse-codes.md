---
type: concept
tags: [domain, liasse, codes, core]
status: draft
updated: 2026-09-15
---

# The liasse's two-letter codes

This is the most important domain page. If you only read one, read this one.

## What they are

On every form of the [[liasse-fiscale]], every line carrying a value has a **two-character
alphanumeric code** printed in a narrow column immediately to the left of the value cell.
The code is **fixed by law**: `FL` means "chiffres d'affaires nets, total" on every 2052
form of every French company, always.

Real example, extracted from
`data/401009741/bilans/ocr/65784e5da67d84faf4042736/page_006.json` (coordinates in 300 dpi
pixels):

```
[  283, 738] Chiffres d'affaires nets *
[ 1098, 736] FJ   [1240,743] 1  [1286,740] 802  [1386,740] 935     ← France column
[ 1502, 740] FK   [1748,736] 2 524                                  ← Export column
[ 1925, 734] FL   [2125,743] 1  [2174,741] 805  [2275,741] 459     ← TOTAL column
```

Three columns, three codes, and what the challenge wants is the **total**: `FL = 1 805 459`.

## Why this changes everything

The obvious path to extract "Montant net du chiffre d'affaires" is to search the OCR for
that text. That path is fragile for four reasons, all observable in the corpus:

1. **The OCR mangles accents and letters.** On the same page you see `du Code géñéral des
   impôts` and `article S3 A` (instead of `53 A`). A long French label has many chances to
   come out corrupted; `FL` has two.
2. **The printed label varies.** "Chiffres d'affaires nets" vs "Chiffre d'affaires net" vs
   "CHIFFRE D'AFFAIRES NET". The code doesn't vary.
3. **A label can designate three values.** "Chiffres d'affaires nets" sits on a single
   line, but there are three cells (`FJ`, `FK`, `FL`). Finding the label doesn't tell you
   which column to take.
4. **The label can be broken across several OCR lines.** E.g.: `Avances et acomptes sur
   immobilisa` / `tions incorporelles` — the word was cut in the middle by the cell's
   width.

The code solves all four at once. See [[idea-01-code-anchoring]].

## Code table — verified in E1.5

Sweep of the liasse pages of the 8 documents, matching code ↔ label ↔ value by row band.
**Every code used by the 12 requested fields was confirmed in the corpus.**

`docs` = in how many of the 8 liasse documents the code was read by the OCR.

### 2050 — Bilan Actif · *three columns: Brut · Amortissements · **Net***

| code | label confirmed in the corpus | use | docs |
|---|---|---|---|
**Every line of the 2050 has two codes: one for the Brut column and one for the Net column.**

| code | label confirmed in the corpus | column | use | docs |
|---|---|---|---|---|
| `CF` | `Disponibilités` | Brut | row anchor | 6/8 ✅ |
| **`CG`** | same | **Net** | **`BS_CASH` (part)** | ✅ |
| `CD` | `Valeurs mobilières de placement` | Brut | row anchor | 3/8 |
| **`CE`** | same | **Net** | **`BS_CASH` (part, VMP)** | 6/8 ✅ |
| `CJ` | `TOTAL (III)` — actif circulant | | check | 6/8 ✅ |
| `CO` | `TOTAL GÉNÉRAL (I à VI)` | **Brut** | row anchor | 6/8 ✅ |
| `IA` / `1A` | same | Amortissements | check | ✅ |
| *(no code read)* | same | **Net** | **`BS_TOTAL_ASSETS`** — 3rd cell | — |
| `BZ` | `Autres créances (3)` | Brut | — (only exists in the 2050) | 6/8 ✅ |

Evidence, `328024377/63e8ebbb…7e` p2:

```
TOTAL GÉNÉRAL (I à VI) | CO | 8 754 311 | IA | 2 520 565 | 6 233 746
                              ↑ Brut            ↑ Amort.    ↑ Net = BS_TOTAL_ASSETS
Valeurs mobilières de placement | CD | 465 358 | CE | 465 358
Disponibilités                  | CF | 1 515 838 | CG | 1 515 838
```

**`CO` is not total assets — it's gross assets.** The requested field is the third cell,
which had no code read in the corpus. So: `CO` serves as a **row anchor**, and the column is
selected by position. This confirms the conclusion of
[[F011-v1-confirmed-and-the-column-structure]] that column selection needs to be
positional.

### 2051 — Bilan Passif

| code | label confirmed in the corpus | use | docs |
|---|---|---|---|
| `DA` | `Capital social ou individuel (1)* (Dont versé : …)` | **`BS_CAPITAL_EQUITY`** | 6/8 ✅ |
| `DB` `DD` `DG` `DH` `DI` | share premium · legal reserve · other reserves · retained earnings · profit for the year | aggregated variant | ✅ |
| `DL` | `TOTAL (I)` — capitaux propres | **`BS_TOTAL_EQUITY`** | 6/8 ✅ |
| `EC` | `TOTAL (IV)` — dettes | check | 6/8 ✅ |
| `EE` | `TOTAL GÉNÉRAL (I à V)` | **check against `CO`, V1** | 6/8 ✅ |

### 2052 — Compte de résultat · *`FL` is the **Total** column, not France or Export*

| code | label confirmed in the corpus | use | docs |
|---|---|---|---|
| `FL` | `Chiffres d'affaires nets *` | **`PL_REVENUE`** | 3/8 ⚠️ |
| `FJ`/`FK` | same — France / Export | *do not use* (partial) | ✅ |
| `FM` | `Production stockée*` | COGS component | 3/8 ✅ |
| `FS` | `Achats de marchandises (y compris droits de douane)*` | COGS | 2/8 ⚠️ |
| `FT` | `Variation de stock (marchandises)*` | COGS | 2/8 ⚠️ |
| `FU` | `Achats de matières premières et autres approvisionnements` | COGS | 2/8 ⚠️ |
| `FV` | `Variation de stock (matières premières et approvisionnements)` | COGS | 2/8 ⚠️ |
| `FW` | `Autres achats et charges externes (3) (6 bis)*` | **`PL_EXT_SERVICES_COSTS`** | 2/8 ⚠️ |
| `FY` | `Salaires et traitements*` | `PL_PERSONNEL_COSTS` | 3/8 ✅ |
| `FZ` | `Charges sociales (10)` | `PL_PERSONNEL_COSTS` | 3/8 ✅ |
| `GA` | `- dotations aux amortissements*` | **`PL_D&A`** | 3/8 ✅ |
| `GB` | `- dotations aux provisions*` | `PL_D&A` (variant) | 3/8 ✅ |
| `GV` | `2 - RÉSULTAT FINANCIER (V - VI)` | **`PL_FINANCIAL_RESULTS`** | 4/8 ✅ |
| `GP`/`GU` | totals of financial income / expense | derive `GV`'s sign | ✅ |

### 2053 — Compte de résultat, continued

| code | label confirmed in the corpus | use | docs |
|---|---|---|---|
| `HK` | `Impôts sur les bénéfices *` | **`PL_INCOME_TAX`** | 4/8 ✅ |
| `HN` | `5 - BÉNÉFICE OU PERTE (Total des produits − total des charges)` | check against `DI` | 4/8 ✅ |

### 2058-C — Renseignements divers

| code | label confirmed in the corpus | use | docs |
|---|---|---|---|
| `YP` | `- Effectif moyen du personnel * (dont: apprentis, handicapés…)` | **`META_AVG_WORKFORCE`** | 3/8 ⚠️ |

`YP` only exists in `504304205`. In the others the workforce figure is in running text, or
absent — see [[F010-actual-field-coverage]].

---

## ⚠️ Collision: the same code means different things on different forms

The field catalogue is indexed by **(form, code, column)** and never by code alone.
Confirmed collision in the corpus:

| code | on the **2050** | on the **2054** |
|---|---|---|
| **`CO`** | `TOTAL GÉNÉRAL (I à VI)`, Brut column | `TOTAL I` in an asset schedule table |

> **Correction (2026-09-15).** This section used to claim another collision — `BZ` meaning
> `Autres créances` on the 2050 and `Production stockée` on the 2052. **That was wrong.**
> The code for `Production stockée` on the 2052 is **`FM`**, correctly read in 3 of the 8
> documents. The only `BZ` on a 2052 page is a false reading: the OCR detected the entire
> code column as a single line of vertical text. See
> [[F013-the-ocr-reads-the-code-column-as-vertical-text]].
>
> The `(form, code, column)` rule still holds — only the example illustrating it was wrong.

## ⚠️ Sanity filter for code candidates

A two-uppercase-letter token is **not** necessarily a code. Three signals from the OCR
itself separate legitimate codes from false positives, and they're independent of each
other:

| signal | legitimate code | observed false positive |
|---|---|---|
| `score` | 0.998 – 0.999 | 0.370 |
| `orientation_angle` | 0 | 1 (vertical text) |
| height | 52 – 57 px | 367 px |

Requiring all three costs nothing and would have prevented the error above. See
[[F013-the-ocr-reads-the-code-column-as-vertical-text]] and
[[F008-degenerate-boxes-and-top-edge-banding]].

## Already-observed trap: the code can be missing from the OCR

On the same page 006 verified above, the OCR **captured** `FY`, `FZ`, `GA`…`GW`, but
**lost** `FS`, `FT`, `FU`, `FV`, `FW`, `FX` — precisely the codes for the purchases and
external-services lines, which are two of the 12 requested fields. The label and value were
read; only the code vanished.

This means anchoring on code **cannot be the only strategy**. A fallback ladder is
required. See [[F005-the-ocr-loses-part-of-the-code-column]] and
[[idea-01-code-anchoring]].

**Measured in E1.5:** the loss isn't isolated. On form 2052, code coverage ranges from
**55% to 92%** per page, and the `FS`–`FX` block is missing on **half** the 2052 pages in
scope — in one document even `FL` is missing. See [[F009-measured-code-loss]]. The ordinal
fallback stops being a refinement and becomes mandatory.

And part of that "loss" has an identified cause: on at least one page the `FM`…`FR` block
didn't disappear, it was **swallowed by a single vertical detection** —
[[F013-the-ocr-reads-the-code-column-as-vertical-text]].

## Links

- [[liasse-fiscale]] · [[the-12-fields]] · [[cogs-a-la-francaise]]
- [[idea-01-code-anchoring]] · [[idea-05-verifier-as-router]]
- [[F013-the-ocr-reads-the-code-column-as-vertical-text]]
- E1.5 findings: [[F008-degenerate-boxes-and-top-edge-banding]] ·
  [[F009-measured-code-loss]] · [[F010-actual-field-coverage]] ·
  [[F011-v1-confirmed-and-the-column-structure]]
