# Lev Haolam — AI Support Chat Platform
## Архитектура системы (Internal — с технологиями)

---

## 1. Что мы строим

Интеллектуальная платформа живого чата для клиентской поддержки Lev Haolam, которая:

- **Общается с клиентами в реальном времени** через чат-виджет на сайте, WhatsApp, Facebook, Email — из единого центра
- **Автоматически понимает и классифицирует** запросы клиентов (10 категорий: отмена, пауза, доставка, повреждения и т.д.)
- **Выполняет действия** — пауза подписки, смена адреса, пропуск месяца, создание damage claim — с подтверждением клиента
- **Учится и улучшается** — система накапливает знания и паттерны, становясь точнее с каждым разговором
- **Оценивает качество** — автоматическая оценка ответов, сравнение моделей, A/B тестирование на исторических данных
- **Даёт аналитику** — "сколько тикетов обработал AI?", "какая категория самая проблемная?" — вопрос на естественном языке → ответ с графиками

### Чем отличается от текущей системы

| | Текущая система (n8n email pipeline) | Новая платформа (live chat) |
|---|---|---|
| Канал | Только email (Zoho) | Чат на сайте + WhatsApp + Facebook + Email |
| Скорость ответа | Минуты-часы (draft → review → send) | Секунды (real-time) |
| Действия | GPT-5.1 пишет текст, человек выполняет | AI выполняет действия сам (с подтверждением) |
| Обучение | Статичные промпты в ai_answerer_instructions | Agno Learning Machine: каждый разговор улучшает систему |
| Аналитика | SQL запросы вручную в Supabase | Agno Dash: вопрос → insight |
| Масштаб | 10 категорий, 1 auto-send | 10+ категорий, все auto-capable |

---

## 2. Архитектура: 5 сервисов

Система состоит из 5 независимых сервисов, каждый в своём Docker-контейнере.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          КЛИЕНТ                                     │
│                                                                     │
│   Сайт (виджет)    WhatsApp    Facebook    Email    Telegram        │
│        │               │           │         │          │           │
└────────┼───────────────┼───────────┼─────────┼──────────┼───────────┘
         │               │           │         │          │
         ▼               ▼           ▼         ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│     СЕРВИС 1: CHATWOOT (open-source, self-hosted)                   │
│     Omnichannel Hub — Единый центр коммуникаций                     │
│     https://github.com/chatwoot/chatwoot                            │
│                                                                     │
│   • Все каналы в одном окне для агентов                             │
│   • Готовый виджет чата (JS embed на сайт)                         │
│   • Автоматическая маршрутизация на AI или человека                 │
│   • Webhook API → отправляет сообщения в Agno                      │
│   • Handoff: AI → человек (бесшовная передача)                      │
│   • CSAT, теги, SLA, canned responses                               │
│                                                                     │
│   Docker: chatwoot/chatwoot:latest | Port: 3000                     │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Webhook API
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│     СЕРВИС 2: AGNO AgentOS (open-source, Apache-2.0)                │
│     AI Engine — Ядро AI-системы                                     │
│     https://github.com/agno-agi/agno                                │
│                                                                     │
│   ┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│   │   Router     │    │  Support Agent   │    │  AgentOS         │  │
│   │   Agent      │───►│  (динамический)  │    │  Control Plane   │  │
│   │             │    │                  │    │  (os.agno.com)   │  │
│   │ GPT-5.1     │    │ GPT-5.1 / Claude │    │                  │  │
│   │ reasoning:  │    │ per category     │    │ • Chat/Playground│  │
│   │ none        │    │                  │    │ • Трейсинг      │  │
│   │ ~50ms       │    │ Agno Tools       │    │ • Сессии        │  │
│   │ Structured  │    │ Agno Knowledge   │    │ • Memory viewer  │  │
│   │ Output      │    │ Agno Guardrails  │    │ • Studio (visual)│  │
│   └─────────────┘    └──────────────────┘    │ • Evals          │  │
│                                              │ • Version control│  │
│   ┌────────────────────────────────────┐     └──────────────────┘  │
│   │    Agno Learning Machine           │                           │
│   │                                    │     FastAPI runtime:      │
│   │ • User profiles (persist)          │     50+ endpoints         │
│   │ • Memories (накапливаются)         │     SSE streaming         │
│   │ • Cross-user learnings (transfer)  │     JWT + RBAC            │
│   │ • learning=True (одна строка)      │     MCP server            │
│   └────────────────────────────────────┘     A2A support           │
│                                                                     │
│   Docker: python + agno SDK | Port: 8000                            │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌──────────────────┐ ┌──────────┐ ┌───────────────┐
│   Supabase       │ │ Pinecone │ │ External APIs │
│   (PostgreSQL)   │ │          │ │               │
│                  │ │ Namespaces│ │ • Zoho CRM   │
│ • Сессии        │ │ per category│ │ • Shipping  │
│ • Memory        │ │ • faq     │ │ • Payments   │
│ • Traces        │ │ • retention│ │ • n8n hooks  │
│ • ai_answerer_  │ │ • shipping│ │               │
│   instructions  │ │ • damage  │ │               │
│ • support_      │ │           │ │               │
│   threads_data  │ │           │ │               │
└──────────────────┘ └──────────┘ └───────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│     СЕРВИС 3: LANGFUSE (open-source, MIT)                            │
│     Observability + Eval Lab                                         │
│     https://github.com/langfuse/langfuse                             │
│                                                                     │
│   • Tracing: автоматический перехват всех вызовов агентов (OTEL)    │
│   • Playground: тест промптов с разными моделями                    │
│   • Datasets: импорт тикетов → test sets                            │
│   • LLM-as-Judge: AI оценивает по критериям (accuracy, tone, safety)│
│   • Experiments: side-by-side model/prompt comparison                │
│   • Prompt management: версионирование + deploy                     │
│   • Cost tracking: стоимость каждого вызова                         │
│                                                                     │
│   Docker: langfuse/langfuse:3 (6 services) | Port: 3100             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│     СЕРВИС 4: AGNO DASH (open-source, Apache-2.0)                   │
│     Analytics Agent — Аналитика на естественном языке               │
│     https://github.com/agno-agi/dash                                │
│                                                                     │
│   "Сколько тикетов AI обработал за неделю?"                        │
│   → SQL генерация (grounded) → execute → интерпретация             │
│   → "1,847 тикетов, +12% к прошлой неделе. Лидер: shipping (34%)" │
│                                                                     │
│   • Self-learning: Agno Learning Machine для SQL паттернов          │
│   • 6 слоёв контекста: schema, rules, queries, docs, learnings     │
│   • Knowledge base: tables/*.json, queries/*.sql, business/*.json  │
│   • Подключение: read-only к Supabase PostgreSQL                    │
│   • UI: через AgentOS Control Plane (os.agno.com)                   │
│                                                                     │
│   Docker: python + agno + dash | Port: 9000                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│     СЕРВИС 5: N8N (уже работает, self-hosted)                       │
│     Workflow Engine — Автоматизация процессов                       │
│     https://github.com/n8n-io/n8n                                   │
│                                                                     │
│   • Email pipeline (текущая система — продолжает работать)          │
│   • Real-time Support Answering (GPT-5.1 drafts → Zoho)            │
│   • AI vs Human Comparison pipeline                                 │
│   • Background jobs (мониторинг, алерты)                            │
│   • Telegram алерты                                                 │
│   • Data collection и preprocessing                                 │
│                                                                     │
│   Docker: n8nio/n8n:latest | Port: 5678 | NODE_FUNCTION_ALLOW_      │
│   BUILTIN=crypto                                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. AI Engine (Agno): как работает мозг системы

### Layered Architecture: Router + Dynamic Support Agent

Двухуровневая архитектура вместо одного super-агента или десятка отдельных.

#### Уровень 1: Router Agent

```python
router_agent = Agent(
    name="Router",
    model=OpenAIChat(id="gpt-5.1", reasoning_effort="none"),
    output_schema=RouterOutput,  # guaranteed JSON
)
```

- **Модель:** GPT-5.1, reasoning: none (самый быстрый/дешёвый режим)
- **Скорость:** ~50ms | **Стоимость:** <$0.001
- **Output:** Structured JSON — primary_category, secondary_category, email, urgency
- **Multi-action detection:** "отмена + смена адреса" → определяет оба intent'а

#### Уровень 2: Dynamic Support Agent

```python
def create_support_agent(category: str, customer_data: dict) -> Agent:
    config = CATEGORY_CONFIG[category]  # из БД / dict
    return Agent(
        model=config["model"],              # GPT-5.1 или Claude per category
        instructions=[
            UNIVERSAL_RULES,                # Слой 1: Red lines (общие)
            load_from_db(config["key"]),     # Слой 2: Category rules (из ai_answerer_instructions)
            config["examples"],             # Слой 3: Few-shot (из Pinecone)
        ],
        tools=[*COMMON_TOOLS, *config["tools"]],
        knowledge=PineconeKnowledge(namespace=config["namespace"]),
        guardrails=[safety_guardrail],
        db=PostgresDb(url=SUPABASE_URL),
        learning=True,
    )
```

Один агент, динамически собирается под категорию:

| Компонент | Откуда загружается | Что меняется |
|-----------|-------------------|-------------|
| **Instructions** | `ai_answerer_instructions` (Supabase) | Правила per category |
| **Tools** | CATEGORY_CONFIG dict | Только нужные actions |
| **Model** | CATEGORY_CONFIG dict | GPT-5.1 / Claude Sonnet 4.5 |
| **Reasoning** | CATEGORY_CONFIG dict | none / low / medium / high |
| **Knowledge** | Pinecone namespace | FAQ per category |
| **Examples** | Pinecone retrieval | Few-shot per category |

#### Трёхслойный промпт (перенос из текущей n8n системы)

```
Слой 1: UNIVERSAL_RULES (hardcoded)
  └── Red lines, safety, tone — одинаковые для всех категорий
  └── Те же правила что сейчас в n8n universal prompt

Слой 2: CATEGORY_RULES (из ai_answerer_instructions, Supabase)
  └── "при damaged_item — запросить фото"
  └── Прямой перенос из текущей БД

Слой 3: FEW-SHOT EXAMPLES (из Pinecone, per category namespace)
  └── Лучшие ответы — retrieval по similarity к текущему вопросу
  └── Переход с текущих hardcoded examples на vector retrieval
```

---

### Полный flow обработки сообщения

```
Клиент: "Hi, I received a damaged item and want to skip next month"
              │
              ▼
   ┌─────────────────────────────────────┐
   │  STEP 1: ROUTER (Agno Agent)        │
   │  Model: GPT-5.1 (reasoning: none)   │
   │  Output: RouterOutput (Pydantic)     │
   │                                     │
   │  {                                  │
   │    primary: "damaged_item",         │
   │    secondary: "skip_month",         │
   │    urgency: "medium",              │
   │    email: null                      │
   │  }                                  │
   │                                     │
   │  ~50ms | ~$0.0001                   │
   └──────────────┬──────────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────────┐
   │  STEP 2: CUSTOMER IDENTIFICATION    │
   │                                     │
   │  email == null → спросить           │
   │  → john@gmail.com                   │
   │  → Zoho API / Supabase lookup       │
   │  → John Smith, subscription #12345  │
   └──────────────┬──────────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────────┐
   │  STEP 3: SUPPORT AGENT             │
   │  create_support_agent("damaged_item")│
   │                                     │
   │  Model: GPT-5.1 (reasoning: low)   │
   │  Tools: create_claim, request_photos│
   │  Knowledge: Pinecone "damage"       │
   │  Instructions: damage rules из БД   │
   │                                     │
   │  → Ответ + create_damage_claim      │
   │  → Agno HITL: "Создать claim? [Да]"│
   │                                     │
   │  → Secondary: skip_month            │
   │  → Agno HITL: "Skip март? [Да]"    │
   └──────────────┬──────────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────────┐
   │  STEP 4: EVAL GATE                  │
   │  (аналог текущего Outstanding       │
   │   Detection + Eval Agent в n8n)     │
   │                                     │
   │  → auto-send / draft / escalate    │
   └─────────────────────────────────────┘
```

---

### Выбор модели per category

| Категория | Модель | reasoning_effort | Стоимость |
|-----------|--------|-----------------|-----------|
| general_question | GPT-5.1 | none | $$$○○ |
| shipping_inquiry | GPT-5.1 | low | $$$○○ |
| change_address | GPT-5.1 | low | $$$○○ |
| change_frequency | GPT-5.1 | low | $$$○○ |
| skip_month | GPT-5.1 | low | $$$○○ |
| damaged_item | GPT-5.1 | low | $$$○○ |
| payment_issue | GPT-5.1 | medium | $$$$○ |
| pause_subscription | GPT-5.1 → Claude* | low → high* | $$$$○ |
| cancel_subscription | **Claude Sonnet 4.5** | **extended thinking** | $$$$$ |
| complex / other | GPT-5.2 | medium | $$$$$ |

*pause_subscription: если клиент в retention mode → переключить на Claude

**Экономика:** 80-90% запросов = GPT-5.1 (none/low) = самый дешёвый. Только 10-20% retention/complex → Claude/GPT-5.2. Экономия ~60-70% vs одна модель для всего.

---

## 4. Chatwoot: Omnichannel Hub

**GitHub:** https://github.com/chatwoot/chatwoot (21k+ ⭐, MIT)

### Каналы

| Канал | Интеграция |
|-------|-----------|
| **Виджет на сайте** | `<script>` тег — встраивается за 5 минут. Кастомизация UI |
| **WhatsApp** | WhatsApp Business API через Chatwoot |
| **Facebook** | Facebook Page → Chatwoot inbox |
| **Email** | Forwarding / IMAP → conversation threads |
| **Telegram** | Bot API → Chatwoot |
| **SMS** | Twilio integration |

### Интеграция с Agno

```
Chatwoot Webhook → POST /api/agent/chat → Agno AgentOS API
                                              │
Chatwoot API ← POST /conversations/{id}/messages ←─┘ (ответ AI)
```

Chatwoot отправляет webhook при каждом новом сообщении. Agno обрабатывает и отвечает через Chatwoot API. Если AI не справляется → assignment на human agent в Chatwoot (в том же conversation thread).

### Что Chatwoot даёт "из коробки"

- **Agent dashboard** — единый inbox для всех каналов
- **Auto-assignment** — правила маршрутизации (AI bot → human teams)
- **CSAT** — автоматический опрос после закрытия
- **Canned responses** — шаблоны для агентов
- **Reports** — response time, resolution time, satisfaction
- **Labels & priorities** — теги, приоритеты, SLA
- **Automation rules** — "если тег = urgent → assign to senior"
- **Contact management** — история клиента по всем каналам
- **Multilingual** — 25+ языков интерфейса

---

## 5. Langfuse: Observability + Eval Lab

**GitHub:** https://github.com/langfuse/langfuse (MIT, self-hosted)

### Что покрывает Langfuse (заменяет Agno Control Plane + Agenta)

| Функция | Описание |
|---------|----------|
| Tracing | Автоматический перехват всех вызовов агентов через AgnoInstrumentor + OTEL |
| Playground | Тест промптов с разными моделями в реальном времени |
| Datasets | Импорт тикетов → test sets для batch evaluation |
| LLM-as-Judge | AI оценивает по критериям (accuracy, tone, safety) |
| Experiments | Side-by-side: GPT-5.1 vs Claude, промпт v1 vs v2 |
| Prompt management | Версионирование, deploy, A/B тестирование |
| Cost tracking | Стоимость каждого вызова по модели |

### Workflow

```
1. TRACING: Все вызовы агентов автоматически попадают в Langfuse (OTEL)

2. DATASET: Импорт тикетов из support_threads_data → Langfuse Dataset
   Ground truth = лучшие ответы агентов

3. EXPERIMENT: Dataset → AI Engine API → ответы → LLM-as-Judge scoring

4. COMPARE:
   • GPT-5.1 vs Claude Sonnet 4.5 → кто лучше для retention?
   • Промпт v1 vs v2 → какой лучше для shipping?

5. DEPLOY: Winner → update config
```

---

## 6. Agno Dash: Analytics Agent

**GitHub:** https://github.com/agno-agi/dash (Apache-2.0)

### 6 слоёв контекста

| Слой | Файл/источник | Пример для Lev Haolam |
|------|--------------|----------------------|
| 1. Table Usage | `tables/support_threads_data.json` | Schema, columns, типы данных |
| 2. Human Annotations | `business/metrics.json` | "Resolution rate = Draft Created / AI Answered" |
| 3. Query Patterns | `queries/resolution_rate.sql` | Проверенные SQL запросы |
| 4. Institutional Knowledge | MCP → ai_answerer_instructions | Правила категоризации, red lines |
| 5. Learnings | PostgreSQL (auto) | "field X — TEXT, не INT" (self-learning) |
| 6. Runtime Context | Supabase introspection | Актуальная схема БД |

### Ключевые таблицы для analytics

- `support_threads_data` — основные тикеты, статусы, категории
- `support_dialogs` — диалоги клиент/агент
- `ai_human_comparison` — сравнение AI vs Human ответов
- `ai_agent_tasks` — задачи AI агента
- `ai_answerer_instructions` — инструкции per category

### Quick Start

```bash
git clone https://github.com/agno-agi/dash.git && cd dash
cp example.env .env
# DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS → Supabase credentials
# OPENAI_API_KEY → для SQL генерации
docker compose up -d --build
docker exec -it dash-api python -m dash.scripts.load_knowledge
# UI: os.agno.com → Add OS → Local → http://localhost:9000
```

---

## 7. Инфраструктура: Монорепо + Docker

### Структура репозитория

```
lev-haolam-ai-platform/
│
├── docker-compose.yml              # Все сервисы
├── docker-compose.dev.yml          # Dev (hot reload, debug ports)
├── .env                            # OPENAI_API_KEY, SUPABASE_URL, etc.
│
├── services/
│   │
│   ├── ai-engine/                  # Agno AgentOS
│   │   ├── Dockerfile              # python:3.12 + agno SDK
│   │   ├── requirements.txt        # agno, pinecone, psycopg2
│   │   ├── main.py                 # AgentOS entry point
│   │   ├── agents/
│   │   │   ├── router.py           # Router Agent (GPT-5.1, structured output)
│   │   │   ├── support.py          # Dynamic Support Agent factory
│   │   │   └── config.py           # CATEGORY_CONFIG dict
│   │   ├── tools/
│   │   │   ├── subscription.py     # pause, skip, cancel, change_frequency
│   │   │   ├── shipping.py         # track, report_missing
│   │   │   ├── damage.py           # create_claim, request_photos, replacement
│   │   │   ├── customer.py         # lookup (Zoho API), identify
│   │   │   └── retention.py        # generate_cancel_link (AES-256-GCM)
│   │   ├── knowledge/              # Pinecone namespace configs
│   │   ├── guardrails/             # safety_guardrail, language_guardrail
│   │   └── registry.py             # Agno Registry (tools, models, dbs)
│   │
│   ├── chatwoot/                   # Chatwoot (Omnichannel)
│   │   ├── docker-compose.chatwoot.yml  # Chatwoot's own compose
│   │   ├── .env.chatwoot           # Chatwoot env vars
│   │   └── hooks/
│   │       └── webhook_handler.py  # Chatwoot → Agno bridge
│   │
│   ├── langfuse/                   # Langfuse (in docker-compose.yml)
│   │   └── (6 services: web, worker, postgres, clickhouse, redis, minio)
│   │
│   ├── analytics/                  # Agno Dash
│   │   ├── Dockerfile
│   │   └── knowledge/
│   │       ├── tables/             # support_threads_data.json, etc.
│   │       ├── queries/            # resolution_rate.sql, funnel.sql
│   │       └── business/           # metrics.json, categories.json
│   │
│   └── n8n/                        # n8n (уже работает)
│       ├── docker-compose.n8n.yml
│       └── backup/                 # Workflow JSON backups
│
├── shared/
│   ├── database/
│   │   ├── migrations/             # Новые таблицы для Agno (sessions, memory)
│   │   └── seed/                   # Initial data
│   └── scripts/
│       ├── export_test_set.py      # Supabase → CSV для Langfuse datasets
│       └── sync_instructions.py    # ai_answerer_instructions → Agno config
│
└── docs/
    ├── architecture-internal.md    # Этот документ
    ├── architecture-external.md    # Версия для босса (без технологий)
    └── runbooks/
        ├── deploy.md
        └── troubleshooting.md
```

### Docker Compose (основной)

```yaml
version: '3.8'

services:
  ai-engine:
    build: ./services/ai-engine
    ports: ["8000:8000"]
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
    depends_on: [postgres]

  chatwoot:
    extends:
      file: ./services/chatwoot/docker-compose.chatwoot.yml
      service: chatwoot
    ports: ["3000:3000"]

  # Langfuse (6 services) — see docker-compose.yml for full config
  # langfuse-web:3100, langfuse-worker, langfuse-postgres, langfuse-clickhouse, langfuse-redis, langfuse-minio

  n8n:
    extends:
      file: ./services/n8n/docker-compose.n8n.yml
      service: n8n
    ports: ["5678:5678"]

  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Взаимодействие сервисов

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Compose Network                  │
│                                                          │
│  ┌───────────────┐  webhook  ┌──────────────────┐       │
│  │ CHATWOOT      │──────────►│ AGNO AgentOS     │       │
│  │ :3000         │◄──────────│ :8000            │       │
│  │               │  response │                  │       │
│  │ Channels:     │           │ Agents:          │       │
│  │ • Widget      │           │ • Router (GPT-5.1)│      │
│  │ • WhatsApp    │           │ • Support (dyn.) │       │
│  │ • Facebook    │           │ • Retention      │       │
│  │ • Email       │           │                  │       │
│  │ • Telegram    │           │ Control Plane:   │       │
│  └───────────────┘           │ os.agno.com      │       │
│                              └────────┬─────────┘       │
│                                       │                  │
│                            ┌──────────┼──────────┐      │
│                            ▼          ▼          ▼      │
│                      ┌──────────┐ ┌────────┐ ┌──────┐   │
│                      │Supabase  │ │Pinecone│ │Zoho  │   │
│                      │PostgreSQL│ │Vector  │ │CRM   │   │
│                      └──────────┘ └────────┘ └──────┘   │
│                            ▲          ▲                  │
│                            │          │                  │
│  ┌───────────────┐         │                            │
│  │ LANGFUSE      │─────────┘                            │
│  │ Observability │  traces + eval                       │
│  │ :3100         │                                      │
│  │               │                                      │
│  │ • Tracing     │                                      │
│  │ • Playground  │                                      │
│  │ • Eval        │                                      │
│  │ • Datasets    │                                      │
│  └───────────────┘                                      │
│                                                          │
│  ┌───────────────┐                                       │
│  │ N8N           │  (email pipeline, продолжает работать)│
│  │ :5678         │                                       │
│  └───────────────┘                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 8. Безопасность

| Принцип | Реализация | Технология |
|---------|-----------|-----------|
| Data sovereignty | Все данные в Supabase, ничего наружу | Supabase self-hosted / cloud |
| Zero egress tracing | Langfuse self-hosted, все трейсы локально | langfuse:3100 → localhost |
| Auth | JWT + RBAC | Agno built-in |
| Encryption | AES-256-GCM для personalized links | Node crypto (n8n) / Python cryptography |
| Red lines | Hardcoded в UNIVERSAL_RULES | Agno Guardrails |
| HITL | needsApproval на tools | Agno Human-in-the-Loop |
| Audit | Полный трейсинг в PostgreSQL | Agno Traces |

---

## 9. Roadmap

### Phase 0: Foundation
**Цель:** Рабочий Agno AgentOS + Control Plane

- `pip install agno` + создать Agent + AgentOS
- PostgresDb → Supabase connection
- PineconeKnowledge → существующий index "support-examples"
- Подключить Control Plane (os.agno.com) → playground + tracing
- Настроить Registry (tools, models) → Studio доступен
- Первые test cases → Agno built-in evals

**Чекпоинт:** Чатим с AI в Control Plane, видим трейсы, тестируем сценарии.

---

### Phase 1: Agent Tuning
**Цель:** 10 категорий настроены

- Перенос промптов из ai_answerer_instructions → Agno instructions
- CATEGORY_CONFIG: model, reasoning, tools, namespace per category
- Тестирование через Control Plane Chat
- Evals: accuracy, reliability, performance
- Сравнение GPT-5.1 vs Claude (через Registry — смена model одной строкой)
- Настроить Guardrails (red lines из текущей системы)

**Чекпоинт:** AI отвечает на все 10 категорий с настроенным качеством.

---

### Phase 2: Chatwoot + Live Chat
**Цель:** Виджет на сайте, клиенты общаются

- Docker: chatwoot/chatwoot → настройка
- Виджет чата на сайте (JS embed)
- Webhook: Chatwoot → Agno API (webhook_handler.py)
- Customer identification flow
- Read-only tools: get_subscription, track_package, order_history
- Handoff rules: AI → human agent в Chatwoot

**Чекпоинт:** Клиент чатит на сайте, AI отвечает, при необходимости передаёт человеку.

---

### Phase 3: Actions + Eval Pipelines
**Цель:** AI действует + глубокое тестирование

- Action tools с Agno HITL: pause, skip, change_address, damage_claim
- Персонализированные cancel links (AES-256-GCM encryption)
- Langfuse datasets: импорт тикетов из support_threads_data
- LLM-as-Judge evaluators в Langfuse (safety, tone, accuracy)
- Experiments: GPT-5.1 vs Claude на retention dataset
- A/B промптов: v1 vs v2 → метрики в Langfuse

**Чекпоинт:** AI выполняет действия. Качество проверено на 5,000+ тикетов в Langfuse.

---

### Phase 4: Retention + Channels
**Цель:** Retention flow + multi-channel

- Retention agent: Claude Sonnet 4.5, extended thinking
- Retention offers: персональные, based on customer history
- Escalation flow: Agno → Chatwoot (assign to human)
- WhatsApp channel через Chatwoot
- Email channel через Chatwoot (параллельно с n8n pipeline)

**Чекпоинт:** Полный retention flow. AI: 80-90%, human: 10-20%.

---

### Phase 5: Dash Analytics + Polish
**Цель:** Аналитика + production

- Docker: agno dash → развернуть
- Knowledge: tables/*.json (все support таблицы)
- Queries: resolution_rate.sql, ai_vs_human.sql, funnel.sql, stuck.sql
- Business rules: metrics.json, categories.json
- Load knowledge → начать использовать
- Learning Machine: ошибки SQL → auto-fix → never repeat
- Production monitoring через Agno Control Plane
- Feedback loop: production → Langfuse eval → improvement

**Чекпоинт:** "Сколько тикетов сегодня?" → мгновенный insight. Production stable.

---

### Phase 6: Scale
**Цель:** Расширение

- Auto-send на все категории (EvalGate через Agno)
- Telegram, Facebook Messenger через Chatwoot
- Agno Teams: QA Agent + Escalation Agent
- Cost optimization (какие категории → дешёвые модели)
- Agno Learning Machine: cross-user insights
- CRM интеграция для проактивной поддержки
- n8n email pipeline → постепенная миграция на Agno

---

## 10. Ожидаемые результаты

| Метрика | Сейчас (n8n + email) | Цель (Agno + Chatwoot) |
|---------|---------------------|------------------------|
| Время ответа | 15-60 минут | **< 10 секунд** |
| AI auto-resolve | ~60% (1 auto-send) | **80-90%** |
| Каналы | 1 (email/Zoho) | **5+** (chat, WhatsApp, FB, email, TG) |
| Human workload | 100% review | **10-20%** (escalations only) |
| Cost per ticket | $$$ (human time) | **$0.01-0.05** (LLM) |
| Model cost optimization | Одна модель (GPT-5.1) | **Per-category** (экономия 60-70%) |

---

## 11. Полный стек

| Сервис | Технология | Лицензия | GitHub Stars | Роль |
|--------|-----------|----------|-------------|------|
| **AI Engine** | Agno AgentOS | Apache-2.0 | 37.4k ⭐ | Агенты, tools, learning, API, console |
| **Omnichannel** | Chatwoot | MIT | 21k+ ⭐ | Каналы, виджет, inbox, handoff |
| **Observability & Eval** | Langfuse | MIT | 10k+ ⭐ | Tracing, playground, eval, datasets, cost tracking |
| **Workflows** | n8n | Fair-code | 50k+ ⭐ | Email pipeline, jobs (уже работает) |
| **Database** | Supabase (PostgreSQL) | Apache-2.0 | — | Данные, memory, traces |
| **Vector Store** | Pinecone | SaaS | — | Knowledge base, FAQ, examples |
| **LLM Models** | OpenAI GPT-5.x / Claude 4.5 | API | — | AI reasoning |

**Всё self-hosted (кроме Pinecone и LLM API), всё в Docker, все данные у нас.**
