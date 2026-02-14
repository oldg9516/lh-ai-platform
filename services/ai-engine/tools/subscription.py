"""Subscription modification tools (stubs).

Write operations return awaiting_customer_confirmation status.
Actual execution requires explicit customer confirmation (Phase 6 HITL).
Eval gate catches any AI response that falsely confirms these actions.
"""

import json

import structlog

logger = structlog.get_logger()


def change_frequency(
    customer_email: str,
    new_frequency: str,
) -> str:
    """Request a subscription frequency change for the customer.

    Use this tool when a customer wants to switch between monthly,
    bi-monthly, or quarterly delivery. The change requires customer
    confirmation before it takes effect. NEVER tell the customer
    the frequency has already been changed.

    Args:
        customer_email: The customer's email address.
        new_frequency: Desired frequency: 'monthly', 'bi-monthly', or 'quarterly'.

    Returns:
        JSON string with the proposed change awaiting customer confirmation.
    """
    logger.info("tool_called", tool="change_frequency", email=customer_email, new_frequency=new_frequency)
    return json.dumps({
        "action": "frequency_change",
        "customer_email": customer_email,
        "current_frequency": "monthly",
        "requested_frequency": new_frequency,
        "status": "awaiting_customer_confirmation",
        "confirmation_required": True,
        "summary": f"Change delivery frequency from monthly to {new_frequency}",
    })


def skip_month(
    customer_email: str,
    month: str = "next",
) -> str:
    """Request to skip the next month's delivery.

    Use this tool when a customer wants to skip their next box.
    The skip request requires customer confirmation. NEVER tell
    the customer the skip has already been processed.

    Args:
        customer_email: The customer's email address.
        month: Which month to skip. Default 'next' for the upcoming month.

    Returns:
        JSON string with the proposed skip awaiting customer confirmation.
    """
    logger.info("tool_called", tool="skip_month", email=customer_email, month=month)
    return json.dumps({
        "action": "skip_month",
        "customer_email": customer_email,
        "skip_month": "March 2026",
        "status": "awaiting_customer_confirmation",
        "confirmation_required": True,
        "summary": "Skip the March 2026 delivery (no charge for that month)",
    })


def pause_subscription(
    customer_email: str,
    duration_months: int = 1,
) -> str:
    """Request to pause a subscription for a specified duration.

    Use this tool when a customer wants to temporarily pause their
    subscription. The pause requires customer confirmation. NEVER
    tell the customer their subscription has been paused.

    Args:
        customer_email: The customer's email address.
        duration_months: Number of months to pause (1-3).

    Returns:
        JSON string with the proposed pause awaiting customer confirmation.
    """
    logger.info("tool_called", tool="pause_subscription", email=customer_email, duration=duration_months)
    return json.dumps({
        "action": "pause_subscription",
        "customer_email": customer_email,
        "requested_pause_months": duration_months,
        "status": "awaiting_customer_confirmation",
        "confirmation_required": True,
        "summary": f"Pause subscription for {duration_months} month(s)",
    })


def change_address(
    customer_email: str,
    new_address: str,
) -> str:
    """Request a shipping address change for the customer.

    Use this tool when a customer provides a new address or wants
    to change the delivery recipient. The change requires customer
    confirmation before it takes effect. NEVER tell the customer
    the address has already been updated.

    Args:
        customer_email: The customer's email address.
        new_address: The full new shipping address as provided by the customer.

    Returns:
        JSON string with the proposed address change awaiting confirmation.
    """
    logger.info("tool_called", tool="change_address", email=customer_email)
    return json.dumps({
        "action": "address_change",
        "customer_email": customer_email,
        "new_address": new_address,
        "status": "awaiting_customer_confirmation",
        "confirmation_required": True,
        "summary": f"Update shipping address to: {new_address}",
    })
