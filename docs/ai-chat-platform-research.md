# Lev Haolam AI Support Chat Platform — Исследование стека

## Твоё видение (резюме)

1. **Embeddable Chat Widget** — скрипт, который вставляется на любой сайт/приложение
2. **Sandbox/Playground** — среда для настройки агентов, добавления тулов, скиллов
3. **Eval Pipeline** — тестирование на исторических данных, метрики, A/B testing
4. **Production Deploy** — безболезненный переход от sandbox к production
5. **Model Flexibility** — GPT-5.x и Claude, сравнение и выбор
6. **Skills System** — переиспользуемые навыки агентов

---

## Часть 1: Agent Framework — Agno (полная экосистема)

### Agno (⭐ Рекомендация #1 — Framework + Runtime + UI + Evals)

**Что это:** Open-source Python framework, runtime и control plane для multi-agent systems. Бывший Phidata, 37.4k ⭐ на GitHub. 529x быстрее LangGraph по instantiation. Apache-2.0.

**Ключевое открытие:** Agno — это НЕ просто framework для создания агентов. Это **полная платформа** из 3 компонентов:

| Компонент | Что делает | Аналог |
|-----------|-----------|--------|
| **Framework (SDK)** | Создание агентов с learning, tools, knowledge, guardrails | LangGraph / CrewAI |
| **AgentOS (Runtime)** | Production FastAPI runtime с SSE endpoints | Custom backend |
| **Control Plane UI** (os.agno.com) | Chat, trace, monitor, manage, eval — из браузера | Agenta / Langfuse / Braintrust |

Это значит: **Agno уже включает в себя playground и мониторинг**, которые мы планировали закрывать отдельными инструментами.

---

### 1.1 Framework (SDK) — Создание агентов

- **Model-agnostic** — OpenAI GPT-5.x, Anthropic Claude, Google Gemini, локальные модели
- **100+ встроенных toolkit'ов** + кастомные tools
- **Human-in-the-loop** — confirmations, approvals, overrides
- **Agentic RAG** — 20+ vector stores (включая Pinecone)
- **Memory + Learning** — persistent user profiles, накопление знаний, transfer learnings между пользователями
- **Guardrails** — validation и security rules
- **MCP + A2A support** — Model Context Protocol и Agent-to-Agent
- **Type-safe I/O** — `input_schema` и `output_schema`
- **Async-first** — built for long-running tasks
- **Multimodal** — text, images, audio, video, files

**Код для Lev Haolam:**
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.knowledge.pinecone import PineconeKnowledge
from agno.db.postgres import PostgresDb
from agno.os import AgentOS

support_agent = Agent(
    name="Lev Haolam Support",
    model=OpenAIChat(id="gpt-5.1"),  # или Claude(id="claude-sonnet-4-5")
    
    # Knowledge base (FAQ, документация)
    knowledge=PineconeKnowledge(
        index_name="support-examples",
        namespace="faq"
    ),
    
    # Persistent memory + learning
    db=PostgresDb(url="postgresql://...supabase..."),
    learning=True,  # ← одна строка — агент учится со временем
    
    # Tools
    tools=[
        lookup_customer_tool,
        get_subscription_tool,
        pause_subscription_tool,      # needsApproval=True
        change_address_tool,           # needsApproval=True
        report_damage_tool,            # needsApproval=True
        initiate_retention_tool,
        create_support_case_tool,
        search_knowledge_tool,
    ],
    
    # Guardrails
    guardrails=[safety_guardrail, language_guardrail],
    
    # Instructions (из ai_answerer_instructions)
    instructions=load_instructions_from_db(),
)

# Deploy как API
agent_os = AgentOS(agents=[support_agent])
app = agent_os.get_app()
```

---

### 1.2 AgentOS (Runtime) — Production API

AgentOS — это **pre-built FastAPI application** с готовыми endpoints:

- **50+ API endpoints** с SSE streaming
- **Request-level isolation** — сессии пользователей изолированы
- **JWT-based RBAC** — role-based access control с hierarchical scopes
- **MCP server** — AgentOS одновременно является MCP server'ом (другие агенты могут подключаться)
- **Knowledge management** — API для управления knowledge bases
- **Session management** — создание, получение, удаление сессий
- **Memory management** — работа с user memories через API

```python
# Полный пример с Registry для Studio
from agno.os import AgentOS
from agno.registry import Registry

registry = Registry(
    name="Lev Haolam Registry",
    tools=[
        lookup_customer_tool,
        pause_subscription_tool,
        retention_tool,
    ],
    models=[
        OpenAIChat(id="gpt-5.1"),
        OpenAIChat(id="gpt-5.2"),
        Claude(id="claude-sonnet-4-5"),
    ],
    dbs=[postgres_db],
)

agent_os = AgentOS(
    agents=[support_agent, retention_agent],
    teams=[support_team],
    registry=registry,  # ← Включает Studio (visual builder)
    db=postgres_db,
)
```

**Деплой:** Docker контейнер в твоём облаке. `fastapi dev agent.py` — и ты в production.

---

### 1.3 Control Plane UI (os.agno.com) — ⭐ Встроенный Playground + Monitoring

**Это то, что ты искал под "playground с метриками".** UI подключается напрямую к твоему AgentOS из браузера. Никакие данные не уходят наружу.

**Chat Page — Playground:**
- Интерактивный чат с каждым агентом, командой или workflow
- Тестирование на реальных сценариях прямо из браузера
- Переключение между агентами (support, retention, shipping)

**Traces — Мониторинг:**
- Полный трейсинг каждого run'а: tool calls, model responses, reasoning chain
- Стоимость, латентность, количество токенов — всё по каждому вызову
- Debug mode с verbose logging
- **Данные хранятся в твоей БД** (не в Agno cloud) — zero egress

**Sessions — Управление:**
- Просмотр всех сессий пользователей
- Контент каждой сессии (messages, tool calls, memory updates)
- Фильтрация и поиск

**Memory — Обучение:**
- Просмотр accumulated memories
- User profiles
- Learnings (что агент выучил)

**Evals — Оценка (встроенная):**
- 3 измерения: **accuracy, reliability, performance**
- Оценка агентов на test cases
- Метрики по run'ам

**Архитектура Control Plane:**
```
┌──────────────┐     напрямую из браузера      ┌──────────────────┐
│  os.agno.com │  ──────────────────────────►  │  Твой AgentOS    │
│  (UI в       │     WebSocket / REST          │  (Docker/Cloud)  │
│   браузере)  │  ◄──────────────────────────  │                  │
└──────────────┘     traces, sessions, data    │  ┌────────────┐  │
                                               │  │ PostgreSQL │  │
                     Никаких данных             │  │ (все данные│  │
                     не уходит в Agno!          │  │  у тебя)   │  │
                                               │  └────────────┘  │
                                               └──────────────────┘
```

---

### 1.4 Studio (ALPHA) — Visual Agent Builder

**Визуальный редактор** для создания агентов, команд и workflow'ов:

- **Drag & drop** — перетаскивание компонентов из Registry на canvas
- **Registry** — зарегистрированные tools, models, dbs доступны как компоненты
- **Version control** — каждый publish создаёт версию, можно откатить
- **Set Current** — выбор какая версия активна в production API
- **Full lifecycle:** Draft → Test (in Control Plane) → Publish → Set Current

**Workflow для Lev Haolam:**
1. Создаёшь agents в коде (Python) — базовая конфигурация
2. Регистрируешь в Registry (tools, models)
3. В Studio визуально комбинируешь, настраиваешь параметры
4. Тестируешь в Control Plane Chat
5. Publish → версия доступна через API
6. Потом можно создать новую версию, сравнить, откатить

---

### 1.5 Built-in Evals — Оценка агентов

Agno включает evaluation framework:
- **Accuracy** — правильность ответов
- **Reliability** — стабильность (одинаковый результат на одинаковых inputs)
- **Performance** — latency, cost, token usage

```python
# Пример eval (из Agno SDK)
from agno.evals import Eval

eval = Eval(
    agent=support_agent,
    test_cases=[
        {"input": "I want to cancel", "expected_tools": ["initiate_retention_tool"]},
        {"input": "Where is my package?", "expected_tools": ["get_shipping_status"]},
    ]
)
results = eval.run()
# → accuracy: 94%, avg_latency: 1.2s, avg_cost: $0.003/query
```

---

### 1.6 Learning Machine — Self-Learning

Уникальная фича Agno — агенты реально учатся:

| Режим | Как работает |
|-------|-------------|
| **Always** | Сохраняет learnings после каждого run'а |
| **Agentic** | Агент сам решает, стоит ли сохранить learning |

Типы обучения:
- **User Profiles** — персональные предпочтения пользователя, persist across sessions
- **User Memories** — факты о пользователе, накапливаются
- **Learned Knowledge** — паттерны и insights, **transfer-ируются между пользователями**

Для Lev Haolam это значит: если агент узнал, что клиенты из Франции часто спрашивают о customs fees — это learning применится ко всем будущим клиентам из Франции.

---

### Альтернативы Agno

| Framework | Плюсы | Минусы | Для кого |
|-----------|-------|--------|----------|
| **LangGraph** | Мощная оркестрация, state machines | Сложный, медленный, нет встроенного UI/runtime | Сложные multi-agent workflows |
| **CrewAI** | Простой для multi-agent teams | Менее гибкий, меньше контроля | Командная работа агентов |
| **PydanticAI** | Type-safe, чистый код | Новый, меньше экосистема, нет playground | Минималистичные агенты |
| **Vercel AI SDK** | Отличный для frontend, streaming | JavaScript only, нет persistent memory | Frontend-first чат |
| **OpenAI Assistants API** | Простейший вход, hosted | Vendor lock-in, нет self-host | Быстрый MVP |

**Вердикт:** Agno — не просто framework, а **полная платформа** (framework + runtime + UI + evals). Ни один конкурент не предлагает всё это вместе. Ты получаешь agent SDK, production API, playground для тестирования, мониторинг, visual builder и self-learning — в одном пакете.

---

## Часть 1b: Архитектура системы — Layered Agent (Router + Dynamic Support Agent)

### Ключевой вопрос: один Super-Agent или Multi-Agent Team?

Два крайних подхода и почему ни один не идеален:

**Super-Agent (один агент с всеми tools):**
- ❌ 10 категорий × правила × red lines × few-shot = огромный промпт (tokens = деньги)
- ❌ Модель путается между инструкциями для shipping и retention
- ❌ reasoning_effort нужен разный: FAQ → none, retention → medium
- ❌ Все tools доступны всегда — лишний context, потенциальные ошибки

**Full Multi-Agent (10 отдельных агентов + orchestrator):**
- ❌ 10x конфигураций, 10x дебага
- ❌ Сложные handoff'ы между агентами (клиент спрашивает про shipping → потом хочет отменить)
- ❌ Transfer контекста между агентами
- ❌ Overkill для 10 категорий

---

### ⭐ Рекомендация: Layered Architecture (2 уровня)

```
┌─────────────────────────────────────────────────────┐
│                   ROUTER AGENT                       │
│                                                     │
│  Лёгкий, быстрый (GPT-5.1, reasoning: none/low)    │
│  Задача: понять intent → выбрать category →          │
│  загрузить правильный config                        │
│                                                     │
│  НЕ отвечает клиенту, только маршрутизирует         │
│  ~50ms, <$0.001 за запрос                           │
└────────────────────┬────────────────────────────────┘
                     │ category + customer_data
                     ▼
┌─────────────────────────────────────────────────────┐
│              SUPPORT AGENT (один, но динамический)    │
│                                                     │
│  Один агент, но с ДИНАМИЧЕСКОЙ конфигурацией:        │
│                                                     │
│  instructions = load_by_category(category)           │
│  tools = get_tools_for_category(category)            │
│  model = select_model(category)                      │
│  reasoning = get_reasoning_level(category)           │
│                                                     │
│  Отвечает клиенту, выполняет actions, escalates     │
└─────────────────────────────────────────────────────┘
```

**Принцип:** Один Support Agent, но каждый раз он "собирается" под конкретную категорию. Как актёр, который получает разный сценарий на каждое выступление — но это один и тот же актёр.

---

### Реализация на Agno

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.knowledge.pinecone import PineconeKnowledge
from agno.db.postgres import PostgresDb
from pydantic import BaseModel
from typing import Optional

# ═══════════════════════════════════════════════
# ROUTER — классификация запроса
# ═══════════════════════════════════════════════

class RouterOutput(BaseModel):
    """Structured output от Router Agent"""
    primary_category: str       # основная категория
    secondary_category: Optional[str] = None  # multi-action detection
    customer_email: Optional[str] = None
    urgency: str               # low / medium / high
    summary: str               # краткое описание intent

router_agent = Agent(
    name="Router",
    model=OpenAIChat(id="gpt-5.1", reasoning_effort="none"),
    instructions="""
    Classify the customer message into categories:
    1. cancel_subscription
    2. pause_subscription  
    3. skip_month
    4. change_frequency
    5. change_address
    6. shipping_inquiry
    7. damaged_item
    8. payment_issue
    9. general_question
    10. other
    
    IMPORTANT: If the message contains MULTIPLE requests,
    set primary_category for the main one and secondary_category 
    for the additional one.
    
    Extract customer email if mentioned.
    Set urgency based on tone and content.
    """,
    output_schema=RouterOutput,  # guaranteed JSON
)

# ═══════════════════════════════════════════════
# CATEGORY CONFIG — загрузка из БД
# ═══════════════════════════════════════════════

# Универсальные правила (одинаковые для ВСЕХ категорий)
UNIVERSAL_RULES = """
RED LINES (никогда не нарушай):
- NEVER confirm a cancellation or pause directly
- NEVER share internal system data with customer
- NEVER make promises about refunds without authorization
- If customer mentions death threats or legal action → escalate immediately
- If customer mentions bank dispute/chargeback → escalate immediately

TONE: Warm, empathetic, professional. Use customer's name.
"""

# Общие tools (доступны всегда)
COMMON_TOOLS = [
    lookup_customer_tool,       # поиск клиента
    search_knowledge_tool,      # поиск в FAQ/knowledge base
    get_subscription_status,    # текущий статус подписки
    escalate_to_human_tool,     # передать человеку
]

# Category-specific конфигурация
CATEGORY_CONFIG = {
    "cancel_subscription": {
        "model": Claude(id="claude-sonnet-4-5"),  # тёплый тон для retention
        "reasoning": None,  # Claude uses extended thinking
        "tools": [
            check_outstanding_tool,       # проверить outstanding case
            generate_retention_offer,     # создать предложение
            generate_cancel_link_tool,    # зашифрованная ссылка
        ],
        "knowledge_namespace": "retention",
        "instructions_key": "cancel_subscription",  # ключ в ai_answerer_instructions
    },
    "shipping_inquiry": {
        "model": OpenAIChat(id="gpt-5.1", reasoning_effort="low"),
        "reasoning": "low",
        "tools": [
            track_package_tool,
            check_delivery_status_tool,
            report_missing_package_tool,
        ],
        "knowledge_namespace": "shipping",
        "instructions_key": "shipping_inquiry",
    },
    "damaged_item": {
        "model": OpenAIChat(id="gpt-5.1", reasoning_effort="low"),
        "reasoning": "low",
        "tools": [
            create_damage_claim_tool,     # needsApproval=True
            request_photos_tool,
            issue_replacement_tool,       # needsApproval=True
        ],
        "knowledge_namespace": "damage",
        "instructions_key": "damaged_item",
    },
    "pause_subscription": {
        "model": OpenAIChat(id="gpt-5.1", reasoning_effort="low"),
        "reasoning": "low",
        "tools": [
            pause_subscription_tool,      # needsApproval=True
            check_outstanding_tool,
        ],
        "knowledge_namespace": "subscription",
        "instructions_key": "pause_subscription",
    },
    # ... аналогично для остальных 6 категорий
}

# ═══════════════════════════════════════════════
# DYNAMIC SUPPORT AGENT — создаётся под категорию
# ═══════════════════════════════════════════════

def create_support_agent(category: str, customer_data: dict) -> Agent:
    """Создаёт агента с конфигурацией под конкретную категорию"""
    
    config = CATEGORY_CONFIG[category]
    
    # Загружаем category-specific instructions из БД
    category_instructions = load_from_db(
        table="ai_answerer_instructions",
        key=config["instructions_key"]
    )
    
    return Agent(
        name=f"Support ({category})",
        model=config["model"],
        
        # Трёхслойный промпт (как в текущей n8n системе)
        instructions=[
            UNIVERSAL_RULES,                    # Layer 1: Safety (одинаковый)
            category_instructions.rules,        # Layer 2: Category rules (из БД)
            category_instructions.examples,     # Layer 3: Few-shot examples
        ],
        
        # Только нужные tools
        tools=[*COMMON_TOOLS, *config["tools"]],
        
        # Knowledge — namespace per category
        knowledge=PineconeKnowledge(
            index_name="support-examples",
            namespace=config["knowledge_namespace"],
        ),
        
        # Guardrails
        guardrails=[safety_guardrail, language_guardrail],
        
        # Memory & Learning
        db=postgres_db,
        learning=True,
        
        # Customer context
        context={"customer": customer_data, "category": category},
    )
```

---

### Полный flow обработки сообщения

```
Клиент: "Hi, I received a damaged item in my last box 
         and also want to skip next month"
              │
              ▼
┌──────────────────────────────────────────────────────┐
│  STEP 1: ROUTER AGENT                                │
│                                                      │
│  Model: GPT-5.1 (reasoning: none)                    │
│  Cost: ~$0.0001 | Latency: ~50ms                     │
│                                                      │
│  Output (structured):                                │
│  {                                                   │
│    "primary_category": "damaged_item",               │
│    "secondary_category": "skip_month",  ← multi!     │
│    "customer_email": null,                           │
│    "urgency": "medium",                              │
│    "summary": "Damaged item + wants to skip"         │
│  }                                                   │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  STEP 2: CUSTOMER IDENTIFICATION                     │
│                                                      │
│  email не в сообщении → спросить                     │
│  "Could you share your email so I can look up        │
│   your account?"                                     │
│                                                      │
│  → Клиент даёт email → lookup в Zoho/Supabase       │
│  → Найден: John Smith, subscription #12345           │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  STEP 3: SUPPORT AGENT (dynamic: damaged_item)       │
│                                                      │
│  Model: GPT-5.1 (reasoning: low)                     │
│  Instructions: UNIVERSAL + damage_rules + examples   │
│  Tools: COMMON + create_claim + request_photos       │
│  Knowledge: Pinecone namespace "damage"              │
│                                                      │
│  → "I'm sorry to hear about the damaged item!        │
│     Could you describe the damage and share a        │
│     photo? I'll create a claim right away."          │
│                                                      │
│  → [create_damage_claim] ← needs approval            │
│  → Widget shows: "Create damage claim? [Yes] [No]"   │
│                                                      │
│  Затем обрабатывает secondary action:                │
│  → "I also see you'd like to skip next month.        │
│     Shall I go ahead and skip March?"                │
│                                                      │
│  → [skip_month_tool] ← needs approval                │
│  → Widget shows: "Skip March box? [Yes] [No]"        │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  STEP 4: EVAL GATE (опционально, Phase 4+)           │
│                                                      │
│  Проверяет ответ перед отправкой (для auto-send):    │
│  - Соответствует safety rules?                       │
│  - Tone appropriate?                                 │
│  - Actions correct?                                  │
│                                                      │
│  → auto-send / save as draft / escalate              │
└──────────────────────────────────────────────────────┘
```

---

### Динамический выбор модели per category

| Категория | Модель | reasoning_effort | Почему |
|-----------|--------|-----------------|--------|
| general_question | GPT-5.1 | none | FAQ, быстрый ответ из knowledge base |
| shipping_inquiry | GPT-5.1 | low | Lookup tracking, простая логика |
| change_address | GPT-5.1 | low | Форматирование + confirmation |
| change_frequency | GPT-5.1 | low | Простое действие + confirmation |
| skip_month | GPT-5.1 | low | Простое действие + confirmation |
| damaged_item | GPT-5.1 | low | Claim creation, empathetic tone |
| payment_issue | GPT-5.1 | medium | Нужно разобраться в деталях |
| pause_subscription | GPT-5.1 | low | Но если retention → переключить на Claude |
| cancel_subscription | **Claude Sonnet 4.5** | extended thinking | Тёплый тон, retention, deep understanding |
| other / complex | GPT-5.2 | medium | Сложные edge cases, multi-step reasoning |

**Cost impact:** 80-90% запросов = GPT-5.1 (low/none) = самый дешёвый путь. Только 10-20% retention/complex идут на Claude/GPT-5.2.

---

### Multi-Action Detection

Router Agent детектирует несколько действий в одном сообщении:

```
"I want to cancel AND change my address" 
→ primary: cancel_subscription, secondary: change_address

"My package is damaged, also where is my other order?"
→ primary: damaged_item, secondary: shipping_inquiry

"Just checking on my delivery"
→ primary: shipping_inquiry, secondary: null (single action)
```

Support Agent обрабатывает оба действия **последовательно в одной сессии** — нет transfer контекста между агентами. Это проще и надёжнее чем multi-agent handoff.

---

### Масштабируемость: добавление новой категории

Добавить 11-ю категорию = **0 изменений в коде:**

1. Добавить запись в `ai_answerer_instructions` (БД)
2. Добавить запись в `CATEGORY_CONFIG` (dict в конфиге)
3. Создать tools для категории (если нужны новые)
4. Добавить namespace в Pinecone
5. Обновить Router Agent instructions (добавить пункт 11)

Это тот же принцип, который ты уже используешь в n8n — database-driven config.

---

### Когда переходить к Multi-Agent Team

Multi-agent через Agno Teams добавить **позже (Phase 5+)** если появятся кейсы:

```python
# Future: Agno Team для сложных кейсов
from agno.team import Team

support_team = Team(
    name="Support Team",
    agents=[
        router_agent,
        support_agent,
        qa_agent,           # проверяет ответы перед отправкой
        escalation_agent,   # для edge cases требующих deep research
    ],
    mode="coordinate",  # route / collaborate / coordinate
)

agent_os = AgentOS(teams=[support_team])
```

**Триггеры для перехода к multi-agent:**
- QA Agent нужен как отдельный "second opinion" перед auto-send
- Escalation Agent для кейсов требующих research (проверка в нескольких системах)
- Supervisor pattern — мониторинг качества в реальном времени
- Billing Specialist — длинные цепочки reasoning для payment disputes

---

### Сравнение подходов

| Аспект | Super-Agent | Full Multi-Agent (10) | **Layered (Router + Dynamic)** |
|--------|------------|----------------------|-------------------------------|
| Сложность | Низкая | Высокая | Средняя |
| Промпт size | Огромный (все rules) | 10 маленьких | Router: маленький, Support: medium |
| Context window | Забит всем сразу | Чистый, focused | ✅ Чистый, загружен по category |
| Model per category | ❌ Одна для всех | ✅ Своя per agent | ✅ Своя per category |
| reasoning_effort | ❌ Один для всех | ✅ Свой per agent | ✅ Свой per category |
| Tool exposure | ❌ Все tools всегда | ✅ Только нужные | ✅ Только нужные |
| Handoff | N/A | ❌ Сложный | ✅ Нет (один агент) |
| Multi-action | Сам разбирается | ❌ Transfer context | ✅ Sequential |
| Debug | ❌ Всё в куче | ⚠️ Много агентов | ✅ Router → Agent |
| Cost per query | ❌ Высокий | ⚠️ Orchestration overhead | ✅ Router дешёвый |
| Добавить категорию | Config change | Новый агент + wiring | ✅ DB record |

---

## Часть 2: Расширенный Eval Pipeline — Agenta (опционально, поверх Agno)

### Что Agno уже покрывает vs что добавляет Agenta

С обновлённым пониманием Agno, вопрос меняется: **нужна ли вообще Agenta?**

| Функция | Agno Control Plane | Agenta | Нужна Agenta? |
|---------|-------------------|--------|---------------|
| Chat с агентом (playground) | ✅ Полноценный | ✅ Да | ❌ Нет |
| Tracing (tool calls, latency, cost) | ✅ Встроенный, zero egress | ✅ Да | ❌ Нет |
| Session management | ✅ Да | ❌ Нет | ❌ Нет |
| Memory/Learning viewer | ✅ Да | ❌ Нет | ❌ Нет |
| Visual agent builder | ✅ Studio (ALPHA) | ❌ Нет | ❌ Нет |
| Version control + deploy | ✅ Publish/Set Current | ✅ Prompt versioning | ❌ Нет |
| Built-in evals | ✅ accuracy/reliability/performance | ✅ Более гибкие | ⚠️ Частично |
| **Side-by-side model comparison** | ❌ Нет | ✅ 50+ моделей | ✅ Да |
| **CSV test sets (исторические данные)** | ❌ Нет | ✅ Upload CSV → eval | ✅ Да |
| **LLM-as-Judge** | ❌ Нет (только code evals) | ✅ Гибкие evaluators | ✅ Да |
| **Human annotation workflow** | ❌ Нет | ✅ Structured review | ✅ Да |
| **A/B testing промптов** | ❌ Нет | ✅ Branching + compare | ✅ Да |

### Рекомендация: Agenta как дополнение, а не замена

**Стратегия:**
- **Phase 0-2:** Только Agno (Control Plane + Studio покрывают playground и мониторинг)
- **Phase 3+:** Добавить Agenta **если** нужны: side-by-side model comparison на больших test sets, LLM-as-Judge eval pipelines, structured human annotation

Agenta остаётся полезной для одной конкретной задачи: **массовое тестирование на исторических данных с автоматической оценкой**. Это то, чего в Agno нет — и это важно для твоего кейса (8,400+ тикетов/месяц для eval).

### Agenta — что она добавляет поверх Agno

**Только уникальные фичи (то, чего нет в Agno):**

1. **Test Sets из продакшн данных:**
   - Загрузка CSV с историческими тикетами из `support_threads_data`
   - Ground truth (эталонные ответы) для evaluation
   - Массовый прогон: 1000 тикетов → метрики за минуты

2. **Side-by-side Model Comparison:**
   - Один и тот же test set → GPT-5.1 vs Claude Sonnet 4.5 vs GPT-5.2
   - Метрики per model per category
   - Визуальное сравнение ответов

3. **LLM-as-Judge + Custom Evaluators:**
   - GPT/Claude оценивает качество ответов по кастомным критериям
   - Python evaluators для специфических проверок (safety, red lines compliance)
   - Human annotation workflow для сложных кейсов

4. **A/B Testing промптов:**
   - Branching промптов → разные версии
   - Прогон через test set → сравнение → deploy winner

**Как это вписывается (если решишь добавить):**
```
[Исторические данные из PostgreSQL]
    → Export CSV (thread conversations + human replies)
    → Upload в Agenta как Test Set
    
[Evaluation]
    → Прогоняем Test Set через Agno agent (через API)
    → LLM-as-Judge оценивает качество
    → Human annotation для сложных кейсов
    → Метрики: accuracy, hallucination rate, safety compliance
    
[Compare]
    → GPT-5.1 vs Claude → какая модель лучше для retention?
    → Prompt v1 vs v2 → какой промпт лучше для shipping?
```

### Альтернативы для расширенного Eval

| Платформа | Тип | Плюсы | Минусы | Цена |
|-----------|-----|-------|--------|------|
| **Agenta** | Open-source | Test sets + LLM-as-Judge + side-by-side, self-host | Небольшая команда | Free (self-host) |
| **Langfuse** | Open-source | Лучший open-source tracing, OpenTelemetry | Но Agno уже имеет tracing | Free (self-host) |
| **Braintrust** | SaaS | Лучший UX, Loop для auto-evals | Closed-source, дорого | Pro $249/mo |
| **LangSmith** | SaaS | Глубокий LangChain integration | Lock-in, не нужен с Agno | $39/user/mo |

**Вердикт:** На старте — **только Agno** (Control Plane покрывает playground, tracing, evals). Добавить Agenta позже для массового model comparison и LLM-as-Judge если встроенных evals Agno окажется недостаточно. Langfuse — **не нужен**, т.к. Agno имеет встроенный tracing без egress.

---

## Часть 3: Embeddable Chat Widget

### Архитектура: Agno Backend + Widget Frontend

Ключевая идея: **Agno AgentOS** экспонирует API, **виджет** — это легкий JavaScript компонент, который вызывает этот API.

### Вариант A: Custom Widget (⭐ Рекомендация)

Создаём свой виджет на React, пакуем как JS bundle:

```html
<!-- Вставка на любой сайт -->
<script src="https://cdn.levhaolam.com/chat-widget.js"></script>
<script>
  LevHaolamChat.init({
    apiUrl: 'https://support-api.levhaolam.com',
    theme: 'light',
    language: 'en',
    position: 'bottom-right',
    // Для authenticated контекста
    customerToken: '...',  // JWT от вашего сайта
  });
</script>
```

**Плюсы:** полный контроль, Generative UI, tool approval dialogs, брендинг
**Минусы:** нужно разработать и поддерживать

### Вариант B: Chatwoot + AI Integration

**Chatwoot** — open-source customer support platform (альтернатива Intercom):
- Готовый embeddable виджет
- Omnichannel: website chat + email + WhatsApp + Telegram + Facebook
- Встроенный AI ("Captain") + можно подключить свой AI backend через API
- Self-hosted (Docker)
- 22k+ stars на GitHub

Интеграция: Chatwoot как UI/routing layer → Agno AgentOS как AI backend

**Плюсы:** готовый production-grade виджет, omnichannel, agent dashboard
**Минусы:** дополнительная система, меньше контроля над AI UX

### Вариант C: Agno + AI SDK Interface

Agno уже поддерживает **AI SDK interface** из коробки:

```python
agent_os = AgentOS(
    agents=[support_agent],
    interfaces=[AISdk()],  # ← Vercel AI SDK совместимый endpoint
)
```

Это значит: фронтенд на Next.js с `useChat()` может напрямую общаться с Agno backend. Ты получаешь:
- Streaming responses
- Tool calling с Generative UI
- Multi-step execution

**Рекомендация:** Начать с **Вариант C** (Agno + AI SDK interface + custom React widget), потом при необходимости добавить **Chatwoot** для omnichannel.

---

## Часть 4: Модели — GPT-5.x vs Claude

### Для Customer Support Bot конкретно

| Критерий | GPT-5.1 / 5.2 | Claude Sonnet 4.5 / Opus 4.6 |
|----------|----------------|-------------------------------|
| **Tool calling** | Отличный, быстрый | Отличный, более точный |
| **Цена (input/output)** | $1.25-1.75 / $10-14 per MTok | $3-5 / $15-25 per MTok |
| **Latency** | Быстрее (особенно GPT-5.1 Instant) | Медленнее, но стабильнее |
| **Reasoning effort контроль** | `reasoning_effort: none/low/medium/high` | Extended thinking, adaptive |
| **Multilingual** | Хороший | Отличный (лучше nuance) |
| **Safety/Alignment** | Хороший, настраиваемый | Лучший в индустрии, 98.7% safety score |
| **Structured output** | JSON mode, CFG support | JSON mode, менее flexible |
| **Customer support style** | Более формальный | Более тёплый, естественный |
| **Long conversations** | Хороший с prompt caching | Лучший (30+ часов автономной работы) |
| **Стоимость для 10K тикетов/мес** | ~$50-150 | ~$100-300 |

### Рекомендация по моделям

**Для production customer support:**
- **GPT-5.1** (reasoning_effort: low) — основная модель для 90% запросов. Быстрый, дешёвый, хороший tool calling
- **Claude Sonnet 4.5** — для сложных retention кейсов, где нужен более тёплый тон и глубокое понимание
- **GPT-5.2** — для Eval Agent (оценка качества), где нужен глубокий reasoning

**Для playground/testing:**
- Тестировать ОБЕ модели на одинаковых test sets через Agenta
- Собирать метрики per-model per-category
- Принимать data-driven решение о том, какую модель использовать для какой категории

### GPT-5.x специфика (из prompting guides)

Из OpenAI Cookbook для GPT-5.1/5.2:
- `reasoning_effort` параметр — критичен для customer support: `none` для простых FAQ, `low` для стандартных ответов, `medium` для retention
- Structured outputs с JSON Schema — гарантированный формат ответа
- Multi-tool calling — несколько тулов за один шаг
- `codestral` / thinking modes — для eval и сложной логики

### Claude специфика

- **Interleaved thinking** — Claude думает между tool calls, что улучшает quality
- **Context editing** — снижает token usage на 84% в длинных conversation
- **Anthropic Agent SDK** — инфраструктура для production agents
- **1M token context** (Opus 4.6) — можно подгрузить всю историю клиента
- **Наименьший уровень "misalignment"** среди всех моделей — минимум ошибок в safety

---

## Часть 5: Skills System

### Можно ли использовать Skills в агенте? — Да!

В контексте Agno, "skills" реализуются через несколько механизмов:

**1. Knowledge Bases (для информационных скиллов)**
```python
# Скилл "Знание о продуктах"
product_knowledge = PineconeKnowledge(
    index_name="support-examples",
    namespace="products"
)

# Скилл "Политики и процедуры"
policy_knowledge = PineconeKnowledge(
    index_name="support-examples",
    namespace="policies"
)
```

**2. Tool Kits (для action скиллов)**
```python
# Скилл "Управление подпиской"
subscription_toolkit = [
    pause_subscription_tool,
    resume_subscription_tool,
    change_frequency_tool,
    get_subscription_status_tool,
]

# Скилл "Работа с доставкой"
shipping_toolkit = [
    get_tracking_tool,
    change_address_tool,
    report_lost_package_tool,
]

# Скилл "Retention"
retention_toolkit = [
    check_outstanding_tool,
    generate_retention_offer_tool,
    generate_cancel_link_tool,
]
```

**3. Instructions (для behavioral скиллов)**
```python
# Динамическая загрузка из ai_answerer_instructions
def load_skills_for_category(category: str):
    instructions = db.query(
        "SELECT * FROM ai_answerer_instructions "
        "WHERE type = %s AND status = 'enabled' AND staging = 'production'",
        [category]
    )
    return {
        'persona': instructions.instruction_1,
        'red_lines': instructions.instruction_2,
        'logic': instructions.instruction_3,
        'format': instructions.instruction_4,
        'examples': instructions.instruction_5,
    }
```

**4. Composable Agents (multi-agent skills)**
```python
# Каждый скилл = отдельный агент
shipping_agent = Agent(name="Shipping Expert", tools=shipping_toolkit, ...)
retention_agent = Agent(name="Retention Expert", tools=retention_toolkit, ...)
billing_agent = Agent(name="Billing Expert", tools=billing_toolkit, ...)

# Orchestrator роутит к нужному
from agno.team import Team
support_team = Team(
    agents=[shipping_agent, retention_agent, billing_agent],
    mode="route",  # или "coordinate" для сложных задач
)
```

### Настройка скиллов в Playground

В Agenta можно:
1. Создать разные конфигурации агента (с разным набором скиллов)
2. Тестировать side-by-side: "agent с retention skill" vs "agent без retention skill"
3. Eval: какой набор скиллов даёт лучший результат на test set
4. Deploy winning configuration в production

---

## Часть 6: RAG-Anything

**Что это:** Framework для RAG по любому типу данных (текст, изображения, таблицы, аудио, видео).

**Релевантность для тебя:** Средняя. У тебя в основном текстовые данные (тикеты, FAQ, документация). Стандартный RAG через Pinecone (который у тебя уже есть) покрывает 95% потребностей.

**Когда может пригодиться:**
- Если клиенты будут отправлять фото повреждённых товаров → multimodal RAG
- Если нужно индексировать PDF каталоги/инструкции
- Если появятся видео-инструкции по продуктам

**Вердикт:** Не приоритет сейчас. Pinecone + стандартный text RAG покрывает текущие потребности. RAG-Anything — keep in mind для будущего.

---

## Часть 6b: Agno Dash — Self-Learning Analytics Agent

**Что это:** [Agno Dash](https://github.com/agno-agi/dash) — self-learning data agent от Agno, вдохновлённый [внутренним data agent'ом OpenAI](https://openai.com/index/inside-our-in-house-data-agent/). Text-to-SQL агент с 6 слоями контекста, который учится с каждым запросом. Apache-2.0 лицензия.

**Ключевая концепция — 6 слоёв контекста:**

| Слой | Dash (оригинал) | Lev Haolam применение |
|------|-----------------|----------------------|
| Table Usage | Schema, колонки, связи | Структура `support_threads_data`, `ai_human_comparison`, `support_dialogs` |
| Human Annotations | Метрики, определения, бизнес-правила | Определения категорий, что считается "успешным" ответом, правила подсчёта |
| Query Patterns | SQL паттерны, которые работают | Готовые запросы: resolution rate по категориям, AI vs Human сравнение, воронка тикетов |
| Institutional Knowledge | Docs, wikis, внешние источники | `ai_answerer_instructions`, правила категоризации, red lines |
| Learnings | Ошибки и найденные фиксы (Agno Learning Machine) | Автоматические learnings: "поле X — TEXT а не INT", "JOIN по customer_id, не по email" |
| Runtime Context | Изменения схемы в реальном времени | Live schema introspection Supabase |

**Self-Learning Loop для аналитики:**
```
Вопрос на обычном языке: "Какой resolution rate по retention кейсам за январь?"
     ↓
Получение knowledge + learnings из базы
     ↓
Генерация grounded SQL (не hallucinated SQL)
     ↓
Выполнение запроса
     ↓
 ┌────┴────┐
 ↓         ↓
Успех      Ошибка
 ↓         ↓
 ↓         Диагностика → Фикс → Сохранение Learning
 ↓         (ошибка больше не повторится)
 ↓
Интерпретация результата (не просто цифры, а insights)
     ↓
"Resolution rate по retention = 73.2%. Это на 8% выше чем в декабре.
 Основной рост за счёт новых outstanding examples, добавленных 15 января."
```

**Практические use cases для Lev Haolam:**

1. **Операционная аналитика (ежедневно):**
   - "Сколько тикетов обработал AI сегодня?"
   - "Какие категории имеют самый низкий resolution rate?"
   - "Покажи stuck тикеты за последние 24 часа"

2. **Сравнение AI vs Human (еженедельно):**
   - "Сравни качество ответов AI и human агентов по категории shipping"
   - "Какой средний penalty score AI ответов за эту неделю?"
   - "Где AI ошибается чаще всего?"

3. **Стратегические решения:**
   - "Какие категории готовы к auto-send? Покажи данные"
   - "Какой ROI от AI: сколько человеко-часов сэкономлено?"
   - "Тренд resolution rate по месяцам за последние 6 месяцев"

4. **Debugging и мониторинг:**
   - "Покажи тикеты, которые застряли на статусе Data collected"
   - "Были ли ошибки в pipeline за последний час?"
   - "Какой процент тикетов не прошёл customer identification?"

**Архитектура интеграции:**

```
┌─────────────────────────────────────────────────┐
│              Dash Analytics Agent                 │
│                                                  │
│  Agno Agent + Learning Machine                   │
│       │                                          │
│       ├── Knowledge Base                         │
│       │   ├── tables/*.json (схема Supabase)     │
│       │   ├── queries/*.sql (проверенные запросы) │
│       │   └── business/*.json (метрики, правила)  │
│       │                                          │
│       ├── Tools                                  │
│       │   ├── run_sql (выполнение запросов)       │
│       │   ├── introspect_schema (live schema)    │
│       │   └── chart_builder (визуализация)        │
│       │                                          │
│       └── Self-Learning                          │
│           └── PostgreSQL learnings storage        │
│                                                  │
│  UI: AgentOS Web → os.agno.com                   │
│  Или: Custom dashboard в admin panel             │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│         Supabase PostgreSQL                      │
│  support_threads_data | support_dialogs          │
│  ai_human_comparison  | ai_agent_tasks           │
│  ai_answerer_instructions                        │
└─────────────────────────────────────────────────┘
```

**Настройка knowledge для Lev Haolam:**

Table metadata (пример `knowledge/tables/support_threads_data.json`):
```json
{
  "table_name": "support_threads_data",
  "table_description": "Основная таблица тикетов поддержки с данными клиентов и статусами обработки",
  "use_cases": ["Воронка тикетов", "Resolution rate", "Категоризация", "AI performance"],
  "data_quality_notes": [
    "request_type: основная категория (10 типов)",
    "request_subtype: подкатегория для детальной маршрутизации",
    "status: Data collected → AI Answered → Draft Created → Sent",
    "created_at в UTC",
    "customer_email может быть NULL для тикетов без идентификации"
  ]
}
```

Query patterns (пример `knowledge/queries/resolution_rate.sql`):
```sql
-- <query name>resolution_rate_by_category</query name>
-- <query description>
-- Resolution rate по категориям за указанный период.
-- Считает % тикетов, дошедших до Draft Created из AI Answered.
-- </query description>
-- <query>
SELECT
    request_type,
    COUNT(*) AS total_tickets,
    COUNT(*) FILTER (WHERE status = 'Draft Created') AS resolved,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'Draft Created') / COUNT(*), 1) AS resolution_rate
FROM support_threads_data
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY request_type
ORDER BY resolution_rate DESC
-- </query>
```

**Быстрый старт (15-30 минут):**
```bash
# Клонировать Dash
git clone https://github.com/agno-agi/dash.git && cd dash
cp example.env .env
# Добавить OPENAI_API_KEY и DB_* переменные (Supabase connection)

# Запустить
docker compose up -d --build

# Загрузить knowledge (после создания файлов tables/*.json, queries/*.sql, business/*.json)
docker exec -it dash-api python -m dash.scripts.load_knowledge

# Подключить UI
# Открыть os.agno.com → Add OS → Local → http://localhost:8000
```

**Преимущества Dash для аналитики vs обычный dashboard:**
- **Self-learning:** Чем больше вопросов задаёшь, тем точнее SQL. Ошибки фиксятся автоматически.
- **Natural language:** Не нужно писать SQL. Задаёшь вопрос — получаешь insight с интерпретацией.
- **Grounded answers:** SQL генерируется на основе проверенных паттернов, а не hallucinated.
- **Быстрое развёртывание:** Docker Compose, подключение к существующей Supabase — и работает.
- **Extensible:** Можно добавлять новые query patterns по мере появления новых вопросов.

---

## Часть 7: Что ты мог упустить

### 1. Conversation History & Handoff
Когда AI не может помочь → нужен seamless handoff к человеку С ПОЛНЫМ КОНТЕКСТОМ разговора. Это не тривиально: нужна система, которая сохраняет всю беседу и передаёт агенту.

### 2. Rate Limiting & Cost Control
10,000 тикетов/месяц × tool calls × RAG queries = значительные расходы на API. Нужен:
- Token budget per conversation
- Caching частых запросов (prompt caching у GPT-5.1 — 24 часа)
- Rate limiting per customer
- Cost monitoring dashboard

### 3. Feedback Loop
После каждого разговора:
- Thumbs up/down от клиента
- Agent review (для сложных кейсов)
- Автоматический сбор "плохих" conversations в test set
- Это закрывает цикл: production → eval → improvement → production

### 4. Compliance & Data Privacy
- Чат содержит PII (имена, адреса, email)
- GDPR/CCPA compliance если есть европейские/калифорнийские клиенты
- Data retention policies
- Audit trail для всех действий AI

### 5. Fallback Strategy
- Что если OpenAI API недоступен? Fallback на Claude (или наоборот)
- Что если Zoho API недоступен? Graceful degradation: "Я могу ответить на вопросы, но не могу выполнить действия сейчас"
- Offline mode: заготовленные ответы для critical path

### 6. Analytics Dashboard
Не просто метрики, а actionable insights:
- Какие категории AI решает лучше всего? Расширяем auto-send
- Какие вопросы повторяются? Улучшаем FAQ/knowledge base
- Где AI ошибается? Обновляем промпты/guardrails
- ROI: сколько человеко-часов экономит AI?

### 7. Multi-language Support
Lev Haolam — международный бизнес. Нужна поддержка минимум English + потенциально Hebrew, Spanish, French. И GPT-5.x и Claude хороши в multilingual, но нужно тестировать quality per language.

### 8. Staging Environment
Полный staging pipeline: staging Zoho (sandbox) + staging Agno agent + staging widget. Чтобы тестировать action tools без влияния на production данные.

---

## Итоговый рекомендуемый стек

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION LAYER                          │
│                                                             │
│  [Chat Widget]          [AgentOS API]        [Channels]     │
│   React/JS embed  ←→  FastAPI + SSE     ←→  WhatsApp/Email │
│   (custom)             50+ endpoints          (Chatwoot)    │
│                              │                              │
│                    ┌─────────┼──────────┐                   │
│                    ▼         ▼          ▼                   │
│              [LLM Models]  [Tools]   [Knowledge]            │
│              GPT-5.1       Zoho API   Pinecone              │
│              Claude 4.5    Supabase   PostgreSQL            │
│              (via Agno)    n8n hooks  (RAG)                 │
│                                                             │
│              [Learning Machine]                              │
│              User profiles, memories, cross-user learnings  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                AGNO CONTROL PLANE (os.agno.com)              │
│                    Подключается напрямую из браузера          │
│                    Zero egress — данные остаются у тебя       │
│                                                             │
│  [Chat/Playground]     [Traces/Monitoring]   [Studio]       │
│   Тест агентов          Tool calls, latency   Visual agent  │
│   в реальном времени    cost, reasoning        builder      │
│                                               Version ctrl   │
│  [Sessions]            [Memory/Learnings]    [Evals]        │
│   Все сессии            User profiles         Accuracy,     │
│   пользователей         Accumulated знания    Reliability,  │
│                                               Performance   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│             РАСШИРЕННЫЙ EVAL (опционально, Phase 3+)         │
│                                                             │
│  [Agenta] — если нужно:                                     │
│   - Side-by-side model comparison на больших test sets       │
│   - LLM-as-Judge evaluation pipeline                        │
│   - CSV import исторических тикетов                         │
│   - Human annotation workflow                               │
│   - A/B testing промптов                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ANALYTICS LAYER (Dash)                     │
│                                                             │
│  [Agno Dash Agent]                                          │
│   Natural language → SQL → Insights                         │
│   - Self-learning (Learning Machine)                        │
│   - 6 слоёв контекста (schema, rules, patterns, learnings)  │
│   - Grounded SQL генерация                                  │
│   - Интерпретация результатов, а не просто цифры            │
│                                                             │
│   UI: AgentOS Web (os.agno.com) / Custom Admin Panel        │
│   Data: Supabase PostgreSQL (все таблицы поддержки)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE                            │
│                                                             │
│  Agno AgentOS (Docker/Cloud) — единая платформа              │
│  Agno Dash (Docker, self-learning analytics)                │
│  Agenta (Docker, опционально для расширенных evals)          │
│  Supabase (PostgreSQL + Auth)                               │
│  Pinecone (Vector Store)                                    │
│  Vercel (Widget hosting) / CDN                              │
│  n8n (Email pipeline, monitoring, background jobs)          │
└─────────────────────────────────────────────────────────────┘
```

---

## Roadmap (обновлённый)

### Phase 0: Foundation (2-3 недели)
- [ ] Развернуть Agno AgentOS с базовым support agent (Docker)
- [ ] Подключить Pinecone knowledge base (FAQ)
- [ ] Подключить Control Plane UI (os.agno.com) — playground + tracing сразу
- [ ] Настроить Registry (tools, models) для Studio
- [ ] Создать первый test case набор, прогнать через built-in evals

### Phase 1: Agent Tuning + Evals (2-3 недели)
- [ ] Настроить промпты для каждой из 10 категорий
- [ ] Тестировать через Control Plane Chat — разные сценарии
- [ ] Использовать Agno Evals для accuracy/reliability/performance
- [ ] Сравнить GPT-5.1 vs Claude Sonnet 4.5 (через Registry — переключение model одной строкой)
- [ ] Определить лучшую модель per category

### Phase 2: Chat Widget + Read-only (2-3 недели)
- [ ] Создать embeddable React widget
- [ ] Подключить к AgentOS через AI SDK interface (`interfaces=[AISdk()]`)
- [ ] Реализовать customer identification (email verification)
- [ ] Lookup tools (read-only): подписка, доставка, история

### Phase 3: Action Tools (3-4 недели)
- [ ] Mock API для действий (пока IT не готов)
- [ ] Реализовать confirmation UI в виджете
- [ ] Pause/skip subscription tool
- [ ] Change address/frequency tool
- [ ] Report damage tool
- [ ] Safety guardrails для всех action tools

### Phase 4: Retention + Escalation (2-3 недели)
- [ ] Retention flow (перенести логику из n8n)
- [ ] Outstanding detection
- [ ] Smart escalation с контекстом
- [ ] Encrypted cancel links

### Phase 5: Production + Analytics (2-3 недели)
- [ ] Production deploy с A/B testing
- [ ] Мониторинг через Agno Control Plane (traces, cost, latency)
- [ ] Feedback loop: production → eval → improvement
- [ ] Fallback strategy (model/API failover)
- [ ] (Опционально) Добавить Agenta для массового model comparison на CSV test sets

### Phase 5b: Dash Analytics Agent (1-2 недели, параллельно с Phase 5)
- [ ] Развернуть Agno Dash (Docker) с подключением к Supabase
- [ ] Создать knowledge: `tables/*.json` для всех таблиц поддержки
- [ ] Написать query patterns: resolution rate, AI vs Human, воронка тикетов, stuck tickets
- [ ] Создать business rules: определения метрик, правила подсчёта, common gotchas
- [ ] Загрузить knowledge, протестировать базовые вопросы
- [ ] Подключить UI через AgentOS (os.agno.com) или встроить в admin panel
- [ ] Позволить Learning Machine накопить learnings на реальных вопросах

### Phase 6: Scale (ongoing)
- [ ] Omnichannel через Chatwoot (WhatsApp, email unification)
- [ ] Photo analysis для damaged items
- [ ] Proactive support notifications
- [ ] Multi-language optimization

---

## Ключевые решения для принятия

| # | Решение | Варианты | Рекомендация |
|---|---------|----------|--------------|
| 1 | Agent Framework | Agno / LangGraph / Custom | **Agno** (framework + runtime + UI — всё в одном) |
| 2 | Playground/Monitoring | Agno Control Plane / Agenta / Langfuse | **Agno Control Plane** (встроенный, zero egress) |
| 3 | Расширенные Evals | Agno built-in / Agenta / Braintrust | **Agno built-in** → Agenta позже если нужны CSV test sets |
| 4 | Chat Widget | Custom React / Chatwoot / готовый | **Custom React** → Chatwoot позже |
| 5 | Primary Model | GPT-5.1 / Claude Sonnet 4.5 | **GPT-5.1** (cost), Claude для retention |
| 6 | Hosting | Vercel / Self-hosted / Cloud | **Docker self-hosted** (Agno) |
| 7 | Mock API для действий | Создать mock / ждать IT | **Создать mock** сразу |
| 8 | Analytics | Dash / Custom dashboard / Metabase | **Agno Dash** (self-learning, natural language) |
