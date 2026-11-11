"""GPT-6.x routing: tool-using agents must go through the Responses API.

GPT-6.x reasoning models reject function tools in /v1/chat/completions
("Function tools with reasoning_effort are not supported"), so every
OpenAI agent that has tools or knowledge search is built on OpenAIResponses.
"""

from agno.models.openai import OpenAIResponses

from agents.config import CATEGORY_CONFIG
from agents.specialists import SPECIALIST_CONFIGS
from agents.support import _resolve_model
from api.copilot import _to_responses_tool


class TestCategoryModels:
    def test_every_openai_category_uses_responses_api(self):
        for category, config in CATEGORY_CONFIG.items():
            if config.model_provider == "anthropic":
                continue
            assert config.model_provider == "openai_responses", category
            assert isinstance(_resolve_model(config), OpenAIResponses), category

    def test_reasoning_effort_passed_through(self):
        model = _resolve_model(CATEGORY_CONFIG["retention_primary_request"])
        assert model.reasoning_effort == "medium"

    def test_no_legacy_models(self):
        for config in CATEGORY_CONFIG.values():
            assert config.model.startswith("gpt-6"), config.model
        for spec in SPECIALIST_CONFIGS.values():
            assert spec.model.startswith("gpt-6"), spec.model
            assert spec.model_provider == "openai_responses"


class TestResponsesToolSchema:
    def test_chat_schema_flattened(self):
        chat_tool = {
            "type": "function",
            "function": {
                "name": "get_subscription",
                "description": "Get subscription",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        assert _to_responses_tool(chat_tool) == {
            "type": "function",
            "name": "get_subscription",
            "description": "Get subscription",
            "parameters": {"type": "object", "properties": {}},
        }

    def test_already_flat_schema_unchanged(self):
        flat = {"type": "function", "name": "x", "parameters": {}}
        assert _to_responses_tool(flat) == flat
