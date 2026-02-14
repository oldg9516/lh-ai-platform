# AI Agent Best Practices 2026 для Customer Support

## Введение

Этот документ анализирует **текущую архитектуру AI агентов** Lev Haolam и сравнивает её с **индустриальными best practices 2026** для customer support систем.

**Источники исследования:**
- [AI in Customer Service: The Complete Guide for 2026](https://www.chatbase.co/blog/ai-in-customer-service)
- [Best AI Agents for Customer Service in 2026](https://www.haptik.ai/blog/best-ai-agents-for-customer-service)
- [Inside the AI-First Support Team - Intercom](https://www.intercom.com/blog/inside-the-ai-first-support-team/)
- [AI Support Agent Implementation Guide - Jeeva.ai](https://www.jeeva.ai/blog/ai-customer-support-agent-implementation-plan)
- [Future of Customer Experience: AI Agents Working Together](https://www.fastcompany.com/91474127/the-future-of-customer-experience-is-ai-agents-working-together)
- Agno AgentOS документация
- Production опыт из n8n pipeline Lev Haolam

---

## Текущая архитектура (что есть сейчас)

### Обзор пайплайна

```
Incoming Message
       ↓
1. Pre-safety check (regex red lines)
       ↓
2. Router Agent (classify_message → category)
       ↓
3. Load conversation history (manual, last 10 messages)
       ↓
4. Support Agent Factory (create_support_agent по category)
       ↓
5. Outstanding Detection (параллельно с агентом)
       ↓
6. Cancel link injection (retention только)
       ↓
7. Response Assembly (HTML email-style)
       ↓
8. Eval Gate (tier 1 regex + tier 2 LLM)
       ↓
9. Save to DB (session, message, eval, trace)
       ↓
10. Return response (send / draft / escalate)
```

### Агенты

**Router Agent:**
- Model: GPT-5.1
- Reasoning: none
- Output: structured (RouterOutput Pydantic)
- Задача: классификация на 10 категорий + urgency + email extraction

**Support Agent Factory:**
- НЕ 10 отдельных агентов — **1 функция** `create_support_agent(category)`
- Динамическая конфигурация из `CATEGORY_CONFIG`:
  - Model: GPT-5.1 для всех категорий
  - Reasoning: `medium` для retention, `none` для остальных
  - Tools: resolves из `TOOL_REGISTRY` (12 tools)
  - Instructions: загружаются из БД + GLOBAL_SAFETY_RULES
  - Knowledge: Pinecone namespace по категории

**Outstanding Detection Agent:**
- Model: GPT-5-mini
- Reasoning: none
- Input: DB rules + Pinecone outstanding-cases namespace
- Output: is_outstanding, trigger, confidence

**Eval Gate Agent:**
- Tier 1: regex fast-fail (subscription safety)
- Tier 2: LLM GPT-5.1 (accuracy, tone, safety, completeness → send/draft/escalate)

### Multi-turn Conversation

**Реализация:** manual (НЕ Agno native sessions из-за багов SDK 2.x).

- Session ID: `cw_{conversation_id}` (Chatwoot) или `sess_{uuid}` (API)
- History loading: `get_conversation_history(session_id, limit=10)`
- Injection: prepend в `agent_input` как текст с маркерами `[Conversation History]` / `[End History]`
- Format: `Customer: <message>` или `Agent: <response>`
- Truncation: ответы агента → 500 символов в истории

### Tools (12 инструментов)

**Read-only (real DB data):**
- `get_subscription(email)` — активная подписка
- `get_customer_history(email)` — заказы, tracking, support
- `get_payment_history(email)` — платежи
- `track_package(email)` — tracking статус
- `get_box_contents(email)` — состав последней коробки

**Write operations (stubs, возвращают `pending_confirmation`):**
- `change_frequency`, `skip_month`, `pause_subscription`, `change_address`, `create_damage_claim`, `request_photos`

**Retention-specific:**
- `generate_cancel_link(email)` — AES-256-GCM encrypted self-service

### Что работает хорошо ✅

1. **Safety-first подход:** pre-check + eval gate + GLOBAL_SAFETY_RULES → низкий риск ошибок
2. **Structured output:** RouterOutput через Pydantic → 100% парсинг
3. **Real customer data:** нормализованные таблицы (customers, subscriptions, orders) → точные ответы
4. **Observability:** Langfuse + traces + eval datasets (3000 golden samples)
5. **Multi-channel:** Chatwoot (widget, email, WhatsApp ready)
6. **Reasoning для сложных кейсов:** retention categories используют `reasoning_effort=medium`

---

## Best Practices 2026 — что рекомендует индустрия

### 1. Архитектурные паттерны

#### **Perceive → Reason → Act Loop**

Современные AI customer service агенты работают в цикле ([источник](https://www.chatbase.co/blog/ai-in-customer-service)):

```
PERCEIVE: Analyze customer message + context
    ↓
REASON: Decide on action (answer / tool call / escalate)
    ↓
ACT: Execute action (API call / human handoff)
    ↓
MONITOR: Log + learn from outcome
```

**Сравнение с нашей архитектурой:**
- ✅ PERCEIVE: Router + conversation history ✅
- ✅ REASON: Support Agent + reasoning_effort ✅
- ⚠️ ACT: частично (tools stubs, нет реальных API)
- ❌ MONITOR: только logging, **нет continuous learning**

---

#### **Orchestration Layer**

Best practice: **отдельный orchestrator** координирует:
- Conversation state tracking
- LLM координация
- Knowledge base retrieval
- API calls
- Human escalation handoff

**Сравнение:**
- ⚠️ У нас: все в `api/routes.py` — **монолитная функция `chat()`**
- ✅ Плюс: простота, всё в одном месте
- ❌ Минус: тяжело тестировать, масштабировать, добавлять новые каналы

**Рекомендация:** выделить `Orchestrator` класс в `agents/orchestrator.py`.

---

#### **Multi-Agent Teams** (будущее support систем)

[Fast Company](https://www.fastcompany.com/91474127/the-future-of-customer-experience-is-ai-agents-working-together):
> "The future of customer experience is AI agents working together."

**Паттерн:**
- **Intake Agent** → первичная обработка, сбор контекста
- **Specialist Agents** → узкая экспертиза (billing, shipping, retention, quality)
- **QA Agent** → проверка ответов перед отправкой
- **Escalation Agent** → handoff к человеку с полным контекстом

**Сравнение:**
- ⚠️ У нас: Router + single Support Agent
- ✅ Плюс: работает для 80% кейсов
- ❌ Минус: нет специализации (один агент делает ВСЁ)

**Agno поддерживает Teams!** ([docs.agno.com](https://docs.agno.com/agent-os/introduction))

**Рекомендация:** Phase 7 — внедрить multi-agent pattern:
```python
from agno.teams import Team

team = Team(
    agents=[intake_agent, billing_agent, shipping_agent, qa_agent],
    orchestrator=coordinator_agent
)
```

---

### 2. Conversation Management

#### **Контекст > История**

Best practice ([Intercom](https://www.intercom.com/blog/inside-the-ai-first-support-team/)):
- **НЕ просто последние N сообщений**
- **Контекст:** customer profile + subscription status + recent orders + sentiment + intent
- **Динамическое окно:** больше контекста для сложных кейсов, меньше для простых

**Сравнение:**
- ⚠️ У нас: manual history (last 10 messages, 500 chars truncation)
- ✅ Плюс: работает, не ломается (в отличие от Agno native sessions)
- ❌ Минус: **теряется важная информация** при truncation
- ❌ Минус: нет **customer context injection** (мы НЕ добавляем subscription status в начало разговора)

**Рекомендация:**
```python
# agents/context_builder.py
def build_agent_context(email: str, session_id: str) -> str:
    """Build rich context for agent, not just message history."""

    context = []

    # 1. Customer profile
    customer = lookup_customer(email)
    if customer:
        context.append(f"Customer: {customer.name}, member since {customer.join_date}")

    # 2. Active subscription
    sub = get_active_subscription_by_email(email)
    if sub:
        context.append(f"Subscription: {sub.frequency}, next charge {sub.next_charge_date}")

    # 3. Recent orders (last 3)
    orders = get_orders_by_subscription(sub.id, limit=3)
    context.append(f"Recent orders: {len(orders)} in last 6 months")

    # 4. Conversation history (smart truncation)
    history = get_conversation_history(session_id, limit=10)
    context.append(format_history_with_intent(history))  # summarize old turns

    # 5. Outstanding issues
    outstanding = detect_outstanding_cached(email)
    if outstanding.is_outstanding:
        context.append(f"⚠️ Outstanding: {outstanding.trigger}")

    return "\n\n".join(context)
```

---

#### **Session Continuity**

Best practice: **stable session IDs** на всех каналах.

**Сравнение:**
- ✅ У нас: `cw_{conversation_id}` для Chatwoot ✅
- ❌ Но: API endpoint создает новый `sess_{uuid}` каждый раз
- ❌ Нет кросс-канальной continuity (email → widget → WhatsApp = 3 разных сессии)

**Рекомендация:** использовать **customer email как stable key** для session_id:
```python
session_id = f"email_{hashlib.sha256(email.encode()).hexdigest()[:12]}"
```

---

### 3. Knowledge Base (RAG)

#### **Retrieval-Augmented Generation**

Best practice ([Jeeva.ai](https://www.jeeva.ai/blog/ai-customer-support-agent-implementation-plan)):
> "When a customer asks a question, the AI searches your knowledge base, retrieves relevant information, and generates a response based on that specific context."

**Что важно:**
1. **Hybrid search** (dense + sparse embeddings)
2. **Reranking** после retrieval
3. **Metadata filtering** (product, category, language)
4. **Freshness priority** (newer docs > старые)

**Сравнение:**
- ✅ У нас: Pinecone с `use_hybrid_search=True`
- ✅ Namespaces по категориям
- ❌ Но: **НЕТ reranking**
- ❌ НЕТ metadata filtering (все категории видят всё в своем namespace)
- ❌ НЕТ приоритета по свежести

**Рекомендация:** использовать **Pinecone Inference** с reranking ([Pinecone Rerank](https://docs.pinecone.io/guides/inference/rerank)):

```python
from pinecone import Pinecone

pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index("support-examples")

# Поиск
results = index.query(
    namespace="retention",
    vector=embed(query),
    top_k=20,  # больше результатов
    include_metadata=True
)

# Reranking
reranked = pc.inference.rerank(
    model="bge-reranker-v2-m3",
    query=query,
    documents=[r.metadata['text'] for r in results],
    top_n=5,  # финальный топ
    return_documents=True
)
```

---

### 4. Escalation Strategy

#### **Smart Routing**

Best practice ([Chatbase](https://www.chatbase.co/blog/ai-in-customer-service)):
> "Smart routing ensures that complex or sensitive conversations are escalated to the right human agent, armed with full context and conversation history, for a seamless handover."

**Сигналы для эскалации:**
1. **Низкая confidence:** Eval Gate → draft
2. **Красные линии:** death threats, bank disputes → escalate
3. **Sentiment:** customer frustration (multiple negative messages)
4. **Complexity:** customer asks for "manager" or "human"
5. **Outstanding issues:** если клиент уже эскалирован ранее

**Сравнение:**
- ✅ У нас: red lines (regex) + eval gate (LLM) → escalate ✅
- ⚠️ Но: **нет sentiment tracking**
- ⚠️ Нет детекции "хочу поговорить с человеком"
- ✅ Outstanding detection работает

**Рекомендация:** добавить **sentiment analysis** в Router Agent:

```python
# agents/router.py
class RouterOutput(BaseModel):
    primary_category: str
    urgency: str
    extracted_email: str | None
    sentiment: str  # NEW: "positive" | "neutral" | "negative" | "frustrated"
    escalation_reason: str | None  # NEW: "low_confidence" | "request_human" | "sentiment"

# В classify_message:
instructions = [
    "...",
    "Analyze customer sentiment: positive (grateful), neutral (question), negative (complaint), frustrated (repeated issue, anger)",
    "If customer explicitly asks for human ('speak to manager', 'real person'), set escalation_reason='request_human'"
]
```

---

#### **Context Handoff**

Best practice: при эскалации агенту **передается полный контекст**.

**Что нужно передать:**
1. Conversation history (full, не truncated)
2. Customer profile + subscription
3. AI agent actions (какие tools вызывались)
4. Eval results (почему draft/escalate)
5. Urgency + sentiment

**Сравнение:**
- ✅ У нас: Chatwoot private note с ответом агента
- ❌ Но: **нет полного контекста** (human видит только последнее сообщение в note)

**Рекомендация:** при escalate создавать **structured handoff note**:

```python
# chatwoot/client.py
async def escalate_to_human(
    conversation_id: int,
    agent_response: str,
    session: ChatSession,
    eval_result: EvalResult,
    category: str
):
    """Escalate with full context."""

    # Формируем handoff note
    context = {
        "customer_email": session.customer_email,
        "category": category,
        "urgency": session.urgency,
        "sentiment": session.sentiment,  # NEW
        "conversation_history": get_conversation_history(session.id, limit=50),
        "ai_attempted_response": agent_response,
        "eval_decision": eval_result.decision,
        "eval_reasons": eval_result.reasons,
        "tools_used": session.tools_executed,  # NEW: какие tools вызывал AI
        "outstanding_trigger": session.outstanding_trigger,
    }

    # Private note в Chatwoot
    await chatwoot.create_message(
        conversation_id=conversation_id,
        content=format_handoff_note(context),
        message_type="outgoing",
        private=True
    )

    # Assign to human agent
    await chatwoot.assign_conversation(
        conversation_id=conversation_id,
        assignee_id=CHATWOOT_ESCALATION_ASSIGNEE_ID,
        team_id=CHATWOOT_SUPPORT_TEAM_ID
    )

    # Labels
    await chatwoot.add_labels(conversation_id, ["escalated", "ai_handoff", category])
```

---

### 5. Continuous Learning

#### **AI Ops Team**

Best practice ([Intercom](https://www.intercom.com/blog/inside-the-ai-first-support-team/)):

**Роли в AI-first support команде:**
1. **AI Ops Lead** — identifies patterns, performance gaps
2. **Knowledge Manager** — resolves inaccuracies, fills content gaps
3. **Conversation Designer** — improves clarity, tone, flow
4. **Automation Specialist** — expands system's ability to take action

**Сравнение:**
- ❌ У нас: **НЕТ formal AI ops процесса**
- ✅ Есть: Langfuse eval datasets → можно анализировать паттерны
- ❌ Нет: **feedback loop** (human corrections → update prompts)
- ❌ Нет: **learning machine** (Agno SDK feature, не используем)

**Рекомендация:** Phase 8 — **AI Ops Dashboard**:

```python
# services/analytics/ai_ops.py
class AIOpsAnalytics:
    """Analytics for AI performance monitoring."""

    def get_failure_patterns(self, days=7) -> list[Pattern]:
        """Find common escalation/draft patterns."""
        # Query eval_results WHERE decision IN ('draft', 'escalate')
        # Group by category, eval_reasons
        # Return top 10 patterns

    def get_knowledge_gaps(self) -> list[Gap]:
        """Find questions AI couldn't answer."""
        # Query chat_messages WHERE eval_result.accuracy < 0.6
        # Extract topics → которых нет в Pinecone

    def get_tone_drift(self) -> Report:
        """Detect if AI tone changed over time."""
        # Query eval_results.tone по неделям
        # Alert if trend вниз

    def suggest_prompt_updates(self) -> list[Suggestion]:
        """ML-based suggestions for instruction updates."""
        # Analyze high-performing vs low-performing responses
        # Diff их prompts → suggest improvements
```

---

#### **Agno Learning Machine**

Agno SDK поддерживает **Learning Machine** ([github.com/agno-agi/agno](https://github.com/agno-agi/agno)):
> "Build multi-agent systems that learn and improve with every interaction."

**Как работает:**
1. Agent делает ошибку (например, неправильный SQL query)
2. Human исправляет
3. Learning Machine сохраняет correction
4. Следующий раз agent **НЕ повторит** ошибку

**Сравнение:**
- ❌ У нас: НЕ используем Learning Machine
- ✅ Есть: `learning_records` таблица в БД (создана, но пустая)

**Рекомендация:** Phase 8 — включить Learning Machine для tools:

```python
# agents/support.py
from agno.learning import LearningMachine

learning = LearningMachine(
    db=get_postgres_db(),  # сохраняет в learning_records
    scope="support_tools"
)

agent = Agent(
    name="support_shipping",
    model=OpenAIChat(id="gpt-5.1"),
    tools=[get_subscription, track_package],
    learning=learning,  # ENABLE
    learn_from_errors=True
)
```

---

### 6. Модели и Reasoning

#### **Model Selection Strategy**

Best practice:
- **Cheap models** для routing, classification, simple Q&A (GPT-5-mini, Haiku)
- **Smart models** для reasoning, complex support (GPT-5.1, Sonnet)
- **Reasoning effort** только где нужно (retention, disputes)

**Сравнение:**
- ✅ У нас: Router использует GPT-5.1 (можно downgrade до 5-mini)
- ✅ Support Agent: GPT-5.1 с `reasoning_effort=medium` для retention
- ✅ Outstanding: GPT-5-mini
- ❌ Eval Gate: GPT-5.1 (можно попробовать Sonnet 4.5 — лучше reasoning)

**Рекомендация — cost optimization:**

| Агент | Текущая модель | Рекомендация | Savings |
|-------|----------------|--------------|---------|
| Router | GPT-5.1 | GPT-5-mini | 90% ⬇️ |
| Support (simple) | GPT-5.1 | GPT-5.1 ✅ | — |
| Support (retention) | GPT-5.1 + reasoning | Sonnet 4.5 + reasoning | 50% ⬆️ качество |
| Outstanding | GPT-5-mini ✅ | — | — |
| Eval Gate | GPT-5.1 | Claude Sonnet 4.5 | Better judgment |

---

## Конкретные Рекомендации для Lev Haolam

### Priority 1: Улучшения в рамках текущей архитектуры (2-3 недели)

#### 1.1. Context Builder (вместо manual history)

**Файл:** `agents/context_builder.py`

**Что делает:**
- Загружает customer profile + subscription + orders
- Форматирует conversation history с **smart truncation** (старые сообщения summarize)
- Добавляет outstanding context
- Возвращает rich context string для agent

**Интеграция:**
```python
# api/routes.py
async def chat(request: ChatRequest):
    # ...
    category = await classify_message(message)

    # OLD: manual history
    # history = get_conversation_history(session_id, limit=10)
    # agent_input = format_history(history) + message

    # NEW: rich context
    from agents.context_builder import build_agent_context
    context = build_agent_context(
        email=request.email,
        session_id=session_id,
        message=message,
        category=category
    )

    agent = create_support_agent(category, email=request.email)
    response = await agent.arun(context)
```

---

#### 1.2. Sentiment Tracking

**Обновить Router Agent:**

```python
# agents/router.py
class RouterOutput(BaseModel):
    primary_category: str
    secondary_category: str | None
    urgency: str
    extracted_email: str | None
    sentiment: str  # NEW
    escalation_signal: bool  # NEW: True if customer wants human

# Добавить в instructions:
ROUTER_INSTRUCTIONS = """
...
5. Analyze SENTIMENT:
   - positive: grateful, satisfied ("thank you", "great service")
   - neutral: just asking question
   - negative: complaint, disappointed
   - frustrated: angry, repeated issue, CAPS, exclamation marks

6. Detect ESCALATION SIGNALS:
   - Customer asks for human: "speak to manager", "real person", "human agent"
   - Multiple failed interactions (check history)
   - Extreme frustration
   → Set escalation_signal=True
"""
```

---

#### 1.3. Pinecone Reranking

**Обновить knowledge/pinecone_client.py:**

```python
# knowledge/pinecone_client.py
from pinecone import Pinecone

def search_with_reranking(
    namespace: str,
    query: str,
    top_k: int = 20,
    top_n: int = 5
) -> list[Document]:
    """Search Pinecone with reranking."""

    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index("support-examples")

    # 1. Initial search (hybrid)
    results = index.query(
        namespace=namespace,
        vector=embed_query(query),
        top_k=top_k,
        include_metadata=True
    )

    # 2. Rerank
    reranked = pc.inference.rerank(
        model="bge-reranker-v2-m3",
        query=query,
        documents=[r.metadata['text'] for r in results.matches],
        top_n=top_n,
        return_documents=True
    )

    return reranked.data
```

---

#### 1.4. Enhanced Escalation Context

**Обновить chatwoot/client.py:**

```python
# chatwoot/client.py
async def escalate_with_context(
    conversation_id: int,
    session: ChatSession,
    agent_response: str,
    eval_result: EvalResult,
    category: str
):
    """Escalate to human with full context."""

    context_note = f"""
🤖 AI Escalation Handoff

📧 Customer: {session.customer_email}
📂 Category: {category}
⚠️ Urgency: {session.urgency}
😊 Sentiment: {session.sentiment}

📜 Conversation Summary:
{summarize_conversation(session.id)}

🔧 AI Attempted Response:
{agent_response}

🚫 Why escalated:
- Decision: {eval_result.decision}
- Reasons: {", ".join(eval_result.reasons)}

🛠 Tools Used:
{format_tools_executed(session.id)}

⚠️ Outstanding Issues:
{session.outstanding_trigger or "None"}

💡 Suggested Next Steps:
{suggest_human_actions(category, session)}
"""

    await chatwoot.create_message(
        conversation_id=conversation_id,
        content=context_note,
        private=True
    )

    await chatwoot.assign_conversation(
        conversation_id=conversation_id,
        assignee_id=get_best_assignee(category),  # route by specialty
        team_id=CHATWOOT_SUPPORT_TEAM_ID
    )

    await chatwoot.add_labels(
        conversation_id,
        ["escalated", "ai_handoff", category, f"sentiment_{session.sentiment}"]
    )
```

---

### Priority 2: Архитектурный рефакторинг (4-6 недель)

#### 2.1. Orchestrator Pattern

**Новый файл:** `agents/orchestrator.py`

```python
# agents/orchestrator.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class OrchestratorResult:
    response: str
    decision: Literal["send", "draft", "escalate"]
    category: str
    session_id: str
    metadata: dict

class SupportOrchestrator:
    """Orchestrates the full support pipeline."""

    def __init__(self):
        self.router = RouterAgent()
        self.context_builder = ContextBuilder()
        self.support_factory = SupportAgentFactory()
        self.outstanding_detector = OutstandingDetector()
        self.eval_gate = EvalGate()
        self.response_assembler = ResponseAssembler()

    async def process(
        self,
        message: str,
        email: str,
        session_id: str,
        channel: str
    ) -> OrchestratorResult:
        """Process customer message through full pipeline."""

        # 1. Pre-safety
        if red_line := check_red_lines(message):
            return self._escalate_immediately(red_line)

        # 2. Routing
        routing = await self.router.classify(message)

        # 3. Context building
        context = self.context_builder.build(
            email=email,
            session_id=session_id,
            message=message,
            category=routing.primary_category
        )

        # 4. Parallel execution
        agent_task = self.support_factory.create(routing.primary_category).arun(context)
        outstanding_task = self.outstanding_detector.check(email, message)

        agent_response, outstanding = await asyncio.gather(agent_task, outstanding_task)

        # 5. Response assembly
        assembled = self.response_assembler.assemble(
            body=agent_response,
            email=email,
            category=routing.primary_category,
            channel=channel
        )

        # 6. Eval gate
        eval_result = await self.eval_gate.evaluate(
            message=message,
            response=assembled,
            category=routing.primary_category,
            tools_available=get_category_tools(routing.primary_category)
        )

        # 7. Persistence
        await self._save_session(session_id, routing, outstanding, eval_result)

        # 8. Return
        return OrchestratorResult(
            response=assembled,
            decision=eval_result.decision,
            category=routing.primary_category,
            session_id=session_id,
            metadata={
                "urgency": routing.urgency,
                "sentiment": routing.sentiment,
                "outstanding": outstanding.is_outstanding,
                "eval_confidence": eval_result.confidence
            }
        )
```

**Использование:**

```python
# api/routes.py
@router.post("/api/chat")
async def chat(request: ChatRequest):
    orchestrator = SupportOrchestrator()

    result = await orchestrator.process(
        message=request.message,
        email=request.email,
        session_id=request.session_id or generate_session_id(),
        channel="api"
    )

    return ChatResponse(
        response=result.response,
        category=result.category,
        decision=result.decision,
        **result.metadata
    )
```

---

#### 2.2. Multi-Agent Teams (Phase 7)

**Новая архитектура:**

```
                  ┌──────────────┐
                  │   Intake     │
                  │    Agent     │
                  └──────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼─────┐   ┌────▼─────┐   ┌────▼─────┐
    │ Billing  │   │ Shipping │   │ Retention│
    │ Specialist│   │Specialist│   │Specialist│
    └────┬─────┘   └────┬─────┘   └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                  ┌──────▼───────┐
                  │  QA Agent    │
                  │  (Eval)      │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │  Response    │
                  │  Assembler   │
                  └──────────────┘
```

**Реализация:**

```python
# agents/teams.py
from agno.teams import Team

class SupportTeam:
    def __init__(self):
        # Intake agent — initial triage
        self.intake_agent = Agent(
            name="intake",
            model=OpenAIChat(id="gpt-5-mini"),
            instructions=[
                "You are the intake agent.",
                "Analyze customer message and decide which specialist to route to.",
                "Extract: category, urgency, sentiment, customer context."
            ],
            output_schema=IntakeDecision
        )

        # Specialist agents
        self.billing_agent = self._create_specialist("billing", BILLING_TOOLS)
        self.shipping_agent = self._create_specialist("shipping", SHIPPING_TOOLS)
        self.retention_agent = self._create_specialist(
            "retention",
            RETENTION_TOOLS,
            model=OpenAIChat(id="gpt-5.1", reasoning_effort="medium")
        )

        # QA agent
        self.qa_agent = Agent(
            name="qa",
            model=Claude(id="claude-sonnet-4-5"),
            instructions=[
                "You are the QA agent.",
                "Review the specialist's response for:",
                "1. Accuracy (based on tools output)",
                "2. Tone (empathetic, professional)",
                "3. Safety (no subscription confirmations)",
                "4. Completeness (all customer questions answered)",
                "Return: approve / reject + reasons"
            ],
            output_schema=QADecision
        )

        # Team
        self.team = Team(
            agents=[
                self.intake_agent,
                self.billing_agent,
                self.shipping_agent,
                self.retention_agent,
                self.qa_agent
            ]
        )

    async def handle_message(self, message: str, context: dict) -> TeamResult:
        """Process message through team."""

        # 1. Intake decision
        intake = await self.intake_agent.arun(message, context)

        # 2. Route to specialist
        specialist = self._get_specialist(intake.category)
        response = await specialist.arun(message, context)

        # 3. QA review
        qa = await self.qa_agent.arun({
            "message": message,
            "response": response,
            "category": intake.category
        })

        # 4. Retry if rejected
        if qa.decision == "reject":
            response = await specialist.arun(
                message,
                context,
                feedback=qa.reasons  # incorporate QA feedback
            )
            qa = await self.qa_agent.arun(...)  # re-check

        return TeamResult(
            response=response,
            category=intake.category,
            qa_approved=qa.decision == "approve"
        )
```

---

### Priority 3: AI Ops & Learning (ongoing)

#### 3.1. AI Ops Dashboard

**Метрики для мониторинга:**

| Метрика | Формула | Target | Alert |
|---------|---------|--------|-------|
| **AI Resolution Rate** | `send / (send + draft + escalate)` | >70% | <60% |
| **Eval Gate Pass Rate** | `send / total` | >80% | <70% |
| **Escalation Rate** | `escalate / total` | <10% | >15% |
| **Average Confidence** | `AVG(eval_result.confidence)` | >0.8 | <0.7 |
| **Category Accuracy** | Per category eval scores | >0.75 | <0.65 |
| **Outstanding Detection** | `outstanding / total` | Track | — |
| **Response Time (p95)** | Latency | <10s | >15s |

**Dashboard в Langfuse или Agno Control Plane.**

---

#### 3.2. Feedback Loop

```python
# services/ai-engine/learning/feedback.py
class FeedbackLoop:
    """Human corrections → prompt updates."""

    async def collect_human_edit(
        self,
        message_id: str,
        ai_response: str,
        human_response: str,
        category: str
    ):
        """When human edits AI response, learn from it."""

        # 1. Save to learning_records
        await save_learning_record({
            "message_id": message_id,
            "category": category,
            "ai_response": ai_response,
            "human_response": human_response,
            "edit_type": classify_edit(ai_response, human_response),  # tone, accuracy, safety
            "timestamp": datetime.now()
        })

        # 2. Analyze pattern
        if await self._is_recurring_pattern(category, edit_type):
            # 3. Suggest prompt update
            suggestion = await self._generate_prompt_update(category, edit_type)

            # 4. Notify AI Ops team
            await notify_slack(
                channel="#ai-ops",
                message=f"🔔 Recurring edit pattern in {category}: {edit_type}\n\n"
                        f"Suggested prompt update:\n```\n{suggestion}\n```"
            )
```

---

## Итоговый План Внедрения

### Phase 6: Generative UI + HITL (текущий приоритет)
- **Сроки:** 4-6 недель
- **Технологии:** CopilotKit + AG-UI Protocol
- **Deliverable:** HITL формы для всех write-операций
- **Документация:** [08-COPILOTKIT-GENERATIVE-UI.md](08-COPILOTKIT-GENERATIVE-UI.md)

### Phase 7: Architecture Refactoring
- **Сроки:** 4-6 недель
- **Изменения:**
  1. Context Builder (вместо manual history)
  2. Orchestrator Pattern (вместо монолита в routes.py)
  3. Sentiment Tracking (в Router)
  4. Pinecone Reranking
  5. Enhanced Escalation Context
- **Цель:** улучшить accuracy на 10-15%, снизить escalation rate на 20%

### Phase 8: Multi-Agent Teams
- **Сроки:** 6-8 недель
- **Изменения:**
  1. Intake Agent + Specialist Agents (billing, shipping, retention)
  2. QA Agent (replace Eval Gate)
  3. Agno Teams интеграция
- **Цель:** резолюция сложных multi-domain кейсов (сейчас → escalate)

### Phase 9: AI Ops & Learning
- **Сроки:** ongoing
- **Изменения:**
  1. AI Ops Dashboard (Langfuse)
  2. Feedback Loop (human edits → prompt updates)
  3. Agno Learning Machine
  4. Continuous model evaluation (A/B testing)
- **Цель:** self-improving system, снижение manual tuning на 80%

---

## Источники

- [AI in Customer Service: The Complete Guide for 2026](https://www.chatbase.co/blog/ai-in-customer-service)
- [Best AI Agents for Customer Service in 2026](https://www.haptik.ai/blog/best-ai-agents-for-customer-service)
- [Inside the AI-First Support Team](https://www.intercom.com/blog/inside-the-ai-first-support-team/)
- [AI Support Agent Implementation Guide](https://www.jeeva.ai/blog/ai-customer-support-agent-implementation-plan)
- [Future of Customer Experience: AI Agents Working Together](https://www.fastcompany.com/91474127/the-future-of-customer-experience-is-ai-agents-working-together)
- [CopilotKit Documentation](https://www.copilotkit.ai/)
- [Agno AgentOS Documentation](https://docs.agno.com/)
- [Pinecone Inference & Reranking](https://docs.pinecone.io/guides/inference/rerank)

---

## Выводы

**Текущая архитектура (Phases 0-4):**
- ✅ **Работает хорошо** для 70-80% кейсов
- ✅ **Safety-first** подход корректен
- ✅ **Real data** из БД → точные ответы
- ⚠️ **Но:** есть возможности для улучшения

**Топ-3 рекомендации для следующих Phases:**
1. **Phase 6:** CopilotKit для HITL — **immediate value**, безопасность write-операций
2. **Phase 7:** Context Builder + Orchestrator — **architecture cleanup**, проще тестировать и масштабировать
3. **Phase 8:** Multi-Agent Teams — **future-proof**, резолюция сложных кейсов

**Долгосрочная цель:** self-improving AI support system с **90%+ resolution rate** и continuous learning.
