---
type: decision
id: ADR-001
tags: [strategy]
status: draft
updated: 2026-09-14
---

# ADR-001 — choosing the Bilan track over Actes

**Date:** 2026-09-13 · **Status:** accepted

## Context

The Data/ML Engineer track offers two mutually exclusive challenges:

- **Bilan** — extract 12 financial fields from 15 annual filings, with provenance, and
  defend the cost per page.
- **Actes** — reconstruct ARCHEAN TECHNOLOGIES' capital structure across 20 years, from 17
  scanned French legal deeds.

Background: strong experience in **embedded systems**, close to zero experience in
Data/ML, no French. The goal is to deliver the best possible work and learn along the way.

## Decision

**Bilan.**

## Reasons

1. **The liasse is a fixed-layout record format.** DGFiP forms defined by law, with
   standardized line codes ([[liasse-codes]]). The real work is geometry-tolerant parsing,
   coordinate correction, and invariant validation — skills that transfer directly from
   embedded systems. The Actes track is mostly French legal comprehension.

2. **There is internal verification, and therefore a metric.** Balance-sheet identity,
   form arithmetic, and the N−1 column give three independent verifiers
   ([[idea-05-verifier-as-router]]). With no answer key, that's the only way to make a
   claim about accuracy. The Actes track openly admits that even the company itself has no
   settled answer: *"our own cross-checks flag contradictions in this company's capital
   chain that no one has adjudicated yet."*

3. **The cost question is first-class and has a clean answer.** A deterministic pipeline
   costs €0.00/page; a VLM costs per token. An architecture where the verifier decides when
   to escalate produces a cost×accuracy **curve** instead of a single point
   ([[cost-per-page]]).

4. **The surface area is larger, and partial delivery is explicitly accepted.** 15
   documents × 12 fields = 180 values leave room to demonstrate robustness and to cut scope
   honestly. The brief itself says this is what it rewards: *"A pipeline that does 6 fields
   well and says so beats one that reports all 12 with three of them silently wrong."*

## Consequences

- This means learning French accounting instead of French corporate law. Upfront cost
  concentrated in [[french-accounting-101]] and [[liasse-codes]].
- The Actes track's corporate-group bonus is out of scope.
- The deliverable is objectively checkable end to end — which cuts both ways: mistakes are
  just as visible as correct answers. Hence the priority given to
  [[idea-05-verifier-as-router]] over field coverage.

## Unanticipated consequence, discovered later

The premise "the liasse is a fixed format" holds for **8 of the 15 documents**, not all 15
([[F001-half-the-corpus-is-not-liasse]]). The decision stands — the core argument still
holds for most of the corpus, and the existence of two formats is itself a finding that
strengthens the deliverable. But scope needs to reflect this, and the README needs to say
so.

## Links

- [[the-bilan-challenge]] · [[00-overview]]
