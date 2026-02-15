"""Tests for Mock API clients.

Verifies that mock implementations return realistic data with
proper structure and latencies.
"""

import pytest

from mock_apis.client import (
    MockZohoAPI,
    MockAddressValidationAPI,
    MockDamageClaimAPI,
)


class TestMockZohoAPI:
    """Test Zoho CRM mock API."""

    @pytest.mark.asyncio
    async def test_pause_subscription(self):
        """Pause subscription returns success with date."""
        api = MockZohoAPI()
        result = await api.pause_subscription("test@example.com", duration_months=2)

        assert result["success"] is True
        assert "paused_until" in result
        assert result["notification_sent"] is True
        assert "subscription_id" in result
        assert "2 month" in result["message"]

    @pytest.mark.asyncio
    async def test_change_frequency(self):
        """Change frequency returns success with new frequency."""
        api = MockZohoAPI()
        result = await api.change_frequency("test@example.com", "bi-monthly")

        assert result["success"] is True
        assert result["new_frequency"] == "bi-monthly"
        assert "next_charge_date" in result
        assert result["notification_sent"] is True

    @pytest.mark.asyncio
    async def test_skip_month(self):
        """Skip month returns success with skipped month."""
        api = MockZohoAPI()
        result = await api.skip_month("test@example.com", "March 2026")

        assert result["success"] is True
        assert result["skipped_month"] == "March 2026"
        assert "next_charge_date" in result
        assert result["notification_sent"] is True


class TestMockAddressAPI:
    """Test address validation mock API."""

    @pytest.mark.asyncio
    async def test_validate_address_success(self):
        """Valid address is accepted."""
        api = MockAddressValidationAPI()
        address = {
            "street": "123 Main St",
            "city": "Tel Aviv",
            "country": "Israel",
        }
        result = await api.validate_and_update_address("test@example.com", address)

        assert result["success"] is True
        assert "validated_address" in result
        assert result["validated_address"]["street"] == "123 Main St"
        assert result["validated_address"]["city"] == "Tel Aviv"
        assert "geocoded" in result
        assert "lat" in result["geocoded"]
        assert "lng" in result["geocoded"]

    @pytest.mark.asyncio
    async def test_validate_address_missing_fields(self):
        """Missing required fields returns error."""
        api = MockAddressValidationAPI()
        address = {"city": "Tel Aviv"}  # Missing street and country
        result = await api.validate_and_update_address("test@example.com", address)

        assert result["success"] is False
        assert "error" in result
        assert "missing" in result["error"]


class TestMockDamageClaimAPI:
    """Test damage claim mock API."""

    @pytest.mark.asyncio
    async def test_create_damage_claim(self):
        """Create damage claim returns claim ID."""
        api = MockDamageClaimAPI()
        result = await api.create_damage_claim(
            "test@example.com",
            "olive oil bottle",
            "bottle cracked, oil leaked",
        )

        assert result["success"] is True
        assert "claim_id" in result
        assert result["claim_id"].startswith("DMG-")
        assert result["status"] == "pending_photos"
        assert "next_steps" in result
        assert len(result["next_steps"]) > 0

    @pytest.mark.asyncio
    async def test_request_photos(self):
        """Request photos returns upload URL."""
        api = MockDamageClaimAPI()
        result = await api.request_photos("test@example.com", "DMG-202402-123")

        assert result["success"] is True
        assert result["claim_id"] == "DMG-202402-123"
        assert "upload_url" in result
        assert "levhaolam.com" in result["upload_url"]
        assert "instructions" in result
        assert result["notification_sent"] is True

    @pytest.mark.asyncio
    async def test_request_photos_without_claim_id(self):
        """Request photos without claim ID generates new one."""
        api = MockDamageClaimAPI()
        result = await api.request_photos("test@example.com")

        assert result["success"] is True
        assert "claim_id" in result
        assert result["claim_id"].startswith("DMG-")
