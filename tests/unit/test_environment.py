"""E0 acceptance: the environment can do the things later stages depend on.

These are not unit tests of our code; they are checks that the ground is solid. They
exist because every one of them has already caused a wrong turn or would have: pymupdf
is the only reliable source of page size in points, and the bbox_viewer that ships with
the challenge is the reference implementation the differential tests will compare against.
"""

from __future__ import annotations

import pytest

from liasse import paths


def test_repo_root_is_the_repository():
    assert (paths.REPO_ROOT / "challenges").is_dir()
    assert (paths.REPO_ROOT / "tools" / "bbox_viewer.py").is_file()


def test_pymupdf_is_importable_and_reads_page_size():
    """Page geometry is read per page, never assumed. Prove the tool works end to end."""
    pymupdf = pytest.importorskip("pymupdf")

    sample = next(paths.DATA_DIR.glob("*/bilans/pdf/*.pdf"), None)
    if sample is None:
        pytest.skip("corpus not present")

    with pymupdf.open(sample) as doc:
        rect = doc[0].rect
    assert rect.width > 0 and rect.height > 0


def test_results_schema_is_valid_json_schema():
    """If the schema itself will not compile, E8 cannot validate anything."""
    import json

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(paths.RESULTS_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_field_definitions_list_twelve_fields():
    """The challenge says 12. If this ever fails, the corpus was swapped under us."""
    import json

    defs = json.loads(paths.FIELD_DEFS.read_text(encoding="utf-8"))
    assert len(defs["fields"]) == 12
