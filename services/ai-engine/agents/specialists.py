"""Specialist Agent configs and factory.

Groups the 10 support categories into 4 specialist domains:
Billing, Shipping, Retention, Quality. Each specialist has
a broader tool set and multi-namespace knowledge compared
to the single-category support agent.
"""

from dataclasses import dataclass, field

import structlog

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from agents.config import CATEGORY_CONFIG
from agents.instructions import load_instructions
from config import settings
from knowledge.pinecone_client import create_knowledge
from tools import resolve_tools, resolve_tools_for_copilot

logger = structlog.get_logger()


@dataclass(frozen=True)
class SpecialistConfig:
    """Configuration for a specialist agent domain."""

    name: str
    role: str
    categories: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    pinecone_namespaces: list[str] = field(default_factory=list)
    model: str = "gpt-5.1"
    model_provider: str = "openai_chat"
    reasoning_effort: str | None = None


SPECIALIST_CONFIGS: dict[str, SpecialistConfig] = {
    "billing": SpecialistConfig(
        name="Billing Specialist",
        role=(
            "You are the Billing Specialist for Lev Haolam. "
            "You handle payments, subscription frequency changes, skips, and pauses. "
            "You have deep knowledge of subscription billing cycles, payment methods, "
            "and the policies around changing or pausing subscriptions."
        ),
        categories=[
            "payment_question",
            "frequency_change_request",
            "skip_or_pause_request",
        ],
        tools=[
            "get_subscription",
            "get_payment_history",
            "change_frequency",
            "skip_month",
            "pause_subscription",
        ],
        pinecone_namespaces=["payment", "subscription"],
    ),
    "shipping": SpecialistConfig(
        name="Shipping Specialist",
        role=(
            "You are the Shipping Specialist for Lev Haolam. "
            "You handle delivery tracking, address changes, and box contents inquiries. "
            "You have deep knowledge of shipping carriers, tracking systems, "
            "and delivery timelines for international shipments from Israel."
        ),
        categories=[
            "shipping_or_delivery_question",
            "recipient_or_address_change",
        ],
        tools=[
            "get_subscription",
            "track_package",
            "change_address",
            "get_box_contents",
        ],
        pinecone_namespaces=["shipping", "subscription"],
    ),
    "retention": SpecialistConfig(
        name="Retention Specialist",
        role=(
            "You are the Retention Specialist for Lev Haolam. "
            "You handle cancellation requests and customer retention. "
            "Your goal is to understand why the customer wants to cancel "
            "and offer appropriate alternatives (pause, skip, frequency change) "
            "while always respecting their right to cancel via the self-service page. "
            "You NEVER confirm cancellation directly — always redirect to the cancel link."
        ),
        categories=[
            "retention_primary_request",
            "retention_repeated_request",
        ],
        tools=[
            "get_subscription",
            "generate_cancel_link",
            "get_customer_history",
            "pause_subscription",
            "skip_month",
        ],
        pinecone_namespaces=["retention"],
        model_provider="openai_responses",
        reasoning_effort="medium",
    ),
    "quality": SpecialistConfig(
        name="Quality Specialist",
        role=(
            "You are the Quality Specialist for Lev Haolam. "
            "You handle damage reports, product quality issues, customization requests, "
            "and customer appreciation messages. "
            "For damage claims, you collect evidence (photos, descriptions) "
            "but NEVER promise specific resolutions (replacements, refunds) without human approval."
        ),
        categories=[
            "damaged_or_leaking_item_report",
            "customization_request",
            "gratitude",
        ],
        tools=[
            "get_subscription",
            "get_box_contents",
            "create_damage_claim",
            "request_photos",
        ],
        pinecone_namespaces=["damage", "customization", "gratitude"],
    ),
}

# Reverse lookup: category → specialist key
CATEGORY_TO_SPECIALIST: dict[str, str] = {}
for _key, _spec in SPECIALIST_CONFIGS.items():
    for _cat in _spec.categories:
        CATEGORY_TO_SPECIALIST[_cat] = _key


async def create_specialist_agent(
    category: str,
    customer_email: str | None = None,
    use_hitl: bool = False,
) -> Agent:
    """Create a specialist agent for the given category.

    Unlike create_support_agent (one agent per category), specialists
    cover multiple related categories with a broader tool set and
    domain-specific role context. When learning is enabled, adds
    Agno Learning Machine for customer memory and few-shot corrections.

    Args:
        category: One of the 10 valid category strings.
        customer_email: Customer email for tool lookups.
        use_hitl: If True, use HITL proxy tools for CopilotKit.

    Returns:
        Configured Agno Agent with specialist role, tools, and knowledge.

    Raises:
        ValueError: If category is not mapped to a specialist.
    """
    specialist_key = CATEGORY_TO_SPECIALIST.get(category)
    if not specialist_key:
        raise ValueError(f"No specialist mapping for category: {category}")

    spec = SPECIALIST_CONFIGS[specialist_key]

    # Load category-specific instructions from DB (same as support agent)
    instructions = load_instructions(category)

    # Prepend specialist role context
    instructions.insert(0, spec.role)

    # Inject few-shot corrections from human edits (Track 2: quality improvement)
    if settings.learning_few_shot_enabled:
        try:
            from learning.few_shot import build_few_shot_instructions

            few_shot = await build_few_shot_instructions(category)
            if few_shot:
                instructions.append(few_shot)
        except Exception as e:
            logger.warning("few_shot_injection_failed", category=category, error=str(e))

    # Add customer email context
    if customer_email:
        instructions.append(
            f"\nIMPORTANT: Customer email for this conversation: {customer_email}\n"
            f"When calling tools that require customer_email parameter, use this email address."
        )

    # Add HITL instructions for CopilotKit path
    if use_hitl:
        instructions.append(
            "\nHUMAN-IN-THE-LOOP TOOLS:\n"
            "You have tools that require customer confirmation before execution. "
            "When the customer wants to pause, skip, change frequency, change address, "
            "or report damage — you MUST call the appropriate tool. "
            "Do NOT tell the customer to visit a website or portal. "
            "Instead, ALWAYS call the tool directly. A confirmation form will appear "
            "for the customer to review and approve the action.\n"
            "After calling the tool, tell the customer that a confirmation form "
            "has appeared and they should review and confirm it."
        )

    # Resolve model
    model_kwargs: dict = {"id": spec.model}
    if spec.reasoning_effort:
        model_kwargs["reasoning_effort"] = spec.reasoning_effort
    model = OpenAIChat(**model_kwargs)

    # Build agent kwargs
    agent_kwargs: dict = {
        "name": spec.name,
        "model": model,
        "instructions": instructions,
        "markdown": True,
    }

    # Create knowledge from all specialist namespaces
    for ns in spec.pinecone_namespaces:
        try:
            knowledge = create_knowledge(ns)
            agent_kwargs["knowledge"] = knowledge
            agent_kwargs["search_knowledge"] = True
            break  # Use first successful namespace as primary
        except Exception as e:
            logger.warning(
                "specialist_knowledge_failed",
                specialist=specialist_key,
                namespace=ns,
                error=str(e),
            )

    # Resolve tools (full specialist tool set)
    resolver = resolve_tools_for_copilot if use_hitl else resolve_tools
    resolved = resolver(spec.tools)
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
        "specialist_agent_created",
        specialist=specialist_key,
        category=category,
        model=spec.model,
        tools_count=len(resolved),
        namespaces=spec.pinecone_namespaces,
        learning_enabled="learning" in agent_kwargs,
    )

    return agent
