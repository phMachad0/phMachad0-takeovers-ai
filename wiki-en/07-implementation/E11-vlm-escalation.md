---
type: implementation
stage: E11
tags: [code, vlm, cost, security, tests]
status: draft
updated: 2026-09-16
---

# E11 — escalation to a vision model

**State:** done · 453 passing tests, 4 skipped · `ruff` clean
**Never run against the real API** — no credential exists in this environment, none was
introduced, and `reports/escalation.json` is not in the repository for that reason. The
whole path is exercised end to end against a fake transport (`StubTransport`).

## What this stage settles, and what it doesn't claim to prove

[[E9-cost-measurement|E9]] derived what a VLM **would cost**. This stage builds the
**path** that would actually do it — client, question/answer contract, and the acceptance
rule — without ever triggering it. The wiki and the README say this plainly: a cost number
produced by code that never ran is not a measurement, it's an estimate of an estimate. The
value of this stage is not "I solved the gaps with AI." It's "the path exists, it's safe by
construction, and I know exactly what it will cost the moment someone presses the button
with a real key."

## What was created

```
src/liasse/vlm/contract.py     the prompt and the response parser — 132 lines
src/liasse/vlm/client.py       the only boundary that touches a credential — 140 lines
src/liasse/vlm/render.py       PDF → PNG at E9's resolution — 39 lines
src/liasse/vlm/escalate.py     who gets asked, and the acceptance rule — 284 lines
src/liasse/vlm/report.py       reports/escalation.json
src/liasse/cli.py              `liasse escalate`
tests/unit/test_vlm.py         31 tests, none of which import `anthropic`
```

---

## The rule that organizes the whole module

> **A value that comes from the model is accepted only if a check, computed from other
> figures on other pages, agrees with it.**

That's stronger than "re-verify and drop whatever fails" — it also drops whatever
**nothing could verify**. The reason: a vision model's failure mode isn't "didn't answer."
It's "answered a plausible number, well formatted, the right size, and nothing in the
response says whether it read the page or made it up." There's no confidence score that
tells the two apart. The only way to distinguish them is to check the answer against
arithmetic the model never saw.

A consequence the report names instead of hiding: `6860f28c` — the document whose reading
order the OCR scrambles — would need the **total liabilities** escalated too, before the
escalated **total assets** could be accepted, because that's what V1b compares. A single
escalated value verifies nothing on its own. It's a limit of the set of checks, not of the
model, and `reports/escalation.json` would say so explicitly if it ran.

## The contract: the parser is deliberately unforgiving

A vision model asked to read a number off a scanned page almost always returns **a**
number, correctly typed and plausibly sized, whether or not it actually read anything. So
nothing is accepted on the model's word alone — the response has to arrive in exactly the
requested shape, and any deviation is refused, not corrected:

```python
if isinstance(value, bool) or not isinstance(value, int):
    raise RefusedAnswer(f"value {value!r} is not a whole number of euros")
```

`bool` is `int` in Python — `isinstance(True, int)` is true — and a `True` that slipped
through would become `1` in a euro field. Eight parametrized tests cover eight shapes of
plausible, useless answers: prose instead of JSON, a code fence, an object about a
different field, a fractional value, a bbox with three numbers, a bbox outside the page, a
bbox that's a point instead of a rectangle, an inverted bbox.

Saying the figure **isn't** on the page is a valid, expected answer — the prompt asks for
it explicitly:

```
If the figure is NOT on this page, answer {"field_key": "...", "value": null}
and nothing else. A wrong figure is worse than no figure, and this answer is expected often.
```

## The client: where a credential can exist, and only there

Two rules from the brief govern `client.py`, and neither is decorative.

**Never commit a real key or a `.env`.** The key is read from the environment **at call
time**, never stored on an object attribute, never shows up in a repr, a log, an artifact,
or `results.json`:

```python
def __repr__(self) -> str:
    return f"AnthropicTransport(model={self._settings.model!r})"
```

Tested by constructing the transport with a plausible fake key and checking that it doesn't
appear in `repr()` or `vars()`:

```python
def test_the_transport_never_holds_or_prints_the_key(monkeypatch):
    secret = "sk-ant-not-a-real-key-0123456789"
    monkeypatch.setenv(client.KEY_VARIABLE, secret)
    transport = client.AnthropicTransport(client.Settings(model="claude-haiku-4-5"))
    assert secret not in repr(transport)
    assert secret not in str(vars(transport).values())
```

**A cost claim only means something if you can see the provider and the model.** That's why
`Transport` is a `Protocol`, not a concrete class — the whole path is driven by a
`StubTransport` in the tests, and construction of the real client is confined to a single
place in the entire package:

```python
def test_only_the_entry_point_builds_the_real_transport():
    """The rule dictates where it can be applied: in the package, not in the tests."""
    ...
    assert builders == ["cli.py"], f"the real transport is constructed in {builders}"
```

And a second static guard confirms that not even one test **imports** `anthropic` — if it
did, that test would be capable of generating a real bill:

```python
def test_no_test_imports_the_provider_sdk():
    ...
```

`liasse doctor` reports whether the path can run without trying — `pip install anthropic`
is not in the project's required dependencies, so that's already the first sign:

```
escalation: unavailable - the anthropic SDK is not installed (pip install anthropic)
```

## The page cap: a guard against a routing bug, not a performance knob

```python
LIASSE_VLM_MAX_PAGES=
```

`Settings.max_pages` (default 12) stops escalation from asking further, and
`escalation.stopped_at_cap` travels through to the report. It's not a parameter to tune for
throughput — it's what stops a buggy router from turning into an unexpected bill.

## The path, end to end, against a stub

`test_the_whole_path_runs_without_a_network` runs `route → extract → verify → escalate` for
real over the corpus, with a `StubTransport` that always answers "not on this page":

```python
transport = StubTransport(json.dumps({"field_key": "BS_TOTAL_ASSETS_FRGAAP", "value": None}))
escalation = escalate_run(verified, transport, Settings(model="claude-opus-5", max_pages=3))

assert len(transport.asked) == 3
assert escalation.accepted == {}
assert escalation.ledger.usd() > 0, "questions are billed whether or not they are answered"
```

The point of that last assert: a question that comes back `null` still **cost** something —
the image was rendered and sent, the input tokens were billed. The ledger doesn't
distinguish "got no answer" from "got an empty answer"; both cost money.

A second test confirms the expensive case: a well-formed, plausible answer for `6860f28c`,
which no check covers, is **paid for and discarded**:

```python
assert all(not o.accepted for o in assets)
assert any("no check covers" in o.why for o in assets)
```

That's correct behavior, not a test failure. It's exactly the rule at the top of this page,
exercised on the one document in scope where it actually bites.

## What was left out, and why

- **No real call was made.** That's the central choice of this stage: deliver a derived
  cost curve, labeled as derived, rather than a "measurement" that actually came from a run
  nobody checked carefully.
- **`PL_COGS_FRGAAP` has no check covering it**, in either format — it's defined by the
  schema itself as a sum of line items with no printed total anywhere to compare against.
  A value escalated for it would be dropped by the acceptance rule for exactly that reason,
  and it's the right reason: inventing a check that compares the sum to itself would verify
  nothing.
- **No retry, no correction of a malformed answer.** A response outside the expected shape
  is refused and becomes an absence, not a second attempt — the cost of asking again would
  disappear from the cost argument if fake questions were free.

## Links

- [[E9-cost-measurement]] · [[cost-per-page]] · [[E7-verifiers]]
- [[E10-plaquette-extractor]] (the V1b and V4 the acceptance rule uses)
