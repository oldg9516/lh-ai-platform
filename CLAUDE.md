# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered live chat platform for Lev Haolam customer support. Replaces email-only pipeline (n8n + Zoho) with real-time multi-channel chat using AI agents that classify, respond, and execute actions autonomously.

**Stack:** Agno AgentOS (Python 3.12) + CopilotKit/AG-UI (Next.js 16) + Chatwoot (Omnichannel) + Langfuse (Observability & Eval) + PostgreSQL (Supabase) + Pinecone + Docker Compose

**Current Status:** Phase 6 complete (Generative UI + HITL forms via CopilotKit). Phase 7 Days 4-7 complete (rich context, sentiment, analytics, demo materials). Phase 8: Dash analytics agent replaces custom analytics service. 19 containers, full pipeline working end-to-end via Chatwoot widget, email, CopilotKit chat, and Dash analytics. See `PROGRESS.md` for phase tracking.

## Commands

```bash
# Start all services (production)
docker compose up -d

# Development with hot reload (ai-engine only)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up ai-engine

# Frontend development (hot reload, outside Docker)
cd services/frontend && pnpm install && pnpm dev   # Port 3000, auto-proxy to localhost:8000

# Rebuild after requirements.txt or Dockerfile changes
docker compose build ai-engine
docker compose build frontend

# Logs
docker compose logs -f ai-engine
docker compose logs -f frontend

# Health checks
curl http://localhost:8000/api/health    # AI Engine
curl http://localhost:9000/health        # Dash Analytics Agent

# UIs
open http://localhost:8000/chat          # Legacy test chat
open http://localhost:3003               # CopilotKit chat (Docker)
open http://localhost:3000               # CopilotKit chat (local dev)
open http://localhost:3010               # Chatwoot
open http://localhost:3100               # Langfuse

# Import data into local Supabase
python database/import.py               # ai_answerer_instructions
python database/import_threads.py       # support_threads_data
python database/import_customers.py     # ETL: JSON → normalized customer tables

# Dash knowledge base
docker compose exec dash python scripts/load_knowledge.py
```

**Run tests:**
```bash
docker compose exec ai-engine pytest tests/ -v                                    # all tests (215+)
docker compose exec ai-engine pytest tests/ -v --ignore=tests/test_pipeline.py    # unit only (fast)
docker compose exec ai-engine pytest tests/test_e2e_multiturn.py -v              # E2E multi-turn
docker compose exec ai-engine pytest tests/test_context_builder.py -v            # context builder
docker compose exec ai-engine pytest tests/test_sentiment.py -v                  # sentiment tracking
docker compose exec ai-engine pytest tests/test_mock_apis.py -v                  # mock APIs
docker compose exec ai-engine pytest tests/test_copilot_agui.py -v              # AG-UI endpoint

# Smoke tests (from host, requires running services)
./smoke-tests.sh 1                      # Automated 6-scenario smoke test
./test-scenarios.sh                     # Manual test commands
```

## Architecture

### Two Chat Pipelines

The system has **two separate chat pipelines** serving different UIs:

1. **Legacy Pipeline** (`api/routes.py` → `POST /api/chat`) — used by Chatwoot webhook and legacy test UI. Full Agno agent with eval gate, response assembly, and HTML formatting.

2. **CopilotKit Pipeline** (`api/copilot.py` → `POST /api/copilot`) — used by Next.js frontend. Direct OpenAI API streaming with AG-UI protocol events. Supports HITL forms and display widgets.

### Legacy Pipeline (api/routes.py)

```
POST /api/chat → Pre-safety → Router Agent → Load History → Support Agent
  → Outstanding Detection (parallel) → Cancel Link → Response Assembly
  → Eval Gate → Save to DB → Return ChatResponse
```

Key details:
- Pre-safety: regex patterns (death threats, legal threats, bank disputes, self-harm)
- Router: GPT-5.1, structured output → RouterOutput (category, urgency, email, sentiment, escalation_signal)
- Support Agent: factory from `CATEGORY_CONFIG` (10 categories), model + tools + knowledge per category
- Outstanding Detection: GPT-5-mini, parallel with support agent
- Response Assembly: deterministic HTML (greeting + opener + body + closer + sign-off)
- Eval Gate: Tier 1 regex fast-fail + Tier 2 LLM evaluation → send/draft/escalate

### CopilotKit Pipeline (api/copilot.py)

```
POST /api/copilot → Router Agent → Rich Context Builder → Direct OpenAI Streaming
  → Tool Call Loop (max 5): LLM → tool → result → LLM
  → HITL tools → AG-UI ToolCall events → CopilotKit renders forms
  → Read-only tools → executed server-side, results fed back to LLM
  → Display tools → self-fetching widgets call /api/copilot/fetch-data
```

**Why direct OpenAI?** Agno SDK doesn't emit proper ToolCall events needed by AG-UI protocol. The copilot endpoint bypasses Agno and streams OpenAI responses directly, emitting AG-UI events.

**Tool classification:**
- `HITL_TOOL_NAMES`: pause_subscription, change_frequency, skip_month, change_address, create_damage_claim — emit ToolCall events, frontend renders confirmation forms
- `DISPLAY_TOOL_NAMES`: display_tracking, display_orders, display_box_contents, display_payments — auto-injected via `READ_TO_DISPLAY` mapping
- `READ_ONLY_TOOLS`: get_subscription, get_customer_history, etc. — executed server-side

**Additional endpoints:**
- `POST /api/copilot/execute-tool` — executes HITL tools after user approval (whitelist: WRITE_TOOLS only)
- `POST /api/copilot/fetch-data` — serves data to self-fetching display widgets

### Chatwoot Webhook (api/routes.py)

```
POST /api/webhook/chatwoot → Filter → Dedup (TTL 5 min) → Extract Channel
  → Build session_id "cw_{conversation_id}" → chat() pipeline
  → Dispatch: send → public msg, draft → private note, escalate → private note + labels
```

### Rich Context Builder (agents/context_builder.py)

Phase 7 addition. `build_customer_context(email)` and `build_full_context(email, session_id, message)` aggregate:
- Customer profile (name, join_date, LTV, total_orders)
- Active subscription (frequency, next_charge, status)
- Recent orders (last 3)
- Support history (last 3 interactions)
- Conversation history (smart truncation, 500 chars per message)
- Outstanding issues (is_outstanding, trigger, confidence)

Injected into CopilotKit pipeline as context prepended to agent input.

### Support Agent Factory

Single factory function (`create_support_agent(category)` in `agents/support.py`) dynamically configures model, reasoning effort, tools, Pinecone namespace, and instructions based on `CATEGORY_CONFIG` (defined in `agents/config.py`).

**10 categories:** shipping_or_delivery_question, payment_question, frequency_change_request, skip_or_pause_request, recipient_or_address_change, customization_request, damaged_or_leaking_item_report, gratitude, retention_primary_request, retention_repeated_request

**Model selection:** All categories use GPT-5.1. Retention categories use `reasoning_effort="medium"` for deeper reasoning on complex cancellation scenarios.

### Frontend (services/frontend/)

Next.js 16 + CopilotKit + AG-UI protocol.

**Key dependencies:** `@copilotkit/react-core` + `react-ui` v1.51.3, `@ag-ui/client` v0.0.45 (HttpAgent), React 19, shadcn/ui + Radix UI, Tailwind CSS v4, Zustand, React Query v5, react-hook-form + zod, sonner (toasts).

**Package manager:** pnpm (not npm/yarn).

**Structure:**
- `app/page.tsx` — CopilotSidebar with "Lev Haolam Support" branding
- `app/api/copilot/` — Next.js proxy routes to FastAPI backend
- `components/forms/` — 5 HITL confirmation forms (PauseSubscription, ChangeFrequency, ChangeAddress, DamageClaim, SkipMonth)
- `components/widgets/` — 4 display widgets (Tracking, OrderHistory, BoxContents, PaymentHistory)
- `components/ui/` — shadcn/ui components

**HITL form pattern:** `useHumanInTheLoop` hook → status lifecycle (inProgress → executing → complete) → form calls `/api/copilot/execute-tool` on Approve → `respond()` with result.

**Display widget pattern:** Widget receives `customer_email` via tool args → calls `/api/copilot/fetch-data` → renders rich UI → auto-responds after 500ms.

### Mock API Infrastructure (mock_apis/)

Phase 6.1.5. Protocol-based factory pattern for development without real external APIs.

- `mock_apis/client.py`: MockZohoAPI, MockAddressValidationAPI, MockDamageClaimAPI
- `mock_apis/factory.py`: Protocol definitions + APIFactory
- Realistic latencies (300-800ms), structured responses
- Settings flag: `USE_MOCK_APIS=true` (default)
- 6 write tools converted to async + APIFactory integration

### Docker Services (19 containers)

| Service | Port | Purpose |
|---------|------|---------|
| ai-engine | 8000 | FastAPI + Agno agents (main support pipeline) |
| frontend | 3003 | Next.js + CopilotKit (AG-UI chat) + Dash chat (/dash) |
| dash | 9000 | Agno Dash — self-learning data agent (AgentOS) |
| dash-db | — | PgVector for Dash knowledge/learnings/state |
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

The new system adds tables:
- **Chat platform:** `chat_sessions`, `chat_messages`, `agent_traces`, `tool_executions`, `learning_records`
- **Customer data:** `customers`, `subscriptions`, `orders`, `tracking_events` — normalized relational model
- **Legacy (n8n only):** `support_threads_data`, `support_dialogs` — read-only

**Customer Identification:** `database/customer_queries.py` provides 8 query functions. Tools use these to fetch real customer data (962 customers, 649 subscriptions, 1826 orders, 268 tracking events imported from production).

Connection: **supabase-py** (REST API) via `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. Schema auto-initializes from SQL files in `services/supabase/init/` (00-roles, 01-schema, 02-permissions, 03-views, 04-customers, 05-analytics-user).

### Pinecone

Index: `support-examples`. Per-category namespaces: `outstanding-cases`, `faq`, `retention`, `shipping`, `damage`, `subscription`, `customization`, `payment`, `gratitude`, `analytics-knowledge`. Dimension: 1536 (main), 1024 (analytics), cosine metric, hybrid search enabled.

**CRITICAL: Embedding Dimension Configuration**

The `dimension` parameter on `PineconeDb()` only validates index dimension — it does NOT control the embedding model dimension. Without an explicit embedder, Agno defaults to `OpenAIEmbedder(id="text-embedding-3-large")` which generates **1536-dimensional** vectors.

For indexes with different dimensions (e.g., analytics uses 1024), you MUST explicitly pass an embedder:

```python
from agno.knowledge.embedder.openai import OpenAIEmbedder

embedder = OpenAIEmbedder(id="text-embedding-3-large", dimensions=1024)
vector_db = PineconeDb(
    name="support-examples",
    dimension=1024,
    namespace="analytics-knowledge",
    embedder=embedder,  # MUST explicitly set to generate 1024-dim vectors
)
```

**Symptom if misconfigured:** `Vector dimension 1536 does not match the dimension of the index 1024`

### Dash Analytics Agent (Phase 8)

Self-learning data agent based on [agno-agi/dash](https://github.com/agno-agi/dash). Replaces the previous custom analytics service.

**Architecture:** 6-layer context system:
1. **Semantic Model** — 9 table schema JSONs loaded into system prompt
2. **Business Rules** — metrics definitions, data quality gotchas, capitalization rules
3. **Validated SQL Patterns** — 8 reusable query templates
4. **Knowledge Base** — PgVector hybrid search (curated, loaded via `load_knowledge.py`)
5. **Learnings** — auto-discovered patterns via LearningMachine (AGENTIC mode)
6. **Runtime Schema Inspection** — `introspect_schema` tool for live DDL

**Dual DB:** `dash-db` (PgVector) for agent state/knowledge/learnings, Supabase (read-only via `analytics_readonly` user) for customer data queries via SQLTools.

**Model:** `OpenAIResponses("gpt-5.2")` with `LearningMachine(mode=LearningMode.AGENTIC)`.

**API:** AgentOS auto-generates REST endpoints: `POST /agents/dash/runs` (SSE streaming), `/health`.

**Frontend:** `/dash` route in Next.js app — standalone chat UI with SSE streaming, no CopilotKit dependency. API proxy at `/api/dash`.

### Multi-turn Conversation History

**Manual implementation** (NOT Agno native sessions due to SDK bugs #2497, #2570):

1. **Session ID:** Chatwoot uses `cw_{conversation_id}`, API fallback `sess_{uuid}`
2. **History loading:** `get_conversation_history(session_id, limit=10)` — last 10 messages (5 turns)
3. **Truncation:** Agent responses truncated to 500 chars
4. **Injection:** Prepended to agent_input with `[Conversation History]` / `[End History]` markers

## Critical Safety Rules (NEVER VIOLATE)

1. **AI NEVER confirms subscription cancellation** — always redirect to self-service cancel page
2. **AI NEVER confirms pause directly** — redirect or HITL confirmation
3. **Death threats, bank disputes** — immediate escalation to human
4. **Unknown category** — draft (not auto-send)
5. **Low confidence** — draft
6. **Refunds** — NEVER without human approval
7. **Sensitive data** — never in logs

Enforced in: `guardrails/safety.py` (regex pre/post checks) and `agents/instructions.py` (GLOBAL_SAFETY_RULES injected into every agent).

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
from agents.support import create_support_agent
from agents.context_builder import build_full_context
from database.connection import get_client
from database.queries import get_conversation_history, save_session, save_message
from database.customer_queries import lookup_customer, get_active_subscription_by_email
from guardrails.safety import check_red_lines
from tools import resolve_tools, TOOL_REGISTRY, WRITE_TOOLS
from mock_apis.factory import APIFactory
from chatwoot.client import ChatwootClient
```

### Action Tools

**12 tools** in `TOOL_REGISTRY` (`tools/__init__.py`):

**Read-only (real data from DB):** get_subscription, get_customer_history, get_payment_history, track_package, get_box_contents

**Write operations (async, mock APIs in dev):** change_frequency, skip_month, pause_subscription, change_address, create_damage_claim, request_photos

**Retention-specific:** generate_cancel_link (AES-256-GCM encrypted self-service link)

**Tool resolution:** `resolve_tools(category_tools)` maps names from `CATEGORY_CONFIG.tools` to callables.

### Agno SDK Patterns (verified against SDK 2.4.8)

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

# Knowledge via PineconeDb (NOT "PineconeKnowledge" — doesn't exist)
vector_db = PineconeDb(
    name="support-examples", dimension=1536, metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
    api_key=settings.pinecone_api_key, namespace="shipping",
    use_hybrid_search=True,
)
knowledge = Knowledge(vector_db=vector_db)

agent = Agent(
    name="support_shipping",
    model=OpenAIChat(id="gpt-5.1"),
    instructions=["...loaded from DB..."],
    knowledge=knowledge,
    search_knowledge=True,  # MUST set explicitly
    tools=[get_subscription, track_package],
)

# Reasoning effort — on OpenAIChat(), NOT Agent()
model = OpenAIChat(id="gpt-5.1", reasoning_effort="medium")

# Structured output — use output_schema (NOT response_model)
agent = Agent(model=OpenAIChat(id="gpt-5.1"), output_schema=RouterOutput)

# Run agent — async
response = await agent.arun(message)  # response.content has text or Pydantic object
```

**Gotchas:**
- `reasoning_effort` is set on `OpenAIChat()`, NOT on `Agent()`
- `arun()` takes a single string, not messages list
- `search_knowledge=True` must be set explicitly on Agent
- Tool docstrings + type hints define the schema for LLM tool calling
- Agno doesn't have a generic custom guardrail base class — safety checks are explicit pre/post-processing
- Pinecone dimension mismatch: always set `embedder=OpenAIEmbedder(dimensions=N)` if index uses non-default dimensions

### Response Assembly (agents/response_assembler.py)

Email-style HTML formatting: `<div>Greeting</div> + <div>Opener</div> + <div>Body</div> + <div>Closer</div> + <div>Sign-off</div>`

Name extraction: fast path uses `contact_name` from Chatwoot, LLM path (GPT-5-mini) extracts from message signature, fallback: "Valued Customer".

## Environment Variables

Required in `.env` (see `.env.example`):
```
OPENAI_API_KEY, ANTHROPIC_API_KEY (optional)
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
PINECONE_API_KEY, PINECONE_INDEX=support-examples
LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
CANCEL_LINK_PASSWORD
CHATWOOT_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID, CHATWOOT_SECRET_KEY_BASE
CHATWOOT_DB_PASSWORD, CHATWOOT_REDIS_PASSWORD, CHATWOOT_FRONTEND_URL
DASH_DB_PASSWORD (Dash PgVector DB), AGNO_API_KEY (optional, Control Plane)
USE_MOCK_APIS=true (default, set false for real external APIs)
NEXT_PUBLIC_API_URL=http://ai-engine:8000 (Docker only, dev auto-proxies to localhost:8000)
```

## Reference Documents

- [docs/01-PRD.md](docs/01-PRD.md) — Product requirements
- [docs/02-IMPLEMENTATION-PLAN.md](docs/02-IMPLEMENTATION-PLAN.md) — Step-by-step build plan
- [docs/03-TECH-SPEC.md](docs/03-TECH-SPEC.md) — Architecture decisions + CATEGORY_CONFIG
- [docs/04-API-CONTRACT.md](docs/04-API-CONTRACT.md) — API endpoints and data formats
- [docs/05-DATABASE-MIGRATIONS.md](docs/05-DATABASE-MIGRATIONS.md) — New tables and migration SQL
- [docs/07-LANGFUSE-GUIDE.md](docs/07-LANGFUSE-GUIDE.md) — Langfuse observability setup (Russian)
- [docs/08-COPILOTKIT-GENERATIVE-UI.md](docs/08-COPILOTKIT-GENERATIVE-UI.md) — Phase 6: CopilotKit + AG-UI protocol for HITL forms (Russian)
- [docs/09-AI-AGENT-BEST-PRACTICES-2026.md](docs/09-AI-AGENT-BEST-PRACTICES-2026.md) — AI agent best practices
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — Phase 6-10 roadmap + Agno Learning Machine analysis (Russian)
- [docs/LH-COMPANY.md](docs/LH-COMPANY.md) — Lev Haolam company overview (Russian) — useful for tone and retention scenarios
- [docs/DEMO-SCRIPT.md](docs/DEMO-SCRIPT.md) — 40-minute demo presentation script
- [docs/DEMO-QA.md](docs/DEMO-QA.md) — 20 prepared demo Q&A answers
- [docs/DEMO-FINAL-CHECKLIST.md](docs/DEMO-FINAL-CHECKLIST.md) — Production readiness gate
- [.agents/skills/agno-sdk/SKILL.md](.agents/skills/agno-sdk/SKILL.md) — Project-specific Agno patterns and gotchas

## Workflow: After Every Code Change

After creating or modifying any file, ALWAYS perform these steps automatically (do not wait for user to ask):

1. **Verify imports** — check that all imports resolve correctly
2. **Docker build check** — run `docker compose build ai-engine` (and `frontend` if frontend changed) to confirm the image builds without errors
3. **Run tests** — `docker compose exec ai-engine pytest tests/ -v` (if tests exist for the changed code)
4. **Commit** — if everything passes, create a git commit with a descriptive message summarizing the change

If any step fails — fix the issue first, then re-run the checks. Never commit broken code.

## Deployment

Single server (same machine as n8n at n8n.diconsulting.pro). All services in one Docker Compose network (`ai-platform-net`). Exposed externally: `ai-engine:8000`, `frontend:3003`, `chatwoot:3010`, `langfuse:3100` (internal only).
