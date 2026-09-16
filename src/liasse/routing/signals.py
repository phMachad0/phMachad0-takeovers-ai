"""The independent signals a page classification is built from.

Each function answers one question and returns what it saw, never a verdict. The verdict
is the classifier's job, and it is built from signals disagreeing as much as from them
agreeing - see wiki/03-ideias/ideia-04-roteamento-de-paginas.md.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from liasse.corpus.models import Token
from liasse.routing.titles import fold, match_title
from liasse.text.codes import codes_present
from liasse.text.numbers import numeric_ratio

# --- signal A: the printed form header -------------------------------------------------

# "DGFiP N° 2052 2023", "N° 2050-S", "DGFiP N°2058-C". The OCR mangles the degree sign and
# sometimes the P of DGFiP, so the anchor is the form number and the DGFiP prefix is
# optional. What keeps that from matching stray text is position, not the prefix: the
# header is printed at the top of the sheet, so only the first tokens are searched.
_HEADER_RE = re.compile(r"(?:DGF[iI]?[Pp]?\s*)?N[°*ºo]?\s*(20\d{2})(?:\s*-?\s*([A-Z])\b)?")
HEADER_SEARCH_DEPTH = 20


def header_form(tokens: Iterable[Token]) -> str | None:
    """The DGFiP form number printed on the page, e.g. "2052" or "2058-C"."""
    text = " ".join(t.text for t in list(tokens)[:HEADER_SEARCH_DEPTH])
    match = _HEADER_RE.search(text)
    if not match:
        return None
    number, suffix = match.group(1), match.group(2)
    return f"{number}-{suffix}" if suffix else number


# --- signal B: the structural fingerprint of line codes --------------------------------

# Codes that appear on EVERY page of a form in the corpus and on no other form. Derived by
# measurement, not from the printed form: see the E2 section of the implementation notes.
FORM_SIGNATURES: dict[str, frozenset[str]] = {
    # Bilan - Actif
    "2050": frozenset(
        {
            "AB",
            "AC",
            "AH",
            "AJ",
            "AL",
            "AM",
            "AQ",
            "AR",
            "AS",
            "AU",
            "AV",
            "AW",
            "AY",
            "BB",
            "BC",
            "BE",
            "BG",
            "BH",
            "BK",
            "BL",
            "BM",
            "BN",
            "BO",
            "BP",
            "BR",
            "BS",
            "BT",
            "BU",
            "BW",
            "BX",
            "BY",
            "BZ",
            "CA",
            "CB",
            "CE",
            "CF",
            "CG",
            "CH",
            "CK",
            "CM",
            "CN",
            "CP",
            "CR",
            "CT",
            "CV",
            "CX",
        }
    ),
    # Bilan - Passif
    "2051": frozenset(
        {
            "B1",
            "DA",
            "DB",
            "DE",
            "DF",
            "DG",
            "DH",
            "DI",
            "DJ",
            "DK",
            "DL",
            "DM",
            "DQ",
            "DR",
            "DS",
            "DU",
            "DY",
            "EA",
            "EB",
            "EC",
            "ED",
            "EF",
            "EG",
            "EH",
            "EI",
        }
    ),
    # Compte de resultat, first half
    "2052": frozenset(
        {
            "FA",
            "FB",
            "FE",
            "FG",
            "FH",
            "FJ",
            "FK",
            "GD",
            "GE",
            "GF",
            "GJ",
            "GN",
            "GP",
            "GR",
            "GS",
            "GT",
            "GU",
            "GV",
        }
    ),
    # Compte de resultat, second half
    "2053": frozenset(
        {
            "A2",
            "A3",
            "A6",
            "HA",
            "HB",
            "HC",
            "HD",
            "HE",
            "HF",
            "HG",
            "HJ",
            "HK",
            "HQ",
            "HY",
            "RC",
            "RD",
        }
    ),
}

# Below this many matching codes the fingerprint is noise, not a form.
MIN_SIGNATURE_OVERLAP = 5
# Below this many codes in total, the page is not a liasse grid at all.
MIN_CODES_FOR_LIASSE = 12


def form_from_codes(codes: set[str]) -> tuple[str | None, int]:
    """Best-matching form and how many signature codes it shares, by overlap."""
    best_form, best_overlap = None, 0
    for form, signature in FORM_SIGNATURES.items():
        overlap = len(codes & signature)
        if overlap > best_overlap:
            best_form, best_overlap = form, overlap
    if best_overlap < MIN_SIGNATURE_OVERLAP:
        return None, best_overlap
    return best_form, best_overlap


def code_fingerprint(tokens: Iterable[Token]) -> set[str]:
    return codes_present(tokens)


# --- signal C: plaquette section titles ------------------------------------------------


# A filed statement is mostly numbers. A divider page that only says "COMPTE DE RESULTAT"
# is not, and two of them exist in the corpus. Requiring density is what tells them apart.
MIN_NUMERIC_RATIO = 0.15


def plaquette_statement(tokens: Iterable[Token]) -> str | None:
    """Which financial statement a plaquette page carries, from its printed title.

    Title recognition itself lives in ``routing.titles``: it is word-level and tolerant of
    one OCR edit per word. What this function adds is the guard that a title alone is not
    a statement - a section divider carries the same words and almost no numbers.
    """
    tokens = list(tokens)
    statement = match_title(tokens)
    if statement is None:
        return None
    if numeric_ratio(tokens) < MIN_NUMERIC_RATIO:
        return None
    return statement


# --- signal C2: accounting labels, when the title did not survive the OCR --------------

# One document (445070311/6860f28c) comes back from the OCR with its reading order
# scrambled and its section titles gone: numbers first, labels scattered. The page type is
# still recoverable from which accounting labels appear on it. This is weaker evidence
# than a title and is recorded as such.
_LABEL_MARKERS: dict[str, tuple[str, ...]] = {
    "BS_LIABILITIES": ("capital", "report a nouveau", "reserve", "dettes", "provisions"),
    "BS_ASSETS": ("immobilis", "stocks", "creances", "disponibilit", "amortissement"),
    "PL": ("chiffre", "achats", "salaires", "charges d'exploitation", "charges externes"),
}
MIN_LABEL_MARKERS = 3


def statement_from_labels(tokens: Iterable[Token]) -> tuple[str | None, dict[str, int]]:
    """Best-matching statement from accounting labels, and the per-statement hit counts."""
    tokens = list(tokens)
    if numeric_ratio(tokens) < MIN_NUMERIC_RATIO:
        return None, {}
    folded = fold(" ".join(t.text for t in tokens))
    hits = {
        statement: sum(1 for marker in markers if marker in folded)
        for statement, markers in _LABEL_MARKERS.items()
    }
    best = max(hits, key=lambda k: hits[k])
    if hits[best] < MIN_LABEL_MARKERS:
        return None, hits
    return best, hits


# --- signal D: the registry's own confidentiality flag ---------------------------------

# A French company may file its income statement under a declaration of confidentiality
# (art. L. 232-25 Code de commerce). The statement is filed but not published, and the
# registry marks the deposit. Across the 15 documents in scope the correlation with a
# missing compte de resultat is exact, 5 out of 5 - see wiki F014.
CONFIDENTIAL_PL = "Partiellement confidentiel"


def income_statement_is_confidential(meta: dict) -> bool:
    return meta.get("confidentiality") == CONFIDENTIAL_PL
