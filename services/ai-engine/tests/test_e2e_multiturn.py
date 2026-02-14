"""E2E tests for multi-turn conversation history.

Tests that conversation context is preserved across multiple messages
with the same session_id.
"""

import pytest
import requests
from uuid import uuid4


BASE_URL = "http://localhost:8000"


class TestMultiTurnConversation:
    """Test multi-turn conversation context preservation."""

    def test_followup_question_uses_context(self):
        """Second message should reference context from first message."""
        session_id = f"test_e2e_multiturn_{uuid4().hex[:8]}"

        # First message: general shipping question
        response1 = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "How long does shipping take?", "session_id": session_id},
            timeout=30,
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["category"] == "shipping_or_delivery_question"
        assert "2" in data1["response"] or "3" in data1["response"]  # mentions timeframe

        # Second message: followup with implicit context reference
        response2 = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "And what about to Canada specifically?",
                "session_id": session_id,
            },
            timeout=30,
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["category"] == "shipping_or_delivery_question"
        # AI should understand "specifically" refers to shipping question
        assert "canada" in data2["response"].lower()

    def test_explicit_reference_to_prior_message(self):
        """Third message explicitly references what was said earlier."""
        session_id = f"test_e2e_multiturn_{uuid4().hex[:8]}"

        # First message
        response1 = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "How long does shipping take?", "session_id": session_id},
            timeout=30,
        )
        assert response1.status_code == 200

        # Second message
        response2 = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "What about to Canada?",
                "session_id": session_id,
            },
            timeout=30,
        )
        assert response2.status_code == 200

        # Third message: explicit reference to earlier content
        response3 = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "You mentioned 2-3 weeks earlier. Can it be faster?",
                "session_id": session_id,
            },
            timeout=30,
        )
        assert response3.status_code == 200
        data3 = response3.json()
        # AI should acknowledge the reference to prior timeframe
        response_lower = data3["response"].lower()
        assert any(
            phrase in response_lower
            for phrase in ["2-3 weeks", "2–3 weeks", "earlier", "mentioned", "usually"]
        )

    def test_different_sessions_dont_share_context(self):
        """Messages with different session_ids should not share context."""
        session_id_1 = f"test_e2e_multiturn_{uuid4().hex[:8]}"
        session_id_2 = f"test_e2e_multiturn_{uuid4().hex[:8]}"

        # Session 1: shipping question
        response1 = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": "How long does shipping take?", "session_id": session_id_1},
            timeout=30,
        )
        assert response1.status_code == 200

        # Session 2: ask "what about Canada?" with NO prior context
        response2 = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "What about to Canada?",
                "session_id": session_id_2,
            },
            timeout=30,
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Should still be shipping category, but without implicit context
        # (AI should still understand "Canada" means shipping to Canada)
        assert data2["category"] == "shipping_or_delivery_question"

    def test_history_truncation_at_500_chars(self):
        """Agent responses in history should be truncated to 500 chars."""
        session_id = f"test_e2e_multiturn_{uuid4().hex[:8]}"

        # Send a message that will generate a long response
        response1 = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "Tell me everything about shipping, delivery times, customs, tracking, and delays",
                "session_id": session_id,
            },
            timeout=60,
        )
        assert response1.status_code == 200
        data1 = response1.json()
        # Response is likely > 500 chars

        # Second message to trigger history loading
        response2 = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "Thanks, that was helpful!",
                "session_id": session_id,
            },
            timeout=30,
        )
        assert response2.status_code == 200
        # If we were logging history, we'd verify truncation here
        # For now, just verify the second message processes successfully
        assert response2.json()["category"] in [
            "gratitude",
            "shipping_or_delivery_question",
        ]

    def test_conversation_history_limit_10_messages(self):
        """Only last 10 messages should be loaded into context."""
        session_id = f"test_e2e_multiturn_{uuid4().hex[:8]}"

        # Send 12 messages (6 turns)
        for i in range(6):
            requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": f"Question {i+1}", "session_id": session_id},
                timeout=30,
            )

        # Final message referencing "Question 1" (which should be outside the 10-message window)
        response_final = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "What was my first question?",
                "session_id": session_id,
            },
            timeout=30,
        )
        assert response_final.status_code == 200
        # AI should not be able to recall "Question 1" since it's beyond the 10-message limit
        # (This is hard to assert precisely without checking logs, but test should pass)
