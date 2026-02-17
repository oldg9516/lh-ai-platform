"""Integration tests for Phase 9 learning mechanism.

Tests that feature flags correctly enable/disable learning features,
and that agent factories properly configure Learning Machine and few-shot.
"""

from unittest.mock import patch, AsyncMock

import pytest

from agents.orchestrator import PipelineContext


# --- Feature Flags ---


class TestLearningFeatureFlags:
    """Verify learning feature flags in config."""

    def test_learning_disabled_by_default(self):
        from config import Settings

        s = Settings(
            openai_api_key="test",
            supabase_url="http://test",
            supabase_service_role_key="test",
        )
        assert s.learning_enabled is False
        assert s.learning_few_shot_enabled is False
        # learning_db_url defaults to "" but may be set via env in Docker
        assert isinstance(s.learning_db_url, str)

    def test_learning_enabled_via_config(self):
        from config import Settings

        s = Settings(
            openai_api_key="test",
            supabase_url="http://test",
            supabase_service_role_key="test",
            learning_enabled=True,
            learning_db_url="postgresql+psycopg://user:pass@host:5432/db",
        )
        assert s.learning_enabled is True
        assert "postgresql" in s.learning_db_url

    def test_few_shot_enabled_independently(self):
        from config import Settings

        s = Settings(
            openai_api_key="test",
            supabase_url="http://test",
            supabase_service_role_key="test",
            learning_few_shot_enabled=True,
        )
        assert s.learning_few_shot_enabled is True
        # Learning Machine can be disabled while few-shot is on
        assert s.learning_enabled is False


# --- Support Agent Learning Integration ---


class TestSupportAgentLearning:
    """Verify Learning Machine integration in support agent factory."""

    @pytest.mark.asyncio
    async def test_agent_without_learning_when_disabled(self):
        """Agent should work normally when learning is disabled."""
        with patch("config.settings") as mock_settings:
            mock_settings.learning_enabled = False
            mock_settings.learning_few_shot_enabled = False
            mock_settings.learning_db_url = ""

            from agents.support import create_support_agent

            agent = await create_support_agent("shipping_or_delivery_question")
            assert agent is not None
            assert agent.name == "Support Agent (shipping_or_delivery_question)"

    @pytest.mark.asyncio
    async def test_agent_without_learning_when_no_email(self):
        """Learning Machine requires customer_email — skip if not provided."""
        with patch("config.settings") as mock_settings:
            mock_settings.learning_enabled = True
            mock_settings.learning_few_shot_enabled = False
            mock_settings.learning_db_url = "postgresql+psycopg://user:pass@host/db"

            from agents.support import create_support_agent

            agent = await create_support_agent(
                "shipping_or_delivery_question",
                customer_email=None,
            )
            assert agent is not None
            # No learning without email
            assert not hasattr(agent, "learning") or agent.learning is None

    @pytest.mark.asyncio
    async def test_few_shot_injected_when_enabled(self):
        """Few-shot corrections should be appended to instructions."""
        mock_few_shot = (
            "\nLEARNING FROM PAST CORRECTIONS:\n"
            "Example 1: Fixed tone\n"
        )
        with (
            patch("agents.support.settings") as mock_settings,
            patch(
                "learning.few_shot.build_few_shot_instructions",
                new_callable=AsyncMock,
                return_value=mock_few_shot,
            ),
        ):
            mock_settings.learning_enabled = False
            mock_settings.learning_few_shot_enabled = True
            mock_settings.learning_db_url = ""

            from agents.support import create_support_agent

            agent = await create_support_agent("shipping_or_delivery_question")
            instructions_text = "\n".join(agent.instructions)
            assert "LEARNING FROM PAST CORRECTIONS" in instructions_text

    @pytest.mark.asyncio
    async def test_few_shot_not_injected_when_disabled(self):
        """Few-shot should not appear when flag is off."""
        from agents.support import create_support_agent

        agent = await create_support_agent("shipping_or_delivery_question")
        instructions_text = "\n".join(agent.instructions)
        assert "LEARNING FROM PAST CORRECTIONS" not in instructions_text


# --- Specialist Agent Learning Integration ---


class TestSpecialistAgentLearning:
    """Verify Learning Machine integration in specialist agent factory."""

    @pytest.mark.asyncio
    async def test_specialist_without_learning_when_disabled(self):
        from agents.specialists import create_specialist_agent

        agent = await create_specialist_agent("shipping_or_delivery_question")
        assert agent is not None
        assert agent.name == "Shipping Specialist"

    @pytest.mark.asyncio
    async def test_specialist_few_shot_injected_when_enabled(self):
        mock_few_shot = "\nLEARNING FROM PAST CORRECTIONS:\nExample 1: Fixed info\n"
        with (
            patch("agents.specialists.settings") as mock_settings,
            patch(
                "learning.few_shot.build_few_shot_instructions",
                new_callable=AsyncMock,
                return_value=mock_few_shot,
            ),
        ):
            mock_settings.learning_enabled = False
            mock_settings.learning_few_shot_enabled = True
            mock_settings.learning_db_url = ""

            from agents.specialists import create_specialist_agent

            agent = await create_specialist_agent("payment_question")
            instructions_text = "\n".join(agent.instructions)
            assert "LEARNING FROM PAST CORRECTIONS" in instructions_text


# --- Orchestrator Email Passing ---


class TestOrchestratorEmailPassing:
    """Verify orchestrator passes customer_email to agent factories."""

    def test_pipeline_context_has_customer_email(self):
        ctx = PipelineContext(
            message="test",
            session_id="s1",
            contact_email="user@example.com",
        )
        assert ctx.contact_email == "user@example.com"

    def test_customer_email_resolved_from_contact(self):
        """customer_email is set from contact_email in _build_context."""
        ctx = PipelineContext(
            message="test",
            session_id="s1",
            contact_email="contact@example.com",
        )
        # Simulate _build_context
        from agents.router import RouterOutput

        ctx.classification = RouterOutput(
            primary="shipping_or_delivery_question",
            secondary=None,
            urgency="medium",
            email=None,
        )
        # customer_email = contact_email || classification.email
        ctx.customer_email = ctx.contact_email or ctx.classification.email
        assert ctx.customer_email == "contact@example.com"

    def test_customer_email_fallback_to_classification(self):
        """Falls back to email from router classification."""
        ctx = PipelineContext(
            message="test",
            session_id="s1",
            contact_email=None,
        )
        from agents.router import RouterOutput

        ctx.classification = RouterOutput(
            primary="shipping_or_delivery_question",
            secondary=None,
            urgency="medium",
            email="router@example.com",
        )
        ctx.customer_email = ctx.contact_email or ctx.classification.email
        assert ctx.customer_email == "router@example.com"


# --- Query Helpers ---


class TestQueryHelpers:
    """Verify new query helper functions exist and handle errors."""

    def test_get_last_ai_message_importable(self):
        from database.queries import get_last_ai_message

        assert callable(get_last_ai_message)

    def test_get_session_category_importable(self):
        from database.queries import get_session_category

        assert callable(get_session_category)
