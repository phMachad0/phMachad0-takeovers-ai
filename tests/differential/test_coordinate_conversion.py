"""Oracle O1: our coordinate conversion against the one the challenge ships.

The brief calls the 300-dpi-pixels to normalised-fractions conversion "a few lines, and
it is on purpose". It is also the single easiest thing in this project to get silently
wrong: a wrong box still validates, still points somewhere on the page, and is only
caught by looking. Takeovers handed us a reference implementation in tools/bbox_viewer.py,
so we test against theirs instead of against our own expectations.

Marked ``corpus`` because it needs the real PDFs for page sizes.
"""

from __future__ import annotations

import random

import pytest

from liasse.corpus import loader
from liasse.corpus.scope import SCOPE
from liasse.geometry import boxes, coords

# How many pages to sample per document. Fixed seed, so a failure is reproducible.
PAGES_PER_DOCUMENT = 3
SAMPLE_SEED = 0
# Below this many tokens compared, the run proves nothing and the suite should say so.
MINIMUM_TOKENS_COMPARED = 1000


def _sampled_pages():
    """(entry, page) pairs spread across all 15 documents, deterministically."""
    rng = random.Random(SAMPLE_SEED)
    out = []
    for entry in SCOPE:
        ocr_dir = loader._bilans_dir(entry.siren) / "ocr" / entry.doc_id
        pages = sorted(int(p.stem.split("_")[1]) for p in ocr_dir.glob("page_*.json"))
        if not pages:
            continue
        out += [(entry, p) for p in rng.sample(pages, min(PAGES_PER_DOCUMENT, len(pages)))]
    return out


SAMPLE = _sampled_pages()

# Filled in as the parametrised test runs; asserted at the end. Counting rather than
# trusting the sample size is what catches "passed because there was nothing to compare",
# which is a real risk here: 10% of the pages in scope carry no OCR at all (wiki F012).
_tokens_compared = 0


@pytest.mark.corpus
@pytest.mark.differential
@pytest.mark.parametrize(
    "entry,page", SAMPLE, ids=lambda v: v if isinstance(v, int) else v.doc_id[:8]
)
def test_matches_the_reference_implementation(entry, page, bbox_viewer):
    global _tokens_compared

    document = loader.load_document(entry)
    ocr_page = loader.load_page(document, page)
    geometry = ocr_page.geometry

    if not ocr_page.tokens:
        pytest.skip(f"{entry.doc_id[:8]} page {page} has no OCR lines (blank scan)")

    for token in ocr_page.tokens:
        theirs = bbox_viewer.polygon_to_norm(token.polygon, geometry.width_pt, geometry.height_pt)
        ours = coords.to_normalized(
            boxes.bounds(token.polygon), geometry.width_pt, geometry.height_pt
        )
        assert ours.as_list() == pytest.approx(theirs, abs=1e-12), (
            f"{entry.doc_id} p{page}: {token.text[:30]!r}\n"
            f"  ours   {ours.as_list()}\n  theirs {theirs}"
        )
    _tokens_compared += len(ocr_page.tokens)


@pytest.mark.corpus
def test_every_document_is_in_the_sample():
    """The comparison must span all 15 documents, not just the easy ones."""
    assert {e.doc_id for e, _ in SAMPLE} == {e.doc_id for e in SCOPE}


@pytest.mark.corpus
@pytest.mark.differential
def test_enough_tokens_were_actually_compared():
    """Defined last in the file, so pytest runs it after the parametrised test above."""
    assert _tokens_compared >= MINIMUM_TOKENS_COMPARED, (
        f"only {_tokens_compared} tokens compared against the reference; "
        "the differential test is not exercising anything meaningful"
    )
