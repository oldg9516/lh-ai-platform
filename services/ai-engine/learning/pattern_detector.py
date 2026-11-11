"""Pattern detection and instruction fix suggestion generator.

Phase 9.2: Detects recurring correction patterns (3+ of same type per
category in 7 days) and uses LLM to generate instruction fix suggestions
that can be reviewed, approved, and deployed by admins.
"""

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
import structlog

from config import settings
from database.connection import get_client
from database.queries import (
    get_instruction_updates,
    save_instruction_update,
)

logger = structlog.get_logger()


class InstructionFix(BaseModel):
    """LLM-generated instruction fix suggestion."""

    issue_pattern: str
    suggested_fix: str


def detect_recurring_patterns(
    min_frequency: int | None = None,
    window_days: int | None = None,
) -> list[dict]:
    """Detect recurring correction patterns above threshold.

    Queries correction_patterns grouped by (category, correction_type) and
    returns groups that exceed the minimum frequency within the time window.
    Skips patterns that already have a pending/approved/deployed instruction update.

    Args:
        min_frequency: Minimum corrections to trigger (default: settings value).
        window_days: Lookback window in days (default: settings value).

    Returns:
        List of pattern dicts: {category, correction_type, frequency, examples}.
    """
    if min_frequency is None:
        min_frequency = settings.pattern_min_frequency
    if window_days is None:
        window_days = settings.pattern_window_days

    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()

    try:
        # Fetch all corrections within the window
        result = (
            get_client()
            .table("correction_patterns")
            .select("*")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .execute()
        )
        corrections = result.data or []
    except Exception as e:
        logger.error("detect_patterns_query_failed", error=str(e))
        return []

    if not corrections:
        return []

    # Group by (category, correction_type)
    groups: dict[tuple[str, str], list[dict]] = {}
    for c in corrections:
        key = (c["category"], c["correction_type"])
        groups.setdefault(key, []).append(c)

    # Filter groups above threshold
    patterns = []
    for (category, correction_type), examples in groups.items():
        if len(examples) < min_frequency:
            continue

        # Check for existing instruction update (avoid duplicates)
        existing = get_instruction_updates(category=category)
        has_active = any(
            u["status"] in ("pending", "approved", "deployed")
            and correction_type in u.get("issue_pattern", "")
            for u in existing
        )
        if has_active:
            logger.debug(
                "pattern_already_tracked",
                category=category,
                correction_type=correction_type,
            )
            continue

        patterns.append({
            "category": category,
            "correction_type": correction_type,
            "frequency": len(examples),
            "examples": examples[:5],  # Cap at 5 examples
        })

    logger.info("patterns_detected", count=len(patterns))
    return patterns


async def suggest_instruction_fix(
    category: str,
    correction_type: str,
    examples: list[dict],
) -> InstructionFix:
    """Use LLM to analyze correction examples and suggest an instruction fix.

    Args:
        category: The support category.
        correction_type: Type of correction (tone/accuracy/safety/completeness).
        examples: List of correction dicts with ai_response, human_edit, specific_issue.

    Returns:
        InstructionFix with issue_pattern description and suggested_fix text.
    """
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    examples_text = ""
    for i, ex in enumerate(examples[:5], 1):
        ai_text = (ex.get("ai_response") or "")[:300]
        human_text = (ex.get("human_edit") or "")[:300]
        issue = ex.get("specific_issue") or "Not specified"
        examples_text += (
            f"\nExample {i}:\n"
            f"  Issue: {issue}\n"
            f"  Original AI: {ai_text}\n"
            f"  Human Edit: {human_text}\n"
        )

    agent = Agent(
        name="Instruction Fix Suggester",
        model=OpenAIChat(id="gpt-6.1-terra"),
        instructions=[
            "You analyze recurring corrections to AI customer support responses and suggest instruction fixes.",
            "Given a category, correction type, and examples of corrections, you must:",
            "1. Identify the common pattern across all examples (issue_pattern)",
            "2. Write a concise, actionable instruction fix (suggested_fix) that can be appended to the agent's instructions to prevent this issue",
            "The suggested_fix should be a single paragraph, written as a direct instruction to the AI agent.",
            "Do NOT include meta-commentary. Write the fix as if you are giving a rule to the agent.",
        ],
        output_schema=InstructionFix,
        markdown=False,
    )

    prompt = (
        f"Category: {category}\n"
        f"Correction Type: {correction_type}\n"
        f"Number of occurrences: {len(examples)}\n"
        f"\nExamples of corrections:{examples_text}\n"
        "Analyze these corrections and suggest an instruction fix."
    )

    try:
        result = await agent.arun(prompt)
        if isinstance(result.content, InstructionFix):
            return result.content
        return InstructionFix(
            issue_pattern=f"Recurring {correction_type} issue in {category}",
            suggested_fix=f"Pay attention to {correction_type} when handling {category} requests.",
        )
    except Exception as e:
        logger.error("suggest_fix_failed", category=category, error=str(e))
        return InstructionFix(
            issue_pattern=f"Recurring {correction_type} issue in {category}",
            suggested_fix=f"Pay attention to {correction_type} when handling {category} requests.",
        )


async def run_pattern_analysis() -> list[str]:
    """Run full pattern analysis: detect → suggest → save.

    Returns:
        List of created instruction_update UUIDs.
    """
    patterns = detect_recurring_patterns()
    if not patterns:
        logger.info("no_recurring_patterns_found")
        return []

    created_ids: list[str] = []
    for pattern in patterns:
        fix = await suggest_instruction_fix(
            category=pattern["category"],
            correction_type=pattern["correction_type"],
            examples=pattern["examples"],
        )

        # Build supporting examples (slim: just issue + key changes)
        supporting = [
            {
                "specific_issue": ex.get("specific_issue"),
                "correction_type": ex.get("correction_type"),
            }
            for ex in pattern["examples"]
        ]

        try:
            update_id = save_instruction_update({
                "category": pattern["category"],
                "issue_pattern": fix.issue_pattern,
                "suggested_fix": fix.suggested_fix,
                "supporting_examples": supporting,
                "frequency": pattern["frequency"],
            })
            created_ids.append(update_id)
            logger.info(
                "instruction_update_created",
                update_id=update_id,
                category=pattern["category"],
                correction_type=pattern["correction_type"],
                frequency=pattern["frequency"],
            )
        except Exception as e:
            logger.error(
                "save_instruction_update_failed",
                category=pattern["category"],
                error=str(e),
            )

    return created_ids
