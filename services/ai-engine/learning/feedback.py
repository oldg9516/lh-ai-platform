"""Correction learning pipeline — collect, classify, detect patterns.

Track 2 of the dual-track learning mechanism. Collects human corrections
of AI responses, classifies them by type, and stores them for few-shot
injection and instruction improvement suggestions.
"""

from pydantic import BaseModel

import structlog

from database.connection import get_client

logger = structlog.get_logger()


class CorrectionRecord(BaseModel):
    """A single human correction of an AI response."""

    conversation_id: str | None = None
    session_id: str | None = None
    category: str
    ai_response: str
    human_edit: str
    correction_type: str  # tone, accuracy, safety, completeness
    specific_issue: str | None = None
    key_changes: list[str] = []


class CorrectionClassification(BaseModel):
    """Output of the LLM correction classifier."""

    correction_type: str  # tone, accuracy, safety, completeness
    specific_issue: str | None = None
    key_changes: list[str] = []


def save_correction(record: CorrectionRecord) -> None:
    """Save a human correction to the correction_patterns table.

    Args:
        record: The correction record to save.
    """
    try:
        get_client().table("correction_patterns").insert({
            "conversation_id": record.conversation_id,
            "session_id": record.session_id,
            "category": record.category,
            "ai_response": record.ai_response,
            "human_edit": record.human_edit,
            "correction_type": record.correction_type,
            "specific_issue": record.specific_issue,
            "key_changes": record.key_changes,
        }).execute()
        logger.info(
            "correction_saved",
            category=record.category,
            correction_type=record.correction_type,
        )
    except Exception as e:
        logger.error("correction_save_failed", error=str(e))


def get_recent_corrections(
    category: str,
    limit: int = 5,
) -> list[dict]:
    """Get recent corrections for a category, sorted newest first.

    Args:
        category: The support category to filter by.
        limit: Maximum number of corrections to return.

    Returns:
        List of correction dicts from the database.
    """
    try:
        result = (
            get_client()
            .table("correction_patterns")
            .select("*")
            .eq("category", category)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        logger.error("get_recent_corrections_failed", category=category, error=str(e))
        return []


async def classify_correction(
    ai_response: str,
    human_edit: str,
) -> CorrectionClassification:
    """Use LLM to classify what type of correction was made.

    Args:
        ai_response: The original AI-generated response.
        human_edit: The human-edited version of the response.

    Returns:
        CorrectionClassification with type, issue, and key changes.
    """
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    classifier = Agent(
        name="Correction Classifier",
        model=OpenAIChat(id="gpt-5-mini"),
        instructions=[
            "You classify human corrections of AI customer support responses.",
            "Compare the original AI response with the human-edited version.",
            "Determine the correction type:",
            "- tone: Changed formality, warmth, empathy, or communication style",
            "- accuracy: Fixed factual errors, wrong information, or misleading claims",
            "- safety: Removed unauthorized promises (cancellations, refunds, pauses)",
            "- completeness: Added missing information, steps, or context",
            "Identify the specific issue and list key changes made.",
        ],
        output_schema=CorrectionClassification,
        markdown=False,
    )

    prompt = (
        f"ORIGINAL AI RESPONSE:\n{ai_response}\n\n"
        f"HUMAN-EDITED VERSION:\n{human_edit}\n\n"
        "Classify this correction."
    )

    try:
        result = await classifier.arun(prompt)
        if isinstance(result.content, CorrectionClassification):
            return result.content
        # Fallback if structured output parsing fails
        return CorrectionClassification(
            correction_type="completeness",
            specific_issue="Unable to classify — defaulting to completeness",
            key_changes=[],
        )
    except Exception as e:
        logger.error("classify_correction_failed", error=str(e))
        return CorrectionClassification(
            correction_type="completeness",
            specific_issue=f"Classification error: {str(e)}",
            key_changes=[],
        )
