"""Where things live on disk.

Every path in the project is derived from ``REPO_ROOT`` so that the pipeline can be run
from any working directory, and so tests never depend on the caller's cwd.
"""

from __future__ import annotations

from pathlib import Path

# src/liasse/paths.py -> src/liasse -> src -> repo root
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = REPO_ROOT / "data"
CHALLENGE_DIR: Path = REPO_ROOT / "challenges" / "bilan"
RESULTS_SCHEMA: Path = CHALLENGE_DIR / "schema" / "results.schema.json"
FIELD_DEFS: Path = CHALLENGE_DIR / "schema" / "financial_fields.json"
BBOX_VIEWER: Path = REPO_ROOT / "tools" / "bbox_viewer.py"

# Intermediate per-stage output, inspectable and disposable.
ARTIFACTS_DIR: Path = REPO_ROOT / "artifacts"
# Measurements cited by the README. Versioned on purpose: the diff shows what changed.
REPORTS_DIR: Path = REPO_ROOT / "reports"
# The deliverable itself, at the repository root as the brief requires.
RESULTS_JSON: Path = REPO_ROOT / "results.json"
