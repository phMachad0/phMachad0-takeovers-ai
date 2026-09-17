"""The accuracy figure the README quotes, and what it is and is not.

There is no answer key, so nothing here measures truth. What it measures is *agreement*:
how often a value met an independent statement the documents themselves make. That is the
best available stand-in and it is not the same thing, which the README has to say.
"""

from __future__ import annotations

from collections import Counter

from liasse.verify.runner import VerifiedDocument, pass_rates


def build_report(documents: list[VerifiedDocument]) -> dict:
    by_confidence: Counter = Counter()
    verified = unverified = contradicted = 0

    per_document = []
    for doc in documents:
        fields = []
        for key, typed in sorted(doc.values.items()):
            if "__" in key:
                continue
            confidence = doc.confidence[key]
            by_confidence[confidence.score] += 1
            if confidence.failed:
                contradicted += 1
            elif confidence.passed:
                verified += 1
            else:
                unverified += 1
            fields.append(
                {
                    "field_key": key,
                    "value": float(typed.value)
                    if not isinstance(typed.value, int)
                    else typed.value,
                    "unit": typed.unit,
                    "confidence": confidence.score,
                    "checks_passed": list(confidence.passed),
                    "checks_failed": list(confidence.failed),
                }
            )
        per_document.append(
            {
                "siren": doc.document.siren,
                "doc_id": doc.document.doc_id,
                "fiscal_year_end": doc.document.fiscal_year_end,
                "fields": fields,
                "checks": [
                    {
                        "check_id": r.check_id,
                        "passed": r.passed,
                        "detail": r.detail,
                        "delta": float(r.delta) if r.delta is not None else None,
                        "tolerance": r.tolerance,
                    }
                    for r in doc.results
                ],
            }
        )

    total = verified + unverified + contradicted
    return {
        "about": (
            "Independent checks over the extracted values. These measure agreement "
            "between statements the documents make more than once - they do not measure "
            "truth, and a reading that is consistently wrong in the same way would pass."
        ),
        "checks": {
            c.check_id: c.description
            for c in __import__("liasse.verify.registry", fromlist=["REGISTRY"]).REGISTRY
        },
        "pass_rates": pass_rates(documents),
        "totals": {
            "documents": len(documents),
            "fields": total,
            "verified_by_at_least_one_check": verified,
            "unverified": unverified,
            "contradicted": contradicted,
            "share_verified": round(verified / total, 4) if total else 0.0,
        },
        "documents": per_document,
    }
