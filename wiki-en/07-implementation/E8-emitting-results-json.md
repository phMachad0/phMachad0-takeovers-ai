---
type: implementation
stage: E8
tags: [code, deliverable, schema, tests]
status: draft
updated: 2026-09-16
---

# E8 — emitting `results.json`

**State:** done · 340 passing tests, 4 skipped · `ruff` clean
**Exit criterion:** done — the JSON **validates** against the schema Takeovers sent.

```
75 values from 15 filings
validates against challenges/bilan/schema/results.schema.json
wrote results.json
```

**The submission exists from this point on.** Every following stage improves a valid
artifact instead of completing one that doesn't exist yet.

## What was created

```
src/liasse/emit/results.py    assembles the deliverable
src/liasse/cli.py             `liasse emit` and `liasse check-boxes`
tests/unit/test_emit_results.py
results.json                  at the repo root, as the brief requires
```

## The two rules that govern the file

### Absence is reported, never invented

`financial_fields.json` is explicit — *"If a field is genuinely absent from a document,
omit it rather than reporting 0"* — and the brief says why it matters: twelve fields with
three silently wrong are worth less than six reported honestly.

So a field that wasn't read **is left out**, and the reason travels with the document in
`fields_absent`.

### All 15 documents appear, including the 7 that weren't processed

```json
{
  "pdf": "data/445070311/bilans/pdf/bilan_2022-02-14_63e2481c….pdf",
  "siren": "445070311",
  "fiscal_year_end": "2020-06-30",
  "fields": [],
  "not_processed": "plaquette format: the accountant's own presentation, with no liasse
                    line codes. The label-anchored extractor for it was not built."
}
```

Listing rather than omitting: whoever reads the file is **told** which ones were left out,
instead of having to notice that seven went missing.

## What each value carries

```json
{
  "field_key": "PL_REVENUE_FRGAAP",
  "value": 1800826, "unit": "EUR", "page": 4,
  "bbox": [0.8515, 0.2149, 0.9458, 0.2274],
  "snippet": "1 800 826",
  "confidence": 0.85,
  "extraction": { "tier": "LABEL", "components": [...] },
  "unit_evidence": { "rule": "form_default_eur", "rejected_markers": [...] },
  "verification": { "checks_passed": ["V2a"], "checks_failed": [] }
}
```

The four extra fields are allowed by the schema, and each answers a question the required
ones don't:

| extra field | question |
|---|---|
| `extraction.tier` | was the code read, or did the label save the line? |
| `extraction.components` | which terms this sum is made of, each with its own box |
| `unit_evidence.rejected_markers` | was the kEUR trap **seen and judged**? |
| `verification` | which independent checks this value survived |
| `schema_ambiguity` | where `label_fr` and `notes` disagree, **both** readings |

The `bbox` isn't a field filled in at the end — it's what's left over from never having
discarded the tokens.

## `liasse check-boxes` — the O6 oracle

```bash
python3 -m liasse check-boxes --n 12
```

Samples values from `results.json`, draws each box over the page with Takeovers' **own**
`tools/bbox_viewer.py`, and saves the result to `artifacts/boxes/`.

It's the one oracle no automated check replaces: every other check compares number to
number, so a consistently wrong reading of the same form would pass all of them. Only
looking catches a box pointing at the wrong line — and in this project a wrong code
interpretation survived a scan of the entire corpus and two pages written before a single
rendered page exposed it
([[F013-the-ocr-reads-the-code-column-as-vertical-text]]).

Check for this stage, by eye:

| field | what the box encloses |
|---|---|
| `BS_TOTAL_ASSETS = 1,717,114` | the **Net** column, next to `270,271` (depreciation) ✓ |
| `PL_FINANCIAL_RESULTS = −76,778` | `76,778)` with the `(` visible on the left ✓ |

## The tests

| test | what it protects |
|---|---|
| **validates against the sent schema** | *"a submission we cannot parse is a submission we cannot score"* |
| **the file on disk also validates** | the builder being right, but not the write |
| every box is `0 ≤ x0 < x1 ≤ 1` | the schema rejects `1.03` and drops the whole submission |
| no box covers the whole page | a wide box means tokens from different blocks got merged |
| `count` only for the workforce field | *"do not attach a currency to it"* |
| `fiscal_year_end < deposit_date` | the closing date is not the filing date |
| the PDF path exists on disk | |
| **building twice gives the same file** | no dict ordering or timestamp leaking |

## The `run` block

Filled in by **measurement**, not by a constant:

```json
"run": {
  "cost_eur_per_page": 0.0,
  "seconds_per_page": 0.00072,
  "pages_processed": 415,
  "model": "provided OCR + rules",
  "notes": "No API is called and no credential is read, so the marginal cost is zero…"
}
```

The schema explicitly accepts `"provided OCR + rules"` as `model`. Defending that number —
and the cost-versus-accuracy curve it should sit next to — is [[E9-cost-measurement|E9]].

## Next

[[phase-2-extraction|E9 — cost measurement]], which closes Track A.

## Links

- [[E7-verifiers]] · [[the-bilan-challenge]] · [[ADR-002-schema-ambiguities]]
- [[bbox-and-normalization]] · [[testing-strategy]] · [[cost-per-page]]
