"""Sample data for Mock APIs - reuses test fixtures for consistency."""

from datetime import datetime, timedelta

# Customer data (from tests/test_tools.py)
SAMPLE_CUSTOMER = {
    "customer_id": 1,
    "email": "sarah.cohen@example.com",
    "name": "Sarah Cohen",
    "join_date": "2022-03-15",
    "total_orders": 24,
    "ltv": 1440.00,
}

SAMPLE_SUBSCRIPTION = {
    "subscription_id": 101,
    "customer_id": 1,
    "status": "active",
    "frequency": "monthly",
    "next_charge_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
    "last_charge_amount": 60.00,
}

SAMPLE_ADDRESS = {
    "street": "123 Main St",
    "city": "Tel Aviv",
    "state": "",
    "postal_code": "12345",
    "country": "Israel",
}

# Damage claim data
SAMPLE_DAMAGE_CLAIM = {
    "claim_id": "DMG-2024-001",
    "status": "pending_review",
    "created_at": datetime.now().isoformat(),
    "description": "Received damaged item",
}

# API response templates
def success_response(data: dict, message: str = "Operation successful") -> dict:
    """Standard success response template."""
    return {
        "success": True,
        "message": message,
        **data,
    }


def error_response(error: str) -> dict:
    """Standard error response template."""
    return {
        "success": False,
        "error": error,
    }
