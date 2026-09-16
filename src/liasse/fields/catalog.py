"""The twelve fields, declared rather than coded.

Every decision about *what* a field is lives here as data: which form it sits on, which
line code names its row, which printed cell of that row holds the figure, and which words
identify the row when the code did not survive the OCR. The extractor knows how to follow
an anchor; it knows nothing about accounting.

That split is the point. This file is readable by a French accountant who does not write
Python, and a change of interpretation - of which there are five open ones, see
wiki/05-decisoes/ADR-002 - is a change to a line of data, not to a branch in a function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Column(Enum):
    """Which printed cell of the anchored row carries the figure."""

    # The first cell to the right of the anchor: the current exercise. A filing that
    # prints N and N-1 side by side puts N first, so this is not "whichever we reach".
    N = "N"
    # Third cell of a form-2050 row: Brut | Amortissements | Net. The figure wanted is the
    # Net, and the Net cell carries no code of its own (wiki F011).
    NET_OF_THREE = "net_of_three"


@dataclass(frozen=True, slots=True)
class RowAnchor:
    """How to find one row, and which of its cells to read."""

    form: str
    code: str
    column: Column = Column.N
    # Discriminative words of the printed label, in order, each with its spellings. Used
    # only when the code is missing - which happens on 22% of the field/page pairs in
    # scope. Empty means the label is not discriminative enough to be trusted: on form
    # 2051 the row for DL is printed "TOTAL (I)", and four other rows say "TOTAL" too.
    label: tuple[frozenset[str], ...] = ()
    # Words that must NOT appear on the row. "dotations aux provisions" names three
    # different rows; only the exclusions tell them apart.
    without: frozenset[str] = frozenset()
    # Codes sharing this row, in printed order, when the form splits a line into columns:
    # the revenue row carries FJ (France), FK (exports) and FL (total). Needed only when
    # the target code itself is missing, to work out which cell of the row is ours.
    siblings: tuple[str, ...] = ()

    @property
    def has_label(self) -> bool:
        return bool(self.label)


def words(*spellings: str) -> frozenset[str]:
    return frozenset(spellings)


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One of the twelve fields the challenge asks for."""

    key: str
    anchors: tuple[RowAnchor, ...]
    unit: str = "EUR"
    # A second reading of the same field, emitted alongside it because the schema's own
    # label and notes disagree about which is meant (ADR-002).
    variant_key: str | None = None
    variant_anchors: tuple[RowAnchor, ...] = field(default_factory=tuple)

    @property
    def is_derived(self) -> bool:
        return len(self.anchors) > 1


# --- form 2052, compte de resultat ------------------------------------------------------

_REVENUE = RowAnchor(
    "2052",
    "FL",
    label=(words("chiffres", "chiffre"), words("affaires"), words("nets", "net")),
    siblings=("FJ", "FK", "FL"),
)
_PURCHASES_GOODS = RowAnchor(
    "2052",
    "FS",
    label=(
        words("achats"),
        words("marchandises"),
    ),
    without=words("variation"),
)
_STOCK_GOODS = RowAnchor(
    "2052", "FT", label=(words("variation"), words("stock"), words("marchandises"))
)
_PURCHASES_MATERIALS = RowAnchor(
    "2052",
    "FU",
    label=(
        words("achats"),
        words("matieres"),
    ),
    without=words("variation"),
)
_STOCK_MATERIALS = RowAnchor(
    "2052", "FV", label=(words("variation"), words("stock"), words("matieres"))
)
_PRODUCTION_STOCKED = RowAnchor("2052", "FM", label=(words("production"), words("stockee")))
_EXTERNAL = RowAnchor(
    "2052", "FW", label=(words("autres"), words("achats"), words("charges"), words("externes"))
)
_WAGES = RowAnchor("2052", "FY", label=(words("salaires"), words("traitements")))
_SOCIAL = RowAnchor("2052", "FZ", label=(words("charges"), words("sociales")))
_DEPRECIATION = RowAnchor(
    "2052", "GA", label=(words("dotations"), words("amortissements")), without=words("provisions")
)
_PROVISIONS_FIXED = RowAnchor(
    "2052",
    "GB",
    label=(words("dotations"), words("provisions")),
    # "dotations aux provisions" also names GC (actif circulant) and GD (risques).
    without=words("circulant", "risques", "charges", "amortissements"),
)
_FINANCIAL = RowAnchor("2052", "GV", label=(words("resultat"), words("financier")))

# --- form 2053 --------------------------------------------------------------------------

_INCOME_TAX = RowAnchor("2053", "HK", label=(words("impots"), words("benefices")))

# --- form 2050, bilan actif -------------------------------------------------------------

_TOTAL_ASSETS = RowAnchor(
    "2050",
    "CO",
    column=Column.NET_OF_THREE,
    label=(words("total"), words("general")),
)
_CASH = RowAnchor("2050", "CG", label=(words("disponibilites"),))
_SECURITIES = RowAnchor("2050", "CE", label=(words("valeurs"), words("mobilieres")))

# --- form 2051, bilan passif ------------------------------------------------------------

_CAPITAL = RowAnchor("2051", "DA", label=(words("capital"), words("social")))
# "TOTAL (I)" is not discriminative: the form prints TOTAL five times.
_TOTAL_EQUITY = RowAnchor("2051", "DL")
_SHARE_PREMIUM = RowAnchor("2051", "DB", label=(words("primes"), words("emission")))
_LEGAL_RESERVE = RowAnchor("2051", "DD", label=(words("reserve"), words("legale")))
_OTHER_RESERVES = RowAnchor("2051", "DG", label=(words("autres"), words("reserves")))

# --- form 2058-C ------------------------------------------------------------------------

_WORKFORCE = RowAnchor(
    "2058-C", "YP", label=(words("effectif"), words("moyen"), words("personnel"))
)


CATALOG: tuple[FieldSpec, ...] = (
    FieldSpec("PL_REVENUE_FRGAAP", (_REVENUE,)),
    # ADR-002 decision 1: the schema's label_fr says to add production stockee, which is
    # economically the wrong sign. The schema wins; the other reading is emitted too.
    FieldSpec(
        "PL_COGS_FRGAAP",
        (
            _PURCHASES_GOODS,
            _STOCK_GOODS,
            _PURCHASES_MATERIALS,
            _STOCK_MATERIALS,
            _PRODUCTION_STOCKED,
        ),
        variant_key="PL_COGS_FRGAAP__excl_production_stockee",
        variant_anchors=(_PURCHASES_GOODS, _STOCK_GOODS, _PURCHASES_MATERIALS, _STOCK_MATERIALS),
    ),
    FieldSpec("PL_PERSONNEL_COSTS_FRGAAP", (_WAGES, _SOCIAL)),
    FieldSpec("PL_EXT_SERVICES_COSTS_FRGAAP", (_EXTERNAL,)),
    # ADR-002 decision 2: GA+GB, charges on fixed assets, not every operating provision.
    FieldSpec("PL_DEPRECIATION_AMORTIZATION_FRGAAP", (_DEPRECIATION, _PROVISIONS_FIXED)),
    FieldSpec("PL_FINANCIAL_RESULTS_FRGAAP", (_FINANCIAL,)),
    FieldSpec("PL_INCOME_TAX_FRGAAP", (_INCOME_TAX,)),
    FieldSpec("BS_TOTAL_ASSETS_FRGAAP", (_TOTAL_ASSETS,)),
    FieldSpec("BS_TOTAL_EQUITY_FRGAAP", (_TOTAL_EQUITY,)),
    # ADR-002 decision 3: DA alone. It is the one reading with a second source inside the
    # document - the capital stated on the legal cover page.
    FieldSpec(
        "BS_CAPITAL_EQUITY_FRGAAP",
        (_CAPITAL,),
        variant_key="BS_CAPITAL_EQUITY_FRGAAP__incl_reserves",
        variant_anchors=(_CAPITAL, _SHARE_PREMIUM, _LEGAL_RESERVE, _OTHER_RESERVES),
    ),
    # ADR-002 decision 4: the Net cells, CG and CE, not the Brut ones CF and CD.
    FieldSpec("BS_CASH_CURRENT_ASSET_FRGAAP", (_CASH, _SECURITIES)),
    FieldSpec("META_AVG_WORKFORCE_FRGAAP", (_WORKFORCE,), unit="count"),
)

BY_KEY: dict[str, FieldSpec] = {spec.key: spec for spec in CATALOG}
