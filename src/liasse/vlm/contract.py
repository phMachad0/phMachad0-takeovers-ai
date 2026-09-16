"""What is asked of the model, and what is accepted back.

The parser here is deliberately unforgiving, and that is the whole design. A vision model
asked to read a number off a scan will almost always return *a* number, correctly typed and
plausibly sized, whether or not it read anything. There is no confidence score that
distinguishes the two. So nothing is trusted on the model's say-so: the answer has to arrive
in the exact shape asked for, and then it has to survive a check that was computed from
other figures on other pages before it is allowed into the deliverable.

Everything this module refuses is reported as an absence. That is the cheap outcome. The
expensive one is a well-formed invention, and every rule below exists to turn one into the
other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from liasse.geometry.boxes import BBox, is_normalized

# Money is an integer count of euros throughout this pipeline, because the checks compare
# for exact equality. A model that answers 1234.56 is answering a different question.
MAX_SNIPPET = 200


@dataclass(frozen=True, slots=True)
class Question:
    """One field, on one page, that the deterministic path could not settle."""

    field_key: str
    label_fr: str
    label_en: str
    doc_id: str
    page: int
    reason: str  # why it was escalated: absent, or contradicted by a named check

    @property
    def prompt(self) -> str:
        return PROMPT.format(
            field_key=self.field_key,
            label_fr=self.label_fr,
            label_en=self.label_en,
            page=self.page,
        )


PROMPT = """\
This image is one page of a French annual filing (liasse fiscale or plaquette), page {page}.

Read exactly one figure from it:
  field_key: {field_key}
  French label on the form: {label_fr}
  what it means: {label_en}

Answer with a single JSON object and nothing else. No prose, no code fence.

  {{"field_key": "{field_key}", "value": <integer or null>, "page": {page},
   "bbox": [x0, y0, x1, y1], "snippet": "<the text you read it from>"}}

Rules, all of which matter:
  - "value" is a whole number of euros as printed, with no thousands separator and no
    decimals. Negative if the page prints it in brackets or with a minus.
  - If the figure is NOT on this page, answer {{"field_key": "{field_key}", "value": null}}
    and nothing else. A wrong figure is worse than no figure, and this answer is expected
    often.
  - "bbox" is [x0, y0, x1, y1] normalised 0-1 against the page width and height, origin at
    the top left, tight around the digits you read.
  - Do not compute, infer, or add anything up. Read one printed figure or answer null.
"""


class RefusedAnswer(ValueError):
    """The model's answer was not in the shape that was asked for."""


@dataclass(frozen=True, slots=True)
class Answer:
    field_key: str
    value: int | None
    page: int
    bbox: BBox | None
    snippet: str

    @property
    def is_null(self) -> bool:
        return self.value is None


def parse(text: str, question: Question) -> Answer:
    """Read the model's reply, or refuse it.

    Refusal is not an error path taken rarely; it is the expected outcome for anything that
    is not exactly right, and the caller treats it as an absence.
    """
    try:
        payload = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise RefusedAnswer(f"not JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise RefusedAnswer("not a JSON object")
    if payload.get("field_key") != question.field_key:
        raise RefusedAnswer(f"answered about {payload.get('field_key')!r}, not the field asked")

    value = payload.get("value")
    if value is None:
        return Answer(question.field_key, None, question.page, None, "")

    # bool is an int in Python and would sail through an isinstance check.
    if isinstance(value, bool) or not isinstance(value, int):
        raise RefusedAnswer(f"value {value!r} is not a whole number of euros")

    box = payload.get("bbox")
    if not (isinstance(box, list) and len(box) == 4):
        raise RefusedAnswer("no usable bbox: a value without a place on the page is not usable")
    if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in box):
        raise RefusedAnswer("bbox is not four numbers")
    bbox = BBox(*(float(v) for v in box))
    # is_normalized also rejects an empty or inverted box, which a model that answered
    # with a point rather than a rectangle would return.
    if not is_normalized(bbox):
        raise RefusedAnswer(f"bbox {tuple(bbox)} is not a normalised rectangle on the page")

    snippet = payload.get("snippet")
    return Answer(
        field_key=question.field_key,
        value=value,
        page=int(payload.get("page", question.page)),
        bbox=bbox,
        snippet=(snippet if isinstance(snippet, str) else "")[:MAX_SNIPPET],
    )
