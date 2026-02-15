"""Rich Context Builder for Support Agents.

Phase 7 Day 4: Builds comprehensive customer context from multiple sources
for injection into agent instructions.

Context includes:
- Customer profile (name, join date, LTV)
- Active subscription (frequency, next charge, status)
- Recent orders (last 3)
- Outstanding issues (from outstanding detection)
- Conversation history (smart truncation)
"""

from datetime import datetime
import structlog

from database.customer_queries import (
    lookup_customer,
    get_active_subscription_by_email,
    get_orders_by_subscription,
    get_customer_history_by_email,
)

logger = structlog.get_logger()


async def build_customer_context(customer_email: str | None) -> str:
    """Build rich customer context from database.

    Args:
        customer_email: Customer email for database lookups.

    Returns:
        Formatted context string for agent instructions.
        Empty string if no email provided or customer not found.
    """
    if not customer_email:
        return ""

    context_parts = []

    try:
        # 1. Customer Profile
        customer = lookup_customer(customer_email)
        if customer and customer.get("customer_id"):
            name = customer.get("name", "Unknown")
            join_date = customer.get("join_date", "Unknown")
            total_orders = customer.get("total_orders", 0)
            ltv = customer.get("ltv", 0.0)

            context_parts.append(
                f"📋 CUSTOMER PROFILE:\n"
                f"Name: {name}\n"
                f"Member since: {join_date}\n"
                f"Total orders: {total_orders}\n"
                f"Lifetime value: ${ltv:.2f}"
            )

            # 2. Active Subscription
            subscription = get_active_subscription_by_email(customer_email)
            if subscription and subscription.get("subscription_id"):
                frequency = subscription.get("frequency", "Unknown")
                status = subscription.get("status", "Unknown")
                next_charge = subscription.get("next_charge_date", "Unknown")

                context_parts.append(
                    f"\n📦 ACTIVE SUBSCRIPTION:\n"
                    f"Frequency: {frequency}\n"
                    f"Status: {status}\n"
                    f"Next charge: {next_charge}"
                )

                # 3. Recent Orders (last 3)
                subscription_id = subscription.get("subscription_id")
                if subscription_id:
                    orders = get_orders_by_subscription(subscription_id, limit=3)
                    if orders:
                        order_lines = []
                        for order in orders[:3]:
                            order_date = order.get("order_date", "Unknown")
                            amount = order.get("amount", 0.0)
                            order_lines.append(f"  - {order_date}: ${amount:.2f}")

                        context_parts.append(
                            f"\n📜 RECENT ORDERS (last 3):\n"
                            + "\n".join(order_lines)
                        )

            # 4. Support History
            support_history = get_customer_history_by_email(customer_email, limit=3)
            if support_history:
                history_lines = []
                for item in support_history[:3]:
                    date = item.get("date", "Unknown")
                    subject = item.get("subject", "N/A")
                    history_lines.append(f"  - {date}: {subject[:50]}")

                context_parts.append(
                    f"\n💬 RECENT SUPPORT HISTORY (last 3):\n"
                    + "\n".join(history_lines)
                )

        else:
            # Customer not found
            context_parts.append(
                f"⚠️ CUSTOMER STATUS: Email {customer_email} not found in database.\n"
                f"Limited information available. Tools may not work without valid customer."
            )

    except Exception as e:
        logger.error(
            "context_builder_error",
            email=customer_email,
            error=str(e),
        )
        # Graceful degradation - return partial context
        context_parts.append(
            f"⚠️ CONTEXT BUILDER ERROR: Could not load full customer context.\n"
            f"Proceeding with limited information."
        )

    if not context_parts:
        return ""

    # Join all parts with separator
    full_context = "\n".join(context_parts)

    logger.info(
        "customer_context_built",
        email=customer_email,
        context_sections=len(context_parts),
        context_length=len(full_context),
    )

    return full_context


def build_conversation_context(history: list[dict], max_turns: int = 5) -> str:
    """Build conversation history context with smart truncation.

    Args:
        history: List of conversation messages.
        max_turns: Maximum number of turns to include (default 5).

    Returns:
        Formatted conversation history string.
    """
    if not history:
        return ""

    # Take last N turns (each turn = user + assistant)
    recent_history = history[-max_turns * 2:] if len(history) > max_turns * 2 else history

    history_lines = ["💬 CONVERSATION HISTORY:"]

    for msg in recent_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Truncate long messages (keep first 500 chars)
        if len(content) > 500:
            content = content[:500] + "..."

        if role == "user":
            history_lines.append(f"Customer: {content}")
        elif role == "assistant":
            history_lines.append(f"Agent: {content}")

    return "\n".join(history_lines)


async def build_full_context(
    customer_email: str | None,
    conversation_history: list[dict] | None = None,
    outstanding_info: dict | None = None,
) -> str:
    """Build complete context from all sources.

    Args:
        customer_email: Customer email for database lookups.
        conversation_history: Previous conversation messages.
        outstanding_info: Outstanding detection result.

    Returns:
        Complete formatted context for agent.
    """
    context_sections = []

    # 1. Customer context (profile + subscription + orders)
    customer_ctx = await build_customer_context(customer_email)
    if customer_ctx:
        context_sections.append(customer_ctx)

    # 2. Conversation history
    if conversation_history:
        conv_ctx = build_conversation_context(conversation_history)
        if conv_ctx:
            context_sections.append(f"\n{conv_ctx}")

    # 3. Outstanding issues
    if outstanding_info and outstanding_info.get("is_outstanding"):
        trigger = outstanding_info.get("trigger", "unknown")
        confidence = outstanding_info.get("confidence", "unknown")
        context_sections.append(
            f"\n⚠️ OUTSTANDING ISSUE DETECTED:\n"
            f"Trigger: {trigger}\n"
            f"Confidence: {confidence}\n"
            f"Handle with extra care and empathy."
        )

    if not context_sections:
        return ""

    # Wrap in clear markers
    full_context = (
        "\n" + "="*60 + "\n"
        "CUSTOMER CONTEXT (for your reference)\n"
        + "="*60 + "\n"
        + "\n".join(context_sections)
        + "\n" + "="*60 + "\n"
    )

    return full_context
