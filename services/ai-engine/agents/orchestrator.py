"""Support Orchestrator — clean pipeline stages.

Extracts the monolithic chat() logic into a structured pipeline:

1. Safety check (pre-processing red lines)
2. Classification (router agent + name extraction, parallel)
3. Context building (history + email)
4. Agent execution + Outstanding detection (parallel)
5. Post-processing (cancel link, response assembly)
6. Evaluation (eval gate OR QA agent in team mode)
7. Persistence (save to DB, best-effort)

Team mode: specialist agents replace the generic support agent,
and the QA agent replaces eval gate with retry capability.

Each stage is a method, making the flow testable and extensible.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field

import structlog

from agents.config import CATEGORY_CONFIG
from agents.eval_gate import evaluate_response
from agents.name_extractor import extract_customer_name
from agents.outstanding import detect_outstanding
from agents.qa_agent import qa_evaluate
from agents.response_assembler import assemble_response
from agents.router import RouterOutput, classify_message
from agents.specialists import CATEGORY_TO_SPECIALIST, create_specialist_agent
from agents.support import create_support_agent
from config import settings
from database.queries import (
    get_conversation_history,
    save_eval_result,
    save_message,
    save_session,
    update_session_outstanding,
)
from guardrails.safety import check_red_lines
from tools.retention import generate_cancel_link, inject_cancel_link

logger = structlog.get_logger()


@dataclass
class PipelineContext:
    """Mutable context passed through all pipeline stages."""

    # Input
    message: str
    session_id: str
    conversation_id: str | None = None
    contact_email: str | None = None
    contact_name: str | None = None
    channel: str = "widget"
    metadata: dict = field(default_factory=dict)

    # Stage 1: Safety
    is_flagged: bool = False
    flag_trigger: str | None = None

    # Stage 2: Classification
    classification: RouterOutput | None = None
    customer_name: str = "Valued Customer"

    # Stage 3: Context
    customer_email: str | None = None
    agent_input: str = ""

    # Stage 4: Agent + Outstanding
    ai_response: str = ""
    outstanding_is_outstanding: bool = False
    outstanding_trigger: str | None = None

    # Stage 6: Evaluation
    decision: str = "send"
    confidence: str = "high"
    eval_checks: list = field(default_factory=list)
    override_reason: str | None = None

    # Team mode
    use_team_mode: bool = False
    specialist_key: str | None = None
    attempt: int = 1
    qa_feedback: str | None = None

    # Timing
    start_time: float = field(default_factory=time.time)
    processing_time_ms: int = 0


@dataclass
class PipelineResult:
    """Immutable result returned from the orchestrator."""

    response: str
    session_id: str
    category: str
    decision: str
    confidence: str
    actions_taken: list = field(default_factory=list)
    actions_pending: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SupportOrchestrator:
    """Orchestrates the 7-stage support pipeline.

    Usage:
        result = await SupportOrchestrator.process(
            message="Where is my package?",
            session_id="sess_abc123",
            contact_email="user@example.com",
        )
    """

    @staticmethod
    async def process(
        message: str,
        session_id: str | None = None,
        conversation_id: str | None = None,
        contact_email: str | None = None,
        contact_name: str | None = None,
        channel: str = "widget",
        metadata: dict | None = None,
        use_team_mode: bool | None = None,
    ) -> PipelineResult:
        """Run the full support pipeline.

        Args:
            message: Customer message text.
            session_id: Stable session identifier.
            conversation_id: External conversation ID (e.g. Chatwoot).
            contact_email: Customer email from contact info.
            contact_name: Customer name from contact info.
            channel: Communication channel (widget, email, etc.).
            metadata: Additional metadata.
            use_team_mode: If True, use specialist agents + QA agent.
                If None, reads from settings.team_mode_enabled.

        Returns:
            PipelineResult with response, category, decision, etc.
        """
        ctx = PipelineContext(
            message=message,
            session_id=session_id or f"sess_{uuid.uuid4().hex[:12]}",
            conversation_id=conversation_id,
            contact_email=contact_email,
            contact_name=contact_name,
            channel=channel,
            metadata=metadata or {},
            use_team_mode=use_team_mode if use_team_mode is not None else settings.team_mode_enabled,
        )

        logger.info(
            "pipeline_start",
            session_id=ctx.session_id,
            team_mode=ctx.use_team_mode,
        )

        # Stage 1: Safety
        result = SupportOrchestrator._check_safety(ctx)
        if result:
            return result

        # Stage 2: Classification + Name (parallel)
        await SupportOrchestrator._classify(ctx)

        # Resolve specialist key for team mode
        if ctx.use_team_mode:
            ctx.specialist_key = CATEGORY_TO_SPECIALIST.get(ctx.classification.primary)

        # Stage 3: Build context
        SupportOrchestrator._build_context(ctx)

        # Stage 4: Agent + Outstanding (parallel)
        result = await SupportOrchestrator._run_agent(ctx)
        if result:
            return result

        # Stage 5: Post-processing
        SupportOrchestrator._post_process(ctx)

        # Stage 6: Evaluation (with retry loop in team mode)
        await SupportOrchestrator._evaluate(ctx)

        # Team mode retry: if QA says "refine", re-run agent with feedback
        if ctx.use_team_mode and ctx.decision == "refine" and ctx.attempt == 1:
            logger.info(
                "qa_retry_triggered",
                session_id=ctx.session_id,
                feedback=ctx.qa_feedback,
            )
            ctx.attempt = 2
            # Append QA feedback to agent input
            ctx.agent_input = (
                f"{ctx.agent_input}\n\n"
                f"[QA FEEDBACK — please revise your response]\n"
                f"{ctx.qa_feedback}\n"
                f"[End QA Feedback]"
            )
            # Re-run stages 4-6
            result = await SupportOrchestrator._run_agent(ctx)
            if result:
                return result
            SupportOrchestrator._post_process(ctx)
            await SupportOrchestrator._evaluate(ctx)

        # Finalize timing
        ctx.processing_time_ms = int((time.time() - ctx.start_time) * 1000)

        # Stage 7: Persistence (best-effort)
        SupportOrchestrator._persist(ctx)

        return SupportOrchestrator._build_result(ctx)

    @staticmethod
    def _check_safety(ctx: PipelineContext) -> PipelineResult | None:
        """Stage 1: Red line safety check. Returns early result if flagged."""
        red_line_check = check_red_lines(ctx.message)
        if red_line_check["is_flagged"]:
            ctx.is_flagged = True
            ctx.flag_trigger = red_line_check["trigger"]
            logger.warning(
                "red_line_triggered",
                session_id=ctx.session_id,
                trigger=ctx.flag_trigger,
            )
            return PipelineResult(
                response="I'm connecting you with a support agent who can better assist you.",
                session_id=ctx.session_id,
                category="unknown",
                decision="escalate",
                confidence="high",
                metadata={
                    "escalation_reason": ctx.flag_trigger,
                    "processing_time_ms": int((time.time() - ctx.start_time) * 1000),
                },
            )
        return None

    @staticmethod
    async def _classify(ctx: PipelineContext) -> None:
        """Stage 2: Classification + Name extraction (parallel)."""
        ctx.classification, ctx.customer_name = await asyncio.gather(
            classify_message(ctx.message),
            extract_customer_name(ctx.message, ctx.contact_name),
        )

    @staticmethod
    def _build_context(ctx: PipelineContext) -> None:
        """Stage 3: Build agent input with history and metadata."""
        ctx.customer_email = ctx.contact_email or ctx.classification.email

        parts = [f"[Customer Name: {ctx.customer_name}]"]
        if ctx.customer_email:
            parts.append(f"[Customer Email: {ctx.customer_email}]")

        # Load conversation history
        history = get_conversation_history(ctx.session_id)
        if history:
            parts.append("")
            parts.append("[Conversation History]")
            for msg in history:
                role = "Customer" if msg["role"] == "user" else "Agent"
                content = msg["content"]
                if role == "Agent" and len(content) > 500:
                    content = content[:500] + "..."
                parts.append(f"{role}: {content}")
            parts.append("[End History]")

        parts.append("")
        parts.append(ctx.message)
        ctx.agent_input = "\n".join(parts)

    @staticmethod
    async def _run_agent(ctx: PipelineContext) -> PipelineResult | None:
        """Stage 4: Support Agent + Outstanding Detection (parallel).

        In team mode, uses specialist agents instead of the generic support agent.
        Returns early PipelineResult if agent fails (escalation).
        """
        async def _support():
            if ctx.use_team_mode:
                agent = await create_specialist_agent(
                    ctx.classification.primary,
                    customer_email=ctx.customer_email,
                )
            else:
                agent = await create_support_agent(
                    ctx.classification.primary,
                    customer_email=ctx.customer_email,
                )
            response = await agent.arun(ctx.agent_input)
            return str(response.content)

        try:
            ctx.ai_response, outstanding_result = await asyncio.gather(
                _support(),
                detect_outstanding(ctx.message, ctx.classification.primary),
            )
            ctx.outstanding_is_outstanding = outstanding_result.is_outstanding
            ctx.outstanding_trigger = outstanding_result.trigger
        except Exception as e:
            logger.error(
                "support_agent_error",
                error=str(e),
                category=ctx.classification.primary,
            )
            return PipelineResult(
                response=(
                    "I apologize, but I'm having trouble processing your request. "
                    "Let me connect you with a support agent."
                ),
                session_id=ctx.session_id,
                category=ctx.classification.primary,
                decision="escalate",
                confidence="low",
                metadata={"error": str(e)},
            )
        return None

    @staticmethod
    def _post_process(ctx: PipelineContext) -> None:
        """Stage 5: Cancel link injection + Response assembly."""
        is_retention = ctx.classification.primary in (
            "retention_primary_request",
            "retention_repeated_request",
        )
        if is_retention and ctx.customer_email:
            cancel_url = generate_cancel_link(
                subscription_id="pending",
                customer_email=ctx.customer_email,
            )
            if cancel_url:
                ctx.ai_response = inject_cancel_link(ctx.ai_response, cancel_url)

        ctx.ai_response = assemble_response(
            raw_response=ctx.ai_response,
            customer_name=ctx.customer_name,
            category=ctx.classification.primary,
            session_id=ctx.session_id,
        )

    @staticmethod
    async def _evaluate(ctx: PipelineContext) -> None:
        """Stage 6: Eval Gate or QA Agent evaluation.

        In team mode, uses the QA Agent with refine/retry capability.
        In standard mode, uses the existing eval gate.
        """
        config = CATEGORY_CONFIG[ctx.classification.primary]

        if ctx.use_team_mode:
            # QA Agent evaluation (team mode)
            qa_result = await qa_evaluate(
                customer_message=ctx.message,
                ai_response=ctx.ai_response,
                category=ctx.classification.primary,
                is_outstanding=ctx.outstanding_is_outstanding,
                tools_available=config.tools or None,
                attempt=ctx.attempt,
                previous_feedback=ctx.qa_feedback,
            )
            ctx.decision = qa_result.decision
            ctx.confidence = qa_result.confidence
            ctx.eval_checks = [c.model_dump() for c in qa_result.checks]
            ctx.override_reason = qa_result.override_reason
            ctx.qa_feedback = qa_result.feedback
        else:
            # Standard eval gate
            eval_result = await evaluate_response(
                customer_message=ctx.message,
                ai_response=ctx.ai_response,
                category=ctx.classification.primary,
                is_outstanding=ctx.outstanding_is_outstanding,
                tools_available=config.tools or None,
            )
            ctx.decision = eval_result.decision
            ctx.confidence = eval_result.confidence
            ctx.eval_checks = [c.model_dump() for c in eval_result.checks]
            ctx.override_reason = eval_result.override_reason

        if ctx.decision not in ("send", "refine"):
            logger.warning(
                "evaluation_not_send",
                session_id=ctx.session_id,
                decision=ctx.decision,
                confidence=ctx.confidence,
                override_reason=ctx.override_reason,
                team_mode=ctx.use_team_mode,
                attempt=ctx.attempt,
            )

    @staticmethod
    def _persist(ctx: PipelineContext) -> None:
        """Stage 7: Save session, messages, eval to DB (best-effort)."""
        config = CATEGORY_CONFIG[ctx.classification.primary]
        try:
            save_session({
                "session_id": ctx.session_id,
                "conversation_id": ctx.conversation_id,
                "channel": ctx.channel,
                "customer_email": ctx.customer_email,
                "customer_name": ctx.customer_name,
                "primary_category": ctx.classification.primary,
                "secondary_category": ctx.classification.secondary,
                "urgency": ctx.classification.urgency,
                "status": "active",
                "eval_decision": ctx.decision,
                "first_response_time_ms": ctx.processing_time_ms,
            })
            update_session_outstanding(
                session_id=ctx.session_id,
                is_outstanding=ctx.outstanding_is_outstanding,
                outstanding_trigger=ctx.outstanding_trigger,
                eval_decision=ctx.decision,
            )
            save_message({
                "session_id": ctx.session_id,
                "role": "user",
                "content": ctx.message,
                "model_used": None,
                "reasoning_effort": None,
                "processing_time_ms": None,
            })
            save_message({
                "session_id": ctx.session_id,
                "role": "assistant",
                "content": ctx.ai_response,
                "model_used": config.model,
                "reasoning_effort": config.reasoning_effort,
                "processing_time_ms": ctx.processing_time_ms,
            })
            save_eval_result({
                "ticket_id": ctx.session_id,
                "request_subtype": ctx.classification.primary,
                "request_sub_subtype": ctx.classification.secondary,
                "decision": ctx.decision,
                "draft_reason": ctx.override_reason,
                "confidence": ctx.confidence,
                "checks": ctx.eval_checks,
                "is_outstanding": ctx.outstanding_is_outstanding,
                "outstanding_trigger": ctx.outstanding_trigger,
                "auto_send_enabled": config.auto_send_phase <= 1,
            })
        except Exception as e:
            logger.error("database_save_error", session_id=ctx.session_id, error=str(e))

    @staticmethod
    def _build_result(ctx: PipelineContext) -> PipelineResult:
        """Build the final PipelineResult from context."""
        config = CATEGORY_CONFIG[ctx.classification.primary]
        meta = {
            "model_used": config.model,
            "reasoning_effort": config.reasoning_effort,
            "processing_time_ms": ctx.processing_time_ms,
            "is_outstanding": ctx.outstanding_is_outstanding,
            "outstanding_trigger": ctx.outstanding_trigger,
            "secondary_category": ctx.classification.secondary,
            "customer_name": ctx.customer_name,
            "eval_checks": ctx.eval_checks,
        }
        if ctx.use_team_mode:
            meta["team_mode"] = True
            meta["specialist"] = ctx.specialist_key
            meta["attempts"] = ctx.attempt
        return PipelineResult(
            response=ctx.ai_response,
            session_id=ctx.session_id,
            category=ctx.classification.primary,
            decision=ctx.decision,
            confidence=ctx.confidence,
            metadata=meta,
        )
