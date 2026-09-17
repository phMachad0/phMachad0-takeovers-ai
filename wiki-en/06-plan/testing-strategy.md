---
type: plan
tags: [testing, quality]
status: draft
updated: 2026-09-15
---

# Testing strategy

The requirement: **each stage validated before moving to the next.** That means knowing,
for every stage, what the *oracle* is — the source that says whether the result is
correct. On a problem with no answer key, finding oracles is the work.

## The six oracles available

In order of strength. The higher up, the more the test proves.

| # | oracle | what it validates | strength |
|---|---|---|---|
| **O1** | Takeovers' own `tools/bbox_viewer.py` | coordinate conversion | **maximum** — it's their code |
| **O2** | form arithmetic (`FJ+FK=FL`, `GP−GU=GV`) | number and row reading | high — law, not heuristic |
| **O3** | balance-sheet identity (`CO == EE`) | whole balance-sheet extraction | high |
| **O4** | N−1 cross-check between two documents | end-to-end extraction | **high** — independent sources |
| **O5** | the `results.schema.json` they sent | deliverable shape | medium — validates shape, not content |
| **O6** | visual inspection of the rendered PDF | anything | low scale, high point-wise confidence |

**O1 is the most important test finding of the project**: the company shipped a reference
implementation of the part that's easiest to get wrong silently. Using it as an oracle
instead of as a manual-checking utility is free and eliminates a whole class of error.

## The six test layers

### L1 · Pure unit tests — `tests/unit/`
Functions with no I/O: geometry, number reassembly, row grouping. Fast, hundreds of them,
run in under a second.

### L2 · Frozen fixtures — `tests/golden/`
Real OCR excerpts pulled from the corpus **once** by a script and committed as small JSON.
The suite doesn't depend on `data/`'s 200 MB and runs on any machine.

The cases already documented in the wiki become fixtures directly — they already have the
coordinates:

```python
# from F003
assert parse_value(tokens("1","805","459")) == 1_805_459
# from F004, case C — the missing parenthesis
assert parse_value(tokens("2","096)")) == -2_096
# from F004, case B — a stray opening parenthesis
assert parse_value(tokens("(","52","814)")) == -52_814
# from F003 — single token with a preserved space
assert parse_value(tokens("2 524")) == 2_524
```

That's the wiki's best property: **every finding is already a written test case.**

### L3 · Differential against the company's oracle — `tests/differential/`
Sample N OCR lines across M documents, convert them with our code, convert them with
`bbox_viewer.py`'s `polygon_to_norm`, and require exact equality.

```python
@pytest.mark.parametrize("doc,page", sample_pages(n=40, seed=0))
def test_conversion_matches_the_reference(doc, page):
    for line in ocr(doc, page)["ocr"]:
        assert ours.to_norm(line["polygon"], geom) == pytest.approx(
               theirs.polygon_to_norm(line["polygon"], w_pt, h_pt), abs=1e-9)
```

### L4 · Invariants and properties — `tests/unit/`
Truths that hold for every output, tested across the whole corpus:

- `0 ≤ x0 < x1 ≤ 1` and `0 ≤ y0 < y1 ≤ 1` — without this, `results.json` doesn't validate
- `(x1−x0) < 0.98` — a page-sized box is a grouping bug
- no monetary value is `float`
- `snippet` reconstructs the number: `"".join(t.text) ≈ format(value)`
- every `RawValue` has at least one token in `tokens_used`

### L5 · Verifiers as acceptance tests — `tests/integration/`
The V1/V2/V3 verifiers are **production logic and oracle at the same time**. Run over the
corpus, they produce pass rates. The suite locks in a floor:

```python
def test_pass_rate_does_not_regress():
    r = run_corpus()
    assert r.pass_rate("V1") >= BASELINE["V1"]     # versioned baseline
    assert r.pass_rate("V2") >= BASELINE["V2"]
```

This turns "I improved the pipeline" into a number that can't drop without someone
noticing.

### L6 · Negative tests — `tests/integration/`
Proof that the verifiers aren't decorative. Inject known errors and require detection:

```python
def test_v1_detects_a_thousand_factor_error():
    values = corrupt(baseline, "BS_TOTAL_ASSETS_FRGAAP", lambda v: v / 1000)
    assert not V1.run(values).passed

def test_v2_detects_a_flipped_sign():
    values = corrupt(baseline, "PL_FINANCIAL_RESULTS_FRGAAP", lambda v: -v)
    assert not V2.run(values).passed

def test_parser_rejects_concatenation_across_columns():
    # "2 524" from column FK + "1","805","459" from column FL
    assert parse_value(tokens("2 524","1","805","459")) is None   # doesn't invent
```

The last one is what guarantees that the syntactic validation in
[[idea-02-digit-reassembly]] **rejects** instead of inventing. Without this test, there's
no way to know whether it's actually active.

### L7 · Architecture test — `tests/architecture/`
Scans the imports and fails if a layer imports from a higher layer. 20 lines, protects the
[[modular-architecture|dependency rule]] from eroding.

## The gate rule

No stage is declared done without:

1. its L1/L2 tests green,
2. its artifact generated under `artifacts/`,
3. and the stage's **specific exit criterion** satisfied — each one has its own in
   [[00-roadmap]].

## What this strategy doesn't prove

Necessary honesty, worth repeating in the README: **the verifiers measure consistency, not
truth.** If digit reassembly fails the same way on both documents of an N−1 pair, V3
approves both. Consistency between independent sources is the best available approximation
of truth without an answer key — it isn't the same thing.

Cheap partial mitigation: **O6**, a sample of 10 to 15 values checked by eye against the
rendered PDF, picked among the ones that passed everything else. If those 15 are correct,
the probability of an invisible systematic error drops a lot. This goes into the README as
"I manually checked N values, here they are."

## Links

- [[modular-architecture]] · [[00-roadmap]] · [[idea-05-verifier-as-router]]
