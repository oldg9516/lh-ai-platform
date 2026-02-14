"""Unit tests for database/queries.py.

Tests get_conversation_history with mocked Supabase client.
"""

from unittest.mock import MagicMock, patch

from database.queries import get_conversation_history


def _mock_response(data):
    """Create a mock Supabase response with the given data list."""
    resp = MagicMock()
    resp.data = data
    return resp


def _mock_chain(response):
    """Create a mock Supabase query chain."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = response
    return chain


class TestGetConversationHistory:
    @patch("database.queries.get_client")
    def test_returns_messages(self, mock_get_client):
        messages = [
            {"role": "user", "content": "Where is my package?"},
            {"role": "assistant", "content": "Your package is on its way."},
        ]
        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response(messages))
        mock_get_client.return_value = client

        result = get_conversation_history("cw_42")
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        client.table.assert_called_once_with("chat_messages")

    @patch("database.queries.get_client")
    def test_empty_session(self, mock_get_client):
        client = MagicMock()
        client.table.return_value = _mock_chain(_mock_response([]))
        mock_get_client.return_value = client

        result = get_conversation_history("cw_999")
        assert result == []

    @patch("database.queries.get_client")
    def test_respects_limit(self, mock_get_client):
        client = MagicMock()
        chain = _mock_chain(_mock_response([]))
        client.table.return_value = chain
        mock_get_client.return_value = client

        get_conversation_history("cw_42", limit=5)
        chain.limit.assert_called_with(5)

    @patch("database.queries.get_client")
    def test_orders_by_created_at(self, mock_get_client):
        client = MagicMock()
        chain = _mock_chain(_mock_response([]))
        client.table.return_value = chain
        mock_get_client.return_value = client

        get_conversation_history("cw_42")
        chain.order.assert_called_with("created_at")

    @patch("database.queries.get_client")
    def test_exception_returns_empty(self, mock_get_client):
        mock_get_client.side_effect = RuntimeError("DB down")
        result = get_conversation_history("cw_42")
        assert result == []

    @patch("database.queries.get_client")
    def test_default_limit_is_ten(self, mock_get_client):
        client = MagicMock()
        chain = _mock_chain(_mock_response([]))
        client.table.return_value = chain
        mock_get_client.return_value = client

        get_conversation_history("cw_42")
        chain.limit.assert_called_with(10)
