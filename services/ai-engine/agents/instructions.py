"""Dynamic instruction loader for Support Agents.

Loads prompts from ai_answerer_instructions table in Supabase,
prepends global safety rules to all agents.
"""

import structlog

from database.queries import get_instructions

logger = structlog.get_logger()

GLOBAL_SAFETY_RULES = [
    "CRITICAL SAFETY RULES (NEVER VIOLATE):",
    "1. NEVER confirm subscription cancellation directly. Always redirect to the self-service cancellation page.",
    "2. NEVER confirm pause directly. Redirect or require human confirmation.",
    "3. If you detect death threats, bank disputes, or explicit threats — immediately respond that you are connecting them with a human agent.",
    "4. NEVER process refunds without human approval.",
    "5. NEVER include sensitive customer data in your response (credit card numbers, passwords, etc.).",
    "6. If you are unsure about the category or your confidence is low — state that you will have a human agent review the case.",
    "7. Always respond in the same language the customer used.",
]


def load_instructions(category: str) -> list[str]:
    """Load dynamic instructions for a category from the database.

    Combines global safety rules with category-specific instructions
    from ai_answerer_instructions (instruction_1..10).

    Args:
        category: The category name (e.g., 'shipping_or_delivery_question').

    Returns:
        List of instruction strings for Agent's instructions parameter.
    """
    instructions = list(GLOBAL_SAFETY_RULES)

    try:
        row = get_instructions(category)
        if row:
            for i in range(1, 11):
                value = row.get(f"instruction_{i}")
                if value and value.strip():
                    instructions.append(value.strip())

            # Add outstanding rules if present
            outstanding = row.get("outstanding_rules")
            if outstanding and outstanding.strip():
                instructions.append(f"OUTSTANDING RULES: {outstanding.strip()}")

            outstanding_hard = row.get("outstanding_hard_rules")
            if outstanding_hard and outstanding_hard.strip():
                instructions.append(f"HARD RULES (NEVER VIOLATE): {outstanding_hard.strip()}")
        else:
            logger.warning("no_instructions_found", category=category)
            instructions.append(
                f"You are a helpful customer support agent for Lev Haolam handling {category} requests. "
                "Be polite, professional, and helpful."
            )
    except Exception as e:
        logger.error("failed_to_load_instructions", category=category, error=str(e))
        instructions.append(
            f"You are a helpful customer support agent for Lev Haolam handling {category} requests. "
            "Be polite, professional, and helpful."
        )

    return instructions
