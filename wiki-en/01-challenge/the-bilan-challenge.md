---
type: challenge
tags: [brief, scope]
status: draft
updated: 2026-09-14
---

# The bilan challenge — what was asked

Source: `challenges/bilan/BRIEF.md` and the root `README.md`. This page is the operational
summary; the original brief governs.

## The ask, in one sentence

> *"Build a pipeline that extracts 12 financial fields from the filings in `data/`, and
> report each value with the place in the document you read it from. Then tell us what it
> cost — in euros per page, in seconds per page, and in accuracy — and defend the trade-off
> you chose."*

## Deliverables

| artifact       | where                    | content                                                        |
| -------------- | ------------------------ | --------------------------------------------------------------- |
| `results.json` | **repository root**      | per `challenges/bilan/schema/results.schema.json`               |
| `README.md`    | root                     | how to run it, the trade-off, **how I used AI**, what was cut  |
| `.env.example` | root                     | environment variable **names**, **no values**                  |
| the code       | anywhere                 |                                                                   |

Submission: a PR on the repository itself, with `@YassineBouderbala` and `@AleBastos25` as
reviewers.

## Constraints

- **6 to 8 hours** of work, within 7 days.
- **The scope is bigger than the time. On purpose.** The brief: *"What you choose to do
  first, what you decide to leave, and how clearly you say which is which, is a large part
  of what we read."*
- Documents in French, with no expectation that the candidate knows French.
- Any external source is allowed, including opening an account at data.inpi.fr.
- AI use is allowed and **encouraged**, with a mandatory declaration.
- **Never commit `.env` or a real key.**

## Evaluation criteria, verbatim

> *"whether the numbers are right where we can check them; whether the boxes point at the
> right place on the page; whether your cost claim is **derived or guessed**; whether your
> README tells us what is broken."*

And the sentence that should govern every scoping decision:

> **"A pipeline that does 6 fields well and says so beats one that reports all 12 with
> three of them silently wrong."**

## The corpus in scope

15 documents, 5 companies, 3 filings each. See [[corpus-and-scope]].

The brief says the 5 were chosen to be different from one another:

| siren       | difficulty as stated by the brief                    | what I measured                                                                         |
| ----------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| `820561470` | crooked scan, average skew 0.7°, rotated pages         | confirmed: skew of −0.9 to −1.0 on most pages; **and it's plaquette, not liasse**       |
| `328024377` | reports in thousands of euros                          | **not confirmed** — see [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]]    |
| `401009741` | dense grid, ~12 tables per page                        | clean liasse, the easiest document in the set                                            |
| `445070311` | sparser, ~6 tables per page, thinner text              | **plaquette in all 3 documents**                                                         |
| `504304205` | the most verbose, ~100 lines of text per page          | **full** liasse, the only one with 2058-C (where `META_AVG_WORKFORCE` lives)             |

Two of the five brief descriptions don't match what the corpus shows. That's not an
accusation — it's exactly the kind of discrepancy the brief itself says it wants reported:
*"Cross-checking one source against another sometimes helps, and sometimes tells you the
sources disagree — which is itself a finding worth reporting."*

## The three hints the brief gives that are easy to miss

1. **Balance sheet identity** — `BS_TOTAL_ASSETS` has to reconcile with the other side.
   *"That is a check you can run yourself."*
2. **The N−1 column** — *"each restates the previous exercise in its own N-1 column, so in
   most cases you can check a figure against the year before without us telling you the
   answers."* It's a partial answer key. See [[idea-05-verifier-as-router]].
3. **Two fields are deliberately hard** — COGS isn't printed and has to be assembled
   ([[cogs-a-la-francaise]]); `META_AVG_WORKFORCE` isn't monetary.

## Links

- [[the-12-fields]] · [[corpus-and-scope]] · [[cost-per-page]] · [[00-overview]]
