"""Box customization tools (stubs).

Returns mock data about box contents and customization options.
"""

import json

import structlog

logger = structlog.get_logger()


def get_box_contents(customer_email: str) -> str:
    """Look up the contents of a customer's most recent and upcoming box.

    Use this tool when a customer asks about what items are in their box,
    requests specific items, or wants to exclude certain products
    (e.g., no alcohol, no cosmetics).

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with recent box contents, upcoming box preview,
        and available customization preferences.
    """
    logger.info("tool_called", tool="get_box_contents", email=customer_email)
    return json.dumps({
        "customer_email": customer_email,
        "last_box": {
            "month": "February 2026",
            "items": [
                {"name": "Extra Virgin Olive Oil (500ml)", "category": "food", "origin": "Gush Etzion"},
                {"name": "Dead Sea Mineral Soap", "category": "cosmetics", "origin": "Dead Sea"},
                {"name": "Handmade Ceramic Mezuzah", "category": "judaica", "origin": "Hebron"},
                {"name": "Organic Honey (250g)", "category": "food", "origin": "Golan Heights"},
                {"name": "Woven Bookmark", "category": "crafts", "origin": "Shiloh"},
                {"name": "Community Story Card", "category": "information", "origin": "Lev Haolam"},
            ],
        },
        "customization_preferences": {
            "current": [],
            "available_exclusions": ["alcohol", "cosmetics", "food_items"],
            "note": "Customization preferences can be updated. Changes take effect from the next box.",
        },
    })
