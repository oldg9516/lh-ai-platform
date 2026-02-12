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
- [x] database/queries.py (get_instructions, get_customer, save_session, save_message)
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

### Pending — Phase 0 Completion
- [ ] Verify all containers healthy (docker compose ps)
- [ ] Verify Langfuse UI accessible (http://localhost:3100)
- [ ] Verify AI Engine health (curl http://localhost:8000/api/health)
- [ ] Create DB tables in Supabase: chat_sessions, chat_messages
- [ ] Verify ai_answerer_instructions table has data for categories
- [ ] Create Pinecone index "support-examples" with namespaces
- [ ] Test POST /api/chat with a real message
- [ ] Push to GitHub

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
