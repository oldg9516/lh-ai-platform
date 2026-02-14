"""Shipping and tracking tools.

Queries normalized tracking_events and orders tables.
Returns JSON strings consumed by the Support Agent.
"""

import json

import structlog

from database.customer_queries import get_tracking_by_email

logger = structlog.get_logger()


def track_package(customer_email: str) -> str:
    """Track the most recent package shipment for a customer.

    Use this tool when a customer asks about their package location,
    delivery status, or estimated delivery date.

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with tracking number, carrier, current status,
        and tracking history.
    """
    logger.info("tool_called", tool="track_package", email=customer_email)

    result = get_tracking_by_email(customer_email)
    if not result:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "No customer found with this email. Please ask the customer to verify their email address.",
        })

    if not result.get("tracking_number"):
        return json.dumps({
            "found": True,
            "customer_email": customer_email,
            "tracking": None,
            "message": result.get("message", "No recent shipment with tracking found."),
        })

    tracking = result.get("tracking") or {}
    order = result.get("order", {})

    return json.dumps({
        "found": True,
        "customer_email": customer_email,
        "tracking_number": result["tracking_number"],
        "carrier": tracking.get("carrier"),
        "delivery_status": tracking.get("delivery_status"),
        "delivery_date": tracking.get("delivery_date"),
        "history": tracking.get("history", []),
        "shipped_date": order.get("shipping_date"),
        "box_name": order.get("box_name"),
        "box_sequence": order.get("box_sequence"),
    })
