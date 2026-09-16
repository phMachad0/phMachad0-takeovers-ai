"""The derived half of the cost claim.

Nothing here talks to an API, and the tests are written so that would be visible if it
ever did: every figure is arithmetic over page sizes and published constants. What is
worth testing is that the arithmetic is the published arithmetic - the two limits on an
image bind in the right order - and that the scenarios are built from the pages rather
than from a table someone typed.
"""

from __future__ import annotations

import math

import pytest

from liasse.cost.meter import PRICES
from liasse.cost.vlm import (
    CHARS_PER_TOKEN,
    MAX_IMAGE_TOKENS,
    MAX_LONG_EDGE_PX,
    PIXELS_PER_IMAGE_TOKEN,
    PageImage,
    answer_characters,
    build_scenarios,
    image_tokens,
    prompt_characters,
    render_size_px,
    saturation_dpi,
    tokens_from_characters,
)

A4_PT = (595.0, 842.0)


def _page(width_px: int, height_px: int, carries: bool = True, kind: str | None = "liasse"):
    return PageImage("doc", 1, width_px, height_px, carries, kind)


# --- rendering and tokenisation ---------------------------------------------------------


def test_render_size_is_points_at_the_asked_resolution():
    assert render_size_px(*A4_PT, 72) == (595, 842)
    assert render_size_px(*A4_PT, 300) == (2479, 3508)


def test_a_small_image_is_charged_by_area():
    assert image_tokens(1000, 1000) == 1_000_000 // PIXELS_PER_IMAGE_TOKEN + 1


def test_the_per_image_ceiling_binds():
    assert image_tokens(3000, 3000) == MAX_IMAGE_TOKENS


def test_an_oversized_image_is_downscaled_before_it_is_charged():
    """Long edge first, then area. A 10000 px page is not charged as a 10000 px page."""
    huge = image_tokens(10_000, 10_000)
    assert huge <= MAX_IMAGE_TOKENS
    # Downscaled to the long edge, the square page is MAX_LONG_EDGE_PX on both sides.
    uncapped = math.ceil(MAX_LONG_EDGE_PX**2 / PIXELS_PER_IMAGE_TOKEN)
    assert huge == min(MAX_IMAGE_TOKENS, uncapped)


def test_tokens_stop_growing_above_the_saturation_resolution():
    """The point the report makes: past here, more pixels cost the same and show less."""
    dpi = saturation_dpi(*A4_PT)
    at_saturation = image_tokens(*render_size_px(*A4_PT, dpi))
    assert at_saturation == MAX_IMAGE_TOKENS
    assert image_tokens(*render_size_px(*A4_PT, dpi * 2)) == at_saturation
    assert image_tokens(*render_size_px(*A4_PT, dpi - 1)) < at_saturation


def test_a_page_rendered_lower_costs_strictly_less():
    assert image_tokens(*render_size_px(*A4_PT, 100)) < image_tokens(
        *render_size_px(*A4_PT, 150)
    )


# --- the two character counts -----------------------------------------------------------


def test_the_answer_is_measured_from_the_keys_the_schema_requires():
    """Provenance this pipeline emits for free is not charged to the model."""
    lean = {
        "documents": [
            {
                "fields": [
                    {"field_key": "PL_REVENUE_FRGAAP", "value": 1, "unit": "EUR", "page": 6,
                     "bbox": [0.1, 0.2, 0.3, 0.4]}
                ]
            }
        ]
    }
    fat = {
        "documents": [
            {
                "fields": [
                    dict(
                        lean["documents"][0]["fields"][0],
                        snippet="a long snippet that a model would never be asked for",
                        extraction={"tier": "CODE"},
                        confidence=0.93,
                    )
                ]
            }
        ]
    }
    assert answer_characters(lean) == answer_characters(fat)


def test_the_prompt_is_measured_from_the_shipped_field_definitions():
    small = prompt_characters({"fields": [{"field_key": "A"}]})
    larger = prompt_characters({"fields": [{"field_key": "A"}, {"field_key": "B"}]})
    assert 0 < small < larger


def test_characters_become_tokens_at_the_stated_ratio_and_the_ratio_is_named():
    assert tokens_from_characters(400) == 400 // CHARS_PER_TOKEN.value
    assert CHARS_PER_TOKEN.name == "chars_per_token"
    assert CHARS_PER_TOKEN.basis, "an assumption without a basis is a guess with a label"


# --- the scenarios ----------------------------------------------------------------------


def _corpus() -> list[PageImage]:
    """Three routed pages, one of them a plaquette, and two that carry nothing."""
    return [
        _page(1000, 1400, carries=True, kind="liasse"),
        _page(1000, 1400, carries=True, kind="liasse"),
        _page(1000, 1400, carries=True, kind="plaquette"),
        _page(1000, 1400, carries=False, kind=None),
        _page(1000, 1400, carries=False, kind=None),
    ]


def test_the_scenarios_are_built_from_the_pages_they_are_given():
    scenarios = {s.name: s for s in build_scenarios(_corpus(), 200, 50)}
    assert scenarios["deterministic"].pages_sent == 0
    assert scenarios["escalate_pages_without_line_codes"].pages_sent == 1
    assert scenarios["vlm_on_routed_pages"].pages_sent == 3
    assert scenarios["vlm_on_every_page"].pages_sent == 5


def test_sending_nothing_costs_nothing_and_it_is_arithmetic_that_says_so():
    deterministic = next(
        s for s in build_scenarios(_corpus(), 200, 50) if s.name == "deterministic"
    )
    assert deterministic.input_tokens == 0
    assert deterministic.output_tokens == 0
    assert deterministic.usd(PRICES["claude-opus-5"]) == pytest.approx(0.0)


def test_the_prompt_is_charged_per_page_sent_and_the_answer_only_where_there_is_one():
    pages = _corpus()
    prompt, answer = 200, 50
    everything = next(
        s for s in build_scenarios(pages, prompt, answer) if s.name == "vlm_on_every_page"
    )
    image = sum(image_tokens(p.width_px, p.height_px) for p in pages)
    assert everything.input_tokens == image + prompt * len(pages)
    # Two of the five pages carry nothing; a model answers them with an empty list.
    assert everything.output_tokens == answer * sum(1 for p in pages if p.carries_fields)


def test_routing_is_the_decision_that_changes_the_bill_by_a_factor():
    scenarios = {s.name: s for s in build_scenarios(_corpus(), 200, 50)}
    price = PRICES["claude-sonnet-5"]
    routed = scenarios["vlm_on_routed_pages"].usd(price)
    everything = scenarios["vlm_on_every_page"].usd(price)
    assert everything > routed
    assert scenarios["escalate_pages_without_line_codes"].usd(price) < routed


def test_a_bigger_model_costs_more_for_the_same_tokens():
    scenario = next(
        s for s in build_scenarios(_corpus(), 200, 50) if s.name == "vlm_on_routed_pages"
    )
    assert scenario.usd(PRICES["claude-opus-5"]) > scenario.usd(PRICES["claude-haiku-4-5"])
