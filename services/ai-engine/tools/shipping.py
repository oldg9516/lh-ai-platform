"""Shipping and tracking tools (stubs).

Returns realistic mock tracking data. In production, will integrate
with DHL/USPS/Israel Post APIs.
"""

import json

import structlog

logger = structlog.get_logger()


def track_package(customer_email: str) -> str:
    """Track the most recent package shipment for a customer.

    Use this tool when a customer asks about their package location,
    delivery status, or estimated delivery date.

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with tracking number, carrier, current status,
        location, and estimated delivery date.
    """
    logger.info("tool_called", tool="track_package", email=customer_email)
    return json.dumps({
        "tracking_number": "LH2026021345IL",
        "carrier": "Israel Post / USPS",
        "status": "in_transit",
        "status_description": "Package is in transit to destination country",
        "shipped_date": "2026-02-05",
        "estimated_delivery": "2026-02-20 to 2026-02-27",
        "last_location": "JFK International Sorting Facility, New York",
        "last_update": "2026-02-11",
        "tracking_url": "https://track.levhaolam.com/LH2026021345IL",
        "events": [
            {"date": "2026-02-11", "location": "New York, US", "status": "Arrived at destination country"},
            {"date": "2026-02-08", "location": "Tel Aviv, IL", "status": "Departed origin country"},
            {"date": "2026-02-05", "location": "Kfar Maimon, IL", "status": "Shipped"},
        ],
    })
