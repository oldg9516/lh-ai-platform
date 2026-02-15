"""HITL proxy tools for CopilotKit integration.

These are lightweight versions of write tools that return
'pending_confirmation' instead of executing the real operation.
The Agno agent calls them during streaming, which emits AG-UI
ToolCall events. CopilotKit intercepts these events and renders
HITL confirmation forms in the chat sidebar.

After user confirmation, the frontend calls /api/copilot/execute-tool
which runs the REAL tool function.
"""

import json

import structlog

logger = structlog.get_logger()


async def pause_subscription(customer_email: str, duration_months: int = 1) -> str:
    """Pause customer subscription for specified duration.

    This action requires customer confirmation. A confirmation form
    will appear for the customer to review and approve.

    Args:
        customer_email: The customer's email address.
        duration_months: Number of months to pause (1-12).

    Returns:
        JSON string indicating confirmation is pending.
    """
    logger.info("hitl_proxy_called", tool="pause_subscription", email=customer_email, months=duration_months)
    return json.dumps({
        "status": "pending_confirmation",
        "tool": "pause_subscription",
        "customer_email": customer_email,
        "duration_months": duration_months,
        "message": "A confirmation form has been shown to the customer. They need to review and confirm the pause.",
    })


async def skip_month(customer_email: str, month: str = "next") -> str:
    """Skip one month of customer subscription.

    This action requires customer confirmation. A confirmation form
    will appear for the customer to review and approve.

    Args:
        customer_email: The customer's email address.
        month: Which month to skip. Default 'next' for the upcoming month.

    Returns:
        JSON string indicating confirmation is pending.
    """
    logger.info("hitl_proxy_called", tool="skip_month", email=customer_email, month=month)
    return json.dumps({
        "status": "pending_confirmation",
        "tool": "skip_month",
        "customer_email": customer_email,
        "month": month,
        "message": "A confirmation form has been shown to the customer. They need to review and confirm the skip.",
    })


async def change_frequency(customer_email: str, new_frequency: str) -> str:
    """Change customer subscription delivery frequency.

    This action requires customer confirmation. A confirmation form
    will appear for the customer to review and approve.

    Args:
        customer_email: The customer's email address.
        new_frequency: Desired frequency: 'monthly', 'bi-monthly', or 'quarterly'.

    Returns:
        JSON string indicating confirmation is pending.
    """
    logger.info("hitl_proxy_called", tool="change_frequency", email=customer_email, freq=new_frequency)
    return json.dumps({
        "status": "pending_confirmation",
        "tool": "change_frequency",
        "customer_email": customer_email,
        "new_frequency": new_frequency,
        "message": "A confirmation form has been shown to the customer. They need to review and confirm the frequency change.",
    })


async def change_address(customer_email: str, new_address: str) -> str:
    """Update customer shipping address.

    This action requires customer confirmation. A confirmation form
    will appear for the customer to review and approve.

    Args:
        customer_email: The customer's email address.
        new_address: The full new shipping address (street, city, country).

    Returns:
        JSON string indicating confirmation is pending.
    """
    logger.info("hitl_proxy_called", tool="change_address", email=customer_email)
    return json.dumps({
        "status": "pending_confirmation",
        "tool": "change_address",
        "customer_email": customer_email,
        "new_address": new_address,
        "message": "A confirmation form has been shown to the customer. They need to review and confirm the address change.",
    })


async def create_damage_claim(
    customer_email: str,
    item_description: str,
    damage_description: str,
) -> str:
    """Create a damage claim for a damaged or leaking item.

    This action requires customer confirmation. A confirmation form
    will appear for the customer to review and approve.

    Args:
        customer_email: The customer's email address.
        item_description: Which item was damaged (e.g., 'olive oil bottle').
        damage_description: Description of the damage (e.g., 'bottle cracked, oil leaked').

    Returns:
        JSON string indicating confirmation is pending.
    """
    logger.info("hitl_proxy_called", tool="create_damage_claim", email=customer_email, item=item_description)
    return json.dumps({
        "status": "pending_confirmation",
        "tool": "create_damage_claim",
        "customer_email": customer_email,
        "item_description": item_description,
        "damage_description": damage_description,
        "message": "A confirmation form has been shown to the customer. They need to review and confirm the damage claim.",
    })
