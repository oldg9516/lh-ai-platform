"""Unit tests for action tools (stubs).

Validates each tool returns valid JSON with expected fields.
"""

import json

from tools.customer import get_customer_history, get_payment_history, get_subscription
from tools.customization import get_box_contents
from tools.damage import create_damage_claim, request_photos
from tools.shipping import track_package
from tools.subscription import change_address, change_frequency, pause_subscription, skip_month


class TestGetSubscription:
    def test_returns_valid_json(self):
        result = json.loads(get_subscription("test@example.com"))
        assert result["subscription_id"] == "sub_LH_29847"
        assert result["status"] == "active"
        assert result["customer_email"] == "test@example.com"

    def test_has_shipping_address(self):
        result = json.loads(get_subscription("test@example.com"))
        assert "shipping_address" in result
        assert "city" in result["shipping_address"]

    def test_has_billing_info(self):
        result = json.loads(get_subscription("test@example.com"))
        assert "next_billing_date" in result
        assert "price_usd" in result


class TestGetCustomerHistory:
    def test_returns_valid_json(self):
        result = json.loads(get_customer_history("test@example.com"))
        assert result["customer_email"] == "test@example.com"
        assert isinstance(result["recent_tickets"], list)

    def test_has_lifetime_value(self):
        result = json.loads(get_customer_history("test@example.com"))
        assert result["lifetime_value_usd"] > 0


class TestGetPaymentHistory:
    def test_returns_payments(self):
        result = json.loads(get_payment_history("test@example.com"))
        assert len(result["payments"]) > 0

    def test_payment_fields(self):
        result = json.loads(get_payment_history("test@example.com"))
        payment = result["payments"][0]
        assert "date" in payment
        assert "amount_usd" in payment
        assert "status" in payment


class TestTrackPackage:
    def test_returns_tracking(self):
        result = json.loads(track_package("test@example.com"))
        assert "tracking_number" in result
        assert "status" in result
        assert "estimated_delivery" in result

    def test_has_events(self):
        result = json.loads(track_package("test@example.com"))
        assert len(result["events"]) > 0


class TestChangeFrequency:
    def test_awaiting_confirmation(self):
        result = json.loads(change_frequency("test@example.com", "bi-monthly"))
        assert result["status"] == "awaiting_customer_confirmation"
        assert result["confirmation_required"] is True
        assert result["requested_frequency"] == "bi-monthly"

    def test_action_field(self):
        result = json.loads(change_frequency("test@example.com", "quarterly"))
        assert result["action"] == "frequency_change"


class TestSkipMonth:
    def test_awaiting_confirmation(self):
        result = json.loads(skip_month("test@example.com"))
        assert result["status"] == "awaiting_customer_confirmation"
        assert result["confirmation_required"] is True

    def test_action_field(self):
        result = json.loads(skip_month("test@example.com", "March"))
        assert result["action"] == "skip_month"


class TestPauseSubscription:
    def test_awaiting_confirmation(self):
        result = json.loads(pause_subscription("test@example.com", 2))
        assert result["status"] == "awaiting_customer_confirmation"
        assert result["confirmation_required"] is True
        assert result["requested_pause_months"] == 2

    def test_action_field(self):
        result = json.loads(pause_subscription("test@example.com"))
        assert result["action"] == "pause_subscription"


class TestChangeAddress:
    def test_awaiting_confirmation(self):
        result = json.loads(change_address("test@example.com", "456 Oak Ave, Chicago, IL 60601"))
        assert result["status"] == "awaiting_customer_confirmation"
        assert result["confirmation_required"] is True
        assert "456 Oak Ave" in result["new_address"]

    def test_action_field(self):
        result = json.loads(change_address("test@example.com", "new address"))
        assert result["action"] == "address_change"


class TestCreateDamageClaim:
    def test_returns_claim_id(self):
        result = json.loads(create_damage_claim("test@example.com", "olive oil", "bottle cracked"))
        assert result["claim_id"].startswith("CLM-")
        assert result["status"] == "submitted"

    def test_has_next_steps(self):
        result = json.loads(create_damage_claim("test@example.com", "soap", "melted"))
        assert "photo" in result["next_steps"].lower()


class TestRequestPhotos:
    def test_with_claim_id(self):
        result = json.loads(request_photos("test@example.com", "CLM-12345678"))
        assert result["action"] == "photos_requested"
        assert result["claim_id"] == "CLM-12345678"

    def test_without_claim_id(self):
        result = json.loads(request_photos("test@example.com"))
        assert result["claim_id"] == "pending"


class TestGetBoxContents:
    def test_returns_items(self):
        result = json.loads(get_box_contents("test@example.com"))
        assert len(result["last_box"]["items"]) > 0

    def test_has_customization(self):
        result = json.loads(get_box_contents("test@example.com"))
        assert "available_exclusions" in result["customization_preferences"]
