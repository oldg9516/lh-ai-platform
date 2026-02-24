# Рабочая инструкция: Самообучающийся аналитический чат с Generative UI

> Это руководство описывает **реально работающую** реализацию. Все ошибки из оригинального `DASH-SELF-LEARNING-GUIDE.md` исправлены, код проверен и протестирован.

---

## Отличия от оригинального гайда

Оригинальный `DASH-SELF-LEARNING-GUIDE.md` содержал ошибки, которые не позволяли запуститься:

| Проблема | Было (не работает) | Стало (работает) |
|----------|-------------------|-----------------|
| PyPI пакет AG-UI | `ag-ui-core` | `ag-ui-protocol>=0.1.13` |
| Encoder SSE | `EventEncoder` (не существует) | Кастомная `_encode_sse()` через `model_dump()` |
| Agno storage | `from agno.storage.postgres import PostgresDb` | `from agno.db.postgres import PostgresDb` |
| Agno document | `from agno.document import Document` | `from agno.knowledge.document import Document` |
| Tool pattern | `@tool` декоратор (factory) | Обычные функции (plain functions) |
| pgvector schema | search_path только `dash` | `search_path=dash,public` (pgvector в public) |
| Generative UI | Не было (только markdown таблицы) | `render_chart` tool + AG-UI ToolCall events + `useRenderToolCall` |
| Frontend hook | `useCopilotAction` (v1, "Invalid action") | `useRenderToolCall` (v2, работает) |
| AG-UI events | Только text streaming | Text + `ToolCallStart` → `ToolCallArgs` → `ToolCallEnd` |
| Safety guards | Не было | `ReadOnlySQLTools` + Topic Guard в instructions |

---

## 1. Архитектура

```
┌─────────────────────────────┐
│ Frontend (Next.js)          │
│ CopilotKit + useRenderToolCall │
│ (Recharts generative UI)    │
└──────────┬──────────────────┘
           │ POST /api/copilot
           ▼
┌──────────────────────────────┐
│ Next.js Proxy Route          │
│ CopilotRuntime + HttpAgent   │
│ + Auth guard                 │
└──────────┬───────────────────┘
           │ Forward SSE
           ▼
┌──────────────────────────────────┐
│ AG-UI ↔ AgentOS Adapter         │
│ POST /api/dash-copilot           │
│ Translates AgentOS SSE → AG-UI  │
│ + ToolCall events for charts    │
└──────────┬───────────────────────┘
           │ httpx.stream
           ▼
┌──────────────────────────────────────────┐
│ Agno AgentOS (port 9000, /dash-os)       │
│ Agent + LearningMachine + Tools          │
├──────────────────────────────────────────┤
│ Tools:                                   │
│ ├── ReadOnlySQLTools (blocks writes)     │
│ ├── introspect_schema                    │
│ ├── save_validated_query                 │
│ └── render_chart (generative UI)         │
│                                          │
│ Knowledge:                               │
│ ├── dash_knowledge (static, PgVector)    │
│ └── dash_learnings (auto, AGENTIC mode)  │
└──────────┬───────────────────────────────┘
           │ SQLAlchemy (read-only)
           ▼
┌──────────────────────┐
│ Production PostgreSQL │
└──────────────────────┘
```

---

## 2. Backend (Python в Docker)

### 2.1 Структура файлов

```
services/dash/
├── Dockerfile
├── requirements.txt
├── main.py                       # FastAPI: AgentOS + AG-UI adapter
├── db/
│   ├── __init__.py
│   ├── url.py                    # DB URLs из env vars
│   └── session.py                # PgVector + dual knowledge
├── dash/
│   ├── __init__.py
│   ├── agent.py                  # Agent definition
│   ├── instructions.py           # System prompt
│   └── tools/
│       ├── __init__.py
│       ├── sql_readonly.py       # ReadOnlySQLTools (блокирует INSERT/UPDATE/DELETE)
│       ├── introspect.py         # Schema introspection
│       ├── save_query.py         # Save validated queries
│       └── render_chart.py       # Generative UI chart tool
├── scripts/
│   └── load_knowledge.py         # Load knowledge into PgVector
└── dash/knowledge/               # JSON/SQL файлы знаний
    ├── tables/*.json
    ├── business/metrics.json
    └── queries/*.sql
```

### 2.2 requirements.txt

```
agno[openai,postgres]>=2.5.2
fastapi[standard]>=0.129.0
uvicorn[standard]>=0.32.0
httpx>=0.28.0
pydantic-settings>=2.6.0
structlog>=24.4.0
sqlalchemy>=2.0.46
psycopg[binary]>=3.1.0
pgvector>=0.4.0
openai>=2.21.0
ag-ui-protocol>=0.1.13
```

> **ВАЖНО**: Пакет называется `ag-ui-protocol`, НЕ `ag-ui-core`.

### 2.3 Dockerfile

```dockerfile
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

### 2.4 docker-compose.yml

```yaml
services:
  dash:
    build:
      context: .
      dockerfile: services/dash/Dockerfile
    ports:
      - "9000:9000"
    env_file:
      - .env
    environment:
      - AGENT_DB_URL=${DASH_AGENT_DB_URL}
      - DATA_DB_URL=${DASH_DATA_DB_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s
    restart: unless-stopped
```

### 2.5 Environment Variables

```bash
# БД агента — schema для PgVector (state, knowledge, learnings)
# Если pgvector установлен в public schema, добавьте public в search_path!
DASH_AGENT_DB_URL=postgresql+psycopg://user:pass@host:5432/db?options=-csearch_path%3Ddash,public

# БД данных — read-only доступ к продовым таблицам
DASH_DATA_DB_URL=postgresql+psycopg://readonly_user:pass@host:5432/db

# OpenAI
OPENAI_API_KEY=sk-...
```

### 2.6 db/url.py

```python
import os

AGENT_DB_URL = os.environ["AGENT_DB_URL"]
DATA_DB_URL = os.environ["DATA_DB_URL"]
```

### 2.7 db/session.py

```python
from agno.db.postgres import PostgresDb          # НЕ agno.storage.postgres!
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

from db.url import AGENT_DB_URL

def get_agent_db() -> PostgresDb:
    return PostgresDb(id="dash-db", db_url=AGENT_DB_URL)

def create_knowledge(name: str, table_name: str) -> Knowledge:
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=AGENT_DB_URL,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=get_agent_db(),
    )

dash_knowledge = create_knowledge("dash_knowledge", "dash_knowledge")
dash_learnings = create_knowledge("dash_learnings", "dash_learnings")
```

### 2.8 Tools — обычные функции (НЕ @tool decorator)

> **ВАЖНО**: `@tool` декоратор из Agno оборачивает функцию в объект `Function`, делая factory-функции не вызываемыми. Используйте обычные Python-функции.

**tools/sql_readonly.py** — блокирует INSERT/UPDATE/DELETE/DROP:

```python
import re
from agno.tools.sql import SQLTools

_WRITE_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|"
    r"REPLACE|MERGE|UPSERT|COPY|CALL|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

class ReadOnlySQLTools(SQLTools):
    def run_sql_query(self, query: str) -> str:
        stripped = query.strip().lstrip("(")
        if _WRITE_PATTERNS.search(stripped.split("--")[0].split("/*")[0]):
            return "ERROR: Only SELECT queries are allowed."
        return super().run_sql_query(query)
```

**tools/introspect.py** — интроспекция schema:

```python
from db.url import DATA_DB_URL

def introspect_schema(table_name: str | None = None) -> str:
    """List tables or describe a specific table with columns, types, sample data."""
    from sqlalchemy import create_engine, inspect, text
    engine = create_engine(DATA_DB_URL)
    inspector = inspect(engine)

    if table_name is None:
        tables = inspector.get_table_names(schema="public")
        views = inspector.get_view_names(schema="public")
        result = "## Available Tables\n\n"
        for t in sorted(tables):
            result += f"- {t}\n"
        if views:
            result += "\n## Views\n\n"
            for v in sorted(views):
                result += f"- {v}\n"
        engine.dispose()
        return result

    columns = inspector.get_columns(table_name, schema="public")
    result = f"## {table_name}\n\n| Column | Type | Nullable |\n|--------|------|----------|\n"
    for col in columns:
        result += f"| {col['name']} | {col['type']} | {col['nullable']} |\n"
    # + sample data, foreign keys, indexes...
    engine.dispose()
    return result
```

**tools/save_query.py** — сохранение валидированных запросов:

```python
from agno.knowledge.document import Document    # НЕ agno.document!
from db.session import dash_knowledge

def save_validated_query(name: str, question: str, query: str, summary: str, tables_used: list[str]) -> str:
    """Save a validated SQL query to the knowledge base."""
    doc_content = f"## {name}\nQuestion: {question}\nTables: {', '.join(tables_used)}\nSummary: {summary}\n\n```sql\n{query}\n```\n"
    dash_knowledge.load_documents([Document(name=name, content=doc_content)])
    return f"Query '{name}' saved to knowledge base."
```

**tools/render_chart.py** — generative UI (фронт рисует, бэк отдаёт данные):

```python
import json

def render_chart(chart_type: str, title: str, data: str, x_key: str, y_keys: str) -> str:
    """Display an interactive chart in the chat UI.

    Args:
        chart_type: One of 'line', 'bar', 'area', 'pie'.
        title: Chart title.
        data: JSON array of objects (data points).
        x_key: Key name for X axis.
        y_keys: Comma-separated key names for Y axis values.
    """
    parsed = json.loads(data)
    y_list = [k.strip() for k in y_keys.split(",")]
    return json.dumps({
        "chart_type": chart_type, "title": title,
        "data": parsed, "x_key": x_key, "y_keys": y_list, "rendered": True,
    })
```

### 2.9 Agent Definition

```python
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.learn import LearningMachine, LearningMode, LearnedKnowledgeConfig
from dash.tools.sql_readonly import ReadOnlySQLTools
from dash.tools.render_chart import render_chart

dash = Agent(
    id="dash",
    name="Dash",
    model=OpenAIResponses(id="gpt-5.1"),
    db=agent_db,
    instructions=INSTRUCTIONS,
    knowledge=dash_knowledge,
    search_knowledge=True,                        # ОБЯЗАТЕЛЬНО!
    enable_agentic_memory=True,
    learning=LearningMachine(
        knowledge=dash_learnings,
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
    tools=[
        ReadOnlySQLTools(db_url=DATA_DB_URL),     # Read-only SQL
        save_validated_query,
        introspect_schema,
        render_chart,                              # Generative UI
    ],
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)
```

### 2.10 AG-UI Adapter — ключевой компонент

Адаптер транслирует AgentOS SSE → AG-UI protocol для CopilotKit.

**Обычный текст**: `RunContent` → `TextMessageContentEvent`

**Generative UI (графики)**: Когда агент вызывает `render_chart`, AgentOS отправляет `ToolCallCompleted`. Адаптер перехватывает это и отправляет 3 AG-UI события:

```
ToolCallStartEvent  — имя tool + ID
ToolCallArgsEvent   — JSON с chart_type, data, x_key, y_keys
ToolCallEndEvent    — сигнал завершения
```

> **ВАЖНО**: `ToolCallEndEvent` НЕ имеет поля `result`. Данные передаются через `ToolCallArgsEvent.delta`.

```python
from ag_ui.core import (
    RunStartedEvent, RunFinishedEvent,
    TextMessageStartEvent, TextMessageEndEvent, TextMessageContentEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,    # все три!
    EventType,
)

FRONTEND_TOOLS = {"render_chart"}

def _encode_sse(event) -> str:
    """Кастомный encoder — EventEncoder из ag-ui-protocol НЕ существует."""
    data = event.model_dump(by_alias=True, exclude_none=True)
    data["type"] = event.type if isinstance(event.type, str) else event.type.value
    return f"data: {json.dumps(data)}\n\n"
```

При обнаружении `ToolCallCompleted` для `render_chart`:
```python
# End text if in progress
if text_started:
    yield _encode_sse(TextMessageEndEvent(...))
    text_started = False

# Parse result and build args payload
result_data = json.loads(tool_result)
args_payload = json.dumps({
    "chart_type": result_data.get("chart_type", "bar"),
    "title": result_data.get("title", ""),
    "data": json.dumps(result_data.get("data", [])),    # data как JSON-строка!
    "x_key": result_data.get("x_key", ""),
    "y_keys": ",".join(result_data.get("y_keys", [])),
})

# Emit: Start → Args → End
yield _encode_sse(ToolCallStartEvent(type=EventType.TOOL_CALL_START, toolCallId=id, toolCallName="render_chart"))
yield _encode_sse(ToolCallArgsEvent(type=EventType.TOOL_CALL_ARGS, toolCallId=id, delta=args_payload))
yield _encode_sse(ToolCallEndEvent(type=EventType.TOOL_CALL_END, toolCallId=id))
```

### 2.11 main.py

```python
from agno.os import AgentOS
from dash.agent import dash
from api.dash_copilot import router as copilot_router

app = FastAPI()
app.get("/health")(lambda: {"status": "ok"})

agent_os = AgentOS(name="Dash", agents=[dash], tracing=True, db=get_agent_db())
app.mount("/dash-os", agent_os.get_app())     # AgentOS endpoints
app.include_router(copilot_router)            # AG-UI adapter

uvicorn.run(app, host="0.0.0.0", port=9000)
```

---

## 3. Frontend (Next.js + CopilotKit)

### 3.1 Пакеты

```bash
pnpm add @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client recharts
```

### 3.2 next.config.ts — обязательно!

CopilotKit runtime зависит от pino, который не бандлится в Next.js:

```typescript
const nextConfig = {
  serverExternalPackages: ['@copilotkit/runtime', 'pino', 'thread-stream'],
  // ...
}
```

### 3.3 Proxy Route (app/api/copilot/route.ts)

```typescript
import { CopilotRuntime, ExperimentalEmptyAdapter, copilotRuntimeNextJSAppRouterEndpoint } from '@copilotkit/runtime'
import { HttpAgent } from '@ag-ui/client'

const DASH_BACKEND_URL = process.env.DASH_BACKEND_URL || 'http://localhost:9000'

const agents = {
  dash: new HttpAgent({ url: `${DASH_BACKEND_URL}/api/dash-copilot` }),
}

const runtime = new CopilotRuntime({ agents } as any)
const serviceAdapter = new ExperimentalEmptyAdapter()  // LLM на стороне Python, не Next.js

export const POST = async (req: NextRequest) => {
  // Добавьте auth guard если нужно
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime, serviceAdapter, endpoint: '/api/copilot',
  })
  return handleRequest(req)
}
```

### 3.4 Chat Component с Generative UI

**Ключевой паттерн**: `useRenderToolCall` регистрирует render-only renderer для backend tool calls.

> **НЕ используйте** `useCopilotAction` с `available: 'disabled'` — это v1 API, который выбрасывает "Invalid action configuration" если нет `handler`.
>
> **Используйте** `useRenderToolCall` из `@copilotkit/react-core` — это v2 API для render-only tool calls.

```tsx
'use client'
import { CopilotKit, useRenderToolCall } from '@copilotkit/react-core'
import { CopilotChat } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, ... } from 'recharts'

function DashChatActions({ labels }) {
  // Регистрируем renderer для render_chart tool calls от бэкенда
  useRenderToolCall({
    name: 'render_chart',
    description: 'Display an interactive chart',
    parameters: [
      { name: 'chart_type', type: 'string', description: 'line, bar, area, pie' },
      { name: 'title', type: 'string', description: 'Chart title' },
      { name: 'data', type: 'string', description: 'JSON array' },
      { name: 'x_key', type: 'string', description: 'X axis key' },
      { name: 'y_keys', type: 'string', description: 'Comma-separated Y keys' },
    ],
    render: ({ status, args }) => {
      // args приходят из ToolCallArgsEvent
      // data — JSON-строка, нужно JSON.parse()
      let chartData = null
      try {
        if (args?.data) {
          chartData = JSON.parse(args.data as string)
        }
      } catch {}

      if (status === 'inProgress' && !chartData) {
        return <div>Generating chart...</div>
      }
      if (!chartData?.length) {
        return <div>No chart data</div>
      }

      const yKeys = args.y_keys?.split(',').map(k => k.trim()) || []

      // Рендерим Recharts компонент
      switch (args.chart_type) {
        case 'bar':
          return (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData}>
                <XAxis dataKey={args.x_key} />
                <YAxis />
                <Tooltip />
                {yKeys.map((key, i) => <Bar key={key} dataKey={key} fill={COLORS[i]} />)}
              </BarChart>
            </ResponsiveContainer>
          )
        case 'line': // ... LineChart
        case 'pie':  // ... PieChart
      }
    },
  })

  return <CopilotChat labels={labels} className='h-full' />
}

// Обёртка — useRenderToolCall ДОЛЖЕН быть внутри <CopilotKit>
export function DashChat() {
  return (
    <CopilotKit runtimeUrl="/api/copilot" agent="dash" threadId={...}>
      <DashChatActions labels={...} />
    </CopilotKit>
  )
}
```

---

## 4. Поток данных для Generative UI (графики)

```
1. Пользователь: "Покажи график тредов по дням"

2. Agno Agent (Python):
   → Генерирует SQL: SELECT date_trunc('day', created_at) AS day, COUNT(*) ...
   → Выполняет через ReadOnlySQLTools
   → Вызывает render_chart(chart_type="line", data="[{...}]", ...)

3. AgentOS SSE:
   → event: ToolCallCompleted, tool_name: "render_chart", result: "{chart_type, data, ...}"

4. AG-UI Adapter (dash_copilot.py):
   → Видит render_chart в FRONTEND_TOOLS
   → Emit: TOOL_CALL_START → TOOL_CALL_ARGS(delta=args_json) → TOOL_CALL_END

5. CopilotKit Runtime (Next.js proxy):
   → Прокидывает SSE events на фронтенд

6. useRenderToolCall (React):
   → Матчит TOOL_CALL_START name="render_chart"
   → Парсит args из TOOL_CALL_ARGS
   → Вызывает render({ status: "inProgress", args: {chart_type, data, ...} })
   → После TOOL_CALL_END: status → "complete"

7. DashChart (Recharts):
   → Рендерит bar/line/area/pie chart inline в чате
```

---

## 5. Safety Guards

### ReadOnlySQLTools

Наследуется от `SQLTools`, перехватывает `run_sql_query()` и блокирует regex-паттерном любые non-SELECT запросы (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE и др.).

### Topic Guard (в instructions)

Агент отказывается отвечать на вопросы не по теме (погода, шутки, код, и т.д.) — но делает это вежливо, предлагая помощь с аналитикой по данным.

---

## 6. Чеклист для переноса в другой проект

- [ ] PostgreSQL с pgvector extension (`CREATE EXTENSION IF NOT EXISTS vector`)
- [ ] Отдельная schema для агента (или отдельная БД)
- [ ] search_path включает schema с pgvector (`options=-csearch_path%3Ddash,public`)
- [ ] Read-only user для продовой БД
- [ ] JSON-файлы knowledge (tables, business rules, validated queries)
- [ ] Docker: `services/dash/` с Dockerfile + requirements.txt
- [ ] Environment: AGENT_DB_URL, DATA_DB_URL, OPENAI_API_KEY
- [ ] `docker compose up -d dash` → `curl localhost:9000/health`
- [ ] `docker exec dash python scripts/load_knowledge.py`
- [ ] Frontend: `pnpm add @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client`
- [ ] next.config: `serverExternalPackages: ['@copilotkit/runtime', 'pino', 'thread-stream']`
- [ ] API route: `/api/copilot/route.ts`
- [ ] Chat component: `useRenderToolCall` + Recharts
- [ ] Тест: вопрос → SQL → ответ + график → самообучение

---

## 7. Версии пакетов (проверено, работает)

### Python
| Пакет | Версия |
|-------|--------|
| agno | 2.5.3+ |
| ag-ui-protocol | 0.1.13+ |
| fastapi | 0.129+ |
| httpx | 0.28+ |
| sqlalchemy | 2.0.46+ |
| psycopg[binary] | 3.1+ |
| pgvector | 0.4+ |

### npm
| Пакет | Версия |
|-------|--------|
| @copilotkit/react-core | 1.51.4 |
| @copilotkit/react-ui | 1.51.4 |
| @copilotkit/runtime | 1.51.4 |
| @ag-ui/client | 0.0.45 |
| recharts | 2.x |

---

## 8. Известные gotchas

1. **`EventEncoder` не существует** в `ag-ui-protocol` — используйте `model_dump()` + `json.dumps()`
2. **`@tool` декоратор** оборачивает в `Function` object — обычные функции работают как tools
3. **pgvector в public schema** — если agent DB url указывает на другую schema, добавьте `public` в search_path
4. **`ToolCallEndEvent` НЕ имеет поля `result`** — данные передаются через `ToolCallArgsEvent.delta`
5. **`useCopilotAction` без `handler`** — выбрасывает "Invalid action configuration". Используйте `useRenderToolCall`
6. **pino bundling** — CopilotKit runtime зависит от pino, нужен `serverExternalPackages` в next.config
7. **Пароли с спецсимволами** в DB URL — нужно URL-encode (`[` → `%5B`, `#` → `%23` и т.д.)
