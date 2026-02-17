"""Few-shot injection — inject top corrections into agent instructions.

Builds a block of text showing recent human corrections as examples
for the agent to learn from. This is appended to the agent's instruction
list at creation time when learning_few_shot_enabled is True.
"""

import structlog

from learning.feedback import get_recent_corrections

logger = structlog.get_logger()

# Truncate individual responses to prevent instruction bloat
_MAX_EXAMPLE_LENGTH = 200


async def build_few_shot_instructions(
    category: str,
    limit: int = 3,
) -> str | None:
    """Build few-shot instruction block from recent corrections.

    Args:
        category: The support category to get corrections for.
        limit: Maximum number of correction examples to include.

    Returns:
        Instruction text to append to agent instructions, or None if
        no corrections are available.
    """
    corrections = get_recent_corrections(category, limit=limit)
    if not corrections:
        return None

    parts = [
        "\nLEARNING FROM PAST CORRECTIONS:",
        "The following are examples of previous responses that were corrected by human agents.",
        "Learn from these patterns to avoid repeating the same mistakes:\n",
    ]

    for i, corr in enumerate(corrections, 1):
        ai_text = corr.get("ai_response", "")
        human_text = corr.get("human_edit", "")
        issue = corr.get("specific_issue") or "Not specified"

        # Truncate long texts
        if len(ai_text) > _MAX_EXAMPLE_LENGTH:
            ai_text = ai_text[:_MAX_EXAMPLE_LENGTH] + "..."
        if len(human_text) > _MAX_EXAMPLE_LENGTH:
            human_text = human_text[:_MAX_EXAMPLE_LENGTH] + "..."

        parts.append(f"Example {i}:")
        parts.append(f"  Issue: {issue}")
        parts.append(f"  Original: {ai_text}")
        parts.append(f"  Corrected: {human_text}")
        parts.append("")

    logger.info(
        "few_shot_injected",
        category=category,
        examples_count=len(corrections),
    )

    return "\n".join(parts)
