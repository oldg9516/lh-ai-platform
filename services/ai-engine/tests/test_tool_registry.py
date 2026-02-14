"""Unit tests for tool registry and resolution."""

from tools import TOOL_REGISTRY, resolve_tools


class TestToolRegistry:
    def test_all_category_config_tools_registered(self):
        """Every tool name in CATEGORY_CONFIG exists in the registry."""
        from agents.config import CATEGORY_CONFIG

        all_tool_names: set[str] = set()
        for config in CATEGORY_CONFIG.values():
            all_tool_names.update(config.tools)
        for name in all_tool_names:
            assert name in TOOL_REGISTRY, f"Tool '{name}' not in TOOL_REGISTRY"

    def test_registry_values_are_callable(self):
        for name, fn in TOOL_REGISTRY.items():
            assert callable(fn), f"Tool '{name}' is not callable"

    def test_registry_has_expected_count(self):
        assert len(TOOL_REGISTRY) == 12


class TestResolveTools:
    def test_resolve_known_tools(self):
        tools = resolve_tools(["get_subscription", "track_package"])
        assert len(tools) == 2
        assert all(callable(t) for t in tools)

    def test_resolve_empty_list(self):
        assert resolve_tools([]) == []

    def test_resolve_unknown_tool_skipped(self):
        tools = resolve_tools(["get_subscription", "nonexistent_tool"])
        assert len(tools) == 1

    def test_resolve_shipping_tools(self):
        tools = resolve_tools(["get_subscription", "track_package"])
        assert len(tools) == 2

    def test_resolve_retention_tools(self):
        tools = resolve_tools(["get_subscription", "generate_cancel_link", "get_customer_history"])
        assert len(tools) == 3
