"""Customer data lookup tools.

Queries normalized customer tables (customers, subscriptions, orders).
Returns JSON strings consumed by the Support Agent.
"""

import json

import structlog

from database.customer_queries import (
    get_active_subscription_by_email,
    get_customer_history_by_email,
    get_payment_history_by_email,
)

logger = structlog.get_logger()


def get_subscription(customer_email: str) -> str:
    """Look up a customer's active subscription by email address.

    Use this tool when you need to know the customer's subscription plan,
    status, shipping address, or billing details to answer their question.

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with subscription details including plan, status,
        next billing date, shipping address, and subscription ID.
    """
    logger.info("tool_called", tool="get_subscription", email=customer_email)

    result = get_active_subscription_by_email(customer_email)
    if not result:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "No customer found with this email. Please ask the customer to verify their email address.",
        })

    customer = result["customer"]
    sub = result.get("subscription")

    if not sub:
        return json.dumps({
            "found": True,
            "customer_email": customer["email"],
            "customer_name": customer.get("name"),
            "subscription": None,
            "subscriptions_count": 0,
            "message": "Customer found but has no subscriptions on record.",
        })

    return json.dumps({
        "found": True,
        "customer_email": customer["email"],
        "customer_name": customer.get("name"),
        "customer_number": sub.get("customer_number"),
        "status": sub.get("status", "Unknown"),
        "frequency": sub.get("frequency", "Monthly"),
        "price": float(sub["regular_box_price"]) if sub.get("regular_box_price") else None,
        "price_currency": sub.get("price_currency", "USD"),
        "next_billing_date": sub.get("next_payment_date"),
        "billing_day": sub.get("billing_day"),
        "start_date": sub.get("start_date"),
        "no_alcohol": sub.get("no_alcohol", False),
        "no_honey": sub.get("no_honey", False),
        "shipping_address": {
            "street": customer.get("street"),
            "line2": customer.get("address_line_2"),
            "city": customer.get("city"),
            "state": customer.get("state"),
            "zip": customer.get("zip_code"),
            "country": customer.get("country"),
        },
        "payment_method": sub.get("payment_method"),
        "payment_method_id": sub.get("payment_method_id"),
        "payment_expire_date": sub.get("payment_expire_date"),
        "payer_name": sub.get("payer_name"),
        "payer_email": sub.get("payer_email"),
        "subscriptions_count": result["subscriptions_count"],
    })


def get_customer_history(customer_email: str) -> str:
    """Look up a customer's support interaction history.

    Use this tool for retention cases to understand the customer's past
    interactions, complaints, and satisfaction level before crafting
    a personalized retention response.

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with past orders, subscription tenure,
        and order history summary.
    """
    logger.info("tool_called", tool="get_customer_history", email=customer_email)

    result = get_customer_history_by_email(customer_email)
    if not result:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "No customer found with this email. Please ask the customer to verify their email address.",
        })

    return json.dumps(result)


def get_payment_history(customer_email: str, months: int = 6) -> str:
    """Look up a customer's recent payment history.

    Use this tool when the customer asks about charges, billing dates,
    amounts, or payment failures.

    Args:
        customer_email: The customer's email address.
        months: Number of months of history to retrieve (default: 6).

    Returns:
        JSON string with recent payments including dates, amounts,
        and payment status.
    """
    logger.info("tool_called", tool="get_payment_history", email=customer_email, months=months)

    result = get_payment_history_by_email(customer_email, months=months)
    if not result:
        return json.dumps({
            "found": False,
            "customer_email": customer_email,
            "message": "No customer found with this email. Please ask the customer to verify their email address.",
        })

    return json.dumps(result)
