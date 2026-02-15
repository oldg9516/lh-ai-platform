"""AG-UI Endpoint for CopilotKit Integration.

This module exposes Agno support agents via the AG-UI protocol,
enabling frontend interaction through CopilotKit.

Phase 6.2: Initial AG-UI implementation
Phase 6.3: HITL tool integration
Phase 7: Multi-turn conversation state

Architecture:
- Frontend (Next.js) → HttpAgent → FastAPI (this endpoint)
- AGUIApp wraps Agno Agent for AG-UI protocol compatibility
- Streaming responses via Server-Sent Events (SSE)
"""

from fastapi import APIRouter
import structlog

from agents.support import create_support_agent

# Try importing AGUI from Agno
try:
    from agno.os import AgentOS
    from agno.os.interfaces.agui import AGUI
    AGUI_AVAILABLE = True
except ImportError:
    try:
        from agno.app.agui.app import AGUIApp
        AGUI_AVAILABLE = True
    except ImportError:
        AGUI_AVAILABLE = False

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def copilot_health():
    """Health check for AG-UI endpoint."""
    return {
        "status": "healthy",
        "service": "ag-ui-copilot",
        "agui_available": AGUI_AVAILABLE,
    }


# Phase 6.2: AG-UI endpoint implementation
# TODO: Implement AG-UI protocol wrapper for Agno agents
#
# Options:
# 1. Use AgentOS + AGUI interface (recommended for production)
# 2. Use AGUIApp wrapper (simpler for prototyping)
#
# Example (AgentOS approach):
# ```python
# agent = create_support_agent("shipping_or_delivery_question")
# agent_os = AgentOS(agents=[agent], interfaces=[AGUI(agent=agent)])
# app = agent_os.get_app()
# router.mount("/", app)
# ```
#
# For now, return stub response indicating backend is ready
@router.post("/")
async def copilot_endpoint():
    """AG-UI protocol endpoint for CopilotKit.

    Phase 6.2: Stub implementation
    Phase 6.3: Full AG-UI streaming with tool calls
    """
    if not AGUI_AVAILABLE:
        return {
            "error": "AGUI not available",
            "message": "Agno AG-UI interface not found. Check Agno SDK version.",
        }

    logger.info("copilot_endpoint_called", agui_available=AGUI_AVAILABLE)

    return {
        "status": "stub",
        "message": "AG-UI endpoint ready. Full implementation coming in Phase 6.3",
        "backend": "FastAPI + Agno AgentOS",
        "protocol": "AG-UI",
    }
