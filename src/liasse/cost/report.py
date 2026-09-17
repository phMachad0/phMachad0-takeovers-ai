"""Turning a measurement and a derivation into reports/cost.json.

The file is split in two at the top level, ``measured`` and ``derived``, because that is
the distinction the brief says it reads. Nothing crosses the line: the measured half is
what the run observed, the derived half never touched an API and says so in its own
``about``.
"""

from __future__ import annotations

import statistics

from liasse.cost.meter import EUR_DECIMALS, FX, PRICES, TOKENS_PER_MILLION, FxRate, Price
from liasse.cost.vlm import (
    CHARS_PER_TOKEN,
    MAX_IMAGE_TOKENS,
    MAX_LONG_EDGE_PX,
    PIXELS_PER_IMAGE_TOKEN,
    Assumption,
    PageImage,
    Scenario,
    image_tokens,
    saturation_dpi,
)


def _priced(scenario: Scenario, price: Price, pages_in_corpus: int, fx: FxRate) -> dict:
    usd = scenario.usd(price)
    eur = fx.to_eur(usd)
    output_usd = scenario.output_tokens * price.usd_per_mtok_output / TOKENS_PER_MILLION
    return {
        "usd": round(usd, EUR_DECIMALS),
        "eur": round(eur, EUR_DECIMALS),
        # Per page of the corpus, not per page sent: that is the number that multiplies
        # when the corpus grows, and the one the schema's cost_eur_per_page means.
        "eur_per_page_of_corpus": round(eur / pages_in_corpus, EUR_DECIMALS),
        "eur_per_page_sent": (
            round(eur / scenario.pages_sent, EUR_DECIMALS) if scenario.pages_sent else None
        ),
        # How much of the bill is the answer rather than the page. Small, which is why the
        # one assumption in this table - characters per token - barely moves it.
        "output_share": round(output_usd / usd, 4) if usd else None,
    }


def render_facts(pages: list[PageImage], dpi: int) -> dict:
    """What the pages cost as images, and where paying for more pixels stops helping."""
    tokens = [image_tokens(p.width_px, p.height_px) for p in pages]
    # 87 distinct page sizes across the 415 pages: these are scans, so no two deposits
    # agree on the millimetre. Reported as a range rather than a list for that reason.
    shapes = {(p.width_pt, p.height_pt) for p in pages if p.width_pt and p.height_pt}
    saturation = [saturation_dpi(w, h) for w, h in shapes]
    return {
        "dpi": dpi,
        "rules": {
            "pixels_per_image_token": PIXELS_PER_IMAGE_TOKEN,
            "max_long_edge_px": MAX_LONG_EDGE_PX,
            "max_image_tokens": MAX_IMAGE_TOKENS,
            "consulted": "2026-06-24",
            "source": "Anthropic published vision limits",
        },
        "image_tokens": {
            "min": min(tokens),
            "median": int(statistics.median(tokens)),
            "max": max(tokens),
        },
        "pages_at_the_ceiling": sum(1 for t in tokens if t == MAX_IMAGE_TOKENS),
        "distinct_page_sizes": len(shapes),
        "saturation_dpi": {"min": min(saturation), "max": max(saturation)},
        "saturation_note": (
            "Above this resolution the image is downscaled or the per-image ceiling binds, "
            "so a higher render costs the same and shows the model less. It is the "
            "resolution the price stops at."
        ),
    }


def build_report(
    run_block: dict,
    pages: list[PageImage],
    scenarios: list[Scenario],
    prompt_tokens_per_page: int,
    output_tokens_per_page: int,
    dpi: int,
    assumptions: list[Assumption] | None = None,
    fx: FxRate = FX,
) -> dict:
    pages_in_corpus = len(pages)
    by_name = {s.name: s for s in scenarios}

    priced = [
        {
            "name": s.name,
            "about": s.about,
            "pages_sent": s.pages_sent,
            "input_tokens": s.input_tokens,
            "output_tokens": s.output_tokens,
            "by_model": {
                model: _priced(s, price, pages_in_corpus, fx) for model, price in PRICES.items()
            },
        }
        for s in scenarios
    ]

    routed = by_name.get("vlm_on_routed_pages")
    everything = by_name.get("vlm_on_every_page")
    headline = None
    if routed and everything and routed.pages_sent:
        headline = {
            "pages_if_routed": routed.pages_sent,
            "pages_if_not": everything.pages_sent,
            "waste_factor": round(everything.pages_sent / routed.pages_sent, 2),
            "note": (
                "Routing is the only decision on this table that changes the bill by a "
                "factor rather than a fraction, and it costs nothing to make. The pages it "
                "discards were measured to carry none of the twelve fields, so the larger "
                "number buys no accuracy - it buys the same answer, later."
            ),
        }

    return {
        "about": (
            "What this run cost, and what a vision model would cost on the same corpus. "
            "The two halves are kept apart on purpose: 'measured' is what the run "
            "observed, 'derived' never called an API."
        ),
        "measured": {
            "cost_eur_per_page": run_block["cost_eur_per_page"],
            "seconds_per_page": run_block["seconds_per_page"],
            "pages_processed": run_block["pages_processed"],
            "model": run_block["model"],
            **run_block["measured"],
        },
        "derived": {
            "about": (
                "No API call was made: this repository holds no credential and reads none. "
                "Every number below is arithmetic over measured page sizes, published "
                "prices and the stated assumptions. It is a derivation, not a measurement, "
                "and converting one row of it into a measurement is the next stage's job."
            ),
            "render": render_facts(pages, dpi),
            "tokens_per_page": {
                "prompt": prompt_tokens_per_page,
                "answer_on_a_page_carrying_fields": output_tokens_per_page,
            },
            "assumptions": [a.as_dict() for a in (assumptions or [CHARS_PER_TOKEN])],
            "prices": [p.as_dict() for p in PRICES.values()],
            "fx": fx.as_dict(),
            "scenarios": priced,
            "headline": headline,
        },
    }
