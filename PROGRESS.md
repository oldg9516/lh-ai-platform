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
  - [x] PauseSubscriptionForm (pause_subscription) — slider 1-12 months
  - [x] ChangeFrequencyForm (change_frequency) — select monthly/bi-monthly/quarterly
  - [x] ChangeAddressForm (change_address) — 3 inputs (street, city, country)
  - [x] DamageClaimForm (create_damage_claim) — input + textarea
  - [x] SkipMonthForm (skip_month) — select with upcoming months
- [x] Backend: Direct OpenAI API (bypasses Agno for proper ToolCall event emission):
  - [x] copilot.py полностью переписан: OpenAI streaming + AG-UI ToolCall events
  - [x] HITL tools → AG-UI ToolCallStart/Args/End events → CopilotKit renders forms
  - [x] Read-only tools → executed server-side, results fed back to LLM
  - [x] Tool call loop (max 5 iterations): LLM → tool → result → LLM → response
  - [x] POST /api/copilot/execute-tool — executes HITL-approved tools after user confirmation
  - [x] Pydantic validation + tool_name whitelist (only WRITE_TOOLS allowed)
- [x] Tool result continuation (_tool_result_stream):
  - [x] Detects ToolMessage as LAST message (not any()) in CopilotKit conversation
  - [x] Converts AG-UI messages → OpenAI format (user, assistant+tool_calls, tool results)
  - [x] Generates acknowledgment text via gpt-4.1-mini, streams as AG-UI events
  - [x] Prevents form re-appearance after Confirm/Cancel
- [x] Frontend: Official CopilotKit pattern (useState directly in render callback):
  - [x] Status lifecycle: inProgress → executing → complete
  - [x] `disabled={!isExecuting || loading}` for form controls
  - [x] All 5 forms call /api/copilot/execute-tool on Approve → respond() with result
  - [x] Next.js proxy route: /api/copilot/execute-tool → FastAPI backend
  - [x] .dockerignore for frontend (reduces build context from 1.4GB to ~5MB)
- [x] Audit logging: save_tool_execution() called with requires_approval=true, approval_status=approved
- [x] Mock APIs для демо (Phase 6.1.5)
- [x] 215 tests passing
- [ ] File upload для damage claims (S3/MinIO integration)
- [ ] Интеграция с реальными API (IT dept):
  - [ ] Zoho CRM (pause, skip, frequency change)
  - [ ] Pay API (payment method updates)
  - [ ] Shipping provider API (address validation)

**Коммиты:**
- `e1874f0` Complete HITL end-to-end: direct OpenAI streaming + tool result continuation

### Phase 6.3: Informational Widgets ✅ COMPLETE
- [x] Read-only display widgets (useHumanInTheLoop + auto-respond pattern):
  - [x] TrackingWidget — progress bar (Shipped→In Transit→Out for Delivery→Delivered), carrier info, tracking history timeline, estimated delivery
  - [x] OrderHistoryWidget — subscription badges (Active/Inactive, frequency, start date), recent orders table with tracking numbers
  - [x] BoxContentsWidget — last box details (SKU, shipping date), customization preferences with exclusion badges (No Alcohol, No Honey)
  - [x] PaymentHistoryWidget — payment timeline with amounts/invoices, next payment date, payment method, total amount
- [x] AG-UI protocol for widgets:
  - [x] DISPLAY_TOOL_NAMES set: display_tracking, display_orders, display_box_contents, display_payments
  - [x] FRONTEND_TOOL_NAMES = HITL_TOOL_NAMES | DISPLAY_TOOL_NAMES — unified frontend tool routing
  - [x] READ_TO_DISPLAY mapping: автоматическая инъекция display tools когда агент имеет read tool (e.g. track_package → display_tracking)
  - [x] Display tool OpenAI schemas (customer_email parameter only)
  - [x] Agent system prompt instructions: "After fetching data, call display_* to show it visually"
- [x] Self-fetching widget pattern:
  - [x] Widget receives customer_email via tool args → calls /api/copilot/fetch-data → renders rich UI
  - [x] /fetch-data FastAPI endpoint with READ_ONLY_TOOLS whitelist (get_subscription, get_customer_history, get_payment_history, track_package, get_box_contents)
  - [x] Next.js proxy route: /api/copilot/fetch-data → FastAPI backend
  - [x] Auto-respond after 500ms delay (widget stays visible after status="complete")
- [x] Unified UI library: shadcn/ui (Card, CardHeader, CardTitle, CardDescription, CardContent)
- [x] 215 tests passing

**Коммиты:**
- `90c927b` Phase 6.3: Informational widgets (Tracking, Orders, BoxContents, Payments)

### Phase 6.4: Production Hardening ✅ COMPLETE
- [x] Rate limiting:
  - [x] In-memory RateLimiter class (configurable max_calls + window_seconds)
  - [x] Tool executions: 5 per minute per IP (_tool_rate_limiter)
  - [x] Stream requests: 10 per minute per IP (_stream_rate_limiter)
  - [x] HTTP 429 responses with user-friendly error messages
- [x] Input validation (Pydantic field_validator):
  - [x] Email format validation (RFC 5321, max 254 chars, regex check)
  - [x] Tool name whitelist (lowercase + underscores only, max 50 chars)
  - [x] String args max length (1000 chars)
  - [x] Validation on both /execute-tool and /fetch-data endpoints
- [x] Error handling:
  - [x] OpenAI streaming timeout (30s) via asyncio.wait_for on both _agent_stream and _tool_result_stream
  - [x] Graceful fallback messages on timeout (not crash)
  - [x] HTTP status checking in frontend forms (429 → toast, 5xx → toast)
  - [x] Toast notifications (sonner) on all 5 HITL forms: success, error, rate-limit, network error
  - [x] Toaster component in root layout with richColors + closeButton
- [x] Mobile responsive:
  - [x] Buttons: flex-col sm:flex-row layout (stacked on mobile, row on desktop)
  - [x] Touch targets: min-h-[44px] on all form buttons (WCAG 2.5.5)
- [x] 215 tests passing (1 flaky from LLM non-determinism)
- [ ] Langfuse eval для HITL flows (approval rate, completion time, cancel rate) — deferred
- [ ] Full WCAG 2.1 accessibility audit — deferred

**Коммиты:**
- `6f31b7f` Phase 6.4: Production hardening (timeout, rate limiting, validation, toasts, mobile)

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

### Orchestrator Pattern ✅ COMPLETE
- [x] agents/orchestrator.py:
  - [x] `SupportOrchestrator` class with 7-stage pipeline (replaces monolithic chat() in routes.py)
  - [x] `PipelineContext` dataclass — mutable state through all stages
  - [x] `PipelineResult` dataclass — immutable output
  - [x] Stage 1: `_check_safety()` — red line pre-check, early return if flagged
  - [x] Stage 2: `_classify()` — router + name extraction (parallel via asyncio.gather)
  - [x] Stage 3: `_build_context()` — conversation history + customer metadata injection
  - [x] Stage 4: `_run_agent()` — support agent + outstanding detection (parallel)
  - [x] Stage 5: `_post_process()` — cancel link injection + response assembly
  - [x] Stage 6: `_evaluate()` — eval gate (regex fast-fail + LLM evaluation)
  - [x] Stage 7: `_persist()` — save session, messages, eval to DB (best-effort)
  - [x] Static `process()` method orchestrates all stages
- [x] Update api/routes.py: `chat()` now delegates to `SupportOrchestrator.process()` (310→120 lines)
- [x] All 219 tests passing with orchestrator
- [x] Commit: `3e0f3a1`

### Model Optimization ✅ COMPLETE
- [x] Router: GPT-5.1 → GPT-5-mini (~90% cost reduction, classification accuracy preserved)
- [ ] Eval Gate: GPT-5.1 → Claude Sonnet 4.5 (better judgment) — future
- [ ] Support (retention): GPT-5.1 → Sonnet 4.5 + reasoning — future
- [ ] Benchmarking: eval на golden dataset (338 items) для каждой модели — future

---

## Phase 8: Multi-Agent Specialists + QA Agent ✅ COMPLETE

**См. документацию:**
- [docs/09-AI-AGENT-BEST-PRACTICES-2026.md](docs/09-AI-AGENT-BEST-PRACTICES-2026.md#phase-8-multi-agent-teams)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — детальный анализ Phase 6-10 + Agno Learning Machine

**Архитектурное решение:** Не используем `agno.team.Team` — у нас уже есть рабочий router + orchestrator. Team добавил бы лишний LLM-вызов для routing. Вместо этого: specialist agents + QA agent интегрированы в существующий orchestrator через feature flag.

### Specialist Agents ✅
- [x] `agents/specialists.py` — 4 specialist agent configs + factory:
  - [x] **Billing Specialist** — `payment_question`, `frequency_change_request`, `skip_or_pause_request` (GPT-5.1, 5 tools)
  - [x] **Shipping Specialist** — `shipping_or_delivery_question`, `recipient_or_address_change` (GPT-5.1, 4 tools)
  - [x] **Retention Specialist** — `retention_primary_request`, `retention_repeated_request` (GPT-5.1 + reasoning=medium, 5 tools)
  - [x] **Quality Specialist** — `damaged_or_leaking_item_report`, `customization_request`, `gratitude` (GPT-5.1, 4 tools)
- [x] `CATEGORY_TO_SPECIALIST` reverse lookup — all 10 categories mapped
- [x] `create_specialist_agent(category)` factory — domain-specific role context, broader tool sets, multi-namespace knowledge
- [x] Each specialist has broader tools than single-category agent (superset guarantee)

### QA Agent ✅
- [x] `agents/qa_agent.py` — replaces LLM tier of eval gate in team mode:
  - [x] New decision: `"refine"` — response needs specific improvement, provides feedback
  - [x] `feedback` field — concrete instructions for specialist on what to fix
  - [x] `attempt` parameter — on retry (attempt 2+), no more refine, only send/draft/escalate
  - [x] Regex fast-fail reused from `eval_gate.fast_safety_check()` (no duplication)
  - [x] GPT-5.1 model (same as eval gate)

### Orchestrator Integration ✅
- [x] `agents/orchestrator.py` updated:
  - [x] `PipelineContext` — new fields: `use_team_mode`, `specialist_key`, `attempt`, `qa_feedback`
  - [x] `process()` — accepts `use_team_mode` param, defaults to `settings.team_mode_enabled`
  - [x] Stage 4 (`_run_agent`): branches to `create_specialist_agent()` or `create_support_agent()`
  - [x] Stage 6 (`_evaluate`): branches to `qa_evaluate()` or `evaluate_response()`
  - [x] Retry loop: if QA says "refine" on attempt 1 → append feedback → re-run stages 4-6
  - [x] `_build_result`: team mode metadata (specialist, attempts) in PipelineResult
- [x] Feature flag: `TEAM_MODE_ENABLED=false` in `config.py` (disabled by default)
- [x] Backwards compatible: team_mode=false → identical to Phase 7 behavior

### Tests ✅
- [x] `tests/test_specialists.py` — 22 tests (configs, mapping, factory, tool superset)
- [x] `tests/test_qa_agent.py` — 14 tests (model, regex, prompt builder)
- [x] `tests/test_orchestrator_team.py` — 10 tests (context fields, metadata, feature flag)
- [x] **266 total tests passing** (220 existing + 46 new)
- [x] Commit: `3d661e3`

### Future (not in scope for Phase 8)
- [ ] A/B testing: single-agent vs team (на 10% трафика)
- [ ] Langfuse comparison: resolution rate, latency, quality scores
- [ ] `agno.team.Team` integration if inter-agent coordination is needed (Phase 9+)

---

## Phase 8.5: Dash Analytics Agent + CopilotKit Generative UI ✅ COMPLETE

Replaces custom analytics service (Phase 5) with Agno Dash self-learning data agent. Adds CopilotKit Generative UI for readable markdown/table rendering.

### Dash Analytics Agent ✅
- [x] `services/dash/` — 29 files, Agno Dash-based self-learning data agent:
  - [x] `dash/agent.py` — `OpenAIResponses("gpt-5.2")` + `LearningMachine(mode=LearningMode.AGENTIC)`
  - [x] `dash/context/semantic_model.py` — 9 table schema JSONs loaded into system prompt
  - [x] `dash/context/business_rules.py` — metrics definitions, data quality gotchas, capitalization rules
  - [x] `dash/knowledge/` — table schemas (9 JSONs) + business rules + validated SQL patterns
  - [x] `dash/tools/introspect.py` — `introspect_schema` tool for live DDL inspection
  - [x] `dash/tools/save_query.py` — save validated queries to knowledge base
  - [x] `main.py` — AgentOS app with `_wait_for_db()` retry loop for container startup
  - [x] `scripts/load_knowledge.py` — bulk load knowledge via `Knowledge.insert()`
- [x] Dual DB architecture:
  - [x] `dash-db` (PgVector) — agent state, knowledge base, learnings
  - [x] Supabase (read-only via `analytics_readonly` user) — customer data queries via SQLTools
- [x] Docker: `dash` + `dash-db` containers replace old `analytics` container
- [x] Health check: `GET /health` → 200 OK
- [x] API: `POST /agents/dash/runs` (SSE streaming) — AgentOS auto-generated endpoints
- [x] Knowledge loaded: 9 table schemas + 1 rule set + 1 query file = 11 documents

### CopilotKit Generative UI for Dash ✅
- [x] AG-UI adapter endpoint (`services/ai-engine/api/dash_copilot.py`):
  - [x] Receives AG-UI requests from CopilotKit
  - [x] Forwards to Dash AgentOS via httpx streaming
  - [x] Translates `RunContent` events → `TextMessageContentEvent` (AG-UI protocol)
  - [x] Protocol method handling (`info`, `agent/connect`)
- [x] CopilotKit multi-agent routing:
  - [x] `dash` HttpAgent registered in `route.ts` alongside `default` (support)
  - [x] `DashProviders` component (`lib/dash-providers.tsx`) with `agent="dash"`
  - [x] CopilotSidebar: defaultOpen, "Dash Analytics" branding
- [x] Frontend route groups:
  - [x] `(support)/` — CopilotKit Providers (support agent)
  - [x] `(dash)/` — DashProviders (dash agent)
  - [x] `(dash)/dash/page.tsx` — landing page with quick prompt suggestions
- [x] Removed old `/api/dash` SSE proxy route + custom chat UI
- [x] Both services built and deployed (19 containers)

**Коммиты:**
- `45b0cb9` Phase 8.5: Dash analytics agent + CopilotKit Generative UI

---

## Phase 9: AI Ops & Continuous Learning

**См. документацию:**
- [docs/09-AI-AGENT-BEST-PRACTICES-2026.md](docs/09-AI-AGENT-BEST-PRACTICES-2026.md#priority-3-ai-ops--learning-ongoing)
- [docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md](docs/10-NEW-PHASES-LEARNING-MACHINE-ANALYSIS.md) — детальный анализ Phase 6-10 + Agno Learning Machine (критические находки: Learning Machine НЕ для self-improvement, dual-track strategy)

### Phase 9.1: Dual-Track Learning Mechanism ✅ COMPLETE

**Архитектурное решение:** Agno Learning Machine ≠ self-improvement. Это user memory/personalization. Для реального самообучения нужен custom pipeline. Реализован dual-track подход:
- **Track 1 (Agno LM):** Customer memory — агент помнит клиента между сессиями
- **Track 2 (Custom):** Correction pipeline — human edits → LLM classification → few-shot injection

#### Track 1: Agno Learning Machine (Customer Memory) ✅
- [x] `config.py` — 3 feature flags: `LEARNING_ENABLED`, `LEARNING_FEW_SHOT_ENABLED`, `LEARNING_DB_URL`
- [x] `requirements.txt` — добавлены `sqlalchemy` + `psycopg[binary]` для Agno PostgresDb
- [x] `agents/support.py` — `create_support_agent()` стал `async`, добавлен Learning Machine:
  - [x] `PostgresDb(db_url=settings.learning_db_url)` — direct PostgreSQL для Agno LM
  - [x] `LearningMachine(user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS))`
  - [x] `user_id=customer_email` — память привязана к клиенту
  - [x] Feature-flagged: только при `learning_enabled=True` + email + db_url
- [x] `agents/specialists.py` — `create_specialist_agent()` стал `async`, аналогичные изменения
- [x] `agents/orchestrator.py` — `_run_agent()` передаёт `customer_email` в обе фабрики + `await`

#### Track 2: Correction Learning Pipeline ✅
- [x] `learning/__init__.py` — новый пакет
- [x] `learning/feedback.py` — correction collection + classification:
  - [x] `CorrectionRecord` model (conversation_id, category, ai_response, human_edit, correction_type)
  - [x] `CorrectionClassification` model (type: tone/accuracy/safety/completeness)
  - [x] `save_correction()` — сохранение в `correction_patterns` table
  - [x] `get_recent_corrections()` — последние N corrections по категории
  - [x] `classify_correction()` — LLM classifier (GPT-5-mini) для типизации правок
- [x] `learning/few_shot.py` — few-shot injection:
  - [x] `build_few_shot_instructions()` — строит блок "LEARNING FROM PAST CORRECTIONS" из recent corrections
  - [x] Truncation до 200 символов per example (предотвращает instruction bloat)
  - [x] Injected в `create_support_agent()` и `create_specialist_agent()` (feature-flagged)

#### Chatwoot Correction Webhook ✅
- [x] `api/routes.py` — обработка `message_updated` events:
  - [x] Детекция human edits AI ответов
  - [x] LLM classification → `correction_patterns` table
  - [x] Feature-flagged: только при `learning_few_shot_enabled=True`
- [x] `database/queries.py` — 2 новых helper'а:
  - [x] `get_last_ai_message(session_id)` — последний AI ответ
  - [x] `get_session_category(session_id)` — категория сессии

#### Database ✅
- [x] `services/supabase/init/01-schema.sql` — 2 новые таблицы:
  - [x] `correction_patterns` — human corrections of AI responses (tone, accuracy, safety, completeness)
  - [x] `instruction_updates` — suggested instruction improvements (pending/approved/deployed)

#### Tests ✅
- [x] `tests/test_learning_feedback.py` — 9 tests (CorrectionRecord, CorrectionClassification models)
- [x] `tests/test_learning_few_shot.py` — 8 tests (build_few_shot_instructions, truncation, empty data)
- [x] `tests/test_learning_integration.py` — 14 tests (feature flags, agent factories, orchestrator email passing)
- [x] `tests/test_specialists.py` — обновлены на async (9 tests)
- [x] `tests/test_email_context.py` — обновлены на async (3 tests)
- [x] `tests/test_chatwoot_webhook.py` — обновлен test_ignores_message_updated → test_processes_message_updated
- [x] **290+ tests passing** (31 новых learning tests)
- [x] Commit: `3803393`

#### Feature Flags (все OFF по умолчанию — полная обратная совместимость)
| Flag | Default | Description |
|------|---------|-------------|
| `LEARNING_ENABLED` | false | Agno Learning Machine (customer memory между сессиями) |
| `LEARNING_FEW_SHOT_ENABLED` | false | Few-shot correction injection в instructions |
| `LEARNING_DB_URL` | "" | Direct PostgreSQL URL для Agno LM |
| `PATTERN_MIN_FREQUENCY` | 3 | Min corrections to trigger instruction update suggestion |
| `PATTERN_WINDOW_DAYS` | 7 | Lookback window (days) for pattern detection |

### Phase 9.2: Eval-Driven Instruction Updates ✅
- [x] `learning/pattern_detector.py`: detect recurring correction patterns (3+ per category/type in 7-day window)
- [x] `pattern_detector.suggest_instruction_fix()`: GPT-5-mini generates `InstructionFix(issue_pattern, suggested_fix)` from examples
- [x] `pattern_detector.run_pattern_analysis()`: orchestrates detect → suggest → save to `instruction_updates`
- [x] `database/queries.py`: 5 CRUD functions for `instruction_updates` (get_instruction_updates, get_instruction_update, save_instruction_update, update_instruction_status, get_deployed_updates)
- [x] `api/learning_api.py`: 6 admin endpoints — list, get, approve, reject, deploy, analyze
- [x] `agents/instructions.py`: deployed fixes injected as "DEPLOYED INSTRUCTION IMPROVEMENTS" block
- [x] `learning/feedback.py`: threshold check after correction save (`_check_pattern_threshold`)
- [x] `config.py`: `pattern_min_frequency=3`, `pattern_window_days=7`
- [x] Tests: 49 new tests (test_pattern_detector.py, test_learning_api.py, test_learning_integration.py additions)

#### Admin API Endpoints (prefix: `/api/learning`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/instruction-updates` | List updates (optional ?status=&category=) |
| GET | `/instruction-updates/{id}` | Get single update with examples |
| POST | `/instruction-updates/{id}/approve` | pending → approved |
| POST | `/instruction-updates/{id}/reject` | pending/approved → rejected |
| POST | `/instruction-updates/{id}/deploy` | approved → deployed |
| POST | `/instruction-updates/analyze` | Trigger pattern analysis on demand |

### AI Ops Dashboard (TODO)
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

### Continuous Evaluation (TODO)
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
