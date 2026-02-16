"""AG-UI Endpoint for CopilotKit Integration.

This module exposes support agents via the AG-UI protocol,
enabling frontend interaction through CopilotKit.

Architecture:
- Frontend (Next.js) -> HttpAgent -> FastAPI (this endpoint)
- AG-UI protocol with EventEncoder for SSE streaming
- Direct OpenAI API for tool calling (bypasses Agno to emit proper ToolCall events)
- HITL tools -> AG-UI ToolCallStart/Args/End -> CopilotKit renders forms
- Read-only tools -> executed server-side, results fed back to LLM
"""

import asyncio
import inspect
import json as json_lib
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
        ToolMessage,
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

from openai import AsyncOpenAI

from agents.config import CATEGORY_CONFIG
from agents.context_builder import build_full_context
from agents.instructions import load_instructions
from agents.router import classify_message
from config import settings
from tools import TOOL_REGISTRY, WRITE_TOOLS

logger = structlog.get_logger()

router = APIRouter()


# --- OpenAI Client (singleton) ---

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Get or create a singleton AsyncOpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


# --- HITL Tool Names (handled by CopilotKit frontend forms) ---

HITL_TOOL_NAMES: set[str] = {
    "pause_subscription",
    "skip_month",
    "change_frequency",
    "change_address",
    "create_damage_claim",
}

# --- Display Tool Names (rendered as rich widgets on frontend) ---

DISPLAY_TOOL_NAMES: set[str] = {
    "display_tracking",
    "display_orders",
    "display_box_contents",
    "display_payments",
}

# Tools that should be emitted as AG-UI ToolCall events (not executed server-side)
FRONTEND_TOOL_NAMES: set[str] = HITL_TOOL_NAMES | DISPLAY_TOOL_NAMES


# --- OpenAI Function Schemas ---

OPENAI_TOOL_SCHEMAS: dict[str, dict] = {
    "get_subscription": {
        "type": "function",
        "function": {
            "name": "get_subscription",
            "description": "Get active subscription details for a customer. Returns next charge date, frequency, status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "get_customer_history": {
        "type": "function",
        "function": {
            "name": "get_customer_history",
            "description": "Get customer order history, tracking, and support interactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "get_payment_history": {
        "type": "function",
        "function": {
            "name": "get_payment_history",
            "description": "Get payment dates, amounts, and methods for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "months": {"type": "number", "description": "Number of months to look back (default 6)"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "track_package": {
        "type": "function",
        "function": {
            "name": "track_package",
            "description": "Get tracking number, carrier, status, and estimated delivery for latest package.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "get_box_contents": {
        "type": "function",
        "function": {
            "name": "get_box_contents",
            "description": "Get the products included in the customer's last box.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "pause_subscription": {
        "type": "function",
        "function": {
            "name": "pause_subscription",
            "description": "Pause customer subscription for specified duration. A confirmation form will appear for the customer to review and approve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "duration_months": {"type": "number", "description": "Number of months to pause (1-12)"},
                },
                "required": ["customer_email", "duration_months"],
            },
        },
    },
    "skip_month": {
        "type": "function",
        "function": {
            "name": "skip_month",
            "description": "Skip one month of customer subscription delivery. A confirmation form will appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "month": {"type": "string", "description": "Which month to skip. Default 'next'."},
                },
                "required": ["customer_email"],
            },
        },
    },
    "change_frequency": {
        "type": "function",
        "function": {
            "name": "change_frequency",
            "description": "Change subscription delivery frequency. A confirmation form will appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "new_frequency": {"type": "string", "description": "Desired frequency: 'monthly', 'bi-monthly', or 'quarterly'"},
                },
                "required": ["customer_email", "new_frequency"],
            },
        },
    },
    "change_address": {
        "type": "function",
        "function": {
            "name": "change_address",
            "description": "Update customer shipping address. A confirmation form will appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "new_address": {"type": "string", "description": "Full new shipping address"},
                },
                "required": ["customer_email", "new_address"],
            },
        },
    },
    "create_damage_claim": {
        "type": "function",
        "function": {
            "name": "create_damage_claim",
            "description": "Create a damage claim for a damaged or leaking item. A confirmation form will appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "item_description": {"type": "string", "description": "Which item was damaged"},
                    "damage_description": {"type": "string", "description": "Description of the damage"},
                },
                "required": ["customer_email", "item_description", "damage_description"],
            },
        },
    },
    "request_photos": {
        "type": "function",
        "function": {
            "name": "request_photos",
            "description": "Request damage photos from customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                    "claim_id": {"type": "string", "description": "Claim ID if available"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "generate_cancel_link": {
        "type": "function",
        "function": {
            "name": "generate_cancel_link",
            "description": "Generate a self-service cancellation link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subscription_id": {"type": "string", "description": "Subscription ID"},
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["subscription_id", "customer_email"],
            },
        },
    },
    # --- Display Tools (informational widgets rendered on frontend) ---
    "display_tracking": {
        "type": "function",
        "function": {
            "name": "display_tracking",
            "description": "Display a rich tracking widget to the customer showing package tracking information. Call this AFTER calling track_package to show the data visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "display_orders": {
        "type": "function",
        "function": {
            "name": "display_orders",
            "description": "Display a rich order history widget to the customer. Call this AFTER calling get_customer_history to show the data visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "display_box_contents": {
        "type": "function",
        "function": {
            "name": "display_box_contents",
            "description": "Display a rich widget showing the contents of the customer's last box. Call this AFTER calling get_box_contents to show the data visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
    "display_payments": {
        "type": "function",
        "function": {
            "name": "display_payments",
            "description": "Display a rich payment history widget to the customer. Call this AFTER calling get_payment_history to show the data visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["customer_email"],
            },
        },
    },
}


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
    """Runtime info endpoint for CopilotKit discovery."""
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
    role: str
    content: str


class CopilotRequest(BaseModel):
    """AG-UI protocol request from CopilotKit HttpAgent."""
    messages: list[CopilotMessage]
    threadId: str | None = None
    agent: str | None = "support_agent"


# --- AG-UI Streaming Endpoint ---


@router.post("/")
async def copilot_stream(request: Request):
    """AG-UI streaming endpoint.

    Accepts POST requests from CopilotKit HttpAgent and streams responses
    using Server-Sent Events (SSE) in AG-UI protocol format.

    Uses direct OpenAI API for tool calling so ToolCall events are properly
    emitted for CopilotKit to intercept and render HITL forms.
    """
    if not AGUI_AVAILABLE:
        return {
            "error": "AG-UI protocol not available",
            "message": "Install ag-ui-protocol: pip install ag-ui-protocol",
        }

    try:
        body = await request.json()

        # Handle CopilotKit protocol methods (info, agent/connect, etc.)
        if "method" in body:
            method = body.get("method")
            logger.info("copilot_protocol_method", method=method)

            if method == "info":
                return {
                    "version": "0.1.0",
                    "runtime": "ag-ui-fastapi",
                    "capabilities": ["streaming", "tools", "hitl"],
                }

            if method == "agent/connect":
                params = body.get("params", {})
                agent_id = params.get("agentId", "default")
                logger.info("agent_connect_request", agent_id=agent_id)
                return {
                    "connected": True,
                    "agent": {
                        "id": agent_id,
                        "name": "Lev Haolam Support Agent",
                        "description": "AI agent for customer support",
                        "capabilities": ["streaming", "tools", "hitl"],
                    },
                }

            return {"error": f"Unknown method: {method}"}

        # Parse messages from request
        try:
            agent_input = RunAgentInput(**body)
            messages = agent_input.messages
            thread_id = agent_input.thread_id or str(uuid4())
        except Exception:
            copilot_request = CopilotRequest(**body)
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
            message_roles=[m.role for m in messages],
        )

        # Check if this is a tool result continuation
        # Only treat as continuation if the LAST message is a ToolMessage.
        # Using any() would catch ALL subsequent requests because old ToolMessages
        # remain in CopilotKit's conversation history.
        last_msg = messages[-1] if messages else None
        is_tool_result_continuation = last_msg is not None and last_msg.role == "tool"

        if is_tool_result_continuation:
            logger.info("copilot_tool_result_continuation", thread_id=thread_id)
            return StreamingResponse(
                _tool_result_stream(messages, thread_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
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

        return StreamingResponse(
            _agent_stream(user_message, thread_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error("copilot_stream_error", error=str(e), exc_info=True)
        return StreamingResponse(
            _error_stream(str(e)),
            media_type="text/event-stream",
        )


async def _execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a read-only tool and return its result as a string.

    Handles both sync and async tools from TOOL_REGISTRY.
    """
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if not tool_fn:
        return json_lib.dumps({"error": f"Tool '{tool_name}' not found"})

    try:
        result = tool_fn(**tool_args)
        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception as e:
        logger.error("tool_execution_error", tool=tool_name, error=str(e))
        return json_lib.dumps({"error": str(e)})


async def _agent_stream(message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """Stream agent response using AG-UI protocol events.

    Uses OpenAI API directly (not Agno) so we can properly detect tool calls
    and emit AG-UI ToolCall events. This is critical for CopilotKit HITL:
    - HITL tools (pause, skip, change, etc.) -> AG-UI ToolCall events -> frontend forms
    - Read-only tools (get_subscription, etc.) -> executed server-side, fed back to LLM
    """
    encoder = EventEncoder()
    run_id = str(uuid4())

    try:
        # 1. Emit RUN_STARTED
        yield encoder.encode(
            RunStartedEvent(threadId=thread_id, runId=run_id)
        )

        # 2. Classify message
        router_output = await classify_message(message)
        category = router_output.primary
        customer_email = router_output.email

        logger.info(
            "copilot_classified",
            category=category,
            customer_email=customer_email,
            thread_id=thread_id,
        )

        # 3. Build customer context
        customer_context = await build_full_context(
            customer_email=customer_email,
            conversation_history=None,
            outstanding_info=None,
        )

        # 4. Load instructions from DB
        instructions = load_instructions(category)
        config = CATEGORY_CONFIG[category]

        # Add customer email context
        if customer_email:
            instructions.append(
                f"\n\nIMPORTANT: Customer email for this conversation: {customer_email}\n"
                f"When calling tools that require customer_email parameter, use this email address."
            )

        # Add HITL instructions
        instructions.append(
            "\n\nHUMAN-IN-THE-LOOP TOOLS:\n"
            "You have tools that require customer confirmation before execution. "
            "When the customer wants to pause, skip, change frequency, change address, "
            "or report damage, you MUST call the appropriate tool immediately. "
            "Do NOT tell the customer to visit a website or portal. "
            "Do NOT give step-by-step manual instructions. "
            "ALWAYS call the tool directly when you have the needed information. "
            "If you need the customer's email, ask for it first, then call the tool."
        )

        # Add display widget instructions
        instructions.append(
            "\n\nDISPLAY WIDGETS:\n"
            "You have display tools (display_tracking, display_orders, display_box_contents, display_payments) "
            "that render rich visual widgets in the chat. ALWAYS use them after fetching data:\n"
            "- After calling track_package, also call display_tracking to show tracking visually.\n"
            "- After calling get_customer_history, also call display_orders to show order history.\n"
            "- After calling get_box_contents, also call display_box_contents to show box items.\n"
            "- After calling get_payment_history, also call display_payments to show payment timeline.\n"
            "Call the display tool in the SAME turn as the data fetch tool. "
            "Still include a brief text summary in your response."
        )

        system_prompt = "\n\n".join(instructions)

        # 5. Build user content with context
        user_content = message
        if customer_context:
            user_content = f"{customer_context}\n\nCustomer message:\n{message}"

        # 6. Build OpenAI messages
        openai_messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # 7. Get tool schemas for this category + display tools
        # Map read-only tools to their corresponding display widgets
        READ_TO_DISPLAY = {
            "track_package": "display_tracking",
            "get_customer_history": "display_orders",
            "get_box_contents": "display_box_contents",
            "get_payment_history": "display_payments",
        }

        openai_tools = []
        display_tools_to_add: set[str] = set()
        if config.tools:
            for name in config.tools:
                schema = OPENAI_TOOL_SCHEMAS.get(name)
                if schema:
                    openai_tools.append(schema)
                # Track which display tools to add
                if name in READ_TO_DISPLAY:
                    display_tools_to_add.add(READ_TO_DISPLAY[name])

        # Add display tool schemas
        for display_name in display_tools_to_add:
            schema = OPENAI_TOOL_SCHEMAS.get(display_name)
            if schema:
                openai_tools.append(schema)

        logger.info(
            "copilot_openai_call",
            model=config.model,
            tools_count=len(openai_tools),
            tool_names=config.tools,
        )

        # 8. Stream from OpenAI with tool-call loop
        client = _get_openai_client()
        max_iterations = 5  # Prevent infinite tool loops

        for iteration in range(max_iterations):
            message_id = str(uuid4())

            kwargs: dict = {
                "model": config.model,
                "messages": openai_messages,
                "stream": True,
            }
            if openai_tools:
                kwargs["tools"] = openai_tools

            response = await client.chat.completions.create(**kwargs)

            text_started = False
            accumulated_tool_calls: dict[int, dict] = {}

            async for chunk in response:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Stream text content
                if delta and delta.content:
                    if not text_started:
                        yield encoder.encode(
                            TextMessageStartEvent(messageId=message_id)
                        )
                        text_started = True
                    yield encoder.encode(
                        TextMessageContentEvent(
                            messageId=message_id,
                            delta=delta.content,
                        )
                    )

                # Accumulate tool calls
                if delta and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc.id or str(uuid4()),
                                "name": "",
                                "args": "",
                            }
                        if tc.function and tc.function.name:
                            accumulated_tool_calls[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            accumulated_tool_calls[idx]["args"] += tc.function.arguments

            # Close text message if open
            if text_started:
                yield encoder.encode(
                    TextMessageEndEvent(messageId=message_id)
                )

            # No tool calls -> done
            if not accumulated_tool_calls:
                break

            # Process tool calls
            hitl_emitted = False
            read_only_results = []

            # Build the assistant message with all tool calls for OpenAI conversation
            assistant_tool_calls = []
            for idx in sorted(accumulated_tool_calls.keys()):
                tc = accumulated_tool_calls[idx]
                assistant_tool_calls.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["args"],
                    },
                })

            for idx in sorted(accumulated_tool_calls.keys()):
                tc = accumulated_tool_calls[idx]
                tool_name = tc["name"]
                tool_args_str = tc["args"]

                try:
                    tool_args = json_lib.loads(tool_args_str) if tool_args_str else {}
                except json_lib.JSONDecodeError:
                    tool_args = {}

                logger.info(
                    "copilot_tool_call",
                    tool=tool_name,
                    args=tool_args,
                    is_hitl=tool_name in FRONTEND_TOOL_NAMES,
                    iteration=iteration,
                )

                if tool_name in FRONTEND_TOOL_NAMES:
                    # HITL tool: emit AG-UI ToolCall events for CopilotKit
                    yield encoder.encode(
                        ToolCallStartEvent(
                            toolCallId=tc["id"],
                            toolCallName=tool_name,
                        )
                    )
                    yield encoder.encode(
                        ToolCallArgsEvent(
                            toolCallId=tc["id"],
                            delta=tool_args_str,
                        )
                    )
                    yield encoder.encode(
                        ToolCallEndEvent(
                            toolCallId=tc["id"],
                        )
                    )
                    hitl_emitted = True
                else:
                    # Read-only tool: execute server-side
                    result = await _execute_tool(tool_name, tool_args)
                    read_only_results.append((tc["id"], tool_name, result))

            # If HITL tool was emitted, stop the loop.
            # CopilotKit will handle the form and send a new request.
            if hitl_emitted:
                break

            # Feed read-only results back to OpenAI for next iteration
            if read_only_results:
                openai_messages.append({
                    "role": "assistant",
                    "tool_calls": assistant_tool_calls,
                })
                for tool_call_id, tool_name, result in read_only_results:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result,
                    })

        # 9. Emit RUN_FINISHED
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )

        logger.info("copilot_stream_complete", thread_id=thread_id, run_id=run_id)

    except Exception as e:
        logger.error(
            "copilot_stream_error",
            error=str(e),
            thread_id=thread_id,
            run_id=run_id,
            exc_info=True,
        )
        error_message_id = str(uuid4())
        yield encoder.encode(
            TextMessageStartEvent(messageId=error_message_id)
        )
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=error_message_id,
                delta=f"I apologize, but I encountered an error processing your request. Please try again.",
            )
        )
        yield encoder.encode(
            TextMessageEndEvent(messageId=error_message_id)
        )
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )


async def _tool_result_stream(messages: list, thread_id: str) -> AsyncGenerator[str, None]:
    """Handle tool result continuation from CopilotKit.

    When the user responds to a HITL form, CopilotKit sends back the full
    conversation including the tool result. We forward this to OpenAI so
    the LLM can generate a final text response acknowledging the action.
    """
    encoder = EventEncoder()
    run_id = str(uuid4())

    try:
        yield encoder.encode(
            RunStartedEvent(threadId=thread_id, runId=run_id)
        )

        # Convert AG-UI messages to OpenAI format
        openai_messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful customer support agent for Lev Haolam. "
                    "A tool was just executed based on user confirmation. "
                    "The tool result message (role=tool) contains the ACTUAL outcome. "
                    "Use ONLY the data from the tool result to describe what happened. "
                    "Do NOT use numbers or details from the original user message — "
                    "the user may have modified the values in the confirmation form. "
                    "Acknowledge the result briefly and ask if there's anything else you can help with. "
                    "Be concise - 1-2 sentences max."
                ),
            }
        ]

        for m in messages:
            if m.role == "user":
                openai_messages.append({"role": "user", "content": m.content or ""})
            elif m.role == "assistant":
                msg: dict = {"role": "assistant"}
                if m.content:
                    msg["content"] = m.content
                if hasattr(m, "tool_calls") and m.tool_calls:
                    msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in m.tool_calls
                    ]
                    if "content" not in msg:
                        msg["content"] = None
                openai_messages.append(msg)
            elif m.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": m.tool_call_id,
                    "content": m.content or "",
                })

        logger.info(
            "tool_result_openai_call",
            message_count=len(openai_messages),
            roles=[m["role"] for m in openai_messages],
        )

        # Call OpenAI to generate acknowledgment
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=openai_messages,
            stream=True,
        )

        message_id = str(uuid4())
        text_started = False

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                if not text_started:
                    yield encoder.encode(
                        TextMessageStartEvent(messageId=message_id)
                    )
                    text_started = True
                yield encoder.encode(
                    TextMessageContentEvent(
                        messageId=message_id,
                        delta=delta.content,
                    )
                )

        if text_started:
            yield encoder.encode(
                TextMessageEndEvent(messageId=message_id)
            )

        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )

        logger.info("tool_result_stream_complete", thread_id=thread_id)

    except Exception as e:
        logger.error(
            "tool_result_stream_error",
            error=str(e),
            thread_id=thread_id,
            exc_info=True,
        )
        error_message_id = str(uuid4())
        yield encoder.encode(
            TextMessageStartEvent(messageId=error_message_id)
        )
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=error_message_id,
                delta="The action was processed. Is there anything else I can help with?",
            )
        )
        yield encoder.encode(
            TextMessageEndEvent(messageId=error_message_id)
        )
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )


async def _error_stream(error: str) -> AsyncGenerator[str, None]:
    """Stream error message in AG-UI format."""
    encoder = EventEncoder()
    message_id = str(uuid4())
    run_id = str(uuid4())
    thread_id = str(uuid4())

    yield encoder.encode(
        RunStartedEvent(threadId=thread_id, runId=run_id)
    )
    yield encoder.encode(
        TextMessageStartEvent(messageId=message_id)
    )
    yield encoder.encode(
        TextMessageContentEvent(messageId=message_id, delta=f"Error: {error}")
    )
    yield encoder.encode(
        TextMessageEndEvent(messageId=message_id)
    )
    yield encoder.encode(
        RunFinishedEvent(threadId=thread_id, runId=run_id)
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
    in the CopilotKit sidebar.
    """
    if req.tool_name not in WRITE_TOOLS:
        logger.warning("execute_tool_rejected", tool_name=req.tool_name)
        return {"status": "error", "message": f"Tool '{req.tool_name}' is not an executable write tool"}

    tool_fn = TOOL_REGISTRY.get(req.tool_name)
    if not tool_fn:
        logger.error("execute_tool_not_found", tool_name=req.tool_name)
        return {"status": "error", "message": f"Tool '{req.tool_name}' not found"}

    try:
        result = tool_fn(**req.tool_args)
        if inspect.isawaitable(result):
            result = await result
        result_data = json_lib.loads(result)

        # Audit log
        try:
            from database.queries import save_tool_execution
            save_tool_execution({
                "session_id": req.session_id or "copilot_hitl",
                "tool_name": req.tool_name,
                "tool_input": req.tool_args,
                "tool_output": result_data,
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
        )

        return {"status": "completed", "result": result_data}

    except Exception as e:
        logger.error("execute_tool_error", tool_name=req.tool_name, error=str(e), exc_info=True)
        return {"status": "error", "message": str(e)}


# --- Read-Only Data Fetch Endpoint (for display widgets) ---

READ_ONLY_TOOLS: set[str] = {
    "get_subscription",
    "get_customer_history",
    "get_payment_history",
    "track_package",
    "get_box_contents",
}


class FetchDataRequest(BaseModel):
    """Request to fetch read-only data for display widgets."""
    tool_name: str
    tool_args: dict


@router.post("/fetch-data")
async def fetch_data(req: FetchDataRequest):
    """Fetch read-only data for display widgets.

    Called by frontend widgets to load data for rich visual display.
    Only allows read-only tools (no write operations).
    """
    if req.tool_name not in READ_ONLY_TOOLS:
        logger.warning("fetch_data_rejected", tool_name=req.tool_name)
        return {"status": "error", "message": f"Tool '{req.tool_name}' is not a read-only tool"}

    tool_fn = TOOL_REGISTRY.get(req.tool_name)
    if not tool_fn:
        logger.error("fetch_data_not_found", tool_name=req.tool_name)
        return {"status": "error", "message": f"Tool '{req.tool_name}' not found"}

    try:
        result = tool_fn(**req.tool_args)
        if inspect.isawaitable(result):
            result = await result
        result_data = json_lib.loads(result)

        logger.info("fetch_data_success", tool_name=req.tool_name)
        return {"status": "ok", "result": result_data}

    except Exception as e:
        logger.error("fetch_data_error", tool_name=req.tool_name, error=str(e), exc_info=True)
        return {"status": "error", "message": str(e)}
