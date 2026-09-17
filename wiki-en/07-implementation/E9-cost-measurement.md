---
type: implementation
stage: E9
tags: [code, cost, measurement, vlm, tests]
status: draft
updated: 2026-09-16
---

# E9 — cost measurement

**State:** done · 370 passing tests, 4 skipped · `ruff` clean
**Exit criterion:** done — the `run` block is filled in by **measurement**, and there is a
test that fails if any of the three numbers is a literal in the code.

With this, **Phase 2 closes** and Track A is complete: there is a valid `results.json`,
with provenance, verification, and now cost.

## The question E9 answers

The brief doesn't ask *how much did it cost*. It asks something else:

> *"whether your cost claim is **derived or guessed**"*

Those are two different claims with the same numeric value. "The cost is €0.00" and "the
cost **came out to** €0.00" print the same characters and mean opposite things. All of E9
exists to make the second one verifiable.

## What was created

```
src/liasse/cost/meter.py      what the run measured  (clock, pages, ledger, prices)
src/liasse/cost/vlm.py        what a VLM would cost   (derived, never measured)
src/liasse/cost/report.py     reports/cost.json, split into `measured` / `derived`
src/liasse/cli.py             `liasse cost`, and `liasse emit` now runs under the meter
tests/unit/test_cost_meter.py 15 tests
tests/unit/test_cost_vlm.py   12 tests
reports/cost.json             the artifact
```

---

## The decisions that matter

### 1. The zero is a division, not a constant

The deterministic cost is €0.00 per page. The temptation is to write `0.0`. What the code
does instead:

```python
@property
def eur_per_page(self) -> float:
    return self.ledger.eur() / self._denominator()
```

`ledger.eur()` is `math.fsum` over the list of API calls made — an **empty** list, because
no call was made. The sum over nothing is zero. That's a derivation that *today* comes out
to zero and **stops** coming out to zero the instant a call is logged. A hand-written `0.0`
doesn't have that property, and that's exactly the difference the brief is reading for.

The test that pins this:

```python
meter = _meter(1.0, 10)
assert meter.eur_per_page == pytest.approx(0.0)

meter.ledger.record("one page", "claude-opus-5", 1_000_000, 0)
assert meter.eur_per_page == pytest.approx(FX.to_eur(5.00) / 10)
```

### 2. A meter that measured nothing refuses to answer

```python
def _denominator(self) -> int:
    if not self.pages:
        raise NothingMeasured(
            "no pages were counted, so there is no rate to report..."
        )
```

The failure mode this stage exists to prevent isn't reporting the wrong number — it's
reporting a comfortable zero that comes from zero data. `0 pages` and `0 seconds` divide
into a `ZeroDivisionError` or, worse, a plausible-looking `0.0`. The meter raises instead.

### 3. How you prove a number isn't a constant

This exit criterion is unusual: it's not that the number is **correct** — a correct
constant passes any value assertion you can write. So the tests attack the **shape**
instead.

**Dynamically** — the same code path, two clocks, two page counts:

```python
assert _meter(4.0, 2).seconds_per_page == pytest.approx(2.0)
assert _meter(4.0, 8).seconds_per_page == pytest.approx(0.5)
assert _meter(1.0, 8).seconds_per_page == pytest.approx(0.125)
```

No constant satisfies all three. The clock is injectable (`Meter(clock=FakeClock(...))`)
for exactly this reason.

**Statically** — `ast` over all of `src/liasse/`: any dict literal carrying the key
`cost_eur_per_page` has its three required fields checked, and none of them may be a
numeric `ast.Constant`. A further test guarantees `cli.py` does **not** assemble its own
`run` block, or it would escape the first guard. And an `assert found` at the end: if the
guard finds no block at all, it was checking against nothing — the same lesson as E7.

### 4. `measured` and `derived` never mix

`reports/cost.json` is split into two at the top level, and the derived half opens with its
own admission:

> *"No API call was made: this repository holds no credential and reads none. Every number
> below is arithmetic over measured page sizes, published prices and the stated
> assumptions. It is a derivation, not a measurement."*

No credential exists in this environment and none was introduced. Turning one line of the
curve into a real measurement is [[E11-vlm-escalation]]'s job, and it costs a few cents of
API.

### 5. Two named assumptions, and the size of the measured error

The VLM curve rests on three things, and they're kept separate in the report:

| origin | what |
|---|---|
| **measured** | the real size of the 415 pages, read from the PDFs; the router's page count |
| **published** | Anthropic's image tokenization and prices (read on 2026-06-24); ECB exchange rate as of 2026-09-16, 1 EUR = 1.1537 USD |
| **assumed** | **one** thing: how many characters make a token (4.0) |

The prompt and the response aren't guessed — they're **counted in real text characters**
and converted by that ratio. The prompt is the challenge's own
`financial_fields.json` (1,000 tokens/page). The response is the `results.json` this
pipeline already emits, reduced to the five keys the schema requires (36 tokens per page
that has a field).

And the report measures **how much that assumption matters**: the response is 3.0% of the
bill in the routed scenario and 0.45% in the run-everything scenario. Even getting the
ratio wrong by 50%, the total moves 1.5%. The assumption is isolated and its influence is
quantified, instead of just defended.

---

## The numbers

### Measured

```
415 pages · 1.673 s total · 0.00403 s/page · €0.00/page · 0 API calls
  count_pages           0.0045 s
  route_extract_verify  1.4630 s
  build_documents        0.2059 s
```

### Derived at 200 dpi — € per **corpus** page

| scenario | pages sent | opus 5 | sonnet 5 | haiku 4.5 |
|---|---:|---:|---:|---:|
| `deterministic` — what the pipeline does | 0 | 0.000000 | 0.000000 | 0.000000 |
| `escalate_plaquettes` | 29 | 0.001806 | 0.001084 | 0.000361 |
| `vlm_on_routed_pages` | 60 | 0.003737 | 0.002242 | 0.000747 |
| `vlm_on_every_page` | 415 | 0.025180 | 0.015108 | 0.005036 |

The row that carries the argument is the last against the second-to-last: **6.92× more
money for the same answer**. The 355 discarded pages were measured by the router as
containing none of the 12 fields ([[E2-page-routing]]). The router is the only decision in
this table that changes the bill by a **factor** instead of a fraction — and it costs zero.

### An unplanned finding: resolution saturates

Measuring the actual pages instead of assuming A4:

```
87 distinct page sizes across the 415   (these are scans; none agree to the millimeter)
415 of 415 pages hit the 4,784-token-per-image ceiling, at 200 dpi
saturation resolution: 192–193 dpi
```

Above ~193 dpi the image is either downscaled by the 2,576 px longest-edge limit, or hits
the per-image token ceiling. **Rendering higher costs the same and shows the model less.**
This was an engineering decision about to be made by guessing — the `.env.example` comment
said cost grows with the square of dpi, which is only true below saturation. The comment
was corrected.

---

## What changed outside the `cost` package

- `emit/results.py`: `build()` now accepts already-assembled `documents`. The caller
  measuring the run needs to **time** that assembly and report the time inside the file
  itself — which isn't possible if the assembly stays hidden inside.
- `cli.py`: `liasse emit` now runs under the `Meter`, in three timed stages. The page count
  comes from listing files, not loading them: parsing 415 pages of OCR just to know how
  many there are would put the cost of measuring inside the measurement.
- `.env.example`: `LIASSE_VLM_DPI` is now **actually read**, as the default for
  `liasse cost --dpi`. The brief asks the file to name every variable the code reads; up to
  this point it named four and the code read none.

## What this stage deliberately does **not** deliver

The table has a euro column and no accuracy column. The brief asks for both — *"what it
cost per page in euros and in seconds, what it bought you in accuracy"*. The missing column
is literally what [[E10-plaquette-extractor|E10]] measures: without a plaquette extractor,
there is no coverage number for the `escalate_plaquettes` row, and inventing one would be
exactly the thing this stage was built not to do.

## Links

- [[cost-per-page]] · [[idea-04-page-routing]] · [[phase-2-extraction]]
- [[E8-emitting-results-json]] · next: E10, plaquette extractor
