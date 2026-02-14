"""Unit tests for action tools.

Read-only tools (customer, shipping, customization) mock the DB query layer.
Write tools (subscription, damage) remain stubs and are tested directly.
"""

import json
from unittest.mock import patch

from tools.customer import get_customer_history, get_payment_history, get_subscription
from tools.customization import get_box_contents
from tools.damage import create_damage_claim, request_photos
from tools.shipping import track_package
from tools.subscription import change_address, change_frequency, pause_subscription, skip_month

# --- Sample data for mocks ---

SAMPLE_CUSTOMER = {
    "id": 42,
    "email": "test@example.com",
    "name": "Rebecca Fedak",
    "customer_number": "LH-1234",
    "phone": "+1234567890",
    "street": "123 Main St",
    "address_line_2": "Apt 4B",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": "11201",
    "country": "US",
}

SAMPLE_SUB = {
    "id": 10,
    "customer_id": 42,
    "customer_number": "LH-1234",
    "status": "Active",
    "frequency": "Monthly",
    "start_date": "2024-06-15",
    "regular_box_price": "54.90",
    "price_currency": "USD",
    "billing_day": 1,
    "no_alcohol": False,
    "no_honey": True,
    "next_payment_date": "2026-03-01",
    "payment_method": "card",
    "payment_method_id": "************8534",
    "payment_expire_date": "10/28",
    "payer_name": "Rebecca Fedak",
    "payer_email": "test@example.com",
}

SAMPLE_ORDER = {
    "id": 100,
    "customer_id": 42,
    "subscription_id": 10,
    "order_type": "subscription",
    "box_sequence": 20,
    "box_name": "February 2026 Box",
    "sku": "LH-FEB-2026",
    "price": "54.90",
    "price_currency": "USD",
    "payment_date_actual": "2026-02-01T00:00:00Z",
    "shipping_date": "2026-02-05T00:00:00Z",
    "tracking_number": "LH2026021345IL",
    "invoice": "INV-2026-02",
    "created_at": "2026-02-01T00:00:00Z",
}

SAMPLE_TRACKING = {
    "id": 1,
    "tracking_number": "LH2026021345IL",
    "carrier": "Israel Post",
    "delivery_status": "in_transit",
    "delivery_date": None,
    "history": [
        {"date": "2026-02-11", "status": "Arrived at destination country"},
        {"date": "2026-02-05", "status": "Shipped"},
    ],
}


# --- get_subscription ---


class TestGetSubscription:
    @patch("tools.customer.get_active_subscription_by_email")
    def test_found_with_subscription(self, mock_query):
        mock_query.return_value = {
            "found": True,
            "customer": SAMPLE_CUSTOMER,
            "subscription": SAMPLE_SUB,
            "subscriptions_count": 1,
        }
        result = json.loads(get_subscription("test@example.com"))
        assert result["found"] is True
        assert result["customer_name"] == "Rebecca Fedak"
        assert result["status"] == "Active"
        assert result["frequency"] == "Monthly"
        assert result["price"] == 54.90
        assert result["next_billing_date"] == "2026-03-01"
        assert result["shipping_address"]["city"] == "Brooklyn"
        assert result["no_honey"] is True

    @patch("tools.customer.get_active_subscription_by_email")
    def test_found_no_subscription(self, mock_query):
        mock_query.return_value = {
            "found": True,
            "customer": SAMPLE_CUSTOMER,
            "subscription": None,
            "subscriptions_count": 0,
        }
        result = json.loads(get_subscription("test@example.com"))
        assert result["found"] is True
        assert result["subscription"] is None
        assert "no subscriptions" in result["message"]

    @patch("tools.customer.get_active_subscription_by_email")
    def test_not_found(self, mock_query):
        mock_query.return_value = None
        result = json.loads(get_subscription("unknown@example.com"))
        assert result["found"] is False
        assert "verify" in result["message"].lower()


# --- get_customer_history ---


class TestGetCustomerHistory:
    @patch("tools.customer.get_customer_history_by_email")
    def test_found(self, mock_query):
        mock_query.return_value = {
            "found": True,
            "customer": {"email": "test@example.com", "name": "Rebecca"},
            "subscription": {"status": "Active"},
            "orders_summary": {
                "total_subscription_boxes": 20,
                "total_one_time_orders": 2,
                "recent_orders": [],
            },
            "subscriptions_count": 1,
        }
        result = json.loads(get_customer_history("test@example.com"))
        assert result["found"] is True
        assert result["orders_summary"]["total_subscription_boxes"] == 20

    @patch("tools.customer.get_customer_history_by_email")
    def test_not_found(self, mock_query):
        mock_query.return_value = None
        result = json.loads(get_customer_history("unknown@example.com"))
        assert result["found"] is False


# --- get_payment_history ---


class TestGetPaymentHistory:
    @patch("tools.customer.get_payment_history_by_email")
    def test_with_payments(self, mock_query):
        mock_query.return_value = {
            "found": True,
            "customer_email": "test@example.com",
            "payments": [
                {"date": "2026-02-01T00:00:00Z", "amount": "54.90", "currency": "USD"},
            ],
            "next_payment_date": "2026-03-01",
            "payment_method": "card",
            "payment_method_id": "************8534",
        }
        result = json.loads(get_payment_history("test@example.com"))
        assert result["found"] is True
        assert len(result["payments"]) == 1
        assert result["next_payment_date"] == "2026-03-01"

    @patch("tools.customer.get_payment_history_by_email")
    def test_not_found(self, mock_query):
        mock_query.return_value = None
        result = json.loads(get_payment_history("unknown@example.com"))
        assert result["found"] is False


# --- track_package ---


class TestTrackPackage:
    @patch("tools.shipping.get_tracking_by_email")
    def test_with_tracking(self, mock_query):
        mock_query.return_value = {
            "found": True,
            "customer_email": "test@example.com",
            "tracking_number": "LH2026021345IL",
            "order": {
                "box_name": "February 2026 Box",
                "box_sequence": 20,
                "shipping_date": "2026-02-05T00:00:00Z",
            },
            "tracking": SAMPLE_TRACKING,
        }
        result = json.loads(track_package("test@example.com"))
        assert result["found"] is True
        assert result["tracking_number"] == "LH2026021345IL"
        assert result["delivery_status"] == "in_transit"
        assert len(result["history"]) == 2

    @patch("tools.shipping.get_tracking_by_email")
    def test_no_tracking(self, mock_query):
        mock_query.return_value = {
            "found": True,
            "customer_email": "test@example.com",
            "tracking": None,
            "message": "No recent shipment with tracking found.",
        }
        result = json.loads(track_package("test@example.com"))
        assert result["found"] is True
        assert result["tracking"] is None

    @patch("tools.shipping.get_tracking_by_email")
    def test_not_found(self, mock_query):
        mock_query.return_value = None
        result = json.loads(track_package("unknown@example.com"))
        assert result["found"] is False


# --- get_box_contents ---


class TestGetBoxContents:
    @patch("tools.customization.get_orders_by_customer")
    @patch("tools.customization.get_active_subscription_by_email")
    def test_with_data(self, mock_sub, mock_orders):
        mock_sub.return_value = {
            "found": True,
            "customer": SAMPLE_CUSTOMER,
            "subscription": SAMPLE_SUB,
            "subscriptions_count": 1,
        }
        mock_orders.return_value = [SAMPLE_ORDER]

        result = json.loads(get_box_contents("test@example.com"))
        assert result["found"] is True
        assert result["last_box"]["box_name"] == "February 2026 Box"
        assert result["customization_preferences"]["no_honey"] is True
        assert result["customization_preferences"]["no_alcohol"] is False
        assert "honey" in result["customization_preferences"]["current"]
        assert "alcohol" not in result["customization_preferences"]["current"]

    @patch("tools.customization.get_orders_by_customer")
    @patch("tools.customization.get_active_subscription_by_email")
    def test_no_orders(self, mock_sub, mock_orders):
        mock_sub.return_value = {
            "found": True,
            "customer": SAMPLE_CUSTOMER,
            "subscription": SAMPLE_SUB,
            "subscriptions_count": 1,
        }
        mock_orders.return_value = []

        result = json.loads(get_box_contents("test@example.com"))
        assert result["found"] is True
        assert result["last_box"]["box_name"] is None

    @patch("tools.customization.get_active_subscription_by_email")
    def test_not_found(self, mock_sub):
        mock_sub.return_value = None
        result = json.loads(get_box_contents("unknown@example.com"))
        assert result["found"] is False


# --- Write tools (stubs, no DB) ---


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
