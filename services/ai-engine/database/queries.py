"""Database queries for the AI Engine.

All queries use psycopg2 (sync) with RealDictCursor.
Reads from existing tables, writes to new chat tables.
"""

from typing import Any

import psycopg2.extras
import structlog

from database.connection import get_connection

logger = structlog.get_logger()


def get_instructions(category: str) -> dict[str, Any] | None:
    """Load agent instructions from ai_answerer_instructions table.

    Args:
        category: The request_subtype to look up (e.g., 'shipping_or_delivery_question').

    Returns:
        Dict with instruction_1..10, outstanding_rules, etc. or None if not found.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM ai_answerer_instructions
                WHERE name = %s AND status = 'enabled'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (category,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_customer(email: str) -> dict[str, Any] | None:
    """Look up customer info by email from existing support data.

    Args:
        email: Customer email address.

    Returns:
        Dict with customer_email, customer_name, subscription_id or None.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT customer_email, customer_name, subscription_id
                FROM support_threads_data
                WHERE customer_email = %s
                LIMIT 1
                """,
                (email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def save_session(data: dict[str, Any]) -> str:
    """Insert a new chat session.

    Args:
        data: Session fields matching chat_sessions table schema.

    Returns:
        The session_id of the created session.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, conversation_id, channel,
                    customer_email, customer_name,
                    primary_category, secondary_category, urgency,
                    status, eval_decision, first_response_time_ms
                ) VALUES (
                    %(session_id)s, %(conversation_id)s, %(channel)s,
                    %(customer_email)s, %(customer_name)s,
                    %(primary_category)s, %(secondary_category)s, %(urgency)s,
                    %(status)s, %(eval_decision)s, %(first_response_time_ms)s
                )
                ON CONFLICT (session_id) DO UPDATE SET
                    primary_category = EXCLUDED.primary_category,
                    secondary_category = EXCLUDED.secondary_category,
                    urgency = EXCLUDED.urgency,
                    eval_decision = EXCLUDED.eval_decision,
                    first_response_time_ms = EXCLUDED.first_response_time_ms,
                    updated_at = NOW()
                """,
                {
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
                },
            )
    return data["session_id"]


def save_message(data: dict[str, Any]) -> None:
    """Insert a chat message.

    Args:
        data: Message fields matching chat_messages table schema.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_messages (
                    session_id, role, content,
                    model_used, reasoning_effort,
                    processing_time_ms
                ) VALUES (
                    %(session_id)s, %(role)s, %(content)s,
                    %(model_used)s, %(reasoning_effort)s,
                    %(processing_time_ms)s
                )
                """,
                {
                    "session_id": data.get("session_id"),
                    "role": data.get("role"),
                    "content": data.get("content"),
                    "model_used": data.get("model_used"),
                    "reasoning_effort": data.get("reasoning_effort"),
                    "processing_time_ms": data.get("processing_time_ms"),
                },
            )
