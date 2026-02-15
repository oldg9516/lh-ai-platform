"""Subscription modification tools.

Phase 2: Uses Mock APIs (via APIFactory) to return realistic results.
Phase 6: HITL forms for confirmation.

Tools now return actual API responses instead of stubs.
"""

import json

import structlog

from database.customer_queries import lookup_customer
from mock_apis.factory import APIFactory

logger = structlog.get_logger()


async def change_frequency(
    customer_email: str,
    new_frequency: str,
) -> str:
    """Change customer's subscription frequency.

    Use this tool when a customer wants to switch between monthly,
    bi-monthly, or quarterly delivery.

    Args:
        customer_email: The customer's email address.
        new_frequency: Desired frequency: 'monthly', 'bi-monthly', or 'quarterly'.

    Returns:
        JSON string with API result
    """
    logger.info("tool_called", tool="change_frequency", email=customer_email, new_frequency=new_frequency)

    # 1. Verify customer exists
    customer = lookup_customer(customer_email)
    if not customer:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "Customer with this email not found. Please verify the email address.",
        })

    # 2. Call API (mock or real via Factory)
    api = APIFactory.get_subscription_api()
    result = await api.change_frequency(customer_email, new_frequency)

    # 3. Return result
    if result["success"]:
        return json.dumps({
            "status": "completed",
            "customer_email": customer_email,
            "customer_name": customer.get("name"),
            "new_frequency": result["new_frequency"],
            "next_charge_date": result["next_charge_date"],
            "notification_sent": result["notification_sent"],
            "message": f"Frequency updated to {new_frequency}. Confirmation email sent.",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Failed to update frequency"),
        })


async def skip_month(
    customer_email: str,
    month: str = "next",
) -> str:
    """Skip one month of customer's subscription.

    Use this tool when a customer wants to skip their next box.

    Args:
        customer_email: The customer's email address.
        month: Which month to skip. Default 'next' for the upcoming month.

    Returns:
        JSON string with API result
    """
    logger.info("tool_called", tool="skip_month", email=customer_email, month=month)

    # 1. Verify customer exists
    customer = lookup_customer(customer_email)
    if not customer:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "Customer with this email not found.",
        })

    # 2. Call API
    api = APIFactory.get_subscription_api()
    result = await api.skip_month(customer_email, month)

    # 3. Return result
    if result["success"]:
        return json.dumps({
            "status": "completed",
            "customer_email": customer_email,
            "customer_name": customer.get("name"),
            "skipped_month": result["skipped_month"],
            "next_charge_date": result["next_charge_date"],
            "notification_sent": result["notification_sent"],
            "message": f"Skipped {result['skipped_month']}. Confirmation email sent.",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Failed to skip month"),
        })


async def pause_subscription(
    customer_email: str,
    duration_months: int = 1,
) -> str:
    """Pause customer's subscription for specified duration.

    Use this tool when a customer wants to temporarily pause their
    subscription.

    Args:
        customer_email: The customer's email address.
        duration_months: Number of months to pause (1-12).

    Returns:
        JSON string with API result
    """
    logger.info("tool_called", tool="pause_subscription", email=customer_email, duration=duration_months)

    # 1. Verify customer exists
    customer = lookup_customer(customer_email)
    if not customer:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "Customer with this email not found.",
        })

    # 2. Call API
    api = APIFactory.get_subscription_api()
    result = await api.pause_subscription(customer_email, duration_months)

    # 3. Return result
    if result["success"]:
        return json.dumps({
            "status": "completed",
            "customer_email": customer_email,
            "customer_name": customer.get("name"),
            "paused_until": result["paused_until"],
            "notification_sent": result["notification_sent"],
            "message": f"Subscription paused until {result['paused_until']}. Confirmation email sent.",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Failed to pause subscription"),
        })


async def change_address(
    customer_email: str,
    new_address: str,
) -> str:
    """Update customer's shipping address.

    Use this tool when a customer provides a new address or wants
    to change the delivery recipient.

    Args:
        customer_email: The customer's email address.
        new_address: The full new shipping address (street, city, country).

    Returns:
        JSON string with API result
    """
    logger.info("tool_called", tool="change_address", email=customer_email)

    # 1. Verify customer exists
    customer = lookup_customer(customer_email)
    if not customer:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "Customer with this email not found.",
        })

    # 2. Parse address string to dict (simple parsing)
    # Expected format: "Street, City, Country" or dict
    if isinstance(new_address, str):
        parts = [p.strip() for p in new_address.split(",")]
        address_dict = {
            "street": parts[0] if len(parts) > 0 else "",
            "city": parts[1] if len(parts) > 1 else "",
            "country": parts[2] if len(parts) > 2 else "Israel",
        }
    else:
        address_dict = new_address

    # 3. Call API
    api = APIFactory.get_address_api()
    result = await api.validate_and_update_address(customer_email, address_dict)

    # 4. Return result
    if result["success"]:
        validated = result["validated_address"]
        return json.dumps({
            "status": "completed",
            "customer_email": customer_email,
            "customer_name": customer.get("name"),
            "new_address": f"{validated['street']}, {validated['city']}, {validated['country']}",
            "validated": True,
            "notification_sent": result["notification_sent"],
            "message": "Address validated and updated. Confirmation email sent.",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Failed to update address"),
        })
