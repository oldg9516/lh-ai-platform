"""Customer name extraction from message context.

Extracts the customer's first name for personalized responses.
Fast path: use contact_name directly if available.
LLM path: extract from message signature via GPT-5.1-nano.
"""

import re

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.models.openai import OpenAIChat

import structlog

logger = structlog.get_logger()

DEFAULT_NAME = "Client"


class NameOutput(BaseModel):
    """Structured output from name extraction."""

    first_name: str = Field(
        default=DEFAULT_NAME,
        description="Customer's first name extracted from the message or signature.",
    )


EXTRACTOR_INSTRUCTIONS = [
    "Extract the customer's FIRST NAME from the message.",
    "Look for:",
    "- Signature at the end (e.g., 'Best, Sarah' or 'Thanks, John')",
    "- Self-introduction (e.g., 'My name is David' or 'This is Rachel')",
    "- Sign-off patterns (e.g., 'Regards, Michael')",
    "If no name is found, return 'Client'.",
    "Return ONLY the first name, capitalized properly.",
    "Do NOT return full names — just the first name.",
]


async def extract_customer_name(
    message: str,
    contact_name: str | None = None,
) -> str:
    """Extract customer first name for personalization.

    Args:
        message: Raw customer message text.
        contact_name: Name from contact info (if available).

    Returns:
        Customer first name or 'Client' as fallback.
    """
    # Fast path: use provided contact name
    if contact_name:
        name = _clean_name(contact_name.split()[0])
        if name:
            logger.info("name_from_contact", name=name)
            return name

    # LLM path: extract from message signature
    try:
        agent = Agent(
            name="Name Extractor",
            model=OpenAIChat(id="gpt-4.1-nano"),
            instructions=EXTRACTOR_INSTRUCTIONS,
            output_schema=NameOutput,
            markdown=False,
        )
        response = await agent.arun(message)
        result = response.content

        if isinstance(result, NameOutput):
            name = _clean_name(result.first_name)
            if name and name.lower() != "client":
                logger.info("name_from_llm", name=name)
                return name
    except Exception as e:
        logger.warning("name_extraction_failed", error=str(e))

    return DEFAULT_NAME


def _clean_name(raw: str) -> str | None:
    """Validate and normalize an extracted name.

    Returns None if the name is invalid (too short, contains digits, etc.).
    """
    if not raw or not isinstance(raw, str):
        return None

    name = raw.strip().strip(".,!?:;\"'")

    # Must be 2-30 chars, letters only (allow hyphens and apostrophes)
    if not re.match(r"^[A-Za-zÀ-ÿ\'\-]{2,30}$", name):
        return None

    return name.capitalize()
