"""Dynamic Support Agent factory.

Creates a configured Agno Agent per category based on CATEGORY_CONFIG.
Each agent gets: model, reasoning effort, tools, knowledge, and instructions
tailored to its specific support category.
"""

import structlog

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude

from agents.config import CATEGORY_CONFIG, CategoryConfig
from agents.instructions import load_instructions
from knowledge.pinecone_client import create_knowledge

logger = structlog.get_logger()


def _resolve_model(config: CategoryConfig):
    """Resolve category config to an Agno model instance.

    Args:
        config: Category configuration with model and provider info.

    Returns:
        Agno model instance (OpenAIChat or Claude).
    """
    if config.model_provider == "openai_chat":
        return OpenAIChat(id=config.model)
    elif config.model_provider == "openai_responses":
        return OpenAIChat(id=config.model)
    elif config.model_provider == "anthropic":
        return Claude(id=config.model)
    else:
        raise ValueError(f"Unknown model_provider: {config.model_provider}")


def create_support_agent(category: str) -> Agent:
    """Create a dynamically-configured Support Agent for a category.

    The agent gets model, instructions, knowledge, and tools
    all driven by CATEGORY_CONFIG.

    Args:
        category: One of the 10 valid category strings.

    Returns:
        Configured Agno Agent ready to process messages.

    Raises:
        ValueError: If category is not in CATEGORY_CONFIG.
    """
    if category not in CATEGORY_CONFIG:
        raise ValueError(f"Unknown category: {category}")

    config = CATEGORY_CONFIG[category]

    # Load instructions from database
    instructions = load_instructions(category)

    # Create knowledge base for this category's namespace
    knowledge = None
    if config.pinecone_namespace:
        try:
            knowledge = create_knowledge(config.pinecone_namespace)
        except Exception as e:
            logger.error(
                "knowledge_creation_failed",
                category=category,
                namespace=config.pinecone_namespace,
                error=str(e),
            )

    # Build agent kwargs
    agent_kwargs: dict = {
        "name": f"Support Agent ({category})",
        "model": _resolve_model(config),
        "instructions": instructions,
        "markdown": True,
    }

    if knowledge:
        agent_kwargs["knowledge"] = knowledge
        agent_kwargs["search_knowledge"] = True

    # Phase 0: no action tools yet (tools are Phase 2-3)
    # agent_kwargs["tools"] = _resolve_tools(config.tools)

    agent = Agent(**agent_kwargs)

    logger.info(
        "support_agent_created",
        category=category,
        model=config.model,
        model_provider=config.model_provider,
        has_knowledge=knowledge is not None,
    )

    return agent
