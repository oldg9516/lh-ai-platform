"""Factory for switching between mock and real APIs.

Uses Python Protocols for type-safe, flexible API abstraction.
Controlled by USE_MOCK_APIS environment variable.
"""

from typing import Protocol
import structlog

logger = structlog.get_logger()


# --- Protocols (API Interfaces) ---


class SubscriptionAPI(Protocol):
    """Protocol for subscription management APIs."""

    async def pause_subscription(self, email: str, duration_months: int) -> dict:
        """Pause subscription for specified duration."""
        ...

    async def change_frequency(self, email: str, new_frequency: str) -> dict:
        """Change subscription billing frequency."""
        ...

    async def skip_month(self, email: str, month: str) -> dict:
        """Skip one month of subscription."""
        ...


class AddressAPI(Protocol):
    """Protocol for address validation APIs."""

    async def validate_and_update_address(
        self, email: str, new_address: dict
    ) -> dict:
        """Validate and update customer address."""
        ...


class DamageClaimAPI(Protocol):
    """Protocol for damage claim APIs."""

    async def create_damage_claim(
        self,
        email: str,
        item_description: str,
        damage_description: str,
    ) -> dict:
        """Create damage claim ticket."""
        ...

    async def request_photos(self, email: str, claim_id: str | None = None) -> dict:
        """Request photos for damage claim."""
        ...


# --- Factory ---


class APIFactory:
    """Factory for creating API clients based on configuration.

    Switches between mock and real implementations using USE_MOCK_APIS flag.
    """

    @staticmethod
    def get_subscription_api() -> SubscriptionAPI:
        """Get subscription management API (mock or real).

        Returns:
            SubscriptionAPI implementation (mock or real Zoho)
        """
        from config import settings

        if settings.use_mock_apis:
            from .client import MockZohoAPI

            logger.debug("using_mock_zoho_api")
            return MockZohoAPI()
        else:
            # Phase 7: Real Zoho API integration
            # from integrations.zoho import RealZohoAPI
            # logger.debug("using_real_zoho_api")
            # return RealZohoAPI()
            raise NotImplementedError(
                "Real Zoho API not implemented yet. Set USE_MOCK_APIS=true"
            )

    @staticmethod
    def get_address_api() -> AddressAPI:
        """Get address validation API (mock or real).

        Returns:
            AddressAPI implementation (mock or real Google Maps)
        """
        from config import settings

        if settings.use_mock_apis:
            from .client import MockAddressValidationAPI

            logger.debug("using_mock_address_api")
            return MockAddressValidationAPI()
        else:
            # Phase 7: Real Google Maps API integration
            # from integrations.google_maps import RealGoogleMapsAPI
            # logger.debug("using_real_google_maps_api")
            # return RealGoogleMapsAPI()
            raise NotImplementedError(
                "Real Google Maps API not implemented yet. Set USE_MOCK_APIS=true"
            )

    @staticmethod
    def get_damage_claim_api() -> DamageClaimAPI:
        """Get damage claim API (mock or real).

        Returns:
            DamageClaimAPI implementation (mock or real support tickets)
        """
        from config import settings

        if settings.use_mock_apis:
            from .client import MockDamageClaimAPI

            logger.debug("using_mock_damage_api")
            return MockDamageClaimAPI()
        else:
            # Phase 7: Real Support Ticket API integration
            # from integrations.support_tickets import RealSupportTicketAPI
            # logger.debug("using_real_support_ticket_api")
            # return RealSupportTicketAPI()
            raise NotImplementedError(
                "Real Support Ticket API not implemented yet. Set USE_MOCK_APIS=true"
            )
