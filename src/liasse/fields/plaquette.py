"""The twelve fields as a plaquette prints them.

A plaquette is the accountant's own presentation of the accounts, produced by whatever
software the firm uses - Cegid, Sage, Quadratus. It carries the same figures as the liasse
and none of its line codes, so the only handle on a row is the words printed beside it, and
those words are not standardised. Three dialects appear in the fifteen filings in scope and
they disagree on nearly every row:

    liasse           Chiffres d'affaires nets          Capital social ou individuel
    dialect A        Ventes de marchandises            Capital social ou individuel
                     + Production vendue
    dialect B        Chiffres d'affaires nets          Capital social ou individuel
    dialect C        (revenue not printed)             Capital (Dont versé : 1 000 000)

Two shapes follow from that. A **term** is one row to find, with the spellings its word may
take. A **reading** is a whole way of building the field out of terms - and a field can have
several, because dialect A prints no net revenue line at all and the figure has to be built
from the two rows above it. Readings are tried in order and the first that resolves
completely wins, so the single printed total is always preferred to a sum we assembled.

Every spelling in this file was read off a page in the corpus. None is anticipated.
"""

from __future__ import annotations

from dataclasses import dataclass

from liasse.fields.catalog import words

# Statement ids, as the router assigns them to a page.
BS_ASSETS = "BS_ASSETS"
BS_LIABILITIES = "BS_LIABILITIES"
PL = "PL"
PL_CONT = "PL_CONT"


@dataclass(frozen=True, slots=True)
class Term:
    """One row to find on the page, by the words printed beside its figure."""

    # A stable id for provenance. It plays the part a liasse line code plays: it is what
    # travels into the emitted components so a reader can see which rows were added up.
    key: str
    label: tuple[frozenset[str], ...]
    without: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Reading:
    """One way of building a field: the terms to find, summed."""

    terms: tuple[Term, ...]
    note: str = ""


@dataclass(frozen=True, slots=True)
class PlaquetteSpec:
    key: str
    statements: tuple[str, ...]
    readings: tuple[Reading, ...]
    unit: str = "EUR"


# --- balance sheet, assets --------------------------------------------------------------

_TOTAL_GENERAL = Term(
    "PQ_TOTAL_GENERAL",
    label=(words("total"), words("general", "generale")),
    # The same page prints TOTAL ACTIF IMMOBILISE and TOTAL ACTIF CIRCULANT above it.
    without=words("immobilise", "circulant", "divers", "disponibilites"),
)
_TOTAL_ACTIF = Term(
    "PQ_TOTAL_ACTIF",
    label=(words("total"), words("actif")),
    without=words("immobilise", "circulant", "divers"),
)
_DISPONIBILITES = Term(
    "PQ_DISPONIBILITES",
    label=(words("disponibilites"),),
    # "DISPONIBILITÉS ET DIVERS" is a section heading and "TOTAL disponibilités et
    # divers :" is a subtotal that already contains the securities counted below.
    without=words("total", "divers"),
)
_SECURITIES = Term(
    "PQ_VMP", label=(words("valeurs"), words("mobilieres"), words("placement"))
)

# --- balance sheet, liabilities ---------------------------------------------------------

_TOTAL_EQUITY = Term(
    "PQ_TOTAL_CAPITAUX_PROPRES",
    label=(words("total"), words("capitaux"), words("propres")),
)
_EQUITY_BARE = Term(
    # One dialect prints the total on the section heading itself: "CApitaux ProprEs
    # 7 076 804 6 000 607". Safe only because a row is required to carry a figure in the
    # column being read, so the bare heading of the other dialects never matches.
    "PQ_CAPITAUX_PROPRES",
    label=(words("capitaux"), words("propres")),
)
_CAPITAL = Term(
    "PQ_CAPITAL_SOCIAL",
    label=(words("capital"), words("social")),
    without=words("souscrit"),
)
_CAPITAL_BARE = Term(
    # "Capital (Dont versé : 1 000 000)" - the amount inside the label is not read,
    # because it is printed far outside every column of the grid.
    "PQ_CAPITAL",
    label=(words("capital"),),
    without=words("souscrit", "primes"),
)

# --- profit and loss --------------------------------------------------------------------

_REVENUE = Term(
    "PQ_CA_NET",
    label=(words("chiffres", "chiffre"), words("affaires"), words("nets", "net")),
)
_SALES_GOODS = Term("PQ_VENTES", label=(words("ventes"), words("marchandises")))
_PRODUCTION_SOLD = Term(
    "PQ_PRODUCTION_VENDUE",
    label=(words("production"), words("vendue")),
    without=words("services"),
)

_VARIATION = words("variation", "vanation", "varation")
_PURCHASES_GOODS = Term(
    "PQ_ACHATS_MARCHANDISES",
    label=(words("achats"), words("marchandises")),
    without=words("variation", "vanation", "varation"),
)
_STOCK_GOODS = Term(
    # One dialect abbreviates to "Vanation de stock (m/ses)", which folds to the words
    # "vanation de stock m ses".
    "PQ_VAR_STOCK_MARCHANDISES",
    label=(_VARIATION, words("stock"), words("marchandises", "ses")),
)
_PURCHASES_MATERIALS = Term(
    "PQ_ACHATS_MATIERES",
    # "Achats de m p & aut approv." folds to "achats de m p aut approv": the condensed
    # dialect abbreviates matieres premieres to two single letters.
    label=(words("achats"), words("matieres", "mp", "m")),
    without=words("variation", "vanation", "varation"),
)
_STOCK_MATERIALS = Term(
    "PQ_VAR_STOCK_MATIERES",
    label=(_VARIATION, words("stock"), words("matieres", "p")),
)
_PRODUCTION_STOCKED = Term(
    "PQ_PRODUCTION_STOCKEE", label=(words("production"), words("stockee"))
)
_EXTERNAL = Term(
    "PQ_AUTRES_ACHATS",
    label=(words("autres"), words("achats"), words("charges"), words("externes")),
)
_WAGES = Term("PQ_SALAIRES", label=(words("salaires"), words("traitements")))
_SOCIAL = Term("PQ_CHARGES_SOCIALES", label=(words("charges"), words("sociales")))
_DEPRECIATION = Term(
    "PQ_DOT_AMORTISSEMENTS",
    label=(words("dotations"), words("amortissements")),
    without=words("provisions", "financieres", "exceptionnelles"),
)
_PROVISIONS_FIXED = Term(
    "PQ_DOT_PROVISIONS_IMMO",
    label=(words("dotations"), words("provisions"), words("immobilisations")),
    without=words("circulant", "risques"),
)
_DEPRECIATION_COMBINED = Term(
    # The condensed dialect prints one row for both: "Amortissements et provisions".
    "PQ_AMORTISSEMENTS_ET_PROVISIONS",
    label=(words("amortissements"), words("provisions")),
    without=words("dotations", "reprises"),
)
_FINANCIAL = Term(
    "PQ_RESULTAT_FINANCIER",
    label=(words("resultat"), words("financier")),
    without=words("courant"),
)
_INCOME_TAX = Term("PQ_IMPOTS", label=(words("impots"), words("benefices")))


def _one(term: Term, note: str = "") -> Reading:
    return Reading((term,), note)


PLAQUETTE_CATALOG: tuple[PlaquetteSpec, ...] = (
    PlaquetteSpec(
        "BS_TOTAL_ASSETS_FRGAAP",
        (BS_ASSETS,),
        (_one(_TOTAL_GENERAL), _one(_TOTAL_ACTIF)),
    ),
    PlaquetteSpec(
        "BS_TOTAL_EQUITY_FRGAAP",
        (BS_LIABILITIES,),
        (_one(_TOTAL_EQUITY), _one(_EQUITY_BARE)),
    ),
    PlaquetteSpec(
        "BS_CAPITAL_EQUITY_FRGAAP",
        (BS_LIABILITIES,),
        (_one(_CAPITAL), _one(_CAPITAL_BARE)),
    ),
    PlaquetteSpec(
        "BS_CASH_CURRENT_ASSET_FRGAAP",
        (BS_ASSETS,),
        (Reading((_DISPONIBILITES, _SECURITIES)),),
    ),
    PlaquetteSpec(
        "PL_REVENUE_FRGAAP",
        (PL, PL_CONT),
        (
            _one(_REVENUE),
            Reading(
                (_SALES_GOODS, _PRODUCTION_SOLD),
                note="the condensed dialect prints no net revenue line; this is the sum "
                "of the two rows it prints instead",
            ),
        ),
    ),
    PlaquetteSpec(
        "PL_COGS_FRGAAP",
        (PL, PL_CONT),
        (
            Reading(
                (
                    _PURCHASES_GOODS,
                    _STOCK_GOODS,
                    _PURCHASES_MATERIALS,
                    _STOCK_MATERIALS,
                    _PRODUCTION_STOCKED,
                )
            ),
        ),
    ),
    PlaquetteSpec("PL_PERSONNEL_COSTS_FRGAAP", (PL, PL_CONT), (Reading((_WAGES, _SOCIAL)),)),
    PlaquetteSpec("PL_EXT_SERVICES_COSTS_FRGAAP", (PL, PL_CONT), (_one(_EXTERNAL),)),
    PlaquetteSpec(
        "PL_DEPRECIATION_AMORTIZATION_FRGAAP",
        (PL, PL_CONT),
        (Reading((_DEPRECIATION, _PROVISIONS_FIXED)), _one(_DEPRECIATION_COMBINED)),
    ),
    PlaquetteSpec("PL_FINANCIAL_RESULTS_FRGAAP", (PL, PL_CONT), (_one(_FINANCIAL),)),
    PlaquetteSpec("PL_INCOME_TAX_FRGAAP", (PL, PL_CONT), (_one(_INCOME_TAX),)),
)

BY_KEY: dict[str, PlaquetteSpec] = {spec.key: spec for spec in PLAQUETTE_CATALOG}

# Read on a balance sheet for the format-agreement check rather than for the deliverable:
# a plaquette prints its own total on both sides, and the two must be the same number.
TOTAL_LIABILITIES = Term(
    "PQ_TOTAL_PASSIF",
    label=(words("total"), words("passif", "general", "generale")),
    without=words("dettes", "provisions", "autres"),
)
