---
type: implementation
stage: E2
tags: [code, routing, cost, tests]
status: draft
updated: 2026-09-16
---

# E2 — page routing

**State:** done · 200 green tests, 4 skipped · `ruff` clean
**Exit criterion:** ✅ `reports/routing.json` generated; the router **agrees with the 15
formats measured by hand** in E1.5.

```
60 of 415 pages carry fields (14%, a 6.92x reduction)
```

## What was created

```
src/liasse/text/codes.py        liasse-code sanity filter                (layer 1)
src/liasse/text/numbers.py      numeric predicate + density               (layer 1)
src/liasse/text/fuzzy.py        bounded edit distance                    (layer 1)
src/liasse/routing/titles.py    word-level title recognition
src/liasse/routing/signals.py   the four signals, each answering ONE question
src/liasse/routing/classifier.py  PageClass · RoutedDocument · the verdict
src/liasse/routing/report.py    builds the report dict (doesn't write a file)
src/liasse/cli.py               `liasse route`
tests/unit/test_text_codes.py · test_text_fuzzy.py · test_routing_titles.py
                                · test_routing_signals.py · test_routing_classifier.py
```

## The four signals

Each function answers **one** question and returns what it saw, never a verdict. The
verdict belongs to the classifier, and it's built as much from agreement as from
**disagreement**.

| signal | question | strength |
|---|---|---|
| **A** `DGFiP N° 2052` header | which form is printed? | precise, but fragile against scan noise |
| **B** code fingerprint | which codes appear on this page? | robust, doesn't depend on text |
| **C** plaquette title | which statement does the title announce? | precise when present |
| **D** `confidentiality` in `meta/` | was the income statement filed as confidential? | **free, before opening the PDF** |

### Signal B — signatures derived by measurement

I didn't write the signatures from memory. For each form, I extracted the codes that
appear on **every** page of that form **and on no other**:

| form | exclusive codes |
|---|---|
| 2050 | 46 |
| 2051 | 25 |
| 2052 | 18 |
| 2053 | 16 |

Very clean separation. A test (`test_signatures_do_not_overlap_between_forms`) locks in
the property: if someone adds a code that already belongs to another form, it breaks.

### Signal D — the finding of this stage

`confidentiality: "Partiellement confidentiel"` in the registry metadata predicts the
absence of the compte de résultat with **correlation 5 of 5**. It's the *déclaration de
confidentialité* under art. L. 232-25. See
[[F014-the-registry-announces-the-confidential-income-statement]].

That turns "couldn't extract it" into "it's legally absent, and the registry says so."

## The three fixes measurement forced

I wrote the classifier, ran it against the 15 documents, and three things were wrong. All
three were fixed by evidence, not intuition.

### 1 · Divider pages read as statements

`BILAN & COMPTE DE RESULTAT` on a page with 12 tokens is a **divider sheet**, not a
statement. Two exist in the corpus and both were misclassified.

Fix: require **numeric density** ≥ 0.15. A filed statement is almost all numbers; a
divider has none.

### 2 · The label-based fallback firing where it shouldn't

One document (`445070311/6860f28c`) comes back from the OCR with the reading order
scrambled and **no title at all** — numbers first, labels scattered. I wrote a fallback
that guesses the statement from the accounting labels present.

Running it, it tagged annexe tables as balance sheet in 8 other documents: a fixed-asset
schedule mentions the same words as a balance sheet.

Fix: **the fallback is a document-level recovery strategy, not a page-level one.** It only
runs when the whole document produced no statement by title, and every page it produces
comes out flagged `low_confidence` and `statement_via: "labels"`.

> The lesson extends past this stage: a last-resort heuristic needs to know it's a last
> resort. Putting it in the same function as the main path erases that distinction.

### 3 · Two titles corrupted by the OCR

- `Bilan Passif` → `Bilan Passit` (328024377)
- `Compte de Résultat` → `Compte de Résu**i**tat` (445070311)

**First solution, later discarded:** a wildcard in each pattern — `passi.` and
`resu.?tat`. It works on these 15 documents and on no others. It's fitting to the sample,
and the brief warns that the five companies were chosen to expose exactly that.

**Solution adopted:** word-level matching, with a tolerance of 1 edit justified by the
vocabulary's separation (minimum 3 edits between `actif` and `passif`), anchored at the
start of the sequence. See [[ADR-003-title-matching]].

Same page count — **60 of 415** —, with a generic mechanism and seven unobserved
corruptions now handled.

## A finding that changes the plan: three documents carry both formats

`328024377` (two filings) and `504304205/66cd893c` contain **both the DGFiP liasse and the
plaquette for the same fiscal year, in the same PDF**:

```
328024377/63e8ebbb…7e
  [liasse]    p2:BS_ASSETS  p3:BS_LIABILITIES  p4:PL  p5:PL_CONT
  [plaquette] p24:BS_ASSETS p25:BS_LIABILITIES p26:PL
```

This isn't redundancy to discard. It's **the same figures rendered two independent ways
within one document** — cross-validation between the two extractors, with no dependency
on the N−1 chain.

This is stronger than what
[[F007-the-n-1-chain-has-holes]] had assumed: there I had identified **one** plaquette↔liasse
pair, across documents from different years. Here there are **three**, in the same fiscal
year and the same file.

## The answer key we wrote ourselves

`scope.py` carries `known_format` per document, measured by hand in E1.5 before any code
existed. The central test of this stage is simply:

```python
def test_router_agrees_with_the_format_measured_by_hand(routed):
    disagreements = [...]
    assert not disagreements
```

8 liasse, 7 plaquette. It's a partial answer key we produced ourselves, and that's why it
counts — the measurement came before the code it evaluates.

## Proof that the tests catch regressions

| mutant | result |
|---|---|
| numeric density turned off (`MIN_NUMERIC_RATIO = 0`) | fails the divider test ✅ |
| edit tolerance raised to 2 | fails the vocabulary-separation test ✅ |
| title matching by presence instead of prefix | fails **5 tests**, including the answer key ✅ |
| label fallback always on | fails **4 tests**, including the format answer key ✅ |
| code sanity filter turned off | **nothing failed** ❌ |

The last one exposed a real hole: nothing was testing that the
[[F013-the-ocr-reads-the-code-column-as-vertical-text|F013]] filter actually rejects the
false `BZ`. I wrote `tests/unit/test_text_codes.py`, with one test per signal **and** one
test on the actual page where the failure happened. The mutant now fails 3 tests.

## The report

`liasse route` writes `reports/routing.json` — versioned on purpose, it's the evidence the
README cites. Every relevant page carries **the signals that justified the decision**, so
a wrong classification is diagnosable without rerunning anything.

```
totals: 415 pages · 60 relevant (14%) · 6.92x reduction
types:  prose 261 · liasse 73 · blank 52 · plaquette 29
statements: BS_ASSETS 19 · BS_LIABILITIES 18 · PL 12 · PL_CONT 8 · WORKFORCE 3
documents with confidential income statement: 5 · with both formats: 3
```

## Next

[[phase-1-foundation|E3 — row reconstruction]], which already inherits two parameters
decided by measurement: banding by **top edge**
([[F008-degenerate-boxes-and-top-edge-banding]]) and a tolerance of 22–26 px.

## Links

- [[E1-corpus-and-geometry]] · [[idea-04-page-routing]] · [[F014-the-registry-announces-the-confidential-income-statement]]
- [[plaquette-vs-liasse]] · [[testing-strategy]] · [[cost-per-page]] · [[ADR-003-title-matching]]
