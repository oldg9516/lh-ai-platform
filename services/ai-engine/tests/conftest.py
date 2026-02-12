"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_messages():
    """Sample messages for each category."""
    return {
        "shipping_or_delivery_question": "Where is my package? I ordered 2 weeks ago and still nothing.",
        "payment_question": "When will I be charged next month?",
        "frequency_change_request": "I want to receive my box every other month instead of monthly.",
        "skip_or_pause_request": "Can I skip next month? I am going on vacation.",
        "recipient_or_address_change": "I moved to 123 Main Street, New York, NY 10001. Please update my address.",
        "customization_request": "Please no wine or alcohol in my box.",
        "damaged_or_leaking_item_report": "My olive oil bottle arrived broken and leaked all over the other items.",
        "gratitude": "Thank you so much for the wonderful items in my last box. I loved everything.",
        "retention_primary_request": "I want to cancel my subscription.",
        "retention_repeated_request": "I already asked to cancel last week. Please cancel now.",
    }
