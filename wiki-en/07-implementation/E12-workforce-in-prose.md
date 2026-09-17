---
type: implementation
stage: E12
tags: [code, running-text, regex, tests]
status: draft
updated: 2026-09-16
---

# E12 — the workforce count in running text

**State:** done · 453 passing tests, 4 skipped · `ruff` clean

**What changed in the deliverable:** `META_AVG_WORKFORCE_FRGAAP` goes from **1 of 15**
documents to **6 of 15**. The five new values don't come from any table.

## Why this field is different from the other eleven

The brief warns: *"average workforce is not a monetary value at all."* What it doesn't
warn — and only measurement shows — is that it's also not a **table** value. Only
`504304205` has form 2058-C with the `YP` line, read by E5's code extractor unchanged. In
the other four documents where the number appears, it sits inside a sentence in the annexe:

```
data/328024377/…/page_019.json    Effectif moyen du personnel 43 personnes
data/328024377/…/page_043.json    Effectif moyen du personnal . 47 personnes.
data/445070311/…/page_005.json    L'effectif salarié moyen à la clôture de l'exercice
                                   s'élève à 33 personnes contre 38 personnes à la
                                   clôture de l'exercice précédent.
```

This isn't table extraction with one fewer column. It's something else: finding a sentence
in the middle of a paragraph and reading the right number out of it. Hence a small, dedicated
module, instead of forcing `columns.py` or `catalog.py` to do something they weren't built
for.

## What was created

```
src/liasse/extract/workforce.py       search by sentence, not by table
tests/unit/test_extract_workforce.py  16 tests
```

Zero changes to any existing module beyond three lines in `cli.py` and
`verify/runner.py` calling the new module when the form didn't resolve the field.

## The trap: the sentence that names two years

```
L'effectif salarié moyen à la clôture de l'exercice s'élève à 33 personnes
contre 38 personnes à la clôture de l'exercice précédent.
```

A regex that grabs "the number closest to the word effectif" has a 50% chance of being
right here, because **both numbers are real** — 33 is this exercise's headcount, 38 is the
prior year's, and both appear in the same sentence, in the same breath. It's exactly the
`FJ+FK` pattern from E3: two plausible readings, one sentence, and the difference matters.

The fix isn't "search for `effectif` and look nearby." It's **making each dialect its own
pattern, anchored to a word that only appears once in the sentence**:

```python
Phrasing(
    "FT_EFFECTIF_SALARIE_MOYEN",
    re.compile(r"effectif salarie moyen .{0,80}?s eleve a (\d{1,6}) personnes?\b"),
    "a sentence that states this exercise and the one before it, in that order",
)
```

The capture group is pinned to `s'élève à`, which only ever introduces the current
exercise's number. The sentence's second number is never reached, because the pattern has
already matched and stopped.

## The second trap: the form row can't become a false positive

```
Effectif moyen du personnel * (dont: apprentis: handicapés): YP 9 9
DECLARATION DES EFFECTIFS Effectif moyen du personnel * : YP 0
```

These two lines exist in the corpus and **must not** match the running-text pattern — they
are already read by E5's code extractor, with a real code (`YP`) and a form page identified
by the router. If the sentence pattern matched here too, the same fact would be counted
through two different paths, and on one of them without the rigor of code anchoring.

What prevents the collision: the pattern requires `\d{1,6} personnes?` right after
"effectif moyen du personnel" — the form row doesn't end in "N personnes," it ends in
"YP N N." Tested explicitly:

```python
def test_the_form_row_is_not_matched_by_the_prose_patterns():
    assert _matches("Effectif moyen du personnel * (dont: apprentis: handicapés): YP 9 9") is None
    assert _matches("DECLARATION DES EFFECTIFS Effectif moyen du personnel * : YP 0") is None
```

## Where the search runs: every page, not the routed ones

```python
def find(pages: Iterable[OcrPage]) -> RawValue | None:
    for page in pages:
        ...
```

E2's router exists so extraction isn't spent on a page that has none of the twelve fields —
and the workforce sentence lives exactly on the pages the router correctly discards as
running text, with no table grid at all. Running the sentence search over **every** page of
a document, not just the routed ones, doesn't contradict E2: the router decides about
tables, and this module handles what isn't one.

## Precedence: the code always wins

In `runner.py` and `cli.py`, running text is only consulted when the form did **not**
resolve the field:

```python
if WORKFORCE_KEY not in reported:
    prose = find_workforce(pages)
```

`YP` is a stronger anchor — a code fixed by law, on a form page identified by the router —
than a sentence matched by regex. Where both exist, the code wins, even though it never
happens in the current scope (no document has both sources at once).

## Every spelling was read off the corpus

Two spelling variants survive in the text: `personnel` and `personnal` (an OCR error, not
mine), and the value read stays correct because the pattern tolerates `personn\w*`. No
spelling was anticipated — each one has an OCR line behind it in
`test_extract_workforce.py`.

## What was left out

- **`820561470`, `401009741`, one of the three from `445070311`.** No sentence, no form
  2058-C — the workforce simply isn't declared in these documents. Left absent, with
  `fields_absent` listing the reason, instead of an invented zero.
- **A third sentence dialect.** Five documents, two patterns, full coverage of what exists
  in the current scope. A sixth document with a third way of saying the same thing would
  break the closed pattern set — which is exactly why each `Phrasing` carries the evidence
  of the page that produced it, so the next person knows what to generalize from.

## Links

- [[E5-liasse-extractor]] · [[E2-page-routing]] · [[E10-plaquette-extractor]]
- [[the-12-fields]]
