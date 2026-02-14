"""Category configuration for the Support Agent factory.

CATEGORY_CONFIG drives all dynamic behavior: model selection,
reasoning effort, tools, and Pinecone namespace per category.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CategoryConfig:
    """Configuration for a single support category."""

    model: str
    model_provider: str  # "openai_chat" | "openai_responses" | "anthropic"
    reasoning_effort: str | None
    tools: list[str] = field(default_factory=list)
    pinecone_namespace: str = ""
    auto_send_phase: int = 99


CATEGORY_CONFIG: dict[str, CategoryConfig] = {
    "shipping_or_delivery_question": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=["get_subscription", "track_package"],
        pinecone_namespace="shipping",
        auto_send_phase=2,
    ),
    "payment_question": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_responses",
        reasoning_effort="medium",
        tools=["get_subscription", "get_payment_history"],
        pinecone_namespace="payment",
        auto_send_phase=3,
    ),
    "frequency_change_request": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=["get_subscription", "change_frequency"],
        pinecone_namespace="subscription",
        auto_send_phase=2,
    ),
    "skip_or_pause_request": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=["get_subscription", "skip_month", "pause_subscription"],
        pinecone_namespace="subscription",
        auto_send_phase=2,
    ),
    "recipient_or_address_change": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=["get_subscription", "change_address"],
        pinecone_namespace="subscription",
        auto_send_phase=2,
    ),
    "customization_request": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=["get_subscription", "get_box_contents"],
        pinecone_namespace="customization",
        auto_send_phase=2,
    ),
    "damaged_or_leaking_item_report": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=["get_subscription", "create_damage_claim", "request_photos"],
        pinecone_namespace="damage",
        auto_send_phase=3,
    ),
    "gratitude": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_chat",
        reasoning_effort=None,
        tools=[],
        pinecone_namespace="gratitude",
        auto_send_phase=1,
    ),
    "retention_primary_request": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_responses",
        reasoning_effort="medium",
        tools=["get_subscription", "generate_cancel_link", "get_customer_history"],
        pinecone_namespace="retention",
        auto_send_phase=4,
    ),
    "retention_repeated_request": CategoryConfig(
        model="gpt-5.1",
        model_provider="openai_responses",
        reasoning_effort="medium",
        tools=["get_subscription", "generate_cancel_link"],
        pinecone_namespace="retention",
        auto_send_phase=4,
    ),
}

VALID_CATEGORIES = list(CATEGORY_CONFIG.keys())
