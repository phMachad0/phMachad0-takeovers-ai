---
type: meta
tags: [log]
status: draft
updated: 2026-09-14
---

# Log

Append-only, chronological. Entries start with `## [YYYY-MM-DD] type | title`, so
`grep "^## \[" log.md | tail -5` still works.

## [2026-09-13] ingest | Takeovers briefs and schemas

Read: `README.md`, `NOTICE.md`, `challenges/bilan/BRIEF.md`, `challenges/actes/BRIEF.md`,
both `results.schema.json` files, `financial_fields.json`, `event_codes.json`,
`tools/bbox_viewer.py`.

Initial corpus reconnaissance: 20 companies in `data/`, 15 documents in scope for the
bilan challenge, 415 pages. OCR coverage confirmed complete within scope.

Result: [[ADR-001-track-choice]] — **Bilan track**.

## [2026-09-13] query | Which track to choose?

Compared the two challenges against my own background (embedded systems, no Data/ML
experience, no French). Recommendation: Bilan, for three reasons — the liasse is a
fixed-layout format, internal verification is available without an answer key, and the
cost question has an elegant architectural answer.

Filed as [[ADR-001-track-choice]].

## [2026-09-14] ingest | Measuring the in-scope corpus

Ad hoc scripts over the 15 documents: form header per page, count of 2-letter codes per
page, search for unit markers, dump of tokens with coordinates grouped by vertical band.

Five findings recorded:

- [[F001-half-the-corpus-is-not-liasse]] — **8 liasse, 7 plaquette.** Reshapes the
  architecture: two extractors are needed.
- [[F002-the-keur-belongs-to-the-annexe-not-the-balance-sheet]] — every `K€` marker in the
  corpus belongs to the annexe's subsidiaries table. Bernachon's balance sheet is in
  euros. Partially contradicts the brief's table.
- [[F003-the-ocr-breaks-numbers-apart]] — `FL = 1 805 459` arrives as `"1"`, `"805"`,
  `"459"`.
- [[F004-negatives-are-printed-in-parentheses]] — `GV` (financial result, one of the 12
  fields) arrives as `"2"`, `"096)"`. Sign flipped by a lost parenthesis.
- [[F005-the-ocr-loses-part-of-the-code-column]] — `FS` through `FX` missing on a clean
  liasse page, even though the labels and values were read.

Correction to an earlier claim: code anchoring doesn't cover "the corpus," it covers 53%
of it. Recorded in [[how-i-used-ai]].

## [2026-09-14] ingest | Wiki created

Initial structure: `CLAUDE.md` at the root as the schema; `wiki/` with 3 challenge pages,
11 concept pages, 7 idea pages, 5 finding pages, 1 ADR, 1 AI-usage page, plus `index.md`
and this log.

Proposed next step: resolve the open items in [[index]] — in particular, confirm the
codes in [[liasse-codes]] that are still unverified against the corpus, which is a
prerequisite for writing the extractor.

## [2026-09-15] query | Glossary: the PL abbreviation collision

`PL` in the schema means *Profit & Loss* (the compte de résultat), but in Portuguese "PL"
means shareholders' equity — which in the schema is `BS_TOTAL_EQUITY`, the other side of
the document. Five ambiguous uses found in the wiki, corrected: shareholders' equity is
now always spelled out or given as *capitaux propres*. A table of schema abbreviations was
added to [[french-glossary]].

## [2026-09-15] ingest | The `meta/*.json` files

Open item resolved. Two findings:

- [[F006-the-meta-json-hands-over-the-closing-date]] — `dateCloture` hands over the
  `fiscal_year_end` for free, and `denomination` identifies the companies. Negative
  finding: `typeBilan = "C"` across all 15 documents, plaquettes included, so it
  **cannot** be used as a routing signal.
- [[F007-the-n-1-chain-has-holes]] — mapping the clôtures, only **7 of 10** consecutive
  pairs exist, and only **3** link two liasses. Limits the V3 verifier and becomes the
  main argument for building a plaquette extractor.

## [2026-09-15] query | Architecture plan and roadmap

Worked out the full execution plan, written up across six new pages in `06-plan/`.

Structural decisions: layers with a one-directional dependency (testable by an
architecture test), a typed, serializable contract between stages stored as an artifact
in `artifacts/`, money never represented as `float`, and four explicit extension points
(a declarative field catalog, an extractor Protocol, a decorator-registered verifier
list, and an anchor ladder).

Testing strategy organized around **six oracles**, the strongest being Takeovers' own
`tools/bbox_viewer.py`, used as a differential reference for the coordinate conversion.

Roadmap in two tracks: **mandatory Track A** (E0–E9, ~6.5 h) delivers 12 fields × 8
liasse documents with measured accuracy; **optional Track B** (E10–E12) prioritizes the
plaquette extractor over the VLM, because coverage is worth more than a cost narrative.
0.8 h reserved and non-negotiable for the README. Clock rule: at hour 6, stop building
and start writing.

Environment checked: `pymupdf` missing (blocks the geometry work), `pytest`,
`jsonschema`, `numpy`, and `pillow` present. No `uv`/`poetry`; `make` available.

Proposed next step: E1.5 — confirm the 11 outstanding codes against the corpus, which is
what blocks the extractor.

## [2026-09-15] ingest | E1.5 — confirming the codes against the corpus

Scanned the liasse pages of the 8 documents with a banding prototype (deskew + banding by
row + code↔label↔value matching). **All 11 outstanding codes confirmed**; the
[[liasse-codes]] table no longer has any unverified rows among the codes used by the 12
fields. The E5 blocker is lifted.

Four new findings, three of them changing project decisions:

- [[F008-degenerate-boxes-and-top-edge-banding]] — the prototype got it wrong, matching
  `BZ` to the wrong row. Cause: the OCR returned a 367 px-tall polygon for that token.
  Banding must align by **top edge**, not center. 3.47% of the in-scope tokens are
  degenerate, and 5 of them are liasse codes.
- [[F009-measured-code-loss]] — code coverage on the 2052 ranges from **55% to 92%**; the
  `FS`–`FX` block missing on half the pages; on one document even `FL` itself is missing.
  The ordinal fallback step becomes mandatory.
- [[F010-actual-field-coverage]] — `504304205/66cd893c` also has no 2052/2053, so **two**
  documents have no income statement. And `META_AVG_WORKFORCE` exists in **8 of 15**
  documents, in three different places, with a semantic divergence in `445070311`
  (*"à la clôture"* ≠ *"moyen sur l'exercice"*).
- [[F011-v1-confirmed-and-the-column-structure]] — **V1 closes 3 of 3** tested documents.
  And it revealed that the 2050 has three columns (Brut · Amort · **Net**) and the field
  requested is the Net one: column selection needs to be explicit in the catalog,
  `Anchor(code, form, column)`.

Collision recorded: `BZ` means `Autres créances` on the 2050 and `Production stockée` on
the 2052. Catalog indexed by **(form, code, column)**, never by code alone.

Next: close the 5 schema ambiguities as ADR-002 (Pedro approved the proposals).

## [2026-09-15] decision | ADR-002 — the 5 schema ambiguities

Closed the five contradictions between `label_fr` and `notes` in `financial_fields.json`,
with the three adjustments that E1.5 made necessary. See
[[ADR-002-schema-ambiguities]].

Summary: COGS sums `BZ` following `label_fr` (but `BZ` on the 2052 only exists in 1 of 8
docs) · D&A = `GA+GB` · Capital = `DA` alone, because it's the only one with a second
source in the document · Cash = `CG+CE` · Workforce = a three-source ladder with
decreasing `confidence` and a `semantic_note` where the source diverges from the concept
requested. All with the alternative reading emitted in an extra field.

**Correction found while verifying decision 4:** every 2050 row has **two codes**, one
per column. `CO` is the **gross** asset figure, not the total assets figure; `CD`/`CF` are
Gross and `CE`/`CG` are Net. The Net cell of the TOTAL GÉNÉRAL row has no code read in the
corpus — so `CO` serves as the row anchor and the column is chosen by position. Fixed
[[liasse-codes]] and [[F011-v1-confirmed-and-the-column-structure]], which ambiguously
stated that `CO` was the field.

Risk raised in discussion and **dismissed by verification**: `CD` read in only 3 of 8
docs does not create a silent inconsistency in `BS_CASH`, because wherever `CD` is
missing the VMP row is genuinely empty (the `CE` code is there, with no value). The gap
is in the value, not in the reading.

With that, both E5 blockers are lifted. Next: E0, the scaffold.

## [2026-09-15] implementation | E0 — scaffold

Project stood up: `pyproject.toml`, the `src/liasse/` package with the ten layers,
`Makefile`, `.env.example`, `liasse doctor`. **23 tests green**, `ruff` clean. See
[[E0-scaffold]].

The piece worth more than the scaffold itself is the **architecture test**: `layers.py`
holds the layer map as data, and `tests/architecture/` parses the imports with `ast`,
failing if a module imports from an equal or higher layer. Verified it fails when it
should — injected `geometry → verify` and a subpackage with no declaration, and both were
caught.

Convention recorded in `CLAUDE.md`: **code always in English**, wiki and conversation in
Portuguese; and one page in `wiki/07-implementacao/` per completed stage.

Removed a stray 0-byte file called `*.json.tmp` at the root — an unexpanded glob from a
command of mine on 09/14, not tracked by git.

Next: E1 — corpus and geometry, whose exit criterion is the differential test against
`tools/bbox_viewer.py`.

## [2026-09-15] implementation | E1 — corpus and geometry

Layer 0 (`corpus/`: models, scope, loader) and layer 1 (`geometry/`: boxes, coords)
stood up. **99 tests green**, 4 skipped, `ruff` clean. See
[[E1-corpus-and-geometry]].

Exit criterion met: the **differential test against `tools/bbox_viewer.py`** matches
token-for-token across **2,729 tokens** from 45 pages, covering all 15 documents.
`bbox_viewer` is loaded as a module, never copied — a copy would drift and the test would
end up comparing us against our own belief.

Three injected mutants, all caught: assuming A4, flipping the 300/72 factor, transposing
x and y.

New finding, [[F012-blank-pages-and-page-sizes]], which came out of the test itself
without being searched for:

- **41 of 415 pages (9.9%) have no OCR line at all**, concentrated in two documents of
  `445070311`, almost all even-numbered — the backs of a double-sided scan.
- **Only 21% of pages are exactly A4.** There are 88 distinct sizes across 415 pages,
  with a maximum deviation of 1.87%. On a 3508 px page that's 66 px — almost two lines of
  text. Assuming A4 produces a box that validates, points to the right page, and to the
  wrong line.

The second finding showed up while injecting the "assume A4" mutant to prove the test
caught errors: it did, and the extent of the failure showed the assumption breaks on 79%
of the corpus.

Two fixes in my own code: a `ruff` false positive (SIM300 on `pytest.approx`) and a test
of mine that was tautological, comparing a function against itself.

Next: E2 — page routing.

## [2026-09-15] lint | Correction: the false BZ and the collision that never existed

Pedro questioned the plausibility of the OCR reading `FM` as `BZ`. He was right — it's not
character confusion at all. Investigated, became
[[F013-the-ocr-reads-the-code-column-as-vertical-text]].

The `BZ` token on page 006 of `65784e5d…` has `score` 0.37, `orientation_angle` 1, and
**367 px of height**. Rendering the region, what's inside is the **entire code column** —
`FM FN FO FP FQ FR` — detected as a single line of vertical text.

Fixes applied:

- [[liasse-codes]]: the `BZ` row on the 2052 becomes **`FM`** (3/8 documents, not 1/8);
  the collision section was rewritten — the real, confirmed collision is **`CO`**
  (2050 × 2054), not `BZ`. Added the **sanity filter** section with the three signals.
- [[ADR-002-schema-ambiguities]]: decision 1 becomes `COGS = FS+FT+FU+FV+FM(2052)`, with
  the correction recorded rather than silently rewritten.
- [[F008-degenerate-boxes-and-top-edge-banding]] and [[F009-measured-code-loss]]: root
  cause noted. Part of the "code loss" isn't loss, it's absorption by vertical-text
  detection.
- Code: `Token` now carries `orientation_angle`, which the loader used to discard. New
  test locks in the separation (false `BZ`: angle=1, score 0.37; real `FL`: angle=0,
  score 0.999). **100 tests green.**

Method note for the README: the error survived a full-corpus scan, made it into a concept
page and an ADR, and fell apart the **first time a page was actually rendered and looked
at**. That's the argument for oracle O6 in [[testing-strategy]].

## [2026-09-15] implementation | E2 — page routing

Layer 2 stood up. **158 tests green**, `ruff` clean. `liasse route` writes
`reports/routing.json`. See [[E2-page-routing]].

**60 of 415 pages load fields — a 6.92× reduction.** The router agrees with the 15
formats measured by hand in E1.5 (8 liasse, 7 plaquette), which is the partial answer key
produced before the code even existed.

Finding from this stage: [[F014-the-registry-announces-the-confidential-income-statement]].
The `confidentiality` field in `meta/` reads `"Partiellement confidentiel"` in exactly the
5 documents with no compte de résultat — a 5-of-5 correlation. It's the *déclaration de
confidentialité* under art. L. 232-25. The 6 `PL_*` fields for those documents are
**legally absent**, not extraction failures. The honest coverage denominator drops from
180 to 150 fields.

Second finding: **three documents carry both the liasse AND the plaquette for the same
fiscal year in the same PDF** (`328024377` ×2, `504304205/66cd893c`). Cross-validation
between the two extractors without depending on the N−1 chain — stronger than
[[F007-the-n-1-chain-has-holes]] assumed.

Three fixes forced by measurement: a numeric-density guard (section dividers were being
read as statements); the label fallback demoted to a **document-level** strategy, not a
page-level one, because it was firing on annexe tables; and two OCR-corrupted titles
(`Passit`, `Résuitat`), each resolved with a wildcard.

Mutants: density switched off and fallback always on were both caught. The third — the
code sanity filter switched off — **failed nothing**, exposing a real gap. Wrote
`tests/unit/test_text_codes.py` with one test per signal plus one on the actual `BZ`-false
page; the mutant then failed 3 tests.

## [2026-09-16] lint | Title matching: from a sample-tuned wildcard to measured fuzzy matching

Pedro questioned the fix for the two corrupted titles (`passi.` and `resu.?tat`), pointing
out it looked hardcoded. He was right, and the brief warns about exactly this. Investigated
and reimplemented — see [[ADR-003-title-matching]].

Three things the measurement showed, two of them against my expectation:

1. **Whole-string similarity is the wrong metric.** The worst true positive was the token
   `PASSIF` alone, at ratio 0.667 — whole-string ratio punishes fragments, and the OCR
   breaks lines wherever it wants.
2. **The high-ratio false positives weren't from title matching at all.** `COMPTE DE
   RESULTAT` at 1.000 are the section dividers (rejected by the density guard), and
   `BILAN - ACTIF` at 0.917 are liasses (decided by the header). It was the guards doing
   the discriminating.
3. **The vocabulary separation is 3 edits** (`actif` ↔ `passif`), which makes a tolerance
   of 1 a **derived bound**, not a tuned parameter.

Solution: word-level matching, tolerance 1, **anchored at the start**. The third rule
carries the most weight — `Notes sur le compte de résultat` contains every word of
`Compte de Résultat`, and requiring presence flagged 19 extra annexe pages. A title
doesn't *contain* its words, it *starts with* them.

Count unchanged: **60 of 415 pages.** The change bought generality, not coverage — seven
corruptions absent from this corpus are now handled too.

Fix in [[idea-01-code-anchoring]]: my original objection to fuzzy matching was generalized
beyond its scope. It holds for discriminating 50 long labels in a table, not for
classifying a page among 4 distinct titles.

**200 tests green.** Mutants: tolerance 2 breaks the separation test; presence-based
matching breaks 5 tests.

## [2026-09-16] implementation | E3 — row reconstruction

Tokens grouped into table rows. **231 tests green**, `ruff` clean. See
[[E3-row-reconstruction]].

**This stage knocked down the idea that motivated it.** [[idea-03-row-banding-with-skew]]
said to rotate coordinates by the OCR's `skew_angle`. Implemented, it **broke rows that
were already correct**. Measuring the actual tilt of the coordinates — the median across
pairs of tokens sharing a printed line — pages reporting −1.0° carry **−0.17°**. The OCR
already straightens the image before detection; the field records how much was corrected,
not the residual. See [[F015-the-ocr-skew-is-not-the-residual]].

A/B: reported gave 3/5 correct pairs, zero gave 5/5, **measured gave 5/5**. Decision: keep
the mechanism, measure the angle from the coordinates themselves, and don't rotate absent
enough evidence.

Three design decisions: band by the **top edge** (F008), a **fixed band anchor** to avoid
chaining, and deskewing as a working space — the reported box always comes from the
original polygon, locked in by a test.

**The architecture test caught a mistake of mine**: `text/lines.py` was importing
`geometry`, and the two were in the same layer. I had anticipated this tension when
designing and forgot it. `geometry` moved down to layer 0.

And a case where the code was right and my test was wrong: I built a golden pair with
capital `10 000` for a document where the capital is `150 000` — there had been a capital
increase. The data contradicts an assumption more often than the code contradicts the
data.

## [2026-09-16] implementation | E4 — number parsing

Geometric number reassembly with syntactic validation and sign resolution. **262 tests
green**, `ruff` clean. See [[E4-number-parsing]].

Every case from [[F003-the-ocr-breaks-numbers-apart]] and
[[F004-negatives-are-printed-in-parentheses]] passes, including the `GV` whose opening
parenthesis the OCR dropped — a parser that strips punctuation would flip the sign of one
of the 12 fields.

**The decision a test forced:** the first design returned the rightmost valid number when
grouping failed, and for `1 | 476747` it returned **476747** — off by a million, silently.
The right distinction isn't *whether* the scan stopped, it's **why**: stopping because of
distance is confidence, stopping because of shape within the distance is ambiguity, and
returns `None`.

**Threshold calibration, measured:** gaps inside a single number run 1–12 px; between
columns, 173–195 px. They don't overlap. The 4.0-digit-width threshold sits in the middle
of a gap spanning more than an order of magnitude. The test locks in the property, not the
number.

**Two of my own measurements that fell apart:** "more values read is better" (a tight
threshold silently read fragments) and "the 55 readings are fragments" (the 55 were two
adjacent columns; the detector was the one at fault).

Explicitly left for E5: column selection (N vs N−1) and the ordinal fallback for missing
codes. And a **1 € discrepancy recorded within a single document**
(`FJ+FK = 5 564 580` against `FL = 5 564 581`), which forces E7 to have a justified
tolerance policy instead of an arbitrary one.

## [2026-09-16] implementation | E5 — liasse extractor

Declarative catalog, anchor ladder, and column selection. **278 tests green**.
`liasse extract` writes `reports/extraction.json`. See [[E5-liasse-extractor]].

```
75 fields read from 8 liasse documents; 14 legally absent, 7 unresolved
tiers: {'CODE': 63, 'LABEL': 12}
```

75 read + 14 legally absent + 7 missing from the source = 96. **Zero unexplained gaps.**

**V1 closes 7 of 7** verifiable documents, with no divergence — two different pages, two
different anchors, one number. First evidence of a check that doesn't depend on trusting
us.

**The ladder's order was flipped by measurement:** the plan was code → ordinal → label.
Measuring the 121 field×page pairs, the label rescues 27 of the 29 lost codes, and the
remaining 2 have the entire row missing from the OCR. The ordinal step is left
**unbuilt, and documented as such**.

Three new decisions: column selection handled three ways (the 2050's version was picking
the **gross** asset figure — a real bug caught by V1); **sibling codes** to locate a cell
when the target code went missing (recovered `PL_REVENUE` on one document); and **a blank
cell counts as zero**, distinct from a row that wasn't found — 0 incomplete sums, 24
legitimate zeros.

Two of my own earlier measurements corrected: `orientation_angle` does **not** flag junk
(12 of 18 cases are legitimate codes; the false `BZ` is caught by score and height), and
the E4 gap threshold was **too high**, from a biased sample — 4.0 merged 68 legitimate
column separations. Measured across every row: intra max 0.70, inter min 2.80. Corrected
to 1.5.

## [2026-09-16] implementation | E6 — units

EUR vs kEUR resolution with scope, form-level default, and a capital anchor. **298 tests
green**. See [[E6-units]].

All 8 liasse documents resolve to **EUR**, and on the two Bernachon documents the **8 and
6 kEUR markers are found, weighed, and rejected**, with the reason recorded in
`rejected_markers` — which is the field that separates not having seen the trap from
having judged it.

The capital anchor (`au capital de 300.000 Euros`, a French legal requirement) works on
12 of the 15 documents, across every separator style. Missing on the three `401009741`
documents because it's a SAS with variable capital and doesn't print a fixed figure — a
fact about the company, not a search failure.

**Refinement the measurement forced:** on `820561470/6543d3fd`, the cover page says
150 000 and the balance sheet says 10 000. Not an error — the cover page declares the
capital as of the **filing date**, the balance sheet as of **closing**. The anchor
corroborates **scale**, not equality. `compare_scales` separates the three cases and only
flags for human review when there are three orders of magnitude of difference; it never
converts automatically.

Deleted a phantom test I had written (`... if False else (None, None)`) — it asserted
nothing and still counted as coverage. The fix was to extract the decision into a pure
function and test it with seven cases, which also improved the design.

Mutants: a marker applying to the whole document, and a loose scale threshold — both
caught.

## [2026-09-16] implementation | E7 — verifiers

Six independent checks, derived confidence, and `reports/verification.json`. **322 tests
green**. See [[E7-verifiers]].

```
V0 5/5 · V1 8/8 · V2a 6/6 · V2b 6/6 · V2c 5/5 · V3 6/10
20 of 75 values agree with an independent check (27%); 0 contradicted
```

**27% is low, and it's the truth.** The verifiers reach total assets, revenue, and
financial result; they don't reach COGS, payroll, outside services, tax, or cash — the
forms don't declare those values twice. The report separates verified, contradicted, and
**unverified**, instead of inflating the number by counting checks that don't apply.

**V3 found a disagreement between documents:** `504304205` reports total assets of
1 807 858 for fiscal year 2016 and restates it as 1 807 435 in the following filing —
a 423 € difference. Each filing is internally consistent (2050 matches 2051 in both), and
`DI`, `HN`, and `GU` match exactly across the pair, so it isn't a reading error.

The rounding tolerance (`max(1, terms // 2)`) resolves the E4 open item: the 1 €
difference between `FJ+FK` and `FL` is rounding budget, not an error. It's never wide
enough to absorb a digit, and a test pins down both bounds.

**A bug of mine:** the first run reported a clean sheet with **zero checks run** —
`verify/checks.py` was never imported and the registry stayed empty. The guard test I had
written **didn't catch the bug**, because that test itself imports `checks`. The guard had
to become static, parsing `runner.py` instead.

Mutants: reverting to the Brut column (V1 drops to 0/8, 8 contradicted), a loose
tolerance (3 tests), an unimported registry (the static guard) — all three caught.

## [2026-09-16] implementation | E8 — emitting results.json

The deliverable exists and **validates against the schema Takeovers sent**. 75 values, 15
documents listed. **340 tests green.** See [[E8-emitting-results-json]].

The 7 unprocessed documents appear in the file with `not_processed` explaining why,
instead of simply vanishing — whoever reads it is told which ones were left out.

Each value carries, beyond the required fields: the anchor's `tier`, the `components` of
sums with their own box, the `rejected_markers` for kEUR, the checks it survived, and both
readings wherever the schema is ambiguous.

Added `liasse check-boxes`, oracle **O6**: samples values from the deliverable and draws
the boxes over the pages using Takeovers' own `bbox_viewer`. It's the only oracle no
automated check can replace. Checked by eye: `BS_TOTAL_ASSETS = 1 717 114` boxes the Net
column next to the depreciation figures, and `PL_FINANCIAL_RESULTS = −76 778` boxes
`76 778)` with the `(` visible on the left.

## [2026-09-16] implementation | E9 — cost measurement

**Phase 2 closed, Track A complete.** 370 tests green. See [[E9-cost-measurement]].

The brief doesn't ask how much it cost; it asks *"whether your cost claim is derived or
guessed."* "The cost is €0.00" and "the cost **came out to** €0.00" print the same
characters and are opposite claims. The code does the second: `ledger.eur() / pages`,
with the ledger being a sum over an **empty** list of API calls. It stops being zero the
instant a call is recorded — and there's a test that records one.

Proving a number isn't a constant means attacking its shape, not its value: the clock is
injectable, and the same code path is forced to report 2.0 / 0.5 / 0.125 s per page; plus
an `ast` guard over all of `src/` forbids the three required fields of the `run` block
from being numeric literals, and a test that `cli.py` doesn't assemble its own block.

**Measured:** 415 pages, 0.00403 s/page, €0.00/page, 0 API calls.

**Derived** (labeled as derived — no credential exists here, none was introduced), € per
page for the corpus at 200 dpi:

| scenario | pages | opus 5 | sonnet 5 | haiku 4.5 |
|---|---:|---:|---:|---:|
| deterministic | 0 | 0.000000 | 0.000000 | 0.000000 |
| plaquettes only | 29 | 0.001806 | 0.001084 | 0.000361 |
| routed pages | 60 | 0.003737 | 0.002242 | 0.000747 |
| everything | 415 | 0.025180 | 0.015108 | 0.005036 |

**6.92× more money for the same answer** between the last two rows. The router is the
only decision in the table that changes the bill by a factor, and it costs nothing.

Just one assumption — 4 characters per token — and the report measures its influence: the
answer accounts for 3.0% of the bill in the routed scenario, 0.45% in the full one. The
prompt and the response are counted in characters of real text (the challenge's
`financial_fields.json` and the `results.json` already emitted), not guessed.

**Finding outside the plan:** resolution saturates. 87 distinct page sizes across the
415, and all 415 hit the 4,784-token-per-image ceiling at 200 dpi; saturation sits at
192–193 dpi. Above that, rendering higher costs the same and shows the model less. The
`.env.example` comment claimed quadratic growth with dpi — true only below saturation,
and it was corrected. `LIASSE_VLM_DPI` is now actually read, as the default for
`liasse cost`.

**What's still missing on purpose:** the table has a euro column and no accuracy column.
Without the E10 plaquette extractor there's no coverage number for the plaquette row, and
inventing one is exactly what this stage was built not to do.

## [2026-09-16] implementation | E10 — plaquette extractor

**8 of 15 documents → 14 of 15. 75 values → 117. 3 companies → 5.** 396 tests green. See
[[E10-plaquette-extractor]].

Nothing downstream changed shape: units, verifiers, confidence, and emission all work on
`RawValue` and don't know which extractor produced the value. Three new modules, zero
changes across five others — the return on the investment in [[modular-architecture]],
now measured.

**The column grid comes from geometry, not from the header.** The header is an OCR line
that has to survive (`31/08/2021.` with an extra period, `du 01/07/19 / au 30/06/20 /
12 mois` across three lines); the column positions are attested by every filled row on
the page. That prevents the error the plaquette invites: reading a row left to right and
returning the third column's number as if it were the second's whenever a cell is empty.

**A mistake of mine, corrected.** I measured the valley of the distribution at 140 px, and
the results pages dropped from 6 columns to 3. The 81–124 px band isn't internal
scatter: it's the distance from a values column to the adjacent **percentage** column. The
real valley is at the other end — within a column, at most 52 px; between columns, at
least 81 px — and the right threshold is 65. A factor of two, and it only showed up
because the output visibly changed shape.

**Arithmetic alone doesn't identify the Net column.** `col0 − col1 = col2` also holds on
a liabilities page that prints N, N−1, and the variance, because the variance *is* the
difference. The router is what decides: the identity **confirms** a layout, it never
discovers one. And an assets page with 3+ columns that doesn't satisfy the identity
**isn't read** — a gap instead of plausible numbers read one column over.

**An empty cell in a plaquette is not a zero**, unlike the liasse: the plaquette prints
section headers whose words match the row below. A label only counts when the row prints
something in the column being read — and that's what makes it safe to accept a header as
a label, since one dialect prints the total shareholders' equity figure right on its own
header row.

**Three genuine OCR defects, found here:** a word split in half (`Dispon bilités`), a
minus sign glued to the digits (`-76778`, a convention the liasse never uses), and a stray
mark stuck to a number (`963 002 '`). All fixed with a test.

**A fix I tried and got wrong:** requiring the opening parenthesis to accept a `)` as
negative. Correct reasoning, wrong conclusion — the liasse genuinely *loses* the opening
parenthesis, the 2052 prints `(76 778)` and the OCR delivers `76 778)`, and the
arithmetic check confirms it's negative. The distinction has to come from evidence the
parser doesn't have: on the assets page, the `Brut − Amort = Net` identity.

**V4, the strongest check in the suite.** Three documents carry both formats for the same
fiscal year, read by two pipelines with no anchoring logic in common. **21 of 23 agree**,
almost all exactly or within 1 € — the two formats round independently. The two real
disagreements are reported at confidence 0.30: D&A differs by 3,045 € because the
plaquette condenses depreciation and provisions into one line while the liasse keeps them
separate (the two numbers measure different things), and outside services differs by 3 €
that rounding doesn't explain.

**V1b** gives the 7 plaquette-only documents the balance-sheet identity they didn't have:
closes 7 of 7.

**What wasn't done, and is stated as such:** the plaquette's N−1 column (so V3 doesn't run
on plaquette→plaquette pairs), `META_AVG_WORKFORCE` on plaquette, and `6860f28c`, whose
OCR returns the tables in shuffled order — the only one of the 15 documents still
unreadable, and which **says so** in `results.json` instead of showing up with an empty
list.

## [2026-09-16] implementation | E12 — workforce in prose

`META_AVG_WORKFORCE_FRGAAP` from 1 to **6 of 15** documents. 453 tests green. See
[[E12-workforce-in-prose]].

Only `504304205` has form 2058-C with the `YP` row, read unchanged by the E5 code
extractor. On the other four, the number is in a **sentence in the annexe**, not a table —
`Effectif moyen du personnel 43 personnes`, `L'effectif salarié moyen … s'élève à 33
personnes contre 38 personnes à la clôture de l'exercice précédent`. This isn't table
extraction with one column short; it's finding the right sentence inside a paragraph. A
new, short module, instead of forcing `columns.py` to do what it wasn't built to do.

**The trap:** the second sentence names two years in the same breath, and both numbers are
real. A "number closest to effectif" regex gets it right half the time. The fix is for
each dialect to be a closed pattern, anchored on a word that only appears once in the
sentence — `s'élève à` introduces only the current workforce figure, and the pattern stops
matching before it reaches the second number.

**Precedence preserved:** the prose pattern is only consulted when the form didn't resolve
the field, and it's explicitly tested that the form's own row (`… : YP 9 9`) doesn't match
the sentence pattern — that would count the same fact twice, one of the times without the
rigor of the code anchor.

Searched across **every page of the document**, not just the routed ones: the sentence
lives exactly on the pages that E2's router correctly discards for having no table grid.

## [2026-09-16] implementation | E11 — VLM escalation

The full path — client, question/answer contract, acceptance gate, cost — and **never
called against the real API**: no credential exists in this environment. 453 tests green,
all against a `StubTransport`. See [[E11-vlm-escalation]].

**The core rule:** a value from the model is only accepted if a check computed from other
figures, on other pages, agrees with it. Stronger than "re-verify and discard what fails"
— it also discards what **nothing could verify**. A VLM's failure mode isn't silence, it's
a plausible, well-formatted answer of the right size, with no way to know whether it read
the page or made it up. Named consequence of the design: the document whose OCR shuffles
the tables (`6860f28c`) would need **two** escalated values that confirm each other before
either is accepted, because that's what V1b compares — a single escalated value verifies
nothing.

**The parser is deliberately unforgiving.** `bool` is `int` in Python, and a `True` that
slipped through would become `1` in a euro field — checked explicitly. Eight plausible,
useless responses are rejected by test: prose instead of JSON, a code fence, a bbox with
three numbers, a bbox outside the page, a bbox that's a point, an inverted bbox. Saying
"it's not on this page" is a valid, expected answer, not an error.

**Where a credential can exist, and only there.** The key is read from the environment at
call time, never stored on an attribute, never shows up in `repr()` — tested by
constructing the client with a plausible fake key and checking it's absent from both the
repr and `vars()`. Two static guards: no test imports `anthropic`, and the real client is
only ever constructed in `cli.py` across the whole package.

**The path runs end to end over the real corpus**, with a fake transport that always
answers "not found here" — and the ledger shows that a question with no answer still
**cost something**: the image was rendered and sent before the model said it found
nothing. A second test confirms the expensive, correct case: a well-formed answer for
`6860f28c`, which no check covers, is paid for and discarded.

**What was left out:** any real call — the central choice of this stage — cost derived and
labeled as such rather than a "measurement" from a run nobody carefully checked;
`PL_COGS_FRGAAP` has no check covering it in either format; no retry on a malformed
response.
