"""Action tools for the AI Engine.

TOOL_REGISTRY maps string tool names (from CATEGORY_CONFIG) to
callable functions. resolve_tools() converts a list of string
names into a list of callables for the Agno Agent.
"""

import structlog

from tools.customer import get_customer_history, get_payment_history, get_subscription
from tools.customization import get_box_contents
from tools.damage import create_damage_claim, request_photos
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
# these are provided by the frontend via useHumanInTheLoop
# and should NOT be included in the backend agent's toolset.
WRITE_TOOLS: set[str] = {
    "change_frequency",
    "skip_month",
    "pause_subscription",
    "change_address",
    "create_damage_claim",
    "request_photos",
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
    """Resolve tools excluding write operations for CopilotKit HITL flow.

    In the CopilotKit path, write tools come from the frontend via
    useHumanInTheLoop. The backend agent should only have read-only tools.

    Args:
        tool_names: List of tool name strings from CATEGORY_CONFIG.

    Returns:
        List of read-only callable tool functions.
    """
    read_only_names = [name for name in tool_names if name not in WRITE_TOOLS]
    logger.info(
        "resolve_tools_copilot",
        total=len(tool_names),
        read_only=len(read_only_names),
        filtered_out=[name for name in tool_names if name in WRITE_TOOLS],
    )
    return resolve_tools(read_only_names)
