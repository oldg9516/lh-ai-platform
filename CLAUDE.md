# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered live chat platform for Lev Haolam customer support. Replaces email-only pipeline (n8n + Zoho) with real-time multi-channel chat using AI agents that classify, respond, and execute actions autonomously.

**Stack:** Agno AgentOS (Python 3.12) + Chatwoot (Omnichannel) + Langfuse (Observability & Eval) + PostgreSQL (Supabase) + Pinecone + Docker Compose

**Current Phase:** Phase 5 complete (AgentOS Analytics Service). 17 containers (11 core + 4 Chatwoot + 2 Supabase Studio/Meta), full pipeline working end-to-end via Chatwoot widget and email. Phase 4 complete (multi-turn, retention reasoning, email channel). See `PROGRESS.md` for phase tracking.

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

# Analytics Service (Phase 5)
docker compose exec analytics python load_knowledge.py  # Load analytics KB to Pinecone
curl http://localhost:9000/api/health                    # Analytics health check
curl http://localhost:9000/api/metrics/overview          # Get platform metrics
open http://os.agno.com                                  # AgentOS Control Plane (requires AGNO_API_KEY)
```

**Run tests:**
```bash
docker compose exec ai-engine pytest tests/ -v                           # all tests (202 total)
docker compose exec ai-engine pytest tests/ -v --ignore=tests/test_pipeline.py  # unit only (162 tests, fast)
docker compose exec ai-engine pytest tests/test_e2e_multiturn.py -v     # multi-turn E2E (5 tests)
```

**Test breakdown:** 162 unit + 35 integration + 5 E2E multi-turn = 202 tests passing

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
3. Load conversation history (get_conversation_history)
   - Last 10 messages (5 turns) for this session_id
   - Agent responses truncated to 500 chars in history
   - Manual prepending to agent_input (NOT Agno native sessions)
       │
       ▼
4. Support Agent (create_support_agent → agent.arun)
   - Factory creates agent dynamically from CATEGORY_CONFIG
   - Configures: model, reasoning_effort, tools, instructions (from DB), Pinecone knowledge namespace
   - Customer email passed to enable tool lookups
   - If agent fails → escalate response
       │
       ▼
5. Outstanding Detection (detect_outstanding) — parallel with step 4
   - GPT-5-mini, DB rules + Pinecone outstanding-cases namespace
   - Returns: is_outstanding, trigger, confidence
       │
       ▼
6. Cancel link injection (retention categories only)
   - AES-256-GCM encrypted link with customer email
       │
       ▼
7. Response assembly (agents/response_assembler.py)
   - Deterministic: greeting + opener + body + closer + sign-off in HTML divs
       │
       ▼
8. Eval Gate (evaluate_response)
   - Tier 1: regex fast-fail (subscription safety)
   - Tier 2: LLM GPT-5.1 evaluation (send/draft/escalate)
   - Receives tools_available context so tool-returned data passes accuracy check
       │
       ▼
9. Save to database (save_session, save_message, save_eval_result)
   - Non-blocking: errors logged but don't fail the response
       │
       ▼
10. Return ChatResponse (response, category, decision, confidence)
```

### Chatwoot Webhook (api/routes.py)

```
POST /api/webhook/chatwoot
       │
       ▼
1. Filter (event=message_created, type=incoming, not private, not empty)
2. Dedup (in-memory TTL 5 min)
3. Extract channel (Channel_Type enum: api_channel, web_widget, email, whatsapp, etc.)
4. Build session_id: "cw_{conversation_id}" for stable multi-turn sessions
5. Build ChatRequest → call chat() (same pipeline above)
6. Dispatch by decision:
   - send     → Chatwoot public message (client sees it)
                • Chat channels: HTML stripped for display
                • Email channels: HTML preserved (native support)
   - draft    → Chatwoot private note + open + labels
   - escalate → Chatwoot private note + open + high_priority labels
7. Error handling: pipeline error → private note + open for agent
```

**Phase 3 complete:** 12 action tools (5 read-only with real DB data, 7 write stubs). Customer identification via normalized tables: customers, subscriptions, orders, tracking_events.

**Phase 4 complete:** Multi-turn conversation history (manual, last 10 messages), reasoning_effort="medium" for retention, email channel support.

**Phase 5 complete:** AgentOS Analytics Service with triple access pattern (see below).

### Analytics Service (Phase 5)

**Triple Access Pattern:**

1. **AgentOS Control Plane** (os.agno.com)
   - Native UI for chatting with analytics agent
   - Auto-sync to cloud via `AGNO_API_KEY`
   - Langfuse integration for tracing

2. **Custom FastAPI Endpoints** (localhost:9000)
   - `/api/metrics/overview` — resolution rate, escalation rate, category distribution
   - `/api/metrics/categories` — per-category stats
   - `/api/charts/category-distribution` — Plotly JSON for visualization
   - `/api/query` — natural language SQL via PostgresTools agent

3. **Langfuse Observability** (localhost:3100)
   - Separate project: "Analytics Agent"
   - Traces all SQL queries + LLM calls
   - Debugging analytics agent behavior

**Architecture:**

```python
# services/analytics/agent.py
analytics_agent = Agent(
    name="analytics_agent",
    model=OpenAIChat(id="gpt-5-mini"),  # Cheap model for SQL
    tools=[PostgresTools(host=..., port=..., db_name=..., user=..., password=...)],
    knowledge=Knowledge(vector_db=PineconeDb(..., namespace="analytics-knowledge")),
    search_knowledge=True,
    instructions=[...],  # PostgreSQL-specific guidance
)
```

**PostgresTools:** Natural language → SQL queries. Requires separate connection parameters (host, port, db_name, user, password) — does NOT accept `db_url` directly. Use `urllib.parse.urlparse()` to extract components.

**Knowledge Base:** Table schemas, sample queries, business rules loaded into Pinecone `analytics-knowledge` namespace via `load_knowledge.py`.

### Support Agent Factory

The Support Agent is **not** 10 separate agents — it's a single factory function (`create_support_agent(category)` in `agents/support.py`) that dynamically configures model, reasoning effort, tools, Pinecone namespace, and instructions based on `CATEGORY_CONFIG` (defined in `agents/config.py`).

**10 categories:** shipping_or_delivery_question, payment_question, frequency_change_request, skip_or_pause_request, recipient_or_address_change, customization_request, damaged_or_leaking_item_report, gratitude, retention_primary_request, retention_repeated_request

**Model selection:** All categories use GPT-5.1. Retention categories (`retention_primary_request`, `retention_repeated_request`) use `model_provider="openai_responses"` with `reasoning_effort="medium"` for deeper reasoning on complex cancellation scenarios.

### Docker Services (17 containers)

| Service | Port | Purpose |
|---------|------|---------|
| ai-engine | 8000 | FastAPI + Agno agents (main support pipeline) |
| analytics | 9000 | AgentOS Analytics Service (PostgresTools + natural language SQL) |
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
- **Customer data (Phase 3):** `customers`, `subscriptions`, `orders`, `tracking_events` — normalized relational model for customer identification and tool lookups
- **Legacy (n8n only):** `support_threads_data`, `support_dialogs` — read-only for historical data

**Customer Identification:** `database/customer_queries.py` provides 8 query functions: `lookup_customer`, `get_active_subscription_by_email`, `get_subscriptions_by_customer`, `get_orders_by_subscription`, `get_payment_history`, `get_tracking_events`, `get_box_info`, `get_customer_support_history`. Tools use these to fetch real customer data (962 customers, 649 subscriptions, 1826 orders, 268 tracking events imported from production).

Connection: **supabase-py** (REST API) via `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. Database schema auto-initializes from SQL files in `services/supabase/init/` (00-roles, 01-schema, 02-permissions, 03-views, 04-customers).

### Pinecone

Index: `support-examples`. Per-category namespaces: `outstanding-cases`, `faq`, `retention`, `shipping`, `damage`, `subscription`, `customization`, `payment`, `gratitude`, `analytics-knowledge`. Dimension: 1536 (main), 1024 (analytics), cosine metric, hybrid search enabled.

**CRITICAL: Embedding Dimension Configuration**

The `dimension` parameter on `PineconeDb()` only sets the index dimension for validation — it does NOT control the embedding model dimension. Without an explicit embedder, Agno defaults to `OpenAIEmbedder(id="text-embedding-3-large")` which generates **1536-dimensional** vectors.

For indexes with different dimensions (e.g., analytics uses 1024), you MUST explicitly pass an embedder:

```python
from agno.knowledge.embedder.openai import OpenAIEmbedder

# For 1024-dimensional index
embedder = OpenAIEmbedder(
    id="text-embedding-3-large",
    dimensions=1024,  # Reduce from default 3072 to match index
)

vector_db = PineconeDb(
    name="support-examples",
    dimension=1024,
    namespace="analytics-knowledge",
    embedder=embedder,  # Explicitly set to generate 1024-dim vectors
)
```

**Symptom if misconfigured:** `Vector dimension 1536 does not match the dimension of the index 1024`

### Multi-turn Conversation History (Phase 4)

**Manual implementation** (NOT Agno native sessions due to bugs in SDK 2.x — see GitHub issues #2497, #2570):

1. **Session ID:** Stable across conversation. Chatwoot uses `cw_{conversation_id}`, API fallback `sess_{uuid}`.
2. **History loading:** `get_conversation_history(session_id, limit=10)` returns last 10 messages (5 turns).
3. **Truncation:** Agent responses truncated to 500 chars in history to prevent context bloat.
4. **Injection:** History prepended to agent_input as text with `[Conversation History]` / `[End History]` markers.
5. **Format:** Each message as `Customer: <message>` or `Agent: <response>`.

See `services/ai-engine/tests/test_e2e_multiturn.py` for multi-turn test scenarios (followup questions, explicit references, session isolation, history limits).

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
from agents.support import create_support_agent
from database.connection import get_client
from database.queries import get_conversation_history, save_session, save_message
from database.customer_queries import lookup_customer, get_active_subscription_by_email
from guardrails.safety import check_red_lines
from tools import resolve_tools, TOOL_REGISTRY
from chatwoot.client import ChatwootClient
```

### Action Tools (Phase 3)

**12 tools** in `TOOL_REGISTRY` (`tools/__init__.py`):

**Read-only (real data from DB):**
- `get_subscription(email)` — active subscription details (next charge, frequency, status)
- `get_customer_history(email)` — order history, tracking, support interactions
- `get_payment_history(email)` — payment dates, amounts, methods
- `track_package(email)` — tracking number, carrier, status, estimated delivery
- `get_box_contents(email)` — products in last box

**Write operations (stubs, return `pending_confirmation`):**
- `change_frequency(email, new_frequency)` — monthly/bi-monthly/quarterly
- `skip_month(email, month)` — skip one shipment
- `pause_subscription(email, months)` — pause for N months
- `change_address(email, new_address)` — update delivery address
- `create_damage_claim(email, description)` — file damage report
- `request_photos(email)` — ask customer for damage photos

**Retention-specific:**
- `generate_cancel_link(email)` — AES-256-GCM encrypted self-service cancel link

**Tool resolution:** `resolve_tools(category_tools: list[str])` maps tool names from `CATEGORY_CONFIG.tools` to callable functions. Passed to `Agent(tools=[...])` in factory.

**Customer not found:** Tools return `{"found": false, "message": "..."}` → AI asks for clarification → Eval Gate drafts (low accuracy).

### Agno SDK Patterns (verified against SDK 2.4.8)

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

# Knowledge via PineconeDb (NOT "PineconeKnowledge" — that class doesn't exist)
# For standard 1536-dimensional embeddings
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

# For custom embedding dimensions (e.g., analytics uses 1024)
from agno.knowledge.embedder.openai import OpenAIEmbedder
embedder = OpenAIEmbedder(id="text-embedding-3-large", dimensions=1024)
vector_db = PineconeDb(
    name="support-examples",
    dimension=1024,
    namespace="analytics-knowledge",
    embedder=embedder,  # MUST explicitly set to match index dimension
    use_hybrid_search=True,
)
knowledge = Knowledge(vector_db=vector_db)

# Basic agent
agent = Agent(
    name="support_shipping",
    model=OpenAIChat(id="gpt-5.1"),
    instructions=["...loaded from DB..."],
    knowledge=knowledge,
    search_knowledge=True,  # MUST set explicitly
    tools=[get_subscription, track_package],  # resolved from TOOL_REGISTRY
)

# Reasoning effort — passed to OpenAIChat() constructor
model = OpenAIChat(id="gpt-5.1", reasoning_effort="medium")  # "none" | "low" | "medium" | "high"
agent = Agent(model=model, instructions=["..."])

# Structured output — use output_schema (NOT response_model)
agent = Agent(model=OpenAIChat(id="gpt-5.1"), output_schema=RouterOutput)

# Run agent — async
response = await agent.arun(message)  # response.content has the text or Pydantic object

# Tool with HITL approval (future Phase 6)
from agno.tools import tool
@tool(requires_confirmation=True)  # NOT needs_approval
def pause_subscription(email: str, months: int) -> str: ...
```

**Important gotchas:**
- `reasoning_effort` is set on `OpenAIChat()`, NOT on `Agent()`
- `arun()` takes a single string, not messages list. For multi-turn, prepend history manually or use `db=PostgresDb()` + `add_history_to_context=True` (currently avoided due to SDK bugs #2497, #2570)
- `search_knowledge=True` must be set explicitly on Agent
- Tool docstrings + type hints define the schema for LLM tool calling
- Agno doesn't have a generic custom guardrail base class. Safety checks are implemented as pre/post-processing functions called explicitly in the pipeline (see `guardrails/safety.py`)
- **Pinecone dimension mismatch:** The `dimension` parameter on `PineconeDb()` only validates index dimension — it does NOT control embedding model dimension. Always explicitly set `embedder=OpenAIEmbedder(dimensions=N)` if your index uses non-default dimensions (see Pinecone section above)

### Response Assembly (agents/response_assembler.py)

Email-style formatting for consistency with n8n legacy pipeline:

```python
from agents.response_assembler import assemble_response

html_response = assemble_response(
    agent_body="Here's your tracking info...",
    customer_name="Sarah",  # from name_extractor or "Valued Customer"
    category="shipping_or_delivery_question"
)
```

**Structure:** `<div>Greeting</div> + <div>Opener</div> + <div>Body</div> + <div>Closer</div> + <div>Sign-off</div>`

**Name extraction:** Fast path uses `contact_name` from Chatwoot. LLM path (GPT-5-mini) extracts from message signature. Fallback: "Valued Customer".

**Cancel link injection:** For retention categories, `generate_cancel_link(email)` → encrypted link appended to closer div.

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

Phase 5 (analytics): `ANALYTICS_DB_URL` (read-only PostgreSQL connection), `AGNO_API_KEY` (optional, for AgentOS Control Plane sync)

## Reference Documents

- [docs/01-PRD.md](docs/01-PRD.md) — Product requirements
- [docs/02-IMPLEMENTATION-PLAN.md](docs/02-IMPLEMENTATION-PLAN.md) — Step-by-step build plan
- [docs/03-TECH-SPEC.md](docs/03-TECH-SPEC.md) — Architecture decisions + CATEGORY_CONFIG
- [docs/04-API-CONTRACT.md](docs/04-API-CONTRACT.md) — API endpoints and data formats
- [docs/05-DATABASE-MIGRATIONS.md](docs/05-DATABASE-MIGRATIONS.md) — New tables and migration SQL
- [docs/07-LANGFUSE-GUIDE.md](docs/07-LANGFUSE-GUIDE.md) — Langfuse observability setup (Russian)
- [docs/08-COPILOTKIT-GENERATIVE-UI.md](docs/08-COPILOTKIT-GENERATIVE-UI.md) — Phase 6: CopilotKit + AG-UI protocol for HITL forms (Russian)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — Phase 6-10 roadmap + Agno Learning Machine analysis: personalization vs self-improvement, dual-track strategy (Russian)
- [docs/LH-COMPANY.md](docs/LH-COMPANY.md) — Lev Haolam company overview, business model, mission, target audience (Russian) — useful context when tuning tone, understanding retention scenarios, and customer expectations
- [.agents/skills/agno-sdk/SKILL.md](.agents/skills/agno-sdk/SKILL.md) — Project-specific Agno patterns, gotchas, tool registry, multi-turn implementation details

## Workflow: After Every Code Change

After creating or modifying any file, ALWAYS perform these steps automatically (do not wait for user to ask):

1. **Verify imports** — check that all imports resolve correctly
2. **Docker build check** — run `docker compose build ai-engine` to confirm the image builds without errors
3. **Run tests** — `docker compose exec ai-engine pytest tests/ -v` (if tests exist for the changed code)
4. **Commit** — if everything passes, create a git commit with a descriptive message summarizing the change

If any step fails — fix the issue first, then re-run the checks. Never commit broken code.

## Deployment

Single server (same machine as n8n at n8n.diconsulting.pro). All services in one Docker Compose network (`ai-platform-net`). Exposed externally: `ai-engine:8000`, `chatwoot:3010`, `langfuse:3100` (internal only).
