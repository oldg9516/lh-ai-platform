"""Unit tests for agents/response_assembler.py — deterministic response assembly."""

from agents.response_assembler import (
    assemble_response,
    _strip_existing_greeting,
    _is_system_response,
)


class TestAssembleResponse:
    """Test response assembly with greeting, opener, body, closer, sign-off."""

    def test_basic_assembly(self):
        result = assemble_response(
            raw_response="Your package is on the way.",
            customer_name="Sarah",
            category="shipping_or_delivery_question",
            session_id="test-1",
        )
        assert "<div>Dear Sarah,</div>" in result
        assert "Your package is on the way." in result
        assert "Warm regards,<br>Lev Haolam Support Team" in result

    def test_contains_opener(self):
        result = assemble_response(
            raw_response="Body text here.",
            customer_name="John",
            category="payment_question",
            session_id="test-2",
        )
        # Should have 5 divs: greeting, opener, body, closer, sign-off
        assert result.count("<div>") >= 5

    def test_deterministic_same_session(self):
        """Same session_id should always produce the same opener/closer."""
        r1 = assemble_response("Body.", "Name", "gratitude", "sess-abc")
        r2 = assemble_response("Body.", "Name", "gratitude", "sess-abc")
        assert r1 == r2

    def test_variety_different_sessions(self):
        """Different session_ids should sometimes produce different openers."""
        results = set()
        for i in range(20):
            r = assemble_response("Body.", "Name", "shipping_or_delivery_question", f"sess-{i}")
            results.add(r)
        # With 20 different sessions, we should get at least 2 variations
        assert len(results) >= 2

    def test_system_response_not_wrapped(self):
        result = assemble_response(
            raw_response="I'm connecting you with a support agent who can better assist you.",
            customer_name="John",
            category="unknown",
            session_id="test-3",
        )
        assert "<div>Dear John,</div>" not in result
        assert "connecting you with a support agent" in result

    def test_client_fallback_name(self):
        result = assemble_response(
            raw_response="We are looking into it.",
            customer_name="Client",
            category="shipping_or_delivery_question",
            session_id="test-4",
        )
        assert "<div>Dear Client,</div>" in result

    def test_retention_opener(self):
        result = assemble_response(
            raw_response="We understand your request.",
            customer_name="David",
            category="retention_primary_request",
            session_id="test-5",
        )
        assert "<div>Dear David,</div>" in result
        # Should have a retention-specific opener (not shipping)
        assert "sorry" in result.lower() or "appreciate" in result.lower() or "thank" in result.lower()

    def test_damage_opener(self):
        result = assemble_response(
            raw_response="Please send photos.",
            customer_name="Rachel",
            category="damaged_or_leaking_item_report",
            session_id="test-6",
        )
        assert "sorry" in result.lower() or "apologize" in result.lower()


class TestStripGreeting:
    """Test removal of duplicate AI-generated greetings."""

    def test_strips_dear_name(self):
        result = _strip_existing_greeting("Dear Sarah,\nYour package is here.", "Sarah")
        assert result == "Your package is here."

    def test_strips_hi_name(self):
        result = _strip_existing_greeting("Hi John,\nWe are on it.", "John")
        assert result == "We are on it."

    def test_strips_hello_name(self):
        result = _strip_existing_greeting("Hello Client,\nThank you.", "Client")
        assert result == "Thank you."

    def test_strips_generic_greeting(self):
        result = _strip_existing_greeting("Dear Customer,\nWe received your request.", "Sarah")
        assert result == "We received your request."

    def test_no_greeting_unchanged(self):
        result = _strip_existing_greeting("Your package is on the way.", "Sarah")
        assert result == "Your package is on the way."


class TestIsSystemResponse:
    """Test detection of system/escalation responses."""

    def test_escalation_response(self):
        assert _is_system_response("I'm connecting you with a support agent who can better assist you.") is True

    def test_error_response(self):
        assert _is_system_response("I'm having trouble processing your request.") is True

    def test_normal_response(self):
        assert _is_system_response("Your package will arrive in 2-3 weeks.") is False
