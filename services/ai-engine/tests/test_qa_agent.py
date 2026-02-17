"""Unit tests for agents/qa_agent.py — QA Agent."""

from agents.eval_gate import EvalCheck, fast_safety_check
from agents.qa_agent import QAOutput, _build_qa_prompt


# --- Model Tests ---


class TestQAOutput:
    """Verify QAOutput model."""

    def test_send_decision(self):
        output = QAOutput(decision="send", confidence="high")
        assert output.decision == "send"
        assert output.feedback is None
        assert output.override_reason is None

    def test_refine_decision_with_feedback(self):
        output = QAOutput(
            decision="refine",
            confidence="medium",
            feedback="Tone is too robotic. Add more warmth.",
        )
        assert output.decision == "refine"
        assert output.feedback is not None
        assert "warmth" in output.feedback

    def test_draft_decision(self):
        output = QAOutput(
            decision="draft",
            confidence="high",
            override_reason="Safety violation detected",
        )
        assert output.decision == "draft"
        assert output.override_reason is not None

    def test_escalate_decision(self):
        output = QAOutput(decision="escalate", confidence="high")
        assert output.decision == "escalate"

    def test_with_checks(self):
        output = QAOutput(
            decision="send",
            confidence="high",
            checks=[
                EvalCheck(name="safety", passed=True, score=1.0, detail=""),
                EvalCheck(name="tone", passed=True, score=0.9, detail=""),
            ],
        )
        assert len(output.checks) == 2
        assert all(c.passed for c in output.checks)


# --- Regex Fast-Fail (reused from eval_gate) ---


class TestQAFastSafetyCheck:
    """QA reuses fast_safety_check from eval_gate — verify it works."""

    def test_safe_response(self):
        is_safe, violation = fast_safety_check(
            "I'd be happy to help you track your package!"
        )
        assert is_safe is True
        assert violation is None

    def test_catches_cancellation(self):
        is_safe, violation = fast_safety_check(
            "I've cancelled your subscription as requested."
        )
        assert is_safe is False
        assert violation == "confirmed_cancellation"

    def test_catches_pause_confirmation(self):
        is_safe, violation = fast_safety_check(
            "Your subscription has been paused for 3 months."
        )
        assert is_safe is False
        assert violation == "confirmed_pause"

    def test_catches_refund(self):
        is_safe, violation = fast_safety_check(
            "I've processed a refund for your last order."
        )
        assert is_safe is False
        assert violation == "confirmed_refund"


# --- Prompt Builder ---


class TestBuildQAPrompt:
    """Verify QA prompt construction."""

    def test_basic_prompt(self):
        prompt = _build_qa_prompt(
            customer_message="Where is my package?",
            ai_response="Your package is on the way!",
            category="shipping_or_delivery_question",
            is_outstanding=False,
        )
        assert "CATEGORY: shipping_or_delivery_question" in prompt
        assert "Where is my package?" in prompt
        assert "Your package is on the way!" in prompt
        assert "ATTEMPT: 1" in prompt

    def test_outstanding_prompt(self):
        prompt = _build_qa_prompt(
            customer_message="Test",
            ai_response="Response",
            category="shipping_or_delivery_question",
            is_outstanding=True,
        )
        assert "OUTSTANDING: True" in prompt
        assert "extra strict" in prompt

    def test_retry_prompt(self):
        prompt = _build_qa_prompt(
            customer_message="Test",
            ai_response="Revised response",
            category="shipping_or_delivery_question",
            is_outstanding=False,
            attempt=2,
            previous_feedback="Add tracking number to the response.",
        )
        assert "ATTEMPT: 2" in prompt
        assert "RETRY" in prompt
        assert "Do NOT use 'refine' again" in prompt
        assert "Add tracking number" in prompt

    def test_tools_context(self):
        prompt = _build_qa_prompt(
            customer_message="Test",
            ai_response="Response",
            category="shipping_or_delivery_question",
            is_outstanding=False,
            tools_available=["track_package", "get_subscription"],
        )
        assert "track_package" in prompt
        assert "get_subscription" in prompt

    def test_first_attempt_no_retry_warning(self):
        prompt = _build_qa_prompt(
            customer_message="Test",
            ai_response="Response",
            category="shipping_or_delivery_question",
            is_outstanding=False,
            attempt=1,
        )
        assert "RETRY" not in prompt
