---
type: implementation
stage: E7
tags: [code, verification, accuracy, tests]
status: draft
updated: 2026-09-16
---

# E7 — verifiers

**State:** done · 322 passing tests, 4 skipped · `ruff` clean
**Exit criterion:** done — `reports/verification.json` is generated, and the negative tests
pass — the verifiers fail when they should.

```
V0: 5/5 = 100%     V1: 8/8 = 100%     V2a: 6/6 = 100%
V2b: 6/6 = 100%    V2c: 5/5 = 100%    V3: 6/10 = 60%
```

## What was created

```
src/liasse/fields/checks.py     codes read only for the checks (EE, FJ, FK, GP, GU, HN, DI)
src/liasse/verify/registry.py   Check · CheckResult · @check · rounding tolerance
src/liasse/verify/checks.py     V0, V1, V2a, V2b, V2c, V3
src/liasse/verify/confidence.py confidence derived from independent checks
src/liasse/verify/runner.py     assembles the facts and runs everything
src/liasse/verify/report.py     reports/verification.json
```

## The six verifiers

| id | what it compares | source of independence |
|---|---|---|
| **V0** | `dateCloture` from the registry × the date printed on the form | two different parties produced the data |
| **V1** | total assets (2050) × total liabilities (2051) | two pages, two anchors |
| **V2a** | `FJ + FK` × `FL` | the total against its own terms |
| **V2b** | `GP − GU` × `GV` | same |
| **V2c** | `HN` (2053) × `DI` (2051) | the whole income statement against the balance sheet |
| **V3** | column N of one filing × column N−1 of the following one | **two documents filed in different years** |

V3 is the strongest, and it's the one the brief hands to us on a plate: *"each restates the
previous exercise in its own N-1 column"*. Agreement there is not self-consistency — it's
two sources, typed, scanned, and read separately, meeting each other.

## The tolerance is a rounding budget, not a convenience factor

E4 left an open item: in one filing, `FJ + FK = 5,564,580` against a printed `FL` of
**5,564,581**. A discrepancy inside the document itself.

Each printed figure is rounded to the euro on its own, so a sum of *n* terms can land up to
`n/2` units away from the printed total without either side being misread. The tolerance is
exactly that budget:

```python
def rounding_tolerance(terms: int) -> int:
    return max(1, terms // 2)
```

**It is never wide enough to absorb a digit.** A test pins both sides: a €1 difference
passes, a €100 one does not.

## Confidence, derived, not decorated

The schema has a `confidence` field. Filling it with the OCR's `score` would answer a
different question — that is confidence about *pixels*, not about the interpretation. Here
it comes from **how many independent checks the value survived**:

| situation | score |
|---|---|
| no check reached the field | 0.60 — unverified, which is different from wrong |
| 1 check | 0.85 |
| 2 | 0.93 |
| 3 or more | 0.97 |
| **any failure** | **0.30** — the document disagrees with itself |

And the aggregator counts only the **applicable** checks: a field with no N−1 counterpart is
not penalized for V3 not having run. Silence and agreement can never look the same.

## What V3 found

```
504304205, fiscal year 2016-12-31:
   2016 filing states TOTAL GÉNÉRAL = 1,807,858
   2017 filing restates TOTAL GÉNÉRAL = 1,807,435     Δ = 423 €
```

Each filing is **internally consistent** — in both, the 2050 matches the 2051. They
disagree **with each other** about the same fiscal year. `DI`, `HN`, and `GU` from the same
pair match exactly, so it's not a column shift or a reading error: it's the 2016 balance
sheet being re-stated with a different number.

It is exactly what the parent README asks to have reported: *"sometimes tells you the
sources disagree — which is itself a finding worth reporting."*

## The honest number

```
20 of 75 values agree with an independent check (27%); 0 contradicted, 55 unverified
```

**27% is low, and it's the truth.** The verifiers reach total assets, revenue, and the
financial result; they do not reach COGS, personnel expense, external services, tax, or
cash — there is no second declaration of those values in the forms to compare against.

The temptation would be to inflate the number by counting checks that do not apply. The
report keeps three things separate: **verified**, **contradicted**, and **unverified**. And
the JSON's `about` field states what the metric is not:

> *these checks measure agreement between statements the documents make more than once —
> not truth, and a consistently wrong reading of the same form would pass.*

## The bug I had, and the test it produced

The first run reported a clean sheet: **zero checks run**, 100% of nothing. `verify/checks.py`
was never imported, so the decorators never executed and the registry stayed empty.

I wrote a guard test — and it **did not catch the bug**, because the test file itself
imports `checks`, populating the registry in the test process. The guard had to be
**static**:

```python
def test_the_runner_imports_the_checks_itself():
    source = (paths.REPO_ROOT / "src/liasse/verify/runner.py").read_text()
    imported = {...ast...}
    assert any("checks" in m for m in imported)
```

## Proof the verifiers fail when they should

| mutant | result |
|---|---|
| `BS_TOTAL_ASSETS` goes back to reading the Brut column | **V1 drops to 0/8**, 8 values contradicted ✅ |
| tolerance turned into a convenience factor (10,000) | 3 tests fail ✅ |
| registry not imported by the runner | the static guard fails ✅ |

The first is the most telling: it's the real bug V1 caught during E5, reinjected.

## Next

[[phase-2-extraction|E8 — emitting `results.json`]], where the submission starts to exist
and validating against the company's schema is the gate.

## Links

- [[E6-units]] · [[idea-05-verifier-as-router]] · [[F007-the-n-1-chain-has-holes]]
- [[F011-v1-confirmed-and-the-column-structure]] · [[testing-strategy]] · [[cost-per-page]]
