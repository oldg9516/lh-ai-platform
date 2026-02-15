"""Learning API endpoints for identifying training candidates.

These endpoints help identify sessions that would be valuable for
improving AI performance through learning and refinement.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from database.queries import get_learning_candidates

router = APIRouter()


class LearningCandidate(BaseModel):
    """A session that is a good candidate for learning/training."""

    session_id: str
    customer_email: str | None
    primary_category: str | None
    eval_decision: str | None
    eval_confidence: str | None
    total_messages: int
    tools_used_count: int
    created_at: str | None
    reason: str


@router.get("/candidates", response_model=list[LearningCandidate])
async def get_candidates(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of candidates"),
):
    """Get sessions that are good candidates for learning/training.

    Identifies cases where AI had:
    - Low confidence (draft decision with low confidence)
    - Escalated to human
    - Multiple tool calls (complex scenarios)
    - Extended conversations (>5 messages)

    These cases are valuable for:
    - Improving prompt engineering
    - Identifying edge cases
    - Enhancing tool usage patterns
    - Training data for future models
    """
    # Run query in thread pool (sync psycopg)
    data = await asyncio.to_thread(get_learning_candidates, days, limit)
    return [LearningCandidate(**row) for row in data]
