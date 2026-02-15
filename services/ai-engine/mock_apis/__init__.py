"""Mock API implementations for demo/development.

This module provides realistic mock implementations of external APIs:
- Zoho CRM (subscription management)
- Google Maps (address validation)
- Support Tickets (damage claims)

Used when USE_MOCK_APIS=true in config.
"""

from .client import (
    MockZohoAPI,
    MockAddressValidationAPI,
    MockDamageClaimAPI,
)
from .factory import APIFactory

__all__ = [
    "MockZohoAPI",
    "MockAddressValidationAPI",
    "MockDamageClaimAPI",
    "APIFactory",
]
