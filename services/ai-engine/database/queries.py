"""Database queries for the AI Engine.

All queries use supabase-py (REST API).
Reads from existing tables, writes to new chat tables.
"""

from typing import Any

import structlog

from database.connection import get_client

logger = structlog.get_logger()


def get_instructions(category: str) -> dict[str, Any] | None:
    """Load agent instructions from ai_answerer_instructions table.

    Args:
        category: The category type to look up (e.g., 'shipping_or_delivery_question').

    Returns:
        Dict with instruction_1..10, outstanding_rules, etc. or None if not found.
    """
    response = (
        get_client()
        .table("ai_answerer_instructions")
        .select("*")
        .eq("type", category)
        .eq("status", "enabled")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_global_rules() -> dict[str, Any] | None:
    """Load global rules from ai_answerer_instructions table.

    Returns:
        Dict with global rules instructions or None if not found.
    """
    response = (
        get_client()
        .table("ai_answerer_instructions")
        .select("*")
        .eq("type", "global_rules")
        .eq("status", "enabled")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def save_session(data: dict[str, Any]) -> str:
    """Insert or update a chat session.

    Args:
        data: Session fields matching chat_sessions table schema.

    Returns:
        The session_id of the created/updated session.
    """
    row = {
        "session_id": data.get("session_id"),
        "conversation_id": data.get("conversation_id"),
        "channel": data.get("channel", "widget"),
        "customer_email": data.get("customer_email"),
        "customer_name": data.get("customer_name"),
        "primary_category": data.get("primary_category"),
        "secondary_category": data.get("secondary_category"),
        "urgency": data.get("urgency", "medium"),
        "status": data.get("status", "active"),
        "eval_decision": data.get("eval_decision"),
        "first_response_time_ms": data.get("first_response_time_ms"),
    }
    get_client().table("chat_sessions").upsert(row, on_conflict="session_id").execute()
    return data["session_id"]


def save_message(data: dict[str, Any]) -> None:
    """Insert a chat message.

    Args:
        data: Message fields matching chat_messages table schema.
    """
    row = {
        "session_id": data.get("session_id"),
        "role": data.get("role"),
        "content": data.get("content"),
        "model_used": data.get("model_used"),
        "reasoning_effort": data.get("reasoning_effort"),
        "processing_time_ms": data.get("processing_time_ms"),
    }
    get_client().table("chat_messages").insert(row).execute()


def save_eval_result(data: dict[str, Any]) -> None:
    """Insert an eval result into the eval_results table.

    Args:
        data: Eval result fields matching eval_results table schema.
    """
    row = {
        "ticket_id": data.get("ticket_id"),
        "request_subtype": data.get("request_subtype"),
        "request_sub_subtype": data.get("request_sub_subtype"),
        "decision": data["decision"],
        "draft_reason": data.get("draft_reason"),
        "confidence": data.get("confidence"),
        "checks": data.get("checks"),
        "overrides": data.get("overrides"),
        "is_outstanding": data.get("is_outstanding", False),
        "outstanding_trigger": data.get("outstanding_trigger"),
        "auto_send_enabled": data.get("auto_send_enabled", False),
    }
    get_client().table("eval_results").insert(row).execute()


def update_session_outstanding(
    session_id: str,
    is_outstanding: bool,
    outstanding_trigger: str | None,
    eval_decision: str,
) -> None:
    """Update a chat session with outstanding detection and eval results.

    Args:
        session_id: The session ID to update.
        is_outstanding: Whether the case is outstanding.
        outstanding_trigger: The trigger description.
        eval_decision: Eval Gate decision (send/draft/escalate).
    """
    get_client().table("chat_sessions").update({
        "is_outstanding": is_outstanding,
        "outstanding_trigger": outstanding_trigger,
        "eval_decision": eval_decision,
    }).eq("session_id", session_id).execute()


def save_tool_execution(data: dict[str, Any]) -> None:
    """Insert a tool execution record.

    Args:
        data: Tool execution fields matching tool_executions table schema.
    """
    row = {
        "session_id": data.get("session_id"),
        "tool_name": data["tool_name"],
        "tool_input": data.get("tool_input"),
        "tool_output": data.get("tool_output"),
        "requires_approval": data.get("requires_approval", False),
        "status": data.get("status", "completed"),
        "duration_ms": data.get("duration_ms"),
        "error_message": data.get("error_message"),
    }
    get_client().table("tool_executions").insert(row).execute()
