---
type: finding
id: F006
tags: [corpus, meta, scope-savings]
status: draft
updated: 2026-09-15
---

# F006 — `meta/*.json` already hands over the closing date

**Impact: medium. Removes an entire extraction step.**

## Claim

The `fiscal_year_end` field required by `results.schema.json` **doesn't need to be read
from the PDF**. It's in the registry's metadata JSON, under `dateCloture`.

## Evidence

`data/401009741/bilans/meta/bilan_2023-11-20_65784e5da67d84faf4042736.json`:

```json
{
  "siren": "401009741",
  "denomination": "CREAMANDE",
  "dateDepot": "2023-11-20",     ← the date in the filename
  "dateCloture": "2023-04-30",   ← the fiscal_year_end the schema asks for
  "typeBilan": "C",
  "id": "65784e5da67d84faf4042736",
  "confidentiality": "Public"
}
```

Present and populated in all 15 in-scope documents. Full table in
[[corpus-and-scope]].

## Consequences

1. `fiscal_year_end` comes for free. One less step in the time budget.
2. `denomination` gives the company name — resolves the open question of identifying
   `504304205`.
3. **`dateCloture` is the key to verifier V3.** The N−1 cross-check needs to know which two
   documents cover consecutive fiscal years, and it's the clôture that defines that, not
   the filing date. See [[F007-the-n-1-chain-has-holes]].
4. The value should be treated as **the registry's assertion**, not absolute truth: if the
   form page says `Exercice N clos le 30/04/2023` and the meta says something else, that's
   a contradiction between sources worth noting. One more cheap verifier.

## Negative finding: `typeBilan` doesn't distinguish format

`typeBilan = "C"` (*complet*, normal regime) across all **15** documents — including the 7
that are plaquette. So it **doesn't work as a routing signal** for
[[plaquette-vs-liasse]]. Tested and discarded, which is information in itself: the
presentation format is the accounting firm's choice and the registry doesn't record it.

## Links

- [[corpus-and-scope]] · [[F007-the-n-1-chain-has-holes]] · [[idea-04-page-routing]]
