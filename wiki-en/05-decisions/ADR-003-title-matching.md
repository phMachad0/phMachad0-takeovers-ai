---
type: decision
id: ADR-003
tags: [ocr, routing, generalization]
status: draft
updated: 2026-09-16
---

# ADR-003 — title matching: why fuzzy, and why at word level

**Date:** 2026-09-16 · **Status:** accepted · **Prompted by:** Pedro

## Context

E2 identified a plaquette's statements by their printed title. Two OCR corruptions in the
corpus broke exact matching:

- `Bilan Passif` → `Bilan Passi**t**` (`328024377`)
- `Compte de Résultat` → `Compte de Résu**i**tat` (`445070311`)

The first fix was a wildcard in each pattern: `passi.` and `resu.?tat`.

**Pedro pointed out that this is fitting to the sample.** That's correct, and the brief is
explicit about the cost of doing that:

> *"If your pipeline only works on the first company you open, you will find out here."*

The five companies were chosen to differ from one another. Hard-coding the two observed
corruptions works on these 15 documents and nowhere else.

## The question this raised: is fuzzy matching a problem here?

[[idea-01-code-anchoring]] had argued that fuzzy matching over labels is fragile —
*"too high and it loses the label; too low and it matches `Achats de marchandises` with
`Achats de matières premières`"*.

**That conflated two different problems.** That argument holds for discriminating among
~50 long, similar-looking labels inside a table. Classifying a page among **four** distinct
titles is a different problem with a different answer. Fuzzy matching is appropriate here.

## What the measurement showed

Three things, two of them against expectation.

**1 · Whole-string similarity is the wrong metric.** Measuring `SequenceMatcher.ratio()`
of each token against the canonical titles, the worst true positive was the standalone
token `PASSIF`, at **0.667** — because whole-string ratio penalizes fragments. The OCR
breaks lines wherever it wants, and a title split across two tokens is common.

**2 · The high-ratio "false positives" weren't a title-matching problem.** `COMPTE DE
RESULTAT` at ratio 1.000 are the **divider pages** — rejected by numeric density. `BILAN -
ACTIF` at 0.917 are **liasse** pages, decided by the header, which takes precedence. Title
matching was never the discriminator; the guards were.

**3 · Vocabulary separation is measurable, and generous.** Minimum edit distance between
any two words in the discriminating vocabulary:

```
bilan · actif · passif · compte · resultat · premiere · seconde · deuxieme · partie

global minimum: 3   (actif ↔ passif)
```

With a minimum of 3, a tolerance of **1 edit** cannot map a corrupted word onto the wrong
neighbor. The tolerance stops being a tuned parameter and becomes a **bound derived from a
checkable property**.

## Decision

Matching **at word level**, with a tolerance of 1 edit, **anchored at the start**.

```python
TitleSpec("BS_LIABILITIES", (frozenset({"bilan"}), frozenset({"passif"})))
```

Three rules, each solving a distinct problem:

| rule | solves |
|---|---|
| edit distance ≤ 1 per word (≥ 5 letters) | OCR corruptions, observed **and unobserved** |
| word-level matching, not whole-string | titles split across tokens (standalone `PASSIF`) |
| the title must **start** the sequence, in order, skipping only articles | `Notes sur le compte de résultat` |

The third rule looks the least important and matters the most. **Presence isn't title.**
`Notes sur le compte de résultat` heads a table in the annex and contains every word of
`Compte de Résultat`. Requiring presence flagged 19 extra annex pages as statements;
requiring the title to *start* the sequence brought the count back to the same 60 pages the
regex found — with a general-purpose mechanism.

This is structural, not a threshold: a printed title doesn't *contain* its words, it
*starts with* them.

## The test that backs the decision

```python
def test_the_vocabulary_separation_justifies_the_tolerance():
    separation = minimum_separation(VOCABULARY)
    assert separation >= 2 * MAX_EDITS + 1
```

It doesn't test a single case; it tests the **property that licenses the tolerance**. If
someone adds a word to the vocabulary that's 2 edits from another, the test fails right
there, not in production. Checked: raising `MAX_EDITS` to 2 breaks exactly this test.

## Consequences

- Seven corruptions **not** present in the corpus are now handled: `pasif`, `passlf`,
  `pa5sif`, `resulta`, `resu1tat`, `actlf`, `bi1an`. The earlier regex would have failed on
  all of them.
- New module `text/fuzzy.py` (layer 1), reusable by step 3 of the
  [[idea-01-code-anchoring|anchor ladder]] in E5 — where the problem is the *other* one, and
  where the original warning about thresholds applies again.
- `routing/titles.py` split from `signals.py`: recognizing the title and deciding whether
  the page is a statement are separate responsibilities.
- The routing count didn't change: **60 of 415 pages**. The change bought generality, not
  coverage — which is how it should be, since the previous result was already correct on
  this corpus.

## What's still a choice, not a deduction

The **vocabulary** is domain knowledge: the words come from French accounting vocabulary,
not from these 15 PDFs. That's legitimate and different from fitting to the sample — the
distinction is between encoding *what the thing is* versus encoding *how it happened to
come out wrong here*.

A sixth company calling the statement `État de résultat` wouldn't be recognized. The right
fix for that is adding the spelling to the vocabulary, not loosening the tolerance.

## Links

- [[E2-page-routing]] · [[idea-04-page-routing]] · [[idea-01-code-anchoring]]
- [[testing-strategy]] · [[ADR-002-schema-ambiguities]]
