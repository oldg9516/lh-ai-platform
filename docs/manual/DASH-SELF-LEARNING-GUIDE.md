# Руководство: Самообучающийся аналитический чат на базе Agno Dash

> Это руководство описывает архитектуру, компоненты и пошаговую реализацию самообучающегося чата для аналитики, реализованного в проекте Lev Haolam. Цель — перенести эту систему в другой проект с существующим дашбордом и чатом.

---

## 1. Обзор архитектуры

### Что делает система

Агент-аналитик, который:
- Принимает вопросы на естественном языке ("Какой процент решённых обращений?")
- Генерирует SQL-запросы к продовым таблицам (read-only)
- **Самообучается**: запоминает ошибки, сохраняет успешные запросы, накапливает знания
- Стримит ответы в реальном времени через SSE → CopilotKit UI
- Рендерит markdown-таблицы, инсайты, статистику

### Стек

| Компонент | Технология |
|-----------|-----------|
| Агент | Agno SDK 2.5+ (`Agent`, `LearningMachine`, `SQLTools`) |
| LLM | OpenAI GPT-5.2 (через `OpenAIResponses`) |
| Знания (статические) | PgVector (hybrid search: BM25 + semantic) |
| Знания (выученные) | PgVector + `LearningMode.AGENTIC` |
| API | AgentOS (FastAPI, SSE streaming на порту 9000) |
| Фронтенд | Next.js 16 + CopilotKit + AG-UI protocol |
| БД агента | pgvector/pgvector:pg17 (отдельный контейнер) |
| БД данных | PostgreSQL (read-only доступ через SQLAlchemy) |

### Архитектурная схема

```
┌─────────────────────────────┐
│ Frontend (CopilotKit)       │
│ CopilotSidebar agent="dash" │
└──────────┬──────────────────┘
           │ POST /api/copilot
           ▼
┌──────────────────────────────┐
│ Next.js Proxy Route          │
│ CopilotRuntime + HttpAgent   │
│ agents: { dash: HttpAgent }  │
└──────────┬───────────────────┘
           │ Forward to backend
           ▼
┌──────────────────────────────────┐
│ Backend Adapter (FastAPI)        │
│ POST /api/dash-copilot           │
│ Translate AG-UI ↔ AgentOS SSE   │
└──────────┬───────────────────────┘
           │ httpx.stream POST
           ▼
┌──────────────────────────────────────────┐
│ Dash AgentOS (port 9000)                 │
│ Agno Agent + LearningMachine + SQLTools  │
├──────────────────────────────────────────┤
│ ┌─────────────┐  ┌──────────────────┐   │
│ │ dash_knowledge│  │ dash_learnings   │   │
│ │ (статика)    │  │ (автообучение)   │   │
│ └─────────────┘  └──────────────────┘   │
│ ┌─────────────┐  ┌──────────────────┐   │
│ │ SQLTools     │  │ introspect_schema│   │
│ │ (read-only)  │  │ save_query       │   │
│ └─────────────┘  └──────────────────┘   │
└──────────┬───────────────────────────────┘
           │ SQLAlchemy (read-only user)
           ▼
┌──────────────────────┐
│ Production PostgreSQL │
│ (ваши таблицы)       │
└──────────────────────┘
```

---

## 2. Двойная система знаний

Ключевая идея — **две раздельные базы знаний в PgVector**:

### 2.1 Статические знания (`dash_knowledge`)

Загружаются один раз через скрипт. Включают:

**a) Метаданные таблиц** — JSON-файлы с описанием каждой таблицы:
```json
// knowledge/tables/orders.json
{
  "table_name": "orders",
  "description": "Customer orders with amounts and statuses",
  "columns": [
    {"name": "id", "type": "uuid", "description": "Primary key"},
    {"name": "customer_id", "type": "uuid", "description": "FK to customers"},
    {"name": "total_amount", "type": "numeric", "description": "Order total in USD"},
    {"name": "status", "type": "text", "description": "Values: Completed, Pending, Cancelled (CAPITALIZED)"}
  ],
  "use_cases": ["Revenue analysis", "Order frequency", "Average order value"],
  "data_quality_notes": "status values are capitalized: 'Completed' not 'completed'"
}
```

**b) Бизнес-правила и метрики** — определения KPI, gotchas:
```json
// knowledge/business/metrics.json
{
  "metrics": {
    "resolution_rate": "% обращений решённых без эскалации",
    "churn_rate": "% отменённых подписок за период",
    "ltv": "Сумма всех заказов клиента"
  },
  "business_rules": {
    "status_values": "Active/Paused/Cancelled — ЗАГЛАВНАЯ первая буква",
    "eval_decision": "send/draft/escalate — строчные"
  },
  "common_gotchas": [
    "JSONB поля требуют ->>'key' для доступа",
    "cost_usd — numeric, используйте ROUND()",
    "JOIN orders ON customers.id = orders.customer_id"
  ]
}
```

**c) Валидированные SQL-запросы** — шаблоны, проверенные на реальных данных:
```sql
-- knowledge/queries/common_queries.sql

-- name: customer_ltv_top20
-- question: Top 20 customers by lifetime value
SELECT c.email, c.full_name,
       COUNT(o.id) as order_count,
       ROUND(SUM(o.total_amount), 2) as lifetime_value
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.status = 'Completed'
GROUP BY c.id, c.email, c.full_name
ORDER BY lifetime_value DESC
LIMIT 20;
```

### 2.2 Выученные знания (`dash_learnings`)

Агент накапливает **автоматически** через `LearningMode.AGENTIC`:

```
Пользователь: "Покажи статусы подписок"
→ Агент: SELECT status FROM subscriptions WHERE status = 'active'
→ Ошибка: 0 rows (status хранится как 'Active', не 'active')
→ Агент: introspect_schema("subscriptions") — видит реальные значения
→ Агент: Исправляет запрос → SELECT ... WHERE status = 'Active'
→ Агент: save_learning("subscription status is capitalized: 'Active' not 'active'")
→ В следующий раз: поиск по learnings → сразу правильный запрос
```

**Что выучивает агент:**
- Правильные регистры значений в колонках
- Рабочие JOIN-цепочки между таблицами
- Типовые ошибки и их исправления
- Нюансы типов данных (JSONB, numeric precision)

---

## 3. Пошаговая реализация

### Шаг 1: Отдельная БД для агента (PgVector)

Агенту нужна **своя** PostgreSQL с расширением pgvector. Не используйте продовую БД — это для состояния агента, сессий и knowledge base.

```yaml
# docker-compose.yml
dash-db:
  image: pgvector/pgvector:pg17
  environment:
    POSTGRES_USER: dash
    POSTGRES_PASSWORD: ${DASH_DB_PASSWORD:-dash}
    POSTGRES_DB: dash
  volumes:
    - dash_db_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U dash"]
    interval: 3s
    retries: 10
```

### Шаг 2: Подключения к БД

**Два подключения — строго раздельные:**

```python
# db/session.py
from agno.storage.postgres import PostgresDb
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

# 1. Подключение к БД агента (PgVector) — для state + knowledge
AGENT_DB_URL = "postgresql+psycopg://dash:dash@dash-db:5432/dash"

def get_agent_db() -> PostgresDb:
    return PostgresDb(id="dash-db", db_url=AGENT_DB_URL)

def create_knowledge(name: str, table_name: str) -> Knowledge:
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=AGENT_DB_URL,
            table_name=table_name,
            search_type=SearchType.hybrid,  # BM25 + semantic
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=get_agent_db(),
    )

# 2. Подключение к продовой БД — read-only через отдельного пользователя
DATA_DB_URL = "postgresql+psycopg://analytics_readonly:password@prod-db:5432/mydb"
```

**Важно: создайте read-only пользователя в продовой БД:**
```sql
CREATE ROLE analytics_readonly WITH LOGIN PASSWORD 'analytics_pass';
GRANT CONNECT ON DATABASE mydb TO analytics_readonly;
GRANT USAGE ON SCHEMA public TO analytics_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_readonly;
```

### Шаг 3: Инструменты агента

**3 кастомных инструмента + SQLTools из Agno:**

```python
# tools/introspect.py
from agno.tools import tool

@tool(name="introspect_schema")
def create_introspect_schema_tool(data_db_url: str):
    """Inspect database schema at runtime."""

    def introspect_schema(table_name: str | None = None) -> str:
        """List tables or describe a specific table with columns, types, sample data.

        Args:
            table_name: Table to inspect. If None, lists all tables.
        """
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(data_db_url)
        inspector = inspect(engine)

        if table_name is None:
            tables = inspector.get_table_names()
            return "Available tables:\n" + "\n".join(f"- {t}" for t in tables)

        columns = inspector.get_columns(table_name)
        result = f"## {table_name}\n\n"
        result += "| Column | Type | Nullable |\n|--------|------|----------|\n"
        for col in columns:
            result += f"| {col['name']} | {col['type']} | {col['nullable']} |\n"

        # Sample data
        with engine.connect() as conn:
            rows = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
            # format as markdown table...

        return result

    return introspect_schema
```

```python
# tools/save_query.py
@tool(name="save_validated_query")
def create_save_validated_query_tool(knowledge: Knowledge):
    """Save a validated SQL query to knowledge base for future reuse."""

    def save_validated_query(
        name: str,
        question: str,
        query: str,
        summary: str,
        tables_used: list[str],
    ) -> str:
        """Save a validated query that produced correct results.

        Args:
            name: Short identifier (e.g., 'customer_ltv_top20')
            question: Natural language question this answers
            query: The validated SQL query
            summary: What this query returns
            tables_used: List of tables referenced
        """
        doc_content = f"""
## {name}
Question: {question}
Tables: {', '.join(tables_used)}
Summary: {summary}

```sql
{query}
```
"""
        # Upsert into PgVector knowledge base
        knowledge.load_documents([
            Document(name=name, content=doc_content)
        ])
        return f"Query '{name}' saved to knowledge base."

    return save_validated_query
```

### Шаг 4: Определение агента

```python
# dash/agent.py
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.learn import LearningMachine, LearningMode, LearnedKnowledgeConfig
from agno.tools.sql import SQLTools

from db.session import get_agent_db, create_knowledge, DATA_DB_URL
from tools.introspect import create_introspect_schema_tool
from tools.save_query import create_save_validated_query_tool

# Два knowledge base — статика и выученное
dash_knowledge = create_knowledge("dash_knowledge", "dash_knowledge")
dash_learnings = create_knowledge("dash_learnings", "dash_learnings")

agent_db = get_agent_db()

# Инструменты
introspect_schema = create_introspect_schema_tool(DATA_DB_URL)
save_validated_query = create_save_validated_query_tool(dash_knowledge)

INSTRUCTIONS = [
    """You are Dash, a self-learning data analyst.

## Workflow
1. ALWAYS start with `search_knowledge_base` and `search_learnings` before writing SQL
2. Write SQL queries (LIMIT 50, no SELECT *, always ORDER BY for rankings)
3. If query fails → use `introspect_schema` → fix → `save_learning` about the error
4. Provide **insights and analysis**, not just raw data
5. If query is reusable → `save_validated_query`

## SQL Rules
- READ-ONLY: only SELECT queries
- LIMIT 50 by default
- Never SELECT * — list specific columns
- Use ROUND() for decimals, NULLIF() for division
- No DROP, DELETE, UPDATE, INSERT

## Available Tables
[Loaded dynamically from knowledge/tables/ JSON files]

## Business Context
[Loaded from knowledge/business/metrics.json]
""",
]

dash = Agent(
    id="dash",
    name="Dash",
    model=OpenAIResponses(id="gpt-5.2"),
    db=agent_db,
    instructions=INSTRUCTIONS,

    # Статические знания (таблицы, правила, запросы)
    knowledge=dash_knowledge,
    search_knowledge=True,  # ОБЯЗАТЕЛЬНО — без этого агент не ищет в knowledge

    # Самообучение
    enable_agentic_memory=True,
    learning=LearningMachine(
        knowledge=dash_learnings,
        learned_knowledge=LearnedKnowledgeConfig(
            mode=LearningMode.AGENTIC,  # Агент сам решает что запоминать
        ),
    ),

    # Инструменты
    tools=[
        SQLTools(db_url=DATA_DB_URL),   # SQL-запросы к продовой БД
        save_validated_query,            # Сохранение успешных запросов
        introspect_schema,               # Интроспекция схемы
    ],

    # Контекст
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
```

### Шаг 5: Запуск через AgentOS

```python
# main.py
import time
import uvicorn
import structlog
from sqlalchemy import create_engine, text

logger = structlog.get_logger()

def wait_for_db(db_url: str, max_retries: int = 30, delay: float = 2.0):
    """Wait for agent DB to be ready."""
    engine = create_engine(db_url, pool_pre_ping=True)
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database ready", attempt=attempt)
            engine.dispose()
            return
        except Exception as exc:
            logger.warning("DB not ready", attempt=attempt, error=str(exc))
            time.sleep(delay)
    raise RuntimeError(f"DB not reachable after {max_retries} attempts")

def create_app():
    from agno.os import AgentOS
    from dash.agent import dash
    from db.session import get_agent_db

    agent_os = AgentOS(
        name="Dash Analytics",
        agents=[dash],
        tracing=True,
        db=get_agent_db(),
    )
    return agent_os

if __name__ == "__main__":
    from db.url import AGENT_DB_URL
    wait_for_db(AGENT_DB_URL)
    agent_os = create_app()
    app = agent_os.get_app()
    uvicorn.run(app, host="0.0.0.0", port=9000)
```

**AgentOS автоматически создаёт эндпоинты:**
- `POST /agents/dash/runs` — запуск агента (SSE streaming)
- `GET /health` — health check

### Шаг 6: Загрузка знаний

```python
# scripts/load_knowledge.py
import json
from pathlib import Path
from agno.document import Document

from db.session import create_knowledge

KNOWLEDGE_DIR = Path(__file__).parent.parent / "dash" / "knowledge"

def load_all():
    knowledge = create_knowledge("dash_knowledge", "dash_knowledge")
    docs = []

    # 1. Метаданные таблиц
    for f in (KNOWLEDGE_DIR / "tables").glob("*.json"):
        data = json.loads(f.read_text())
        content = f"## Table: {data['table_name']}\n{data['description']}\n"
        content += f"Use cases: {', '.join(data.get('use_cases', []))}\n"
        if notes := data.get("data_quality_notes"):
            content += f"Data quality: {notes}\n"
        for col in data.get("columns", []):
            content += f"- {col['name']} ({col['type']}): {col['description']}\n"
        docs.append(Document(name=f"table_{data['table_name']}", content=content))

    # 2. Бизнес-правила
    metrics_file = KNOWLEDGE_DIR / "business" / "metrics.json"
    if metrics_file.exists():
        data = json.loads(metrics_file.read_text())
        content = json.dumps(data, indent=2, ensure_ascii=False)
        docs.append(Document(name="business_rules", content=content))

    # 3. SQL-запросы
    for f in (KNOWLEDGE_DIR / "queries").glob("*.sql"):
        docs.append(Document(name=f"queries_{f.stem}", content=f.read_text()))

    knowledge.load_documents(docs)
    print(f"Loaded {len(docs)} documents into knowledge base")

if __name__ == "__main__":
    load_all()
```

Запуск: `docker compose exec dash python scripts/load_knowledge.py`

### Шаг 7: Адаптер AG-UI ↔ AgentOS (для CopilotKit)

Agno AgentOS стримит в своём формате. CopilotKit ожидает AG-UI protocol. Нужен адаптер:

```python
# api/dash_copilot.py
import httpx
import json
from uuid import uuid4
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from ag_ui.core import (
    RunStartedEvent, RunFinishedEvent,
    TextMessageStartEvent, TextMessageEndEvent,
    TextMessageContentEvent, EventEncoder,
)

router = APIRouter()
DASH_URL = "http://dash:9000"  # AgentOS endpoint

@router.post("/api/dash-copilot")
async def dash_copilot(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    thread_id = body.get("threadId", str(uuid4()))

    # Извлечь последнее сообщение пользователя
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    return StreamingResponse(
        _stream(user_message, thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

async def _stream(message: str, thread_id: str):
    encoder = EventEncoder()
    run_id = str(uuid4())
    message_id = str(uuid4())

    # 1. Run started
    yield encoder.encode(RunStartedEvent(threadId=thread_id, runId=run_id))
    yield encoder.encode(TextMessageStartEvent(messageId=message_id))

    # 2. Stream from Dash AgentOS
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{DASH_URL}/agents/dash/runs",
                data={
                    "message": message,
                    "stream": "true",
                    "session_id": f"copilot_{thread_id}",
                    "user_id": "copilot",
                },
            ) as resp:
                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        if event.get("event") == "RunContent":
                            content = event.get("content", "")
                            if content:
                                yield encoder.encode(
                                    TextMessageContentEvent(
                                        messageId=message_id,
                                        delta=content,
                                    )
                                )
    except Exception as exc:
        yield encoder.encode(
            TextMessageContentEvent(
                messageId=message_id,
                delta=f"Error connecting to analytics agent: {exc}",
            )
        )

    # 3. End
    yield encoder.encode(TextMessageEndEvent(messageId=message_id))
    yield encoder.encode(RunFinishedEvent(threadId=thread_id, runId=run_id))
```

### Шаг 8: Фронтенд (Next.js + CopilotKit)

**Установка:**
```bash
pnpm add @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client
```

**Proxy route (Next.js):**
```typescript
// app/api/copilot/route.ts
import { CopilotRuntime, ExperimentalEmptyAdapter, copilotRuntimeNextJSAppRouterEndpoint } from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";

const agents = {
  dash: new HttpAgent({
    url: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/dash-copilot`,
  }),
};

const runtime = new CopilotRuntime({ agents } as any);
const serviceAdapter = new ExperimentalEmptyAdapter();

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilot",
  });
  return handleRequest(req);
};
```

**Провайдер:**
```tsx
// lib/dash-providers.tsx
"use client";
import { useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export function DashProviders({ children }: { children: React.ReactNode }) {
  const [threadId] = useState(() => crypto.randomUUID());

  return (
    <CopilotKit
      runtimeUrl="/api/copilot"
      agent="dash"
      threadId={threadId}
    >
      <CopilotSidebar
        defaultOpen={true}
        labels={{
          title: "Analytics Chat",
          initial: "Задавайте вопросы по данным. Я генерирую SQL и учусь на ошибках.",
        }}
      >
        {children}
      </CopilotSidebar>
    </CopilotKit>
  );
}
```

**Страница:**
```tsx
// app/(dash)/layout.tsx
import { DashProviders } from "@/lib/dash-providers";

export default function DashLayout({ children }) {
  return <DashProviders>{children}</DashProviders>;
}
```

---

## 4. Как работает самообучение (LearningMode.AGENTIC)

### Цикл обучения

```
Запрос → search_knowledge + search_learnings
  ↓
Генерация SQL (с учётом найденных знаний)
  ↓
Выполнение SQL (SQLTools)
  ├─ Успех → ответ пользователю
  │         → save_validated_query (если запрос полезный/повторяющийся)
  │
  └─ Ошибка → introspect_schema (узнать реальную структуру)
             → Исправить SQL
             → save_learning ("Колонка X имеет тип Y, не Z")
             → Повторить запрос
             → Ответ пользователю
```

### Что хранится в `dash_learnings`

Agno автоматически сохраняет через `save_learning()`:
- **Ошибки типов:** "subscription.status хранит 'Active', не 'active'"
- **JOIN-паттерны:** "Для связи orders → customers используй orders.customer_id = customers.id"
- **Gotchas:** "JSONB поле metadata доступно через metadata->>'key'"
- **Аггрегации:** "Для LTV используй SUM(total_amount) с GROUP BY customer_id"

### Hybrid Search

PgVector с `SearchType.hybrid` объединяет:
- **BM25 (keyword):** точное совпадение "resolution_rate" → находит запрос с таким именем
- **Semantic (embedding):** "процент автоматических ответов" → находит "resolution_rate" по смыслу

---

## 5. Docker-конфигурация

```yaml
# docker-compose.yml
services:
  dash-db:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: dash
      POSTGRES_PASSWORD: ${DASH_DB_PASSWORD:-dash}
      POSTGRES_DB: dash
    volumes:
      - dash_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dash"]
      interval: 3s
      retries: 10

  dash:
    build:
      context: .
      dockerfile: services/dash/Dockerfile
    ports:
      - "9000:9000"
    environment:
      - DB_USER=dash
      - DB_PASS=${DASH_DB_PASSWORD:-dash}
      - DB_HOST=dash-db
      - DB_DATABASE=dash
      - DATA_DB_URL=postgresql+psycopg://analytics_readonly:pass@your-prod-db:5432/yourdb
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      dash-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s

volumes:
  dash_db_data:
```

```dockerfile
# services/dash/Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN apt-get update && apt-get install -y curl libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY services/dash/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/dash/ .
EXPOSE 9000
CMD ["python", "main.py"]
```

```
# requirements.txt
agno[openai,postgres]>=2.5.2
fastapi[standard]>=0.129.0
uvicorn[standard]>=0.32.0
pydantic-settings>=2.6.0
structlog>=24.4.0
sqlalchemy>=2.0.46
psycopg[binary]>=3.1.0
pgvector>=0.4.0
openai>=2.21.0
```

---

## 6. Подготовка знаний для вашего проекта

### Что нужно создать

```
knowledge/
├── tables/           # По 1 JSON на каждую вашу таблицу
│   ├── users.json
│   ├── orders.json
│   └── ...
├── business/
│   └── metrics.json  # KPI, бизнес-правила, gotchas
└── queries/
    └── common.sql    # 5-10 проверенных SQL-запросов
```

### Минимальный шаблон для таблицы

```json
{
  "table_name": "your_table",
  "description": "Что хранит эта таблица",
  "columns": [
    {
      "name": "column_name",
      "type": "text/integer/uuid/timestamp/jsonb",
      "description": "Что означает эта колонка"
    }
  ],
  "use_cases": ["Какие вопросы можно ответить с этой таблицей"],
  "data_quality_notes": "Особенности: регистр значений, NULL-ы, формат дат"
}
```

### Советы

1. **data_quality_notes критичны** — агент будет ошибаться без них (регистр, enum-значения, формат дат)
2. **Валидированные запросы** — начните с 5-10 запросов, которые вы точно знаете что работают
3. **Бизнес-контекст** — объясните что значат метрики в вашем домене
4. **После запуска** — агент сам дополнит knowledge base через `save_validated_query` и `save_learning`

---

## 7. Интеграция с существующим проектом

Поскольку у вас уже есть дашборд и чат:

### Вариант A: Отдельный микросервис (рекомендуется)

Добавьте Dash как отдельный контейнер. Ваш существующий бэкенд добавляет адаптер-эндпоинт, фронтенд добавляет CopilotKit.

**Плюсы:** Независимый деплой, изоляция, свой lifecycle
**Минусы:** Ещё один контейнер

### Вариант B: Встроить агента в существующий бэкенд

Если не хотите отдельный сервис — создайте агента прямо в вашем FastAPI:

```python
# В вашем существующем бэкенде
from agno.agent import Agent
from agno.os import AgentOS

# Создать агента при старте приложения
dash = Agent(...)  # как описано в шаге 4

# Добавить AgentOS как sub-application
agent_os = AgentOS(agents=[dash])
app.mount("/dash", agent_os.get_app())
```

**Плюсы:** Меньше инфраструктуры
**Минусы:** Shared process, сложнее масштабировать

### Чеклист интеграции

- [ ] Создать read-only пользователя в продовой БД
- [ ] Развернуть pgvector контейнер для state агента
- [ ] Описать таблицы в JSON-файлах
- [ ] Написать 5-10 валидированных SQL-запросов
- [ ] Описать бизнес-метрики и gotchas
- [ ] Настроить Agno Agent с LearningMachine
- [ ] Загрузить знания через load_knowledge скрипт
- [ ] Добавить адаптер AG-UI ↔ AgentOS (если CopilotKit)
- [ ] Добавить CopilotKit на фронтенд
- [ ] Протестировать: задать вопрос → SQL → ответ → обучение

---

## 8. Ключевые Agno SDK паттерны

```python
# Импорты
from agno.agent import Agent
from agno.models.openai import OpenAIResponses  # Для GPT-5.x
from agno.learn import LearningMachine, LearningMode, LearnedKnowledgeConfig
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.storage.postgres import PostgresDb
from agno.tools.sql import SQLTools
from agno.os import AgentOS

# Gotchas:
# - search_knowledge=True ОБЯЗАТЕЛЬНО на Agent, иначе knowledge не используется
# - LearningMode.AGENTIC = агент сам решает что запоминать
# - LearningMode.ALWAYS = запоминает всё (для customer memory)
# - Новый Agent на каждый запрос (не переиспользуйте — утечка состояния)
# - instructions — это list[str], каждый элемент = секция system prompt
# - SQLTools автоматически создаёт инструменты run_sql, describe_table и т.д.
```

---

## 9. Тестирование и верификация

```bash
# 1. Запустить сервисы
docker compose up -d dash-db dash

# 2. Загрузить знания
docker compose exec dash python scripts/load_knowledge.py

# 3. Проверить health
curl http://localhost:9000/health

# 4. Тестовый запрос напрямую к AgentOS
curl -X POST http://localhost:9000/agents/dash/runs \
  -d "message=Сколько активных пользователей?&stream=true&user_id=test" \
  --no-buffer

# 5. Проверить что learning работает
# Задать вопрос → получить ошибку → задать снова → агент должен исправиться
```

---

## 10. Ссылки на исходный код (Lev Haolam проект)

| Файл | Описание |
|------|----------|
| `services/dash/dash/agent.py` | Определение агента с LearningMachine |
| `services/dash/db/session.py` | PgVector + dual knowledge setup |
| `services/dash/dash/tools/introspect.py` | Инструмент интроспекции схемы |
| `services/dash/dash/tools/save_query.py` | Сохранение валидированных запросов |
| `services/dash/dash/context/semantic_model.py` | Загрузка метаданных таблиц в промпт |
| `services/dash/dash/context/business_rules.py` | Загрузка бизнес-правил |
| `services/dash/dash/knowledge/` | JSON-файлы таблиц, метрик, SQL-запросов |
| `services/dash/scripts/load_knowledge.py` | Скрипт загрузки знаний в PgVector |
| `services/dash/main.py` | Запуск AgentOS |
| `services/ai-engine/api/dash_copilot.py` | Адаптер AG-UI ↔ AgentOS |
| `services/frontend/lib/dash-providers.tsx` | CopilotKit провайдер для Dash |
| `services/frontend/app/(dash)/` | Фронтенд страницы Dash |
| `services/frontend/app/api/copilot/route.ts` | Next.js proxy route |
