"""Unit tests for guardrails/safety.py — red lines + subscription safety."""

from guardrails.safety import check_red_lines, check_subscription_safety


# --- Red Line Tests ---


class TestRedLines:
    """Pre-processing safety check: detect dangerous customer messages."""

    def test_death_threat(self):
        result = check_red_lines("I will kill you")
        assert result["is_flagged"] is True
        assert result["trigger"] == "death_threat"

    def test_legal_threat(self):
        result = check_red_lines("I will sue your company")
        assert result["is_flagged"] is True
        assert result["trigger"] == "legal_threat"

    def test_bank_dispute(self):
        result = check_red_lines("I will dispute the charge with my bank")
        assert result["is_flagged"] is True
        assert result["trigger"] == "bank_dispute"

    def test_self_harm(self):
        result = check_red_lines("I want to end my life")
        assert result["is_flagged"] is True
        assert result["trigger"] == "self_harm"

    def test_violence_threat(self):
        result = check_red_lines("I have a bomb")
        assert result["is_flagged"] is True
        assert result["trigger"] == "violence_threat"

    def test_safe_message(self):
        result = check_red_lines("Where is my package?")
        assert result["is_flagged"] is False
        assert result["trigger"] is None

    def test_safe_cancel_request(self):
        result = check_red_lines("I want to cancel my subscription")
        assert result["is_flagged"] is False

    def test_safe_complaint(self):
        result = check_red_lines("This is terrible service, I am very unhappy")
        assert result["is_flagged"] is False

    def test_case_insensitive(self):
        result = check_red_lines("I WILL SUE YOU")
        assert result["is_flagged"] is True
        assert result["trigger"] == "legal_threat"

    def test_lawyer_mention(self):
        result = check_red_lines("My lawyer will contact you")
        assert result["is_flagged"] is True
        assert result["trigger"] == "legal_threat"

    def test_chargeback(self):
        result = check_red_lines("I filed a chargeback")
        assert result["is_flagged"] is True
        assert result["trigger"] == "bank_dispute"


# --- Subscription Safety Tests ---


class TestSubscriptionSafety:
    """Post-processing safety check: ensure AI never confirms cancel/pause/refund."""

    def test_confirmed_cancellation(self):
        result = check_subscription_safety("I have cancelled your subscription.")
        assert result["is_safe"] is False
        assert result["violation"] == "confirmed_cancellation"

    def test_confirmed_pause(self):
        result = check_subscription_safety("I have paused your subscription for you.")
        assert result["is_safe"] is False
        assert result["violation"] == "confirmed_pause"

    def test_confirmed_refund(self):
        result = check_subscription_safety("I have processed a refund for you.")
        assert result["is_safe"] is False
        assert result["violation"] == "confirmed_refund"

    def test_safe_redirect_cancel(self):
        result = check_subscription_safety(
            "To cancel, please visit our cancellation page."
        )
        assert result["is_safe"] is True

    def test_safe_redirect_pause(self):
        result = check_subscription_safety(
            "To pause your subscription, please contact our team."
        )
        assert result["is_safe"] is True

    def test_safe_normal_response(self):
        result = check_subscription_safety(
            "Your package is on its way and should arrive within 2-3 weeks."
        )
        assert result["is_safe"] is True

    def test_subscription_is_now_canceled(self):
        result = check_subscription_safety("Your subscription is now canceled.")
        assert result["is_safe"] is False
        assert result["violation"] == "confirmed_cancellation"

    def test_refund_was_issued(self):
        result = check_subscription_safety("Your refund was issued successfully.")
        assert result["is_safe"] is False
        assert result["violation"] == "confirmed_refund"
