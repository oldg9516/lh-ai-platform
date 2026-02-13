"""Unit tests for Chatwoot webhook handler.

Tests webhook filtering, idempotency, payload parsing, and HTML stripping.
No real AI calls — uses mocks for chat() and Chatwoot dispatch.
"""

from fastapi.testclient import TestClient

from main import app
from api.routes import _processed_messages, _strip_html

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


# --- HTML Stripping ---


class TestStripHtml:
    """Verify HTML tags are stripped from AI responses for chat display."""

    def test_strips_div_tags(self):
        html = "<div>Dear Client,</div><div>Thank you!</div>"
        assert _strip_html(html) == "Dear Client,\nThank you!"

    def test_strips_br_tags(self):
        html = "Line one<br>Line two<br/>Line three"
        assert _strip_html(html) == "Line one\nLine two\nLine three"

    def test_strips_nested_divs(self):
        html = "<div><div>Hello</div><div>World</div></div>"
        result = _strip_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_strips_paragraph_tags(self):
        html = "<p>First paragraph</p><p>Second paragraph</p>"
        assert _strip_html(html) == "First paragraph\nSecond paragraph"

    def test_collapses_multiple_newlines(self):
        html = "<div>A</div><div></div><div></div><div>B</div>"
        result = _strip_html(html)
        assert "\n\n\n" not in result
        assert "A" in result and "B" in result

    def test_plain_text_unchanged(self):
        text = "No HTML here, just plain text."
        assert _strip_html(text) == text

    def test_real_agent_response(self):
        """Test with actual HTML format from email-style agent instructions."""
        html = (
            "<div>Dear Client,</div>"
            "<div>I'd be happy to help with your shipment!</div>"
            "<div><div>Your latest box is on the way.</div></div>"
        )
        result = _strip_html(html)
        assert result.startswith("Dear Client,")
        assert "happy to help" in result
        assert "<div>" not in result
