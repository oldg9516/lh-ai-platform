"""Metrics API endpoints for pre-computed analytics.

These endpoints provide fast responses without LLM overhead.
For ad-hoc queries, use /query endpoint with natural language.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from database.queries import (
    get_resolution_rate,
    get_category_breakdown,
    get_eval_decisions,
    get_customer_patterns,
)

router = APIRouter()


class MetricsOverview(BaseModel):
    """High-level platform metrics."""

    period: str
    total_sessions: int
    auto_sent: int
    drafted: int
    escalated: int
    resolution_rate_pct: float
    escalation_rate_pct: float
    draft_rate_pct: float
    avg_response_time_ms: float


class CategoryMetrics(BaseModel):
    """Metrics for a single category."""

    category: str
    count: int
    percentage: float
    resolution_rate: float
    avg_response_time_ms: int


class CustomerPattern(BaseModel):
    """Customer with repeat sessions."""

    customer_email: str
    session_count: int
    most_common_category: str
    last_interaction: str | None
    escalation_rate: float


@router.get("/overview", response_model=MetricsOverview)
async def get_overview(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back")
):
    """Get high-level platform metrics for the last N days.

    Returns resolution rate, escalation rate, and average response time.
    """
    # Run query in thread pool (sync psycopg)
    data = await asyncio.to_thread(get_resolution_rate, days)

    total = data["total_sessions"]
    if total == 0:
        return MetricsOverview(
            period=f"{days}d",
            total_sessions=0,
            auto_sent=0,
            drafted=0,
            escalated=0,
            resolution_rate_pct=0,
            escalation_rate_pct=0,
            draft_rate_pct=0,
            avg_response_time_ms=0,
        )

    return MetricsOverview(
        period=f"{days}d",
        total_sessions=total,
        auto_sent=data["auto_sent"],
        drafted=data["drafted"],
        escalated=data["escalated"],
        resolution_rate_pct=round(100 * data["auto_sent"] / total, 2),
        escalation_rate_pct=round(100 * data["escalated"] / total, 2),
        draft_rate_pct=round(100 * data["drafted"] / total, 2),
        avg_response_time_ms=data["avg_response_time_ms"],
    )


@router.get("/categories", response_model=list[CategoryMetrics])
async def get_categories(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back")
):
    """Get message count and metrics by category.

    Returns category distribution with resolution rates and response times.
    """
    data = await asyncio.to_thread(get_category_breakdown, days)
    return [CategoryMetrics(**row) for row in data]


@router.get("/customer-patterns", response_model=list[CustomerPattern])
async def get_patterns(
    days: int = Query(30, ge=1, le=90, description="Number of days to look back"),
    min_sessions: int = Query(2, ge=2, le=10, description="Minimum number of sessions"),
):
    """Get customers with repeat sessions.

    Helps identify high-touch customers or systematic issues.
    """
    data = await asyncio.to_thread(get_customer_patterns, days, min_sessions)
    return [CustomerPattern(**row) for row in data]
