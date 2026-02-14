"""Damage and leaking item report tools (stubs).

Tools for creating damage claims and requesting photo evidence.
"""

import json
import uuid

import structlog

logger = structlog.get_logger()


def create_damage_claim(
    customer_email: str,
    item_description: str,
    damage_description: str,
) -> str:
    """Create a damage claim for a damaged or leaking item.

    Use this tool when a customer reports receiving a damaged or
    leaking item. Creates a claim record that will be reviewed
    by the support team. Ask the customer for photos to speed
    up the resolution.

    Args:
        customer_email: The customer's email address.
        item_description: Which item was damaged (e.g., 'olive oil bottle').
        damage_description: Description of the damage (e.g., 'bottle cracked, oil leaked').

    Returns:
        JSON string with claim ID, status, and next steps.
    """
    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    logger.info("tool_called", tool="create_damage_claim", email=customer_email, claim_id=claim_id)
    return json.dumps({
        "claim_id": claim_id,
        "customer_email": customer_email,
        "item_description": item_description,
        "damage_description": damage_description,
        "status": "submitted",
        "next_steps": "Please send photos of the damaged item so we can process your claim quickly.",
        "resolution_options": ["replacement_item", "full_box_replacement", "credit_to_account"],
        "estimated_resolution_days": 3,
    })


def request_photos(
    customer_email: str,
    claim_id: str = "",
) -> str:
    """Request damage photos from the customer.

    Use this tool after creating a damage claim to formally request
    that the customer send photos of the damaged item(s).

    Args:
        customer_email: The customer's email address.
        claim_id: The damage claim ID (if already created).

    Returns:
        JSON string with photo upload instructions.
    """
    logger.info("tool_called", tool="request_photos", email=customer_email, claim_id=claim_id)
    return json.dumps({
        "action": "photos_requested",
        "customer_email": customer_email,
        "claim_id": claim_id or "pending",
        "instructions": "Please reply with photos showing the damaged item(s) and packaging. This helps us process your claim faster.",
        "accepted_formats": ["jpg", "png", "heic"],
    })
