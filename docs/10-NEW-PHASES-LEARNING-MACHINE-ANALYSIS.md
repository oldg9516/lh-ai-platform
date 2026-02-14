# Анализ: Новые фазы проекта и Agno Learning Machine

## Контекст

Пользователь запросил анализ:
1. Изучить новые фазы проекта (Phase 6-10) из PROGRESS.md и docs/08-COPILOTKIT-GENERATIVE-UI.md
2. Оценить применимость Agno Learning Machine для самообучения support агентов, которые отвечают на запросы клиентов

**Current status:** Phase 5 complete (AgentOS Analytics Service operational)

---

## Обзор новых фаз (Phase 6-10)

### Phase 6: Generative UI + HITL (8 недель)

**Цель:** Реализовать Human-in-the-Loop подтверждение для write-операций через CopilotKit framework

**Ключевые компоненты:**

1. **CopilotKit + AG-UI протокол** (открытый стандарт, поддержка Google/AWS/Microsoft)
   - Controlled Generative UI: разработчик создает компоненты, агент выбирает какой показать
   - Streaming: Python backend → React frontend (HTTP SSE или WebSocket)
   - Type-safe: TypeScript + Pydantic

2. **HITL формы для write-операций:**
   - `PauseSubscriptionForm` — выбор месяцев паузы
   - `ChangeAddressForm` — редактирование адреса с валидацией (Google Maps API)
   - `DamageClaimForm` — описание + photo upload (S3/MinIO)
   - `SkipMonthForm` — выбор месяца пропуска
   - `FrequencyChangeForm` — monthly/bi-monthly/quarterly

3. **Informational widgets (no confirmation):**
   - `TrackingCard` — tracking number, carrier, прогресс-бар, карта
   - `OrderHistoryTable` — история заказов с фильтрами
   - `BoxContentsCard` — список продуктов в последней коробке
   - `PaymentHistoryCard` — timeline платежей

4. **Backend AG-UI endpoint:**
   ```python
   @router.post("/api/copilot")
   async def copilot_stream(request):
       async for chunk in agent.arun_stream(message):
           if chunk.type == "tool_call":
               # Отправить frontendToolCall event → React форма
               confirmation = await wait_for_confirmation()
               if confirmation.approved:
                   result = await execute_real_tool()
   ```

5. **Интеграция:**
   - Chatwoot widget embedding (iframe)
   - Tool updates: `@tool(requires_confirmation=True)` в Agno SDK
   - Audit logging: `tool_executions` с `confirmation_timestamp`, `user_approved`
   - Реальные API: Zoho CRM, Pay API, shipping providers

**Преимущества:**
- ✅ Безопасность: ни одна write-операция без явного подтверждения
- ✅ UX: нативные UI компоненты вместо текстовых ссылок
- ✅ Валидация на фронтенде ДО отправки на backend
- ✅ Type-safe, reusable, testable
- ✅ Стандарт AG-UI (не vendor lock-in)

---

### Phase 7: Architecture Refactoring (4 недели)

**Цель:** Улучшить архитектуру для масштабируемости и качества

**Компоненты:**

1. **Context Builder** (`agents/context_builder.py`)
   - Customer profile injection (name, join_date, LTV)
   - Active subscription (frequency, next_charge)
   - Recent orders summary (last 3)
   - Smart history truncation (старые → summarize)
   - Outstanding context injection

2. **Sentiment tracking в Router**
   - Добавить `sentiment` field: positive/neutral/negative/frustrated
   - Добавить `escalation_signal` field (customer wants human)
   - Enhanced escalation context: structured handoff note, smart assignee routing

3. **Pinecone reranking**
   - Initial search: top_k=20 (hybrid)
   - Reranking: bge-reranker-v2-m3, top_n=5
   - Metadata filtering: product, language, freshness

4. **Orchestrator Pattern** (`agents/orchestrator.py`)
   - Вынести всю логику из monolith `api/routes.py`
   - Clean separation: router → context → agent → eval → assembly → persistence
   - Parallel execution: agent + outstanding detection (asyncio.gather)

5. **Model Optimization**
   - Router: GPT-5.1 → GPT-5-mini (90% ⬇️ cost)
   - Eval Gate: GPT-5.1 → Claude Sonnet 4.5 (better judgment)
   - Support (retention): GPT-5.1 → Sonnet 4.5 + reasoning (50% ⬆️ quality)
   - Benchmarking на golden dataset для каждой модели

---

### Phase 8: Multi-Agent Teams (5 недель)

**Цель:** Перейти от single-agent factory к multi-agent teams с узкой специализацией

**Team Architecture:**

1. **Intake Agent** (GPT-5-mini)
   - Triage + routing decision
   - Sentiment analysis
   - Initial classification

2. **Specialist Agents:**
   - **Billing Specialist** — payment, refund, subscription questions
   - **Shipping Specialist** — delivery, tracking, address
   - **Retention Specialist** — pause, cancel, downsell (Sonnet 4.5 + reasoning)
   - **Quality Specialist** — damage, leaking, replacement

3. **QA Agent** (Claude Sonnet 4.5)
   - Заменяет Eval Gate
   - Better judgment для tone/accuracy/safety
   - Retry logic: QA reject → specialist refines → QA re-check

4. **Integration:**
   - Agno Team orchestration
   - Inter-agent communication (shared context)
   - A/B testing: single-agent vs team (10% traffic)
   - Langfuse comparison: resolution rate, latency, quality scores

---

### Phase 9: AI Ops & Continuous Learning (Ongoing)

**Цель:** Мониторинг, feedback loop, автоматическое улучшение

**Компоненты:**

1. **AI Ops Dashboard** (`services/analytics/ai_ops.py`)
   - `get_failure_patterns()` — топ причины draft/escalate
   - `get_knowledge_gaps()` — вопросы с низкой accuracy
   - `get_tone_drift()` — tracking тона по времени
   - `suggest_prompt_updates()` — ML-based рекомендации

2. **Метрики мониторинга:**
   - AI Resolution Rate (target >70%)
   - Eval Gate Pass Rate (target >80%)
   - Escalation Rate (target <10%)
   - Average Confidence (target >0.8)
   - Category Accuracy (per category, >0.75)
   - Response Time p95 (<10s)

3. **Feedback Loop** (`learning/feedback.py`)
   - `collect_human_edit()` — когда human редактирует AI ответ
   - `classify_edit()` — tone, accuracy, safety, completeness
   - `is_recurring_pattern()` — детекция паттернов ошибок
   - `generate_prompt_update()` — предложения по обновлению промптов

4. **Agno Learning Machine** (см. детальный анализ ниже)
   ```python
   learning = LearningMachine(db=get_postgres_db(), scope="support_tools")
   agent = Agent(..., learning=learning, learn_from_errors=True)
   ```

5. **Continuous Evaluation**
   - Daily auto-eval на golden dataset (338 items)
   - Compare с baseline scores
   - Alert если regression >5%

---

### Phase 10: Scale + Production (6 недель)

**Цель:** Full production deployment с gradual rollout

**Компоненты:**

1. **Auto-Send Expansion**
   - Per-category confidence thresholds (retention → 0.9, gratitude → 0.7)
   - Gradual rollout: 10% → 25% → 50% → 100%

2. **Production Monitoring**
   - Langfuse 100% tracing
   - Agno Control Plane integration (os.agno.com)
   - Real-time performance dashboard
   - Cost tracking (per category/model/day)

3. **CRM Integration — Proactive Support**
   - Detect subscription issues BEFORE customer contacts
   - Automated outreach (Chatwoot proactive message)
   - Predictive churn prevention (ML model: predict cancel → offer downsell)

4. **n8n Migration (Gradual)**
   - Phase 10.1: 10% email → AI platform (A/B test)
   - Phase 10.2: 50% email → AI platform
   - Phase 10.3: 100% email → AI platform
   - Fallback: если AI fails → n8n backup pipeline

5. **Feedback Loop v2 (Autonomous)**
   - Production traces → Langfuse eval → автоматическое улучшение промптов (no human in loop)
   - Auto-detect quality regression
   - Auto-rollback к предыдущей версии промптов

---

## 🔴 Критические находки: Agno Learning Machine

### Что это НЕ делает (вопреки ожиданиям из PROGRESS.md)

**Learning Machine НЕ предназначена для автоматического самообучения агентов на основе ошибок.**

Из исследования Agno SDK документации:

❌ **НЕ учится из:**
- Tool execution errors (нет `learn_from_errors` flag или автоматической оптимизации параметров)
- Human corrections в Chatwoot (нет HITL integration с edits)
- Eval results из Langfuse (интеграция только для observability/tracing, не training)
- User feedback (нет системы сбора feedback или quality scoring)
- Response quality issues (нет eval→learning feedback loop)

### Что Learning Machine РЕАЛЬНО делает

✅ **Learning Machine = User Personalization & Memory**, не Self-Improvement

**Компоненты:**

1. **User Profile** — structured user data
   ```python
   {
       "name": "Sarah Cohen",
       "timezone": "Asia/Jerusalem",
       "company": "Lev Haolam",
       "role": "subscriber",
       "subscription_tier": "premium"
   }
   ```

2. **User Memory** — remember customer preferences
   ```python
   UserMemoryConfig(
       max_memories=10,  # Last 10 significant preferences
       memory_types=["preference", "communication_style", "ongoing_projects"]
   )
   ```

3. **Learned Knowledge** — collective insights shared across all users
   - Global knowledge base (не per-user)
   - Accumulates facts discovered during conversations
   - Shared context для всех сессий

4. **Session Context** — conversation-specific planning and state
   - Текущий conversation plan
   - Intermediate results
   - Context для multi-turn

### Конфигурация для Support Platform

```python
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.learn import LearningMachine, UserMemoryConfig

# PostgreSQL backend для Learning Machine
db = PostgresDb(
    db_url=settings.supabase_url,  # Используем существующую Supabase DB
    schema="learning",  # Отдельная схема для learning tables
)

# Learning config
learning = LearningMachine(
    user_profile=True,  # Enable customer profile storage
    user_memory=UserMemoryConfig(
        max_memories=10,  # Помнить 10 последних preferences
        memory_types=["preference", "communication_style", "issues"]
    ),
)

# Support Agent с learning
agent = Agent(
    name="support_shipping",
    model=OpenAIChat(id="gpt-5.1"),
    tools=[track_package, get_subscription],
    db=db,
    learning=learning,
    user_id=customer_email,  # КРИТИЧНО: user_id для персонализации
    instructions=[...],
)
```

**Database tables (auto-created):**
- `learning.agent_profile` — user profiles
- `learning.agent_memory` — user memories
- `learning.agent_knowledge` — learned knowledge
- `learning.agent_sessions` — session context

### Use Cases для Lev Haolam

✅ **Хорошо подходит для:**

1. **Customer Preferences Across Sessions**
   ```
   Session 1: "Я предпочитаю общаться кратко, без деталей"
   → Сохранить в user_memory: communication_style="concise"

   Session 2 (через неделю): Agent автоматически использует краткий стиль
   ```

2. **Recurring Issues Tracking**
   ```
   Session 1: "Посылка опоздала в прошлый раз"
   → Сохранить в user_memory: past_issue="delayed_delivery"

   Session 2: Agent проактивно проверяет tracking и обновляет customer
   ```

3. **Product Preferences**
   ```
   Session 1: "Я не пью алкоголь, только безалкогольные вина"
   → Сохранить в user_profile: product_preference="alcohol_free"

   Session 2: Customization request → Agent автоматически предлагает alcohol-free опции
   ```

4. **Communication Style**
   ```
   Session 1: Customer использует Hebrew
   → Сохранить в user_profile: preferred_language="he"

   Session 2: Agent отвечает на Hebrew (если multi-language support)
   ```

❌ **НЕ подходит для:**
- Автоматическое улучшение tone на основе human corrections
- Оптимизация tool parameters на основе failures
- Learning from eval gate rejections
- Prompt refinement на основе low-accuracy patterns

---

## Рекомендации: Как реализовать Self-Learning для Support Агентов

Для настоящего самообучения нужно построить **custom pipelines**. Agno Learning Machine можно использовать для персонализации, но основной self-learning должен быть custom.

### Стратегия: Dual-Track Approach

**Track 1: Agno Learning Machine (персонализация)**
- Customer preferences across sessions
- Communication style memory
- Product preferences
- Past issues tracking

**Track 2: Custom Learning Pipelines (quality improvement)**
- Eval-driven learning
- Correction learning from human edits
- Tool analytics and optimization
- Few-shot enhancement

---

### 1. Eval-Driven Learning Pipeline

**Цель:** Автоматически улучшать промпты на основе eval results

```python
# learning/eval_driven.py
async def analyze_eval_failures(category: str, days: int = 7):
    """Analyze eval failures for a category to find patterns."""

    # 1. Get failed evals
    failures = await db.query("""
        SELECT er.eval_decision, er.eval_reasoning,
               cs.primary_category, cm.customer_message, cm.agent_response
        FROM eval_results er
        JOIN chat_sessions cs ON er.session_id = cs.session_id
        JOIN chat_messages cm ON cs.session_id = cm.session_id
        WHERE cs.primary_category = %s
          AND er.eval_decision IN ('draft', 'escalate')
          AND er.created_at >= NOW() - INTERVAL '%s days'
        ORDER BY er.created_at DESC
        LIMIT 50
    """, (category, days))

    # 2. Use GPT to extract patterns
    pattern_prompt = f"""
    Analyze these {len(failures)} eval failures for {category} category.

    For each failure, identify:
    1. Root cause (tone, accuracy, safety, completeness)
    2. Common mistake pattern
    3. How to fix it

    Failures:
    {json.dumps([{
        "message": f.customer_message,
        "response": f.agent_response,
        "reason": f.eval_reasoning
    } for f in failures], indent=2)}

    Output as JSON:
    {{
        "patterns": [
            {{"issue": "too formal tone", "frequency": 15, "fix": "use warmer language"}},
            ...
        ],
        "suggested_instruction_updates": ["instruction text", ...]
    }}
    """

    analysis = await openai_client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": pattern_prompt}],
        response_format={"type": "json_object"}
    )

    patterns = json.loads(analysis.choices[0].message.content)

    # 3. If pattern repeats 3+ times, suggest instruction update
    for pattern in patterns["patterns"]:
        if pattern["frequency"] >= 3:
            await create_instruction_update_suggestion(
                category=category,
                issue=pattern["issue"],
                fix=pattern["fix"],
                suggested_instructions=patterns["suggested_instruction_updates"]
            )

    return patterns

# Weekly cron job
async def weekly_instruction_refinement():
    """Run eval-driven learning for all categories."""
    for category in CATEGORY_CONFIG.keys():
        patterns = await analyze_eval_failures(category, days=7)

        # If regression detected, alert
        if len(patterns["patterns"]) > 5:
            await send_alert(f"Category {category} has {len(patterns['patterns'])} recurring issues")
```

---

### 2. Correction Learning Pipeline

**Цель:** Learn from human edits в Chatwoot

```python
# learning/correction_learning.py
from chatwoot.client import ChatwootClient

async def capture_human_correction(conversation_id: int):
    """Capture when human agent edits AI response in Chatwoot."""

    # 1. Get conversation messages
    messages = await chatwoot_client.get_messages(conversation_id)

    # Find AI message + human edit
    ai_message = None
    human_edit = None

    for i, msg in enumerate(messages):
        if msg["sender_type"] == "bot" and msg["private"] == False:
            ai_message = msg
            # Check if next message is human edit (private note)
            if i + 1 < len(messages) and messages[i+1]["sender_type"] == "user" and messages[i+1]["private"]:
                human_edit = messages[i+1]
                break

    if not ai_message or not human_edit:
        return None

    # 2. Classify the correction type
    correction_analysis = await openai_client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{
            "role": "user",
            "content": f"""
            Analyze this human correction of AI response.

            AI Response: {ai_message["content"]}
            Human Edit: {human_edit["content"]}

            Classify the correction type:
            - tone (too formal, too casual, wrong emotion)
            - accuracy (wrong information, missing details)
            - safety (subscription confirmation, refund policy)
            - completeness (missing steps, incomplete answer)

            Output JSON:
            {{
                "type": "tone|accuracy|safety|completeness",
                "specific_issue": "description",
                "key_changes": ["change 1", "change 2"]
            }}
            """
        }],
        response_format={"type": "json_object"}
    )

    correction = json.loads(correction_analysis.choices[0].message.content)

    # 3. Store in correction_patterns table
    await db.execute("""
        INSERT INTO correction_patterns
        (conversation_id, category, ai_response, human_edit, correction_type, specific_issue, key_changes, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """, (
        conversation_id,
        ai_message.get("category"),
        ai_message["content"],
        human_edit["content"],
        correction["type"],
        correction["specific_issue"],
        json.dumps(correction["key_changes"])
    ))

    # 4. Check for recurring patterns
    recurring = await db.query("""
        SELECT correction_type, specific_issue, COUNT(*) as frequency
        FROM correction_patterns
        WHERE category = %s AND created_at >= NOW() - INTERVAL '7 days'
        GROUP BY correction_type, specific_issue
        HAVING COUNT(*) >= 3
        ORDER BY frequency DESC
    """, (ai_message.get("category"),))

    # 5. If pattern repeats 3+ times, create alert
    for pattern in recurring:
        await send_alert(f"Recurring {pattern['correction_type']} issue in {ai_message.get('category')}: {pattern['specific_issue']} ({pattern['frequency']} times)")

# Chatwoot webhook integration
@router.post("/api/webhook/chatwoot/correction")
async def chatwoot_correction_webhook(payload: dict):
    """Triggered when human agent creates private note after AI response."""

    if payload["event"] == "message_created" and payload["message_type"] == "incoming" and payload["private"]:
        # This might be a correction
        await capture_human_correction(payload["conversation"]["id"])
```

---

### 3. Few-Shot Learning Enhancement

**Цель:** Use top corrections as few-shot examples

```python
# agents/support.py (update create_support_agent)
async def create_support_agent(category: str, email: str = None) -> Agent:
    """Create support agent with few-shot learning from corrections."""

    # Get top 5 corrections for this category (best human edits)
    corrections = await db.query("""
        SELECT ai_response, human_edit, specific_issue
        FROM correction_patterns
        WHERE category = %s
          AND correction_type IN ('tone', 'accuracy')
        ORDER BY created_at DESC
        LIMIT 5
    """, (category,))

    # Build few-shot examples
    few_shot_messages = []
    for corr in corrections:
        few_shot_messages.extend([
            {
                "role": "assistant",
                "content": corr.ai_response,
                "metadata": {"issue": corr.specific_issue}
            },
            {
                "role": "user",
                "content": f"[Correction needed: {corr.specific_issue}]. Better response: {corr.human_edit}"
            }
        ])

    # Create agent with few-shot learning + personalization
    agent = Agent(
        name=f"support_{category}",
        model=_resolve_model(category),
        tools=_resolve_tools(category),
        knowledge=_get_knowledge(category),
        instructions=_load_instructions(category),
        additional_input=few_shot_messages,  # Inject corrections as few-shot examples
        user_id=email,
        # Agno Learning Machine для customer personalization
        learning=LearningMachine(
            user_profile=True,
            user_memory=UserMemoryConfig(max_memories=10)
        ) if email else None,
    )

    return agent
```

---

### 4. Tool Analytics Dashboard

**Цель:** Optimize tool parameters на основе execution patterns

```python
# services/analytics/tool_analytics.py
async def analyze_tool_usage(tool_name: str, days: int = 30):
    """Analyze tool execution patterns to find parameter issues."""

    executions = await db.query("""
        SELECT tool_name, tool_args, tool_result,
               success, error_message, execution_time_ms
        FROM tool_executions
        WHERE tool_name = %s
          AND created_at >= NOW() - INTERVAL '%s days'
        ORDER BY created_at DESC
    """, (tool_name, days))

    analysis = {
        "total_executions": len(executions),
        "success_rate": sum(1 for e in executions if e.success) / len(executions),
        "avg_execution_time": sum(e.execution_time_ms for e in executions) / len(executions),
        "common_errors": {},
        "parameter_patterns": {}
    }

    # Analyze errors
    for exec in executions:
        if not exec.success and exec.error_message:
            error_key = exec.error_message[:100]  # First 100 chars
            analysis["common_errors"][error_key] = analysis["common_errors"].get(error_key, 0) + 1

    # Top 5 errors
    analysis["top_errors"] = sorted(
        analysis["common_errors"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # Parameter analysis
    for exec in executions:
        args = json.loads(exec.tool_args) if isinstance(exec.tool_args, str) else exec.tool_args
        for param, value in args.items():
            if param not in analysis["parameter_patterns"]:
                analysis["parameter_patterns"][param] = {"values": {}, "errors": {}}

            value_str = str(value)
            analysis["parameter_patterns"][param]["values"][value_str] = \
                analysis["parameter_patterns"][param]["values"].get(value_str, 0) + 1

            if not exec.success:
                analysis["parameter_patterns"][param]["errors"][value_str] = \
                    analysis["parameter_patterns"][param]["errors"].get(value_str, 0) + 1

    # Generate recommendations
    recommendations = []
    for param, data in analysis["parameter_patterns"].items():
        # Find values with high error rate
        for value, count in data["errors"].items():
            error_rate = count / data["values"].get(value, 1)
            if error_rate > 0.5 and count >= 3:
                recommendations.append(f"Parameter '{param}' with value '{value}' has {error_rate*100:.0f}% error rate. Consider adding validation or updating instructions.")

    analysis["recommendations"] = recommendations
    return analysis
```

---

## Итоговые рекомендации

### Для Phase 9 (AI Ops & Learning)

**1. Использовать Agno Learning Machine ДЛЯ:**
- ✅ Customer personalization (preferences, communication style)
- ✅ User memory across sessions (recurring issues, product preferences)
- ✅ Profile storage (language, timezone, subscription_tier)

**Реализация:**
```python
# Добавить в create_support_agent()
learning = LearningMachine(
    user_profile=True,
    user_memory=UserMemoryConfig(max_memories=10)
) if customer_email else None

agent = Agent(..., learning=learning, user_id=customer_email)
```

**Эффект:** 10-15% улучшение customer experience (personalized responses)

---

**2. Построить Custom Pipelines ДЛЯ:**
- ✅ Eval-driven learning (eval failures → instruction updates)
- ✅ Correction learning (Chatwoot edits → few-shot examples)
- ✅ Tool analytics (execution patterns → parameter guidance)
- ✅ Response quality improvement (eval results → prompt refinement)

**Приоритеты:**
1. **Week 1-2:** Correction Learning Pipeline (highest ROI)
   - Chatwoot webhook для human edits
   - `correction_patterns` table
   - Alert система для recurring issues

2. **Week 3:** Few-Shot Enhancement
   - Inject top 5 corrections в agent context
   - A/B test: few-shot vs baseline

3. **Week 4:** Eval-Driven Learning
   - Weekly analysis на eval failures
   - Automatic instruction update suggestions

4. **Week 5:** Tool Analytics Dashboard
   - Parameter error analysis
   - Recommendations для tool guidance

**Expected Impact:**
- 15-20% reduction в eval failures (from corrections)
- 10-15% improvement в tone consistency (from few-shot)
- 5-10% reduction в tool errors (from analytics)
- Better customer experience (from personalization)

---

**3. Database Schema для Custom Learning:**

```sql
-- Correction patterns table
CREATE TABLE correction_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id INTEGER,
    category TEXT,
    ai_response TEXT,
    human_edit TEXT,
    correction_type TEXT, -- tone, accuracy, safety, completeness
    specific_issue TEXT,
    key_changes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_correction_category_date
ON correction_patterns(category, created_at DESC);

-- Instruction update suggestions
CREATE TABLE instruction_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT,
    current_version INTEGER,
    suggested_version INTEGER,
    issue_pattern TEXT,
    suggested_fix TEXT,
    supporting_examples JSONB, -- Array of correction IDs
    status TEXT, -- pending, approved, rejected, deployed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deployed_at TIMESTAMPTZ
);

-- Learning analytics
CREATE TABLE learning_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type TEXT, -- eval_failure_rate, correction_frequency, tool_error_rate
    category TEXT,
    metric_value FLOAT,
    details JSONB,
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Ответ на вопрос: Применимо ли самообучение Agno Dash для support агентов?

**Короткий ответ: Частично применимо, но с ограничениями.**

### ✅ ЧТО можно использовать:

**Agno Learning Machine** отлично подходит для:
- **Customer personalization** — помнить предпочтения клиентов между сессиями
- **Communication style adaptation** — адаптация под стиль общения клиента
- **Product preferences** — помнить product choices
- **Issue history** — track recurring problems per customer

**Эффект:** Улучшение customer experience на 10-15% за счет персонализации

### ❌ ЧТО НЕ работает:

**Agno Learning Machine НЕ подходит для:**
- Автоматическое улучшение качества ответов
- Learning from eval failures или human corrections
- Tool parameter optimization
- Prompt refinement на основе паттернов ошибок

**Причина:** Learning Machine предназначена для user memory, не для agent self-improvement

### ✅ РЕШЕНИЕ: Гибридный подход

**Dual-Track Strategy:**

1. **Track 1: Agno Learning Machine** (персонализация)
   - Добавить в create_support_agent()
   - Хранить customer preferences в learning.agent_memory
   - Работает out-of-the-box, минимальные изменения кода

2. **Track 2: Custom Learning Pipelines** (качество)
   - Eval-driven learning (weekly analysis → instruction updates)
   - Correction learning (Chatwoot edits → few-shot examples)
   - Tool analytics (execution patterns → guidance)
   - Few-shot enhancement (inject corrections)

**Итого:**
- Learning Machine (персонализация): 1-2 дня integration
- Custom pipelines (качество): 2-3 недели development
- **Total effort: 3-4 weeks**
- **Expected improvement: 25-35% (combined effect)**

---

## Следующие шаги

### Immediate (Phase 5 complete ✅)
- Analytics service operational
- Knowledge base loaded
- All endpoints tested

### Next (Phase 6 start)
- Setup CopilotKit React app
- Implement AG-UI streaming endpoint
- Create first HITL form (PauseSubscriptionForm)

### Parallel track (Learning foundation)
- Add Agno Learning Machine для customer personalization
- Build correction_patterns table
- Implement Chatwoot webhook для correction capture
- Start collecting data для eval-driven learning
