"""Tests for Chatwoot API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from chatwoot.client import (
    send_message,
    toggle_conversation_status,
    add_labels,
    assign_conversation,
)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for Chatwoot API calls."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 123, "status": "success"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.patch = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
class TestSendMessage:
    """Tests for send_message function."""

    @patch("chatwoot.client._get_client")
    async def test_public_message(self, mock_get_client, mock_httpx_client):
        """Should send public message with correct payload."""
        mock_get_client.return_value = mock_httpx_client

        result = await send_message(123, "Hello customer", private=False)

        assert result == {"id": 123, "status": "success"}
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert "/conversations/123/messages" in call_args[0][0]
        assert call_args[1]["json"]["content"] == "Hello customer"
        assert call_args[1]["json"]["private"] is False

    @patch("chatwoot.client._get_client")
    async def test_private_note(self, mock_get_client, mock_httpx_client):
        """Should send private note with private=True."""
        mock_get_client.return_value = mock_httpx_client

        result = await send_message(123, "Internal note", private=True)

        assert result == {"id": 123, "status": "success"}
        call_args = mock_httpx_client.post.call_args
        assert call_args[1]["json"]["private"] is True


@pytest.mark.asyncio
class TestToggleStatus:
    """Tests for toggle_conversation_status function."""

    @patch("chatwoot.client._get_client")
    async def test_status_change(self, mock_get_client, mock_httpx_client):
        """Should change conversation status."""
        mock_get_client.return_value = mock_httpx_client

        result = await toggle_conversation_status(123, "open")

        assert result == {"id": 123, "status": "success"}
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert "/conversations/123/toggle_status" in call_args[0][0]
        assert call_args[1]["json"]["status"] == "open"


@pytest.mark.asyncio
class TestAddLabels:
    """Tests for add_labels function."""

    @patch("chatwoot.client._get_client")
    async def test_add_multiple_labels(self, mock_get_client, mock_httpx_client):
        """Should add multiple labels to conversation."""
        mock_get_client.return_value = mock_httpx_client

        result = await add_labels(123, ["ai_escalation", "high_priority"])

        assert result == {"id": 123, "status": "success"}
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert "/conversations/123/labels" in call_args[0][0]
        assert call_args[1]["json"]["labels"] == ["ai_escalation", "high_priority"]


@pytest.mark.asyncio
class TestAssignConversation:
    """Tests for assign_conversation function."""

    @patch("chatwoot.client._get_client")
    async def test_assign_to_agent(self, mock_get_client, mock_httpx_client):
        """Should assign conversation to agent via PATCH."""
        mock_get_client.return_value = mock_httpx_client

        result = await assign_conversation(123, assignee_id=5)

        assert result == {"id": 123, "status": "success"}
        mock_httpx_client.patch.assert_called_once()
        call_args = mock_httpx_client.patch.call_args
        assert "/conversations/123" in call_args[0][0]
        assert call_args[1]["json"]["assignee_id"] == 5

    @patch("chatwoot.client._get_client")
    async def test_assign_logs_action(self, mock_get_client, mock_httpx_client):
        """Should log assignment action."""
        mock_get_client.return_value = mock_httpx_client

        with patch("chatwoot.client.logger") as mock_logger:
            await assign_conversation(456, assignee_id=10)

            mock_logger.info.assert_called_once_with(
                "chatwoot_conversation_assigned",
                conversation_id=456,
                assignee_id=10,
            )
