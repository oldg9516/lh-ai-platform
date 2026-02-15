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

    # Sanitize — remove unsafe phrases
    body = _sanitize_response(body, category)

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


def _sanitize_response(text: str, category: str) -> str:
    """Remove unsafe or internal phrases from AI response.

    Filters out:
    - Internal system messages ("Answer is not needed")
    - Direct compensation promises ("we'll arrange for reshipment")
    - Raw database field names

    Args:
        text: Raw response body.
        category: Primary category.

    Returns:
        Sanitized response text.
    """
    original = text
    sanitized = False

    # Debug logging
    logger.debug(
        "sanitize_response_called",
        category=category,
        text_length=len(text),
        text_preview=text[:200] if len(text) > 200 else text,
    )

    # Extra debug for damaged category
    if category == "damaged_or_leaking_item_report":
        logger.debug(
            "damaged_full_text",
            full_text=text,
            contains_arrange=("arrange" in text.lower()),
        )

    # Remove "Answer is not needed" (internal instruction that leaked)
    if "Answer is not needed" in text:
        text = text.replace("Answer is not needed.", "").replace("Answer is not needed", "")
        sanitized = True
        logger.warning("sanitized_internal_message", category=category, phrase="Answer is not needed")

    # Replace dangerous compensation promises (case-insensitive, multi-line)
    # IMPORTANT: Patterns must work with HTML tags in text (e.g., </div><div>)
    # Use flexible apostrophe matching: \u2019 (curly), \u0027 (straight), ' (backtick)
    dangerous_patterns = [
        # Most specific patterns first - match exact phrases (with Unicode apostrophe variants)
        (r"we[\u2019\u0027']ll arrange for (?:a )?reshipment", "our team will review your case and reach out with a resolution"),
        (r"we[\u2019\u0027']ll arrange for (?:a )?replacement", "our team will investigate and get back to you"),
        (r"we[\u2019\u0027']ll send (?:a )?replacement", "our team will review this and contact you"),
        (r"replacements? will be sent", "our team will reach out with next steps"),
        # Catch any "we'll arrange" in damage context (after patterns above don't match)
        (r"we[\u2019\u0027']ll arrange", "our team will review and"),
    ]

    for pattern, safe_replacement in dangerous_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            logger.debug(
                "pattern_matched",
                category=category,
                pattern=pattern[:50],
                matched_text=match.group(0)[:100],
            )
            text = re.sub(pattern, safe_replacement, text, flags=re.IGNORECASE | re.DOTALL)
            sanitized = True
            logger.warning(
                "sanitized_dangerous_promise",
                category=category,
                pattern=pattern[:50],
                replacement=safe_replacement[:50],
            )

    # Remove "I don't have [technical_field_name]" internal messages (only explicit database field names)
    internal_field_patterns = [
        # Match explicit database field names with dots or underscores
        (r"I don't have\s+(?:payer\.email|next_planned_unpaid_box\.payment_date_planned|subscription_status)\s+for the customer\.?",
         "I apologize, but I'm unable to locate that information at the moment. Could you please provide your email address or order number?"),
        # Match raw field references in sentences
        (r"I don't have\s+[\w._]+\.[\w._]+\s+for",
         "I apologize, but I'm unable to locate that information at the moment. Could you please provide your email address or order number?"),
    ]

    for pattern, fallback in internal_field_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = re.sub(pattern, fallback, text, flags=re.IGNORECASE)
            sanitized = True
            logger.warning(
                "sanitized_internal_field_message",
                category=category,
                matched_text=match.group(0),
            )

    # Log if sanitization occurred
    if sanitized:
        logger.info(
            "response_sanitized",
            category=category,
            original_length=len(original),
            sanitized_length=len(text),
        )

    return text.strip()


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
