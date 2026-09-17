"""The boundary where this pipeline would talk to a model, and the one place a key lives.

Two rules govern this module and both are the brief's:

*Never commit a real key or a .env.* So the key is read from the environment at the moment
of the call, is never stored on an object, never appears in a repr, a log line, an artefact
or results.json, and is never passed anywhere but to the SDK constructor. The names of the
variables are in .env.example with no values beside them.

*The cost claim has to say which provider and model produced it.* So every call returns its
own token counts, taken from the response rather than estimated, and the caller puts them in
the ledger that produces cost_eur_per_page.

``Transport`` exists so the escalation path can be driven end to end by a test without a
credential and without a network. That is not only a convenience: it is how the suite can
assert that no test ever constructs the real client.

**This path has never made a real call.** No credential exists in this repository and none
was introduced, so everything below is exercised against a stub. The wiki and the README say
so; a cost figure produced by code that has never run is not a measurement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

# Named in .env.example. LIASSE_VLM_DPI is read by `liasse cost`, the other three here.
KEY_VARIABLE = "ANTHROPIC_API_KEY"
MODEL_VARIABLE = "LIASSE_VLM_MODEL"
MAX_PAGES_VARIABLE = "LIASSE_VLM_MAX_PAGES"

DEFAULT_MODEL = "claude-opus-5"
# A guard against a routing bug turning into an unexpected bill, not a performance tuning
# knob. Escalation stops when it is reached and says that it did.
DEFAULT_MAX_PAGES = 12
# The answer is one small JSON object. Nothing legitimate needs more than this, and a cap
# is the only thing standing between a looping model and a large invoice.
MAX_OUTPUT_TOKENS = 512


@dataclass(frozen=True, slots=True)
class Completion:
    """What came back, and what it cost. Token counts are reported, never estimated."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int


class Transport(Protocol):
    """Anything that can answer one image-and-text question."""

    def ask(self, image_png: bytes, media_type: str, prompt: str) -> Completion: ...


@dataclass(frozen=True, slots=True)
class Settings:
    model: str = DEFAULT_MODEL
    max_pages: int = DEFAULT_MAX_PAGES

    @classmethod
    def from_environment(cls) -> Settings:
        raw = os.environ.get(MAX_PAGES_VARIABLE)
        return cls(
            model=os.environ.get(MODEL_VARIABLE) or DEFAULT_MODEL,
            max_pages=int(raw) if raw and raw.isdigit() else DEFAULT_MAX_PAGES,
        )


def credential_present() -> bool:
    """Is a key set? The value is not read here and is never returned anywhere."""
    return bool(os.environ.get(KEY_VARIABLE))


def sdk_present() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def unavailable_because() -> str | None:
    """Why escalation cannot run, in a sentence, or None when it can."""
    if not sdk_present():
        return "the anthropic SDK is not installed (pip install anthropic)"
    if not credential_present():
        return f"{KEY_VARIABLE} is not set; see .env.example for the variables to set"
    return None


class AnthropicTransport:
    """The real thing. Constructed only by `liasse escalate`, never by a test."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings.from_environment()

    def __repr__(self) -> str:
        # Explicitly not the default repr: nothing about this object may print a secret,
        # and the cheapest way to guarantee that is to hold no secret and say so.
        return f"AnthropicTransport(model={self._settings.model!r})"

    def ask(self, image_png: bytes, media_type: str, prompt: str) -> Completion:
        import base64

        import anthropic

        # Read at the moment of use and handed straight to the SDK: never stored on self,
        # never interpolated into a string, never logged.
        client = anthropic.Anthropic(api_key=os.environ[KEY_VARIABLE])
        response = client.messages.create(
            model=self._settings.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.standard_b64encode(image_png).decode("utf-8"),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return Completion(
            text=text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
