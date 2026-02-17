"""FastAPI routes for the AI Engine.

POST /api/chat            — delegates to SupportOrchestrator 7-stage pipeline.
POST /api/webhook/chatwoot — Chatwoot webhook bridge: parse → chat() → dispatch back.
GET  /api/health           — service health check.
"""

import re
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field
import structlog

from config import settings
from agents.orchestrator import SupportOrchestrator
from chatwoot.client import (
    send_message,
    toggle_conversation_status,
    add_labels,
    assign_conversation,
)

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

    Delegates to SupportOrchestrator which runs the 7-stage pipeline:
    safety → classify+name → context → agent+outstanding → post-process → eval → persist.
    """
    contact_email = request.contact.email if request.contact else None
    contact_name = request.contact.name if request.contact else None
    channel = (request.metadata or {}).get("channel", "widget")

    result = await SupportOrchestrator.process(
        message=request.message,
        session_id=request.session_id,
        conversation_id=request.conversation_id,
        contact_email=contact_email,
        contact_name=contact_name,
        channel=channel,
        metadata=request.metadata,
    )

    return ChatResponse(
        response=result.response,
        session_id=result.session_id,
        category=result.category,
        decision=result.decision,
        confidence=result.confidence,
        actions_taken=result.actions_taken,
        actions_pending=result.actions_pending,
        metadata=result.metadata,
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
    channel: str | None = None


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
    # Handle message edits (human corrections of AI responses)
    if payload.event == "message_updated":
        await _handle_message_edit(payload)
        return {"status": "processed", "event": "message_updated"}

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

    # Detect channel from Chatwoot conversation metadata
    channel = payload.conversation.channel if payload.conversation else "web"

    chat_request = ChatRequest(
        message=payload.content,
        session_id=f"cw_{conversation_id}",
        conversation_id=str(conversation_id),
        contact=ContactInfo(email=contact_email, name=contact_name)
        if (contact_email or contact_name)
        else None,
        metadata={"channel": channel, "chatwoot_message_id": payload.id},
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

    await _dispatch_to_chatwoot(conversation_id, result, channel=channel)
    return {"status": "processed", "decision": result.decision}


def _strip_html(text: str) -> str:
    """Strip HTML tags and convert to plain text for chat display."""
    text = re.sub(r"<br\s*/?>|</div>|</p>|</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def _dispatch_to_chatwoot(
    conversation_id: int,
    result: ChatResponse,
    channel: str = "web",
) -> None:
    """Send AI response to Chatwoot based on eval gate decision."""
    # Email supports HTML natively; chat widget needs plain text
    if channel == "email":
        clean_response = result.response
    else:
        clean_response = _strip_html(result.response)

    try:
        if result.decision == "send":
            await send_message(conversation_id, clean_response, private=False)

        elif result.decision == "draft":
            draft_note = (
                f"**AI Draft (needs review)**\n\n"
                f"Category: {result.category}\n"
                f"Confidence: {result.confidence}\n\n"
                f"---\n\n{clean_response}"
            )
            await send_message(conversation_id, draft_note, private=True)
            await toggle_conversation_status(conversation_id, "open")
            await add_labels(conversation_id, ["ai_draft", result.category])

        elif result.decision == "escalate":
            escalation_note = (
                f"**AI Escalation**\n\n"
                f"Category: {result.category}\n"
                f"Reason: {result.metadata.get('escalation_reason', 'eval_gate')}\n\n"
                f"---\n\nAI draft:\n{clean_response}"
            )
            await send_message(conversation_id, escalation_note, private=True)
            await toggle_conversation_status(conversation_id, "open")
            await add_labels(
                conversation_id,
                ["ai_escalation", result.category, "high_priority"],
            )
            # Assign to human agent if configured
            if settings.chatwoot_escalation_assignee_id:
                await assign_conversation(
                    conversation_id, settings.chatwoot_escalation_assignee_id
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


async def _handle_message_edit(payload: ChatwootWebhookPayload) -> None:
    """Detect and record human corrections of AI messages.

    When a human agent edits a bot message in Chatwoot, this captures the
    correction for the learning pipeline (Track 2).
    """
    if not settings.learning_few_shot_enabled:
        return

    # Only process outgoing messages (AI-generated) that were edited
    if payload.message_type != "outgoing":
        return

    content_after = payload.content
    if not content_after or not content_after.strip():
        return

    conversation_id = str(payload.conversation.id) if payload.conversation else None
    if not conversation_id:
        return

    session_id = f"cw_{conversation_id}"

    try:
        from database.queries import get_last_ai_message, get_session_category

        original = get_last_ai_message(session_id)
        if not original or original == content_after:
            return

        category = get_session_category(session_id) or "unknown"

        from learning.feedback import (
            CorrectionRecord,
            classify_correction,
            save_correction,
        )

        classification = await classify_correction(original, content_after)

        save_correction(CorrectionRecord(
            conversation_id=conversation_id,
            session_id=session_id,
            category=category,
            ai_response=original,
            human_edit=content_after,
            correction_type=classification.correction_type,
            specific_issue=classification.specific_issue,
            key_changes=classification.key_changes,
        ))

        logger.info(
            "correction_captured",
            conversation_id=conversation_id,
            category=category,
            correction_type=classification.correction_type,
        )

    except Exception as e:
        logger.error(
            "handle_message_edit_failed",
            conversation_id=conversation_id,
            error=str(e),
        )
