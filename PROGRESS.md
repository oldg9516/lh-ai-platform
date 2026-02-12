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

### Data Import
- [x] Import 10 ai_answerer_instructions (v3 prompts) from production
- [x] Import 500 support_threads_data records from production
- [x] database/import.py + database/import_threads.py scripts

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

- [ ] Test all 10 categories with real customer messages
- [ ] Tune prompts based on Langfuse traces
- [ ] Set up Langfuse datasets from historical tickets
- [ ] Run first eval pipeline (safety, tone, accuracy)
- [ ] Add error handling improvements based on live testing
- [ ] Switch retention to Claude Sonnet 4.5 when API key available

---

## Phase 2: Chatwoot (Omnichannel)

- [ ] Deploy Chatwoot (docker-compose)
- [ ] Website chat widget
- [ ] Chatwoot webhook → AI Engine bridge
- [ ] Agent inbox for human escalations
- [ ] WhatsApp channel

---

## Phase 3: Actions + Eval

- [ ] Action tools with HITL (pause, skip, change_address, damage_claim)
- [ ] Cancel link generation (AES-256-GCM)
- [ ] Langfuse eval pipelines (LLM-as-Judge)
- [ ] Side-by-side model comparison experiments
- [ ] A/B prompt testing

---

## Phase 4: Retention + Channels

- [ ] Claude Sonnet 4.5 for retention
- [ ] Personalized retention offers
- [ ] Email channel via Chatwoot
- [ ] Telegram, Facebook Messenger
