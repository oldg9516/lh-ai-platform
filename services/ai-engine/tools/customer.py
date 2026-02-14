"""Customer data lookup tools (stubs).

All functions return realistic mock data. In production (Phase 4+),
these will query Zoho CRM / Supabase for real customer records.
"""

import json

import structlog

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
    return json.dumps({
        "subscription_id": "sub_LH_29847",
        "customer_email": customer_email,
        "customer_name": "Valued Customer",
        "plan": "Lev Haolam Monthly Box",
        "status": "active",
        "frequency": "monthly",
        "price_usd": 54.90,
        "currency": "USD",
        "next_billing_date": "2026-03-01",
        "last_billing_date": "2026-02-01",
        "shipping_address": {
            "line1": "123 Main Street",
            "line2": "Apt 4B",
            "city": "Brooklyn",
            "state": "NY",
            "zip": "11201",
            "country": "US",
        },
        "created_at": "2024-06-15",
        "total_boxes_received": 20,
        "payment_method": "Visa ending in 4242",
    })


def get_customer_history(customer_email: str) -> str:
    """Look up a customer's support interaction history.

    Use this tool for retention cases to understand the customer's past
    interactions, complaints, and satisfaction level before crafting
    a personalized retention response.

    Args:
        customer_email: The customer's email address.

    Returns:
        JSON string with past support tickets, complaint count,
        lifetime value, and subscription tenure.
    """
    logger.info("tool_called", tool="get_customer_history", email=customer_email)
    return json.dumps({
        "customer_email": customer_email,
        "subscription_tenure_months": 20,
        "total_boxes_received": 20,
        "lifetime_value_usd": 1098.00,
        "support_tickets_total": 3,
        "recent_tickets": [
            {
                "date": "2026-01-10",
                "category": "damaged_or_leaking_item_report",
                "resolution": "replacement_sent",
                "satisfied": True,
            },
            {
                "date": "2025-08-22",
                "category": "shipping_or_delivery_question",
                "resolution": "tracking_provided",
                "satisfied": True,
            },
        ],
        "has_previous_cancel_request": False,
        "loyalty_tier": "gold",
        "average_csat": 4.5,
    })


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
    return json.dumps({
        "customer_email": customer_email,
        "payments": [
            {"date": "2026-02-01", "amount_usd": 54.90, "status": "paid", "method": "Visa ending in 4242"},
            {"date": "2026-01-01", "amount_usd": 54.90, "status": "paid", "method": "Visa ending in 4242"},
            {"date": "2025-12-01", "amount_usd": 54.90, "status": "paid", "method": "Visa ending in 4242"},
            {"date": "2025-11-01", "amount_usd": 54.90, "status": "paid", "method": "Visa ending in 4242"},
            {"date": "2025-10-01", "amount_usd": 54.90, "status": "paid", "method": "Visa ending in 4242"},
            {"date": "2025-09-01", "amount_usd": 54.90, "status": "paid", "method": "Visa ending in 4242"},
        ],
        "next_charge_date": "2026-03-01",
        "next_charge_amount_usd": 54.90,
    })
