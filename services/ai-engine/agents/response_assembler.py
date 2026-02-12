"""Response assembler — adds greeting, opener, closer, and sign-off.

Deterministic template-based assembly (no LLM calls).
Matches n8n Combinator Agent output structure with HTML div format.
"""

import hashlib
import re

import structlog

logger = structlog.get_logger()

# --- Openers by category group ---

OPENERS = {
    "shipping": [
        "I'd be happy to help you with your shipment!",
        "Let me look into your delivery for you.",
        "I understand how important it is to receive your package on time.",
    ],
    "payment": [
        "I'd be happy to help with your payment question.",
        "Let me look into your billing details.",
        "I understand you have a question about your payment.",
    ],
    "subscription": [
        "I'd be happy to help with your subscription.",
        "Let me assist you with that change.",
        "I can help you with your subscription request.",
    ],
    "damage": [
        "I'm sorry to hear about the issue with your package.",
        "I apologize for the inconvenience — let me help resolve this.",
        "I'm sorry that happened. Let me help make it right.",
    ],
    "retention": [
        "I'm sorry to hear you're considering leaving us.",
        "I understand, and I appreciate you reaching out before making a decision.",
        "Thank you for letting us know. I'd love the opportunity to help.",
    ],
    "gratitude": [
        "What a wonderful message — thank you so much!",
        "That truly means a lot to our team!",
        "Thank you for your kind words!",
    ],
    "general": [
        "Thank you for reaching out to us.",
        "I'd be happy to help you with that.",
        "Thank you for contacting Lev Haolam support.",
    ],
}

# Category → opener group mapping
CATEGORY_TO_GROUP = {
    "shipping_or_delivery_question": "shipping",
    "payment_question": "payment",
    "frequency_change_request": "subscription",
    "skip_or_pause_request": "subscription",
    "recipient_or_address_change": "subscription",
    "customization_request": "subscription",
    "damaged_or_leaking_item_report": "damage",
    "retention_primary_request": "retention",
    "retention_repeated_request": "retention",
    "gratitude": "gratitude",
}

# --- Closers ---

CLOSERS = [
    "If you have any other questions, please don't hesitate to reach out.",
    "Please let me know if there's anything else I can help with.",
    "Feel free to contact us again if you need further assistance.",
    "Don't hesitate to reach out if you need anything else.",
    "I'm here if you need any further help.",
    "Please let me know if you have any other questions or concerns.",
    "We're always here to help — just reach out anytime.",
    "Is there anything else I can assist you with today?",
]

SIGN_OFF = "Warm regards,<br>Lev Haolam Support Team"


def assemble_response(
    raw_response: str,
    customer_name: str,
    category: str,
    session_id: str,
) -> str:
    """Assemble a complete response with greeting, opener, body, closer, sign-off.

    Uses deterministic hash-based selection for consistency within sessions
    and variety across sessions.

    Args:
        raw_response: Raw AI-generated response body.
        customer_name: Customer first name (or 'Client').
        category: Primary category from classification.
        session_id: Session ID for deterministic variety.

    Returns:
        Assembled HTML response string.
    """
    # Don't wrap system/escalation responses
    if _is_system_response(raw_response):
        return raw_response

    # Deterministic index from session_id
    idx = int(hashlib.md5(session_id.encode()).hexdigest(), 16)

    # Greeting
    greeting = f"Dear {customer_name},"

    # Opener
    group = CATEGORY_TO_GROUP.get(category, "general")
    opener_list = OPENERS.get(group, OPENERS["general"])
    opener = opener_list[idx % len(opener_list)]

    # Body — strip existing greeting if AI already added one
    body = _strip_existing_greeting(raw_response, customer_name)

    # Closer
    closer = CLOSERS[idx % len(CLOSERS)]

    # Assemble with HTML div structure
    parts = [
        f"<div>{greeting}</div>",
        f"<div>{opener}</div>",
        f"<div>{body}</div>",
        f"<div>{closer}</div>",
        f"<div>{SIGN_OFF}</div>",
    ]

    return "\n".join(parts)


def _strip_existing_greeting(text: str, customer_name: str) -> str:
    """Remove duplicate greeting if the AI already added one.

    Strips patterns like 'Dear John,', 'Hi John,', 'Hello Client,' etc.
    from the beginning of the response.
    """
    # Pattern: greeting word + optional name + comma/exclamation + optional newline
    pattern = rf"^(Dear|Hi|Hello|Hey)\s+{re.escape(customer_name)}[,!]?\s*\n?"
    text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Also strip generic greetings without name
    pattern_generic = r"^(Dear Customer|Dear Client|Hello|Hi there)[,!]?\s*\n?"
    text = re.sub(pattern_generic, "", text, flags=re.IGNORECASE).strip()

    return text


def _is_system_response(text: str) -> bool:
    """Check if this is a system/escalation response that shouldn't be wrapped."""
    system_phrases = [
        "connecting you with a support agent",
        "connect you with a human",
        "having trouble processing",
        "let me connect you",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in system_phrases)
