"""AG-UI Adapter for Dash Analytics Agent.

Translates AgentOS SSE events from Dash (port 9000) into AG-UI protocol
events that CopilotKit can consume. This enables CopilotKit's native
markdown rendering for Dash analytics responses.

Architecture:
  CopilotKit → CopilotRuntime → HttpAgent("dash")
    → This endpoint → httpx stream → dash:9000/agents/dash/runs
    → AgentOS SSE (RunContent) → AG-UI (TextMessage*) → CopilotKit
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
    )
    from ag_ui.encoder import EventEncoder

    AGUI_AVAILABLE = True
except ImportError:
    AGUI_AVAILABLE = False

logger = structlog.get_logger()

router = APIRouter()

DASH_URL = getenv("DASH_API_URL", "http://dash:9000")
DASH_STREAM_TIMEOUT_S = 120  # Dash queries can take time (SQL + LLM)


@router.post("/")
async def dash_copilot_stream(request: Request):
    """AG-UI streaming endpoint that bridges CopilotKit to Dash AgentOS.

    Accepts AG-UI protocol requests, forwards to Dash, translates
    AgentOS SSE events to AG-UI events for CopilotKit markdown rendering.
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
            # Fallback: extract messages directly
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
    """Stream Dash response, translating AgentOS SSE → AG-UI events."""
    encoder = EventEncoder()
    run_id = str(uuid4())
    message_id = str(uuid4())
    session_id = f"copilot_{thread_id}"

    try:
        # 1. Run started
        yield encoder.encode(
            RunStartedEvent(threadId=thread_id, runId=run_id)
        )

        # 2. Start text message
        yield encoder.encode(
            TextMessageStartEvent(messageId=message_id)
        )

        # 3. Connect to Dash AgentOS and stream
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
                    yield encoder.encode(
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

                            # Only forward RunContent events with actual text
                            if (
                                event.get("event") == "RunContent"
                                and event.get("content")
                            ):
                                content_received = True
                                yield encoder.encode(
                                    TextMessageContentEvent(
                                        messageId=message_id,
                                        delta=event["content"],
                                    )
                                )

        if not content_received:
            yield encoder.encode(
                TextMessageContentEvent(
                    messageId=message_id,
                    delta="No response from analytics agent. Please try again.",
                )
            )

        # 4. End text message
        yield encoder.encode(
            TextMessageEndEvent(messageId=message_id)
        )

        # 5. Run finished
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )

        logger.info("dash_copilot_complete", thread_id=thread_id)

    except httpx.ConnectError:
        logger.error("dash_connect_error", url=DASH_URL)
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta="Cannot connect to Dash analytics service. Make sure it's running.",
            )
        )
        yield encoder.encode(TextMessageEndEvent(messageId=message_id))
        yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))

    except Exception as e:
        logger.error("dash_stream_error", error=str(e), exc_info=True)
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta=f"Error: {e}",
            )
        )
        yield encoder.encode(TextMessageEndEvent(messageId=message_id))
        yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))


async def _error_stream(error: str) -> AsyncGenerator[str, None]:
    """Stream error in AG-UI format."""
    encoder = EventEncoder()
    message_id = str(uuid4())
    run_id = str(uuid4())
    thread_id = str(uuid4())

    yield encoder.encode(RunStartedEvent(threadId=thread_id, runId=run_id))
    yield encoder.encode(TextMessageStartEvent(messageId=message_id))
    yield encoder.encode(
        TextMessageContentEvent(messageId=message_id, delta=f"Error: {error}")
    )
    yield encoder.encode(TextMessageEndEvent(messageId=message_id))
    yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
