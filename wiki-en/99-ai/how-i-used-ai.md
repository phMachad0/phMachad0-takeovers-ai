---
type: meta
tags: [ai, readme, honesty]
status: draft
updated: 2026-09-14
---

# Living draft — "How I used AI"

The brief requires a section with this exact heading in the final README:

> *"a section in your `README.md`, headed **"How I used AI"**, saying what you delegated,
> what you checked yourself, and anywhere the tool led you somewhere wrong. A short, honest
> paragraph is worth more to us than a long one."*

This page collects the raw material as the work happens. **The final text has to be
short** — a paragraph or two. Everything goes in here; only what matters goes in there.

## Session log

### Session 1 — 2026-09-13/14 · reconnaissance and wiki

**Tool:** Claude Code (Opus), interactive session.

**What was delegated:**
- Reading both briefs and the JSON schemas, with a comparative summary of the tracks.
- Ad hoc reconnaissance scripts over the OCR: page counts, form-header detection, code
  counts per page, unit-marker search, token dumps with coordinates sorted by band.
- Writing this entire wiki, including the French accounting explanations.

**What I verified myself:**
- *(to fill in as I go — tracking which sections I've personally read and checked)*

**Where the tool led me somewhere wrong:**
- In the first track recommendation, it claimed that anchoring by liasse codes would solve
  the corpus, based on **a single page** from **a single company**. The later measurement
  across the 15 documents showed that **7 of them have no codes at all**
  ([[F001-half-the-corpus-is-not-liasse]]). The idea is still good, but the claimed reach
  was wrong by a factor of two. Lesson recorded: *a one-page sample is not a measurement of
  the corpus.*

**Findings that came from measurement, not from the model:**
Worth separating this out in the README. The statements below are results of running code
over the data, and each one has its evidence attached on the corresponding page:
- [[F001-half-the-corpus-is-not-liasse]] — 8 liasse / 7 plaquette
- [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] — partially contradicts the brief
- [[F003-the-ocr-breaks-numbers-apart]] — `1,805,459` arrives as 3 tokens
- [[F004-negatives-are-printed-in-parentheses]] — `GV`'s sign inverted by a lost parenthesis
- [[F005-the-ocr-loses-part-of-the-code-column]] — `FS`…`FX` missing

## The wiki as part of the answer

This wiki is itself an argument for how to use AI well: the model did the reading, the
measurement, and the drafting; I directed it, checked its work, and signed off on it.

Worth mentioning the wiki in the final README, with one sentence and a link to the
directory. Not as decoration: as evidence that the process was traceable.

## Skeleton of the final text

> The pipeline was built with Claude Code. I delegated: reading the French-language
> documents, reconnaissance scripts over the OCR, and writing the documentation. I verified
> myself: ⟨…⟩. The model got ⟨…⟩ wrong — it claimed ⟨…⟩ based on a one-page sample, and the
> measurement across the 15 documents showed ⟨…⟩. The architecture decisions ⟨…⟩ are mine
> and are justified in ⟨…⟩. The full reasoning is versioned in `wiki/`.

## Links

- [[the-bilan-challenge]] · [[00-overview]]
