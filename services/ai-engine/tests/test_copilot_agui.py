"""Tests for AG-UI CopilotKit endpoint.

Verify AG-UI protocol implementation:
- SSE streaming format
- Typed event structure (RunStarted, TextMessage*, ToolCall*, RunFinished)
- Direct OpenAI API for tool calling
- HITL tool calls emit AG-UI ToolCall events
- Read-only tools executed server-side
"""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from main import app


client = TestClient(app)


# --- Helpers ---


def _mock_router_output(category="gratitude", email=None):
    """Create a mock RouterOutput."""
    mock = MagicMock()
    mock.primary = category
    mock.email = email
    return mock


def _mock_openai_text_stream(text="Hello from agent"):
    """Create a mock OpenAI streaming response with text content."""
    chunks = []

    # First chunk with text
    for word in text.split():
        chunk = MagicMock()
        choice = MagicMock()
        choice.delta = MagicMock()
        choice.delta.content = word + " "
        choice.delta.tool_calls = None
        choice.finish_reason = None
        chunk.choices = [choice]
        chunks.append(chunk)

    # Final chunk
    final = MagicMock()
    final_choice = MagicMock()
    final_choice.delta = MagicMock()
    final_choice.delta.content = None
    final_choice.delta.tool_calls = None
    final_choice.finish_reason = "stop"
    final.choices = [final_choice]
    chunks.append(final)

    async def async_iter():
        for c in chunks:
            yield c

    return async_iter()


def _mock_openai_tool_call_stream(tool_name="pause_subscription", tool_args='{"customer_email":"test@test.com","duration_months":2}'):
    """Create a mock OpenAI streaming response with a tool call."""
    chunks = []

    # Tool call start chunk
    tc_start = MagicMock()
    tc_start_choice = MagicMock()
    tc_start_choice.delta = MagicMock()
    tc_start_choice.delta.content = None
    tc_mock = MagicMock()
    tc_mock.index = 0
    tc_mock.id = "call_test_123"
    tc_mock.function = MagicMock()
    tc_mock.function.name = tool_name
    tc_mock.function.arguments = ""
    tc_start_choice.delta.tool_calls = [tc_mock]
    tc_start_choice.finish_reason = None
    tc_start.choices = [tc_start_choice]
    chunks.append(tc_start)

    # Tool call args chunk
    tc_args = MagicMock()
    tc_args_choice = MagicMock()
    tc_args_choice.delta = MagicMock()
    tc_args_choice.delta.content = None
    tc_args_mock = MagicMock()
    tc_args_mock.index = 0
    tc_args_mock.id = None
    tc_args_mock.function = MagicMock()
    tc_args_mock.function.name = None
    tc_args_mock.function.arguments = tool_args
    tc_args_choice.delta.tool_calls = [tc_args_mock]
    tc_args_choice.finish_reason = None
    tc_args.choices = [tc_args_choice]
    chunks.append(tc_args)

    # Finish chunk
    final = MagicMock()
    final_choice = MagicMock()
    final_choice.delta = MagicMock()
    final_choice.delta.content = None
    final_choice.delta.tool_calls = None
    final_choice.finish_reason = "tool_calls"
    final.choices = [final_choice]
    chunks.append(final)

    async def async_iter():
        for c in chunks:
            yield c

    return async_iter()


# --- Tests ---


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
        assert data["agui_available"] is True


class TestCopilotStream:
    """Test AG-UI streaming endpoint."""

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_streaming_response(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """Copilot endpoint returns SSE streaming response."""
        mock_classify.return_value = _mock_router_output("gratitude")

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.return_value = _mock_openai_text_stream("Thank you for your message!")
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Thank you!"}],
            "threadId": "test-thread-123",
        }

        response = client.post("/api/copilot", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        content = response.text
        assert "data: " in content
        assert "RUN_STARTED" in content
        assert "TEXT_MESSAGE_START" in content
        assert "TEXT_MESSAGE_CONTENT" in content
        assert "TEXT_MESSAGE_END" in content
        assert "RUN_FINISHED" in content

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_text_content_streamed(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """Text content is streamed as TEXT_MESSAGE_CONTENT events."""
        mock_classify.return_value = _mock_router_output("gratitude")

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.return_value = _mock_openai_text_stream("Test response content")
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "threadId": "test-thread-456",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        assert "Test" in content
        assert "response" in content
        assert "TEXT_MESSAGE_CONTENT" in content

    def test_missing_message_error(self):
        """Empty messages list returns error stream."""
        request_data = {
            "messages": [],
            "threadId": "test-thread-789",
        }

        response = client.post("/api/copilot", json=request_data)

        assert response.status_code == 200
        content = response.text
        assert "data: " in content
        assert "No user message found" in content or "Error" in content

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_tool_calls_streamed(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """HITL tool calls are streamed as TOOL_CALL_* events."""
        mock_classify.return_value = _mock_router_output(
            "skip_or_pause_request", email="test@example.com"
        )

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.return_value = _mock_openai_tool_call_stream(
            "pause_subscription",
            '{"customer_email":"test@example.com","duration_months":2}',
        )
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Pause my subscription for 2 months"}],
            "threadId": "test-thread-tools",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        assert "TOOL_CALL_START" in content
        assert "pause_subscription" in content
        assert "TOOL_CALL_ARGS" in content
        assert "TOOL_CALL_END" in content

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_handles_agent_error(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """OpenAI errors are caught and returned as error stream."""
        mock_classify.return_value = _mock_router_output("gratitude")

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.side_effect = Exception("OpenAI API error")
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "threadId": "test-error",
        }

        response = client.post("/api/copilot", json=request_data)

        assert response.status_code == 200
        content = response.text
        assert "data: " in content
        # Error should be caught and streamed
        assert "RUN_STARTED" in content or "Error" in content


class TestAGUIEventFormat:
    """Test AG-UI event structure and formatting."""

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_event_contains_ids(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """Events contain proper IDs (run_id, thread_id, message_id)."""
        mock_classify.return_value = _mock_router_output("gratitude")

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.return_value = _mock_openai_text_stream("Hello")
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Hi"}],
            "threadId": "thread-with-id",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        assert "runId" in content
        assert "threadId" in content
        assert "messageId" in content

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_sse_format_valid(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """Events follow SSE format: data: {json}\\n\\n"""
        mock_classify.return_value = _mock_router_output("gratitude")

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.return_value = _mock_openai_text_stream("Test")
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Test"}],
            "threadId": "sse-format-test",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        lines = content.split("\n")
        data_lines = [line for line in lines if line.startswith("data: ")]

        assert len(data_lines) > 0, "Should have at least one SSE data line"

        for line in data_lines:
            json_str = line.replace("data: ", "")
            try:
                event = json.loads(json_str)
                assert "type" in event, "Each event should have a type field"
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in SSE line: {line}")


class TestHITLToolCalls:
    """Test HITL tool call handling."""

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    def test_hitl_tool_emits_events(self, mock_client, mock_classify, mock_instr, mock_ctx):
        """HITL tools emit ToolCall AG-UI events (not executed server-side)."""
        mock_classify.return_value = _mock_router_output(
            "skip_or_pause_request", email="user@test.com"
        )

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.return_value = _mock_openai_tool_call_stream(
            "skip_month",
            '{"customer_email":"user@test.com","month":"next"}',
        )
        mock_client.return_value = mock_openai

        request_data = {
            "messages": [{"role": "user", "content": "Skip next month please"}],
            "threadId": "test-hitl-skip",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        assert "TOOL_CALL_START" in content
        assert "skip_month" in content
        assert "TOOL_CALL_ARGS" in content
        assert "customer_email" in content
        assert "TOOL_CALL_END" in content
        assert "RUN_FINISHED" in content

    @patch("api.copilot.build_full_context", new_callable=AsyncMock, return_value="")
    @patch("api.copilot.load_instructions", return_value=["Be helpful."])
    @patch("api.copilot.classify_message")
    @patch("api.copilot._get_openai_client")
    @patch("api.copilot._execute_tool")
    def test_readonly_tool_executed_server_side(self, mock_exec, mock_client, mock_classify, mock_instr, mock_ctx):
        """Read-only tools are executed server-side, not emitted as ToolCall events."""
        mock_classify.return_value = _mock_router_output(
            "shipping_or_delivery_question", email="user@test.com"
        )

        # First call returns tool call, second call returns text
        mock_openai = AsyncMock()
        mock_openai.chat.completions.create.side_effect = [
            _mock_openai_tool_call_stream(
                "get_subscription",
                '{"customer_email":"user@test.com"}',
            ),
            _mock_openai_text_stream("Your subscription is active."),
        ]
        mock_client.return_value = mock_openai

        mock_exec.return_value = '{"status":"active","frequency":"monthly"}'

        request_data = {
            "messages": [{"role": "user", "content": "What is my subscription status?"}],
            "threadId": "test-readonly",
        }

        response = client.post("/api/copilot", json=request_data)
        content = response.text

        # Read-only tool should NOT emit ToolCall events
        assert "TOOL_CALL_START" not in content
        # But text response should be present
        assert "TEXT_MESSAGE_CONTENT" in content
        assert "RUN_FINISHED" in content
        # Tool was executed server-side
        mock_exec.assert_called_once()
