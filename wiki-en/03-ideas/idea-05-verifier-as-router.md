---
type: idea
tags: [verification, cost, architecture, core]
status: draft
updated: 2026-09-14
---

# ❺ The verifier is the cost router

The central idea. The other five are improvements; this is what makes them measurable.

## The two problems it solves at once

**Problem 1 — there's no answer key.** The brief: *"There is no answer key, and we are
not hiding one."* How do you claim anything about accuracy?

**Problem 2 — when do you spend money?** A VLM costs per page and sometimes gets right
what the rule gets wrong. Calling it always is expensive. Never calling it leaves fields
on the table. What's the criterion?

The observation that connects both: **the same function that answers "is this value
correct?" also answers "is this value worth paying for?"**. A verifier is simultaneously
a quality metric and a cost-routing policy.

## The verifiers

There are three, and what matters is that they're **independent of each other** — they
use information from different sources, so agreement between them is real evidence.

### V1 — Balance sheet identity (within the page)

```
BS_TOTAL_ASSETS (CO, form 2050)  ==  TOTAL GÉNÉRAL PASSIF (EE, form 2051)
```

The brief points at this directly: *"it must reconcile against the other side of the
balance sheet. That is a check you can run yourself."*

Cost: zero. Power: high — it catches digit-reassembly errors, column swaps (N vs N-1),
and unit errors (one side in EUR, the other in kEUR, gives a factor-1000 difference).

### V2 — Internal form arithmetic (within the page)

The form is a system of equations. Several have already been verified in the corpus:

```
FJ + FK           == FL        (France + Exports = total revenue)
GP − GU           == GV        (financial income − financial expense = financial result)
DA+DB+DC+DD+DE+DF+DG+DH+DI+DJ+DK  ==  DL   (components = total capitaux propres)
GG + (GH−GI) + GV == GW        (operating result + shared + financial = current)
```

Each equation checks **several fields at once** and, when it fails, localizes the error:
if `FJ + FK ≠ FL` but `FL` matches the prior year's `FL`, the problem is in `FJ` or `FK`.

Cost: zero. Valuable side effect: where the equation holds and exactly **one** term is
missing, that term can be **derived instead of read** — that's how the negative sign of
`GV` was resolved in [[idea-02-digit-reassembly]].

### V3 — N-1 cross-check between documents (the strongest one)

This is the challenge's hidden gem. The brief:

> *"Three filings per company is also deliberate: each restates the previous exercise in
> its own N-1 column, so in most cases you can check a figure against the year before
> without us telling you the answers."*

Every liasse has two columns: **Exercice N** and **Exercice N-1**. So:

```
value(doc_2023, field, column=N−1)  ==  value(doc_2022, field, column=N)
```

This is a **partial answer key the company didn't realize it handed over** — or, more
likely, that it handed over on purpose to see who notices. It's not self-consistency
within one document: it's **agreement between two independent documents**, filed in
different years, possibly typed by different accountants, scanned under different
conditions.

A number that survives V3 is almost certainly correct. A number that fails V3 is almost
certainly wrong — in one of the two documents.

Scope implication: taking advantage of V3 requires extracting **the N-1 column too**,
which isn't asked for in the deliverable. It's extra work that doesn't show up in
`results.json`, and that produces the metric the `README.md` needs. It's worth doing, and
worth stating as a deliberate choice.

### V4 (optional) — cross-plausibility against an external source

The brief allows it: *"Use any source you like."* The `chiffre d'affaires` of a French
SAS is often available on `data.inpi.fr` or in public aggregators. Order-of-magnitude
agreement is a fourth independent signal. Low priority — it costs network time and the
benefit over V3 is marginal.

## The state machine

```
                 deterministic extraction
                          │
                     ┌────▼────┐
                     │ V1 V2 V3│
                     └────┬────┘
          passes ─────────┴───────── fails or field missing
             │                              │
             ▼                              ▼
    confidence = 0.95                escalate to VLM
    tier = "deterministic"           (just the page, just the field)
    cost = €0.00                            │
                                       ┌────▼────┐
                                       │ V1 V2 V3│   ← re-verify!
                                       └────┬────┘
                              ┌─────────────┴──────────┐
                            passes                   fails
                              │                        │
                              ▼                        ▼
                    confidence = 0.80          OMIT the field
                    tier = "vlm"               and record it in the README
                    cost = measured            confidence = null
```

The rightmost branch is what the brief rewards: *"A pipeline that does 6 fields well and
says so beats one that reports all 12 with three of them silently wrong."* Omitting is a
legitimate outcome, and `financial_fields.json` agrees: *"If a field is genuinely absent,
omit it rather than reporting 0."*

## What this produces

**An accuracy metric with no answer key.** "94% of extracted values pass at least one
independent verifier; 71% pass V3, which compares against another document." That's
defensible in a way "I think it looks right" isn't.

**A derived cost number.** The total spent on the VLM is the sum of the token costs of
the calls the router actually fired. Divided by pages, that's `cost_eur_per_page`. Not an
estimate — it's accounting.

**An honest `confidence` in `results.json`.** The schema has the field. Most submissions
will likely fill it with the OCR's `score` (confidence over the pixels) or a made-up
number. Deriving it from "how many independent verifiers approved" is a defensible
semantics, worth explaining in the README.

**An experimentation framework.** Every other idea becomes testable: turning off
[[idea-03-row-banding-with-skew]] and measuring the drop in pass rate on `820561470` is
how the value of the skew correction gets proven.

## The honesty this requires

A verifier can approve a wrong value. If digit reassembly fails the same way in two
consecutive years' documents, V3 approves it. This needs to be written into the README:
**the verifiers measure consistency, not truth.** Agreement between independent sources
is a good approximation of truth, and the best one available without an answer key — but
it isn't the same thing, and saying so is part of the answer.

## Links

- [[cost-per-page]] · [[the-bilan-challenge]] · [[liasse-codes]]
- [[idea-01-code-anchoring]] · [[idea-02-digit-reassembly]] · [[idea-03-row-banding-with-skew]]
