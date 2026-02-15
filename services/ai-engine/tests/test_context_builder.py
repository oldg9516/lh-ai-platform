"""Tests for Rich Context Builder.

Phase 7 Day 4: Verify that context builder creates comprehensive
customer context from multiple database sources.
"""

import pytest
from unittest.mock import patch

from agents.context_builder import (
    build_customer_context,
    build_conversation_context,
    build_full_context,
)


class TestCustomerContext:
    """Test customer context building from database."""

    @pytest.mark.asyncio
    @patch("agents.context_builder.lookup_customer")
    @patch("agents.context_builder.get_active_subscription_by_email")
    @patch("agents.context_builder.get_orders_by_subscription")
    @patch("agents.context_builder.get_customer_history_by_email")
    async def test_build_full_customer_context(
        self, mock_history, mock_orders, mock_subscription, mock_customer
    ):
        """Should build complete context with all sections."""
        # Mock customer data
        mock_customer.return_value = {
            "customer_id": 1,
            "name": "Sarah Cohen",
            "join_date": "2022-03-15",
            "total_orders": 24,
            "ltv": 1440.00,
        }

        mock_subscription.return_value = {
            "subscription_id": 101,
            "frequency": "monthly",
            "status": "active",
            "next_charge_date": "2024-05-15",
        }

        mock_orders.return_value = [
            {"order_date": "2024-04-01", "amount": 60.00},
            {"order_date": "2024-03-01", "amount": 60.00},
            {"order_date": "2024-02-01", "amount": 60.00},
        ]

        mock_history.return_value = [
            {"date": "2024-04-10", "subject": "Shipping question"},
            {"date": "2024-03-20", "subject": "Payment inquiry"},
        ]

        # Build context
        context = await build_customer_context("sarah.cohen@example.com")

        # Verify all sections present
        assert "CUSTOMER PROFILE" in context
        assert "Sarah Cohen" in context
        assert "2022-03-15" in context
        assert "24" in context  # total_orders
        assert "$1440.00" in context  # ltv

        assert "ACTIVE SUBSCRIPTION" in context
        assert "monthly" in context
        assert "active" in context
        assert "2024-05-15" in context

        assert "RECENT ORDERS" in context
        assert "2024-04-01" in context
        assert "$60.00" in context

        assert "SUPPORT HISTORY" in context
        assert "Shipping question" in context

    @pytest.mark.asyncio
    async def test_build_context_with_no_email(self):
        """Should return empty string when no email provided."""
        context = await build_customer_context(None)
        assert context == ""

    @pytest.mark.asyncio
    @patch("agents.context_builder.lookup_customer")
    async def test_build_context_customer_not_found(self, mock_customer):
        """Should handle customer not found gracefully."""
        mock_customer.return_value = None

        context = await build_customer_context("unknown@example.com")

        assert "not found in database" in context
        assert "Limited information available" in context

    @pytest.mark.asyncio
    @patch("agents.context_builder.lookup_customer")
    async def test_build_context_handles_errors(self, mock_customer):
        """Should handle database errors gracefully."""
        mock_customer.side_effect = Exception("Database connection failed")

        context = await build_customer_context("test@example.com")

        assert "CONTEXT BUILDER ERROR" in context
        assert "Proceeding with limited information" in context


class TestConversationContext:
    """Test conversation history context building."""

    def test_build_conversation_context(self):
        """Should format conversation history correctly."""
        history = [
            {"role": "user", "content": "Where is my package?"},
            {"role": "assistant", "content": "Let me check your tracking information..."},
            {"role": "user", "content": "Thank you!"},
        ]

        context = build_conversation_context(history)

        assert "CONVERSATION HISTORY" in context
        assert "Customer: Where is my package?" in context
        assert "Agent: Let me check your tracking" in context
        assert "Customer: Thank you!" in context

    def test_truncates_long_messages(self):
        """Should truncate messages longer than 500 characters."""
        long_message = "x" * 600
        history = [
            {"role": "user", "content": long_message},
        ]

        context = build_conversation_context(history)

        assert len(context) < len(long_message)
        assert "..." in context

    def test_limits_to_max_turns(self):
        """Should limit history to max_turns."""
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(20)
        ]

        context = build_conversation_context(history, max_turns=3)

        # Should only include last 6 messages (3 turns * 2 messages)
        assert "Message 14" in context or "Message 15" in context
        assert "Message 0" not in context

    def test_empty_history(self):
        """Should return empty string for empty history."""
        context = build_conversation_context([])
        assert context == ""


class TestFullContext:
    """Test complete context assembly."""

    @pytest.mark.asyncio
    @patch("agents.context_builder.build_customer_context")
    async def test_build_full_context_all_sources(self, mock_customer_ctx):
        """Should combine all context sources."""
        mock_customer_ctx.return_value = "Customer: Sarah Cohen"

        conversation_history = [
            {"role": "user", "content": "Hello"},
        ]

        outstanding_info = {
            "is_outstanding": True,
            "trigger": "repeated_complaint",
            "confidence": "high",
        }

        context = await build_full_context(
            customer_email="sarah@example.com",
            conversation_history=conversation_history,
            outstanding_info=outstanding_info,
        )

        assert "CUSTOMER CONTEXT" in context
        assert "Customer: Sarah Cohen" in context
        assert "CONVERSATION HISTORY" in context
        assert "Customer: Hello" in context
        assert "OUTSTANDING ISSUE DETECTED" in context
        assert "repeated_complaint" in context

    @pytest.mark.asyncio
    async def test_build_full_context_minimal(self):
        """Should work with minimal inputs."""
        context = await build_full_context(customer_email=None)
        assert context == ""


class TestRealCustomerContext:
    """Test with real database (integration test)."""

    @pytest.mark.asyncio
    async def test_real_customer_from_db(self):
        """Should build context for real customer from database."""
        # fedaka42020@gmail.com exists in imported test data
        context = await build_customer_context("fedaka42020@gmail.com")

        # Should have customer data
        assert context != ""
        # Should have profile or warning
        assert ("CUSTOMER PROFILE" in context) or ("not found" in context)
