"""Unit tests for learning/few_shot.py — Few-shot injection."""

from unittest.mock import patch

import pytest

from learning.few_shot import _MAX_EXAMPLE_LENGTH, build_few_shot_instructions


# --- build_few_shot_instructions ---


class TestBuildFewShotInstructions:
    """Verify few-shot instruction builder."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_corrections(self):
        with patch("learning.few_shot.get_recent_corrections", return_value=[]):
            result = await build_few_shot_instructions("shipping_or_delivery_question")
        assert result is None

    @pytest.mark.asyncio
    async def test_formats_single_correction(self):
        corrections = [
            {
                "ai_response": "Your package is on the way.",
                "human_edit": "Your package shipped Jan 5, tracking: ABC123.",
                "specific_issue": "Missing tracking info",
            },
        ]
        with patch("learning.few_shot.get_recent_corrections", return_value=corrections):
            result = await build_few_shot_instructions("shipping_or_delivery_question")

        assert result is not None
        assert "LEARNING FROM PAST CORRECTIONS" in result
        assert "Example 1:" in result
        assert "Missing tracking info" in result
        assert "Your package is on the way." in result
        assert "tracking: ABC123" in result

    @pytest.mark.asyncio
    async def test_formats_multiple_corrections(self):
        corrections = [
            {
                "ai_response": "Response 1",
                "human_edit": "Edit 1",
                "specific_issue": "Issue 1",
            },
            {
                "ai_response": "Response 2",
                "human_edit": "Edit 2",
                "specific_issue": "Issue 2",
            },
            {
                "ai_response": "Response 3",
                "human_edit": "Edit 3",
                "specific_issue": "Issue 3",
            },
        ]
        with patch("learning.few_shot.get_recent_corrections", return_value=corrections):
            result = await build_few_shot_instructions("payment_question")

        assert "Example 1:" in result
        assert "Example 2:" in result
        assert "Example 3:" in result
        assert "Issue 1" in result
        assert "Issue 3" in result

    @pytest.mark.asyncio
    async def test_truncates_long_responses(self):
        long_text = "A" * 500
        corrections = [
            {
                "ai_response": long_text,
                "human_edit": long_text,
                "specific_issue": "Long response",
            },
        ]
        with patch("learning.few_shot.get_recent_corrections", return_value=corrections):
            result = await build_few_shot_instructions("shipping_or_delivery_question")

        assert result is not None
        # Should be truncated with ellipsis
        assert "..." in result
        # Should not contain the full 500-char text
        assert long_text not in result

    @pytest.mark.asyncio
    async def test_handles_missing_specific_issue(self):
        corrections = [
            {
                "ai_response": "Response",
                "human_edit": "Better response",
                "specific_issue": None,
            },
        ]
        with patch("learning.few_shot.get_recent_corrections", return_value=corrections):
            result = await build_few_shot_instructions("gratitude")

        assert result is not None
        assert "Not specified" in result

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self):
        corrections = [
            {
                "ai_response": f"Response {i}",
                "human_edit": f"Edit {i}",
                "specific_issue": f"Issue {i}",
            }
            for i in range(5)
        ]
        with patch("learning.few_shot.get_recent_corrections", return_value=corrections[:2]) as mock:
            await build_few_shot_instructions("payment_question", limit=2)
        mock.assert_called_once_with("payment_question", limit=2)

    @pytest.mark.asyncio
    async def test_handles_empty_fields_gracefully(self):
        corrections = [
            {
                "ai_response": "",
                "human_edit": "",
                "specific_issue": "",
            },
        ]
        with patch("learning.few_shot.get_recent_corrections", return_value=corrections):
            result = await build_few_shot_instructions("shipping_or_delivery_question")

        # Should still produce output without errors
        assert result is not None
        assert "Example 1:" in result

    def test_max_example_length_constant(self):
        assert _MAX_EXAMPLE_LENGTH == 200
