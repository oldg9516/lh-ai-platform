"""Unit tests for agents/eval_gate.py — Eval Gate Agent."""

from agents.eval_gate import (
    EvalCheck,
    EvalGateOutput,
    fast_safety_check,
    _build_eval_prompt,
)


# --- Model Tests ---


class TestEvalCheck:
    """Verify EvalCheck model."""

    def test_passed_check(self):
        check = EvalCheck(name="safety", passed=True, score=1.0, detail="")
        assert check.passed is True
        assert check.score == 1.0

    def test_failed_check(self):
        check = EvalCheck(name="safety", passed=False, score=0.0, detail="Confirmed cancel")
        assert check.passed is False
        assert check.detail == "Confirmed cancel"

    def test_partial_score(self):
        check = EvalCheck(name="tone", passed=True, score=0.8, detail="Slightly robotic")
        assert check.score == 0.8


class TestEvalGateOutput:
    """Verify EvalGateOutput model."""

    def test_send_decision(self):
        output = EvalGateOutput(decision="send", confidence="high")
        assert output.decision == "send"
        assert output.checks == []
        assert output.override_reason is None

    def test_draft_decision(self):
        output = EvalGateOutput(
            decision="draft",
            confidence="high",
            override_reason="Fast-fail regex: confirmed_cancellation",
            checks=[
                EvalCheck(name="safety", passed=False, score=0.0, detail="regex violation"),
            ],
        )
        assert output.decision == "draft"
        assert len(output.checks) == 1
        assert output.checks[0].passed is False

    def test_escalate_decision(self):
        output = EvalGateOutput(decision="escalate", confidence="medium")
        assert output.decision == "escalate"


# --- Fast Safety Check (regex) ---


class TestFastSafetyCheck:
    """Tier 1: regex-based instant checks (same patterns as check_subscription_safety)."""

    def test_confirmed_cancellation(self):
        is_safe, violation = fast_safety_check("I have cancelled your subscription.")
        assert is_safe is False
        assert violation == "confirmed_cancellation"

    def test_subscription_is_now_canceled(self):
        is_safe, violation = fast_safety_check("Your subscription is now canceled.")
        assert is_safe is False
        assert violation == "confirmed_cancellation"

    def test_confirmed_pause(self):
        is_safe, violation = fast_safety_check("I have paused your subscription for you.")
        assert is_safe is False
        assert violation == "confirmed_pause"

    def test_subscription_suspended(self):
        is_safe, violation = fast_safety_check("Your subscription has been suspended.")
        assert is_safe is False
        assert violation == "confirmed_pause"

    def test_confirmed_refund(self):
        is_safe, violation = fast_safety_check("I have processed a refund for you.")
        assert is_safe is False
        assert violation == "confirmed_refund"

    def test_refund_issued(self):
        is_safe, violation = fast_safety_check("Your refund was issued successfully.")
        assert is_safe is False
        assert violation == "confirmed_refund"

    def test_safe_redirect_cancel(self):
        is_safe, violation = fast_safety_check(
            "To cancel, please visit our cancellation page."
        )
        assert is_safe is True
        assert violation is None

    def test_safe_redirect_pause(self):
        is_safe, violation = fast_safety_check(
            "To pause your subscription, please contact our team."
        )
        assert is_safe is True
        assert violation is None

    def test_safe_normal_response(self):
        is_safe, violation = fast_safety_check(
            "Your package is on its way and should arrive within 2-3 weeks."
        )
        assert is_safe is True
        assert violation is None

    def test_case_insensitive(self):
        is_safe, violation = fast_safety_check("I HAVE CANCELLED YOUR SUBSCRIPTION.")
        assert is_safe is False


# --- Eval Prompt Builder ---


class TestBuildEvalPrompt:
    """Verify prompt construction for LLM eval."""

    def test_basic_prompt(self):
        prompt = _build_eval_prompt(
            customer_message="Where is my order?",
            ai_response="Your order is on the way.",
            category="shipping_or_delivery_question",
            is_outstanding=False,
        )
        assert "CATEGORY: shipping_or_delivery_question" in prompt
        assert "Where is my order?" in prompt
        assert "Your order is on the way." in prompt
        assert "OUTSTANDING: False" in prompt
        assert "extra strict" not in prompt

    def test_outstanding_prompt(self):
        prompt = _build_eval_prompt(
            customer_message="Cancel now!",
            ai_response="I understand.",
            category="retention_primary_request",
            is_outstanding=True,
        )
        assert "OUTSTANDING: True" in prompt
        assert "extra strict" in prompt

    def test_tools_available_included(self):
        prompt = _build_eval_prompt(
            customer_message="Where is my order?",
            ai_response="Your tracking number is LH2026021345IL.",
            category="shipping_or_delivery_question",
            is_outstanding=False,
            tools_available=["get_subscription", "track_package"],
        )
        assert "TOOLS AVAILABLE TO AGENT" in prompt
        assert "get_subscription" in prompt
        assert "track_package" in prompt
        assert "considered accurate" in prompt

    def test_no_tools_no_note(self):
        prompt = _build_eval_prompt(
            customer_message="Thanks!",
            ai_response="You're welcome!",
            category="gratitude",
            is_outstanding=False,
            tools_available=None,
        )
        assert "TOOLS AVAILABLE" not in prompt

    def test_empty_tools_no_note(self):
        prompt = _build_eval_prompt(
            customer_message="Thanks!",
            ai_response="You're welcome!",
            category="gratitude",
            is_outstanding=False,
            tools_available=[],
        )
        assert "TOOLS AVAILABLE" not in prompt
