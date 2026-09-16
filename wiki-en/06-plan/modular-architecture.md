---
type: plan
tags: [architecture, code, maintainability]
status: draft
updated: 2026-09-15
---

# Modular architecture

The requirement: understandable, maintainable code that absorbs new ideas without a
rewrite. That isn't achieved by writing "with good practices" — it's achieved with
**three concrete structural decisions**.

## Decision 1 — layers with unidirectional dependency

```
layer 5   verify/      ← verifiers and confidence
layer 4   units/       ← unit resolution
layer 3   extract/  fields/   ← extraction strategies and declarative catalogue
layer 2   routing/     ← page classification
layer 1   text/  geometry/    ← pure functions, no I/O
layer 0   corpus/      ← data access, read-only
```

**Rule:** a layer only imports from lower-numbered layers. `geometry/` and `text/` import
nothing from `corpus/` — they receive data as arguments. That rule is what makes layers 1
and 2 testable without touching disk, and what keeps the codebase from turning into a ball
of mud.

Verifiable automatically with an architecture test that scans the imports — 20 lines, runs
in CI, and fails the moment someone inverts a dependency.

## Decision 2 — the contract between stages is a typed, serializable artifact

Each stage is a pure function from one type to another. No stage mutates the previous one.

```
Document       ──route──▶  RoutedDoc        pages classified
RoutedDoc      ──lines──▶  LinedDoc         relevant pages become rows
LinedDoc       ──extract─▶  [RawValue]      raw number + tokens + anchor
[RawValue]     ──units───▶  [TypedValue]    + unit + unit_evidence
[TypedValue]   ──verify──▶  [VerifiedValue] + checks + confidence
[VerifiedValue]──emit────▶  results.json
```

Every intermediate artifact is dumped to `artifacts/<stage>/<doc_id>.json`.

That buys three things at once:

- **Debugging**: you can inspect stage 3's output without running stages 4 through 8.
- **Testing**: each stage is testable with a frozen artifact as input, without needing the
  whole corpus.
- **Regression**: `git diff` on the artifacts shows exactly what a change altered.

### The types

```python
@dataclass(frozen=True)
class Token:
    text: str
    poly: tuple[tuple[float, float], ...]   # px @300dpi, ORIGINAL
    score: float
    x0: float; y0: float; x1: float; y1: float   # px, derived

@dataclass(frozen=True)
class PageGeometry:
    width_pt: float; height_pt: float       # read from the PDF
    skew_deg: float                         # from the OCR, or re-estimated

@dataclass(frozen=True)
class PageClass:
    kind: Literal["liasse", "plaquette", "prose", "blank"]
    form: str | None                        # "2050", "2052", ...
    signals: dict                           # header_hit, code_count, jaccard
    # signals is never discarded: it's what explains the decision in the report

@dataclass(frozen=True)
class Anchor:
    tier: int                               # 1 code · 2 ordinal · 3 label · 4 VLM
    code: str | None
    label_matched: str | None
    note: str

@dataclass(frozen=True)
class RawValue:
    field_key: str
    number: int | Decimal                   # NEVER float — see decision 3
    tokens_used: tuple[Token, ...]          # the bbox comes from here
    page: int
    anchor: Anchor
    components: tuple["RawValue", ...] = () # for derived fields (COGS)
```

`tokens_used` is the detail that ties everything together: the deliverable's `bbox` is the
union of these tokens' polygons, and the `snippet` is the concatenation of their texts.
Provenance isn't a field filled in at the end — it's a consequence of never discarding
where the number came from.

## Decision 3 — money is never `float`

The verifiers compare exact equalities (`CO == EE`, `FJ + FK == FL`). With `float`,
`0.1 + 0.2 != 0.3`, and the comparison would need an arbitrary tolerance, which masks real
reading errors.

Values in euros are integers in the overwhelming majority of cases. The rule:

```python
# int when there's no decimal part; Decimal when there is. float nowhere.
```

A property test that sweeps every extracted value and fails if any of them is `float`
guarantees this forever.

## The four extension points

Here's the answer to *"as new ideas come up."* Each one was designed so that a new idea
is **an addition, not an edit**.

### 1. Field catalogue — declarative, no logic

```python
# fields/catalog.py
CATALOG = {
  "PL_REVENUE_FRGAAP":       Direct(code="FL", form="2052"),
  "PL_PERSONNEL_COSTS_FRGAAP": Derived(op=SUM, codes=["FY", "FZ"], form="2052"),
  "PL_COGS_FRGAAP":          Derived(op=SUM, codes=["FS","FT","FU","FV"], form="2052",
                                     variants={"excl_bz": ...}),
  ...
}
```

`Derived` accepts `variants=` to emit, through the same path, the alternative reading for
the ambiguities settled in [[ADR-002-schema-ambiguities]] — with no `if` scattered across
the extractor.

A new field, or a revision of an ADR-002 decision, is **one line**. No new `if` anywhere.
And the file is readable by a French financial analyst who doesn't code — which is the
point of [[idea-01-code-anchoring]].

### 2. Extractor protocol — a new format is a new class

```python
class Extractor(Protocol):
    def handles(self, page: PageClass) -> bool: ...
    def extract(self, page: LinedPage, catalog) -> list[RawValue]: ...

EXTRACTORS = [LiasseExtractor(), PlaquetteExtractor(), VlmExtractor()]
```

The orchestrator walks the list and uses the first one that answers `handles`. A new
format — a simplified 2033 liasse, a different accounting package — joins the list without
touching anything that already exists. **This is the decision that makes stage E10
cheap**, which is why it needs to be in place as of E5, even though only one extractor
exists at that point.

### 3. Verifier registry — decorator

```python
@check(id="V1", scope="document", needs=["BS_TOTAL_ASSETS_FRGAAP"])
def balance_identity(doc) -> CheckResult: ...
```

A new verifier is a function with a decorator. The confidence aggregator doesn't know how
many exist — it just counts how many passed out of how many applied. See
[[idea-05-verifier-as-router]].

### 4. Anchor ladder — ordered list of strategies

```python
LADDER = [CodeFromOcr(), OrdinalFromTemplate(), FuzzyLabel(), VlmFallback()]
```

Each rung returns `RawValue | None` and **stamps its `tier` on the `Anchor`.** Reordering,
inserting a rung, or turning one off is a list change. And since the tier is recorded on
every value, the tier distribution in the output is a free metric.

## Directory structure

```
src/liasse/
├── corpus/     scope.py  loader.py  models.py
├── geometry/   coords.py  deskew.py  boxes.py
├── text/       lines.py  columns.py  numbers.py
├── routing/    signals.py  classifier.py
├── fields/     catalog.py  forms.py
├── extract/    base.py  liasse.py  plaquette.py  vlm.py
├── units/      resolver.py
├── verify/     registry.py  identity.py  arithmetic.py  crossyear.py  confidence.py
├── cost/       meter.py
├── emit/       results.py
└── cli.py
tests/          unit/  golden/  differential/  integration/  architecture/
tools/          recognition and fixture-freezing scripts
artifacts/      intermediate outputs per stage   (git-ignored)
reports/        routing.json  verification.json  cost.json   (versioned)
```

`reports/` is versioned on purpose: it's the evidence the README cites, and the `git diff`
of it between commits shows the effect of each change.

## Links

- [[00-roadmap]] · [[testing-strategy]] · [[00-overview]]
