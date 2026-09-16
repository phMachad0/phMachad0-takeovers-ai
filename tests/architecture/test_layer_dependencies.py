"""The layering rule is enforced here, not by convention.

A module in layer N may import from layers strictly below N. Violating this is how a
modular design quietly becomes a ball of mud, and it is cheap to detect: parse every
source file and look at what it imports.

See wiki/06-plano/arquitetura-modular.md, decision 1.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from liasse import layers, paths

SRC = paths.REPO_ROOT / "src" / "liasse"


def _own_layer(module_path: Path) -> tuple[str, int] | None:
    """Return (subpackage, layer) for a source file, or None if it sits outside layering."""
    relative = module_path.relative_to(SRC)
    head = relative.parts[0]
    if head.removesuffix(".py") in layers.UNLAYERED:
        return None
    if head in layers.LAYERS:
        return head, layers.LAYERS[head]
    return None


def _imported_subpackages(tree: ast.AST) -> set[str]:
    """Names of liasse subpackages this module imports, however the import is spelled."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[0] == "liasse" and len(parts) > 1:
                found.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "liasse" and len(parts) > 1:
                    found.add(parts[1])
    return found


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_there_is_source_to_check():
    """Guard against the suite passing because it found nothing to look at."""
    assert _source_files(), f"no python sources under {SRC}"


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: str(p.relative_to(SRC)))
def test_module_only_imports_lower_layers(path: Path):
    own = _own_layer(path)
    if own is None:
        return  # entry points and the layer map itself are exempt
    name, level = own

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for imported in _imported_subpackages(tree):
        if imported == name or imported in layers.UNLAYERED:
            continue
        other = layers.LAYERS.get(imported)
        if other is None:
            continue  # a helper module such as liasse.paths, not a layer
        assert other < level, (
            f"{path.relative_to(SRC)} is layer {level} ({name}) but imports "
            f"liasse.{imported}, which is layer {other}. A layer may only import "
            f"from layers below it."
        )


def test_every_subpackage_is_in_the_layer_map():
    """A new subpackage must declare its layer, or the rule silently stops covering it."""
    on_disk = {p.name for p in SRC.iterdir() if p.is_dir() and not p.name.startswith("_")}
    undeclared = on_disk - set(layers.LAYERS)
    assert not undeclared, f"subpackages missing from layers.LAYERS: {sorted(undeclared)}"
