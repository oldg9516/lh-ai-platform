"""Unit tests for learning/feedback.py — Correction learning pipeline."""

from learning.feedback import CorrectionClassification, CorrectionRecord


# --- CorrectionRecord Model ---


class TestCorrectionRecord:
    """Verify CorrectionRecord model validation."""

    def test_minimal_record(self):
        record = CorrectionRecord(
            category="shipping_or_delivery_question",
            ai_response="Your package is on the way.",
            human_edit="Your package is on the way! Tracking: ABC123.",
            correction_type="completeness",
        )
        assert record.category == "shipping_or_delivery_question"
        assert record.correction_type == "completeness"
        assert record.conversation_id is None
        assert record.session_id is None
        assert record.specific_issue is None
        assert record.key_changes == []

    def test_full_record(self):
        record = CorrectionRecord(
            conversation_id="123",
            session_id="cw_123",
            category="payment_question",
            ai_response="Your payment was received.",
            human_edit="Your payment of $29.99 was received on Jan 5.",
            correction_type="completeness",
            specific_issue="Missing payment amount and date",
            key_changes=["Added amount", "Added date"],
        )
        assert record.conversation_id == "123"
        assert record.session_id == "cw_123"
        assert len(record.key_changes) == 2

    def test_tone_correction(self):
        record = CorrectionRecord(
            category="retention_primary_request",
            ai_response="You can cancel at the link below.",
            human_edit="We're sorry to hear you're considering leaving. Here's the link.",
            correction_type="tone",
            specific_issue="Response too cold for retention scenario",
        )
        assert record.correction_type == "tone"

    def test_safety_correction(self):
        record = CorrectionRecord(
            category="retention_primary_request",
            ai_response="I've cancelled your subscription as requested.",
            human_edit="I understand you'd like to cancel. Please use this self-service link.",
            correction_type="safety",
            specific_issue="AI confirmed cancellation directly",
        )
        assert record.correction_type == "safety"

    def test_accuracy_correction(self):
        record = CorrectionRecord(
            category="shipping_or_delivery_question",
            ai_response="Your package ships from New York.",
            human_edit="Your package ships from Israel.",
            correction_type="accuracy",
            specific_issue="Wrong shipping origin",
        )
        assert record.correction_type == "accuracy"


# --- CorrectionClassification Model ---


class TestCorrectionClassification:
    """Verify CorrectionClassification model."""

    def test_minimal(self):
        cls = CorrectionClassification(correction_type="tone")
        assert cls.correction_type == "tone"
        assert cls.specific_issue is None
        assert cls.key_changes == []

    def test_full(self):
        cls = CorrectionClassification(
            correction_type="accuracy",
            specific_issue="Wrong shipping date",
            key_changes=["Fixed date from Jan 5 to Jan 10"],
        )
        assert cls.correction_type == "accuracy"
        assert cls.specific_issue == "Wrong shipping date"
        assert len(cls.key_changes) == 1

    def test_all_correction_types(self):
        """All four correction types should be valid."""
        for ct in ("tone", "accuracy", "safety", "completeness"):
            cls = CorrectionClassification(correction_type=ct)
            assert cls.correction_type == ct

    def test_multiple_key_changes(self):
        cls = CorrectionClassification(
            correction_type="completeness",
            key_changes=["Added tracking number", "Added delivery estimate", "Added carrier name"],
        )
        assert len(cls.key_changes) == 3
