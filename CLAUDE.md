# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered live chat platform for Lev Haolam customer support. Replaces email-only pipeline (n8n + Zoho) with real-time multi-channel chat using AI agents that classify, respond, and execute actions autonomously.

**Stack:** Agno AgentOS (Python 3.12) + Chatwoot (Omnichannel) + Langfuse (Observability & Eval) + PostgreSQL (Supabase) + Pinecone + Docker Compose

**Current Phase:** Phase 0 (Foundation — AI Engine core). Core source code implemented.

## Commands

```bash
# Development (hot reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up ai-engine

# Production
docker compose up -d

# Logs
docker compose logs -f ai-engine

# Run all tests
docker compose exec ai-engine pytest tests/

# Run a single test
docker compose exec ai-engine pytest tests/test_router.py -v

# Run database migrations
docker compose exec ai-engine python -m shared.database.migrate

# Health check
curl http://localhost:8000/api/health

# Langfuse UI (observability + eval)
open http://localhost:3100
```

## Architecture

### Two-Layer Agent System

```
Customer Message
       │
       ▼
┌─────────────────┐
│  Router Agent    │  GPT-5.1, no reasoning, ~50ms
│  (classify)      │  Output: { primary, secondary, urgency, email }
└────────┬────────┘
         │ category
         ▼
┌─────────────────┐
│  Support Agent   │  Dynamic factory: model/tools/knowledge per category
│  (respond+act)   │  CATEGORY_CONFIG drives everything
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Outstanding     │  Detects red flags via rules + Pinecone similarity
│  Detection       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Eval Gate       │  Decides: send / draft / escalate
│                  │  Checks: safety, tone, accuracy, confidence
└─────────────────┘
```

The Support Agent is not 10 separate agents — it's a single factory function (`create_support_agent(category)`) that dynamically configures model, reasoning effort, tools, Pinecone namespace, and instructions based on `CATEGORY_CONFIG`.

### Service Architecture

| Service | Port | Phase | Technology |
|---------|------|-------|------------|
| AI Engine | 8000 | 0 | Agno AgentOS + FastAPI |
| Langfuse | 3100 | 0 | Observability, tracing, eval, playground |
| Chatwoot | 3000 | 2 | Omnichannel hub |
| n8n | 5678 | existing | Email pipeline (continues in parallel) |

### Model Selection per Category

- **GPT-5.1** (none/low reasoning): shipping, payment, frequency, skip/pause, address, customization, damage, gratitude — ~80% of requests
- **Claude Sonnet 4.5** (extended reasoning): retention_primary, retention_repeated — complex persuasion cases

This split saves ~60-70% cost vs using one model for everything.

### Database: Dual Pipeline

Both the existing n8n email pipeline and the new Agno chat platform:
- **Read** prompts from `ai_answerer_instructions` (instruction_1..10, outstanding_rules, outstanding_hard_rules)
- **Write** eval results to `eval_results`

The new system adds 5 tables (`chat_sessions`, `chat_messages`, `agent_traces`, `tool_executions`, `learning_records`) and does NOT write to `support_threads_data` or `support_dialogs` (email-only).

Connection is via **supabase-py** (REST API) using `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.

### Pinecone Namespaces

Index: `support-examples`. Namespaces: `outstanding-cases`, `faq`, `retention`, `shipping`, `damage`, `subscription`, `customization`, `payment`, `gratitude`.

## Critical Safety Rules (NEVER VIOLATE)

1. **AI NEVER confirms subscription cancellation** — always redirect to self-service cancel page
2. **AI NEVER confirms pause directly** — redirect or HITL confirmation
3. **Death threats, bank disputes** — immediate escalation to human
4. **Unknown category** — draft (not auto-send)
5. **Low confidence** — draft
6. **Refunds** — NEVER without human approval
7. **Sensitive data** — never in logs

## Coding Conventions

- **Python 3.12**, type hints everywhere
- **Pydantic** for all data models (input/output)
- **Async** for FastAPI routes, **sync** for database queries (supabase-py)
- **structlog** with JSON output for logging
- **pydantic-settings** for env var config
- Custom exceptions; never bare `except:`
- Google-style docstrings

### Agno Patterns (verified against SDK 2.4.8)

```python
# Agent creation — use OpenAIChat for no-reasoning, Claude for retention
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

# Knowledge via PineconeDb (NOT "PineconeKnowledge" — that class doesn't exist)
vector_db = PineconeDb(
    name="support-examples",
    dimension=1536,
    metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
    api_key=settings.pinecone_api_key,
    namespace="shipping",  # per-category namespace
    use_hybrid_search=True,
)
knowledge = Knowledge(vector_db=vector_db)

agent = Agent(
    name="support_shipping",
    model=OpenAIChat(id="gpt-5.1"),
    instructions=["...loaded from DB..."],
    knowledge=knowledge,
    search_knowledge=True,
)

# Structured output — use output_schema parameter (NOT response_model)
from pydantic import BaseModel
class RouterOutput(BaseModel):
    primary: str
    urgency: str

agent = Agent(model=OpenAIChat(id="gpt-5.1"), output_schema=RouterOutput)

# Tool with HITL approval (Phase 2+)
from agno.tools import tool

@tool(requires_confirmation=True)  # NOT needs_approval
def pause_subscription(subscription_id: str) -> str:
    """Pause customer subscription. Requires customer confirmation."""
    ...
```

### Custom Guardrails

Agno doesn't have a generic custom guardrail base class. Safety checks are implemented as pre/post-processing functions called explicitly in the pipeline (see `guardrails/safety.py`).

## Environment Variables

Required in `.env` (see `.env.example`):
```
OPENAI_API_KEY              # GPT-5.1
ANTHROPIC_API_KEY           # Claude Sonnet 4.5 (retention only, optional for now)
SUPABASE_URL                # Supabase project URL
SUPABASE_SERVICE_ROLE_KEY   # Supabase service role key (bypasses RLS)
PINECONE_API_KEY            # Vector store
PINECONE_INDEX=support-examples
LANGFUSE_PUBLIC_KEY         # Langfuse (auto-created on first boot)
LANGFUSE_SECRET_KEY         # Langfuse
LANGFUSE_HOST               # http://langfuse-web:3000
CANCEL_LINK_PASSWORD        # AES-256-GCM for cancel link encryption
```

Phase 2+ adds: `CHATWOOT_URL`, `CHATWOOT_API_TOKEN`, `CHATWOOT_ACCOUNT_ID`, `N8N_URL`, `N8N_API_KEY`

### Observability: Langfuse (self-hosted)

Langfuse replaces both Agno Control Plane (paid SaaS) and Agenta (eval lab). Self-hosted via Docker Compose (6 services: web, worker, postgres, clickhouse, redis, minio). All agent calls are automatically traced via `AgnoInstrumentor` + OpenTelemetry.

UI: `http://localhost:3100` — tracing, playground, evaluations, prompt management, cost tracking.

## Phase 0 File Creation Order

Create files strictly in this order (each step: create → verify imports → ensure Docker builds):

1. `.env.example` + `.gitignore`
2. `docker-compose.yml` + `docker-compose.dev.yml`
3. `services/ai-engine/requirements.txt`
4. `services/ai-engine/Dockerfile`
5. `services/ai-engine/config.py`
6. `services/ai-engine/database/connection.py`
7. `services/ai-engine/database/queries.py`
8. `services/ai-engine/knowledge/pinecone_client.py`
9. `services/ai-engine/guardrails/safety.py`
10. `services/ai-engine/agents/router.py`
11. `services/ai-engine/agents/config.py`
12. `services/ai-engine/agents/support.py`
13. `services/ai-engine/agents/instructions.py`
14. `services/ai-engine/main.py`
15. `services/ai-engine/api/routes.py`

## Reference Documents

- [docs/01-PRD.md](docs/01-PRD.md) — Product requirements
- [docs/02-IMPLEMENTATION-PLAN.md](docs/02-IMPLEMENTATION-PLAN.md) — Step-by-step build plan
- [docs/03-TECH-SPEC.md](docs/03-TECH-SPEC.md) — Architecture decisions + CATEGORY_CONFIG
- [docs/04-API-CONTRACT.md](docs/04-API-CONTRACT.md) — API endpoints and data formats
- [docs/05-DATABASE-MIGRATIONS.md](docs/05-DATABASE-MIGRATIONS.md) — New tables and migration SQL

## Workflow: After Every Code Change

After creating or modifying any file, ALWAYS perform these steps automatically (do not wait for user to ask):

1. **Verify imports** — check that all imports resolve correctly
2. **Docker build check** — run `docker compose build ai-engine` to confirm the image builds without errors
3. **Run tests** — `docker compose exec ai-engine pytest tests/ -v` (if tests exist for the changed code)
4. **Commit** — if everything passes, create a git commit with a descriptive message summarizing the change

If any step fails — fix the issue first, then re-run the checks. Never commit broken code.

## Deployment

Single server (same machine as n8n at n8n.diconsulting.pro). All services in one Docker Compose network (`ai-platform-net`). Exposed externally: `ai-engine:8000`, `chatwoot:3000` (Phase 2), `langfuse:3100` (internal only).
