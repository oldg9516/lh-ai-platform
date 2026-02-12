"""Router Agent — fast message classification.

Uses GPT-5.1 (no reasoning) to classify customer messages
into one of 10 support categories with structured output.
"""

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from agents.config import VALID_CATEGORIES

import structlog

logger = structlog.get_logger()


class RouterOutput(BaseModel):
    """Structured output from the Router Agent."""

    primary: str = Field(
        description=(
            "Primary category. One of: "
            + ", ".join(VALID_CATEGORIES)
        ),
    )
    secondary: str | None = Field(
        default=None,
        description="Secondary category if message contains multiple intents.",
    )
    urgency: str = Field(
        default="medium",
        description="Urgency level: low, medium, high, critical.",
    )
    email: str | None = Field(
        default=None,
        description="Customer email if mentioned in the message.",
    )


ROUTER_INSTRUCTIONS = [
    "You are a message classifier for Lev Haolam customer support.",
    "Classify the customer message into exactly one primary category.",
    f"Valid categories: {', '.join(VALID_CATEGORIES)}.",
    "If the message contains multiple intents, set the secondary category.",
    "Extract customer email if present in the message.",
    "Set urgency based on:",
    "- critical: death threats, bank disputes, legal threats",
    "- high: damaged items, repeated cancellation requests",
    "- medium: most requests (default)",
    "- low: gratitude, simple questions",
    "If unclear, default to shipping_or_delivery_question with medium urgency.",
    "Respond ONLY with the structured output, no extra text.",
]


def create_router_agent() -> Agent:
    """Create the Router Agent for message classification."""
    return Agent(
        name="Router Agent",
        model=OpenAIChat(id="gpt-5.1"),
        instructions=ROUTER_INSTRUCTIONS,
        response_model=RouterOutput,
        markdown=False,
    )


async def classify_message(message: str) -> RouterOutput:
    """Classify a customer message into a support category.

    Args:
        message: Raw customer message text.

    Returns:
        RouterOutput with primary category, urgency, etc.
    """
    router = create_router_agent()
    response = await router.arun(message)

    result = response.content
    if not isinstance(result, RouterOutput):
        logger.warning("router_unexpected_output", output_type=type(result).__name__)
        result = RouterOutput(primary="shipping_or_delivery_question")

    # Validate category
    if result.primary not in VALID_CATEGORIES:
        logger.warning("router_invalid_category", category=result.primary)
        result.primary = "shipping_or_delivery_question"

    logger.info(
        "message_classified",
        primary=result.primary,
        secondary=result.secondary,
        urgency=result.urgency,
    )
    return result
