---
type: idea
tags: [cost, classification, architecture]
status: draft
updated: 2026-09-14
---

# ❹ Page routing

## The problem

The 15 documents in scope add up to **415 pages** (measured). They range from 13 to 58
pages per document.

The 12 requested fields live on **4 to 6 pages per document** — about **75 pages in
total**. The other 340 are: registry certificates, meeting minutes, management report,
auditor's report, explanatory notes, fixed-asset schedules, depreciation, provisions,
receivable maturities, dividends.

Processing 415 pages when 75 would do is a **5.5×** waste. If the processing runs through
a vision model, that waste is literal money, and it multiplies across hundreds of
thousands of documents in production.

## The idea

A cheap page classifier before any expensive processing. And — the part that makes the
difference — **a classifier with two independent signals that cross-check each other**.

### Signal A: form header

```python
re.search(r"DGF[iI]P\s*N[°*ºo]?\s*(20\d\d(?:\s*-\s*[A-Z])?)", page_text)
```

Precise when it works. But **not reliable alone**: the header sits in the top corner of
the page, in small type, and is the first thing a crooked scan or a staple mark ruins.

### Signal B: structural fingerprint

A liasse page has a signature that doesn't depend on any specific text: **many isolated
two-uppercase-letter tokens, aligned in a narrow vertical column.**

```python
codes = {t.text for t in tokens if re.fullmatch(r"[A-Z][A-Z0-9]", t.text)}
is_liasse_page = len(codes) >= 12
```

And it goes further than "this is a liasse": **which** liasse. Each form has a
characteristic set of codes.

```python
SIGNATURES = {
    "2050": {"AA","AB","AF","AH","AN","BJ","BX","CF","CO"},   # actif
    "2051": {"DA","DB","DD","DG","DH","DI","DL","DP","EE"},   # passif
    "2052": {"FA","FD","FG","FJ","FL","FW","FY","FZ","GA"},   # résultat 1
    "2053": {"HA","HD","HE","HK","HL","HN"},                  # résultat 2
}
form = argmax_by(lambda s: jaccard(codes, SIGNATURES[s]))
```

This identifies the form **without reading the header**, and works even if half the codes
were lost in OCR — which is exactly what happens
([[F005-the-ocr-loses-part-of-the-code-column]]).

### The cross-check is the product

The two signals agreeing is confirmation. Disagreeing is **information**:

| signal A (header) | signal B (codes) | reading |
|---|---|---|
| 2052 | 2052 | high confidence, process |
| absent | 2052 | header damaged, process anyway |
| 2052 | absent | **code column lost in OCR** — use rung 2/3 of [[idea-01-code-anchoring]] |
| absent | absent | either plaquette or text — test for plaquette signature |

Row 3 is the one that saves fields that would otherwise be silently lost.

## Already measured in the corpus

I ran both signals on the 15 documents. Results are in
[[F001-half-the-corpus-is-not-liasse]]. Summary:

```
401009741/65784e5da67d84faf4042736   16p → liasse pages: 4,5,6,7      (25%)
504304205/63e13943526e1f30cd100db5   28p → liasse pages: 4..23        (43%)
328024377/63e8ebbb54febda17c19ee7e   42p → liasse pages: 2,3,4,5      (10%)
445070311/*                          all → NO liasse pages
820561470/*                          all → NO liasse pages
```

The last company is instructive: in `328024377`, **4 pages out of 42 contain the 12
fields.** Routing cuts the work by 10×.

## The plaquette signature

For the 7 documents with no code, the signal has to be something else. Candidates
observed:

- short, isolated section titles: `Bilan Actif`, `Bilan Passif`,
  `Compte de Résultat (Première Partie)`, `Compte de Résultat (Seconde Partie)`
- two closing dates side by side (`31/08/2021` and `31/08/2020`)
- a high density of purely numeric, right-aligned tokens

The first is the most direct and probably sufficient. See [[plaquette-vs-liasse]].

## What this buys in the README

Two sentences only someone who measured this can write:

> *"Routing identifies 75 of the 415 in-scope pages as content-bearing. Escalating to the
> VLM only on those, the cost per document drops from €0.041 to €0.0075 with no loss in
> field coverage — the measurement is in `reports/routing.json`."*

> *"In `328024377`, 4 pages out of 42 carry the 12 fields. A pipeline that sends the whole
> PDF to a model pays 10× more to read the same rows."*

## Links

- [[cost-per-page]] · [[liasse-fiscale]] · [[plaquette-vs-liasse]]
- [[F001-half-the-corpus-is-not-liasse]] · [[idea-05-verifier-as-router]]
