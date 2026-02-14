"""Box customization tools.

Queries normalized customer/subscription tables for preferences.
Detailed box contents are not available in the current data;
returns subscription preferences and last order info.
"""

import json

import structlog

from database.customer_queries import (
    get_active_subscription_by_email,
    get_orders_by_customer,
)

logger = structlog.get_logger()


def get_box_contents(customer_email: str) -> str:
    """Look up a customer's box customization preferences and recent orders.

    Use this tool when a customer asks about what items are in their box,
    requests specific items, or wants to exclude certain products
    (e.g., no alcohol, no cosmetics).

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with customization preferences (no_alcohol, no_honey),
        last order info, and available exclusion options.
    """
    logger.info("tool_called", tool="get_box_contents", email=customer_email)

    result = get_active_subscription_by_email(customer_email)
    if not result:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "No customer found with this email. Please ask the customer to verify their email address.",
        })

    customer = result["customer"]
    sub = result.get("subscription")

    # Get last order for box info
    orders = get_orders_by_customer(customer["id"], limit=1)
    last_order = orders[0] if orders else None

    current_exclusions = []
    if sub:
        if sub.get("no_alcohol"):
            current_exclusions.append("alcohol")
        if sub.get("no_honey"):
            current_exclusions.append("honey")

    return json.dumps({
        "found": True,
        "customer_email": customer["email"],
        "last_box": {
            "box_name": last_order.get("box_name") if last_order else None,
            "box_sequence": last_order.get("box_sequence") if last_order else None,
            "sku": last_order.get("sku") if last_order else None,
            "shipping_date": last_order.get("shipping_date") if last_order else None,
            "detailed_contents_available": False,
        },
        "customization_preferences": {
            "current": current_exclusions,
            "no_alcohol": sub.get("no_alcohol", False) if sub else False,
            "no_honey": sub.get("no_honey", False) if sub else False,
            "available_exclusions": ["alcohol", "honey"],
            "note": "Customization preferences can be updated. Changes take effect from the next box.",
        },
    })
