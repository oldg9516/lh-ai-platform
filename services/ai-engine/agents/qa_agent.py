"""QA Agent — response quality check with retry capability.

Replaces the LLM tier of eval_gate.py when team mode is enabled.
Key difference: adds a "refine" decision that triggers a retry loop
where the specialist gets QA feedback and re-generates its response.

Tier 1 (regex fast-fail) is reused from eval_gate.fast_safety_check().
Tier 2 (LLM evaluation) uses GPT-5.1 with stricter judgment.
"""

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from agents.eval_gate import EvalCheck, fast_safety_check

import structlog

logger = structlog.get_logger()


class QAOutput(BaseModel):
    """Structured output from QA Agent."""

    decision: str = Field(
        description=(
            "Final decision: 'send' (ready for customer), "
            "'refine' (needs improvement, provide feedback), "
            "'draft' (needs human review), "
            "'escalate' (connect to human agent)."
        ),
    )
    confidence: str = Field(
        default="high",
        description="Confidence in the decision: high, medium, low.",
    )
    checks: list[EvalCheck] = Field(
        default_factory=list,
        description="Individual check results (safety, tone, accuracy, completeness).",
    )
    feedback: str | None = Field(
        default=None,
        description=(
            "Specific feedback for the specialist agent when decision is 'refine'. "
            "Should describe exactly what needs to be fixed."
        ),
    )
    override_reason: str | None = Field(
        default=None,
        description="If decision was overridden from what checks suggest, explain why.",
    )


QA_INSTRUCTIONS = [
    "You are the QA Agent — the final quality gate before an AI response is sent to a customer.",
    "You work for Lev Haolam, an Israel-based subscription box company.",
    "",
    "Evaluate the AI response on four dimensions:",
    "",
    "1. SAFETY (most critical):",
    "   - NEVER confirms subscription cancellation (must redirect to cancel page)",
    "   - NEVER confirms pause directly (must redirect or get human confirmation)",
    "   - NEVER confirms refund processing (requires human approval)",
    "   - NEVER promises specific resolution for damage (replacement, credit, refund)",
    "   - No sensitive data exposure",
    "   - If ANY safety rule is violated → 'draft' or 'escalate'",
    "",
    "2. TONE:",
    "   - Professional, empathetic, warm (Lev Haolam brand voice)",
    "   - Not robotic, not overly casual, not dismissive",
    "",
    "3. ACCURACY:",
    "   - Data returned by tool calls (tracking numbers, dates, subscription details) is real — treat as accurate",
    "   - No made-up information that did NOT come from a tool call",
    "   - No raw database field names or technical placeholders",
    "",
    "4. COMPLETENESS:",
    "   - Addresses the customer's actual question",
    "   - Provides actionable next steps",
    "",
    "DECISION RULES:",
    "- 'send': All checks pass with score >= 0.7, safety >= 0.9",
    "- 'refine': Response is close but needs specific improvement (tone issue, missing info, minor problem)",
    "   → You MUST provide detailed 'feedback' explaining what to fix",
    "- 'draft': Significant quality issues OR safety concern (needs human review)",
    "- 'escalate': Critical safety violation OR customer explicitly requests human",
    "",
    "IMPORTANT: Use 'refine' only on the FIRST attempt. On retry (attempt 2+), ",
    "choose only 'send', 'draft', or 'escalate'.",
]


def _build_qa_prompt(
    customer_message: str,
    ai_response: str,
    category: str,
    is_outstanding: bool,
    tools_available: list[str] | None = None,
    attempt: int = 1,
    previous_feedback: str | None = None,
) -> str:
    """Build the QA evaluation prompt."""
    parts = [f"CATEGORY: {category}"]

    if is_outstanding:
        parts.append("OUTSTANDING: True — be extra strict. When in doubt, 'draft'.")

    if tools_available:
        parts.append(
            f"TOOLS AVAILABLE: {', '.join(tools_available)}\n"
            "The agent had access to these tools. Data matching tool output should be considered accurate."
        )

    parts.append(f"ATTEMPT: {attempt}")

    if attempt > 1:
        parts.append(
            "This is a RETRY attempt. The specialist was given feedback and re-generated. "
            "Do NOT use 'refine' again — only 'send', 'draft', or 'escalate'."
        )

    if previous_feedback:
        parts.append(f"PREVIOUS QA FEEDBACK:\n{previous_feedback}")

    parts.append(f"\nCUSTOMER MESSAGE:\n{customer_message}")
    parts.append(f"\nAI RESPONSE TO EVALUATE:\n{ai_response}")

    return "\n".join(parts)


async def qa_evaluate(
    customer_message: str,
    ai_response: str,
    category: str,
    is_outstanding: bool = False,
    tools_available: list[str] | None = None,
    attempt: int = 1,
    previous_feedback: str | None = None,
) -> QAOutput:
    """Evaluate an AI response through the QA Agent.

    Two-tier approach:
    1. Fast regex check for obvious safety violations (reused from eval_gate)
    2. LLM evaluation with refine/retry capability

    Args:
        customer_message: Original customer message.
        ai_response: AI-generated response to evaluate.
        category: Classified category.
        is_outstanding: Whether this is an outstanding case.
        tools_available: List of tool names available to the specialist.
        attempt: Current attempt number (1 = first, 2 = retry after refine).
        previous_feedback: QA feedback from previous attempt (if retrying).

    Returns:
        QAOutput with decision, confidence, checks, and optional feedback.
    """
    # Tier 1: Regex fast-fail (reused from eval_gate)
    is_safe, violation = fast_safety_check(ai_response)
    if not is_safe:
        logger.warning("qa_fast_fail", violation=violation, category=category)
        return QAOutput(
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

    # Tier 2: LLM evaluation
    try:
        agent = Agent(
            name="QA Agent",
            model=OpenAIChat(id="gpt-5.1"),
            instructions=QA_INSTRUCTIONS,
            output_schema=QAOutput,
            markdown=False,
        )
        prompt = _build_qa_prompt(
            customer_message=customer_message,
            ai_response=ai_response,
            category=category,
            is_outstanding=is_outstanding,
            tools_available=tools_available,
            attempt=attempt,
            previous_feedback=previous_feedback,
        )
        response = await agent.arun(prompt)
        result = response.content

        if not isinstance(result, QAOutput):
            logger.warning("qa_unexpected_output", output_type=type(result).__name__)
            return QAOutput(decision="draft", confidence="low", override_reason="Parse error")

        # On retry (attempt > 1), force no "refine" decision
        if attempt > 1 and result.decision == "refine":
            result.decision = "draft"
            result.override_reason = "Refine not allowed on retry — forced to draft"

        # Outstanding cases bias toward draft
        if is_outstanding and result.decision == "send" and result.confidence != "high":
            result.decision = "draft"
            result.override_reason = "Outstanding case with non-high confidence forced to draft"

        logger.info(
            "qa_evaluation_complete",
            decision=result.decision,
            confidence=result.confidence,
            attempt=attempt,
            checks_passed=sum(1 for c in result.checks if c.passed),
            has_feedback=result.feedback is not None,
        )
        return result

    except Exception as e:
        logger.error("qa_evaluation_failed", error=str(e))
        return QAOutput(
            decision="draft",
            confidence="low",
            override_reason=f"QA agent error: {str(e)}",
        )
