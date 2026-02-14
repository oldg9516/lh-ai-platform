"""Eval Gate Agent.

Verifies AI responses before they are sent to customers.
Two-tier approach:
1. Fast regex checks for obvious safety violations (instant)
2. LLM-based evaluation for nuanced judgment (~300ms)

Replaces the regex-only check_subscription_safety.
"""

import re

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat

import structlog

logger = structlog.get_logger()


class EvalCheck(BaseModel):
    """Individual evaluation check result."""

    name: str = Field(description="Check name: safety, tone, accuracy, completeness.")
    passed: bool = Field(description="Whether the check passed.")
    score: float = Field(ge=0.0, le=1.0, description="Score from 0.0 (fail) to 1.0 (perfect).")
    detail: str = Field(default="", description="Explanation if check failed.")


class EvalGateOutput(BaseModel):
    """Structured output from Eval Gate Agent."""

    decision: str = Field(
        description="Final decision: 'send', 'draft', or 'escalate'.",
    )
    confidence: str = Field(
        default="high",
        description="Confidence in the decision: high, medium, low.",
    )
    checks: list[EvalCheck] = Field(
        default_factory=list,
        description="Individual check results.",
    )
    override_reason: str | None = Field(
        default=None,
        description="If decision was overridden, explain why.",
    )


# --- Fast regex checks (no LLM needed) ---

UNSAFE_RESPONSE_PATTERNS = [
    (r"(cancelled|canceled) your subscription", "confirmed_cancellation"),
    (r"subscription (has been|is now) (cancelled|canceled)", "confirmed_cancellation"),
    (r"(paused|suspended) your subscription", "confirmed_pause"),
    (r"subscription (has been|is now) (paused|suspended)", "confirmed_pause"),
    (r"(processed|issued|approved) (a |your )?(refund|reimbursement)", "confirmed_refund"),
    (r"refund (has been|is now|was) (processed|issued|approved)", "confirmed_refund"),
]


def fast_safety_check(response: str) -> tuple[bool, str | None]:
    """Regex-based fast safety check.

    Returns:
        Tuple of (is_safe, violation_name). violation_name is None if safe.
    """
    response_lower = response.lower()
    for pattern, violation in UNSAFE_RESPONSE_PATTERNS:
        if re.search(pattern, response_lower):
            return False, violation
    return True, None


# --- LLM-based Eval Gate ---

EVAL_GATE_INSTRUCTIONS = [
    "You are the Eval Gate — the final quality check before an AI response is sent to a customer.",
    "You work for Lev Haolam, an Israel-based subscription box company.",
    "",
    "Evaluate the AI response on four dimensions:",
    "",
    "1. SAFETY (most critical):",
    "   - NEVER confirms subscription cancellation (must redirect to cancel page)",
    "   - NEVER confirms pause directly (must redirect or get human confirmation)",
    "   - NEVER confirms refund processing (requires human approval)",
    "   - No sensitive data exposure",
    "   - If ANY safety rule is violated: decision MUST be 'draft' or 'escalate'",
    "",
    "2. TONE:",
    "   - Professional, empathetic, warm (Lev Haolam brand voice)",
    "   - Not robotic, not overly casual, not dismissive",
    "",
    "3. ACCURACY:",
    "   - Information is factually plausible",
    "   - Data returned by tool calls (tracking numbers, dates, subscription details, claim IDs) is real — treat it as accurate",
    "   - No made-up information that did NOT come from a tool call",
    "",
    "4. COMPLETENESS:",
    "   - Addresses the customer's actual question",
    "   - Provides actionable next steps",
    "",
    "DECISION RULES:",
    "- 'send': All checks pass with score >= 0.7, safety >= 0.9",
    "- 'draft': Any check fails (score < 0.7) OR safety < 0.9",
    "- 'escalate': Critical safety violation OR customer needs human handoff",
]


def _build_eval_prompt(
    customer_message: str,
    ai_response: str,
    category: str,
    is_outstanding: bool,
    tools_available: list[str] | None = None,
) -> str:
    """Build the evaluation prompt for the Eval Gate."""
    outstanding_note = ""
    if is_outstanding:
        outstanding_note = (
            "\n**OUTSTANDING CASE — be extra strict. When in doubt, 'draft'.**\n"
        )
    tools_note = ""
    if tools_available:
        tools_note = (
            f"\nTOOLS AVAILABLE TO AGENT: {', '.join(tools_available)}\n"
            "The agent had access to these tools and may have called them. "
            "Any data in the response that matches tool output (tracking numbers, "
            "dates, subscription details, claim IDs) should be considered accurate.\n"
        )
    return (
        f"CATEGORY: {category}\n"
        f"OUTSTANDING: {is_outstanding}{outstanding_note}\n"
        f"{tools_note}\n"
        f"CUSTOMER MESSAGE:\n{customer_message}\n\n"
        f"AI RESPONSE TO EVALUATE:\n{ai_response}"
    )


async def evaluate_response(
    customer_message: str,
    ai_response: str,
    category: str,
    is_outstanding: bool = False,
    tools_available: list[str] | None = None,
) -> EvalGateOutput:
    """Evaluate an AI response through the Eval Gate.

    Two-tier approach:
    1. Fast regex check for obvious safety violations (instant)
    2. LLM evaluation for nuanced judgment (~300ms)

    Args:
        customer_message: Original customer message.
        ai_response: AI-generated response to evaluate.
        category: Classified category.
        is_outstanding: Whether this is an outstanding case.
        tools_available: List of tool names available to the agent for this category.

    Returns:
        EvalGateOutput with decision, confidence, and detailed checks.
    """
    # Tier 1: Fast regex safety check
    is_safe, violation = fast_safety_check(ai_response)
    if not is_safe:
        logger.warning("eval_gate_fast_fail", violation=violation, category=category)
        return EvalGateOutput(
            decision="draft",
            confidence="high",
            checks=[
                EvalCheck(
                    name="safety",
                    passed=False,
                    score=0.0,
                    detail=f"Regex safety violation: {violation}",
                ),
            ],
            override_reason=f"Fast-fail regex: {violation}",
        )

    # Tier 2: LLM-based evaluation
    try:
        agent = Agent(
            name="Eval Gate",
            model=OpenAIChat(id="gpt-5.1"),
            instructions=EVAL_GATE_INSTRUCTIONS,
            output_schema=EvalGateOutput,
            markdown=False,
        )
        prompt = _build_eval_prompt(customer_message, ai_response, category, is_outstanding, tools_available)
        response = await agent.arun(prompt)
        result = response.content

        if not isinstance(result, EvalGateOutput):
            logger.warning("eval_gate_unexpected_output", output_type=type(result).__name__)
            return EvalGateOutput(decision="draft", confidence="low", override_reason="Parse error")

        # Outstanding cases bias toward draft unless high confidence send
        if is_outstanding and result.decision == "send" and result.confidence != "high":
            result.decision = "draft"
            result.override_reason = "Outstanding case with non-high confidence forced to draft"

        logger.info(
            "eval_gate_complete",
            decision=result.decision,
            confidence=result.confidence,
            checks_passed=sum(1 for c in result.checks if c.passed),
            checks_total=len(result.checks),
        )
        return result

    except Exception as e:
        logger.error("eval_gate_failed", error=str(e))
        return EvalGateOutput(
            decision="draft",
            confidence="low",
            override_reason=f"Eval gate error: {str(e)}",
        )
