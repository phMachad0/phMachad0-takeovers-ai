"""The layer map, as data.

Kept in the package rather than in the test so that the rule is visible to anyone
reading the source, and so the test has a single source of truth to check against.
"""

# Layer number per subpackage. A module may import from strictly lower layers only.
LAYERS: dict[str, int] = {
    # Layer 0 has no dependencies of its own. ``geometry`` is pure maths on plain numbers
    # and ``corpus`` only reads files into containers; neither knows the other exists.
    # They sat on separate layers until text/lines.py needed both, which the architecture
    # test caught immediately - a same-layer import is forbidden for the same reason a
    # backwards one is.
    "corpus": 0,
    "geometry": 0,
    "text": 1,
    "routing": 2,
    "fields": 3,
    "extract": 4,
    "units": 5,
    "verify": 6,
    "cost": 6,
    # Both sit above verify and neither knows the other exists: escalation decides what to
    # re-read from what the checks said, and emission writes down what survived.
    "emit": 7,
    "vlm": 7,
}

# Modules that sit outside the layering: entry points are allowed to touch everything.
UNLAYERED: frozenset[str] = frozenset({"cli", "layers", "__init__", "__main__"})
