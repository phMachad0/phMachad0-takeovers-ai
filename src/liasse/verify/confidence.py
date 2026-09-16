"""Turning check results into a number that means something.

The schema has a `confidence` field. Filling it with the OCR's own score would answer a
different question - that is confidence about pixels, not about the interpretation - and
filling it with a constant would be decoration.

What it is derived from here is how many *independent* checks a value survived. A figure
that met the other side of its balance sheet, its own arithmetic, and a filing deposited a
year later is grounded three different ways; one that no check could reach is reported, and
says so.
"""

from __future__ import annotations

from dataclasses import dataclass

from liasse.verify.registry import CheckResult

# A value no check could reach is not wrong, it is unverified. Above the floor of a bare
# extraction, below anything a check has actually confirmed.
UNVERIFIED = 0.60
# One check passing is real evidence; each further independent one adds less.
BY_CHECKS_PASSED = {1: 0.85, 2: 0.93, 3: 0.97}
MAX_CONFIDENCE = 0.98
# Any failure dominates: the value disagrees with something the document itself says.
FAILED = 0.30


@dataclass(frozen=True, slots=True)
class Confidence:
    score: float
    passed: tuple[str, ...]
    failed: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return bool(self.passed) and not self.failed


def for_field(field_key: str, results: list[CheckResult]) -> Confidence:
    relevant = [r for r in results if field_key in r.covers]
    passed = tuple(sorted({r.check_id for r in relevant if r.passed}))
    failed = tuple(sorted({r.check_id for r in relevant if not r.passed}))

    if failed:
        score = FAILED
    elif passed:
        score = min(BY_CHECKS_PASSED.get(len(passed), MAX_CONFIDENCE), MAX_CONFIDENCE)
    else:
        score = UNVERIFIED
    return Confidence(score=score, passed=passed, failed=failed)
