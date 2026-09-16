"""Measuring what a run cost.

The brief says what it reads in this block: "whether your cost claim is derived or
guessed". So the two halves of the claim are kept apart, and neither is allowed to be a
number someone typed.

``Meter`` measures. It holds a wall clock and the pages a run actually touched, and it
knows nothing about models or money. Every figure it reports is a division of two things
it observed, and it refuses to report anything at all if it observed nothing - a meter
that measured no pages raises rather than returning a comfortable zero.

``Call`` and ``TokenLedger`` price. A ledger accumulates the tokens of the calls that were
made - none, in this pipeline - and a dated price table turns them into euros. That is why
``cost_eur_per_page`` here is not the literal ``0.0``: it is an empty ledger divided by a
measured page count. It comes out at zero today and stops coming out at zero the instant a
call is recorded, which is the property the E9 test pins down.

The price table and the exchange rate carry the date they were read. A price is a fact
about a day, and one stored without its day rots silently.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from liasse.corpus.loader import iter_scope

TOKENS_PER_MILLION = 1_000_000

# Micro-euro. Below the resolution of any decision, and enough that a per-page cost of a
# few thousandths of a cent does not round away to nothing.
EUR_DECIMALS = 6
SECONDS_DECIMALS = 5

_ANTHROPIC_PRICING = "Anthropic published list prices"
_ECB = "ECB euro foreign exchange reference rate"


@dataclass(frozen=True, slots=True)
class Price:
    """A published list price in USD per million tokens, with the day it was read."""

    model: str
    usd_per_mtok_input: float
    usd_per_mtok_output: float
    consulted: str
    source: str

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "usd_per_mtok_input": self.usd_per_mtok_input,
            "usd_per_mtok_output": self.usd_per_mtok_output,
            "consulted": self.consulted,
            "source": self.source,
        }


# Read 2026-06-24. Sonnet 5 carried an introductory rate of 2.00/10.00 that expired on
# 2026-08-31, so the standard rate is the one that applies to any run made today.
PRICES: dict[str, Price] = {
    "claude-opus-5": Price("claude-opus-5", 5.00, 25.00, "2026-06-24", _ANTHROPIC_PRICING),
    "claude-sonnet-5": Price("claude-sonnet-5", 3.00, 15.00, "2026-06-24", _ANTHROPIC_PRICING),
    "claude-haiku-4-5": Price("claude-haiku-4-5", 1.00, 5.00, "2026-06-24", _ANTHROPIC_PRICING),
}


@dataclass(frozen=True, slots=True)
class FxRate:
    """USD per EUR on a stated day, from a stated authority."""

    usd_per_eur: float
    date: str
    source: str

    def to_eur(self, usd: float) -> float:
        return usd / self.usd_per_eur

    def as_dict(self) -> dict:
        return {"usd_per_eur": self.usd_per_eur, "date": self.date, "source": self.source}


# The schema asks for euros and every published price is in dollars, so the conversion is
# part of the claim and is quoted like the prices are: with its date and its source.
FX = FxRate(1.1537, "2026-09-16", _ECB)


@dataclass(frozen=True, slots=True)
class Call:
    """One API call that happened, priced at the table's rate for its model."""

    label: str
    model: str
    input_tokens: int
    output_tokens: int

    def usd(self) -> float:
        price = PRICES[self.model]
        return (
            self.input_tokens * price.usd_per_mtok_input
            + self.output_tokens * price.usd_per_mtok_output
        ) / TOKENS_PER_MILLION


@dataclass(slots=True)
class TokenLedger:
    """Every call a run made. Empty here, because this pipeline calls nothing."""

    calls: list[Call] = field(default_factory=list)

    def record(self, label: str, model: str, input_tokens: int, output_tokens: int) -> Call:
        if model not in PRICES:
            raise KeyError(f"no price on file for {model!r}; add it with the date you read it")
        call = Call(label, model, input_tokens, output_tokens)
        self.calls.append(call)
        return call

    @property
    def input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def models(self) -> list[str]:
        return sorted({c.model for c in self.calls})

    def usd(self) -> float:
        """What the recorded calls would be billed. A sum over nothing, when nothing ran."""
        return math.fsum(c.usd() for c in self.calls)

    def eur(self, fx: FxRate = FX) -> float:
        return fx.to_eur(self.usd())


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    seconds: float


def pages_in_scope() -> int:
    """Every page of every filing in scope, counted from the files on disk.

    Counted by listing rather than by loading: the point is the denominator of the cost,
    and parsing 415 pages of OCR to learn how many there are would put the measurement's
    own cost inside the measurement.
    """
    return sum(1 for document in iter_scope() for _ in document.ocr_dir.glob("page_*.json"))


class NothingMeasured(RuntimeError):
    """Asked for a rate before any page was counted."""


@dataclass(slots=True)
class Meter:
    """Wall clock per stage, and the pages a run touched.

    ``clock`` is injectable so a test can drive the meter with a clock it controls and
    check that the reported rate follows the measurement. That is the whole guarantee: a
    hardcoded number cannot satisfy two different clocks.
    """

    stages: list[Stage] = field(default_factory=list)
    ledger: TokenLedger = field(default_factory=TokenLedger)
    pages: int = 0
    pages_carrying_fields: int = 0
    # Through a factory rather than as a bare default: a plain function sitting in a class
    # body is a descriptor, and self.clock would arrive bound to the instance.
    clock: Callable[[], float] = field(default_factory=lambda: time.perf_counter)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = self.clock()
        try:
            yield
        finally:
            self.stages.append(Stage(name, self.clock() - started))

    def count(self, pages: int, carrying_fields: int = 0) -> None:
        self.pages += pages
        self.pages_carrying_fields += carrying_fields

    @property
    def seconds(self) -> float:
        return math.fsum(s.seconds for s in self.stages)

    def _denominator(self) -> int:
        if not self.pages:
            raise NothingMeasured(
                "no pages were counted, so there is no rate to report. A meter that "
                "measured nothing must say so rather than report zero."
            )
        return self.pages

    @property
    def seconds_per_page(self) -> float:
        return self.seconds / self._denominator()

    @property
    def eur_per_page(self) -> float:
        return self.ledger.eur() / self._denominator()

    def run_block(self, model: str, notes: str) -> dict:
        """The ``run`` block of results.json, entirely out of what this meter observed.

        The three keys the schema requires are ratios. The ``measured`` block underneath
        them is what they were divided from, so a reader can redo the arithmetic instead
        of taking the ratio on trust.
        """
        return {
            "cost_eur_per_page": round(self.eur_per_page, EUR_DECIMALS),
            "seconds_per_page": round(self.seconds_per_page, SECONDS_DECIMALS),
            "pages_processed": self.pages,
            "model": model,
            "notes": notes,
            "measured": {
                "seconds_total": round(self.seconds, SECONDS_DECIMALS),
                "pages_in_scope": self.pages,
                "pages_carrying_fields": self.pages_carrying_fields,
                "stages": [
                    {"name": s.name, "seconds": round(s.seconds, SECONDS_DECIMALS)}
                    for s in self.stages
                ],
                "api_calls": len(self.ledger.calls),
                "models_called": self.ledger.models,
                "input_tokens": self.ledger.input_tokens,
                "output_tokens": self.ledger.output_tokens,
                "usd_total": round(self.ledger.usd(), EUR_DECIMALS),
                "fx": FX.as_dict(),
            },
        }
