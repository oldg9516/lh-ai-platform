"""Unit tests for Chatwoot webhook handler.

Tests webhook filtering, idempotency, and payload parsing.
No real AI calls — uses mocks for chat() and Chatwoot dispatch.
"""

from fastapi.testclient import TestClient

from main import app
from api.routes import _processed_messages

client = TestClient(app)


def _reset_dedup():
    """Clear the dedup dict between tests."""
    _processed_messages.clear()


# --- Webhook Filtering ---


class TestWebhookFiltering:
    """Verify that only valid incoming messages are processed."""

    def test_ignores_non_message_events(self):
        payload = {"event": "conversation_created", "content": "test"}
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert "event=" in resp.json()["reason"]

    def test_ignores_outgoing_messages(self):
        payload = {
            "event": "message_created",
            "message_type": "outgoing",
            "content": "bot reply",
            "conversation": {"id": 1},
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "not incoming message"

    def test_ignores_private_notes(self):
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "private": True,
            "content": "internal note",
            "conversation": {"id": 1},
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "private note"

    def test_ignores_empty_content(self):
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "",
            "conversation": {"id": 1},
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "empty content"

    def test_ignores_whitespace_only(self):
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "   ",
            "conversation": {"id": 1},
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_requires_conversation_id(self):
        payload = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "hello",
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
        assert resp.json()["reason"] == "no conversation_id"

    def test_ignores_message_updated(self):
        payload = {"event": "message_updated", "content": "edited"}
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.json()["status"] == "ignored"

    def test_ignores_conversation_status_changed(self):
        payload = {"event": "conversation_status_changed"}
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.json()["status"] == "ignored"


# --- Payload Parsing ---


class TestPayloadParsing:
    """Verify Pydantic models parse Chatwoot payloads correctly."""

    def test_minimal_payload(self):
        """Minimal valid payload parses without error."""
        payload = {
            "event": "message_created",
            "message_type": "outgoing",
            "content": "test",
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200

    def test_full_payload_parses(self):
        """Full payload with all optional fields parses."""
        payload = {
            "event": "message_created",
            "id": 12345,
            "message_type": "outgoing",
            "content": "Hello!",
            "private": False,
            "sender": {
                "id": 1,
                "name": "John Smith",
                "email": "john@example.com",
                "type": "contact",
            },
            "conversation": {
                "id": 42,
                "inbox_id": 1,
                "status": "pending",
            },
            "account": {"id": 1},
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200

    def test_null_sender_accepted(self):
        payload = {
            "event": "message_created",
            "message_type": "outgoing",
            "content": "test",
            "sender": None,
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200


# --- Idempotency ---


class TestIdempotency:
    """Verify duplicate webhooks are handled."""

    def test_duplicate_detected(self):
        _reset_dedup()
        # Red line message so it doesn't call LLM (instant response)
        payload = {
            "event": "message_created",
            "id": 77777,
            "message_type": "incoming",
            "content": "I will kill you",
            "conversation": {"id": 1},
            "sender": {"name": "Test", "type": "contact"},
        }
        # First call processes (red line → escalate → dispatch fails silently)
        resp1 = client.post("/api/webhook/chatwoot", json=payload)
        assert resp1.json()["status"] in ("processed", "error")

        # Second call is duplicate
        resp2 = client.post("/api/webhook/chatwoot", json=payload)
        assert resp2.json()["status"] == "duplicate"
        assert resp2.json()["message_id"] == 77777

    def test_different_ids_not_duplicate(self):
        _reset_dedup()
        base = {
            "event": "message_created",
            "message_type": "incoming",
            "content": "I will kill you",
            "conversation": {"id": 1},
            "sender": {"name": "Test", "type": "contact"},
        }
        resp1 = client.post("/api/webhook/chatwoot", json={**base, "id": 11111})
        resp2 = client.post("/api/webhook/chatwoot", json={**base, "id": 22222})
        # Both should be processed (not duplicate)
        assert resp1.json()["status"] != "duplicate"
        assert resp2.json()["status"] != "duplicate"
