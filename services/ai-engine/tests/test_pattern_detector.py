"""Tests for learning/pattern_detector.py — Phase 9.2."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from learning.pattern_detector import (
    InstructionFix,
    detect_recurring_patterns,
    suggest_instruction_fix,
    run_pattern_analysis,
)


# --- InstructionFix Model ---


class TestInstructionFixModel:
    def test_basic(self):
        fix = InstructionFix(
            issue_pattern="Tone too formal in gratitude",
            suggested_fix="Use warmer language when responding to gratitude messages.",
        )
        assert fix.issue_pattern == "Tone too formal in gratitude"
        assert "warmer" in fix.suggested_fix


# --- detect_recurring_patterns ---


class TestDetectRecurringPatterns:
    def _make_corrections(self, category, correction_type, count):
        return [
            {
                "id": f"id-{i}",
                "category": category,
                "correction_type": correction_type,
                "ai_response": f"Original {i}",
                "human_edit": f"Edited {i}",
                "specific_issue": f"Issue {i}",
                "created_at": "2026-02-17T10:00:00Z",
            }
            for i in range(count)
        ]

    @patch("learning.pattern_detector.get_instruction_updates", return_value=[])
    @patch("learning.pattern_detector.get_client")
    def test_detects_pattern_above_threshold(self, mock_client, mock_updates):
        corrections = self._make_corrections("shipping_or_delivery_question", "tone", 4)
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=corrections)

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert len(patterns) == 1
        assert patterns[0]["category"] == "shipping_or_delivery_question"
        assert patterns[0]["correction_type"] == "tone"
        assert patterns[0]["frequency"] == 4

    @patch("learning.pattern_detector.get_instruction_updates", return_value=[])
    @patch("learning.pattern_detector.get_client")
    def test_ignores_below_threshold(self, mock_client, mock_updates):
        corrections = self._make_corrections("gratitude", "tone", 2)
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=corrections)

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert len(patterns) == 0

    @patch("learning.pattern_detector.get_instruction_updates", return_value=[])
    @patch("learning.pattern_detector.get_client")
    def test_returns_empty_on_no_corrections(self, mock_client, mock_updates):
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert patterns == []

    @patch("learning.pattern_detector.get_instruction_updates")
    @patch("learning.pattern_detector.get_client")
    def test_skips_already_tracked_pattern(self, mock_client, mock_updates):
        corrections = self._make_corrections("shipping_or_delivery_question", "tone", 5)
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=corrections)
        # Existing pending update for this pattern
        mock_updates.return_value = [
            {"status": "pending", "issue_pattern": "Recurring tone issue in shipping"}
        ]

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert len(patterns) == 0

    @patch("learning.pattern_detector.get_instruction_updates", return_value=[])
    @patch("learning.pattern_detector.get_client")
    def test_multiple_groups(self, mock_client, mock_updates):
        tone_corrections = self._make_corrections("shipping_or_delivery_question", "tone", 3)
        accuracy_corrections = self._make_corrections("payment_question", "accuracy", 4)
        below_threshold = self._make_corrections("gratitude", "completeness", 1)
        all_corrections = tone_corrections + accuracy_corrections + below_threshold
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=all_corrections)

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert len(patterns) == 2
        categories = {p["category"] for p in patterns}
        assert "shipping_or_delivery_question" in categories
        assert "payment_question" in categories

    @patch("learning.pattern_detector.get_instruction_updates", return_value=[])
    @patch("learning.pattern_detector.get_client")
    def test_caps_examples_at_5(self, mock_client, mock_updates):
        corrections = self._make_corrections("shipping_or_delivery_question", "tone", 10)
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=corrections)

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert len(patterns) == 1
        assert len(patterns[0]["examples"]) == 5

    @patch("learning.pattern_detector.get_client")
    def test_handles_db_error(self, mock_client):
        mock_client.return_value.table.return_value.select.return_value.gte.return_value.order.return_value.execute.side_effect = Exception("DB error")

        patterns = detect_recurring_patterns(min_frequency=3, window_days=7)

        assert patterns == []


# --- suggest_instruction_fix ---


class TestSuggestInstructionFix:
    @pytest.mark.asyncio
    async def test_returns_instruction_fix(self):
        mock_fix = InstructionFix(
            issue_pattern="AI uses overly formal tone",
            suggested_fix="Use a warmer, friendlier tone.",
        )
        with patch("agno.agent.Agent") as MockAgent:
            instance = MockAgent.return_value
            instance.arun = AsyncMock(return_value=MagicMock(content=mock_fix))

            result = await suggest_instruction_fix(
                category="gratitude",
                correction_type="tone",
                examples=[{"ai_response": "Hi.", "human_edit": "Hi there!", "specific_issue": "Too cold"}],
            )

        assert result.issue_pattern == "AI uses overly formal tone"
        assert "warmer" in result.suggested_fix

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        with patch("agno.agent.Agent") as MockAgent:
            instance = MockAgent.return_value
            instance.arun = AsyncMock(side_effect=Exception("LLM error"))

            result = await suggest_instruction_fix(
                category="shipping_or_delivery_question",
                correction_type="accuracy",
                examples=[],
            )

        assert "accuracy" in result.suggested_fix
        assert "shipping_or_delivery_question" in result.issue_pattern

    @pytest.mark.asyncio
    async def test_fallback_on_non_schema_result(self):
        with patch("agno.agent.Agent") as MockAgent:
            instance = MockAgent.return_value
            instance.arun = AsyncMock(return_value=MagicMock(content="plain string"))

            result = await suggest_instruction_fix(
                category="payment_question",
                correction_type="tone",
                examples=[],
            )

        # Should return a generic fallback fix
        assert isinstance(result, InstructionFix)


# --- run_pattern_analysis ---


class TestRunPatternAnalysis:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_patterns(self):
        with patch("learning.pattern_detector.detect_recurring_patterns", return_value=[]):
            result = await run_pattern_analysis()

        assert result == []

    @pytest.mark.asyncio
    async def test_creates_updates_for_detected_patterns(self):
        patterns = [
            {
                "category": "shipping_or_delivery_question",
                "correction_type": "tone",
                "frequency": 5,
                "examples": [
                    {"specific_issue": "Too formal", "correction_type": "tone"},
                ],
            }
        ]
        mock_fix = InstructionFix(
            issue_pattern="Formal tone in shipping",
            suggested_fix="Use casual tone.",
        )

        with (
            patch("learning.pattern_detector.detect_recurring_patterns", return_value=patterns),
            patch("learning.pattern_detector.suggest_instruction_fix", new_callable=AsyncMock, return_value=mock_fix),
            patch("learning.pattern_detector.save_instruction_update", return_value="uuid-123"),
        ):
            result = await run_pattern_analysis()

        assert result == ["uuid-123"]

    @pytest.mark.asyncio
    async def test_continues_on_save_error(self):
        patterns = [
            {
                "category": "cat1",
                "correction_type": "tone",
                "frequency": 3,
                "examples": [],
            },
            {
                "category": "cat2",
                "correction_type": "accuracy",
                "frequency": 4,
                "examples": [],
            },
        ]
        mock_fix = InstructionFix(issue_pattern="x", suggested_fix="y")

        call_count = 0

        def save_side_effect(data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("DB error")
            return "uuid-456"

        with (
            patch("learning.pattern_detector.detect_recurring_patterns", return_value=patterns),
            patch("learning.pattern_detector.suggest_instruction_fix", new_callable=AsyncMock, return_value=mock_fix),
            patch("learning.pattern_detector.save_instruction_update", side_effect=save_side_effect),
        ):
            result = await run_pattern_analysis()

        # First failed, second succeeded
        assert result == ["uuid-456"]
