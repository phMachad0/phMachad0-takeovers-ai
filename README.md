# Bilan - 12 financial fields from 15 French annual filings

**Track:** Data / ML Engineer · **Challenge:** [Bilan](challenges/bilan/BRIEF.md) · **Author:** Pedro Machado

This is my submission for the Bilan challenge. `results.json` is at the repository root.
Everything below is my README; the original challenge brief is preserved at the bottom of
this file and unchanged.

## How to run it

```bash
pip install -e ".[dev]"
make run      # route -> extract -> verify -> emit  (writes results.json)
make test     # 450 tests, no corpus needed except a subset marked `corpus`
```

No API key is required for any of this. `make run` is fully deterministic: it reads the
OCR shipped in `data/`, anchors on the liasse's own line codes or, where a filing carries
no line codes, on the printed French labels, and writes `results.json` plus a set of
reports under `reports/`. Individual stages are also exposed (`liasse route`, `liasse
extract`, `liasse verify`, `liasse emit`, `liasse cost`), each writing its own report, so
the pipeline can be inspected stage by stage instead of only as a black box.

An optional escalation stage (`liasse escalate`) can re-read, with a vision model, the
fields the deterministic path could not settle. It needs `ANTHROPIC_API_KEY` (see
`.env.example`) and **I never ran it against the real API** - no credential exists in
this environment. Without a key it prints why it can't run and changes nothing. More on
this below.

## The trade-off

**What I chose.** A fully deterministic, OCR-only pipeline as the primary path, with a
credentialed vision-model escalation built but never exercised. I made this choice before
I knew what the corpus actually looked like, and it survived contact with the corpus for
a reason I did not anticipate: **7 of the 15 filings carry no liasse line codes at all.**
They are *plaquettes*, the accountant's own presentation of the same accounts, produced
by whatever software the firm used, with none of the two-letter codes the tax form prints.
I only found this by asking the AI to measure the corpus page by page before writing
any extraction logic, rather than build against the one clean example first (see "How I
used AI" below - this is also where the tool first led me wrong).

That finding is the reason there are two extractors in this pipeline, not one: a
code-anchored reader for the 8 filings that are liasses, and a second, label-anchored
reader for the 7 that are plaquettes, which recovers the column grid of a table that
carries no codes at all from the geometry of the figures printed on it - a column is a
position enough rows agree on, measured directly rather than assumed from a header row
that the OCR mangles as often as not. Three filings in the corpus happen to carry *both*
formats for the same exercise, which let me cross-check the two extractors against each
other on real data instead of only against themselves. I asked for that check
specifically once I saw the overlap existed, and it is the strongest evidence in the
whole verification suite that either reader is reading correctly, because the two share
no anchoring logic at all.

**Coverage.** 122 of 180 possible values (68%), from 14 of 15 filings - the deterministic
path reads every filing except one whose OCR hands back its tables in a scrambled reading
order that no column grid could be recovered from. Of the 58 unfilled cells, 14 are legally
absent (two filings elected the L.232-25 confidentiality option and the income statement is
withheld by law, not missing by failure - the registry's own metadata says so) and 44 are
genuine gaps I could not resolve deterministically.

**Cost.** Zero credentialed API calls, so the cost measured for the deterministic run is
**€0.00 per page** and **0.006 s per page** over all 415 pages in scope - that number comes
from `sum() over an empty list of API calls`, not a literal zero I typed, and the code has a
test that would fail if a call were ever recorded and the number did not move. What a vision
model *would* cost is derived, never measured (`reports/cost.json`), from the real page
sizes in the corpus, published token-per-pixel rules, and one stated assumption (characters
per token, whose influence on the total is quantified at ~3% rather than argued about).
Sending every page to a model would cost **€0.0025/page of the corpus** (Sonnet); sending
only the 61 pages the router already knows carry a field costs **6.8× less**, for the exact
same answer - the 355 discarded pages were measured to carry none of the twelve fields.

**Accuracy.** I have no answer key, so "accuracy" here means agreement between statements
the documents make more than once - not ground truth. Eight independent checks run over
the extracted values (an arithmetic identity that must hold on every liasse, one that must
hold on every plaquette, three that compare a total against its own terms, one that
compares a filing against its own restatement a year later, and the cross-format check
described above). 34% of the 122 emitted values are confirmed by at least one such check;
the rest simply had no independent statement of the same fact anywhere in the 15-document
scope to compare against, which is a property of the corpus, not a claim that they are
wrong. Two values are outright contradicted between the liasse and plaquette readings of
the same exercise, by €3 and €3,045 respectively, and both are reported as contradicted
rather than silently averaged or dropped - I'd rather ship a value flagged as disputed
than a confident-looking one that happens to be wrong.

**What I'd do differently with a week.** Actually run the escalation path against the real
API on the 44 deterministic gaps and the one unreadable filing, and replace the derived
cost curve with a measured one from that run - right now the escalation code is built,
tested end-to-end against a stub, and has never made a real call. I'd also widen the check
set: `PL_COGS_FRGAAP` (a field the schema itself defines as a sum of line items that isn't
printed anywhere as a single number) currently has no independent check covering it at all,
so an escalated value for it would be discarded by the acceptance rule I built for exactly
that reason - a model's answer is only kept if some other figure in the document, read
independently, agrees with it. And I'd go back to the two real cross-format
contradictions and find out by hand, rather than by argument, whether the €3,045 gap is a
genuine difference in what each dialect includes in depreciation or a bug I haven't
found yet.

## How I used AI

I don't have a finance or ML-engineering background, and my French is advanced but not
professional-level for tax-form vocabulary, so I started by having Claude Code build a
study wiki in Obsidian (`wiki/`) covering French GAAP concepts, the liasse fiscale, and
OCR/geometry basics, before either of us wrote extraction code. That wiki stayed the
working memory for the whole project and every factual claim about the corpus in it carries
the file, page, and OCR text it came from, and I read it as we went rather than at the
end.

What I directed rather than delegated: I asked for the corpus to be measured ( page counts,
form types, OCR coverage) across all 15 documents before any extraction logic was written,
specifically because the first pass had jumped to a strategy off one example. That
measurement is what surfaced the liasse/plaquette split, and once it did, filtering pages
by what they actually are (a table with codes, a table without, prose) rather than
extracting everything indiscriminately was the design decision I pushed for - it's the
reason 355 of 415 pages never reach an extractor at all, and it's also the reason the cost
argument in this README has a number behind it instead of a guess. I asked, separately, for
every extracted value to be checked against something else the documents say rather than
trusted on its own and that's the check suite described above, and the cross-format
comparison in particular was my call once I noticed three filings carried both formats for
the same year.

What I checked myself: I read the wiki's findings pages against the source OCR and PDFs
directly - my French was enough to confirm the label matching (e.g. "Chiffres d'affaires
nets" vs. the abbreviated "Ventes de marchandises + Production vendue" one accounting
software dialect prints instead) was reading the right rows, not just plausible ones. I
used `tools/bbox_viewer.py` to render sampled boxes back onto the actual pages and eyeballed
them against the printed figures rather than trusting the pipeline's own reported
confidence. And I went through the five schema ambiguities in `financial_fields.json` by
hand against the ADR that documents each decision, because that's a judgment call no
measurement resolves for you.

Where the tool led me wrong: the very first recommendation was that code-anchoring the
liasse line codes would cover the corpus, based on one page of one company. It does not -
measuring across all 15 documents showed 7 of them have no line codes at all. The
architecture held up (two extractors behind a router, rather than one universal one), but
the claimed coverage was off by roughly a factor of two until I insisted on measuring
before building further. That correction is logged in the wiki's session notes, not
edited out after the fact.

## What I cut, and why

- **The escalation path was never run against a real API.** It's built, has a hard
  page cap, refuses any answer that isn't well-formed JSON in the exact shape asked for,
  and only accepts a re-read value if an independent check confirms it - but every test
  of it runs against a stub transport, never `anthropic`. I'd rather ship a derived cost
  curve labelled as derived than a real one I didn't have time to validate carefully.
- **One filing (`6860f28ca0138eae340c7453`) is unread.** Its OCR returns table rows in a
  scrambled order that no column-grid recovery could untangle; it's reported with
  `not_processed` naming the reason rather than silently producing zero values, and it's
  the first candidate for the escalation path above.
- **`PL_COGS_FRGAAP` has no independent check.** It's defined by the schema itself as a
  sum of several line items with no single printed total anywhere in the form to compare
  it against, on either format. I flagged this rather than build a check that would just
  be checking the sum against itself.
- **I did not pull external sources** (INPI, the gazette) for this track - the brief
  explicitly allows it, but everything the 12 fields need is on the pages given, and I
  spent the time budget on the routing/verification architecture instead.

## Where I disagree with the brief, with evidence

- The brief's rule of thumb is that units are stated "in small print, once" per document.
  Measured across the corpus, the kEUR marker that appears on `328024377`'s filings scopes
  the *annexe* (the notes), not the balance sheet or income statement themselves - applying
  it document-wide would misstate the primary statements by a factor of 1000.
- Five of the twelve field definitions in `financial_fields.json` have a `label_fr` and a
  `notes` that specify different formulas. I picked a reading for each, wrote down why, and
  emit the alternative reading alongside the chosen one under `schema_ambiguity` in

---