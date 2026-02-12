# Tech Spec: Architecture Decision Record

## 1. Финальный стек

| Компонент | Решение | Обоснование |
|-----------|---------|-------------|
| **AI Framework** | Agno AgentOS (Apache-2.0) | 37.4k ⭐, built-in tools/knowledge/guardrails/learning, Control Plane |
| **Omnichannel** | Chatwoot (MIT) | 21k+ ⭐, self-hosted, widget + WhatsApp + FB + Email + TG |
| **Eval Lab** | Agenta (MIT) | Self-hosted, test sets, LLM-as-Judge, model comparison |
| **Analytics** | Agno Dash (Apache-2.0) | NL → SQL, self-learning, 6 layers context |
| **Workflows** | n8n (Fair-code) | Уже работает, email pipeline продолжает |
| **Database** | PostgreSQL (Supabase) | Уже работает, все таблицы на месте |
| **Vector Store** | Pinecone (SaaS) | Уже работает, support-examples index |
| **LLM (primary)** | OpenAI GPT-5.1 | 80-90% запросов, low cost |
| **LLM (retention)** | Claude Sonnet 4.5 | Extended thinking для complex cases |
| **LLM (analytics)** | GPT-5.2 | Medium reasoning для SQL generation |
| **Language** | Python 3.12 | Agno SDK, ML ecosystem |
| **Container** | Docker Compose | Self-hosted, single server |
| **Repo** | Monorepo | Все сервисы в одном месте |

---

## 2. Архитектурные решения

### ADR-1: Agno vs Custom agents
**Решение:** Agno AgentOS  
**Альтернативы:** LangChain, custom FastAPI + OpenAI SDK  
**Причины:**
- Built-in tool calling с HITL (needsApproval)
- Learning Machine: self-improving agents
- Control Plane: playground, tracing, evals без кода
- Registry: смена модели одной строкой (GPT → Claude)
- Guardrails as first-class feature
- AgentOS API: единый API для всех агентов

### ADR-2: Chatwoot vs Custom widget
**Решение:** Chatwoot  
**Альтернативы:** Intercom ($$$), Tidio, custom React widget  
**Причины:**
- Self-hosted (MIT license, all data ours)
- 7+ каналов из коробки
- Agent dashboard ready
- Webhook API → easy integration с Agno
- CSAT, SLA, canned responses built-in

### ADR-3: Monorepo vs Microservices repos
**Решение:** Monorepo  
**Причины:**
- Один человек (Gleb) управляет всем
- Shared config (.env), shared scripts
- Проще деплой (одна машина, docker compose up)
- Claude Code работает лучше с одним repo

### ADR-4: Router + Dynamic Agent vs Single Super-Agent
**Решение:** Two-layer (Router → Dynamic Support Agent)  
**Причины:**
- Router: fast (GPT-5.1, no reasoning, ~50ms), cheap
- Support Agent: настраивается per category (model, tools, knowledge)
- Не нужно 10 отдельных агентов — одна factory function
- Легко добавить новую категорию через config

### ADR-5: Model selection per category
**Решение:** Дифференцированный подход  
**Причины:**
- 80-90% запросов = GPT-5.1 (none/low reasoning) = самый дешёвый
- Только retention → Claude Sonnet 4.5 (extended thinking)
- Экономия ~60-70% vs одна модель для всего
- Настраивается в CATEGORY_CONFIG без изменения кода

### ADR-6: Agno HITL vs Custom approval flow
**Решение:** Agno built-in HITL (needsApproval)  
**Причины:**
- Встроено в Agno tool definition
- Рендерится автоматически в виджете
- Не нужно строить custom UI для confirmations
- Audit trail из коробки

### ADR-7: n8n coexistence
**Решение:** n8n email pipeline продолжает работать параллельно  
**Причины:**
- Zero-risk migration: новая система не ломает старую
- Email через n8n, chat через Agno — разные каналы
- Постепенная миграция email → Chatwoot в Phase 4
- n8n остаётся для background jobs, monitoring, alerts

---

## 3. Структура монорепо

```
lev-haolam-ai-platform/
│
├── CLAUDE.md                       # Claude Code project config
├── docker-compose.yml              # Production: все сервисы
├── docker-compose.dev.yml          # Dev: hot reload, debug
├── .env.example                    # Template переменных
├── .gitignore
│
├── services/
│   ├── ai-engine/                  # Agno AgentOS (Python)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                 # Entry point + AgentOS
│   │   ├── config.py               # CATEGORY_CONFIG, env vars
│   │   ├── pipeline.py             # Full message processing pipeline
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # Router Agent
│   │   │   ├── support.py          # Dynamic Support Agent factory
│   │   │   ├── outstanding.py      # Outstanding Detection Agent
│   │   │   ├── eval_gate.py        # Eval Gate Agent
│   │   │   ├── instructions.py     # Dynamic prompt loader
│   │   │   └── config.py           # CATEGORY_CONFIG
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── customer.py         # identify, get_subscription, get_tracking
│   │   │   ├── subscription.py     # pause, skip, change_frequency (HITL)
│   │   │   ├── shipping.py         # track, report_missing
│   │   │   ├── damage.py           # create_claim, request_photos
│   │   │   └── retention.py        # generate_cancel_link (AES-256-GCM)
│   │   ├── knowledge/
│   │   │   ├── __init__.py
│   │   │   └── pinecone_client.py  # Pinecone wrapper
│   │   ├── guardrails/
│   │   │   ├── __init__.py
│   │   │   └── safety.py           # Red lines, language, subscription safety
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py       # Connection pool
│   │   │   └── queries.py          # SQL queries
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py           # FastAPI routes
│   │   └── tests/
│   │       ├── test_router.py
│   │       ├── test_pipeline.py
│   │       └── test_guardrails.py
│   │
│   ├── chatwoot/                   # Phase 2
│   │   ├── docker-compose.chatwoot.yml
│   │   ├── .env.chatwoot
│   │   └── hooks/
│   │       └── webhook_handler.py
│   │
│   ├── eval-lab/                   # Phase 3
│   │   ├── docker-compose.agenta.yml
│   │   ├── .env.agenta
│   │   ├── test-sets/
│   │   └── evaluators/
│   │       ├── safety_eval.py
│   │       ├── tone_eval.py
│   │       └── action_eval.py
│   │
│   └── analytics/                  # Phase 5
│       ├── Dockerfile
│       └── knowledge/
│           ├── tables/
│           ├── queries/
│           └── business/
│
├── shared/
│   ├── database/
│   │   └── migrations/
│   │       ├── 001_chat_sessions.sql
│   │       ├── 002_agent_traces.sql
│   │       └── 003_eval_results.sql
│   └── scripts/
│       ├── export_test_set.py
│       └── sync_instructions.py
│
└── docs/
    ├── 01-PRD.md
    ├── 02-IMPLEMENTATION-PLAN.md
    ├── 03-TECH-SPEC.md
    ├── 04-API-CONTRACT.md
    ├── 05-DATABASE-MIGRATIONS.md
    └── runbooks/
        ├── deploy.md
        └── troubleshooting.md
```

---

## 4. CATEGORY_CONFIG

```python
CATEGORY_CONFIG = {
    "shipping_or_delivery_question": {
        "model": "gpt-5.1",
        "reasoning_effort": "low",
        "tools": ["get_subscription", "track_package"],
        "pinecone_namespace": "shipping",
        "auto_send_phase": 2,
    },
    "payment_question": {
        "model": "gpt-5.1",
        "reasoning_effort": "medium",
        "tools": ["get_subscription", "get_payment_history"],
        "pinecone_namespace": "payment",
        "auto_send_phase": 3,
    },
    "frequency_change_request": {
        "model": "gpt-5.1",
        "reasoning_effort": "low",
        "tools": ["get_subscription", "change_frequency"],
        "pinecone_namespace": "subscription",
        "auto_send_phase": 2,
    },
    "skip_or_pause_request": {
        "model": "gpt-5.1",
        "reasoning_effort": "low",
        "tools": ["get_subscription", "skip_month", "pause_subscription"],
        "pinecone_namespace": "subscription",
        "auto_send_phase": 2,
    },
    "recipient_or_address_change": {
        "model": "gpt-5.1",
        "reasoning_effort": "low",
        "tools": ["get_subscription", "change_address"],
        "pinecone_namespace": "subscription",
        "auto_send_phase": 2,
    },
    "customization_request": {
        "model": "gpt-5.1",
        "reasoning_effort": "low",
        "tools": ["get_subscription", "get_box_contents"],
        "pinecone_namespace": "customization",
        "auto_send_phase": 2,
    },
    "damaged_or_leaking_item_report": {
        "model": "gpt-5.1",
        "reasoning_effort": "low",
        "tools": ["get_subscription", "create_damage_claim", "request_photos"],
        "pinecone_namespace": "damage",
        "auto_send_phase": 3,
    },
    "gratitude": {
        "model": "gpt-5.1",
        "reasoning_effort": "none",
        "tools": [],
        "pinecone_namespace": "gratitude",
        "auto_send_phase": 1,
    },
    "retention_primary_request": {
        "model": "claude-sonnet-4-5",
        "reasoning_effort": "extended",
        "tools": ["get_subscription", "generate_cancel_link", "get_customer_history"],
        "pinecone_namespace": "retention",
        "auto_send_phase": 4,
    },
    "retention_repeated_request": {
        "model": "claude-sonnet-4-5",
        "reasoning_effort": "extended",
        "tools": ["get_subscription", "generate_cancel_link"],
        "pinecone_namespace": "retention",
        "auto_send_phase": 4,
    },
}
```

---

## 5. Docker networking

```
Все сервисы в одной Docker network: ai-platform-net

ai-engine:8000      ← Agno AgentOS API
chatwoot:3000       ← Omnichannel Hub (Phase 2)
eval-lab:4000       ← Agenta UI (Phase 3)
analytics:9000      ← Agno Dash (Phase 5)
n8n:5678            ← Уже работает (external)
postgres:5432       ← Supabase (external, hosted)
```

Сервисы общаются по internal network. Только chatwoot:3000 и ai-engine:8000 exposed наружу.

---

## 6. Environment Variables

```bash
# LLM APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database (Supabase)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
DB_HOST=db.xxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASS=...

# Pinecone
PINECONE_API_KEY=...
PINECONE_INDEX=support-examples

# Agno
AGNO_API_KEY=...  # для Control Plane

# Encryption (для cancel links)
CANCEL_LINK_PASSWORD=4hUQ3WFzA4D2RV6g

# Chatwoot (Phase 2)
CHATWOOT_URL=http://chatwoot:3000
CHATWOOT_API_TOKEN=...
CHATWOOT_ACCOUNT_ID=1

# n8n
N8N_URL=https://n8n.diconsulting.pro
N8N_API_KEY=...
```
