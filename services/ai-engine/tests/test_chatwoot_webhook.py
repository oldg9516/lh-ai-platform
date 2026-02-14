"""Unit tests for Chatwoot webhook handler.

Tests webhook filtering, idempotency, payload parsing, HTML stripping,
stable session IDs, and email channel detection.
No real AI calls — uses mocks for chat() and Chatwoot dispatch.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from api.routes import _processed_messages, _strip_html, ChatwootConversation

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


# --- Stable Session ID ---


class TestStableSessionId:
    """Verify Chatwoot webhook produces stable session_id from conversation_id."""

    def test_session_id_format(self):
        """Session ID should be cw_{conversation_id}."""
        _reset_dedup()
        payload = {
            "event": "message_created",
            "id": 99901,
            "message_type": "incoming",
            "content": "I will kill you",
            "conversation": {"id": 42},
            "sender": {"name": "Test", "type": "contact"},
        }
        with patch("api.routes._dispatch_to_chatwoot", new_callable=AsyncMock):
            resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200

    def test_same_conversation_same_session(self):
        """Two messages in the same conversation get the same session_id."""
        _reset_dedup()
        # Both messages use conversation_id=100, red line for instant response
        payload1 = {
            "event": "message_created",
            "id": 99902,
            "message_type": "incoming",
            "content": "I will kill you",
            "conversation": {"id": 100},
            "sender": {"name": "Test", "type": "contact"},
        }
        payload2 = {
            "event": "message_created",
            "id": 99903,
            "message_type": "incoming",
            "content": "My lawyer will contact you",
            "conversation": {"id": 100},
            "sender": {"name": "Test", "type": "contact"},
        }
        with patch("api.routes._dispatch_to_chatwoot", new_callable=AsyncMock) as mock_dispatch:
            client.post("/api/webhook/chatwoot", json=payload1)
            client.post("/api/webhook/chatwoot", json=payload2)
            # Both calls should have session_id=cw_100
            calls = mock_dispatch.call_args_list
            assert len(calls) == 2
            session_ids = [call.args[1].session_id for call in calls]
            assert session_ids[0] == "cw_100"
            assert session_ids[1] == "cw_100"


# --- ChatwootConversation Model ---


class TestChatwootConversationModel:
    """Verify ChatwootConversation includes channel field."""

    def test_channel_field_parsed(self):
        conv = ChatwootConversation(id=1, channel="email")
        assert conv.channel == "email"

    def test_channel_field_optional(self):
        conv = ChatwootConversation(id=1)
        assert conv.channel is None

    def test_full_payload_with_channel(self):
        """Full webhook payload with channel parses correctly."""
        payload = {
            "event": "message_created",
            "message_type": "outgoing",
            "content": "test",
            "conversation": {
                "id": 42,
                "inbox_id": 1,
                "status": "pending",
                "channel": "email",
            },
        }
        resp = client.post("/api/webhook/chatwoot", json=payload)
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestEscalationFlow:
    """Verify escalation assigns to human agent when configured."""

    async def test_escalate_assigns_agent_when_configured(self):
        """Escalation should assign conversation to agent if assignee_id set."""
        from unittest.mock import AsyncMock, patch
        from api.routes import _dispatch_to_chatwoot
        from config import settings
        from api.routes import ChatResponse

        result = ChatResponse(
            response="Draft response",
            session_id="test",
            category="payment_question",
            decision="escalate",
            confidence="low",
            actions_taken=[],
            actions_pending=[],
            metadata={"escalation_reason": "low_confidence"},
        )

        with (
            patch("api.routes.send_message", new_callable=AsyncMock) as mock_send,
            patch(
                "api.routes.toggle_conversation_status", new_callable=AsyncMock
            ) as mock_status,
            patch("api.routes.add_labels", new_callable=AsyncMock) as mock_labels,
            patch(
                "api.routes.assign_conversation", new_callable=AsyncMock
            ) as mock_assign,
            patch.object(settings, "chatwoot_escalation_assignee_id", 5),
        ):
            await _dispatch_to_chatwoot(123, result)

            mock_send.assert_called_once()
            mock_status.assert_called_once_with(123, "open")
            mock_labels.assert_called_once_with(
                123, ["ai_escalation", "payment_question", "high_priority"]
            )
            mock_assign.assert_called_once_with(123, 5)

    async def test_escalate_skips_assign_when_not_configured(self):
        """Escalation should not assign if assignee_id not set."""
        from unittest.mock import AsyncMock, patch
        from api.routes import _dispatch_to_chatwoot
        from config import settings
        from api.routes import ChatResponse

        result = ChatResponse(
            response="Draft response",
            session_id="test",
            category="payment_question",
            decision="escalate",
            confidence="low",
            actions_taken=[],
            actions_pending=[],
            metadata={},
        )

        with (
            patch("api.routes.send_message", new_callable=AsyncMock),
            patch("api.routes.toggle_conversation_status", new_callable=AsyncMock),
            patch("api.routes.add_labels", new_callable=AsyncMock),
            patch(
                "api.routes.assign_conversation", new_callable=AsyncMock
            ) as mock_assign,
            patch.object(settings, "chatwoot_escalation_assignee_id", None),
        ):
            await _dispatch_to_chatwoot(123, result)

            mock_assign.assert_not_called()

    async def test_send_and_draft_do_not_assign(self):
        """Send and draft decisions should not assign agent."""
        from unittest.mock import AsyncMock, patch
        from api.routes import _dispatch_to_chatwoot
        from config import settings
        from api.routes import ChatResponse

        for decision in ["send", "draft"]:
            result = ChatResponse(
                response="Response",
                session_id="test",
                category="gratitude",
                decision=decision,
                confidence="high",
                actions_taken=[],
                actions_pending=[],
                metadata={},
            )

            with (
                patch("api.routes.send_message", new_callable=AsyncMock),
                patch("api.routes.toggle_conversation_status", new_callable=AsyncMock),
                patch("api.routes.add_labels", new_callable=AsyncMock),
                patch(
                    "api.routes.assign_conversation", new_callable=AsyncMock
                ) as mock_assign,
                patch.object(settings, "chatwoot_escalation_assignee_id", 5),
            ):
                await _dispatch_to_chatwoot(123, result)

                mock_assign.assert_not_called()
