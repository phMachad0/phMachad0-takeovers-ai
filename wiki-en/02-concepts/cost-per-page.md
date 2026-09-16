---
type: concept
tags: [cost, llm, evaluation]
status: draft
updated: 2026-09-16
---

# Cost per page: the question the challenge is really asking

The bilan track's `results.json` requires a `run` block:

```json
"run": {
  "cost_eur_per_page": 0.0,
  "seconds_per_page": 0.0,
  "pages_processed": 0,
  "model": "...",
  "notes": "..."
}
```

And the brief says what will be checked: *"whether your cost claim is **derived or
guessed**"*.

That's a production-engineering question disguised as a form field. A company processing
hundreds of thousands of registry pages needs to know its marginal cost precisely, because
it multiplies.

## The three possible architectures and their cost profiles

| approach | € / page | s / page | fails as |
|---|---|---|---|
| **rules over the provided OCR** | **0.00** (CPU only) | ~0.01–0.1 | silently, when the layout departs from what's expected |
| **own OCR + rules** | ~0.00 (local CPU/GPU) | ~1–5 | digit-reading errors, and you inherit the cost of maintaining an engine |
| **vision model (VLM) on the page image** | **0.002–0.02** | ~2–10 | hallucinates a plausible number; also fails silently, just differently |

The interesting column is the last one. The brief says: *"They cost different amounts and
they **fail in different ways** — which is the point of the cost question."*

## How to derive a VLM's cost honestly

You don't guess. You count:

1. **Input tokens per page.** A page image's token cost depends on resolution:
   `tokens ≈ (width_px × height_px) / 750`. **But it's capped** — the longer edge is
   downscaled to 2,576 px and there's a ceiling of 4,784 tokens per image. Measured across
   the 415 in-scope pages in [[E9-cost-measurement]]: at 150 dpi a page comes out to ≈ 2,900
   tokens; **from 192–193 dpi onward every page hits the ceiling**, and rendering higher
   costs the same while showing the model less. The engineering decision isn't "150 or 300
   dpi" — it's "where's the saturation point," and that's something you measure.
2. **Output tokens.** Count them for real from the response, don't estimate.
3. **Published model price**, in USD per million tokens, with the date it was checked.
4. **USD → EUR conversion**, with the rate and the date.

And then: **instrument the pipeline to accumulate this at run time**, not calculate it in a
spreadsheet afterward. A counter that sums `input_tokens` and `output_tokens` from every
call and divides by the number of pages produces a *derived* number, not a guessed one.

For the deterministic approach the number is **€0.00 per page**, and that's not an excuse —
it's a result, and `seconds_per_page` measured with `time.perf_counter()` is the real
metric.

## Why a single cost line is a weak answer

Reporting *"€0.004/page"* answers the question but doesn't show any thinking. What shows
thinking is a **curve**:

Measured in [[E9-cost-measurement]], in € per page **of the corpus** (415 pages), at 200
dpi:

| configuration | pages sent | opus 5 | sonnet 5 | haiku 4.5 |
|---|---:|---:|---:|---:|
| deterministic only | 0 | 0.000000 | 0.000000 | 0.000000 |
| VLM on plaquettes only | 29 | 0.001806 | 0.001084 | 0.000361 |
| VLM on all routed pages | 60 | 0.003737 | 0.002242 | 0.000747 |
| VLM on all 415 pages | 415 | 0.025180 | 0.015108 | 0.005036 |

The **accuracy column doesn't exist yet** — that's what E10 measures. A cost table without
an accuracy column is half an answer, and naming which half is missing beats filling it in
from memory.

A table like this says: *I know where the knee of the curve is*. The last two rows are the
strongest argument, because they show that **7× more money buys zero extra accuracy** —
which is only demonstrable if you have the page routing from [[idea-04-page-routing]] and
the selective escalation from [[idea-05-verifier-as-router]].

## The corpus scale arithmetic

Measured: the 15 in-scope documents add up to **415 pages**. Of those, **60** carry at
least one of the 12 fields — not ~75, which is what this page estimated before
[[E2-page-routing]] actually counted.

```
415 pages  →  €0.0151/corpus page    ← VLM on everything      (sonnet 5, 200 dpi)
 60 pages  →  €0.0022/corpus page    ← routed pages only
                                        6.92× reduction
```

On a production corpus with hundreds of thousands of documents, that 6.92× is the
difference between a viable service and an unviable one. And it's obtained by a page
classifier that costs nothing. The 355 discarded pages were measured, not assumed, to carry
none of the 12 fields: the extra money buys **the same answer, later**.

## Links

- [[idea-04-page-routing]] · [[idea-05-verifier-as-router]]
- [[the-bilan-challenge]] · [[E9-cost-measurement]]
