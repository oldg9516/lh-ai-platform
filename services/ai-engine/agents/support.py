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
from config import settings
from knowledge.pinecone_client import create_knowledge
from tools import resolve_tools, resolve_tools_for_copilot

logger = structlog.get_logger()


def _resolve_model(config: CategoryConfig):
    """Resolve category config to an Agno model instance.

    Args:
        config: Category configuration with model and provider info.

    Returns:
        Agno model instance (OpenAIChat or Claude).
    """
    if config.model_provider in ("openai_chat", "openai_responses"):
        kwargs: dict = {"id": config.model}
        if config.reasoning_effort:
            kwargs["reasoning_effort"] = config.reasoning_effort
        return OpenAIChat(**kwargs)
    elif config.model_provider == "anthropic":
        return Claude(id=config.model)
    else:
        raise ValueError(f"Unknown model_provider: {config.model_provider}")


async def create_support_agent(
    category: str,
    customer_email: str | None = None,
    use_hitl: bool = False,
) -> Agent:
    """Create a dynamically-configured Support Agent for a category.

    The agent gets model, instructions, knowledge, and tools
    all driven by CATEGORY_CONFIG. When learning is enabled,
    adds Agno Learning Machine for customer memory and few-shot
    corrections from human edits.

    Args:
        category: One of the 10 valid category strings.
        customer_email: Customer email for tool lookups and personalization.
        use_hitl: If True, replace write tools with HITL proxy versions
            that return "pending_confirmation". AG-UI ToolCall events trigger
            CopilotKit forms for user confirmation.

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

    # Inject few-shot corrections from human edits (Track 2: quality improvement)
    if settings.learning_few_shot_enabled:
        try:
            from learning.few_shot import build_few_shot_instructions

            few_shot = await build_few_shot_instructions(category)
            if few_shot:
                instructions.append(few_shot)
        except Exception as e:
            logger.warning("few_shot_injection_failed", category=category, error=str(e))

    # Add customer email context if provided
    if customer_email:
        email_context = (
            f"\n\nIMPORTANT: Customer email for this conversation: {customer_email}\n"
            f"When calling tools that require customer_email parameter, use this email address."
        )
        instructions.append(email_context)

    # Add HITL instructions for CopilotKit path
    if use_hitl:
        hitl_context = (
            "\n\nHUMAN-IN-THE-LOOP TOOLS:\n"
            "You have tools that require customer confirmation before execution. "
            "When the customer wants to pause, skip, change frequency, change address, "
            "or report damage — you MUST call the appropriate tool. "
            "Do NOT tell the customer to visit a website or portal. "
            "Do NOT give step-by-step manual instructions. "
            "Instead, ALWAYS call the tool directly. A confirmation form will appear "
            "for the customer to review and approve the action.\n"
            "After calling the tool, tell the customer that a confirmation form "
            "has appeared and they should review and confirm it."
        )
        instructions.append(hitl_context)

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

    # Resolve action tools from CATEGORY_CONFIG
    # For CopilotKit HITL: exclude write tools (they come from frontend)
    if config.tools:
        resolver = resolve_tools_for_copilot if use_hitl else resolve_tools
        resolved = resolver(config.tools)
        if resolved:
            agent_kwargs["tools"] = resolved

    # Track 1: Agno Learning Machine (customer memory/personalization)
    if settings.learning_enabled and customer_email and settings.learning_db_url:
        try:
            from agno.db.postgres import PostgresDb
            from agno.learn import LearningMachine, LearningMode, UserMemoryConfig

            db = PostgresDb(db_url=settings.learning_db_url)
            agent_kwargs["db"] = db
            agent_kwargs["user_id"] = customer_email
            agent_kwargs["learning"] = LearningMachine(
                user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
            )
        except Exception as e:
            logger.warning("learning_machine_init_failed", error=str(e))

    agent = Agent(**agent_kwargs)

    logger.info(
        "support_agent_created",
        category=category,
        model=config.model,
        model_provider=config.model_provider,
        has_knowledge=knowledge is not None,
        tools_count=len(agent_kwargs.get("tools", [])),
        learning_enabled="learning" in agent_kwargs,
    )

    return agent
