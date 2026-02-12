# CLAUDE.md — Lev Haolam AI Support Chat Platform

## Project Overview

AI-powered live chat platform for Lev Haolam customer support. Replaces email-only pipeline (n8n + Zoho) with real-time multi-channel chat using AI agents that can classify, respond, and execute actions autonomously.

**Stack:** Agno AgentOS (Python) + Chatwoot (Omnichannel) + Langfuse (Observability & Eval) + PostgreSQL (Supabase) + Pinecone + Docker Compose

**Current Phase:** Phase 0 (Foundation — AI Engine core)

---

## Quick Start

```bash
# 1. Clone and setup
cp .env.example .env
# Edit .env with your API keys

# 2. Start AI Engine
docker compose up ai-engine -d

# 3. Verify
curl http://localhost:8000/api/health

# 4. Connect Agno Control Plane
# Go to os.agno.com → Add OS → Local → http://localhost:8000
```

---

## Project Structure

```
lev-haolam-ai-platform/
├── CLAUDE.md                    # THIS FILE
├── docker-compose.yml           # All services
├── docker-compose.dev.yml       # Dev: hot reload
├── .env.example                 # Environment variables template
│
├── services/ai-engine/          # MAIN SERVICE (Phase 0+)
│   ├── main.py                  # Entry point + AgentOS + FastAPI
│   ├── config.py                # CATEGORY_CONFIG, env vars
│   ├── pipeline.py              # Full message processing flow
│   ├── agents/                  # AI Agents
│   │   ├── router.py            # Router (GPT-5.1, structured output)
│   │   ├── support.py           # Dynamic Support Agent factory
│   │   ├── outstanding.py       # Outstanding Detection
│   │   ├── eval_gate.py         # Quality gate (send/draft/escalate)
│   │   └── instructions.py      # Dynamic prompt loader from DB
│   ├── tools/                   # Agent tools
│   │   ├── customer.py          # identify, get_subscription
│   │   ├── subscription.py      # pause, skip (HITL)
│   │   ├── shipping.py          # track_package
│   │   ├── damage.py            # create_claim
│   │   └── retention.py         # generate_cancel_link (AES-256-GCM)
│   ├── knowledge/               # Pinecone integration
│   ├── guardrails/              # Safety rules
│   ├── database/                # PostgreSQL connection + queries
│   └── api/                     # FastAPI routes
│
├── services/chatwoot/           # Phase 2: Omnichannel
├── langfuse (in docker-compose)  # Phase 0: Observability & Eval
├── services/analytics/          # Phase 5: Agno Dash
│
├── shared/database/migrations/  # SQL migration files
├── shared/scripts/              # Utility scripts
└── docs/                        # Documentation
```

---

## Key Technical Decisions

1. **Agno AgentOS** for AI agents (not LangChain) — built-in HITL, learning, Control Plane
2. **Two-layer architecture:** Router Agent (fast, cheap) → Dynamic Support Agent (per category config)
3. **Model per category:** GPT-5.1 for 80% requests, Claude Sonnet 4.5 for retention only
4. **n8n continues running** in parallel (email pipeline) — zero-risk migration
5. **All data self-hosted** except Pinecone and LLM APIs

---

## Critical Safety Rules (NEVER VIOLATE)

1. **AI NEVER confirms subscription cancellation** → always redirect to self-service page
2. **AI NEVER confirms pause** → redirect or HITL confirmation
3. **Death threats, bank disputes** → immediate escalation to human
4. **Unknown category** → draft (not auto-send)
5. **Low confidence** → draft
6. **Refunds** → NEVER without human approval
7. **Sensitive data** → never in logs

---

## Database

**Provider:** Supabase (PostgreSQL)
**Existing tables:** support_threads_data, support_dialogs, ai_human_comparison, ai_answerer_instructions, ai_agent_tasks, eval_results
**New tables:** chat_sessions, chat_messages, agent_traces, tool_executions, learning_records

Connection via psycopg2 (not REST API) for speed. Read existing tables, write to new tables.

---

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=          # GPT-5.1, GPT-5.2
ANTHROPIC_API_KEY=       # Claude Sonnet 4.5 (retention)
DB_HOST=                 # Supabase PostgreSQL host
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASS=                 # Supabase DB password
PINECONE_API_KEY=        # Vector store
PINECONE_INDEX=support-examples
AGNO_API_KEY=            # Control Plane (os.agno.com)
CANCEL_LINK_PASSWORD=    # AES-256-GCM encryption key
```

---

## Common Commands

```bash
# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up ai-engine

# Production
docker compose up -d

# Logs
docker compose logs -f ai-engine

# Run tests
docker compose exec ai-engine pytest tests/

# Run migrations
docker compose exec ai-engine python -m shared.database.migrate

# Langfuse UI (observability + eval)
open http://localhost:3100
```

---

## Coding Conventions

- **Python 3.12**, type hints everywhere
- **Pydantic** for all data models (input/output)
- **Async** for API routes (FastAPI)
- **Sync** for database queries (psycopg2, not asyncpg — simpler)
- Docstrings: Google style
- Logging: `structlog` with JSON output
- Config: env vars via `pydantic-settings`
- Error handling: custom exceptions, never bare `except:`

---

## Agno-Specific Patterns

```python
# Agent creation
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    name="support_shipping",
    model=OpenAIChat(id="gpt-5.1", reasoning_effort="low"),
    instructions=["...loaded from DB..."],
    tools=[track_package, get_subscription],
    knowledge=PineconeKnowledge(namespace="shipping"),
    guardrails=[safety_guardrail],
)

# Tool with HITL
from agno.tools import tool

@tool(needs_approval=True)
def pause_subscription(subscription_id: str) -> str:
    """Pause customer subscription. Requires customer confirmation."""
    # ... API call to LH Pay
```

---

## Testing Strategy

- **Unit tests:** agents/router.py, agents/eval_gate.py, guardrails/safety.py
- **Integration tests:** full pipeline with mock DB
- **Eval tests:** via Langfuse eval pipelines + datasets
- **Load tests:** via Langfuse experiments (datasets + evaluators)

---

## Deployment

Single server with Docker Compose. All services in one `docker-compose.yml`.
Server: same machine as n8n (n8n.diconsulting.pro).
n8n already running in Docker on port 5678.

```
:8000 — AI Engine (Agno AgentOS)
:3100 — Langfuse (Observability & Eval)
:3000 — Chatwoot (Phase 2)
:5678 — n8n (already running)
```

---

## Reference Documents

- `docs/01-PRD.md` — Product Requirements
- `docs/02-IMPLEMENTATION-PLAN.md` — Step-by-step build plan
- `docs/03-TECH-SPEC.md` — Architecture decisions + repo structure
- `docs/04-API-CONTRACT.md` — API endpoints and data formats
- `docs/05-DATABASE-MIGRATIONS.md` — New tables and migration plan
