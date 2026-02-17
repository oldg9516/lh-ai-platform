"""AG-UI Endpoint for CopilotKit Integration.

This module exposes support agents via the AG-UI protocol,
enabling frontend interaction through CopilotKit.

Architecture:
- Frontend (Next.js) -> HttpAgent -> FastAPI (this endpoint)
- AG-UI protocol with EventEncoder for SSE streaming
- Direct OpenAI API for tool calling (bypasses Agno to emit proper ToolCall events)
- HITL tools -> AG-UI ToolCallStart/Args/End -> CopilotKit renders forms
- Read-only tools -> executed server-side, results fed back to LLM

Pipeline (customer-facing mode):
1. Pre-safety (red lines) -> immediate escalation if flagged
2. Classify + name extraction (parallel)
3. Build context (with DB history)
4. Run agent buffered -> collect full response
5. Outstanding detection (parallel capable)
6. Eval Gate on buffered text (if enabled)
7. Sanitize response
8. Stream to client based on decision (send/draft/escalate)
9. Persist to DB + Chatwoot sync (background)
"""

import asyncio
import inspect
import json as json_lib
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
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
from agents.eval_gate import evaluate_response, fast_safety_check
from agents.instructions import load_instructions
from agents.name_extractor import extract_customer_name
from agents.outstanding import detect_outstanding
from agents.response_assembler import sanitize_response, strip_existing_greeting
from agents.router import classify_message
from config import settings
from database.queries import (
    get_conversation_history,
    save_eval_result,
    save_message,
    save_session,
    update_session_outstanding,
)
from guardrails.safety import check_red_lines
from tools import TOOL_REGISTRY, WRITE_TOOLS

logger = structlog.get_logger()

router = APIRouter()

# --- Production Hardening Constants ---

OPENAI_STREAM_TIMEOUT_S = 30  # Max time for OpenAI streaming response
MAX_INPUT_LENGTH = 1000  # Max length for user text inputs
MAX_EMAIL_LENGTH = 254  # RFC 5321 max email length
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class RateLimiter:
    """Simple in-memory rate limiter for tool executions."""

    def __init__(self, max_calls: int = 5, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        calls = self._calls[key]
        self._calls[key] = [t for t in calls if now - t < self.window_seconds]
        if len(self._calls[key]) >= self.max_calls:
            return False
        self._calls[key].append(now)
        return True


_tool_rate_limiter = RateLimiter(max_calls=5, window_seconds=60)
_stream_rate_limiter = RateLimiter(max_calls=10, window_seconds=60)


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


# --- Chatwoot Sync Cache ---

# Cache: thread_id -> (chatwoot_conversation_id, timestamp)
_thread_to_chatwoot: dict[str, tuple[int, float]] = {}
_CHATWOOT_CACHE_TTL = 3600  # 1 hour


def _get_cached_conversation(thread_id: str) -> int | None:
    """Get cached Chatwoot conversation_id for a CopilotKit thread."""
    entry = _thread_to_chatwoot.get(thread_id)
    if entry and (time.monotonic() - entry[1]) < _CHATWOOT_CACHE_TTL:
        return entry[0]
    return None


def _cache_conversation(thread_id: str, conversation_id: int) -> None:
    """Cache the thread -> conversation mapping."""
    _thread_to_chatwoot[thread_id] = (conversation_id, time.monotonic())


# --- Buffered Agent Result ---


@dataclass
class AgentBufferedResult:
    """Result from running the agent with tool loop in buffered mode."""

    text: str = ""
    hitl_events: list = field(default_factory=list)
    display_events: list = field(default_factory=list)
    tool_calls_made: list = field(default_factory=list)
    has_hitl: bool = False


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


# --- Helper Functions ---


def _sanitize_for_chat(text: str, customer_name: str, category: str) -> str:
    """Sanitize AI response for chat display (no HTML wrapping)."""
    text = strip_existing_greeting(text, customer_name)
    text = sanitize_response(text, category)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = 15) -> list[str]:
    """Split text into small word-group chunks for simulated streaming."""
    words = text.split(" ")
    chunks = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= chunk_size:
            chunks.append(" ".join(current) + " ")
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


async def _execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a read-only tool and return its result as a string."""
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


# --- Buffered Agent Execution ---


async def _run_agent_buffered(
    user_content: str,
    system_prompt: str,
    openai_tools: list[dict],
    model: str,
    thread_id: str,
) -> AgentBufferedResult:
    """Run OpenAI with tool-call loop, collecting full response in buffer.

    Returns AgentBufferedResult with text, HITL events, and tool call info.
    HITL tools are NOT executed — their AG-UI events are collected for later emission.
    Read-only tools ARE executed server-side, with results fed back to OpenAI.
    """
    result = AgentBufferedResult()
    client = _get_openai_client()
    max_iterations = 5

    openai_messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    for iteration in range(max_iterations):
        kwargs: dict = {
            "model": model,
            "messages": openai_messages,
            "stream": True,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(**kwargs),
                timeout=OPENAI_STREAM_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.error("copilot_openai_timeout", thread_id=thread_id, iteration=iteration)
            result.text = "I'm sorry, the request timed out. Please try again."
            return result

        accumulated_text = ""
        accumulated_tool_calls: dict[int, dict] = {}

        async for chunk in response:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if delta and delta.content:
                accumulated_text += delta.content

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

        result.text += accumulated_text

        # No tool calls -> done
        if not accumulated_tool_calls:
            break

        # Process tool calls
        hitl_emitted = False
        read_only_results = []
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

            result.tool_calls_made.append(tool_name)

            tool_events = [
                ToolCallStartEvent(
                    toolCallId=tc["id"],
                    toolCallName=tool_name,
                ),
                ToolCallArgsEvent(
                    toolCallId=tc["id"],
                    delta=tool_args_str,
                ),
                ToolCallEndEvent(toolCallId=tc["id"]),
            ]

            if tool_name in HITL_TOOL_NAMES:
                # True HITL tool: collect events, stop pipeline (human is the gate)
                result.hitl_events.extend(tool_events)
                result.has_hitl = True
                hitl_emitted = True
            elif tool_name in DISPLAY_TOOL_NAMES:
                # Display widget: collect events but continue pipeline
                result.display_events.extend(tool_events)
                hitl_emitted = True  # still breaks tool loop (display needs frontend)
            else:
                # Read-only tool: execute server-side
                tool_result = await _execute_tool(tool_name, tool_args)
                read_only_results.append((tc["id"], tool_name, tool_result))

        if hitl_emitted:
            break

        # Feed read-only results back to OpenAI
        if read_only_results:
            openai_messages.append({
                "role": "assistant",
                "tool_calls": assistant_tool_calls,
            })
            for tool_call_id, tool_name, tool_result in read_only_results:
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result,
                })

    return result


# --- Persistence ---


def _persist_copilot_exchange(
    session_id: str,
    thread_id: str,
    customer_email: str | None,
    customer_name: str,
    category: str,
    router_output,
    user_message: str,
    ai_response: str,
    decision: str,
    eval_result,
    outstanding_result,
    config,
    processing_time_ms: int = 0,
) -> None:
    """Best-effort persistence of copilot exchange to DB."""
    try:
        save_session({
            "session_id": session_id,
            "conversation_id": thread_id,
            "channel": "copilot",
            "customer_email": customer_email,
            "customer_name": customer_name,
            "primary_category": category,
            "secondary_category": router_output.secondary if router_output else None,
            "urgency": router_output.urgency if router_output else "medium",
            "status": "active",
            "eval_decision": decision,
            "first_response_time_ms": processing_time_ms,
        })
        if outstanding_result:
            update_session_outstanding(
                session_id=session_id,
                is_outstanding=outstanding_result.is_outstanding,
                outstanding_trigger=outstanding_result.trigger,
                eval_decision=decision,
            )
        save_message({
            "session_id": session_id,
            "role": "user",
            "content": user_message,
            "model_used": None,
            "reasoning_effort": None,
            "processing_time_ms": None,
        })
        save_message({
            "session_id": session_id,
            "role": "assistant",
            "content": ai_response,
            "model_used": config.model,
            "reasoning_effort": config.reasoning_effort,
            "processing_time_ms": processing_time_ms,
        })
        if eval_result:
            save_eval_result({
                "ticket_id": session_id,
                "request_subtype": category,
                "request_sub_subtype": router_output.secondary if router_output else None,
                "decision": decision,
                "draft_reason": eval_result.override_reason if hasattr(eval_result, "override_reason") else None,
                "confidence": eval_result.confidence if hasattr(eval_result, "confidence") else "high",
                "checks": [c.model_dump() for c in eval_result.checks] if hasattr(eval_result, "checks") else [],
                "is_outstanding": outstanding_result.is_outstanding if outstanding_result else False,
                "outstanding_trigger": outstanding_result.trigger if outstanding_result else None,
                "auto_send_enabled": config.auto_send_phase <= 1,
            })
    except Exception as e:
        logger.error("copilot_persist_error", session_id=session_id, error=str(e))


# --- Chatwoot Sync ---


async def _sync_to_chatwoot(
    thread_id: str,
    customer_email: str | None,
    customer_name: str,
    category: str,
    user_message: str,
    ai_response: str,
    decision: str,
    escalation_reason: str | None = None,
) -> None:
    """One-way sync: push CopilotKit exchange to Chatwoot for operator visibility."""
    if not settings.copilot_chatwoot_sync_enabled:
        return
    if not settings.chatwoot_copilot_inbox_id:
        return
    if not customer_email:
        logger.info("chatwoot_sync_skipped_no_email", thread_id=thread_id)
        return

    try:
        from chatwoot.client import (
            find_or_create_contact,
            create_conversation,
            send_message as chatwoot_send_message,
            toggle_conversation_status,
            add_labels,
            assign_conversation,
        )

        # Check cache for existing conversation
        cw_conversation_id = _get_cached_conversation(thread_id)

        if cw_conversation_id is None:
            # Create contact + conversation
            contact = await find_or_create_contact(customer_email, customer_name)
            contact_id = contact.get("id")
            if not contact_id:
                logger.error("chatwoot_sync_no_contact_id", thread_id=thread_id)
                return

            conversation = await create_conversation(
                contact_id=contact_id,
                inbox_id=settings.chatwoot_copilot_inbox_id,
                source_id=thread_id,
            )
            cw_conversation_id = conversation.get("id")
            if not cw_conversation_id:
                return
            _cache_conversation(thread_id, cw_conversation_id)

        # Sync user message as private note
        await chatwoot_send_message(
            cw_conversation_id,
            f"[CopilotKit] Customer: {user_message}",
            private=True,
        )

        # Sync AI response based on decision
        if decision == "send":
            await chatwoot_send_message(cw_conversation_id, ai_response, private=False)
            await add_labels(cw_conversation_id, ["copilot", category, "ai_sent"])
            await toggle_conversation_status(cw_conversation_id, "resolved")

        elif decision == "draft":
            draft_note = (
                f"**AI Draft (CopilotKit — needs review)**\n\n"
                f"Category: {category}\n\n"
                f"---\n\n{ai_response}"
            )
            await chatwoot_send_message(cw_conversation_id, draft_note, private=True)
            await add_labels(cw_conversation_id, ["copilot", category, "ai_draft"])
            await toggle_conversation_status(cw_conversation_id, "open")

        elif decision == "escalate":
            escalation_note = (
                f"**AI Escalation (CopilotKit)**\n\n"
                f"Category: {category}\n"
                f"Reason: {escalation_reason or 'eval_gate'}\n\n"
                f"---\n\nAI draft:\n{ai_response}"
            )
            await chatwoot_send_message(cw_conversation_id, escalation_note, private=True)
            await add_labels(cw_conversation_id, ["copilot", category, "ai_escalation", "high_priority"])
            await toggle_conversation_status(cw_conversation_id, "open")
            if settings.chatwoot_escalation_assignee_id:
                await assign_conversation(cw_conversation_id, settings.chatwoot_escalation_assignee_id)

        logger.info(
            "chatwoot_sync_complete",
            thread_id=thread_id,
            conversation_id=cw_conversation_id,
            decision=decision,
        )

    except Exception as e:
        logger.error("chatwoot_sync_error", thread_id=thread_id, error=str(e))


# --- AG-UI Streaming Endpoint ---


@router.post("/")
async def copilot_stream(request: Request):
    """AG-UI streaming endpoint for CopilotKit."""
    if not AGUI_AVAILABLE:
        return {
            "error": "AG-UI protocol not available",
            "message": "Install ag-ui-protocol: pip install ag-ui-protocol",
        }

    try:
        # Rate limiting
        client_ip = request.client.host if request.client else "unknown"
        if not _stream_rate_limiter.check(client_ip):
            logger.warning("copilot_stream_rate_limited", client_ip=client_ip)
            return StreamingResponse(
                _error_stream("Too many requests. Please wait a moment before trying again."),
                media_type="text/event-stream",
            )

        body = await request.json()

        # Handle CopilotKit protocol methods
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
        )

        # Check if this is a tool result continuation
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


async def _agent_stream(message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """Stream agent response using AG-UI protocol events.

    Full pipeline: safety → classify → context → agent → outstanding → eval → sanitize → stream.
    """
    encoder = EventEncoder()
    run_id = str(uuid4())
    start_time = time.time()

    try:
        # 1. Emit RUN_STARTED
        yield encoder.encode(
            RunStartedEvent(threadId=thread_id, runId=run_id)
        )

        # 2. PRE-SAFETY: Red line check (instant regex)
        red_line_result = check_red_lines(message)
        if red_line_result["is_flagged"]:
            logger.warning(
                "copilot_red_line_triggered",
                trigger=red_line_result["trigger"],
                thread_id=thread_id,
            )
            escalation_text = "I'm connecting you with a support agent who can better assist you."
            msg_id = str(uuid4())
            yield encoder.encode(TextMessageStartEvent(messageId=msg_id))
            yield encoder.encode(TextMessageContentEvent(messageId=msg_id, delta=escalation_text))
            yield encoder.encode(TextMessageEndEvent(messageId=msg_id))
            yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
            # Background: sync escalation to Chatwoot
            asyncio.create_task(_sync_to_chatwoot(
                thread_id=thread_id,
                customer_email=None,
                customer_name="Unknown",
                category="unknown",
                user_message=message,
                ai_response=escalation_text,
                decision="escalate",
                escalation_reason=red_line_result["trigger"],
            ))
            return

        # 3. CLASSIFY + NAME EXTRACTION (parallel)
        router_output, customer_name = await asyncio.gather(
            classify_message(message),
            extract_customer_name(message, None),
        )
        category = router_output.primary
        customer_email = router_output.email
        session_id = f"copilot_{thread_id}"

        logger.info(
            "copilot_classified",
            category=category,
            customer_email=customer_email,
            customer_name=customer_name,
            thread_id=thread_id,
        )

        # 4. BUILD CONTEXT (with DB history)
        db_history = get_conversation_history(session_id, limit=10)
        customer_context = await build_full_context(
            customer_email=customer_email,
            conversation_history=db_history,
            outstanding_info=None,
        )

        # 5. LOAD INSTRUCTIONS
        instructions = load_instructions(category)
        config = CATEGORY_CONFIG[category]

        if customer_email:
            instructions.append(
                f"\n\nIMPORTANT: Customer email for this conversation: {customer_email}\n"
                f"When calling tools that require customer_email parameter, use this email address."
            )

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

        # 6. BUILD USER CONTENT
        user_content = message
        if customer_context:
            user_content = f"{customer_context}\n\nCustomer message:\n{message}"

        # 7. GET TOOL SCHEMAS
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
                if name in READ_TO_DISPLAY:
                    display_tools_to_add.add(READ_TO_DISPLAY[name])

        for display_name in display_tools_to_add:
            schema = OPENAI_TOOL_SCHEMAS.get(display_name)
            if schema:
                openai_tools.append(schema)

        logger.info(
            "copilot_openai_call",
            model=config.model,
            tools_count=len(openai_tools),
        )

        # 8. RUN AGENT (buffered)
        agent_result = await _run_agent_buffered(
            user_content=user_content,
            system_prompt=system_prompt,
            openai_tools=openai_tools,
            model=config.model,
            thread_id=thread_id,
        )

        # 9a. If true HITL tools triggered, emit events and stop (human is the gate)
        if agent_result.has_hitl:
            # Emit display events first (if any), then HITL events
            for event in agent_result.display_events:
                yield encoder.encode(event)
            for event in agent_result.hitl_events:
                yield encoder.encode(event)
            yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
            # Persist the exchange (HITL is always "send" — human approves)
            _persist_copilot_exchange(
                session_id=session_id,
                thread_id=thread_id,
                customer_email=customer_email,
                customer_name=customer_name,
                category=category,
                router_output=router_output,
                user_message=message,
                ai_response=f"[HITL tool called: {', '.join(agent_result.tool_calls_made)}]",
                decision="send",
                eval_result=None,
                outstanding_result=None,
                config=config,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
            return

        # 9b. Collect display events to emit later (before text)
        display_events_to_emit = agent_result.display_events

        buffered_text = agent_result.text

        # 9c. Display-only response (display widget called, no/minimal text)
        # Skip eval gate — the display widget IS the response
        if display_events_to_emit and not buffered_text.strip():
            for event in display_events_to_emit:
                yield encoder.encode(event)
            yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
            _persist_copilot_exchange(
                session_id=session_id,
                thread_id=thread_id,
                customer_email=customer_email,
                customer_name=customer_name,
                category=category,
                router_output=router_output,
                user_message=message,
                ai_response=f"[Display widget: {', '.join(agent_result.tool_calls_made)}]",
                decision="send",
                eval_result=None,
                outstanding_result=None,
                config=config,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
            sync_task = asyncio.create_task(_sync_to_chatwoot(
                thread_id=thread_id,
                customer_email=customer_email,
                customer_name=customer_name,
                category=category,
                user_message=message,
                ai_response=f"[Customer viewed {', '.join(agent_result.tool_calls_made)}]",
                decision="send",
            ))
            sync_task.add_done_callback(
                lambda t: logger.error("chatwoot_sync_task_error", error=str(t.exception()))
                if t.exception() else None
            )
            return

        # 10. OUTSTANDING DETECTION + EVAL GATE
        decision = "send"
        eval_result = None
        outstanding_result = None

        if settings.copilot_eval_gate_enabled:
            # Run outstanding detection
            try:
                outstanding_result = await detect_outstanding(message, category)
            except Exception as e:
                logger.warning("copilot_outstanding_error", error=str(e))

            # Run eval gate
            try:
                eval_result = await evaluate_response(
                    customer_message=message,
                    ai_response=buffered_text,
                    category=category,
                    is_outstanding=outstanding_result.is_outstanding if outstanding_result else False,
                    tools_available=config.tools or None,
                )
                decision = eval_result.decision
            except Exception as e:
                logger.error("copilot_eval_gate_error", error=str(e))
                # Fallback: run fast regex check only
                is_safe, violation = fast_safety_check(buffered_text)
                if not is_safe:
                    decision = "draft"
        else:
            # Even without eval gate, run fast regex safety check
            is_safe, violation = fast_safety_check(buffered_text)
            if not is_safe:
                logger.warning("copilot_fast_safety_violation", violation=violation)
                decision = "draft"

        # 11. SANITIZE
        buffered_text = _sanitize_for_chat(buffered_text, customer_name, category)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # 12. PERSIST (best-effort, before streaming)
        _persist_copilot_exchange(
            session_id=session_id,
            thread_id=thread_id,
            customer_email=customer_email,
            customer_name=customer_name,
            category=category,
            router_output=router_output,
            user_message=message,
            ai_response=buffered_text,
            decision=decision,
            eval_result=eval_result,
            outstanding_result=outstanding_result,
            config=config,
            processing_time_ms=processing_time_ms,
        )

        # 13. CHATWOOT SYNC (background, fire-and-forget)
        sync_task = asyncio.create_task(_sync_to_chatwoot(
            thread_id=thread_id,
            customer_email=customer_email,
            customer_name=customer_name,
            category=category,
            user_message=message,
            ai_response=buffered_text,
            decision=decision,
        ))
        sync_task.add_done_callback(
            lambda t: logger.error("chatwoot_sync_task_error", error=str(t.exception()))
            if t.exception() else None
        )

        # 14. STREAM TO CLIENT based on decision
        # Emit display widget events first (before text)
        for event in display_events_to_emit:
            yield encoder.encode(event)

        msg_id = str(uuid4())

        if decision == "send":
            yield encoder.encode(TextMessageStartEvent(messageId=msg_id))
            for chunk in _chunk_text(buffered_text):
                yield encoder.encode(TextMessageContentEvent(messageId=msg_id, delta=chunk))
            yield encoder.encode(TextMessageEndEvent(messageId=msg_id))

        elif decision == "draft":
            yield encoder.encode(TextMessageStartEvent(messageId=msg_id))
            yield encoder.encode(TextMessageContentEvent(
                messageId=msg_id,
                delta="Thank you for your message. Your question is being reviewed by our team, and we'll get back to you shortly.",
            ))
            yield encoder.encode(TextMessageEndEvent(messageId=msg_id))

        elif decision == "escalate":
            yield encoder.encode(TextMessageStartEvent(messageId=msg_id))
            yield encoder.encode(TextMessageContentEvent(
                messageId=msg_id,
                delta="I'm connecting you with a support agent who can better assist you with this matter.",
            ))
            yield encoder.encode(TextMessageEndEvent(messageId=msg_id))

        else:
            # Unknown decision — treat as send
            yield encoder.encode(TextMessageStartEvent(messageId=msg_id))
            for chunk in _chunk_text(buffered_text):
                yield encoder.encode(TextMessageContentEvent(messageId=msg_id, delta=chunk))
            yield encoder.encode(TextMessageEndEvent(messageId=msg_id))

        # 15. RUN_FINISHED
        yield encoder.encode(
            RunFinishedEvent(threadId=thread_id, runId=run_id)
        )

        logger.info(
            "copilot_stream_complete",
            thread_id=thread_id,
            decision=decision,
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(
            "copilot_stream_error",
            error=str(e),
            thread_id=thread_id,
            exc_info=True,
        )
        error_message_id = str(uuid4())
        yield encoder.encode(TextMessageStartEvent(messageId=error_message_id))
        yield encoder.encode(TextMessageContentEvent(
            messageId=error_message_id,
            delta="I apologize, but I encountered an error processing your request. Please try again.",
        ))
        yield encoder.encode(TextMessageEndEvent(messageId=error_message_id))
        yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))


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

        # Buffer the OpenAI response
        client = _get_openai_client()
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=openai_messages,
                    stream=True,
                ),
                timeout=OPENAI_STREAM_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            fallback_id = str(uuid4())
            yield encoder.encode(TextMessageStartEvent(messageId=fallback_id))
            yield encoder.encode(TextMessageContentEvent(
                messageId=fallback_id,
                delta="The action was processed successfully. Is there anything else I can help with?",
            ))
            yield encoder.encode(TextMessageEndEvent(messageId=fallback_id))
            yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
            return

        # Buffer full response
        buffered_text = ""
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                buffered_text += delta.content

        # Fast safety check on buffered text
        is_safe, violation = fast_safety_check(buffered_text)
        if not is_safe:
            buffered_text = "The action was processed successfully. Is there anything else I can help with?"

        # Persist acknowledgment
        session_id = f"copilot_{thread_id}"
        try:
            save_message({
                "session_id": session_id,
                "role": "assistant",
                "content": buffered_text,
                "model_used": "gpt-4.1-mini",
                "reasoning_effort": None,
                "processing_time_ms": None,
            })
        except Exception as e:
            logger.warning("copilot_tool_result_persist_error", error=str(e))

        # Stream buffered text
        message_id = str(uuid4())
        yield encoder.encode(TextMessageStartEvent(messageId=message_id))
        for chunk_text in _chunk_text(buffered_text):
            yield encoder.encode(TextMessageContentEvent(messageId=message_id, delta=chunk_text))
        yield encoder.encode(TextMessageEndEvent(messageId=message_id))
        yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))

        logger.info("tool_result_stream_complete", thread_id=thread_id)

    except Exception as e:
        logger.error(
            "tool_result_stream_error",
            error=str(e),
            thread_id=thread_id,
            exc_info=True,
        )
        error_message_id = str(uuid4())
        yield encoder.encode(TextMessageStartEvent(messageId=error_message_id))
        yield encoder.encode(TextMessageContentEvent(
            messageId=error_message_id,
            delta="The action was processed. Is there anything else I can help with?",
        ))
        yield encoder.encode(TextMessageEndEvent(messageId=error_message_id))
        yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))


async def _error_stream(error: str) -> AsyncGenerator[str, None]:
    """Stream error message in AG-UI format."""
    encoder = EventEncoder()
    message_id = str(uuid4())
    run_id = str(uuid4())
    thread_id = str(uuid4())

    yield encoder.encode(RunStartedEvent(threadId=thread_id, runId=run_id))
    yield encoder.encode(TextMessageStartEvent(messageId=message_id))
    yield encoder.encode(TextMessageContentEvent(messageId=message_id, delta=f"Error: {error}"))
    yield encoder.encode(TextMessageEndEvent(messageId=message_id))
    yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))


# --- HITL Tool Execution Endpoint ---


class ExecuteToolRequest(BaseModel):
    """Request to execute a HITL-approved tool."""
    tool_name: str
    tool_args: dict
    session_id: str | None = None

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or len(v) > 50:
            raise ValueError("Invalid tool name")
        if not re.match(r"^[a-z_]+$", v):
            raise ValueError("Tool name must contain only lowercase letters and underscores")
        return v

    @field_validator("tool_args")
    @classmethod
    def validate_tool_args(cls, v: dict) -> dict:
        email = v.get("customer_email", "")
        if email:
            if len(email) > MAX_EMAIL_LENGTH or not EMAIL_REGEX.match(email):
                raise ValueError("Invalid customer email format")
        for key, val in v.items():
            if isinstance(val, str) and len(val) > MAX_INPUT_LENGTH:
                raise ValueError(f"Field '{key}' exceeds maximum length of {MAX_INPUT_LENGTH}")
        return v


@router.post("/execute-tool")
async def execute_tool(request: Request, req: ExecuteToolRequest):
    """Execute a HITL-approved tool after user confirmation."""
    client_ip = request.client.host if request.client else "unknown"
    if not _tool_rate_limiter.check(client_ip):
        logger.warning("execute_tool_rate_limited", client_ip=client_ip)
        raise HTTPException(status_code=429, detail="Too many requests. Please wait before trying again.")

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

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or len(v) > 50:
            raise ValueError("Invalid tool name")
        if not re.match(r"^[a-z_]+$", v):
            raise ValueError("Tool name must contain only lowercase letters and underscores")
        return v

    @field_validator("tool_args")
    @classmethod
    def validate_tool_args(cls, v: dict) -> dict:
        email = v.get("customer_email", "")
        if email:
            if len(email) > MAX_EMAIL_LENGTH or not EMAIL_REGEX.match(email):
                raise ValueError("Invalid customer email format")
        return v


@router.post("/fetch-data")
async def fetch_data(req: FetchDataRequest):
    """Fetch read-only data for display widgets."""
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
