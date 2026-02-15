"""Damage and leaking item report tools.

Phase 2: Uses Mock APIs to return realistic damage claim results.
Tools for creating damage claims and requesting photo evidence.
"""

import json

import structlog

from database.customer_queries import lookup_customer
from mock_apis.factory import APIFactory

logger = structlog.get_logger()


async def create_damage_claim(
    customer_email: str,
    item_description: str,
    damage_description: str,
) -> str:
    """Create a damage claim for a damaged or leaking item.

    Use this tool when a customer reports receiving a damaged or
    leaking item. Creates a claim record that will be reviewed
    by the support team.

    Args:
        customer_email: The customer's email address.
        item_description: Which item was damaged (e.g., 'olive oil bottle').
        damage_description: Description of the damage (e.g., 'bottle cracked, oil leaked').

    Returns:
        JSON string with claim ID, status, and next steps.
    """
    logger.info("tool_called", tool="create_damage_claim", email=customer_email, item=item_description)

    # 1. Verify customer exists
    customer = lookup_customer(customer_email)
    if not customer:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "Customer with this email not found.",
        })

    # 2. Call API
    api = APIFactory.get_damage_claim_api()
    result = await api.create_damage_claim(
        customer_email, item_description, damage_description
    )

    # 3. Return result
    if result["success"]:
        return json.dumps({
            "status": "completed",
            "customer_email": customer_email,
            "customer_name": customer.get("name"),
            "claim_id": result["claim_id"],
            "claim_status": result["status"],
            "next_steps": result["next_steps"],
            "message": f"Damage claim {result['claim_id']} created successfully.",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Failed to create damage claim"),
        })


async def request_photos(
    customer_email: str,
    claim_id: str = "",
) -> str:
    """Request damage photos from the customer.

    Use this tool after creating a damage claim to formally request
    that the customer send photos of the damaged item(s).

    Args:
        customer_email: The customer's email address.
        claim_id: The damage claim ID (optional, if already created).

    Returns:
        JSON string with photo upload instructions.
    """
    logger.info("tool_called", tool="request_photos", email=customer_email, claim_id=claim_id)

    # 1. Verify customer exists
    customer = lookup_customer(customer_email)
    if not customer:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "Customer with this email not found.",
        })

    # 2. Call API
    api = APIFactory.get_damage_claim_api()
    result = await api.request_photos(customer_email, claim_id or None)

    # 3. Return result
    if result["success"]:
        return json.dumps({
            "status": "completed",
            "customer_email": customer_email,
            "customer_name": customer.get("name"),
            "claim_id": result["claim_id"],
            "upload_url": result["upload_url"],
            "instructions": result["instructions"],
            "notification_sent": result["notification_sent"],
            "message": "Photo upload instructions sent via email.",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Failed to send photo request"),
        })
