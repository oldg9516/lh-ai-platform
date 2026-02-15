"""Mock API clients for demo/development.

Provides realistic mock implementations with:
- Async methods with realistic latencies (300-800ms)
- Structured logging
- Realistic response formats
"""

import asyncio
from datetime import datetime, timedelta
import random
import structlog

from .sample_data import success_response, error_response

logger = structlog.get_logger()


class MockZohoAPI:
    """Mock Zoho CRM API for subscription management.

    Simulates realistic latencies and responses for:
    - pause_subscription()
    - change_frequency()
    - skip_month()
    """

    async def pause_subscription(
        self, email: str, duration_months: int = 1
    ) -> dict:
        """Pause subscription for specified duration.

        Args:
            email: Customer email address
            duration_months: How many months to pause (1-12)

        Returns:
            dict with success, paused_until, notification_sent
        """
        # Realistic latency
        await asyncio.sleep(random.uniform(0.3, 0.6))

        logger.info(
            "mock_zoho_pause",
            email=email,
            duration=duration_months,
            api="mock",
        )

        # Calculate pause end date
        paused_until = (
            datetime.now() + timedelta(days=30 * duration_months)
        ).strftime("%Y-%m-%d")

        return success_response(
            {
                "paused_until": paused_until,
                "notification_sent": True,
                "subscription_id": f"SUB-{hash(email) % 10000}",
            },
            message=f"Subscription paused for {duration_months} month(s)",
        )

    async def change_frequency(self, email: str, new_frequency: str) -> dict:
        """Change subscription frequency.

        Args:
            email: Customer email address
            new_frequency: monthly, bi-monthly, or quarterly

        Returns:
            dict with success, new_frequency, next_charge_date
        """
        await asyncio.sleep(random.uniform(0.4, 0.7))

        logger.info(
            "mock_zoho_change_frequency",
            email=email,
            frequency=new_frequency,
            api="mock",
        )

        # Calculate next charge based on frequency
        days_map = {
            "monthly": 30,
            "bi-monthly": 60,
            "quarterly": 90,
        }
        days = days_map.get(new_frequency, 30)
        next_charge = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        return success_response(
            {
                "new_frequency": new_frequency,
                "next_charge_date": next_charge,
                "notification_sent": True,
            },
            message=f"Frequency updated to {new_frequency}",
        )

    async def skip_month(self, email: str, month: str) -> dict:
        """Skip one month of subscription.

        Args:
            email: Customer email address
            month: Month to skip (e.g., "March 2024")

        Returns:
            dict with success, skipped_month, next_charge_date
        """
        await asyncio.sleep(random.uniform(0.3, 0.5))

        logger.info(
            "mock_zoho_skip_month",
            email=email,
            month=month,
            api="mock",
        )

        # Next charge is 2 months from now (skipped + next regular)
        next_charge = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

        return success_response(
            {
                "skipped_month": month,
                "next_charge_date": next_charge,
                "notification_sent": True,
            },
            message=f"Skipped {month}",
        )


class MockAddressValidationAPI:
    """Mock Google Maps / Address Validation API.

    Simulates address validation and update.
    """

    async def validate_and_update_address(
        self, email: str, new_address: dict
    ) -> dict:
        """Validate and update customer address.

        Args:
            email: Customer email address
            new_address: dict with street, city, state, postal_code, country

        Returns:
            dict with success, validated_address, geocoded (lat/lng)
        """
        await asyncio.sleep(random.uniform(0.5, 0.8))

        logger.info(
            "mock_address_validation",
            email=email,
            city=new_address.get("city"),
            api="mock",
        )

        # Simulate validation - accept most addresses
        # Reject if missing required fields
        required = ["street", "city", "country"]
        missing = [f for f in required if not new_address.get(f)]

        if missing:
            return error_response(
                f"Address validation failed: missing {', '.join(missing)}"
            )

        # Return validated address with geocoding
        return success_response(
            {
                "validated_address": {
                    "street": new_address.get("street"),
                    "city": new_address.get("city"),
                    "state": new_address.get("state", ""),
                    "postal_code": new_address.get("postal_code", ""),
                    "country": new_address.get("country"),
                },
                "geocoded": {
                    "lat": random.uniform(30.0, 35.0),  # Israel-ish
                    "lng": random.uniform(34.0, 36.0),
                },
                "notification_sent": True,
            },
            message="Address validated and updated",
        )


class MockDamageClaimAPI:
    """Mock Damage Claim / Support Ticket API.

    Simulates damage claim creation and photo requests.
    """

    async def create_damage_claim(
        self,
        email: str,
        item_description: str,
        damage_description: str,
    ) -> dict:
        """Create a damage claim ticket.

        Args:
            email: Customer email address
            item_description: What item was damaged
            damage_description: Description of damage

        Returns:
            dict with success, claim_id, status, next_steps
        """
        await asyncio.sleep(random.uniform(0.4, 0.7))

        logger.info(
            "mock_damage_claim_create",
            email=email,
            item=item_description,
            api="mock",
        )

        # Generate realistic claim ID
        claim_id = f"DMG-{datetime.now().strftime('%Y%m')}-{random.randint(100, 999)}"

        return success_response(
            {
                "claim_id": claim_id,
                "status": "pending_photos",
                "created_at": datetime.now().isoformat(),
                "next_steps": [
                    "Upload photos of damaged item",
                    "Photos will be reviewed within 24 hours",
                    "Replacement or refund will be processed",
                ],
            },
            message=f"Damage claim {claim_id} created",
        )

    async def request_photos(self, email: str, claim_id: str | None = None) -> dict:
        """Request photos for damage claim.

        Args:
            email: Customer email address
            claim_id: Optional existing claim ID

        Returns:
            dict with success, upload_url, instructions
        """
        await asyncio.sleep(random.uniform(0.3, 0.5))

        logger.info(
            "mock_damage_request_photos",
            email=email,
            claim_id=claim_id,
            api="mock",
        )

        # Use provided claim_id or generate new one
        if not claim_id:
            claim_id = f"DMG-{datetime.now().strftime('%Y%m')}-{random.randint(100, 999)}"

        return success_response(
            {
                "claim_id": claim_id,
                "upload_url": f"https://support.levhaolam.com/upload/{claim_id}",
                "instructions": [
                    "Take photos of damaged item from multiple angles",
                    "Include photos of packaging if available",
                    "Upload within 7 days",
                ],
                "notification_sent": True,
            },
            message="Photo upload instructions sent to email",
        )
