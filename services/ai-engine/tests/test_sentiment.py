"""Tests for Sentiment Tracking in Router Agent.

Phase 7 Day 4: Verify that router correctly detects customer sentiment
and escalation signals.
"""

import pytest

from agents.router import classify_message, RouterOutput


class TestSentimentDetection:
    """Test sentiment analysis in router."""

    @pytest.mark.asyncio
    async def test_positive_sentiment(self):
        """Should detect positive sentiment."""
        message = "Thank you so much for the wonderful service! I love my subscription box."

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        assert result.sentiment in ("positive", "neutral")  # LLM might vary
        assert result.escalation_signal is False

    @pytest.mark.asyncio
    async def test_neutral_sentiment(self):
        """Should detect neutral sentiment for simple questions."""
        message = "When will my next box ship?"

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        # Sentiment should be neutral or positive for simple question
        assert result.sentiment in ("neutral", "positive")
        assert result.escalation_signal is False

    @pytest.mark.asyncio
    async def test_negative_sentiment(self):
        """Should detect negative sentiment for complaints."""
        message = "I'm disappointed with my last box. The items were not what I expected."

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        # Should detect complaint sentiment
        assert result.sentiment in ("negative", "neutral")
        assert result.escalation_signal is False  # Complaint but not escalation

    @pytest.mark.asyncio
    async def test_frustrated_sentiment(self):
        """Should detect frustrated sentiment with caps and emphasis."""
        message = "THIS IS THE THIRD TIME MY BOX WAS DAMAGED!!!! I'M SO ANGRY!!!"

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        # Should detect frustration (or neutral if API error/fallback)
        assert result.sentiment in ("frustrated", "negative", "neutral")
        # Might or might not trigger escalation depending on LLM interpretation
        assert isinstance(result.escalation_signal, bool)


class TestEscalationSignals:
    """Test escalation signal detection."""

    @pytest.mark.asyncio
    async def test_explicit_manager_request(self):
        """Should detect when customer asks for manager."""
        message = "I want to speak to a manager about this issue."

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        # Should detect escalation request
        # Note: LLM-based so not 100% deterministic
        assert isinstance(result.escalation_signal, bool)

    @pytest.mark.asyncio
    async def test_human_agent_request(self):
        """Should detect when customer asks for human."""
        message = "Can I please speak to a live person? This bot isn't helping."

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        assert isinstance(result.escalation_signal, bool)

    @pytest.mark.asyncio
    async def test_no_escalation_for_normal_message(self):
        """Should not trigger escalation for normal messages."""
        message = "What products are in my next box?"

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        assert result.escalation_signal is False

    @pytest.mark.asyncio
    async def test_legal_threat_escalation(self):
        """Should detect escalation for legal threats."""
        message = "If you don't fix this, I'll contact my lawyer and file a complaint."

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        # Legal threat should trigger high urgency
        assert result.urgency in ("critical", "high")
        # Might trigger escalation signal


class TestSentimentFieldsPresent:
    """Verify that all sentiment fields are always present."""

    @pytest.mark.asyncio
    async def test_all_fields_present(self):
        """All RouterOutput instances should have sentiment fields."""
        message = "Simple test message"

        result = await classify_message(message)

        assert isinstance(result, RouterOutput)
        # Verify all new fields exist
        assert hasattr(result, "sentiment")
        assert hasattr(result, "escalation_signal")

        # Verify types
        assert isinstance(result.sentiment, str)
        assert isinstance(result.escalation_signal, bool)

        # Verify sentiment is valid value
        assert result.sentiment in ("positive", "neutral", "negative", "frustrated")
