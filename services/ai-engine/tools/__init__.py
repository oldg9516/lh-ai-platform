"""Action tools for the AI Engine.

TOOL_REGISTRY maps string tool names (from CATEGORY_CONFIG) to
callable functions. resolve_tools() converts a list of string
names into a list of callables for the Agno Agent.
"""

import structlog

from tools.customer import get_customer_history, get_payment_history, get_subscription
from tools.customization import get_box_contents
from tools.damage import create_damage_claim, request_photos
from tools import hitl_proxies
from tools.retention import generate_cancel_link
from tools.shipping import track_package
from tools.subscription import change_address, change_frequency, pause_subscription, skip_month

logger = structlog.get_logger()

TOOL_REGISTRY: dict[str, callable] = {
    "get_subscription": get_subscription,
    "get_customer_history": get_customer_history,
    "get_payment_history": get_payment_history,
    "track_package": track_package,
    "change_frequency": change_frequency,
    "skip_month": skip_month,
    "pause_subscription": pause_subscription,
    "change_address": change_address,
    "create_damage_claim": create_damage_claim,
    "request_photos": request_photos,
    "get_box_contents": get_box_contents,
    "generate_cancel_link": generate_cancel_link,
}

# Write tools that modify data. For CopilotKit HITL flow,
# these are replaced with proxy versions that return "pending_confirmation".
# The real execution happens via /api/copilot/execute-tool after user approval.
WRITE_TOOLS: set[str] = {
    "change_frequency",
    "skip_month",
    "pause_subscription",
    "change_address",
    "create_damage_claim",
    "request_photos",
}

# HITL proxy versions of write tools. Same signatures but return
# "pending_confirmation" instead of executing. Used in CopilotKit path
# so the LLM knows about the tools and can call them, triggering
# AG-UI ToolCall events → CopilotKit renders HITL forms.
HITL_PROXY_REGISTRY: dict[str, callable] = {
    "pause_subscription": hitl_proxies.pause_subscription,
    "skip_month": hitl_proxies.skip_month,
    "change_frequency": hitl_proxies.change_frequency,
    "change_address": hitl_proxies.change_address,
    "create_damage_claim": hitl_proxies.create_damage_claim,
}


def resolve_tools(tool_names: list[str]) -> list[callable]:
    """Resolve a list of tool name strings to callable functions.

    Args:
        tool_names: List of tool name strings from CATEGORY_CONFIG.

    Returns:
        List of callable tool functions for Agno Agent(tools=[...]).
    """
    tools = []
    for name in tool_names:
        fn = TOOL_REGISTRY.get(name)
        if fn is None:
            logger.warning("unknown_tool_name", tool_name=name)
            continue
        tools.append(fn)
    return tools


def resolve_tools_for_copilot(tool_names: list[str]) -> list[callable]:
    """Resolve tools for CopilotKit HITL flow.

    Write tools are replaced with HITL proxy versions that return
    "pending_confirmation". This way the LLM knows about the tools
    and calls them, which emits AG-UI ToolCall events. CopilotKit
    intercepts these and renders confirmation forms.

    Args:
        tool_names: List of tool name strings from CATEGORY_CONFIG.

    Returns:
        List of callable tool functions (read-only + HITL proxies).
    """
    tools = []
    proxied = []
    for name in tool_names:
        if name in HITL_PROXY_REGISTRY:
            tools.append(HITL_PROXY_REGISTRY[name])
            proxied.append(name)
        else:
            fn = TOOL_REGISTRY.get(name)
            if fn is None:
                logger.warning("unknown_tool_name", tool_name=name)
                continue
            tools.append(fn)
    logger.info(
        "resolve_tools_copilot",
        total=len(tool_names),
        resolved=len(tools),
        hitl_proxied=proxied,
    )
    return tools
