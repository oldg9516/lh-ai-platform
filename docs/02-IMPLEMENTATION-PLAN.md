# Implementation Plan: Claude Code Execution Guide

## Общий подход

Монорепо `lev-haolam-ai-platform/` с Docker Compose. Каждая фаза — рабочий инкремент. Claude Code создаёт файлы, конфигурации, код поэтапно.

---

## Phase 0: Foundation (AI Engine core)

### Шаг 0.1: Структура монорепо
```
Создать:
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .gitignore
├── CLAUDE.md
├── services/
│   └── ai-engine/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── main.py
│       ├── agents/
│       ├── tools/
│       ├── knowledge/
│       └── guardrails/
├── shared/
│   ├── database/
│   │   └── migrations/
│   └── scripts/
└── docs/
```

### Шаг 0.2: AI Engine — базовый Agno AgentOS
```
Файлы:
- services/ai-engine/requirements.txt (agno, openai, anthropic, pinecone, psycopg2-binary, pydantic)
- services/ai-engine/main.py (AgentOS entry point, FastAPI health check)
- services/ai-engine/config.py (env vars, CATEGORY_CONFIG dict)
- services/ai-engine/Dockerfile (python:3.12-slim)
```

### Шаг 0.3: Router Agent
```
Файлы:
- services/ai-engine/agents/router.py
  - Модель: GPT-5.1, reasoning: none
  - Input: customer message (text)
  - Output (Pydantic): { primary: str, secondary: str|None, urgency: str, email: str|None }
  - 10 категорий из CATEGORY_CONFIG
```

### Шаг 0.4: Support Agent Factory
```
Файлы:
- services/ai-engine/agents/support.py
  - create_support_agent(category: str) → Agent
  - Динамическая загрузка промптов из ai_answerer_instructions
  - Model/reasoning per category из CATEGORY_CONFIG
- services/ai-engine/agents/config.py
  - CATEGORY_CONFIG dict (model, reasoning, tools, pinecone namespace per category)
```

### Шаг 0.5: Database integration
```
Файлы:
- services/ai-engine/database/connection.py (Supabase/PostgreSQL connection pool)
- services/ai-engine/database/queries.py (get_instructions, get_customer, save_session)
```

### Шаг 0.6: Pinecone Knowledge
```
Файлы:
- services/ai-engine/knowledge/pinecone_client.py
  - PineconeKnowledge wrapper для Agno
  - Namespaces: support-examples, outstanding-cases
```

### Шаг 0.7: Guardrails
```
Файлы:
- services/ai-engine/guardrails/safety.py
  - safety_guardrail: red lines (death, bank, threats → escalate)
  - language_guardrail: detect language, respond in same
  - subscription_guardrail: НИКОГДА не подтверждать отмену напрямую
```

### Шаг 0.8: Docker Compose + первый запуск
```
docker-compose.yml: ai-engine service
docker-compose.dev.yml: hot reload, debug ports
.env.example: все нужные переменные
```

**Чекпоинт Phase 0:** `docker compose up` → AI Engine запущен, /health отвечает, Agent доступен через Agno Control Plane (os.agno.com).

---

## Phase 1: Agent Tuning

### Шаг 1.1: Промпты из БД
```
Файлы:
- services/ai-engine/agents/instructions.py
  - load_instructions(category) → загрузка из ai_answerer_instructions
  - Структура: instruction_1..10 (persona, red lines, logic, format, examples)
  - Global rules + category-specific rules
```

### Шаг 1.2: Outstanding Detection
```
Файлы:
- services/ai-engine/agents/outstanding.py
  - Агент для определения триггеров в запросе клиента
  - Dynamic rules из ai_answerer_instructions (outstanding_rules, outstanding_hard_rules)
  - Pinecone tool: outstanding-cases namespace (top-5 similar)
  - Output: { is_outstanding: bool, trigger: str }
```

### Шаг 1.3: Eval Gate
```
Файлы:
- services/ai-engine/agents/eval_gate.py
  - Проверка AI-ответа перед отправкой
  - Решения: send / draft / escalate
  - Checks: safety, tone, accuracy, completeness
  - Confidence: high / medium / low
```

### Шаг 1.4: Customer Identification
```
Файлы:
- services/ai-engine/tools/customer.py
  - identify_customer(email) → lookup Zoho/Supabase
  - get_subscription_info(customer_id)
  - get_tracking_info(customer_id)
  - get_order_history(customer_id)
```

### Шаг 1.5: Полный pipeline
```
Файлы:
- services/ai-engine/pipeline.py
  - process_message(message, session_id) → response
  - Flow: Router → Identify → Support Agent → Outstanding → Eval Gate → Response
```

### Шаг 1.6: API endpoints
```
Файлы:
- services/ai-engine/api/routes.py
  - POST /api/chat — основной endpoint
  - POST /api/webhook/chatwoot — для Phase 2
  - GET /api/health
  - GET /api/sessions/{id}
```

### Шаг 1.7: Testing через Control Plane
```
- Подключить Agno Control Plane (os.agno.com)
- Playground: тестирование всех 10 категорий
- Tracing: видеть весь flow каждого запроса
- Built-in evals: accuracy, reliability
```

**Чекпоинт Phase 1:** Все 10 категорий отвечают корректно через Agno playground. Outstanding Detection работает. Eval Gate принимает решения.

---

## Phase 2: Chatwoot + Live Chat

### Шаг 2.1: Chatwoot setup
```
Файлы:
- services/chatwoot/docker-compose.chatwoot.yml
- services/chatwoot/.env.chatwoot
- Обновить docker-compose.yml: добавить chatwoot service
```

### Шаг 2.2: Webhook bridge
```
Файлы:
- services/chatwoot/hooks/webhook_handler.py
  - Chatwoot webhook → POST /api/webhook/chatwoot
  - Parse message, extract conversation_id, contact info
  - Forward to AI Engine
  - AI response → Chatwoot API (POST /conversations/{id}/messages)
```

### Шаг 2.3: Виджет на сайте
```
- Chatwoot JS embed code → levhaolam.com
- Кастомизация UI (цвета, логотип, welcome message)
```

### Шаг 2.4: Customer identification через Chatwoot
```
- Chatwoot contact → email
- Flow: new message → check contact → identify → route
```

### Шаг 2.5: Handoff rules
```
Файлы:
- services/ai-engine/handoff/rules.py
  - Когда передавать человеку
  - Как передавать контекст
  - Assignment rules в Chatwoot
```

### Шаг 2.6: Read-only tools
```
Файлы:
- services/ai-engine/tools/subscription.py (get only)
- services/ai-engine/tools/shipping.py (track only)
```

**Чекпоинт Phase 2:** Клиент чатит на сайте через виджет. AI отвечает в real-time. При необходимости передаёт человеку.

---

## Phase 3: Actions + Eval Pipelines

### Шаг 3.1: Action tools с HITL
```
Файлы:
- services/ai-engine/tools/subscription.py (добавить: pause, skip, change_frequency)
- services/ai-engine/tools/shipping.py (добавить: report_missing)
- services/ai-engine/tools/damage.py (create_claim, request_photos, replacement)
- services/ai-engine/tools/retention.py (generate_cancel_link с AES-256-GCM)
Каждый action tool: needsApproval=true → HITL confirmation
```

### Шаг 3.2: Langfuse Eval Pipelines
```
Настроить в Langfuse (http://localhost:3100):
- Datasets: импорт исторических тикетов из Supabase
- Evaluators: safety, tone, action accuracy (LLM-as-Judge)
- Experiments: side-by-side model comparison
- Prompt management: версионирование промптов
Langfuse уже развёрнут в Phase 0 (docker-compose.yml).
```

**Чекпоинт Phase 3:** AI выполняет действия с подтверждением. Качество проверено на 5,000+ тикетов в Langfuse.

---

## Phase 4: Retention + Channels

### Шаг 4.1: Retention agent
```
- Claude Sonnet 4.5 с extended thinking
- Персональные предложения на основе customer history
- Cancel link generation (AES-256-GCM)
```

### Шаг 4.2: Дополнительные каналы
```
- WhatsApp через Chatwoot
- Email через Chatwoot (параллельно с n8n)
```

**Чекпоинт Phase 4:** Полный retention flow. AI 80-90%, human 10-20%.

---

## Phase 5: Analytics

### Шаг 5.1: Agno Dash
```
Файлы:
- services/analytics/Dockerfile
- services/analytics/knowledge/tables/ (*.json)
- services/analytics/knowledge/queries/ (*.sql)
- services/analytics/knowledge/business/ (metrics.json, categories.json)
```

**Чекпоинт Phase 5:** "Сколько тикетов сегодня?" → мгновенный insight.

---

## Phase 6: Scale
- Auto-send на все категории
- Telegram, Facebook Messenger
- Multi-agent teams
- Cost optimization per category
- Learning Machine: cross-user insights

---

## Порядок создания файлов (Phase 0)

Claude Code должен создавать файлы строго в этом порядке:

1. `CLAUDE.md` — проектная конфигурация
2. `.env.example` + `.gitignore`
3. `docker-compose.yml` + `docker-compose.dev.yml`
4. `services/ai-engine/requirements.txt`
5. `services/ai-engine/Dockerfile`
6. `services/ai-engine/config.py` — env vars, CATEGORY_CONFIG
7. `services/ai-engine/database/connection.py`
8. `services/ai-engine/database/queries.py`
9. `services/ai-engine/knowledge/pinecone_client.py`
10. `services/ai-engine/guardrails/safety.py`
11. `services/ai-engine/agents/router.py`
12. `services/ai-engine/agents/config.py`
13. `services/ai-engine/agents/support.py`
14. `services/ai-engine/agents/instructions.py`
15. `services/ai-engine/main.py`
16. `services/ai-engine/api/routes.py`

Каждый файл: создать → проверить импорты → убедиться что Docker собирается.
