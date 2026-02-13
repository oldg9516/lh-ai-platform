# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered live chat platform for Lev Haolam customer support. Replaces email-only pipeline (n8n + Zoho) with real-time multi-channel chat using AI agents that classify, respond, and execute actions autonomously.

**Stack:** Agno AgentOS (Python 3.12) + Chatwoot (Omnichannel) + Langfuse (Observability & Eval) + PostgreSQL (Supabase) + Pinecone + Docker Compose

**Current Phase:** Phase 2 complete (Chatwoot Omnichannel). 16 containers (10 core + 4 Chatwoot + 2 Supabase Studio/Meta), full pipeline working end-to-end via Chatwoot widget. See `PROGRESS.md` for phase tracking.

## Commands

```bash
# Start all services (production)
docker compose up -d

# Development with hot reload (ai-engine only)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up ai-engine

# Rebuild after requirements.txt or Dockerfile changes
docker compose build ai-engine

# Logs
docker compose logs -f ai-engine

# Health check
curl http://localhost:8000/api/health

# Test chat UI
open http://localhost:8000/chat

# Langfuse UI (observability + eval)
open http://localhost:3100

# Import data into local Supabase
python database/import.py             # ai_answerer_instructions
python database/import_threads.py     # support_threads_data
```

**Run tests:** `docker compose exec ai-engine pytest tests/ -v`

**Chatwoot UI:** `open http://localhost:3010`

## Architecture

### Request Pipeline (api/routes.py)

This is the actual execution flow for every incoming message:

```
POST /api/chat
       │
       ▼
1. Pre-safety check (check_red_lines)
   - Regex patterns: death threats, legal threats, bank disputes, self-harm
   - If flagged → immediate escalate response, skip everything else
       │
       ▼
2. Router Agent (classify_message)
   - GPT-5.1, no reasoning, structured output → RouterOutput
   - Returns: primary category, secondary, urgency, extracted email
       │
       ▼
3. Support Agent (create_support_agent → agent.arun)
   - Factory creates agent dynamically from CATEGORY_CONFIG
   - Configures: model, instructions (from DB), Pinecone knowledge namespace
   - If agent fails → escalate response
       │
       ▼
4. Outstanding Detection (detect_outstanding) — parallel with step 3
   - GPT-5-mini, DB rules + Pinecone outstanding-cases namespace
   - Returns: is_outstanding, trigger, confidence
       │
       ▼
5. Eval Gate (evaluate_response)
   - Tier 1: regex fast-fail (subscription safety)
   - Tier 2: LLM GPT-5.1 evaluation (send/draft/escalate)
       │
       ▼
6. Save to database (save_session, save_message, save_eval_result)
   - Non-blocking: errors logged but don't fail the response
       │
       ▼
7. Return ChatResponse (response, category, decision, confidence)
```

### Chatwoot Webhook (api/routes.py)

```
POST /api/webhook/chatwoot
       │
       ▼
1. Filter (event=message_created, type=incoming, not private, not empty)
2. Dedup (in-memory TTL 5 min)
3. Build ChatRequest → call chat() (same pipeline above)
4. Dispatch by decision:
   - send     → Chatwoot public message (client sees it)
   - draft    → Chatwoot private note + open + labels
   - escalate → Chatwoot private note + open + high_priority labels
```

**Not yet implemented** (future phases): action tools with HITL, multi-turn conversation history.

### Support Agent Factory

The Support Agent is **not** 10 separate agents — it's a single factory function (`create_support_agent(category)` in `agents/support.py`) that dynamically configures model, reasoning effort, tools, Pinecone namespace, and instructions based on `CATEGORY_CONFIG` (defined in `agents/config.py`).

**10 categories:** shipping_or_delivery_question, payment_question, frequency_change_request, skip_or_pause_request, recipient_or_address_change, customization_request, damaged_or_leaking_item_report, gratitude, retention_primary_request, retention_repeated_request

**Model selection:** Currently all categories use GPT-5.1. Retention categories have a TODO to switch to Claude Sonnet 4.5 when available.

### Docker Services (16 containers)

| Service | Port | Purpose |
|---------|------|---------|
| ai-engine | 8000 | FastAPI + Agno agents |
| supabase-db | 54322 | PostgreSQL 17 |
| supabase-rest | — | PostgREST API adapter |
| supabase-api | 54321 | Nginx reverse proxy for Supabase |
| supabase-studio | 54323 | Supabase Studio UI |
| supabase-meta | — | PostgreSQL metadata API |
| langfuse-web | 3100 | Observability UI |
| langfuse-worker | — | Async job processor |
| langfuse-postgres | — | Langfuse database |
| langfuse-clickhouse | — | Tracing analytics backend |
| langfuse-redis | — | Langfuse cache |
| langfuse-minio | — | S3-compatible object storage |
| chatwoot-web | 3010 | Chatwoot omnichannel UI + API |
| chatwoot-worker | — | Sidekiq background jobs |
| chatwoot-postgres | — | Chatwoot database (pgvector) |
| chatwoot-redis | — | Chatwoot cache |

### Database: Dual Pipeline

Both the existing n8n email pipeline and the new Agno chat platform:
- **Read** prompts from `ai_answerer_instructions` (instruction_1..10, outstanding_rules, outstanding_hard_rules)
- **Write** eval results to `eval_results`

The new system adds tables: `chat_sessions`, `chat_messages`, `agent_traces`, `tool_executions`, `learning_records`. It does NOT write to `support_threads_data` or `support_dialogs` (email-only tables).

Connection: **supabase-py** (REST API) via `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. Database schema auto-initializes from SQL files in `services/supabase/init/` (00-roles, 01-schema, 02-permissions, 03-views).

### Pinecone

Index: `support-examples`. Per-category namespaces: `outstanding-cases`, `faq`, `retention`, `shipping`, `damage`, `subscription`, `customization`, `payment`, `gratitude`. Dimension: 1536, cosine metric, hybrid search enabled.

## Critical Safety Rules (NEVER VIOLATE)

1. **AI NEVER confirms subscription cancellation** — always redirect to self-service cancel page
2. **AI NEVER confirms pause directly** — redirect or HITL confirmation
3. **Death threats, bank disputes** — immediate escalation to human
4. **Unknown category** — draft (not auto-send)
5. **Low confidence** — draft
6. **Refunds** — NEVER without human approval
7. **Sensitive data** — never in logs

These are enforced in two places: `guardrails/safety.py` (regex-based pre/post checks) and `agents/instructions.py` (GLOBAL_SAFETY_RULES injected into every agent's instructions).

## Coding Conventions

- **Python 3.12**, type hints everywhere
- **Pydantic** for all data models (input/output)
- **Async** for FastAPI routes, **sync** for database queries (supabase-py is sync-only)
- **structlog** with JSON output for logging
- **pydantic-settings** for env var config
- Custom exceptions; never bare `except:`
- Google-style docstrings

### Import Paths

The Dockerfile copies `services/ai-engine/` to `/app` inside the container. All imports are relative to that root:
```python
from config import settings          # NOT from services.ai_engine.config
from agents.router import classify_message
from database.connection import get_client
from guardrails.safety import check_red_lines
```

### Agno SDK Patterns (verified against SDK 2.4.8)

```python
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
    namespace="shipping",
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

# Structured output — use output_schema (NOT response_model)
agent = Agent(model=OpenAIChat(id="gpt-5.1"), output_schema=RouterOutput)

# Run agent — async
response = await agent.arun(message)  # response.content has the text

# Tool with HITL approval (Phase 2+)
from agno.tools import tool
@tool(requires_confirmation=True)  # NOT needs_approval
def pause_subscription(subscription_id: str) -> str: ...
```

Agno doesn't have a generic custom guardrail base class. Safety checks are implemented as pre/post-processing functions called explicitly in the pipeline (see `guardrails/safety.py`).

## Environment Variables

Required in `.env` (see `.env.example`):
```
OPENAI_API_KEY, ANTHROPIC_API_KEY (optional for now)
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
PINECONE_API_KEY, PINECONE_INDEX=support-examples
LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
CANCEL_LINK_PASSWORD
```

Phase 2 (active): `CHATWOOT_URL`, `CHATWOOT_API_TOKEN`, `CHATWOOT_ACCOUNT_ID`, `CHATWOOT_SECRET_KEY_BASE`, `CHATWOOT_DB_PASSWORD`, `CHATWOOT_REDIS_PASSWORD`, `CHATWOOT_FRONTEND_URL`

Phase 3+ adds: `N8N_URL`, `N8N_API_KEY`

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

Single server (same machine as n8n at n8n.diconsulting.pro). All services in one Docker Compose network (`ai-platform-net`). Exposed externally: `ai-engine:8000`, `chatwoot:3010`, `langfuse:3100` (internal only).
