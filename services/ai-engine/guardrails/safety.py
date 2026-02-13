"""Safety guardrails for the AI pipeline.

Pre-processing: check_red_lines — detect dangerous content before routing.
Post-processing: check_subscription_safety — verify AI response doesn't violate rules.
"""

import re

# Patterns that trigger immediate escalation
RED_LINE_PATTERNS = [
    (r"\b(kill|murder|die|death threat)\b", "death_threat"),
    (r"\b(sue|lawsuit|lawyer|legal action|court)\b", "legal_threat"),
    (r"\b(bank dispute|chargeback|dispute the charge)\b", "bank_dispute"),
    (r"\b(suicide|end my life|harm myself)\b", "self_harm"),
    (r"\b(bomb|weapon|attack)\b", "violence_threat"),
]

# Phrases AI must never use in responses
UNSAFE_RESPONSE_PATTERNS = [
    (r"(cancelled|canceled) your subscription", "confirmed_cancellation"),
    (r"subscription (has been|is now) (cancelled|canceled)", "confirmed_cancellation"),
    (r"(paused|suspended) your subscription", "confirmed_pause"),
    (r"subscription (has been|is now) (paused|suspended)", "confirmed_pause"),
    (r"(processed|issued|approved) (a |your )?(refund|reimbursement)", "confirmed_refund"),
    (r"refund (has been|is now|was) (processed|issued|approved)", "confirmed_refund"),
]


def check_red_lines(message: str) -> dict:
    """Scan incoming message for red-line triggers.

    Args:
        message: Raw customer message text.

    Returns:
        Dict with is_flagged, trigger, and action fields.
    """
    message_lower = message.lower()

    for pattern, trigger_name in RED_LINE_PATTERNS:
        if re.search(pattern, message_lower):
            return {
                "is_flagged": True,
                "trigger": trigger_name,
                "action": "escalate",
            }

    return {"is_flagged": False, "trigger": None, "action": None}


def check_subscription_safety(response: str) -> dict:
    """Post-process AI response to catch safety violations.

    .. deprecated::
        Replaced by :func:`agents.eval_gate.evaluate_response` which provides
        the same regex checks (Tier 1) plus LLM-based evaluation (Tier 2).
        Kept for backward compatibility and unit tests.

    Ensures AI never confirms cancellation, pause, or refund directly.

    Args:
        response: AI-generated response text.

    Returns:
        Dict with is_safe and violation fields.
    """
    response_lower = response.lower()

    for pattern, violation_name in UNSAFE_RESPONSE_PATTERNS:
        if re.search(pattern, response_lower):
            return {
                "is_safe": False,
                "violation": violation_name,
            }

    return {"is_safe": True, "violation": None}
