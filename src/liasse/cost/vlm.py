"""What the same twelve fields would cost read by a vision model, derived not measured.

No API call was made anywhere in this repository: no credential exists here and none was
introduced. So every figure in this module is a derivation, and it is labelled as one in
``reports/cost.json``. It rests on three things:

*Measured.* The page sizes of the fifteen PDFs in scope, read from the PDFs themselves, and
the page counts the router produced. A page's cost in tokens is a function of its size, and
the sizes are on disk rather than assumed to be A4.

*Published.* Anthropic's vision tokenisation and list prices, each carrying the date it was
read, and the ECB's exchange rate for the day.

*Assumed.* Exactly two things, both named in ``Assumption`` objects that travel into the
report: how many characters make a token, and - through it - how long the prompt and the
answer are. Both are derived from character counts of real text rather than invented, but
the characters-per-token ratio is a convention, not a tokeniser. It is carried separately
so a reader can disagree with that one number instead of with the whole table.

The point of the table is not the euro figure. It is the shape: sending every page costs
several times what sending the routed pages costs, and buys nothing, because the router
measured that the other pages carry none of the twelve fields.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from liasse.corpus.loader import iter_scope, page_geometry
from liasse.cost.meter import TOKENS_PER_MILLION, Price

POINTS_PER_INCH = 72

# Anthropic's published vision behaviour, read 2026-06-24. An image whose long edge exceeds
# the limit is downscaled before it is charged; what survives is billed at roughly one token
# per 750 pixels, up to a hard ceiling per image.
PIXELS_PER_IMAGE_TOKEN = 750
MAX_LONG_EDGE_PX = 2576
MAX_IMAGE_TOKENS = 4784

# Just above the resolution at which an A4 page stops costing more (see saturation_dpi):
# high enough that nothing is left on the table, low enough that the render is quick.
DEFAULT_RENDER_DPI = 200

# The five keys the results schema requires of a field. The answer a vision model has to
# return is this and nothing else; the extras this pipeline emits are provenance it can
# produce for free, and charging the model for them would overstate the comparison.
REQUIRED_FIELD_KEYS = ("field_key", "value", "unit", "page", "bbox")


@dataclass(frozen=True, slots=True)
class Assumption:
    """A number that is not measured, stated with what it rests on."""

    name: str
    value: float
    basis: str

    def as_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "basis": self.basis}


CHARS_PER_TOKEN = Assumption(
    "chars_per_token",
    4.0,
    "the conventional English average. JSON tokenises worse than prose, so this "
    "under-counts the answer; the report prints the answer's share of the bill so the "
    "size of that error can be seen rather than argued about.",
)


@dataclass(frozen=True, slots=True)
class PageImage:
    """One page as it would be sent: its rendered size, and whether it carries a field."""

    doc_id: str
    page: int
    width_px: int
    height_px: int
    carries_fields: bool
    kind: str | None
    # The page as the PDF states it. Kept beside the rendered size because the resolution
    # questions are asked in points: deriving them back out of rounded pixels invents
    # differences between pages that are the same size.
    width_pt: float = 0.0
    height_pt: float = 0.0


def render_size_px(width_pt: float, height_pt: float, dpi: int) -> tuple[int, int]:
    """Pixel size of a page rendered at ``dpi``. PDF points are 1/72 inch."""
    scale = dpi / POINTS_PER_INCH
    return round(width_pt * scale), round(height_pt * scale)


def image_tokens(width_px: int, height_px: int) -> int:
    """What one page image costs in input tokens, under the published rules."""
    long_edge = max(width_px, height_px)
    if long_edge > MAX_LONG_EDGE_PX:
        scale = MAX_LONG_EDGE_PX / long_edge
        width_px, height_px = width_px * scale, height_px * scale
    uncapped = math.ceil(width_px * height_px / PIXELS_PER_IMAGE_TOKEN)
    return min(MAX_IMAGE_TOKENS, uncapped)


def saturation_dpi(width_pt: float, height_pt: float, ceiling: int = 600) -> int:
    """The lowest dpi at which rendering a page higher stops costing more.

    Worth knowing before choosing a render resolution: above this point the extra pixels
    are either downscaled away or hit the per-image ceiling, so they are paid for in
    render time and bought nothing. Found by scanning rather than by algebra because the
    two limits bind in different orders for different page shapes.
    """
    at_ceiling = image_tokens(*render_size_px(width_pt, height_pt, ceiling))
    for dpi in range(1, ceiling + 1):
        if image_tokens(*render_size_px(width_pt, height_pt, dpi)) >= at_ceiling:
            return dpi
    return ceiling


def measure_pages(routing: dict, dpi: int) -> list[PageImage]:
    """Every page in scope, at its real size, tagged with what the router decided."""
    relevant_by_doc: dict[str, dict[int, str]] = {
        d["doc_id"]: {r["page"]: r["kind"] for r in d["relevant"]} for d in routing["documents"]
    }

    out: list[PageImage] = []
    for document in iter_scope():
        relevant = relevant_by_doc.get(document.doc_id, {})
        for path in sorted(document.ocr_dir.glob("page_*.json")):
            page = int(path.stem.split("_")[1])
            geometry = page_geometry(document, page)
            width_px, height_px = render_size_px(geometry.width_pt, geometry.height_pt, dpi)
            out.append(
                PageImage(
                    doc_id=document.doc_id,
                    page=page,
                    width_px=width_px,
                    height_px=height_px,
                    carries_fields=page in relevant,
                    kind=relevant.get(page),
                    width_pt=geometry.width_pt,
                    height_pt=geometry.height_pt,
                )
            )
    return out


def answer_characters(results: dict) -> int:
    """Characters of the answer a model would have to return for the whole corpus.

    Built from the file this pipeline already emits, cut down to the keys the schema
    requires. That makes it the length of a real answer to a real corpus rather than a
    guess at one - the only assumption left is how many characters make a token.
    """
    minimal = [
        {key: field[key] for key in REQUIRED_FIELD_KEYS if key in field}
        for document in results["documents"]
        for field in document["fields"]
    ]
    return len(json.dumps(minimal, separators=(",", ":"), ensure_ascii=False))


def prompt_characters(field_defs: dict) -> int:
    """Characters of the instruction that would go out with every page.

    The prompt is the challenge's own field definitions - the twelve keys with their
    English and French labels and their notes - because that is what a model would have to
    be told to read the same twelve things. Measured from the shipped file, not invented.
    """
    return len(json.dumps(field_defs, separators=(",", ":"), ensure_ascii=False))


def tokens_from_characters(characters: int, ratio: Assumption = CHARS_PER_TOKEN) -> int:
    return math.ceil(characters / ratio.value)


@dataclass(frozen=True, slots=True)
class Scenario:
    """A choice of which pages to send, with the token bill that choice implies."""

    name: str
    about: str
    pages_sent: int
    input_tokens: int
    output_tokens: int

    def usd(self, price: Price) -> float:
        return (
            self.input_tokens * price.usd_per_mtok_input
            + self.output_tokens * price.usd_per_mtok_output
        ) / TOKENS_PER_MILLION


def build_scenarios(
    pages: list[PageImage],
    prompt_tokens_per_page: int,
    output_tokens_per_page_with_fields: int,
) -> list[Scenario]:
    """The four ways to spend money on this corpus, cheapest first.

    Output tokens are charged only for pages that carry something: a model asked to read
    a page of court minutes answers with an empty list, which is a handful of tokens. The
    input side is charged for every page sent, because the image is paid for whether or
    not it turns out to contain anything.
    """
    with_fields = [p for p in pages if p.carries_fields]
    plaquette = [p for p in with_fields if p.kind == "plaquette"]

    def bill(selected: list[PageImage], name: str, about: str) -> Scenario:
        input_tokens = sum(
            image_tokens(p.width_px, p.height_px) + prompt_tokens_per_page for p in selected
        )
        answering = sum(1 for p in selected if p.carries_fields)
        return Scenario(
            name=name,
            about=about,
            pages_sent=len(selected),
            input_tokens=input_tokens,
            output_tokens=answering * output_tokens_per_page_with_fields,
        )

    return [
        bill([], "deterministic", "what this pipeline does: no page is sent to any model."),
        bill(
            plaquette,
            "escalate_pages_without_line_codes",
            "send only the pages that carry no liasse line code - the accountant's own "
            "presentation of the accounts. This was the obvious escalation target until "
            "the label-anchored reader was built for exactly those pages; it is priced "
            "here as the alternative that was not taken.",
        ),
        bill(
            with_fields,
            "vlm_on_routed_pages",
            "send every page the router says carries at least one of the twelve fields.",
        ),
        bill(
            pages,
            "vlm_on_every_page",
            "send the whole corpus, which is what a pipeline without a router has to do.",
        ),
    ]
