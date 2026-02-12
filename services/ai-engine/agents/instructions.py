"""Dynamic instruction loader for Support Agents.

Loads prompts from ai_answerer_instructions table in Supabase.
Merges global + category-specific instructions matching n8n logic:
  instruction_1: specific, fallback global (persona)
  instruction_2: global + specific concatenated (RED LINES)
  instruction_3: global + specific concatenated (LOGIC)
  instruction_4: specific, fallback global (format)
  instruction_5..10: specific only
"""

import structlog

from database.queries import get_instructions, get_global_rules

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
    """Load and merge global + category-specific instructions.

    Merging rules (matching n8n production logic):
        instruction_1: specific, fallback to global (persona)
        instruction_2: global + specific concatenated (red lines)
        instruction_3: global + specific concatenated (logic)
        instruction_4: specific, fallback to global (format)
        instruction_5..10: specific only

    Args:
        category: The category name (e.g., 'shipping_or_delivery_question').

    Returns:
        List of instruction strings for Agent's instructions parameter.
    """
    instructions = list(GLOBAL_SAFETY_RULES)

    try:
        specific_row = get_instructions(category)
        global_row = get_global_rules()

        if not specific_row:
            logger.warning("no_instructions_found", category=category)
            instructions.append(
                f"You are a helpful customer support agent for Lev Haolam handling {category} requests. "
                "Be polite, professional, and helpful."
            )
            return instructions

        # instruction_1: persona — specific, fallback to global
        instr_1 = _get_field(specific_row, "instruction_1") or _get_field(global_row, "instruction_1")
        if instr_1:
            instructions.append(instr_1)

        # instruction_2: RED LINES — global + specific (concatenated)
        instr_2 = _merge_fields(global_row, specific_row, "instruction_2")
        if instr_2:
            instructions.append(instr_2)

        # instruction_3: LOGIC — global + specific (concatenated)
        instr_3 = _merge_fields(global_row, specific_row, "instruction_3")
        if instr_3:
            instructions.append(instr_3)

        # instruction_4: format — specific, fallback to global
        instr_4 = _get_field(specific_row, "instruction_4") or _get_field(global_row, "instruction_4")
        if instr_4:
            instructions.append(instr_4)

        # instruction_5..10: specific only
        for i in range(5, 11):
            value = _get_field(specific_row, f"instruction_{i}")
            if value:
                instructions.append(value)

        # Outstanding rules
        outstanding = _get_field(specific_row, "outstanding_rules")
        if outstanding:
            instructions.append(f"OUTSTANDING RULES: {outstanding}")

        outstanding_hard = _get_field(specific_row, "outstanding_hard_rules")
        if outstanding_hard:
            instructions.append(f"HARD RULES (NEVER VIOLATE): {outstanding_hard}")

    except Exception as e:
        logger.error("failed_to_load_instructions", category=category, error=str(e))
        instructions.append(
            f"You are a helpful customer support agent for Lev Haolam handling {category} requests. "
            "Be polite, professional, and helpful."
        )

    return instructions


def _get_field(row: dict | None, field: str) -> str | None:
    """Extract a non-empty string field from a row dict."""
    if not row:
        return None
    value = row.get(field)
    if value and isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _merge_fields(global_row: dict | None, specific_row: dict | None, field: str) -> str | None:
    """Merge global + specific instruction fields by concatenation.

    Returns global + "\\n\\n" + specific if both exist,
    or whichever one exists alone.
    """
    global_val = _get_field(global_row, field)
    specific_val = _get_field(specific_row, field)

    if global_val and specific_val:
        return f"{global_val}\n\n{specific_val}"
    return global_val or specific_val
