"""Unit tests for database/customer_queries.py.

All tests mock the Supabase client to avoid requiring a live database.
"""

from unittest.mock import MagicMock, patch

from database.customer_queries import (
    get_active_subscription_by_email,
    get_customer_history_by_email,
    get_orders_by_customer,
    get_orders_by_subscription,
    get_payment_history_by_email,
    get_subscriptions_by_customer,
    get_tracking_by_email,
    lookup_customer,
)

# --- Sample data ---

SAMPLE_CUSTOMER = {
    "id": 42,
    "email": "test@example.com",
    "name": "Test User",
    "customer_number": "LH-1234",
    "phone": "+1234567890",
    "street": "123 Main St",
    "city": "Brooklyn",
    "state": "NY",
    "zip_code": "11201",
    "country": "US",
}

SAMPLE_SUB_ACTIVE = {
    "id": 10,
    "customer_id": 42,
    "customer_number": "LH-1234",
    "status": "Active",
    "frequency": "Monthly",
    "start_date": "2024-06-15",
    "regular_box_price": 54.90,
    "price_currency": "USD",
    "no_alcohol": False,
    "no_honey": True,
    "next_payment_date": "2026-03-01",
    "payment_method": "card",
    "payment_method_id": "************8534",
}

SAMPLE_SUB_INACTIVE = {
    "id": 11,
    "customer_id": 42,
    "customer_number": "LH-5678",
    "status": "Inactive",
    "frequency": "Monthly",
}

SAMPLE_ORDER = {
    "id": 100,
    "customer_id": 42,
    "subscription_id": 10,
    "order_type": "subscription",
    "box_sequence": 20,
    "box_name": "February 2026 Box",
    "price": 54.90,
    "price_currency": "USD",
    "payment_date_actual": "2026-02-01T00:00:00Z",
    "shipping_date": "2026-02-05T00:00:00Z",
    "tracking_number": "LH2026021345IL",
    "invoice": "INV-2026-02",
    "created_at": "2026-02-01T00:00:00Z",
}

SAMPLE_ORDER_NO_TRACKING = {
    "id": 101,
    "customer_id": 42,
    "subscription_id": 10,
    "order_type": "subscription",
    "box_sequence": 19,
    "box_name": "January 2026 Box",
    "payment_date_actual": "2026-01-01T00:00:00Z",
    "tracking_number": None,
    "created_at": "2026-01-01T00:00:00Z",
}

SAMPLE_TRACKING = {
    "id": 1,
    "tracking_number": "LH2026021345IL",
    "delivery_status": "in_transit",
    "delivery_date": None,
    "history": [
        {"date": "2026-02-11", "status": "Arrived at destination country"},
        {"date": "2026-02-05", "status": "Shipped"},
    ],
}


def _mock_response(data):
    """Create a mock Supabase response with the given data list."""
    resp = MagicMock()
    resp.data = data
    return resp


def _mock_chain(response):
    """Create a mock Supabase query chain that returns the given response."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = response
    return chain


# --- lookup_customer ---


class TestLookupCustomer:
    @patch("database.customer_queries.get_client")
    def test_found(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response([SAMPLE_CUSTOMER]))
        mock_get_client.return_value = client

        result = lookup_customer("Test@Example.com")
        assert result is not None
        assert result["email"] == "test@example.com"
        client.table.assert_called_once_with("customers")

    @patch("database.customer_queries.get_client")
    def test_not_found(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response([]))
        mock_get_client.return_value = client

        result = lookup_customer("unknown@example.com")
        assert result is None

    @patch("database.customer_queries.get_client")
    def test_normalizes_email(self, mock_get_client):
        client = MagicMock()
        chain = _mock_chain(_mock_response([]))
        client.table.return_value = chain
        mock_get_client.return_value = client

        lookup_customer("  USER@Example.COM  ")
        # Verify the normalized email was used in the eq call
        chain.eq.assert_called_with("email", "user@example.com")

    @patch("database.customer_queries.get_client")
    def test_exception_returns_none(self, mock_get_client):
        mock_get_client.side_effect = RuntimeError("DB down")
        result = lookup_customer("test@example.com")
        assert result is None


# --- get_subscriptions_by_customer ---


class TestGetSubscriptionsByCustomer:
    @patch("database.customer_queries.get_client")
    def test_returns_list(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(
            _mock_response([SAMPLE_SUB_ACTIVE, SAMPLE_SUB_INACTIVE]),
        )
        mock_get_client.return_value = client

        result = get_subscriptions_by_customer(42)
        assert len(result) == 2
        assert result[0]["status"] == "Active"

    @patch("database.customer_queries.get_client")
    def test_no_subscriptions(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response([]))
        mock_get_client.return_value = client

        result = get_subscriptions_by_customer(99)
        assert result == []

    @patch("database.customer_queries.get_client")
    def test_exception_returns_empty(self, mock_get_client):
        mock_get_client.side_effect = RuntimeError("DB down")
        result = get_subscriptions_by_customer(42)
        assert result == []


# --- get_active_subscription_by_email ---


class TestGetActiveSubscriptionByEmail:
    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_found_active(self, mock_lookup, mock_subs):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = [SAMPLE_SUB_ACTIVE, SAMPLE_SUB_INACTIVE]

        result = get_active_subscription_by_email("test@example.com")
        assert result is not None
        assert result["found"] is True
        assert result["subscription"]["status"] == "Active"
        assert result["subscriptions_count"] == 2

    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_no_active_falls_back(self, mock_lookup, mock_subs):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = [SAMPLE_SUB_INACTIVE]

        result = get_active_subscription_by_email("test@example.com")
        assert result["subscription"]["status"] == "Inactive"
        assert result["subscriptions_count"] == 1

    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_no_subscriptions(self, mock_lookup, mock_subs):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = []

        result = get_active_subscription_by_email("test@example.com")
        assert result["found"] is True
        assert result["subscription"] is None
        assert result["subscriptions_count"] == 0

    @patch("database.customer_queries.lookup_customer")
    def test_customer_not_found(self, mock_lookup):
        mock_lookup.return_value = None

        result = get_active_subscription_by_email("unknown@example.com")
        assert result is None


# --- get_orders_by_customer ---


class TestGetOrdersByCustomer:
    @patch("database.customer_queries.get_client")
    def test_returns_orders(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(
            _mock_response([SAMPLE_ORDER, SAMPLE_ORDER_NO_TRACKING]),
        )
        mock_get_client.return_value = client

        result = get_orders_by_customer(42)
        assert len(result) == 2

    @patch("database.customer_queries.get_client")
    def test_empty(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response([]))
        mock_get_client.return_value = client

        result = get_orders_by_customer(42)
        assert result == []


# --- get_payment_history_by_email ---


class TestGetPaymentHistoryByEmail:
    @patch("database.customer_queries.get_orders_by_customer")
    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_with_payments(self, mock_lookup, mock_subs, mock_orders):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = [SAMPLE_SUB_ACTIVE]
        mock_orders.return_value = [SAMPLE_ORDER]

        result = get_payment_history_by_email("test@example.com")
        assert result["found"] is True
        assert len(result["payments"]) == 1
        assert result["payments"][0]["date"] == "2026-02-01T00:00:00Z"
        assert result["next_payment_date"] == "2026-03-01"
        assert result["payment_method"] == "card"

    @patch("database.customer_queries.get_orders_by_customer")
    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_no_payments(self, mock_lookup, mock_subs, mock_orders):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = []
        mock_orders.return_value = [SAMPLE_ORDER_NO_TRACKING]

        result = get_payment_history_by_email("test@example.com")
        # SAMPLE_ORDER_NO_TRACKING has payment_date_actual
        assert result["found"] is True
        assert result["next_payment_date"] is None

    @patch("database.customer_queries.lookup_customer")
    def test_customer_not_found(self, mock_lookup):
        mock_lookup.return_value = None

        result = get_payment_history_by_email("unknown@example.com")
        assert result is None


# --- get_tracking_by_email ---


class TestGetTrackingByEmail:
    @patch("database.customer_queries.get_client")
    @patch("database.customer_queries.get_orders_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_with_tracking(self, mock_lookup, mock_orders, mock_get_client):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_orders.return_value = [SAMPLE_ORDER]

        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response([SAMPLE_TRACKING]))
        mock_get_client.return_value = client

        result = get_tracking_by_email("test@example.com")
        assert result["found"] is True
        assert result["tracking_number"] == "LH2026021345IL"
        assert result["tracking"]["delivery_status"] == "in_transit"

    @patch("database.customer_queries.get_orders_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_no_tracked_orders(self, mock_lookup, mock_orders):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_orders.return_value = [SAMPLE_ORDER_NO_TRACKING]

        result = get_tracking_by_email("test@example.com")
        assert result["found"] is True
        assert result["tracking"] is None
        assert "No recent shipment" in result["message"]

    @patch("database.customer_queries.lookup_customer")
    def test_customer_not_found(self, mock_lookup):
        mock_lookup.return_value = None

        result = get_tracking_by_email("unknown@example.com")
        assert result is None


# --- get_customer_history_by_email ---


class TestGetCustomerHistoryByEmail:
    @patch("database.customer_queries.get_orders_by_customer")
    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_full_history(self, mock_lookup, mock_subs, mock_orders):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = [SAMPLE_SUB_ACTIVE]
        mock_orders.return_value = [SAMPLE_ORDER, SAMPLE_ORDER_NO_TRACKING]

        result = get_customer_history_by_email("test@example.com")
        assert result["found"] is True
        assert result["customer"]["email"] == "test@example.com"
        assert result["subscription"]["status"] == "Active"
        assert result["subscription"]["no_honey"] is True
        assert result["orders_summary"]["total_subscription_boxes"] == 2
        assert result["subscriptions_count"] == 1

    @patch("database.customer_queries.get_orders_by_customer")
    @patch("database.customer_queries.get_subscriptions_by_customer")
    @patch("database.customer_queries.lookup_customer")
    def test_no_subscriptions(self, mock_lookup, mock_subs, mock_orders):
        mock_lookup.return_value = SAMPLE_CUSTOMER
        mock_subs.return_value = []
        mock_orders.return_value = []

        result = get_customer_history_by_email("test@example.com")
        assert result["found"] is True
        assert result["subscription"] is None
        assert result["orders_summary"]["total_subscription_boxes"] == 0

    @patch("database.customer_queries.lookup_customer")
    def test_customer_not_found(self, mock_lookup):
        mock_lookup.return_value = None

        result = get_customer_history_by_email("unknown@example.com")
        assert result is None
