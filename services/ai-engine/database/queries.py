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
