"""Customer data queries from normalized customer tables.

Query functions for customers, subscriptions, orders, and tracking_events.
Used by tools/customer.py, tools/shipping.py, tools/customization.py.
"""

from typing import Any

import structlog

from database.connection import get_client

logger = structlog.get_logger()


def lookup_customer(email: str) -> dict[str, Any] | None:
    """Find a customer by email address.

    Args:
        email: Customer email (will be normalized to lowercase).

    Returns:
        Customer record dict or None if not found.
    """
    normalized = email.strip().lower()
    try:
        response = (
            get_client()
            .table("customers")
            .select("*")
            .eq("email", normalized)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception:
        logger.exception("lookup_customer_failed", email=normalized)
        return None


def get_subscriptions_by_customer(customer_id: int) -> list[dict[str, Any]]:
    """Get all subscriptions for a customer.

    Args:
        customer_id: The customer's internal ID.

    Returns:
        List of subscription records, ordered by status (Active first).
    """
    try:
        response = (
            get_client()
            .table("subscriptions")
            .select("*")
            .eq("customer_id", customer_id)
            .order("status")
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception("get_subscriptions_failed", customer_id=customer_id)
        return []


def get_active_subscription_by_email(email: str) -> dict[str, Any] | None:
    """Get the active subscription for a customer by email.

    Returns the active subscription (or most recent if none active),
    along with customer info and subscription count.

    Args:
        email: Customer email address.

    Returns:
        Dict with customer info, subscription details, and count, or None.
    """
    customer = lookup_customer(email)
    if not customer:
        return None

    subs = get_subscriptions_by_customer(customer["id"])
    if not subs:
        return {
            "found": True,
            "customer": customer,
            "subscription": None,
            "subscriptions_count": 0,
        }

    # Prefer Active subscription
    active = next((s for s in subs if s.get("status") == "Active"), None)
    chosen = active or subs[0]

    return {
        "found": True,
        "customer": customer,
        "subscription": chosen,
        "subscriptions_count": len(subs),
    }


def get_orders_by_customer(
    customer_id: int, limit: int = 20,
) -> list[dict[str, Any]]:
    """Get recent orders for a customer.

    Args:
        customer_id: The customer's internal ID.
        limit: Max number of orders to return.

    Returns:
        List of order records, newest first.
    """
    try:
        response = (
            get_client()
            .table("orders")
            .select("*")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception("get_orders_failed", customer_id=customer_id)
        return []


def get_orders_by_subscription(
    subscription_id: int, limit: int = 20,
) -> list[dict[str, Any]]:
    """Get orders for a specific subscription.

    Args:
        subscription_id: The subscription's internal ID.
        limit: Max number of orders to return.

    Returns:
        List of order records, newest first.
    """
    try:
        response = (
            get_client()
            .table("orders")
            .select("*")
            .eq("subscription_id", subscription_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception(
            "get_orders_by_subscription_failed",
            subscription_id=subscription_id,
        )
        return []


def get_payment_history_by_email(
    email: str, months: int = 6,
) -> dict[str, Any] | None:
    """Get payment history for a customer.

    Args:
        email: Customer email address.
        months: Number of months of history (used to limit results).

    Returns:
        Dict with payments list and next charge info, or None.
    """
    customer = lookup_customer(email)
    if not customer:
        return None

    subs = get_subscriptions_by_customer(customer["id"])
    active_sub = (
        next((s for s in subs if s.get("status") == "Active"), None)
        if subs
        else None
    )

    orders = get_orders_by_customer(customer["id"], limit=months * 2)

    payments = []
    for order in orders:
        if order.get("payment_date_actual"):
            payments.append({
                "date": order["payment_date_actual"],
                "amount": order.get("price"),
                "currency": order.get("price_currency", "USD"),
                "box_name": order.get("box_name"),
                "box_sequence": order.get("box_sequence"),
                "order_type": order.get("order_type"),
                "invoice": order.get("invoice"),
            })

    return {
        "found": True,
        "customer_email": customer["email"],
        "payments": payments[:months],
        "next_payment_date": (
            active_sub.get("next_payment_date") if active_sub else None
        ),
        "payment_method": (
            active_sub.get("payment_method") if active_sub else None
        ),
        "payment_method_id": (
            active_sub.get("payment_method_id") if active_sub else None
        ),
    }


def get_tracking_by_email(email: str) -> dict[str, Any] | None:
    """Get the most recent tracking info for a customer.

    Finds the customer's most recent order with a tracking number,
    then looks up the tracking event.

    Args:
        email: Customer email address.

    Returns:
        Dict with tracking details, or None if customer not found.
    """
    customer = lookup_customer(email)
    if not customer:
        return None

    orders = get_orders_by_customer(customer["id"], limit=10)
    tracked_order = next(
        (o for o in orders if o.get("tracking_number")),
        None,
    )

    if not tracked_order:
        return {
            "found": True,
            "customer_email": customer["email"],
            "tracking": None,
            "message": "No recent shipment with tracking found.",
        }

    tracking_number = tracked_order["tracking_number"]
    try:
        response = (
            get_client()
            .table("tracking_events")
            .select("*")
            .eq("tracking_number", tracking_number)
            .limit(1)
            .execute()
        )
        tracking = response.data[0] if response.data else None
    except Exception:
        logger.exception("get_tracking_failed", tracking_number=tracking_number)
        tracking = None

    return {
        "found": True,
        "customer_email": customer["email"],
        "tracking_number": tracking_number,
        "order": {
            "box_name": tracked_order.get("box_name"),
            "box_sequence": tracked_order.get("box_sequence"),
            "shipping_date": tracked_order.get("shipping_date"),
        },
        "tracking": tracking,
    }


def get_customer_history_by_email(email: str) -> dict[str, Any] | None:
    """Get comprehensive customer history for retention analysis.

    Includes subscription info, order count, tenure, and recent orders.

    Args:
        email: Customer email address.

    Returns:
        Dict with customer profile, subscription, and order history.
    """
    customer = lookup_customer(email)
    if not customer:
        return None

    subs = get_subscriptions_by_customer(customer["id"])
    active_sub = (
        next((s for s in subs if s.get("status") == "Active"), None)
        if subs
        else None
    )
    orders = get_orders_by_customer(customer["id"], limit=50)

    sub_orders = [o for o in orders if o.get("order_type") == "subscription"]
    one_time_orders = [o for o in orders if o.get("order_type") == "one_time"]

    return {
        "found": True,
        "customer": {
            "email": customer["email"],
            "name": customer.get("name"),
            "customer_number": customer.get("customer_number"),
        },
        "subscription": {
            "status": active_sub.get("status") if active_sub else "none",
            "frequency": active_sub.get("frequency") if active_sub else None,
            "start_date": active_sub.get("start_date") if active_sub else None,
            "no_alcohol": active_sub.get("no_alcohol") if active_sub else None,
            "no_honey": active_sub.get("no_honey") if active_sub else None,
        } if subs else None,
        "orders_summary": {
            "total_subscription_boxes": len(sub_orders),
            "total_one_time_orders": len(one_time_orders),
            "recent_orders": [
                {
                    "box_name": o.get("box_name"),
                    "box_sequence": o.get("box_sequence"),
                    "payment_date": o.get("payment_date_actual"),
                    "tracking_number": o.get("tracking_number"),
                }
                for o in orders[:5]
            ],
        },
        "subscriptions_count": len(subs),
    }
