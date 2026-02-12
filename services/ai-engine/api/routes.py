"""FastAPI routes for the AI Engine.

POST /api/chat — main pipeline: safety check → classify → generate → post-check → save.
GET  /api/health — service health check.
"""

import time
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
import structlog

from config import settings
from agents.config import CATEGORY_CONFIG
from agents.router import classify_message
from agents.support import create_support_agent
from guardrails.safety import check_red_lines, check_subscription_safety
from database.queries import save_session, save_message

logger = structlog.get_logger()
router = APIRouter()


# --- Request/Response Models ---


class ContactInfo(BaseModel):
    email: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    conversation_id: str | None = None
    contact: ContactInfo | None = None
    metadata: dict | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    category: str
    decision: str = "send"
    confidence: str = "high"
    actions_taken: list = Field(default_factory=list)
    actions_pending: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    services: dict
    version: str


# --- Endpoints ---


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Service health check."""
    db_status = "connected"
    try:
        from database.connection import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        services={
            "database": db_status,
            "pinecone": "available",
            "openai": "available",
            "anthropic": "available",
        },
        version=settings.app_version,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a customer message through the AI pipeline.

    Pipeline: red line check → classify → support agent → post-safety → save → respond.
    """
    start_time = time.time()
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:12]}"

    logger.info("chat_request_received", session_id=session_id)

    # Step 1: Red line safety check
    red_line_check = check_red_lines(request.message)
    if red_line_check["is_flagged"]:
        logger.warning(
            "red_line_triggered",
            session_id=session_id,
            trigger=red_line_check["trigger"],
        )
        return ChatResponse(
            response="I'm connecting you with a support agent who can better assist you.",
            session_id=session_id,
            category="unknown",
            decision="escalate",
            confidence="high",
            metadata={
                "escalation_reason": red_line_check["trigger"],
                "processing_time_ms": int((time.time() - start_time) * 1000),
            },
        )

    # Step 2: Classify message
    classification = await classify_message(request.message)

    # Step 3: Generate response with Support Agent
    try:
        agent = create_support_agent(classification.primary)
        response = await agent.arun(request.message)
        ai_response = str(response.content)
    except Exception as e:
        logger.error("support_agent_error", error=str(e), category=classification.primary)
        return ChatResponse(
            response=(
                "I apologize, but I'm having trouble processing your request. "
                "Let me connect you with a support agent."
            ),
            session_id=session_id,
            category=classification.primary,
            decision="escalate",
            confidence="low",
            metadata={"error": str(e)},
        )

    # Step 4: Post-processing safety check
    safety_check = check_subscription_safety(ai_response)
    decision = "draft" if not safety_check["is_safe"] else "send"

    if not safety_check["is_safe"]:
        logger.warning(
            "subscription_safety_violation",
            session_id=session_id,
            violation=safety_check["violation"],
        )

    processing_time_ms = int((time.time() - start_time) * 1000)

    # Step 5: Save to database (best effort)
    config = CATEGORY_CONFIG[classification.primary]
    try:
        save_session({
            "session_id": session_id,
            "conversation_id": request.conversation_id,
            "channel": (request.metadata or {}).get("channel", "widget"),
            "customer_email": request.contact.email if request.contact else classification.email,
            "customer_name": request.contact.name if request.contact else None,
            "primary_category": classification.primary,
            "secondary_category": classification.secondary,
            "urgency": classification.urgency,
            "status": "active",
            "eval_decision": decision,
            "first_response_time_ms": processing_time_ms,
        })
        save_message({
            "session_id": session_id,
            "role": "user",
            "content": request.message,
            "model_used": None,
            "reasoning_effort": None,
            "processing_time_ms": None,
        })
        save_message({
            "session_id": session_id,
            "role": "assistant",
            "content": ai_response,
            "model_used": config.model,
            "reasoning_effort": config.reasoning_effort,
            "processing_time_ms": processing_time_ms,
        })
    except Exception as e:
        logger.error("database_save_error", session_id=session_id, error=str(e))

    return ChatResponse(
        response=ai_response,
        session_id=session_id,
        category=classification.primary,
        decision=decision,
        confidence="high",
        metadata={
            "model_used": config.model,
            "reasoning_effort": config.reasoning_effort,
            "processing_time_ms": processing_time_ms,
            "is_outstanding": False,
            "secondary_category": classification.secondary,
        },
    )
