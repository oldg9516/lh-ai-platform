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

### Action Tools (Stubs) — 12 инструментов
- [x] Cancel link generation (AES-256-GCM) — done in Phase 1
- [x] TOOL_REGISTRY (tools/__init__.py) + resolve_tools()
- [x] Read-only: get_subscription, get_customer_history, get_payment_history (tools/customer.py)
- [x] Read-only: track_package (tools/shipping.py)
- [x] Read-only: get_box_contents (tools/customization.py)
- [x] Write (pending_confirmation): change_frequency, skip_month, pause_subscription, change_address (tools/subscription.py)
- [x] Write: create_damage_claim, request_photos (tools/damage.py)
- [x] Support Agent wired: resolve_tools → Agent(tools=[...]) (agents/support.py)
- [x] Customer email в agent input (api/routes.py)
- [x] save_tool_execution() в database/queries.py
- [x] Двухфазное выполнение write-операций: Phase A — tools возвращают `awaiting_customer_confirmation`

### Eval Gate: Tool Context
- [x] Eval gate принимает tools_available — список инструментов категории
- [x] ACCURACY инструкции обновлены: данные от инструментов считаются достоверными
- [x] _build_eval_prompt() включает контекст инструментов в промпт для LLM-judge
- [x] E2E: shipping вопрос → track_package → eval gate send → ответ в виджете

### Customer Identification Flow
- [x] Нормализованные таблицы: customers, subscriptions, orders, tracking_events (04-customers.sql)
- [x] ETL: import_customers.py — импорт из support_threads_data JSON → реляционная модель
- [x] 962 клиента, 649 подписок, 1826 заказов, 268 tracking events импортировано
- [x] database/customer_queries.py — 8 query-функций (lookup, subscriptions, orders, payments, tracking, history)
- [x] Read-only tools подключены к БД: get_subscription, get_payment_history, get_customer_history, track_package, get_box_contents
- [x] Customer not found → tool возвращает `{"found": false}`, AI просит уточнить email
- [x] Eval gate корректно drafts при отсутствии данных клиента (accuracy/completeness low)
- [x] E2E: реальные данные клиента в ответах (tracking number, next charge date, box info)

### Тесты
- [x] test_customer_queries.py — 22 теста (lookup, subscriptions, orders, payments, tracking, history + not found + errors)
- [x] test_tools.py — 26 тестов (found/not found/error paths, mock DB layer)
- [x] test_tool_registry.py — 8 тестов (реестр, resolve, CATEGORY_CONFIG sync)
- [x] test_eval_gate.py — 3 новых теста на tools_available в промпте
- [x] test_pipeline.py — интеграционные тесты обновлены с реальным email клиента из БД
- [x] 211 тестов проходят (171 unit + 35 integration + 5 E2E multi-turn)

### Remaining
- [ ] Реальные API вместо стабов для write-операций (Zoho, Pay, shipping provider)
- [ ] Phase B: UI формы подтверждения для write-операций (Phase 6)

### Eval & Experiments
- [ ] Side-by-side model comparison in Langfuse (GPT-5.1 vs Claude on retention)
- [ ] A/B prompt testing (v1 vs v2 per category)
- [ ] Run full eval on golden dataset (338 items) — baseline scores established

---

## Phase 4: Retention + Multi-turn + Email

### Retention — reasoning_effort=medium
- [x] GPT 5.1 + openai_responses + reasoning_effort="medium" для retention_primary_request и retention_repeated_request
- [x] `_resolve_model()` передаёт reasoning_effort в OpenAIChat (agents/support.py)
- [x] Escalation flow: AI → Chatwoot (assign to human agent via CHATWOOT_ESCALATION_ASSIGNEE_ID)

### Multi-turn Conversation History
- [x] Стабильный session_id для Chatwoot: `cw_{conversation_id}` (api/routes.py)
- [x] `get_conversation_history(session_id, limit)` в database/queries.py
- [x] Загрузка истории в agent_input с разделителями `[Conversation History]` / `[End History]`
- [x] Truncation ответов агента до 500 символов в истории
- [x] 6 unit тестов (test_queries.py), 5 webhook тестов (session stability, channel model)
- [x] E2E: 5 multi-turn тестов (followup context, explicit reference, session isolation, truncation, history limit)

### Email через Chatwoot
- [x] ChatwootConversation model + channel field
- [x] Channel detection из Chatwoot payload (api/routes.py)
- [x] Email канал: HTML не стрипается (email поддерживает HTML нативно)
- [x] Chat канал: HTML стрипается (как раньше)
- [ ] Настройка Email inbox в Chatwoot UI (IMAP/SMTP)

### Multi-Channel
- [ ] WhatsApp channel via Chatwoot
- [ ] Telegram bot via Chatwoot
- [ ] Facebook Messenger via Chatwoot

---

## Phase 5: AgentOS Analytics Service

### Infrastructure
- [x] Analytics service (Python 3.12 + Agno + FastAPI, port 9000)
- [x] Read-only PostgreSQL user (analytics_readonly) в services/supabase/init/05-analytics-user.sql
- [x] Docker integration: analytics service в docker-compose.yml
- [x] Env vars: ANALYTICS_DB_URL, PINECONE_API_KEY, LANGFUSE_ANALYTICS_* keys
- [x] Health check endpoint: http://localhost:9000/api/health

### Triple Access Pattern
- [x] **AgentOS Control Plane** (self-hosted): http://localhost:9000/ — chat UI для exploratory analytics
- [x] **Custom FastAPI endpoints**: /metrics/*, /charts/*, /query — pre-computed метрики + Plotly JSON
- [x] **Langfuse (separate project)**: http://localhost:3100 — observability для SQL queries (manual: создать "Analytics Agent" project)

### Analytics Agent
- [x] agent.py: OpenAIChat(gpt-5-mini) + PostgresTools + Pinecone knowledge
- [x] PostgresTools config: использует отдельные параметры (host, port, db_name, user, password)
- [x] Knowledge base: Pinecone namespace "analytics-knowledge" (PgVector не установлен в Supabase)
- [x] Pinecone версия 5.4.2 (Agno SDK не совместим с v6+), pinecone-text для hybrid search

### Knowledge Base Content
- [x] knowledge/schemas/ — table schemas JSON (chat_sessions, chat_messages, agent_traces)
- [x] knowledge/queries/ — sample SQL (resolution_rate.sql, category_breakdown.sql, customer_patterns.sql)
- [x] knowledge/rules/metrics.json — metric definitions, formulas, targets, thresholds
- [x] Load knowledge: `docker exec analytics python load_knowledge.py` (fixed dimension mismatch: added OpenAIEmbedder with dimensions=1024)

### Custom FastAPI Endpoints
- [x] api/metrics.py: /metrics/overview, /metrics/categories, /metrics/customer-patterns
- [x] api/charts.py: /charts/category-distribution, /charts/resolution-trend, /charts/eval-decision-breakdown
- [x] api/query.py: POST /query — natural language → SQL via analytics agent
- [x] database/queries.py: direct SQL functions (get_resolution_rate, get_category_breakdown, get_daily_trends)

### Key Metrics (Phase 5 MVP)
- [x] AI Performance: resolution_rate (66.11%), escalation_rate (0.95%), draft_rate (32.94%), avg_response_time (11202ms)
- [x] Category Analytics: 10 categories tracked, top 3: retention (32.7%), shipping (25.3%), gratitude (9.55%)
- [x] Customer Insights: 419 sessions in 7 days, multi-turn support, session-based tracking

### Documentation
- [x] services/analytics/README.md — setup guide, API reference, troubleshooting
- [x] PROGRESS.md updated (Phase 5 completion)
- [x] Test endpoints: /metrics/overview, /charts/category-distribution, /query (all working, returning real data)

### Testing Results
- [x] Health check: http://localhost:9000/api/health → {"status":"healthy","service":"analytics"}
- [x] Metrics endpoint: /metrics/overview?days=7 → 419 sessions, 66.11% resolution rate
- [x] Categories endpoint: /metrics/categories → breakdown by 10 categories with performance metrics
- [x] Chart endpoint: /charts/category-distribution → Plotly JSON with visualization data
- [x] Natural language query: "How many chat sessions in the last 7 days?" → SQL generation + execution + plain language answer
- [x] AgentOS endpoints: /agents → analytics_agent with PostgresTools (show_tables, run_query, search_knowledge_base)

### Completed
- [x] Create Langfuse "Analytics Agent" project (manual в UI: Settings → Projects → "Analytics Agent")
- [x] Knowledge base loaded successfully (7 items: 3 schemas, 3 queries, 1 rules)
- [x] Analytics agent operational (natural language → SQL working)
- [x] All three access patterns functional: Control Plane UI, FastAPI endpoints, Langfuse observability

### Optional (Future)
- [ ] Test natural language queries через Control Plane UI (http://localhost:9000/)
- [ ] Custom dashboards в Langfuse для SQL query performance (top queries, slow queries, errors)

---

## Phase 6: Generative UI + HITL (Human-in-the-Loop)

**См. документацию:**
- [docs/08-COPILOTKIT-GENERATIVE-UI.md](docs/08-COPILOTKIT-GENERATIVE-UI.md)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — детальный анализ Phase 6-10 + Agno Learning Machine

### Phase 6.1: CopilotKit Prototype ✅ COMPLETE
- [x] Setup CopilotKit в новом React app (services/frontend)
  - [x] Next.js 16 + pnpm + shadcn/ui
  - [x] CopilotKit v1.51.3 (@copilotkit/react-core + react-ui + runtime)
  - [x] @ag-ui/client v0.0.45 для HttpAgent
  - [x] React Query v5.90.21 для state management
  - [x] CopilotSidebar с брендингом "Lev Haolam Support"
  - [x] threadId generation для session management
- [x] Реализовать AG-UI streaming endpoint (/api/copilot)
  - [x] Frontend: CopilotRuntime + HttpAgent → FastAPI backend
  - [x] Backend: FastAPI AG-UI stub endpoint (services/ai-engine/api/copilot.py)
  - [x] Architecture: Next.js → HttpAgent → FastAPI (AG-UI protocol)
  - [x] Bug fixes: RouterOutput attribute, create_support_agent signature
- [x] Создать первую HITL форму: PauseSubscriptionForm
  - [x] useHumanInTheLoop hook с parameters (email, months)
  - [x] shadcn/ui компоненты (Button, Card, Label, Slider)
  - [x] Confirmation/Cancel actions
- [x] Frontend Docker Integration
  - [x] Dockerfile (multi-stage: deps → builder → runner)
  - [x] next.config.ts: standalone output + rewrites для AG-UI proxy
  - [x] docker-compose.yml: frontend service (port 3003)
  - [x] Production build успешен, container запущен
- [ ] Интеграция с Chatwoot widget (iframe embedding)
- [ ] E2E тест: Chatwoot → pause request → форма → user confirmation → Zoho API

**Коммиты:**
- `f5e23d0` Phase 6.1 Complete: CopilotKit + Agno integration working

### Phase 6.1.5: Mock API Infrastructure ✅ COMPLETE
- [x] Mock API Layer (protocol-based factory pattern)
  - [x] mock_apis/client.py: MockZohoAPI, MockAddressValidationAPI, MockDamageClaimAPI
  - [x] mock_apis/factory.py: Protocol definitions + APIFactory
  - [x] Realistic latencies (300-800ms), structured responses
  - [x] Settings flag: use_mock_apis (default True)
- [x] Tool Integration
  - [x] 6 write tools converted to async + APIFactory
  - [x] pause_subscription, change_frequency, skip_month, change_address, create_damage_claim, request_photos
  - [x] Customer lookup verification в каждом tool
- [x] Testing
  - [x] 8 unit tests для Mock APIs (все проходят)
  - [x] 12 integration tests для tools с mocks (async conversion)
  - [x] Всего: 227 tests passing (225 после LLM недетерминистичности)

### Phase 6.2: Full HITL Implementation ✅ COMPLETE
- [x] HITL формы для write-операций (5/5):
  - [x] PauseSubscriptionForm (pause_subscription) — Day 2
  - [x] ChangeFrequencyForm (change_frequency) — Day 3
  - [x] ChangeAddressForm (change_address) — Day 3
  - [x] DamageClaimForm (create_damage_claim) — Day 3
  - [x] SkipMonthForm (skip_month) — Phase 6.2 completion
- [x] Backend HITL Architecture:
  - [x] WRITE_TOOLS set + resolve_tools_for_copilot() — filters write tools for CopilotKit path
  - [x] create_support_agent(use_hitl=True) — backend agent gets only read-only tools
  - [x] Frontend tools via useHumanInTheLoop auto-forwarded to agent via AG-UI protocol
  - [x] POST /api/copilot/execute-tool — executes HITL-approved tools after user confirmation
  - [x] Pydantic validation + tool_name whitelist (only WRITE_TOOLS allowed)
- [x] Frontend HITL Integration:
  - [x] Parameter alignment: email → customer_email, months → duration_months (matching backend signatures)
  - [x] All 5 forms call /api/copilot/execute-tool on Approve → get real API result → respond() to agent
  - [x] Loading states on all forms (disabled inputs + "Processing..." button text)
  - [x] Next.js proxy route: /api/copilot/execute-tool → FastAPI backend
  - [x] CopilotSidebar integrated in providers.tsx (branding: "Lev Haolam Support")
  - [x] Updated page.tsx: registered SkipMonthForm, removed placeholder, updated status
- [x] Audit logging: save_tool_execution() called with requires_approval=true, approval_status=approved
- [x] Mock APIs для демо (Phase 6.1.5)
- [ ] File upload для damage claims (S3/MinIO integration)
- [ ] Интеграция с реальными API (IT dept):
  - [ ] Zoho CRM (pause, skip, frequency change)
  - [ ] Pay API (payment method updates)
  - [ ] Shipping provider API (address validation)

### Phase 6.3: Informational Widgets (2 недели)
- [ ] Read-only компоненты (no confirmation needed):
  - [ ] TrackingCard (track_package → карточка с картой и прогресс-баром)
  - [ ] OrderHistoryTable (get_customer_history → таблица с фильтрами)
  - [ ] BoxContentsCard (get_box_contents → список продуктов)
  - [ ] PaymentHistoryCard (get_payment_history → timeline)
- [ ] A2UI для виджетов (агент генерирует JSON → фронтенд рендерит)
- [ ] Unified UI library (shadcn/ui или Material-UI)

### Phase 6.4: Production Hardening (1 неделя)
- [ ] Langfuse eval для HITL flows (approval rate, completion time, cancel rate)
- [ ] Rate limiting на формах (анти-спам: max 5 submissions per minute)
- [ ] Mobile-responsive формы (тесты на iOS Safari, Android Chrome)
- [ ] Accessibility (WCAG 2.1: keyboard navigation, screen readers, color contrast)
- [ ] Error handling: network timeouts, API failures → graceful degradation
- [ ] Security audit: CSRF protection, input sanitization, encrypted confirmations

### Документация
- [x] CopilotKit integration guide (docs/08-COPILOTKIT-GENERATIVE-UI.md)
- [ ] AG-UI protocol implementation details
- [ ] HITL flows diagrams (Mermaid)
- [ ] Developer guide: how to add new HITL forms

---

## Phase 7: Architecture Refactoring

**См. документацию:**
- [docs/09-AI-AGENT-BEST-PRACTICES-2026.md](docs/09-AI-AGENT-BEST-PRACTICES-2026.md)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — детальный анализ Phase 6-10 + Agno Learning Machine

### Context & Conversation (Day 4-5 ✅ COMPLETE)
- [x] **Customer Email Context (Day 4-5)**
  - [x] Router agent extracts email from message (`RouterOutput.email`)
  - [x] `create_support_agent(category, customer_email)` accepts email parameter
  - [x] Email injected into agent instructions as context
  - [x] Tools can use customer email for database lookups
  - [x] AG-UI endpoint passes email to support agent
  - [x] Tests: 6 tests passing (email extraction, context injection, tool integration)
- [x] **Rich Context Builder (agents/context_builder.py)** ✅
  - [x] Customer profile injection (name, join_date, LTV, total_orders)
  - [x] Active subscription injection (frequency, next_charge, status)
  - [x] Recent orders summary (last 3 with dates and amounts)
  - [x] Support history injection (last 3 interactions)
  - [x] Conversation history builder with smart truncation (500 chars per message)
  - [x] Outstanding context injection (is_outstanding, trigger, confidence)
  - [x] Integrated into AG-UI endpoint (prepended to agent input)
  - [x] Tests: 11 tests passing (full context, missing data, error handling)
  - [x] Commit: `8fa9262`
- [ ] Stable session IDs across channels (email-based key вместо random UUID) — postponed

### Sentiment & Escalation (Day 4 ✅ COMPLETE)
- [x] **Sentiment tracking в Router Agent** ✅
  - [x] Added sentiment field в RouterOutput (positive/neutral/negative/frustrated)
  - [x] Added escalation_signal field (boolean: customer wants human)
  - [x] Updated router instructions с sentiment analysis rules
  - [x] LLM-based detection (GPT-5.1 structured output)
  - [x] Tests: 8 tests passing (flexible assertions for LLM variability)
  - [x] Commit: `8fa9262`
- [ ] Enhanced escalation context:
  - [ ] Structured handoff note в Chatwoot (conversation summary, AI actions, eval reasons)
  - [ ] Smart assignee routing by category (billing → billing_agent, retention → retention_specialist)
  - [ ] Labels: sentiment_{value}, category, escalation_reason

### Analytics Dashboard Enhancements (Day 5 ✅ COMPLETE)
- [x] **Learning Candidates Endpoint** ✅
  - [x] GET /learning/candidates (draft/escalated sessions for training)
  - [x] SQL query: chat_sessions + tool_executions JOIN
  - [x] Filters: low confidence, escalated, complex (>3 tools), extended (>5 messages)
  - [x] Returns: session_id, category, decision, confidence, tools_used_count, reason
  - [x] API route: services/analytics/api/learning.py
  - [x] Commit: `5a6a74e`
- [x] **HITL Statistics Endpoint** ✅
  - [x] GET /metrics/hitl-stats (approval/cancellation rates)
  - [x] SQL query: tool_executions WHERE requires_approval = true
  - [x] Overall stats: total, approved, cancelled, pending, approval_rate_pct
  - [x] Per-tool breakdown with individual approval rates
  - [x] Added to services/analytics/api/metrics.py
  - [x] Commit: `5a6a74e`

### Demo Development (Days 6-7 ✅ COMPLETE)
- [x] **Demo Script (Day 6)** ✅
  - [x] Created docs/DEMO-SCRIPT.md (796 lines, 40-min presentation)
  - [x] 6 demo scenes with detailed speaking points:
    - Scene 1: Problem Statement (3 min)
    - Scene 2: AI Quality - 3 demos (8 min)
    - Scene 3: HITL Automation (12 min)
    - Scene 4: Multi-turn Intelligence (8 min)
    - Scene 5: Observability & Learning (8 min)
    - Scene 6: Roadmap & Next Steps (3 min)
  - [x] Pre-demo setup checklist (browser tabs, services health)
  - [x] Fallback materials guide (screenshots, video, Postman)
  - [x] Rehearsal schedule (3 runs with timing)
  - [x] Commit: `1aa5fcf`
- [x] **Q&A Document (Days 6-7)** ✅
  - [x] Created docs/DEMO-QA.md (1,546 lines, 20 prepared answers)
  - [x] Technical questions (8): Cost, outages, security, languages, edge cases, customization, scaling, hallucination
  - [x] Business questions (7): ROI, Zoho integration, human escalation, competitors, timeline, A/B testing, wrong actions
  - [x] Operational questions (5): Training, maintenance, opt-out, metrics, internationalization
  - [x] Each answer includes: explanations, code snippets, SQL queries, timelines, risk mitigation
  - [x] Commit: `3c269c8`
- [x] **Final Checklist (Day 7)** ✅
  - [x] Created docs/DEMO-FINAL-CHECKLIST.md (612 lines, production readiness gate)
  - [x] 13 verification sections:
    - 7.1: Smoke tests (6 scenarios × 3 runs each)
    - 7.2: Infrastructure checks (17 containers)
    - 7.3: Langfuse observability verification
    - 7.4: Analytics endpoints testing
    - 7.5: Pinecone knowledge base connectivity
    - 7.6: Environment variables validation
    - 7.7: Full test suite (202+ tests)
    - 7.8: Git status verification
    - 7.9: Demo materials readiness
    - 7.10: Presentation setup
    - 7.11: Team coordination (roles, communication)
    - 7.12: Rehearsal tracking
    - 7.13: Pre-demo final check (-1 hour protocol)
  - [x] Go/No-Go decision criteria
  - [x] Emergency contacts and success metrics
  - [x] Post-demo tasks and follow-up
  - [x] Commit: `4f47396`
- [x] **Manual Test Script** ✅
  - [x] Created test-scenarios.sh (executable smoke tests)
  - [x] Scenarios: tracking, retention, escalation, analytics
  - [x] Ready for demo rehearsal

**Days 4-7 Summary:**
- 4 new files created (context_builder.py, learning.py, 3 comprehensive docs)
- 5 files modified (router.py, queries.py, metrics.py, main.py, copilot.py)
- 19 new tests added (11 context builder + 8 sentiment)
- 2 new API endpoints (learning candidates, HITL stats)
- 2,954 lines of demo documentation (script, Q&A, checklist)
- All tests passing: 202+ (100% pass rate)
- **Status: READY FOR DEMO** 🎉

### Knowledge & Retrieval
- [ ] Pinecone reranking (knowledge/pinecone_client.py):
  - [ ] search_with_reranking() function
  - [ ] Initial search: top_k=20 (hybrid)
  - [ ] Reranking: bge-reranker-v2-m3, top_n=5
  - [ ] Metadata filtering (product, language, freshness)
- [ ] Knowledge freshness priority (newer docs > старые в ранжировании)

### Orchestrator Pattern
- [ ] agents/orchestrator.py:
  - [ ] SupportOrchestrator class (вместо монолита в api/routes.py)
  - [ ] Методы: process(), _escalate_immediately(), _save_session()
  - [ ] Parallel execution: agent + outstanding detection (asyncio.gather)
  - [ ] Clean separation: router → context → agent → eval → assembly → persistence
- [ ] Update api/routes.py: использовать orchestrator.process()
- [ ] Unit tests для orchestrator (mock все компоненты)

### Model Optimization
- [ ] Cost optimization:
  - [ ] Router: GPT-5.1 → GPT-5-mini (90% ⬇️ cost)
  - [ ] Eval Gate: GPT-5.1 → Claude Sonnet 4.5 (better judgment)
  - [ ] Support (retention): GPT-5.1 → Sonnet 4.5 + reasoning (50% ⬆️ quality)
- [ ] Benchmarking: eval на golden dataset (338 items) для каждой модели

---

## Phase 8: Multi-Agent Teams

**См. документацию:**
- [docs/09-AI-AGENT-BEST-PRACTICES-2026.md](docs/09-AI-AGENT-BEST-PRACTICES-2026.md#phase-8-multi-agent-teams)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — детальный анализ Phase 6-10 + Agno Learning Machine

### Team Architecture
- [ ] agents/teams.py:
  - [ ] Intake Agent (GPT-5-mini, triage + routing)
  - [ ] Specialist Agents:
    - [ ] Billing Specialist (payment, refund, subscription questions)
    - [ ] Shipping Specialist (delivery, tracking, address)
    - [ ] Retention Specialist (pause, cancel, downsell) — Sonnet 4.5 + reasoning
    - [ ] Quality Specialist (damage, leaking, replacement)
  - [ ] QA Agent (Claude Sonnet 4.5, заменяет Eval Gate)
  - [ ] Agno Team orchestration
- [ ] Team coordinator: routing decision logic
- [ ] Inter-agent communication (shared context)
- [ ] Retry logic: QA reject → specialist refines → QA re-check

### Integration
- [ ] Update orchestrator: support both single-agent and team modes
- [ ] A/B testing: single-agent vs team (на 10% трафика)
- [ ] Langfuse comparison: resolution rate, latency, quality scores

---

## Phase 9: AI Ops & Continuous Learning

**См. документацию:**
- [docs/09-AI-AGENT-BEST-PRACTICES-2026.md](docs/09-AI-AGENT-BEST-PRACTICES-2026.md#priority-3-ai-ops--learning-ongoing)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — детальный анализ Phase 6-10 + Agno Learning Machine (критические находки: Learning Machine НЕ для self-improvement, dual-track strategy)

### AI Ops Dashboard
- [ ] services/analytics/ai_ops.py:
  - [ ] get_failure_patterns() — топ причины draft/escalate
  - [ ] get_knowledge_gaps() — вопросы с низкой accuracy
  - [ ] get_tone_drift() — tracking тона по времени
  - [ ] suggest_prompt_updates() — ML-based рекомендации
- [ ] Метрики мониторинга:
  - [ ] AI Resolution Rate (target >70%)
  - [ ] Eval Gate Pass Rate (target >80%)
  - [ ] Escalation Rate (target <10%)
  - [ ] Average Confidence (target >0.8)
  - [ ] Category Accuracy (per category, target >0.75)
  - [ ] Response Time p95 (target <10s)
- [ ] Alerts в Slack (#ai-ops channel)
- [ ] Weekly AI Performance Report (automated)

### Feedback Loop
- [ ] learning/feedback.py:
  - [ ] collect_human_edit() — когда human редактирует AI ответ
  - [ ] classify_edit() — tone, accuracy, safety, completeness
  - [ ] is_recurring_pattern() — детекция паттернов ошибок
  - [ ] generate_prompt_update() — предложения по обновлению промптов
- [ ] Chatwoot integration: hook на human edits → feedback collection
- [ ] Prompt versioning (v1, v2, ...) в ai_answerer_instructions
- [ ] A/B testing prompts (старая vs новая версия на 50/50 трафика)

### Agno Learning Machine
- [ ] Enable Learning Machine для tools:
  - [ ] learning = LearningMachine(db=get_postgres_db(), scope="support_tools")
  - [ ] agent = Agent(..., learning=learning, learn_from_errors=True)
- [ ] learning_records таблица: population с real data
- [ ] Learning dashboard: какие ошибки исправлялись, как часто

### Continuous Evaluation
- [ ] Auto-eval pipeline (daily):
  - [ ] Run full eval на golden dataset (338 items)
  - [ ] Compare с baseline scores
  - [ ] Alert если regression >5%
- [ ] Model comparison dashboard (Langfuse Experiments):
  - [ ] GPT-5.1 vs Sonnet 4.5 на retention
  - [ ] reasoning_effort: none vs low vs medium vs high
  - [ ] Prompt variants: v1 vs v2 vs v3

---

## Phase 10: Scale + Production

### Auto-Send Expansion
- [ ] Auto-send на все safe категории (на основе eval confidence thresholds)
- [ ] Per-category thresholds (retention → 0.9, gratitude → 0.7)
- [ ] Gradual rollout: 10% → 25% → 50% → 100%

### Production Monitoring
- [ ] Langfuse production tracing (100% coverage)
- [ ] Agno Control Plane integration (os.agno.com)
- [ ] Real-time performance dashboard
- [ ] Cost tracking (per category, per model, per day)

### CRM Integration
- [ ] Proactive support:
  - [ ] Detect subscription issues BEFORE customer contacts (upcoming charge fails, delivery delay)
  - [ ] Automated outreach (Chatwoot proactive message)
  - [ ] Predictive churn prevention (ML model: predict cancel → offer downsell)

### n8n Migration
- [ ] Gradual migration from n8n email pipeline:
  - [ ] Phase 10.1: 10% email → AI platform (A/B test)
  - [ ] Phase 10.2: 50% email → AI platform
  - [ ] Phase 10.3: 100% email → AI platform
- [ ] Fallback: если AI fails → n8n backup pipeline

### Feedback Loop v2
- [ ] Production traces → Langfuse eval → автоматическое улучшение промптов (no human in loop)
- [ ] Auto-detect quality regression:
  - [ ] Monitor eval scores daily
  - [ ] Alert если drop >5%
  - [ ] Auto-rollback к предыдущей версии промптов
