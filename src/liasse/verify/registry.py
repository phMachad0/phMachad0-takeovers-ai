"""Checks, and what running one produces.

A check is production logic and test oracle at the same time. That is the whole idea of
this stage: there is no answer key, so the only way to say anything about accuracy is to
find statements the documents make twice and see whether the two agree.

Registering them by decorator means adding a check is adding a function, and the confidence
aggregator never needs to know how many exist.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

Number = int | Decimal


class Scope(Enum):
    DOCUMENT = "document"  # inside one filing
    COMPANY = "company"  # between two filings of the same company


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    passed: bool
    detail: str
    # Field keys whose confidence this result speaks to.
    covers: tuple[str, ...] = ()
    delta: Number | None = None
    tolerance: Number = 0


@dataclass(frozen=True, slots=True)
class Check:
    check_id: str
    scope: Scope
    description: str
    run: Callable[..., list[CheckResult]]


REGISTRY: list[Check] = []


def check(check_id: str, scope: Scope, description: str) -> Callable:
    def register(fn: Callable[..., list[CheckResult]]) -> Callable:
        REGISTRY.append(Check(check_id=check_id, scope=scope, description=description, run=fn))
        return fn

    return register


def checks_for(scope: Scope) -> list[Check]:
    return [c for c in REGISTRY if c.scope is scope]


# Each printed figure is rounded to the euro on its own, so an n-term sum can sit a few
# units away from the printed total without either being misread. The tolerance is that
# rounding budget and nothing more: it is never wide enough to absorb a digit.
def rounding_tolerance(terms: int) -> int:
    return max(1, terms // 2)


def compare(
    check_id: str,
    left: Number,
    right: Number,
    terms: int,
    detail: str,
    covers: tuple[str, ...] = (),
) -> CheckResult:
    tolerance = rounding_tolerance(terms)
    delta = left - right
    return CheckResult(
        check_id=check_id,
        passed=abs(delta) <= tolerance,
        detail=f"{detail}: {left} vs {right}" + (f", off by {delta}" if delta else ""),
        covers=covers,
        delta=delta,
        tolerance=tolerance,
    )


@dataclass(frozen=True, slots=True)
class DocumentFacts:
    """Everything the checks need about one filing."""

    doc_id: str
    siren: str
    fiscal_year_end: str | None
    fields: dict[str, Any] = field(default_factory=dict)  # field_key -> TypedValue
    # The same fields as read off this filing's plaquette pages, when it carries both
    # formats. Kept apart from `fields` rather than merged into them: the point of having
    # two readings is to compare them, and a merge would destroy exactly that.
    fields_plaquette: dict[str, Any] = field(default_factory=dict)
    codes: dict[str, Number] = field(default_factory=dict)  # line code -> current year
    # Rows read off plaquette pages for the checks: a plaquette has no line codes,
    # so these are keyed by the catalogue's own term ids instead.
    terms_plaquette: dict[str, Number] = field(default_factory=dict)
    codes_previous: dict[str, Number] = field(default_factory=dict)  # -> previous year
    # The closing date as printed on the form, against the registry's own dateCloture.
    printed_closing_date: str | None = None

    def value(self, field_key: str) -> Number | None:
        typed = self.fields.get(field_key)
        return None if typed is None else typed.value
