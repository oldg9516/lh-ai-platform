"""Pre-defined SQL queries for analytics metrics.

These functions provide fast, pre-computed metrics without LLM overhead.
For ad-hoc queries, use the analytics agent with natural language.
"""

from datetime import datetime, timedelta
from typing import Any

from database.connection import get_connection


def get_resolution_rate(days: int = 7) -> dict[str, Any]:
    """Calculate AI resolution rate for last N days.

    Args:
        days: Number of days to look back

    Returns:
        dict with keys:
            - total_sessions: Total number of sessions
            - auto_sent: Number of sessions auto-sent
            - drafted: Number of sessions drafted for review
            - escalated: Number of sessions escalated
            - avg_response_time_ms: Average response time in milliseconds
    """
    since = datetime.now() - timedelta(days=days)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    COUNT(*) FILTER (WHERE eval_decision = 'send') as auto_sent,
                    COUNT(*) FILTER (WHERE eval_decision = 'draft') as drafted,
                    COUNT(*) FILTER (WHERE eval_decision = 'escalate') as escalated,
                    AVG(first_response_time_ms) as avg_response_time_ms
                FROM chat_sessions
                WHERE created_at >= %s
            """,
                (since,),
            )
            row = cur.fetchone()
            if not row:
                return {
                    "total_sessions": 0,
                    "auto_sent": 0,
                    "drafted": 0,
                    "escalated": 0,
                    "avg_response_time_ms": 0,
                }

            return {
                "total_sessions": row[0] or 0,
                "auto_sent": row[1] or 0,
                "drafted": row[2] or 0,
                "escalated": row[3] or 0,
                "avg_response_time_ms": round(row[4], 2) if row[4] else 0,
            }


def get_eval_decisions(days: int = 7) -> dict[str, int]:
    """Get count of each eval decision.

    Args:
        days: Number of days to look back

    Returns:
        dict with keys: total, send, draft, escalate
    """
    data = get_resolution_rate(days)
    return {
        "total": data["total_sessions"],
        "send": data["auto_sent"],
        "draft": data["drafted"],
        "escalate": data["escalated"],
    }


def get_category_breakdown(days: int = 7) -> list[dict[str, Any]]:
    """Get message count and metrics by category.

    Args:
        days: Number of days to look back

    Returns:
        List of dicts with keys:
            - category: Primary category name
            - count: Number of sessions in this category
            - percentage: Percentage of total sessions
            - resolution_rate: % of sessions auto-sent in this category
            - avg_response_time_ms: Average response time for this category
    """
    since = datetime.now() - timedelta(days=days)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    primary_category as category,
                    COUNT(*) as count,
                    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'send') / COUNT(*), 2) as resolution_rate,
                    ROUND(AVG(first_response_time_ms), 0) as avg_response_time_ms
                FROM chat_sessions
                WHERE created_at >= %s
                GROUP BY primary_category
                ORDER BY count DESC
            """,
                (since,),
            )
            return [
                {
                    "category": row[0],
                    "count": row[1],
                    "percentage": float(row[2]) if row[2] else 0,
                    "resolution_rate": float(row[3]) if row[3] else 0,
                    "avg_response_time_ms": int(row[4]) if row[4] else 0,
                }
                for row in cur.fetchall()
            ]


def get_daily_trends(days: int = 30) -> list[dict[str, Any]]:
    """Get daily resolution rate trend.

    Args:
        days: Number of days to look back

    Returns:
        List of dicts with keys:
            - day: Date string (YYYY-MM-DD)
            - total: Total sessions on that day
            - auto_sent: Sessions auto-sent
            - drafted: Sessions drafted
            - escalated: Sessions escalated
            - resolution_rate_pct: Resolution rate percentage
    """
    since = datetime.now() - timedelta(days=days)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    DATE_TRUNC('day', created_at) as day,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE eval_decision = 'send') as auto_sent,
                    COUNT(*) FILTER (WHERE eval_decision = 'draft') as drafted,
                    COUNT(*) FILTER (WHERE eval_decision = 'escalate') as escalated,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'send') / COUNT(*), 2) as resolution_rate_pct
                FROM chat_sessions
                WHERE created_at >= %s
                GROUP BY day
                ORDER BY day DESC
            """,
                (since,),
            )
            return [
                {
                    "day": row[0].strftime("%Y-%m-%d"),
                    "total": row[1],
                    "auto_sent": row[2],
                    "drafted": row[3],
                    "escalated": row[4],
                    "resolution_rate_pct": float(row[5]) if row[5] else 0,
                }
                for row in cur.fetchall()
            ]


def get_customer_patterns(days: int = 30, min_sessions: int = 2) -> list[dict[str, Any]]:
    """Get customers with repeat sessions.

    Args:
        days: Number of days to look back
        min_sessions: Minimum number of sessions to include

    Returns:
        List of dicts with keys:
            - customer_email: Customer email
            - session_count: Number of sessions
            - most_common_category: Most frequent category
            - last_interaction: Last interaction timestamp
            - escalation_rate: % of sessions escalated for this customer
    """
    since = datetime.now() - timedelta(days=days)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    customer_email,
                    COUNT(DISTINCT session_id) as session_count,
                    MODE() WITHIN GROUP (ORDER BY primary_category) as most_common_category,
                    MAX(created_at) as last_interaction,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'escalate') / COUNT(*), 2) as escalation_rate
                FROM chat_sessions
                WHERE created_at >= %s
                GROUP BY customer_email
                HAVING COUNT(DISTINCT session_id) >= %s
                ORDER BY session_count DESC
                LIMIT 50
            """,
                (since, min_sessions),
            )
            return [
                {
                    "customer_email": row[0],
                    "session_count": row[1],
                    "most_common_category": row[2],
                    "last_interaction": row[3].isoformat() if row[3] else None,
                    "escalation_rate": float(row[4]) if row[4] else 0,
                }
                for row in cur.fetchall()
            ]


def get_learning_candidates(days: int = 7, limit: int = 50) -> list[dict[str, Any]]:
    """Get sessions that are good candidates for learning/training.

    Identifies cases where AI had low confidence or made multiple attempts.

    Args:
        days: Number of days to look back
        limit: Maximum number of candidates to return

    Returns:
        List of dicts with keys:
            - session_id: Session identifier
            - customer_email: Customer email
            - primary_category: Category classification
            - eval_decision: Final decision (draft/escalate)
            - eval_confidence: Confidence level
            - total_messages: Number of messages in conversation
            - tools_used_count: Number of tool calls made
            - created_at: Timestamp
            - reason: Why this is a learning candidate
    """
    since = datetime.now() - timedelta(days=days)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH session_tools AS (
                    SELECT
                        session_id,
                        COUNT(*) as tool_count,
                        COUNT(DISTINCT tool_name) as unique_tools
                    FROM tool_executions
                    GROUP BY session_id
                )
                SELECT
                    s.session_id,
                    s.customer_email,
                    s.primary_category,
                    s.eval_decision,
                    s.eval_confidence,
                    s.total_messages,
                    COALESCE(st.tool_count, 0) as tools_used_count,
                    s.created_at,
                    CASE
                        WHEN s.eval_decision = 'draft' AND s.eval_confidence = 'low' THEN 'Low confidence draft'
                        WHEN s.eval_decision = 'escalate' THEN 'Escalated to human'
                        WHEN st.tool_count > 3 THEN 'Multiple tool calls (complex case)'
                        WHEN s.total_messages > 5 THEN 'Extended conversation'
                        ELSE 'Edge case'
                    END as reason
                FROM chat_sessions s
                LEFT JOIN session_tools st ON s.session_id = st.session_id
                WHERE s.created_at >= %s
                    AND (
                        s.eval_decision IN ('draft', 'escalate')
                        OR s.eval_confidence = 'low'
                        OR st.tool_count > 3
                        OR s.total_messages > 5
                    )
                ORDER BY s.created_at DESC
                LIMIT %s
            """,
                (since, limit),
            )
            return [
                {
                    "session_id": row[0],
                    "customer_email": row[1],
                    "primary_category": row[2],
                    "eval_decision": row[3],
                    "eval_confidence": row[4],
                    "total_messages": row[5],
                    "tools_used_count": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "reason": row[8],
                }
                for row in cur.fetchall()
            ]


def get_hitl_stats(days: int = 7) -> dict[str, Any]:
    """Get HITL (Human-in-the-Loop) confirmation statistics.

    Args:
        days: Number of days to look back

    Returns:
        dict with keys:
            - total_hitl_calls: Total tool calls requiring approval
            - approved: Number of approved confirmations
            - cancelled: Number of cancelled confirmations
            - pending: Number still pending
            - approval_rate_pct: Approval rate percentage
            - by_tool: Breakdown by tool name with approval rates
    """
    since = datetime.now() - timedelta(days=days)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Overall stats
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE approval_status = 'approved') as approved,
                    COUNT(*) FILTER (WHERE approval_status = 'cancelled') as cancelled,
                    COUNT(*) FILTER (WHERE approval_status IS NULL) as pending
                FROM tool_executions
                WHERE created_at >= %s
                    AND requires_approval = true
            """,
                (since,),
            )
            overall = cur.fetchone()
            total = overall[0] or 0
            approved = overall[1] or 0
            cancelled = overall[2] or 0
            pending = overall[3] or 0

            # By tool breakdown
            cur.execute(
                """
                SELECT
                    tool_name,
                    COUNT(*) as total_calls,
                    COUNT(*) FILTER (WHERE approval_status = 'approved') as approved,
                    COUNT(*) FILTER (WHERE approval_status = 'cancelled') as cancelled,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE approval_status = 'approved') / NULLIF(COUNT(*), 0), 2) as approval_rate
                FROM tool_executions
                WHERE created_at >= %s
                    AND requires_approval = true
                GROUP BY tool_name
                ORDER BY total_calls DESC
            """,
                (since,),
            )
            by_tool = [
                {
                    "tool_name": row[0],
                    "total_calls": row[1],
                    "approved": row[2],
                    "cancelled": row[3],
                    "approval_rate_pct": float(row[4]) if row[4] else 0,
                }
                for row in cur.fetchall()
            ]

            return {
                "total_hitl_calls": total,
                "approved": approved,
                "cancelled": cancelled,
                "pending": pending,
                "approval_rate_pct": round(100 * approved / total, 2) if total > 0 else 0,
                "by_tool": by_tool,
            }
