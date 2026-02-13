"""FastAPI routes for the AI Engine.

POST /api/chat            — main pipeline: safety → classify+name → support+outstanding
                            → cancel link → assemble → eval gate → save → respond.
POST /api/webhook/chatwoot — Chatwoot webhook bridge: parse → chat() → dispatch back.
GET  /api/health           — service health check.
"""

import asyncio
import time
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
import structlog

from config import settings
from agents.config import CATEGORY_CONFIG
from agents.router import classify_message
from agents.name_extractor import extract_customer_name
from agents.support import create_support_agent
from agents.response_assembler import assemble_response
from agents.outstanding import detect_outstanding
from agents.eval_gate import evaluate_response
from guardrails.safety import check_red_lines
from tools.retention import generate_cancel_link, inject_cancel_link
from database.queries import save_session, save_message, save_eval_result, update_session_outstanding

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
        from database.connection import get_client

        get_client().table("ai_answerer_instructions").select("id").limit(1).execute()
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

    Pipeline: red line → classify+name (parallel) → support+outstanding (parallel)
              → cancel link → assemble → eval gate → save → respond.
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

    # Step 2: Classify message + extract customer name (parallel)
    contact_name = request.contact.name if request.contact else None
    classification, customer_name = await asyncio.gather(
        classify_message(request.message),
        extract_customer_name(request.message, contact_name),
    )

    # Step 3: Support Agent + Outstanding Detection (parallel)
    agent_input = f"[Customer Name: {customer_name}]\n\n{request.message}"

    async def _run_support_agent() -> str:
        agent = create_support_agent(classification.primary)
        response = await agent.arun(agent_input)
        return str(response.content)

    try:
        ai_response, outstanding_result = await asyncio.gather(
            _run_support_agent(),
            detect_outstanding(request.message, classification.primary),
        )
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

    # Step 4: Cancel link injection (retention categories only)
    is_retention = classification.primary in (
        "retention_primary_request",
        "retention_repeated_request",
    )
    if is_retention:
        customer_email = (
            request.contact.email if request.contact else classification.email
        )
        if customer_email:
            cancel_url = generate_cancel_link(
                subscription_id="pending",
                customer_email=customer_email,
            )
            if cancel_url:
                ai_response = inject_cancel_link(ai_response, cancel_url)

    # Step 5: Assemble response (greeting + opener + body + closer + sign-off)
    ai_response = assemble_response(
        raw_response=ai_response,
        customer_name=customer_name,
        category=classification.primary,
        session_id=session_id,
    )

    # Step 6: Eval Gate (replaces check_subscription_safety)
    eval_result = await evaluate_response(
        customer_message=request.message,
        ai_response=ai_response,
        category=classification.primary,
        is_outstanding=outstanding_result.is_outstanding,
    )

    decision = eval_result.decision
    confidence = eval_result.confidence

    if decision != "send":
        logger.warning(
            "eval_gate_not_send",
            session_id=session_id,
            decision=decision,
            confidence=confidence,
            override_reason=eval_result.override_reason,
        )

    processing_time_ms = int((time.time() - start_time) * 1000)

    # Step 7: Save to database (best effort)
    config = CATEGORY_CONFIG[classification.primary]
    try:
        save_session({
            "session_id": session_id,
            "conversation_id": request.conversation_id,
            "channel": (request.metadata or {}).get("channel", "widget"),
            "customer_email": request.contact.email if request.contact else classification.email,
            "customer_name": customer_name,
            "primary_category": classification.primary,
            "secondary_category": classification.secondary,
            "urgency": classification.urgency,
            "status": "active",
            "eval_decision": decision,
            "first_response_time_ms": processing_time_ms,
        })
        update_session_outstanding(
            session_id=session_id,
            is_outstanding=outstanding_result.is_outstanding,
            outstanding_trigger=outstanding_result.trigger,
            eval_decision=decision,
        )
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
        save_eval_result({
            "ticket_id": session_id,
            "request_subtype": classification.primary,
            "request_sub_subtype": classification.secondary,
            "decision": decision,
            "draft_reason": eval_result.override_reason,
            "confidence": confidence,
            "checks": [c.model_dump() for c in eval_result.checks],
            "is_outstanding": outstanding_result.is_outstanding,
            "outstanding_trigger": outstanding_result.trigger,
            "auto_send_enabled": config.auto_send_phase <= 1,
        })
    except Exception as e:
        logger.error("database_save_error", session_id=session_id, error=str(e))

    return ChatResponse(
        response=ai_response,
        session_id=session_id,
        category=classification.primary,
        decision=decision,
        confidence=confidence,
        metadata={
            "model_used": config.model,
            "reasoning_effort": config.reasoning_effort,
            "processing_time_ms": processing_time_ms,
            "is_outstanding": outstanding_result.is_outstanding,
            "outstanding_trigger": outstanding_result.trigger,
            "secondary_category": classification.secondary,
            "customer_name": customer_name,
            "eval_checks": [c.model_dump() for c in eval_result.checks],
        },
    )


# --- Chatwoot Webhook ---


# Idempotency: track recently processed message IDs (TTL 5 min)
_processed_messages: dict[int, float] = {}
_DEDUP_TTL_SECONDS = 300


def _is_duplicate(message_id: int) -> bool:
    """Check if message was already processed. Prunes stale entries."""
    now = time.time()
    stale = [k for k, v in _processed_messages.items() if now - v > _DEDUP_TTL_SECONDS]
    for k in stale:
        del _processed_messages[k]
    if message_id in _processed_messages:
        return True
    _processed_messages[message_id] = now
    return False


class ChatwootSender(BaseModel):
    id: int | None = None
    name: str | None = None
    email: str | None = None
    type: str | None = None


class ChatwootConversation(BaseModel):
    id: int
    inbox_id: int | None = None
    status: str | None = None


class ChatwootWebhookPayload(BaseModel):
    event: str
    id: int | None = None
    content: str | None = None
    message_type: str | None = None
    private: bool = False
    sender: ChatwootSender | None = None
    conversation: ChatwootConversation | None = None
    account: dict | None = None


@router.post("/webhook/chatwoot")
async def chatwoot_webhook(payload: ChatwootWebhookPayload):
    """Handle incoming Chatwoot webhook events.

    Only processes message_created events with incoming message_type.
    Dispatches AI response back to Chatwoot based on eval gate decision.
    """
    if payload.event != "message_created":
        return {"status": "ignored", "reason": f"event={payload.event}"}

    if payload.message_type != "incoming":
        return {"status": "ignored", "reason": "not incoming message"}

    if not payload.content or not payload.content.strip():
        return {"status": "ignored", "reason": "empty content"}

    if payload.private:
        return {"status": "ignored", "reason": "private note"}

    if payload.id and _is_duplicate(payload.id):
        logger.info("chatwoot_duplicate_webhook", message_id=payload.id)
        return {"status": "duplicate", "message_id": payload.id}

    conversation_id = payload.conversation.id if payload.conversation else None
    if not conversation_id:
        return {"status": "error", "reason": "no conversation_id"}

    contact_email = payload.sender.email if payload.sender else None
    contact_name = payload.sender.name if payload.sender else None

    chat_request = ChatRequest(
        message=payload.content,
        conversation_id=str(conversation_id),
        contact=ContactInfo(email=contact_email, name=contact_name)
        if (contact_email or contact_name)
        else None,
        metadata={"channel": "chatwoot", "chatwoot_message_id": payload.id},
    )

    logger.info(
        "chatwoot_webhook_processing",
        conversation_id=conversation_id,
        message_id=payload.id,
    )

    try:
        result = await chat(chat_request)
    except Exception as e:
        logger.error(
            "chatwoot_pipeline_error",
            error=str(e),
            conversation_id=conversation_id,
        )
        await _handle_pipeline_error(conversation_id, str(e))
        return {"status": "error", "reason": str(e)}

    await _dispatch_to_chatwoot(conversation_id, result)
    return {"status": "processed", "decision": result.decision}


async def _dispatch_to_chatwoot(conversation_id: int, result: ChatResponse) -> None:
    """Send AI response to Chatwoot based on eval gate decision."""
    from chatwoot.client import send_message, toggle_conversation_status, add_labels

    try:
        if result.decision == "send":
            await send_message(conversation_id, result.response, private=False)

        elif result.decision == "draft":
            draft_note = (
                f"**AI Draft (needs review)**\n\n"
                f"Category: {result.category}\n"
                f"Confidence: {result.confidence}\n\n"
                f"---\n\n{result.response}"
            )
            await send_message(conversation_id, draft_note, private=True)
            await toggle_conversation_status(conversation_id, "open")
            await add_labels(conversation_id, ["ai_draft", result.category])

        elif result.decision == "escalate":
            escalation_note = (
                f"**AI Escalation**\n\n"
                f"Category: {result.category}\n"
                f"Reason: {result.metadata.get('escalation_reason', 'eval_gate')}\n\n"
                f"---\n\nAI draft:\n{result.response}"
            )
            await send_message(conversation_id, escalation_note, private=True)
            await toggle_conversation_status(conversation_id, "open")
            await add_labels(
                conversation_id,
                ["ai_escalation", result.category, "high_priority"],
            )

    except Exception as e:
        logger.error(
            "chatwoot_dispatch_error",
            conversation_id=conversation_id,
            decision=result.decision,
            error=str(e),
        )


async def _handle_pipeline_error(conversation_id: int, error: str) -> None:
    """Handle AI pipeline failure: notify agents via Chatwoot."""
    from chatwoot.client import send_message, toggle_conversation_status, add_labels

    try:
        await send_message(
            conversation_id,
            f"**AI Error:** Pipeline failed: {error}\nPlease handle manually.",
            private=True,
        )
        await toggle_conversation_status(conversation_id, "open")
        await add_labels(conversation_id, ["ai_error"])
    except Exception as e:
        logger.error("chatwoot_error_handler_failed", error=str(e))
