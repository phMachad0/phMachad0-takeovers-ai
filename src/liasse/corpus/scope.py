"""The 15 documents the bilan challenge puts in scope, declared rather than discovered.

Listing them explicitly means a stray PDF appearing under data/ cannot silently widen
the run, and the scope is reviewable against the table in the brief without reading code.

Source: challenges/bilan/BRIEF.md. Format column: measured, see wiki F001.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Format = Literal["liasse", "plaquette"]


@dataclass(frozen=True, slots=True)
class ScopeEntry:
    siren: str
    doc_id: str
    deposit_date: str
    known_format: Format  # measured in E1.5, used to assert the router agrees


SCOPE: tuple[ScopeEntry, ...] = (
    ScopeEntry("820561470", "6493e4372f502414800f8164", "2023-06-05", "plaquette"),
    ScopeEntry("820561470", "6543d3fd08093cdace058668", "2023-06-13", "plaquette"),
    ScopeEntry("820561470", "67458f18cea78a70070fa226", "2024-01-15", "plaquette"),
    ScopeEntry("328024377", "63e8ebbb54febda17c19ee7c", "2020-12-24", "plaquette"),
    ScopeEntry("328024377", "63e8ebbb54febda17c19ee7d", "2021-12-17", "liasse"),
    ScopeEntry("328024377", "63e8ebbb54febda17c19ee7e", "2022-12-13", "liasse"),
    ScopeEntry("445070311", "63e2481c916269756a09542b", "2022-02-14", "plaquette"),
    ScopeEntry("445070311", "65a4095d5fd178b16b09b860", "2023-11-21", "plaquette"),
    ScopeEntry("445070311", "6860f28ca0138eae340c7453", "2025-05-15", "plaquette"),
    ScopeEntry("504304205", "63e13943526e1f30cd100db5", "2017-05-31", "liasse"),
    ScopeEntry("504304205", "63e13943526e1f30cd100db6", "2018-10-24", "liasse"),
    ScopeEntry("504304205", "66cd893cedec9b09d50191e8", "2024-08-06", "liasse"),
    ScopeEntry("401009741", "63e881158be6eb9f9d1ff975", "2022-11-30", "liasse"),
    ScopeEntry("401009741", "65784e5da67d84faf4042736", "2023-11-20", "liasse"),
    ScopeEntry("401009741", "68f0a715f28d8aaf48046416", "2025-10-03", "liasse"),
)

SIRENS: tuple[str, ...] = tuple(dict.fromkeys(e.siren for e in SCOPE))
