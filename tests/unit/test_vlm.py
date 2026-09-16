"""Escalation: the contract, the gate, and the guarantee that no test calls anything.

The path has never made a real call - no credential exists in this repository - so what is
testable is the part that decides. That turns out to be the part worth testing: a vision
model's failure mode is a well-formed plausible answer, so everything protecting against
one lives in the parser and the acceptance gate, and both run without a network.
"""

from __future__ import annotations

import ast
import json

import pytest

from liasse import paths
from liasse.cost.meter import PRICES, TokenLedger
from liasse.geometry.boxes import BBox
from liasse.verify.registry import CheckResult
from liasse.vlm import client
from liasse.vlm.contract import Question, RefusedAnswer, parse
from liasse.vlm.escalate import _verdict, statements_for

QUESTION = Question(
    field_key="BS_TOTAL_ASSETS_FRGAAP",
    label_fr="Total général actif",
    label_en="Total assets",
    doc_id="6860f28ca0138eae340c7453",
    page=15,
    reason="absent",
)


def _reply(**payload) -> str:
    return json.dumps({"field_key": QUESTION.field_key, **payload})


# --- the contract -------------------------------------------------------------------------


def test_a_well_formed_answer_is_read():
    answer = parse(
        _reply(value=1689390, page=15, bbox=[0.6, 0.8, 0.75, 0.82], snippet="1 689 390"),
        QUESTION,
    )
    assert answer.value == 1689390
    assert answer.bbox == BBox(0.6, 0.8, 0.75, 0.82)
    assert answer.snippet == "1 689 390"


def test_saying_the_figure_is_not_there_is_a_real_answer():
    answer = parse(_reply(value=None), QUESTION)
    assert answer.is_null
    assert answer.bbox is None


@pytest.mark.parametrize(
    ("reply", "because"),
    [
        ("I could not find it, sorry.", "prose instead of JSON"),
        ('```json\n{"field_key": "x"}\n```', "a code fence"),
        ("[1, 2, 3]", "not an object"),
        ('{"field_key": "PL_REVENUE_FRGAAP", "value": 1}', "answered about another field"),
    ],
)
def test_an_answer_in_the_wrong_shape_is_refused(reply: str, because: str):
    with pytest.raises(RefusedAnswer):
        parse(reply, QUESTION)


@pytest.mark.parametrize(
    "payload",
    [
        {"value": 1234.56, "bbox": [0.1, 0.1, 0.2, 0.2]},  # money is never a float here
        {"value": True, "bbox": [0.1, 0.1, 0.2, 0.2]},  # a bool is an int in Python
        {"value": 100},  # no box: a value with no place on the page
        {"value": 100, "bbox": [0.1, 0.1, 0.2]},  # three numbers
        {"value": 100, "bbox": [0.1, 0.1, 1.4, 0.2]},  # outside the page
        {"value": 100, "bbox": [0.3, 0.1, 0.3, 0.2]},  # a point, not a rectangle
        {"value": 100, "bbox": [0.5, 0.5, 0.2, 0.9]},  # inverted
        {"value": 100, "bbox": ["a", "b", "c", "d"]},
    ],
)
def test_a_plausible_but_unusable_answer_is_refused(payload: dict):
    with pytest.raises(RefusedAnswer):
        parse(_reply(**payload), QUESTION)


def test_the_prompt_names_the_field_and_asks_for_null_when_absent():
    prompt = QUESTION.prompt
    assert QUESTION.field_key in prompt
    assert "Total général actif" in prompt
    assert "null" in prompt
    assert "Do not compute" in prompt


# --- the acceptance gate ---------------------------------------------------------------------


def _result(check_id: str, passed: bool, covers: str) -> CheckResult:
    return CheckResult(check_id=check_id, passed=passed, detail="", covers=(covers,))


KEY = "BS_TOTAL_ASSETS_FRGAAP"


def test_a_value_a_check_confirms_is_accepted():
    accepted, why = _verdict([_result("V1", True, KEY)], KEY)
    assert accepted
    assert "V1" in why


def test_a_value_a_check_contradicts_is_dropped():
    accepted, why = _verdict([_result("V1", False, KEY)], KEY)
    assert not accepted
    assert why.startswith("rejected")


def test_one_failing_check_beats_any_number_of_passing_ones():
    results = [_result("V1", True, KEY), _result("V3", False, KEY), _result("V4", True, KEY)]
    assert _verdict(results, KEY)[0] is False


def test_a_value_nothing_could_check_is_dropped_too():
    """The rule that makes this path worth having.

    A model answers with a number whether or not it read one, so a figure with no
    arithmetic behind it is indistinguishable from an invention - and it would arrive
    carrying a provenance box and a confidence score.
    """
    accepted, why = _verdict([_result("V1", True, "BS_TOTAL_EQUITY_FRGAAP")], KEY)
    assert not accepted
    assert "no check covers" in why


def test_a_field_is_only_asked_about_on_a_page_of_its_own_statement():
    assert statements_for("BS_TOTAL_ASSETS_FRGAAP") == ("BS_ASSETS",)
    assert statements_for("BS_TOTAL_EQUITY_FRGAAP") == ("BS_LIABILITIES",)
    assert statements_for("META_AVG_WORKFORCE_FRGAAP") == ("WORKFORCE",)


# --- cost -----------------------------------------------------------------------------------


def test_the_ledger_prices_simulated_calls_at_the_published_rate():
    """No call is made here; the tokens are the ones a response would report."""
    ledger = TokenLedger()
    ledger.record("p15 BS_TOTAL_ASSETS", "claude-opus-5", 4_784, 60)
    ledger.record("p9 BS_TOTAL_EQUITY", "claude-opus-5", 4_784, 55)

    price = PRICES["claude-opus-5"]
    expected = (9_568 * price.usd_per_mtok_input + 115 * price.usd_per_mtok_output) / 1_000_000
    assert ledger.input_tokens == 9_568
    assert ledger.usd() == pytest.approx(expected)
    assert ledger.usd() > 0, "a run that called an API does not cost zero"


# --- the credential -----------------------------------------------------------------------


def test_availability_is_reported_as_a_sentence_not_a_crash(monkeypatch):
    monkeypatch.delenv(client.KEY_VARIABLE, raising=False)
    reason = client.unavailable_because()
    assert reason and isinstance(reason, str)
    assert client.credential_present() is False


def test_settings_come_from_the_variables_named_in_env_example(monkeypatch):
    monkeypatch.setenv(client.MODEL_VARIABLE, "claude-haiku-4-5")
    monkeypatch.setenv(client.MAX_PAGES_VARIABLE, "3")
    settings = client.Settings.from_environment()
    assert settings.model == "claude-haiku-4-5"
    assert settings.max_pages == 3


def test_every_variable_the_code_reads_is_named_in_env_example():
    """The brief asks for exactly this, and says why: the cost claim only means something
    if the reader can see which provider and model produced it."""
    declared = (paths.REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    for name in (
        client.KEY_VARIABLE,
        client.MODEL_VARIABLE,
        client.MAX_PAGES_VARIABLE,
        "LIASSE_VLM_DPI",
    ):
        assert name in declared, f"{name} is read by the code but not named in .env.example"


def test_the_transport_never_holds_or_prints_the_key(monkeypatch):
    secret = "sk-ant-not-a-real-key-0123456789"
    monkeypatch.setenv(client.KEY_VARIABLE, secret)
    transport = client.AnthropicTransport(client.Settings(model="claude-haiku-4-5"))
    assert secret not in repr(transport)
    assert secret not in str(vars(transport).values())


def test_no_credential_is_committed():
    """`.env` is ignored and `.env.example` names variables only."""
    example = (paths.REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    for line in example.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            assert line.strip().endswith("="), f"a value leaked into .env.example: {line!r}"
    assert "sk-ant-" not in paths.RESULTS_JSON.read_text(encoding="utf-8")


# --- the guarantee that the tests do not call anything -------------------------------------


def test_no_test_imports_the_provider_sdk():
    """Checked statically, because a test that made a network call would pass silently.

    A test that reaches the SDK is a test that can bill the user. Only the CLI may build
    the real transport, and only the real transport may import anthropic.
    """
    offenders = []
    for path in sorted((paths.REPO_ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            if any(name.split(".")[0] == "anthropic" for name in imported):
                offenders.append(str(path.relative_to(paths.REPO_ROOT)))
    assert not offenders, f"tests importing the provider SDK: {sorted(set(offenders))}"


def test_only_the_entry_point_builds_the_real_transport():
    """The rule stated where it can be enforced: in the package, not in the tests."""
    source = paths.REPO_ROOT / "src" / "liasse"
    builders = []
    for path in sorted(source.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "AnthropicTransport"
            ):
                builders.append(path.name)
    assert builders == ["cli.py"], f"the real transport is constructed in {builders}"


# --- the whole path, against a stub ---------------------------------------------------------


class StubTransport:
    """Answers without a network. The reason `Transport` is a protocol and not a class."""

    def __init__(self, reply: str, input_tokens: int = 4784, output_tokens: int = 40) -> None:
        self.reply = reply
        self.asked: list[str] = []
        self._tokens = (input_tokens, output_tokens)

    def ask(self, image_png: bytes, media_type: str, prompt: str):
        from liasse.vlm.client import Completion

        assert image_png.startswith(b"\x89PNG"), "a real page image should have been rendered"
        assert media_type == "image/png"
        self.asked.append(prompt)
        return Completion(self.reply, "claude-opus-5", *self._tokens)


@pytest.fixture(scope="module")
def verified():
    from liasse.verify.runner import run

    return run()


@pytest.mark.corpus
def test_the_whole_path_runs_without_a_network(verified):
    """Render, ask, parse, re-check, account - end to end, nothing accepted.

    The stub says the figure is not on the page, which is the answer the prompt tells the
    model to give when it cannot read one. Everything is still paid for, and the report
    says so: that is the number the cost curve is actually about.
    """
    from liasse.vlm.client import Settings
    from liasse.vlm.escalate import run as escalate_run
    from liasse.vlm.report import build_report

    transport = StubTransport(json.dumps({"field_key": "BS_TOTAL_ASSETS_FRGAAP", "value": None}))
    escalation = escalate_run(verified, transport, Settings(model="claude-opus-5", max_pages=3))

    assert len(transport.asked) == 3
    assert escalation.accepted == {}
    assert len(escalation.ledger.calls) == 3
    assert escalation.ledger.usd() > 0, "questions are billed whether or not they are answered"

    report = build_report(escalation, "claude-opus-5", 200)
    assert report["totals"]["questions_asked"] == 3
    assert report["totals"]["accepted"] == 0
    assert report["cost"]["measured"] is True
    assert all(q["accepted"] is False for q in report["questions"])


@pytest.mark.corpus
def test_the_page_cap_stops_the_run_and_says_so(verified):
    """A guard against a routing bug becoming an invoice, not a tuning knob."""
    from liasse.vlm.client import Settings
    from liasse.vlm.escalate import run as escalate_run

    transport = StubTransport(json.dumps({"field_key": "X", "value": None}))
    escalation = escalate_run(verified, transport, Settings(model="claude-opus-5", max_pages=2))

    assert len(transport.asked) == 2
    assert escalation.stopped_at_cap is True


@pytest.mark.corpus
def test_a_well_formed_answer_that_no_check_covers_is_paid_for_and_dropped(verified):
    """The expensive, correct outcome, exercised on the real corpus.

    The filing whose OCR is scrambled has nothing else read from it, so an answer about
    its total assets has no second figure to be confronted with. It is bought and thrown
    away, and the report is where that shows up.
    """
    from liasse.vlm.client import Settings
    from liasse.vlm.escalate import run as escalate_run

    reply = json.dumps(
        {
            "field_key": "BS_TOTAL_ASSETS_FRGAAP",
            "value": 4_000_000,
            "page": 15,
            "bbox": [0.60, 0.80, 0.75, 0.82],
            "snippet": "4 000 000",
        }
    )
    scrambled = [v for v in verified if v.document.doc_id.startswith("6860f28c")]
    assert scrambled, "expected the scrambled filing to be in scope"

    escalation = escalate_run(
        scrambled, StubTransport(reply), Settings(model="claude-opus-5", max_pages=12)
    )
    assets = [o for o in escalation.outcomes if o.target.field_key == "BS_TOTAL_ASSETS_FRGAAP"]
    assert assets, "expected total assets to be escalated on this filing"
    assert all(not o.accepted for o in assets)
    assert any("no check covers" in o.why for o in assets)
    assert escalation.accepted == {}
