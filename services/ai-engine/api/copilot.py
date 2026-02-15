"""AG-UI Endpoint for CopilotKit Integration.

This module exposes Agno support agents via the AG-UI protocol,
enabling frontend interaction through CopilotKit.

Phase 6.2: AG-UI protocol implementation with typed events
Phase 6.3: HITL tool integration
Phase 7: Multi-turn conversation state

Architecture:
- Frontend (Next.js) → HttpAgent → FastAPI (this endpoint)
- AG-UI protocol with EventEncoder for SSE streaming
- Agno agent streaming transformed to AG-UI events
"""

import asyncio
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import structlog

# AG-UI Protocol imports
try:
    from ag_ui.core import (
        RunAgentInput,
        UserMessage,
        AssistantMessage,
        TextMessageStartEvent,
        TextMessageContentEvent,
        TextMessageEndEvent,
        ToolCallStartEvent,
        ToolCallArgsEvent,
        ToolCallEndEvent,
        RunStartedEvent,
        RunFinishedEvent,
        EventType,
    )
    from ag_ui.encoder import EventEncoder
    AGUI_AVAILABLE = True
except ImportError:
    AGUI_AVAILABLE = False

from agents.support import create_support_agent
from agents.router import classify_message
from tools import TOOL_REGISTRY, WRITE_TOOLS

logger = structlog.get_logger()

router = APIRouter()


# --- Health Check ---


@router.get("/health")
async def copilot_health():
    """Health check for AG-UI endpoint."""
    return {
        "status": "healthy",
        "service": "ag-ui-copilot",
        "agui_available": AGUI_AVAILABLE,
    }


@router.get("/info")
async def runtime_info():
    """Runtime info endpoint for CopilotKit discovery.

    Returns runtime information and available agents.
    Required by CopilotKit for agent discovery and capabilities.
    """
    # CopilotKit expects both id and name fields for agents
    return {
        "version": "0.1.0",
        "runtime": "ag-ui-fastapi",
        "capabilities": ["streaming", "tools", "hitl"],
        "agents__unsafe_dev_only": [
            {
                "id": "default",
                "name": "default",
                "description": "Lev Haolam Support Agent - handles all customer support categories",
            }
        ],
    }


# --- Request Models (Fallback if ag_ui.core not available) ---


class CopilotMessage(BaseModel):
    """Single message in conversation."""
    role: str  # "user" or "assistant"
    content: str


class CopilotRequest(BaseModel):
    """AG-UI protocol request from CopilotKit HttpAgent."""
    messages: list[CopilotMessage]
    threadId: str | None = None
    agent: str | None = "support_agent"


# --- AG-UI Streaming Endpoint ---


@router.post("/")
async def copilot_stream(request: Request):
    """AG-UI streaming endpoint using proper protocol events.

    Accepts POST requests from CopilotKit HttpAgent and streams responses
    using Server-Sent Events (SSE) in AG-UI protocol format.

    Phase 6.2: Text streaming with AG-UI events
    Phase 6.3: Add HITL confirmation flow for write operations
    """
    if not AGUI_AVAILABLE:
        return {
            "error": "AG-UI protocol not available",
            "message": "Install ag-ui-protocol: pip install ag-ui-protocol",
        }

    try:
        # Parse request body
        body = await request.json()

        # Handle CopilotKit protocol methods (info, agent/connect, etc.)
        if "method" in body:
            method = body.get("method")
            logger.info("copilot_protocol_method", method=method, body=body)

            if method == "info":
                return {
                    "version": "0.1.0",
                    "runtime": "ag-ui-fastapi",
                    "capabilities": ["streaming", "tools", "hitl"],
                }

            if method == "agent/connect":
                # Extract agentId from params (CopilotKit sends it there)
                params = body.get("params", {})
                agent_id = params.get("agentId", "default")

                logger.info(
                    "agent_connect_request",
                    agent_id=agent_id,
                    params=params,
                )

                return {
                    "connected": True,
                    "agent": {
                        "id": agent_id,
                        "name": "Lev Haolam Support Agent",
                        "description": "AI agent for customer support",
                        "capabilities": ["streaming", "tools", "hitl"],
                    },
                }

            # Unknown method
            return {"error": f"Unknown method: {method}"}

        # Try parsing as RunAgentInput first (AG-UI native format)
        try:
            agent_input = RunAgentInput(**body)
            messages = agent_input.messages
            thread_id = agent_input.thread_id or str(uuid4())
        except Exception:
            # Fallback to CopilotKit format
            copilot_request = CopilotRequest(**body)
            # Convert to AG-UI message format (each message needs unique ID)
            messages = [
                UserMessage(id=str(uuid4()), content=m.content) if m.role == "user"
                else AssistantMessage(id=str(uuid4()), content=m.content)
                for m in copilot_request.messages
            ]
            thread_id = copilot_request.threadId or str(uuid4())

        logger.info(
            "copilot_stream_start",
            thread_id=thread_id,
            message_count=len(messages),
        )

        # Get last user message
        user_message = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            None,
        )

        if not user_message:
            return StreamingResponse(
                _error_stream("No user message found"),
                media_type="text/event-stream",
            )

        # Create streaming response
        return StreamingResponse(
            _agent_stream(user_message, thread_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except Exception as e:
        logger.error("copilot_stream_error", error=str(e), exc_info=True)
        return StreamingResponse(
            _error_stream(str(e)),
            media_type="text/event-stream",
        )


async def _agent_stream(message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """Stream agent response using AG-UI protocol events.

    Transforms Agno's RunContentEvent → AG-UI typed events.
    """
    encoder = EventEncoder()
    run_id = str(uuid4())
    message_id = str(uuid4())

    try:
        # 1. Emit RUN_STARTED event
        yield encoder.encode(
            RunStartedEvent(
                threadId=thread_id,
                runId=run_id,
            )
        )

        # 2. Classify message to determine category
        router_output = await classify_message(message)
        category = router_output.primary
        customer_email = router_output.email

        logger.info(
            "agent_stream_classified",
            category=category,
            customer_email=customer_email,
            thread_id=thread_id,
        )

        # 3. Build rich customer context
        from agents.context_builder import build_full_context

        customer_context = await build_full_context(
            customer_email=customer_email,
            conversation_history=None,  # TODO: Add conversation history from DB
            outstanding_info=None,  # TODO: Add outstanding detection
        )

        # 4. Create support agent with customer email context
        # use_hitl=True: write tools come from frontend via useHumanInTheLoop
        agent = create_support_agent(category, customer_email=customer_email, use_hitl=True)

        # 5. Prepend context to message
        agent_input = message
        if customer_context:
            agent_input = f"{customer_context}\n\nCustomer message:\n{message}"

        logger.info(
            "agent_input_prepared",
            has_context=bool(customer_context),
            context_length=len(customer_context) if customer_context else 0,
        )

        # 6. Emit TEXT_MESSAGE_START
        yield encoder.encode(
            TextMessageStartEvent(
                messageId=message_id,
            )
        )

        # 7. Stream using Agno's native streaming
        # agent.arun() returns async generator of RunContentEvent objects
        stream = agent.arun(agent_input, stream=True)

        async for chunk in stream:
            # Text content delta → TEXT_MESSAGE_CONTENT
            if hasattr(chunk, "content") and chunk.content:
                yield encoder.encode(
                    TextMessageContentEvent(
                        messageId=message_id,
                        delta=chunk.content,
                    )
                )

            # Tool calls (Phase 6.3 will add HITL confirmation)
            if hasattr(chunk, "tools") and chunk.tools:
                for tool in chunk.tools:
                    tool_call_id = str(uuid4())
                    tool_name = tool.name if hasattr(tool, "name") else str(tool)

                    # TOOL_CALL_START
                    yield encoder.encode(
                        ToolCallStartEvent(
                            toolCallId=tool_call_id,
                            toolCallName=tool_name,
                        )
                    )

                    # TOOL_CALL_ARGS (if available)
                    if hasattr(tool, "args"):
                        import json
                        yield encoder.encode(
                            ToolCallArgsEvent(
                                toolCallId=tool_call_id,
                                delta=json.dumps(tool.args),
                            )
                        )

                    # TOOL_CALL_END
                    yield encoder.encode(
                        ToolCallEndEvent(
                            toolCallId=tool_call_id,
                        )
                    )

        # 6. Emit TEXT_MESSAGE_END
        yield encoder.encode(
            TextMessageEndEvent(
                messageId=message_id,
            )
        )

        # 7. Emit RUN_FINISHED
        yield encoder.encode(
            RunFinishedEvent(
                threadId=thread_id,
                runId=run_id,
            )
        )

        logger.info("agent_stream_complete", thread_id=thread_id, run_id=run_id)

    except Exception as e:
        logger.error(
            "agent_stream_error",
            error=str(e),
            thread_id=thread_id,
            run_id=run_id,
            exc_info=True,
        )
        # Send error as text message
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta=f"\n\n[Error: {str(e)}]",
            )
        )
        yield encoder.encode(
            TextMessageEndEvent(
                messageId=message_id,
            )
        )
        yield encoder.encode(
            RunFinishedEvent(
                threadId=thread_id,
                runId=run_id,
            )
        )


async def _error_stream(error: str) -> AsyncGenerator[str, None]:
    """Stream error message in AG-UI format."""
    encoder = EventEncoder()
    message_id = str(uuid4())

    yield encoder.encode(
        TextMessageStartEvent(
            messageId=message_id,
        )
    )

    yield encoder.encode(
        TextMessageContentEvent(
            messageId=message_id,
            delta=f"Error: {error}",
        )
    )

    yield encoder.encode(
        TextMessageEndEvent(
            messageId=message_id,
        )
    )


# --- HITL Tool Execution Endpoint ---


class ExecuteToolRequest(BaseModel):
    """Request to execute a HITL-approved tool."""
    tool_name: str
    tool_args: dict
    session_id: str | None = None


@router.post("/execute-tool")
async def execute_tool(req: ExecuteToolRequest):
    """Execute a HITL-approved tool after user confirmation.

    Called by the frontend after the user approves a write operation
    in the CopilotKit sidebar. Validates the tool name against the
    whitelist and executes with the provided arguments.
    """
    # Validate tool name is a known write tool
    if req.tool_name not in WRITE_TOOLS:
        logger.warning("execute_tool_rejected", tool_name=req.tool_name, reason="not_a_write_tool")
        return {"status": "error", "message": f"Tool '{req.tool_name}' is not an executable write tool"}

    tool_fn = TOOL_REGISTRY.get(req.tool_name)
    if not tool_fn:
        logger.error("execute_tool_not_found", tool_name=req.tool_name)
        return {"status": "error", "message": f"Tool '{req.tool_name}' not found in registry"}

    try:
        import json as json_lib
        result_str = await tool_fn(**req.tool_args)
        result = json_lib.loads(result_str)

        # Audit log
        try:
            from database.queries import save_tool_execution
            save_tool_execution({
                "session_id": req.session_id or "copilot_hitl",
                "tool_name": req.tool_name,
                "tool_input": req.tool_args,
                "tool_output": result,
                "requires_approval": True,
                "approval_status": "approved",
                "status": "completed",
            })
        except Exception as audit_err:
            logger.warning("audit_log_failed", error=str(audit_err))

        logger.info(
            "execute_tool_success",
            tool_name=req.tool_name,
            session_id=req.session_id,
            result_status=result.get("status"),
        )

        return {"status": "completed", "result": result}

    except Exception as e:
        logger.error("execute_tool_error", tool_name=req.tool_name, error=str(e), exc_info=True)
        return {"status": "error", "message": str(e)}
