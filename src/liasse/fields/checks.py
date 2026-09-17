"""Line codes read only so the checks have something to check against.

None of these is one of the twelve fields. They exist because a filed form is a system of
equations - France plus exports equals total revenue, financial income minus financial
expense equals the financial result - and those equations are the only way to tell a
correct reading from a plausible one when there is no answer key.
"""

from __future__ import annotations

from liasse.fields.catalog import Column, RowAnchor, words

CHECK_ANCHORS: tuple[RowAnchor, ...] = (
    # Form 2051: the other side of the balance sheet, for V1.
    RowAnchor("2051", "EE", label=(words("total"), words("general")), allows_previous=True),
    RowAnchor("2051", "DI", label=(words("resultat"), words("exercice")), allows_previous=True),
    # Form 2052: the terms of the revenue split and of the financial result.
    RowAnchor("2052", "FJ"),
    RowAnchor("2052", "FK"),
    RowAnchor(
        "2052",
        "GP",
        label=(words("total"), words("produits"), words("financiers")),
        allows_previous=True,
    ),
    RowAnchor(
        "2052",
        "GU",
        label=(words("total"), words("charges"), words("financieres")),
        allows_previous=True,
    ),
    # Form 2053: the bottom line, to meet DI coming from the balance sheet.
    RowAnchor("2053", "HN", label=(words("benefice"), words("perte")), allows_previous=True),
    # Form 2050: total assets read as gross, for the column-selection check.
    RowAnchor(
        "2050",
        "CO",
        column=Column.NET_OF_THREE,
        label=(words("total"), words("general")),
        allows_previous=True,
    ),
)

BY_CODE: dict[str, RowAnchor] = {a.code: a for a in CHECK_ANCHORS}
