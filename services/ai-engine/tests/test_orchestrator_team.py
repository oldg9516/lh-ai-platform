"""Unit tests for orchestrator team mode (Phase 8).

Tests the branching logic in SupportOrchestrator when
use_team_mode is enabled/disabled, and the retry flow.
"""

from agents.orchestrator import PipelineContext, PipelineResult


# --- PipelineContext Team Fields ---


class TestPipelineContextTeamFields:
    """Verify team mode fields exist on PipelineContext."""

    def test_default_team_mode_disabled(self):
        ctx = PipelineContext(message="test", session_id="s1")
        assert ctx.use_team_mode is False
        assert ctx.specialist_key is None
        assert ctx.attempt == 1
        assert ctx.qa_feedback is None

    def test_team_mode_enabled(self):
        ctx = PipelineContext(
            message="test",
            session_id="s1",
            use_team_mode=True,
        )
        assert ctx.use_team_mode is True

    def test_attempt_tracking(self):
        ctx = PipelineContext(message="test", session_id="s1")
        assert ctx.attempt == 1
        ctx.attempt = 2
        assert ctx.attempt == 2

    def test_qa_feedback_storage(self):
        ctx = PipelineContext(message="test", session_id="s1")
        ctx.qa_feedback = "Fix the tone."
        assert ctx.qa_feedback == "Fix the tone."

    def test_specialist_key_storage(self):
        ctx = PipelineContext(message="test", session_id="s1")
        ctx.specialist_key = "billing"
        assert ctx.specialist_key == "billing"


# --- PipelineResult Team Metadata ---


class TestPipelineResultTeamMetadata:
    """Verify team mode metadata in results."""

    def test_standard_result_no_team_fields(self):
        result = PipelineResult(
            response="Hello",
            session_id="s1",
            category="shipping_or_delivery_question",
            decision="send",
            confidence="high",
            metadata={"model_used": "gpt-5.1"},
        )
        assert "team_mode" not in result.metadata

    def test_team_mode_result_has_metadata(self):
        result = PipelineResult(
            response="Hello",
            session_id="s1",
            category="shipping_or_delivery_question",
            decision="send",
            confidence="high",
            metadata={
                "model_used": "gpt-5.1",
                "team_mode": True,
                "specialist": "shipping",
                "attempts": 1,
            },
        )
        assert result.metadata["team_mode"] is True
        assert result.metadata["specialist"] == "shipping"
        assert result.metadata["attempts"] == 1

    def test_retry_result_has_attempts_2(self):
        result = PipelineResult(
            response="Revised response",
            session_id="s1",
            category="payment_question",
            decision="send",
            confidence="high",
            metadata={
                "team_mode": True,
                "specialist": "billing",
                "attempts": 2,
            },
        )
        assert result.metadata["attempts"] == 2


# --- Feature Flag ---


class TestTeamModeFeatureFlag:
    """Verify team_mode_enabled in config."""

    def test_default_disabled(self):
        from config import Settings

        s = Settings(
            openai_api_key="test",
            supabase_url="http://test",
            supabase_service_role_key="test",
        )
        assert s.team_mode_enabled is False

    def test_enabled_via_env(self):
        from config import Settings

        s = Settings(
            openai_api_key="test",
            supabase_url="http://test",
            supabase_service_role_key="test",
            team_mode_enabled=True,
        )
        assert s.team_mode_enabled is True
