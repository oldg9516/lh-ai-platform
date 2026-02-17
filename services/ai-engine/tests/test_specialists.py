"""Unit tests for agents/specialists.py — Specialist Agent configs and factory."""

import pytest

from agents.config import VALID_CATEGORIES
from agents.specialists import (
    CATEGORY_TO_SPECIALIST,
    SPECIALIST_CONFIGS,
    SpecialistConfig,
    create_specialist_agent,
)


# --- Config Tests ---


class TestSpecialistConfigs:
    """Verify specialist configuration structure."""

    def test_four_specialists_defined(self):
        assert len(SPECIALIST_CONFIGS) == 4
        assert set(SPECIALIST_CONFIGS.keys()) == {"billing", "shipping", "retention", "quality"}

    def test_all_categories_covered(self):
        """Every valid category must map to a specialist."""
        for category in VALID_CATEGORIES:
            assert category in CATEGORY_TO_SPECIALIST, f"{category} not mapped to specialist"

    def test_no_duplicate_categories(self):
        """Each category should belong to exactly one specialist."""
        seen = {}
        for key, spec in SPECIALIST_CONFIGS.items():
            for cat in spec.categories:
                assert cat not in seen, f"{cat} in both {seen[cat]} and {key}"
                seen[cat] = key

    def test_billing_config(self):
        billing = SPECIALIST_CONFIGS["billing"]
        assert billing.name == "Billing Specialist"
        assert "payment_question" in billing.categories
        assert "frequency_change_request" in billing.categories
        assert "skip_or_pause_request" in billing.categories
        assert "get_payment_history" in billing.tools
        assert "change_frequency" in billing.tools

    def test_shipping_config(self):
        shipping = SPECIALIST_CONFIGS["shipping"]
        assert "shipping_or_delivery_question" in shipping.categories
        assert "recipient_or_address_change" in shipping.categories
        assert "track_package" in shipping.tools
        assert "change_address" in shipping.tools

    def test_retention_config(self):
        retention = SPECIALIST_CONFIGS["retention"]
        assert "retention_primary_request" in retention.categories
        assert "retention_repeated_request" in retention.categories
        assert retention.reasoning_effort == "medium"
        assert retention.model_provider == "openai_responses"
        assert "generate_cancel_link" in retention.tools

    def test_quality_config(self):
        quality = SPECIALIST_CONFIGS["quality"]
        assert "damaged_or_leaking_item_report" in quality.categories
        assert "customization_request" in quality.categories
        assert "gratitude" in quality.categories
        assert "create_damage_claim" in quality.tools
        assert "request_photos" in quality.tools

    def test_specialist_has_broader_tools_than_category(self):
        """Specialist should have more tools than a single category config."""
        from agents.config import CATEGORY_CONFIG

        for key, spec in SPECIALIST_CONFIGS.items():
            for cat in spec.categories:
                cat_tools = set(CATEGORY_CONFIG[cat].tools)
                spec_tools = set(spec.tools)
                # Specialist tools should be a superset of any single category's tools
                assert cat_tools.issubset(spec_tools), (
                    f"Specialist {key} missing tools {cat_tools - spec_tools} from {cat}"
                )


class TestCategoryToSpecialist:
    """Verify reverse lookup mapping."""

    def test_shipping_category_maps_to_shipping(self):
        assert CATEGORY_TO_SPECIALIST["shipping_or_delivery_question"] == "shipping"

    def test_payment_category_maps_to_billing(self):
        assert CATEGORY_TO_SPECIALIST["payment_question"] == "billing"

    def test_retention_category_maps_to_retention(self):
        assert CATEGORY_TO_SPECIALIST["retention_primary_request"] == "retention"

    def test_damage_category_maps_to_quality(self):
        assert CATEGORY_TO_SPECIALIST["damaged_or_leaking_item_report"] == "quality"

    def test_gratitude_maps_to_quality(self):
        assert CATEGORY_TO_SPECIALIST["gratitude"] == "quality"


# --- Factory Tests ---


class TestCreateSpecialistAgent:
    """Verify specialist agent creation."""

    @pytest.mark.asyncio
    async def test_creates_shipping_specialist(self):
        agent = await create_specialist_agent("shipping_or_delivery_question")
        assert agent.name == "Shipping Specialist"

    @pytest.mark.asyncio
    async def test_creates_billing_specialist(self):
        agent = await create_specialist_agent("payment_question")
        assert agent.name == "Billing Specialist"

    @pytest.mark.asyncio
    async def test_creates_retention_specialist(self):
        agent = await create_specialist_agent("retention_primary_request")
        assert agent.name == "Retention Specialist"

    @pytest.mark.asyncio
    async def test_creates_quality_specialist(self):
        agent = await create_specialist_agent("damaged_or_leaking_item_report")
        assert agent.name == "Quality Specialist"

    @pytest.mark.asyncio
    async def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="No specialist mapping"):
            await create_specialist_agent("nonexistent_category")

    @pytest.mark.asyncio
    async def test_specialist_has_tools(self):
        agent = await create_specialist_agent("shipping_or_delivery_question")
        assert agent.tools is not None
        assert len(agent.tools) > 0

    @pytest.mark.asyncio
    async def test_specialist_has_instructions(self):
        agent = await create_specialist_agent("shipping_or_delivery_question")
        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    @pytest.mark.asyncio
    async def test_specialist_role_in_instructions(self):
        """Specialist role should be prepended to instructions."""
        agent = await create_specialist_agent("shipping_or_delivery_question")
        # Role is the first instruction
        first_instruction = agent.instructions[0]
        assert "Shipping Specialist" in first_instruction

    @pytest.mark.asyncio
    async def test_customer_email_added_to_instructions(self):
        agent = await create_specialist_agent(
            "shipping_or_delivery_question",
            customer_email="test@example.com",
        )
        instructions_text = "\n".join(agent.instructions)
        assert "test@example.com" in instructions_text
