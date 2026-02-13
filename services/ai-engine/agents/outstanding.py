"""Outstanding Detection Agent.

Determines if a customer request triggers outstanding (exceptional/difficult)
case rules. Uses dynamic rules from ai_answerer_instructions + Pinecone
similarity search against the outstanding-cases namespace.
"""

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from knowledge.pinecone_client import create_knowledge
from database.queries import get_instructions, get_global_rules

import structlog

logger = structlog.get_logger()


class OutstandingOutput(BaseModel):
    """Structured output from Outstanding Detection Agent."""

    is_outstanding: bool = Field(
        default=False,
        description="Whether this request is an outstanding (exceptional) case.",
    )
    trigger: str = Field(
        default="none",
        description="The specific outstanding trigger found. 'none' if not outstanding.",
    )
    confidence: str = Field(
        default="high",
        description="Confidence in the determination: high, medium, low.",
    )


def _load_outstanding_rules(category: str) -> list[str]:
    """Load outstanding detection rules from the database.

    Loads outstanding_rules, outstanding_examples, and outstanding_hard_rules
    from ai_answerer_instructions for the given category + global rules.
    """
    instructions = [
        "You are an Outstanding Case Detector for Lev Haolam customer support.",
        "Determine if a customer request is an OUTSTANDING case.",
        "Outstanding cases require special handling or human review.",
        "",
        "Analyze the customer message against the rules below.",
        "Also consider any similar past cases provided via knowledge search.",
        "",
        "If ANY hard rule is triggered, is_outstanding MUST be true.",
        "If soft rules are triggered, use judgment based on severity.",
        "If no rules match, is_outstanding=false.",
    ]

    try:
        specific_row = get_instructions(category)
        global_row = get_global_rules()

        for row in [global_row, specific_row]:
            if not row:
                continue
            rules = row.get("outstanding_rules")
            if rules and isinstance(rules, str) and rules.strip():
                instructions.append(f"\nOUTSTANDING RULES:\n{rules.strip()}")

            examples = row.get("outstanding_examples")
            if examples and isinstance(examples, str) and examples.strip():
                instructions.append(f"\nOUTSTANDING EXAMPLES:\n{examples.strip()}")

            hard_rules = row.get("outstanding_hard_rules")
            if hard_rules and isinstance(hard_rules, str) and hard_rules.strip():
                instructions.append(
                    f"\nHARD RULES (if ANY match, is_outstanding MUST be true):\n"
                    f"{hard_rules.strip()}"
                )
    except Exception as e:
        logger.error("outstanding_rules_load_failed", category=category, error=str(e))
        instructions.append("Could not load rules. If in doubt, mark as outstanding.")

    return instructions


def create_outstanding_agent(category: str) -> Agent:
    """Create the Outstanding Detection Agent."""
    instructions = _load_outstanding_rules(category)

    knowledge = None
    try:
        knowledge = create_knowledge("outstanding-cases")
    except Exception as e:
        logger.warning("outstanding_knowledge_failed", error=str(e))

    agent_kwargs = {
        "name": "Outstanding Detector",
        "model": OpenAIChat(id="gpt-5-mini"),
        "instructions": instructions,
        "output_schema": OutstandingOutput,
        "markdown": False,
    }

    if knowledge:
        agent_kwargs["knowledge"] = knowledge
        agent_kwargs["search_knowledge"] = True

    return Agent(**agent_kwargs)


async def detect_outstanding(message: str, category: str) -> OutstandingOutput:
    """Detect if a customer message is an outstanding case.

    Args:
        message: Raw customer message text.
        category: Classified category from Router Agent.

    Returns:
        OutstandingOutput with is_outstanding, trigger, and confidence.
    """
    try:
        agent = create_outstanding_agent(category)
        response = await agent.arun(message)
        result = response.content

        if not isinstance(result, OutstandingOutput):
            logger.warning("outstanding_unexpected_output", output_type=type(result).__name__)
            return OutstandingOutput(is_outstanding=False, trigger="none")

        logger.info(
            "outstanding_detection_complete",
            is_outstanding=result.is_outstanding,
            trigger=result.trigger,
            confidence=result.confidence,
        )
        return result

    except Exception as e:
        logger.error("outstanding_detection_failed", error=str(e))
        return OutstandingOutput(is_outstanding=False, trigger="detection_error")
