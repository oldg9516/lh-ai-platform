"""Unit tests for agents/outstanding.py — Outstanding Detection Agent."""

from agents.outstanding import OutstandingOutput, _load_outstanding_rules


class TestOutstandingOutput:
    """Verify OutstandingOutput model defaults and constraints."""

    def test_default_values(self):
        output = OutstandingOutput()
        assert output.is_outstanding is False
        assert output.trigger == "none"
        assert output.confidence == "high"

    def test_outstanding_case(self):
        output = OutstandingOutput(
            is_outstanding=True,
            trigger="repeated_complaint",
            confidence="high",
        )
        assert output.is_outstanding is True
        assert output.trigger == "repeated_complaint"

    def test_low_confidence(self):
        output = OutstandingOutput(
            is_outstanding=True,
            trigger="edge_case",
            confidence="low",
        )
        assert output.confidence == "low"

    def test_detection_error_fallback(self):
        output = OutstandingOutput(is_outstanding=False, trigger="detection_error")
        assert output.is_outstanding is False
        assert output.trigger == "detection_error"


class TestLoadOutstandingRules:
    """Verify rule loading produces valid instructions."""

    def test_base_instructions_present(self):
        """Even if DB is unreachable, base instructions are returned."""
        rules = _load_outstanding_rules("shipping_or_delivery_question")
        assert len(rules) >= 5
        assert any("Outstanding" in r for r in rules)
        assert any("hard rule" in r.lower() for r in rules)

    def test_returns_list_of_strings(self):
        rules = _load_outstanding_rules("gratitude")
        assert isinstance(rules, list)
        assert all(isinstance(r, str) for r in rules)
