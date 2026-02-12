# Database Migration Plan

## 1. Существующие таблицы (переиспользуем as-is)

Эти таблицы уже работают в Supabase и не требуют изменений:

| Таблица | Использование в новой системе |
|---------|------------------------------|
| `support_threads_data` | Reference: категории, статусы, история тикетов |
| `support_dialogs` | Reference: тексты сообщений, направление, даты |
| `ai_human_comparison` | Reference: AI vs Human метрики, quality scores |
| `ai_answerer_instructions` | **Active**: промпты per category, outstanding rules, eval rules |
| `ai_agent_tasks` | Reference: задачи AI агентов |
| `backlog_reports` | Reference: аналитические отчёты |
| `eval_results` | **Active**: результаты Eval Gate |

---

## 2. Новые таблицы

### Migration 001: chat_sessions

```sql
-- Chat sessions для real-time чата
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Идентификация
    session_id TEXT UNIQUE NOT NULL,           -- sess_abc123
    conversation_id TEXT,                       -- Chatwoot conversation ID
    channel TEXT NOT NULL DEFAULT 'widget',     -- widget, whatsapp, facebook, email, telegram
    
    -- Клиент
    customer_email TEXT,
    customer_name TEXT,
    customer_id TEXT,                           -- Zoho/internal ID
    subscription_id TEXT,
    
    -- Классификация
    primary_category TEXT,                      -- request_subtype
    secondary_category TEXT,                    -- multi-action
    urgency TEXT DEFAULT 'medium',             -- low, medium, high, critical
    language TEXT DEFAULT 'en',
    
    -- Статус
    status TEXT NOT NULL DEFAULT 'active',      -- active, resolved, escalated, closed
    assigned_to TEXT,                           -- 'ai' or human agent ID
    escalation_reason TEXT,
    
    -- AI Decisions
    eval_decision TEXT,                         -- send, draft, escalate
    eval_confidence TEXT,                       -- high, medium, low
    is_outstanding BOOLEAN DEFAULT false,
    outstanding_trigger TEXT,
    
    -- Метрики
    first_response_time_ms INTEGER,
    total_messages INTEGER DEFAULT 0,
    ai_messages INTEGER DEFAULT 0,
    human_messages INTEGER DEFAULT 0,
    resolution_time_seconds INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    
    -- CSAT
    csat_score INTEGER,                        -- 1-5
    csat_comment TEXT
);

CREATE INDEX idx_chat_sessions_email ON chat_sessions(customer_email);
CREATE INDEX idx_chat_sessions_status ON chat_sessions(status);
CREATE INDEX idx_chat_sessions_category ON chat_sessions(primary_category);
CREATE INDEX idx_chat_sessions_created ON chat_sessions(created_at DESC);
CREATE INDEX idx_chat_sessions_conversation ON chat_sessions(conversation_id);
```

### Migration 002: chat_messages

```sql
-- Сообщения в чат-сессиях
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    
    -- Содержимое
    role TEXT NOT NULL,                        -- user, assistant, system, tool
    content TEXT NOT NULL,
    
    -- AI Metadata
    model_used TEXT,                           -- gpt-5.1, claude-sonnet-4-5
    reasoning_effort TEXT,                     -- none, low, medium, high, extended
    tools_used JSONB DEFAULT '[]'::jsonb,      -- ["track_package", "get_subscription"]
    processing_time_ms INTEGER,
    token_count INTEGER,
    cost_usd NUMERIC(10, 6),
    
    -- Actions
    actions_taken JSONB DEFAULT '[]'::jsonb,   -- completed tool results
    actions_pending JSONB DEFAULT '[]'::jsonb,  -- HITL awaiting approval
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at);
CREATE INDEX idx_chat_messages_role ON chat_messages(role);
```

### Migration 003: agent_traces

```sql
-- Трейсы AI pipeline (Router → Support → Outstanding → Eval)
CREATE TABLE agent_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    message_id UUID REFERENCES chat_messages(id),
    
    -- Pipeline step
    step TEXT NOT NULL,                        -- router, identify, support, outstanding, eval_gate
    agent_name TEXT NOT NULL,
    
    -- Input/Output
    input_data JSONB,
    output_data JSONB,
    
    -- Model info
    model TEXT,
    reasoning_effort TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd NUMERIC(10, 6),
    
    -- Performance
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'success',    -- success, error, timeout
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_traces_session ON agent_traces(session_id);
CREATE INDEX idx_agent_traces_step ON agent_traces(step);
CREATE INDEX idx_agent_traces_status ON agent_traces(status);
CREATE INDEX idx_agent_traces_created ON agent_traces(created_at DESC);
```

### Migration 004: tool_executions

```sql
-- Логи выполнения tools (actions)
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    trace_id UUID REFERENCES agent_traces(id),
    
    -- Tool info
    tool_name TEXT NOT NULL,                   -- pause_subscription, track_package, etc.
    tool_input JSONB,
    tool_output JSONB,
    
    -- HITL
    requires_approval BOOLEAN DEFAULT false,
    approval_status TEXT,                      -- pending, approved, rejected
    approved_at TIMESTAMPTZ,
    approved_by TEXT,                          -- 'customer' or agent_id
    
    -- Execution
    status TEXT NOT NULL DEFAULT 'pending',    -- pending, executing, completed, failed
    duration_ms INTEGER,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tool_executions_session ON tool_executions(session_id);
CREATE INDEX idx_tool_executions_tool ON tool_executions(tool_name);
CREATE INDEX idx_tool_executions_status ON tool_executions(status);
CREATE INDEX idx_tool_executions_approval ON tool_executions(approval_status) WHERE requires_approval = true;
```

### Migration 005: learning_records

```sql
-- Agno Learning Machine: паттерны и улучшения
CREATE TABLE learning_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Контекст
    category TEXT,
    subcategory TEXT,
    agent_name TEXT NOT NULL,
    
    -- Learning
    learning_type TEXT NOT NULL,               -- error_fix, pattern, optimization
    trigger_description TEXT,                   -- что вызвало learning
    learned_pattern TEXT NOT NULL,              -- что выучено
    confidence NUMERIC(3, 2),                  -- 0.00 - 1.00
    
    -- Application
    times_applied INTEGER DEFAULT 0,
    success_rate NUMERIC(3, 2),
    
    -- Status
    status TEXT DEFAULT 'active',              -- active, deprecated, merged
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_applied_at TIMESTAMPTZ
);

CREATE INDEX idx_learning_category ON learning_records(category);
CREATE INDEX idx_learning_status ON learning_records(status);
```

---

## 3. Изменения в существующих таблицах

### ai_answerer_instructions — НЕТ изменений
Уже содержит все нужные поля:
- `instruction_1..10` — промпты per category
- `outstanding_rules`, `outstanding_examples`, `outstanding_hard_rules`
- `auto_send_enabled` — флаг per category

Agno будет читать эту таблицу через `database/queries.py`.

### eval_results — уже создана
Используется текущим Eval Agent в n8n. Новая система будет записывать в неё же.

---

## 4. Views для аналитики

```sql
-- Обзор сессий за период
CREATE VIEW v_session_stats AS
SELECT 
    DATE_TRUNC('day', created_at) AS day,
    primary_category,
    channel,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE status = 'resolved') AS resolved,
    COUNT(*) FILTER (WHERE status = 'escalated') AS escalated,
    AVG(first_response_time_ms) AS avg_first_response_ms,
    AVG(resolution_time_seconds) AS avg_resolution_sec,
    AVG(csat_score) AS avg_csat
FROM chat_sessions
GROUP BY 1, 2, 3;

-- Стоимость per category
CREATE VIEW v_cost_by_category AS
SELECT 
    cs.primary_category,
    COUNT(DISTINCT cs.id) AS sessions,
    SUM(cm.cost_usd) AS total_cost,
    AVG(cm.cost_usd) AS avg_cost_per_message,
    SUM(cm.cost_usd) / NULLIF(COUNT(DISTINCT cs.id), 0) AS avg_cost_per_session
FROM chat_sessions cs
JOIN chat_messages cm ON cm.session_id = cs.session_id
WHERE cm.role = 'assistant'
GROUP BY 1;

-- Funnel: Router → Support → Eval → Send
CREATE VIEW v_pipeline_funnel AS
SELECT 
    cs.primary_category,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE cs.eval_decision = 'send') AS auto_sent,
    COUNT(*) FILTER (WHERE cs.eval_decision = 'draft') AS drafted,
    COUNT(*) FILTER (WHERE cs.eval_decision = 'escalate') AS escalated,
    ROUND(
        COUNT(*) FILTER (WHERE cs.eval_decision = 'send') * 100.0 / NULLIF(COUNT(*), 0),
        1
    ) AS auto_send_rate
FROM chat_sessions cs
WHERE cs.created_at >= NOW() - INTERVAL '30 days'
GROUP BY 1;
```

---

## 5. Migration Order

```
1. 001_chat_sessions.sql      — основная таблица сессий
2. 002_chat_messages.sql       — сообщения (FK → sessions)
3. 003_agent_traces.sql        — трейсы pipeline (FK → sessions, messages)
4. 004_tool_executions.sql     — логи tools (FK → sessions, traces)
5. 005_learning_records.sql    — Agno Learning Machine
6. 006_views.sql               — Аналитические views
```

Выполнять через Supabase SQL Editor или через `shared/database/migrations/` скрипт.

---

## 6. Data Flow: Existing ↔ New

```
EXISTING TABLES (n8n pipeline)          NEW TABLES (Agno platform)
┌──────────────────────┐                ┌──────────────────────┐
│ support_threads_data │ ◄── read ────► │ chat_sessions        │
│ support_dialogs      │                │ chat_messages         │
│ ai_human_comparison  │                │ agent_traces          │
│ ai_answerer_         │ ◄── read ──── │ (loads prompts)       │
│   instructions       │                │                      │
│ eval_results         │ ◄── write ──► │ (eval gate results)  │
└──────────────────────┘                └──────────────────────┘

Оба pipeline (n8n email + Agno chat) пишут в eval_results.
Оба читают промпты из ai_answerer_instructions.
Новая система НЕ пишет в support_threads_data / support_dialogs — это email-only.
```
