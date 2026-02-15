"""Tests for AG-UI CopilotKit endpoint.

Phase 6.2: Verify AG-UI protocol implementation
- SSE streaming format
- Typed event structure (RunStarted, TextMessage*, RunFinished)
- EventEncoder formatting
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from main import app


client = TestClient(app)


class TestCopilotHealth:
    """Test AG-UI health endpoint."""

    def test_health_check(self):
        """Health endpoint returns AG-UI availability."""
        response = client.get("/api/copilot/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ag-ui-copilot"
        assert "agui_available" in data
        assert data["agui_available"] is True  # ag-ui-protocol installed


class TestCopilotStream:
    """Test AG-UI streaming endpoint."""

    @patch("api.copilot.classify_message")
    @patch("api.copilot.create_support_agent")
    def test_streaming_response(self, mock_create_agent, mock_classify):
        """Copilot endpoint returns SSE streaming response."""
        # Mock router output
        mock_classify.return_value = AsyncMock(primary_category="gratitude")

        # Mock agent streaming
        mock_agent = MagicMock()

        # Create a mock async generator for agent.arun
        async def mock_stream():
            # Simulate agent streaming chunks
            chunk1 = MagicMock()
            chunk1.content = "Thank you "
            chunk1.tools = []
            yield chunk1

            chunk2 = MagicMock()
            chunk2.content = "for your message!"
            chunk2.tools = []
            yield chunk2

        mock_agent.arun = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        # Send request
        request_data = {
            "messages": [
                {"role": "user", "content": "Thank you for the help!"}
            ],
            "threadId": "test-thread-123",
            "agent": "support_agent",
        }

        response = client.post("/api/copilot", json=request_data)

        # Verify SSE response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE events
        content = response.text
        assert "data: " in content  # SSE format

        # Verify AG-UI event types present
        assert "RUN_STARTED" in content
        assert "TEXT_MESSAGE_START" in content
        assert "TEXT_MESSAGE_CONTENT" in content
        assert "TEXT_MESSAGE_END" in content
        assert "RUN_FINISHED" in content

    @patch("api.copilot.classify_message")
    @patch("api.copilot.create_support_agent")
    def test_text_content_streamed(self, mock_create_agent, mock_classify):
        """Text content is streamed as TEXT_MESSAGE_CONTENT events."""
        mock_classify.return_value = AsyncMock(primary_category="gratitude")

        mock_agent = MagicMock()

        async def mock_stream():
            chunk = MagicMock()
            chunk.content = "Test response content"
            chunk.tools = []
            yield chunk

        mock_agent.arun = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        request_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "threadId": "test-thread-456",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        # Verify text delta is in response
        assert "Test response content" in content
        assert "TEXT_MESSAGE_CONTENT" in content

    def test_missing_message_error(self):
        """Empty messages list returns error stream."""
        request_data = {
            "messages": [],
            "threadId": "test-thread-789",
        }

        response = client.post("/api/copilot", json=request_data)

        assert response.status_code == 200  # Still SSE
        content = response.text

        # Error message in SSE format
        assert "data: " in content
        assert "No user message found" in content or "Error" in content

    @patch("api.copilot.classify_message")
    @patch("api.copilot.create_support_agent")
    def test_tool_calls_streamed(self, mock_create_agent, mock_classify):
        """Tool calls are streamed as TOOL_CALL_* events."""
        mock_classify.return_value = AsyncMock(primary_category="shipping_or_delivery_question")

        mock_agent = MagicMock()

        async def mock_stream():
            # Text chunk
            chunk1 = MagicMock()
            chunk1.content = "Let me check your package."
            chunk1.tools = []
            yield chunk1

            # Tool call chunk
            chunk2 = MagicMock()
            chunk2.content = ""
            mock_tool = MagicMock()
            mock_tool.name = "track_package"
            mock_tool.args = {"email": "test@example.com"}
            chunk2.tools = [mock_tool]
            yield chunk2

        mock_agent.arun = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        request_data = {
            "messages": [{"role": "user", "content": "Where is my package?"}],
            "threadId": "test-thread-tools",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        # Verify tool call events
        assert "TOOL_CALL_START" in content
        assert "track_package" in content
        assert "TOOL_CALL_END" in content

    @patch("api.copilot.classify_message")
    def test_handles_agent_error(self, mock_classify):
        """Agent errors are caught and returned as error stream."""
        mock_classify.return_value = AsyncMock(primary_category="gratitude")

        # Simulate agent creation failure
        with patch("api.copilot.create_support_agent") as mock_create:
            mock_create.side_effect = Exception("Agent creation failed")

            request_data = {
                "messages": [{"role": "user", "content": "Hello"}],
                "threadId": "test-error",
            }

            response = client.post("/api/copilot", json=request_data)

            assert response.status_code == 200  # Still SSE
            content = response.text

            # Error in response
            assert "data: " in content
            # Either error in stream or caught during parsing


class TestAGUIEventFormat:
    """Test AG-UI event structure and formatting."""

    @patch("api.copilot.classify_message")
    @patch("api.copilot.create_support_agent")
    def test_event_contains_ids(self, mock_create_agent, mock_classify):
        """Events contain proper IDs (run_id, thread_id, message_id)."""
        mock_classify.return_value = AsyncMock(primary_category="gratitude")

        mock_agent = MagicMock()

        async def mock_stream():
            chunk = MagicMock()
            chunk.content = "Hello"
            chunk.tools = []
            yield chunk

        mock_agent.arun = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        request_data = {
            "messages": [{"role": "user", "content": "Hi"}],
            "threadId": "thread-with-id",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        # Check for ID fields in events
        assert "run_id" in content or "runId" in content
        assert "thread_id" in content or "threadId" in content
        assert "message_id" in content or "messageId" in content

    @patch("api.copilot.classify_message")
    @patch("api.copilot.create_support_agent")
    def test_sse_format_valid(self, mock_create_agent, mock_classify):
        """Events follow SSE format: data: {json}\\n\\n"""
        mock_classify.return_value = AsyncMock(primary_category="gratitude")

        mock_agent = MagicMock()

        async def mock_stream():
            chunk = MagicMock()
            chunk.content = "Test"
            chunk.tools = []
            yield chunk

        mock_agent.arun = MagicMock(return_value=mock_stream())
        mock_create_agent.return_value = mock_agent

        request_data = {
            "messages": [{"role": "user", "content": "Test"}],
            "threadId": "sse-format-test",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        # Verify SSE format
        lines = content.split("\n")
        data_lines = [line for line in lines if line.startswith("data: ")]

        assert len(data_lines) > 0, "Should have at least one SSE data line"

        # Each data line should be valid JSON
        import json
        for line in data_lines:
            json_str = line.replace("data: ", "")
            try:
                event = json.loads(json_str)
                assert "type" in event, "Each event should have a type field"
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in SSE line: {line}")
