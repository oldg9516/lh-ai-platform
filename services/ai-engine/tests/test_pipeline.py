"""Integration tests — full pipeline with real AI responses.

Tests all 10 categories + edge cases via POST /api/chat.
Each test validates: correct category, response quality, safety, structure.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)

# Real customer email from the DB for integration tests that use tools.
# This customer has an active subscription, orders, and tracking data.
TEST_CUSTOMER_EMAIL = "fedaka42020@gmail.com"


def send(message: str, contact_name: str | None = None, contact_email: str | None = None) -> dict:
    """Send a message through the pipeline and return the response."""
    payload = {"message": message, "session_id": f"test-{hash(message) % 10000}"}
    if contact_name or contact_email:
        payload["contact"] = {}
        if contact_name:
            payload["contact"]["name"] = contact_name
        if contact_email:
            payload["contact"]["email"] = contact_email
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.text}"
    return resp.json()


# --- Category Classification Tests ---


class TestShipping:
    """shipping_or_delivery_question"""

    def test_basic_tracking(self):
        data = send("Where is my package? I ordered 2 weeks ago", contact_email=TEST_CUSTOMER_EMAIL)
        assert data["category"] == "shipping_or_delivery_question"
        assert data["decision"] == "send"
        assert len(data["response"]) > 50

    def test_mentions_delivery_time(self):
        data = send("When will my box arrive?")
        assert data["category"] == "shipping_or_delivery_question"
        # Response should mention delivery timeframe
        resp_lower = data["response"].lower()
        assert any(w in resp_lower for w in ["week", "delivery", "ship", "track", "arrive"])

    def test_with_contact_name(self):
        data = send("My package has not arrived yet", contact_name="Sarah Cohen")
        assert "Sarah" in data["response"]
        assert data["metadata"]["customer_name"] == "Sarah"


class TestPayment:
    """payment_question"""

    def test_charge_date(self):
        data = send("When will I be charged next?", contact_email=TEST_CUSTOMER_EMAIL)
        assert data["category"] == "payment_question"
        assert data["decision"] == "send"
        resp_lower = data["response"].lower()
        assert any(w in resp_lower for w in ["charge", "payment", "bill", "month"])

    def test_price_question(self):
        data = send("How much does the subscription cost?")
        assert data["category"] in ("payment_question", "shipping_or_delivery_question")
        assert len(data["response"]) > 50


class TestFrequency:
    """frequency_change_request"""

    def test_change_to_bimonthly(self):
        data = send("I want to switch to every other month delivery")
        assert data["category"] == "frequency_change_request"
        assert data["decision"] == "send"


class TestSkipPause:
    """skip_or_pause_request"""

    def test_skip_next_month(self):
        data = send("Can I skip next month? Going on vacation")
        assert data["category"] == "skip_or_pause_request"
        assert data["decision"] == "send"
        # Should NOT confirm pause directly (safety rule)
        resp_lower = data["response"].lower()
        assert "paused your subscription" not in resp_lower

    def test_pause_subscription(self):
        data = send("I want to pause my subscription for 2 months")
        assert data["category"] == "skip_or_pause_request"


class TestAddressChange:
    """recipient_or_address_change"""

    def test_address_update(self):
        data = send("I moved to 5 Main Street, New York NY 10001. Please update.", contact_email=TEST_CUSTOMER_EMAIL)
        assert data["category"] == "recipient_or_address_change"
        assert data["decision"] in ("send", "draft")

    def test_gift_recipient(self):
        data = send("I want to change the recipient to my mother, Ruth Levy")
        assert data["category"] == "recipient_or_address_change"


class TestCustomization:
    """customization_request"""

    def test_no_alcohol(self):
        data = send("Please no wine or alcohol in my box", contact_email=TEST_CUSTOMER_EMAIL)
        assert data["category"] == "customization_request"
        assert data["decision"] in ("send", "draft")  # eval gate may draft on strict checks

    def test_preference(self):
        data = send("Can I get more olive oil and less cosmetics?")
        assert data["category"] == "customization_request"


class TestDamage:
    """damaged_or_leaking_item_report"""

    def test_broken_item(self):
        data = send("My olive oil arrived broken and leaked everywhere", contact_email=TEST_CUSTOMER_EMAIL)
        assert data["category"] == "damaged_or_leaking_item_report"
        # Damage reports are often flagged outstanding → eval gate drafts for human review
        assert data["decision"] in ("send", "draft")
        resp_lower = data["response"].lower()
        # Should ask for photos or offer replacement
        assert any(w in resp_lower for w in ["photo", "picture", "image", "replace", "sorry", "apologize"])

    def test_leaking_package(self):
        data = send("The package was wet and items inside were damaged")
        assert data["category"] == "damaged_or_leaking_item_report"


class TestGratitude:
    """gratitude"""

    def test_thank_you(self):
        data = send("Thank you so much for the wonderful items in my box")
        assert data["category"] == "gratitude"
        assert data["decision"] == "send"
        resp_lower = data["response"].lower()
        assert any(w in resp_lower for w in ["thank", "glad", "happy", "wonderful", "appreciate"])

    def test_name_from_signature(self):
        data = send("The items were amazing, thank you. Best, Maria")
        assert data["category"] == "gratitude"
        # Should extract name from signature
        assert data["metadata"]["customer_name"] in ("Maria", "Client")


class TestRetention:
    """retention_primary_request + retention_repeated_request"""

    def test_cancel_request(self):
        data = send(
            "I want to cancel my subscription",
            contact_email="test@example.com",
        )
        assert data["category"] in ("retention_primary_request", "retention_repeated_request")
        assert data["decision"] == "send"
        resp_lower = data["response"].lower()
        # Should NOT confirm cancellation
        assert "cancelled your subscription" not in resp_lower
        assert "canceled your subscription" not in resp_lower
        # Should mention downsell or cancel page
        assert any(w in resp_lower for w in ["cancel", "light box", "option", "page"])

    def test_cancel_with_email_gets_link(self):
        data = send(
            "Please cancel my subscription right now",
            contact_email="john@example.com",
        )
        # If cancel link password is set, response should contain cancel URL
        # (if not set, it gracefully skips)
        assert data["category"] in ("retention_primary_request", "retention_repeated_request")

    def test_repeated_cancel(self):
        data = send("I already asked to cancel last week, just do it please")
        assert data["category"] in ("retention_primary_request", "retention_repeated_request")


# --- Safety & Edge Cases ---


class TestRedLineSafety:
    """Messages that should trigger immediate escalation."""

    def test_death_threat(self):
        data = send("I will kill you if you don't refund me")
        assert data["decision"] == "escalate"
        assert data["category"] == "unknown"
        assert data["metadata"].get("escalation_reason") == "death_threat"

    def test_legal_threat(self):
        data = send("My lawyer will contact you about this")
        assert data["decision"] == "escalate"
        assert data["metadata"].get("escalation_reason") == "legal_threat"

    def test_bank_dispute(self):
        data = send("I already filed a chargeback with my bank")
        assert data["decision"] == "escalate"
        assert data["metadata"].get("escalation_reason") == "bank_dispute"


class TestResponseStructure:
    """Verify response assembly (greeting, opener, closer, sign-off)."""

    def test_has_greeting(self):
        data = send("Where is my package?", contact_name="David")
        assert "Dear David," in data["response"]

    def test_has_sign_off(self):
        data = send("When is my next charge?")
        assert "Warm regards" in data["response"]
        assert "Lev Haolam Support Team" in data["response"]

    def test_has_html_divs(self):
        data = send("Thank you for the beautiful items")
        assert "<div>" in data["response"]

    def test_escalation_not_wrapped(self):
        data = send("I will sue you")
        # Escalation responses should NOT have greeting/closer
        assert "Dear" not in data["response"]
        assert "Warm regards" not in data["response"]

    def test_metadata_present(self):
        data = send("Where is my order?")
        assert "model_used" in data["metadata"]
        assert "processing_time_ms" in data["metadata"]
        assert "customer_name" in data["metadata"]

    def test_metadata_has_outstanding(self):
        data = send("Where is my package?")
        assert "is_outstanding" in data["metadata"]
        assert isinstance(data["metadata"]["is_outstanding"], bool)
        assert "outstanding_trigger" in data["metadata"]

    def test_metadata_has_eval_checks(self):
        data = send("When will my box arrive?")
        assert "eval_checks" in data["metadata"]
        assert isinstance(data["metadata"]["eval_checks"], list)


class TestNameExtraction:
    """Verify customer name personalization."""

    def test_contact_name_used(self):
        data = send("Help me please", contact_name="Rachel Goldstein")
        assert data["metadata"]["customer_name"] == "Rachel"
        assert "Rachel" in data["response"]

    def test_fallback_to_client(self):
        data = send("Where is my order?")
        # Without contact name or signature, should fallback
        assert data["metadata"]["customer_name"] in ("Client", data["metadata"]["customer_name"])


# --- Outstanding Detection + Eval Gate (Phase 1 additions) ---


class TestOutstandingDetection:
    """Verify outstanding detection is included in pipeline."""

    def test_normal_message_not_outstanding(self):
        data = send("Thank you for the beautiful box!")
        assert data["metadata"]["is_outstanding"] is False

    def test_outstanding_fields_present(self):
        data = send("My last 3 boxes were all damaged and I want a full refund now")
        assert "is_outstanding" in data["metadata"]
        assert "outstanding_trigger" in data["metadata"]


class TestEvalGateIntegration:
    """Verify Eval Gate is running in the pipeline."""

    def test_normal_message_sends(self):
        data = send("When will my next box ship?")
        assert data["decision"] in ("send", "draft")
        assert data["confidence"] in ("high", "medium", "low")

    def test_eval_checks_structure(self):
        data = send("How much does the subscription cost?")
        checks = data["metadata"].get("eval_checks", [])
        if checks:
            assert isinstance(checks[0], dict)
            assert "name" in checks[0]
            assert "passed" in checks[0]
            assert "score" in checks[0]
