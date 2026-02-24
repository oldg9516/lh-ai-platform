"""AG-UI Adapter for Dash Analytics Agent.

Translates AgentOS SSE events from Dash (port 9000) into AG-UI protocol
events that CopilotKit can consume. Supports both text streaming and
Generative UI via ToolCall events for render_chart.

Architecture:
  CopilotKit → CopilotRuntime → HttpAgent("dash")
    → This endpoint → httpx stream → dash:9000/agents/dash/runs
    → AgentOS SSE (RunContent / ToolCallCompleted) → AG-UI events → CopilotKit
"""

import json
from os import getenv
from typing import AsyncGenerator
from uuid import uuid4

import httpx
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

try:
    from ag_ui.core import (
        RunAgentInput,
        RunStartedEvent,
        RunFinishedEvent,
        TextMessageStartEvent,
        TextMessageContentEvent,
        TextMessageEndEvent,
        ToolCallStartEvent,
        ToolCallArgsEvent,
        ToolCallEndEvent,
        EventType,
    )

    AGUI_AVAILABLE = True
except ImportError:
    AGUI_AVAILABLE = False

# Try importing EventEncoder — may not exist in all ag-ui-protocol versions
try:
    from ag_ui.encoder import EventEncoder

    _HAS_ENCODER = True
except ImportError:
    _HAS_ENCODER = False

logger = structlog.get_logger()

router = APIRouter()

DASH_URL = getenv("DASH_API_URL", "http://dash:9000")
DASH_STREAM_TIMEOUT_S = 120  # Dash queries can take time (SQL + LLM)

# Tools whose results should be rendered on the frontend via AG-UI ToolCall events
FRONTEND_TOOLS = {"render_chart"}


def _encode_sse(event) -> str:
    """Encode an AG-UI event as SSE data line.

    Fallback when EventEncoder is not available.
    """
    data = event.model_dump(by_alias=True, exclude_none=True)
    if hasattr(event, "type"):
        data["type"] = event.type if isinstance(event.type, str) else event.type.value
    return f"data: {json.dumps(data)}\n\n"


def _get_encoder():
    """Get the best available SSE encoder function."""
    if _HAS_ENCODER:
        try:
            return EventEncoder().encode
        except Exception:
            pass
    return _encode_sse


@router.post("/")
async def dash_copilot_stream(request: Request):
    """AG-UI streaming endpoint that bridges CopilotKit to Dash AgentOS.

    Accepts AG-UI protocol requests, forwards to Dash, translates
    AgentOS SSE events to AG-UI events for CopilotKit rendering.
    Supports text streaming and Generative UI (charts via ToolCall events).
    """
    if not AGUI_AVAILABLE:
        return {
            "error": "AG-UI protocol not available",
            "message": "Install ag-ui-protocol: pip install ag-ui-protocol",
        }

    try:
        body = await request.json()

        # Handle CopilotKit protocol methods
        if "method" in body:
            method = body.get("method")
            if method == "info":
                return {
                    "version": "0.1.0",
                    "runtime": "ag-ui-dash-adapter",
                    "capabilities": ["streaming"],
                }
            if method == "agent/connect":
                return {
                    "connected": True,
                    "agent": {
                        "id": "dash",
                        "name": "Dash Analytics",
                        "description": "Self-learning data agent for customer analytics",
                        "capabilities": ["streaming"],
                    },
                }
            return {"error": f"Unknown method: {method}"}

        # Parse AG-UI messages
        try:
            agent_input = RunAgentInput(**body)
            messages = agent_input.messages
            thread_id = agent_input.thread_id or str(uuid4())
        except Exception:
            raw_messages = body.get("messages", [])
            messages = raw_messages
            thread_id = body.get("threadId", str(uuid4()))

        # Get last user message
        user_message = None
        for m in reversed(messages):
            role = m.role if hasattr(m, "role") else m.get("role", "")
            if role == "user":
                user_message = m.content if hasattr(m, "content") else m.get("content", "")
                break

        if not user_message:
            return StreamingResponse(
                _error_stream("No user message found"),
                media_type="text/event-stream",
            )

        logger.info(
            "dash_copilot_stream",
            thread_id=thread_id,
            message_preview=user_message[:100],
        )

        return StreamingResponse(
            _dash_stream(user_message, thread_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error("dash_copilot_error", error=str(e), exc_info=True)
        return StreamingResponse(
            _error_stream(str(e)),
            media_type="text/event-stream",
        )


async def _dash_stream(
    message: str,
    thread_id: str,
) -> AsyncGenerator[str, None]:
    """Stream Dash response, translating AgentOS SSE → AG-UI events.

    Handles two types of AgentOS events:
    - RunContent: text → TextMessageContentEvent (markdown rendering)
    - ToolCallCompleted for render_chart → ToolCall events (Generative UI)
    """
    encode = _get_encoder()
    run_id = str(uuid4())
    message_id = str(uuid4())
    session_id = f"copilot_{thread_id}"
    text_started = False

    try:
        # 1. Run started
        yield encode(
            RunStartedEvent(threadId=thread_id, runId=run_id)
        )

        # 2. Connect to Dash AgentOS and stream
        content_received = False

        async with httpx.AsyncClient(timeout=httpx.Timeout(DASH_STREAM_TIMEOUT_S)) as client:
            async with client.stream(
                "POST",
                f"{DASH_URL}/agents/dash/runs",
                data={
                    "message": message,
                    "stream": "true",
                    "session_id": session_id,
                    "user_id": "copilot",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    logger.error(
                        "dash_api_error",
                        status=resp.status_code,
                        body=error_text.decode()[:500],
                    )
                    yield encode(TextMessageStartEvent(messageId=message_id))
                    text_started = True
                    yield encode(
                        TextMessageContentEvent(
                            messageId=message_id,
                            delta=f"Error connecting to Dash analytics: HTTP {resp.status_code}",
                        )
                    )
                else:
                    buffer = ""
                    async for chunk in resp.aiter_text():
                        buffer += chunk
                        lines = buffer.split("\n")
                        buffer = lines.pop()  # Keep incomplete line

                        for line in lines:
                            line = line.strip()
                            if not line.startswith("data: "):
                                continue

                            try:
                                event = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue

                            event_type = event.get("event")

                            # --- Text content ---
                            if event_type == "RunContent" and event.get("content"):
                                if not text_started:
                                    yield encode(
                                        TextMessageStartEvent(messageId=message_id)
                                    )
                                    text_started = True
                                content_received = True
                                yield encode(
                                    TextMessageContentEvent(
                                        messageId=message_id,
                                        delta=event["content"],
                                    )
                                )

                            # --- Generative UI: render_chart tool call ---
                            elif event_type == "ToolCallCompleted":
                                tool_name = event.get("tool_name", "")
                                tool_result = event.get("result", "")

                                if tool_name in FRONTEND_TOOLS:
                                    # End current text message if in progress
                                    if text_started:
                                        yield encode(
                                            TextMessageEndEvent(messageId=message_id)
                                        )
                                        text_started = False
                                        message_id = str(uuid4())

                                    # Parse tool result
                                    try:
                                        result_data = json.loads(tool_result)
                                    except (json.JSONDecodeError, TypeError):
                                        result_data = {}

                                    tool_call_id = f"tc_{uuid4().hex[:12]}"

                                    # Build args matching frontend useRenderToolCall parameters
                                    args_payload = json.dumps({
                                        "chart_type": result_data.get("chart_type", "bar"),
                                        "title": result_data.get("title", ""),
                                        "data": json.dumps(result_data.get("data", [])),
                                        "x_key": result_data.get("x_key", ""),
                                        "y_keys": ",".join(result_data.get("y_keys", [])),
                                    })

                                    # Emit AG-UI ToolCall triple: Start → Args → End
                                    yield encode(
                                        ToolCallStartEvent(
                                            type=EventType.TOOL_CALL_START,
                                            toolCallId=tool_call_id,
                                            toolCallName=tool_name,
                                        )
                                    )
                                    yield encode(
                                        ToolCallArgsEvent(
                                            type=EventType.TOOL_CALL_ARGS,
                                            toolCallId=tool_call_id,
                                            delta=args_payload,
                                        )
                                    )
                                    yield encode(
                                        ToolCallEndEvent(
                                            type=EventType.TOOL_CALL_END,
                                            toolCallId=tool_call_id,
                                        )
                                    )

                                    content_received = True
                                    logger.info(
                                        "dash_chart_emitted",
                                        tool=tool_name,
                                        chart_type=result_data.get("chart_type"),
                                    )

        # Handle empty response
        if not content_received:
            if not text_started:
                yield encode(TextMessageStartEvent(messageId=message_id))
                text_started = True
            yield encode(
                TextMessageContentEvent(
                    messageId=message_id,
                    delta="No response from analytics agent. Please try again.",
                )
            )

        # Close open text message
        if text_started:
            yield encode(TextMessageEndEvent(messageId=message_id))

        # Run finished
        yield encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )

        logger.info("dash_copilot_complete", thread_id=thread_id)

    except httpx.ConnectError:
        logger.error("dash_connect_error", url=DASH_URL)
        if not text_started:
            yield encode(TextMessageStartEvent(messageId=message_id))
        yield encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta="Cannot connect to Dash analytics service. Make sure it's running.",
            )
        )
        yield encode(TextMessageEndEvent(messageId=message_id))
        yield encode(RunFinishedEvent(threadId=thread_id, runId=run_id))

    except Exception as e:
        logger.error("dash_stream_error", error=str(e), exc_info=True)
        if not text_started:
            yield encode(TextMessageStartEvent(messageId=message_id))
        yield encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta=f"Error: {e}",
            )
        )
        yield encode(TextMessageEndEvent(messageId=message_id))
        yield encode(RunFinishedEvent(threadId=thread_id, runId=run_id))


async def _error_stream(error: str) -> AsyncGenerator[str, None]:
    """Stream error in AG-UI format."""
    encode = _get_encoder()
    message_id = str(uuid4())
    run_id = str(uuid4())
    thread_id = str(uuid4())

    yield encode(RunStartedEvent(threadId=thread_id, runId=run_id))
    yield encode(TextMessageStartEvent(messageId=message_id))
    yield encode(
        TextMessageContentEvent(messageId=message_id, delta=f"Error: {error}")
    )
    yield encode(TextMessageEndEvent(messageId=message_id))
    yield encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
