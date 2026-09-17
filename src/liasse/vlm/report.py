"""What escalation asked, what it got, and what it kept.

Every question appears, including the ones whose answer was thrown away. A report that only
listed the accepted values would make the path look far better than it is: the interesting
number here is how much was paid for answers that no check could confirm.
"""

from __future__ import annotations

from liasse.cost.meter import FX
from liasse.vlm.escalate import Escalation


def build_report(escalation: Escalation, model: str, dpi: int) -> dict:
    outcomes = escalation.outcomes
    accepted = [o for o in outcomes if o.accepted]
    return {
        "about": (
            "Values the deterministic path could not settle, re-read by a vision model. A "
            "re-read value is emitted only when a check computed from other figures on "
            "other pages agrees with it - so a question that no check could cover is paid "
            "for and discarded, and appears here as such."
        ),
        "settings": {"model": model, "render_dpi": dpi},
        "totals": {
            "questions_asked": len(outcomes),
            "accepted": len(accepted),
            "refused_by_shape": sum(1 for o in outcomes if "refused" in o.why),
            "not_on_the_page": sum(1 for o in outcomes if "not on this page" in o.why),
            "no_check_could_cover": sum(1 for o in outcomes if "no check covers" in o.why),
            "rejected_by_a_check": sum(1 for o in outcomes if o.why.startswith("rejected")),
            "stopped_at_page_cap": escalation.stopped_at_cap,
        },
        "cost": {
            "api_calls": len(escalation.ledger.calls),
            "input_tokens": escalation.ledger.input_tokens,
            "output_tokens": escalation.ledger.output_tokens,
            "usd": round(escalation.ledger.usd(), 6),
            "eur": round(escalation.ledger.eur(), 6),
            "fx": FX.as_dict(),
            "measured": True,
        },
        "questions": [
            {
                "doc_id": o.target.document.doc_id,
                "siren": o.target.document.siren,
                "field_key": o.target.field_key,
                "page": o.target.page,
                "escalated_because": o.target.reason,
                "value": o.value,
                "accepted": o.accepted,
                "verdict": o.why,
                "input_tokens": o.call.input_tokens if o.call else None,
                "output_tokens": o.call.output_tokens if o.call else None,
            }
            for o in outcomes
        ],
    }
