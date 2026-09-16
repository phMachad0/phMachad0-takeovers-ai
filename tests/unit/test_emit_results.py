"""The deliverable itself.

The gate is the schema Takeovers ships: "a submission we cannot parse is a submission we
cannot score". Everything else here guards the two rules the brief states outright - that
absence is reported rather than invented, and that every value carries where it was read.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from liasse import paths
from liasse.corpus.scope import SCOPE
from liasse.emit.results import build, build_documents
from liasse.fields.catalog import BY_KEY
from liasse.verify.runner import run

pytestmark = pytest.mark.corpus


@pytest.fixture(scope="module")
def document():
    return build(
        run(),
        {
            "cost_eur_per_page": 0.0,
            "seconds_per_page": 0.1,
            "pages_processed": 415,
            "model": "provided OCR + rules",
            "notes": "test run",
        },
    )


@pytest.fixture(scope="module")
def schema():
    return json.loads(paths.RESULTS_SCHEMA.read_text(encoding="utf-8"))


# --- the gate -----------------------------------------------------------------------------


def test_it_validates_against_the_schema_takeovers_ships(document, schema):
    jsonschema.validate(document, schema)


def test_the_file_on_disk_validates_too(schema):
    """Guards the case where the builder is right and what was written is not."""
    if not paths.RESULTS_JSON.exists():
        pytest.skip("run `liasse emit` first")
    jsonschema.validate(json.loads(paths.RESULTS_JSON.read_text(encoding="utf-8")), schema)


# --- absence -------------------------------------------------------------------------------


def test_every_filing_in_scope_appears(document):
    """All fifteen, so a reader is told which were left rather than noticing seven gone."""
    assert len(document["documents"]) == len(SCOPE)
    assert {d["siren"] for d in document["documents"]} == {e.siren for e in SCOPE}


def test_the_filings_not_processed_say_why(document):
    skipped = [d for d in document["documents"] if "not_processed" in d]
    assert len(skipped) == 7
    assert all("plaquette" in d["not_processed"] for d in skipped)
    assert all(d["fields"] == [] for d in skipped)


def test_no_field_is_reported_as_zero_when_it_was_not_read(document):
    """financial_fields.json: "omit it rather than reporting 0"."""
    for record in document["documents"]:
        emitted = {f["field_key"] for f in record["fields"]}
        for absent in record.get("fields_absent", []):
            assert absent not in emitted


def test_a_field_absent_from_a_filing_is_listed_not_invented(document):
    confidential = [
        d
        for d in document["documents"]
        if d["siren"] == "401009741" and d["fiscal_year_end"] == "2025-04-30"
    ]
    assert confidential
    absent = confidential[0].get("fields_absent", [])
    assert "PL_REVENUE_FRGAAP" in absent


# --- grounding ------------------------------------------------------------------------------


def test_every_box_is_a_valid_normalised_rectangle(document):
    for record in document["documents"]:
        for field in record["fields"]:
            x0, y0, x1, y1 = field["bbox"]
            assert 0.0 <= x0 < x1 <= 1.0
            assert 0.0 <= y0 < y1 <= 1.0


def test_no_box_covers_most_of_a_page(document):
    """A box that spans the sheet means tokens from unrelated blocks were merged."""
    for record in document["documents"]:
        for field in record["fields"]:
            x0, y0, x1, y1 = field["bbox"]
            assert (x1 - x0) < 0.98
            assert (y1 - y0) < 0.5


def test_every_value_carries_a_snippet_and_its_components(document):
    for record in document["documents"]:
        for field in record["fields"]:
            assert field["snippet"].strip()
            assert field["extraction"]["components"]


# --- the schema's own constraints -----------------------------------------------------------


def test_only_the_twelve_keys_are_emitted(document):
    for record in document["documents"]:
        for field in record["fields"]:
            assert field["field_key"] in BY_KEY


def test_count_is_used_only_for_the_workforce(document):
    for record in document["documents"]:
        for field in record["fields"]:
            if field["unit"] == "count":
                assert field["field_key"] == "META_AVG_WORKFORCE_FRGAAP"
            else:
                assert field["unit"] in ("EUR", "kEUR")
                assert field["field_key"] != "META_AVG_WORKFORCE_FRGAAP"


def test_the_pdf_path_points_at_a_file_that_exists(document):
    for record in document["documents"]:
        assert (paths.REPO_ROOT / record["pdf"]).is_file()


def test_fiscal_year_end_is_the_closing_date_not_the_deposit_date(document):
    by_id = {e.doc_id: e for e in SCOPE}
    for record in document["documents"]:
        doc_id = record["pdf"].rsplit("_", 1)[1].removesuffix(".pdf")
        assert record["fiscal_year_end"] < by_id[doc_id].deposit_date


# --- the extras that carry the reasoning -----------------------------------------------------


def test_the_rejected_kEUR_markers_travel_with_the_values(document):
    """wiki F002: seeing the trap and judging it is the part worth reporting."""
    bernachon = [d for d in document["documents"] if d["siren"] == "328024377" and d["fields"]]
    assert bernachon
    with_markers = [
        f for d in bernachon for f in d["fields"] if f["unit_evidence"]["rejected_markers"]
    ]
    assert with_markers
    assert all(f["unit"] == "EUR" for f in with_markers)


def test_the_schema_ambiguities_carry_both_readings(document):
    """ADR-002: where label_fr and notes disagree, both numbers are in the file."""
    ambiguous = [f for d in document["documents"] for f in d["fields"] if "schema_ambiguity" in f]
    assert ambiguous
    for field in ambiguous:
        assert field["schema_ambiguity"]["alternative_key"] != field["field_key"]


def test_the_run_block_is_present_and_declares_what_did_the_work(document):
    run_block = document["run"]
    assert run_block["model"]
    assert run_block["notes"].strip()
    assert run_block["cost_eur_per_page"] >= 0


def test_building_twice_gives_the_same_file(document):
    """No dictionary ordering or timestamp leaking into the deliverable."""
    again = build_documents(run())
    assert json.dumps(again, sort_keys=True) == json.dumps(document["documents"], sort_keys=True)
