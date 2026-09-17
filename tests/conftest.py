"""Shared fixtures.

Kept deliberately thin: most tests should work on frozen fixtures under tests/golden/
rather than on the 200 MB corpus, so the suite stays fast and portable.
"""

from __future__ import annotations

import importlib.util
from types import ModuleType

import pytest

from liasse import paths


@pytest.fixture(scope="session")
def repo_root():
    return paths.REPO_ROOT


@pytest.fixture(scope="session")
def corpus_dir():
    """The shipped corpus. Tests using this must be marked ``@pytest.mark.corpus``."""
    if not paths.DATA_DIR.is_dir():
        pytest.skip("corpus not present at data/")
    return paths.DATA_DIR


@pytest.fixture(scope="session")
def bbox_viewer() -> ModuleType:
    """``tools/bbox_viewer.py`` loaded as a module.

    It ships as a script, so it is imported by path. Importing it rather than copying its
    arithmetic is the point: a copy would drift, and the differential test would end up
    comparing us against our own belief instead of against Takeovers' implementation.
    """
    spec = importlib.util.spec_from_file_location("takeovers_bbox_viewer", paths.BBOX_VIEWER)
    if spec is None or spec.loader is None:
        pytest.skip(f"cannot load {paths.BBOX_VIEWER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
