# Progress Tracker

## Phase 0: Foundation (AI Engine core)

### Infrastructure
- [x] .gitignore + .env.example
- [x] docker-compose.yml (ai-engine + Langfuse stack)
- [x] docker-compose.dev.yml (hot reload)
- [x] Dockerfile (Python 3.12-slim)
- [x] requirements.txt (agno, supabase, langfuse, fastapi, etc.)

### AI Engine Code
- [x] config.py (pydantic-settings, env vars)
- [x] database/connection.py (supabase-py client singleton)
- [x] database/queries.py (get_instructions, get_global_rules, save_session, save_message)
- [x] knowledge/pinecone_client.py (PineconeDb per-namespace)
- [x] guardrails/safety.py (red lines + subscription safety)
- [x] agents/config.py (CATEGORY_CONFIG, 10 categories)
- [x] agents/router.py (RouterOutput, classify_message)
- [x] agents/support.py (create_support_agent factory)
- [x] agents/instructions.py (load from DB + GLOBAL_SAFETY_RULES)
- [x] main.py (FastAPI + lifespan + Langfuse tracing)
- [x] api/routes.py (POST /api/chat, GET /api/health)

### Observability
- [x] Langfuse self-hosted (6 services in docker-compose)
- [x] AgnoInstrumentor + OpenTelemetry integration
- [x] Auto-created project with keys on first boot

### Docs Updated
- [x] CLAUDE.md (stack, env vars, DB connection, Langfuse)
- [x] All docs/* (Agenta replaced with Langfuse)

### Local Supabase
- [x] supabase-db (PostgreSQL 17) in docker-compose
- [x] supabase-rest (PostgREST) in docker-compose
- [x] supabase-api (nginx reverse proxy) in docker-compose
- [x] Init SQL: roles, schema (all tables), permissions, views
- [x] Supabase Studio UI (port 54323) + postgres-meta service

### Data Import
- [x] Import 10 ai_answerer_instructions (v3 prompts) from production
- [x] Import 500 support_threads_data records from production
- [x] Import 1000 more support_threads_data records (total: 1500)
- [x] Import 3000 ai_human_comparison records (with subscription_info, tracking_info, identification)
- [x] database/import.py + database/import_threads.py + database/import_comparison.py scripts

### Smoke Test Results (all passed)
- [x] shipping_or_delivery_question — correct classification + quality response (8.4s)
- [x] retention_primary_request — downsell offer + cancel link (9.0s)
- [x] death threat → escalate (38ms, red line pre-check)
- [x] gratitude — warm response (5.2s)
- [x] damaged_or_leaking_item_report — photo request + replacement (4.7s)
- [x] recipient_or_address_change — asks for full address (10.7s)
- [x] payment_question — charge date info (5.8s)
- [x] customization_request — alcohol-free update (3.8s)

### Phase 0 Completed
- [x] All 10 containers healthy (docker compose ps)
- [x] Langfuse UI accessible (http://localhost:3100)
- [x] AI Engine health check (http://localhost:8000/api/health)
- [x] DB tables auto-created by init SQL
- [x] Local Supabase with production schemas
- [x] Pinecone index "support-examples" connected
- [x] POST /api/chat full pipeline working
- [x] Pushed to GitHub

---

## Phase 1: Live Testing + Tuning

### N8n Workflow Feature Parity
- [x] Instruction merging (global + specific, matching n8n production logic)
- [x] Pinecone dimension fix (1536 → 1024 configurable)
- [x] Name extraction (fast path: contact_name, LLM path: GPT-5-mini from signature)
- [x] Response assembly (deterministic: greeting + opener + body + closer + sign-off in HTML divs)
- [x] Cancel link generation (AES-256-GCM encryption) — moved from Phase 3
- [x] Cancel link injection for retention categories

### Testing
- [x] Test all 10 categories with real customer messages (29 integration tests)
- [x] Unit tests: guardrails (19), response assembler (16), name extractor (14)
- [x] All 78 tests passing (49 unit + 29 integration)

### Observability Fixes
- [x] Fix Langfuse tracing (Basic Auth on OTLP exporter)
- [x] Traces visible in Langfuse UI

### Eval System
- [x] Export 3000 ai_human_comparison records (golden dataset with classification)
- [x] Import ai_human_comparison into local Supabase (3000 records)
- [x] Create Langfuse datasets: golden (338), good (1722), full (2413)
- [x] Eval runner: pipeline + LLM-judge (GPT-5.1) scoring → Langfuse
- [x] Baseline scores: accuracy=0.75, tone=0.89, safety=0.98, overall=0.77
- [x] Langfuse documentation (docs/07-LANGFUSE-GUIDE.md, Russian)

### Outstanding Detection + Eval Gate
- [x] Outstanding Detection agent (GPT-5-mini, DB rules + Pinecone outstanding-cases)
- [x] Eval Gate agent (Tier 1: regex fast-fail + Tier 2: LLM GPT-5.1 evaluation)
- [x] Pipeline updated: parallel outstanding + support, eval gate replaces check_subscription_safety
- [x] Database: save_eval_result + update_session_outstanding queries
- [x] Unit tests: test_outstanding.py, test_eval_gate.py
- [x] Integration tests: TestOutstandingDetection, TestEvalGateIntegration

### Remaining
- [ ] Tune prompts based on Langfuse eval results
- [ ] Switch retention to Claude Sonnet 4.5 when API key available

---

## Phase 2: Chatwoot (Omnichannel)

### Infrastructure
- [x] Deploy Chatwoot (4 containers: web, worker, postgres, redis) on port 3010
- [x] Chatwoot API client module (chatwoot/client.py)
- [x] Chatwoot env vars in config.py + .env.example

### Webhook Bridge
- [x] POST /api/webhook/chatwoot endpoint
- [x] Webhook filtering (event, message_type, private, empty)
- [x] Idempotency (in-memory dedup with TTL)
- [x] Echo loop prevention (ignore outgoing messages)
- [x] Decision dispatch: send → public, draft → private note + open, escalate → private note + labels
- [x] Error handling: pipeline error → private note + open for agent

### Testing
- [x] Unit tests: 20 webhook tests (filtering, parsing, idempotency, HTML stripping)
- [x] All tests passing

### Documentation
- [x] Setup guide (services/chatwoot/setup.md, Russian)
- [x] Bot setup script (services/chatwoot/setup_bot.py)

### E2E Verified
- [x] Widget test page (services/chatwoot/test-widget.html)
- [x] send → public message in widget (shipping, gratitude, retention)
- [x] escalate → private note (payment outstanding, death threat)
- [x] HTML stripping for chat display (agent responses use email-style HTML)

### Remaining
- [ ] Website chat widget (Chatwoot JS embed on levhaolam.com)
- [ ] Agent inbox configuration for human escalations
- [ ] WhatsApp channel

---

## Phase 3: Actions + Eval

- [x] Cancel link generation (AES-256-GCM) — done in Phase 1
- [ ] Action tools with HITL (pause, skip, change_address, damage_claim)
- [ ] Side-by-side model comparison experiments in Langfuse
- [ ] A/B prompt testing

---

## Phase 4: Retention + Channels

- [ ] Claude Sonnet 4.5 for retention
- [ ] Personalized retention offers
- [ ] Email channel via Chatwoot
- [ ] Telegram, Facebook Messenger
