# Demo Script: AI-Powered Support Platform for Lev Haolam

**Total Duration:** 40 minutes + 10 min Q&A
**Audience:** Management / Executive Team
**Goal:** Demonstrate AI quality, automation with safety, and observability for production readiness

---

## Pre-Demo Setup Checklist

**15 minutes before demo:**
- [ ] Start all Docker containers: `docker compose up -d`
- [ ] Verify all services healthy:
  - [ ] AI Engine: http://localhost:8000/api/health
  - [ ] Analytics: http://localhost:9000/api/health
  - [ ] Langfuse: http://localhost:3100 (login ready)
  - [ ] Frontend: http://localhost:3000 (CopilotKit sidebar visible)
- [ ] Pre-load browser tabs:
  - Tab 1: Frontend (http://localhost:3000)
  - Tab 2: Langfuse (http://localhost:3100)
  - Tab 3: Analytics Dashboard (http://localhost:9000/docs)
  - Tab 4: Chatwoot (http://localhost:3010) — optional
- [ ] Clear Langfuse traces from previous tests (for clean demo)
- [ ] Test customer email: `sarah.cohen@example.com` (exists in database)
- [ ] Have fallback materials ready (screenshots, video link)

---

## Сцена 1: Problem Statement (3 минуты)

### Slide 1: Current State

**Говорить:**
> "Сейчас у нас email-only pipeline через n8n. Средний response time — 30-60 минут, потому что каждый AI draft требует human review. Это создаёт bottleneck и не масштабируется."

**Показать:**
- Diagram: Email → n8n → AI Draft → Human Review → Send (30-60 min)

### Slide 2: New System

**Говорить:**
> "Новая система — multi-channel AI Engine с автоматическими safety checks. Response time сокращается до <10 секунд, 70-80% автоматически отправляются без review."

**Показать:**
- Architecture diagram: Chatwoot → AI Engine → Auto-send (80%) / Draft (15%) / Escalate (5%)

**Ключевые метрики:**
- Response time: **30-60 min → <10 sec**
- Auto-send rate: **0% → 70-80%**
- Channels: **Email only → Web widget + Email + WhatsApp**

**Переход:** "Давайте посмотрим на качество AI в действии."

---

## Сцена 2: AI Quality (8 минут)

### Demo 1: Tracking Question with Real Data (3 мин)

**Setup:**
- Open frontend (http://localhost:3000)
- Open CopilotKit sidebar

**Message:**
```
Hi, I haven't received my box yet. My email is sarah.cohen@example.com.
Where is my package?
```

**Expected AI Response:**
```
Hi Sarah,

I checked your order and found your tracking information:

📦 Tracking Number: TRACK-2024-001
🚚 Carrier: Israel Post
📍 Status: In Transit
📅 Expected Delivery: 2024-04-18

Your package is currently in transit and should arrive by April 18th.
You can track it directly on the Israel Post website using the tracking number above.

Is there anything else I can help you with?

Best regards,
Lev Haolam Support
```

**Говорить (пока AI печатает):**
> "Обратите внимание — AI автоматически:
> 1. **Идентифицировал клиента** по email (sarah.cohen@example.com)
> 2. **Извлёк данные** из database используя tool `track_package()`
> 3. **Форматировал ответ** с эмодзи и структурой
> 4. Всё это за **<3 секунды**"

**После ответа — показать Langfuse:**
- Switch to Langfuse tab
- Find latest trace (should be top of list)
- Open trace → показать:
  - Router classification: `shipping_or_delivery_question`
  - Support Agent: Model GPT-5.1
  - Tool call: `track_package(email="sarah.cohen@example.com")`
  - Tool result: Real tracking data from database
  - Eval Gate: **Decision: SEND** (high confidence)

**Говорить:**
> "Eval Gate проверил ответ на accuracy, tone, safety — и автоматически одобрил для отправки. Никакого human review не нужно."

---

### Demo 2: Retention with Downsell (3 мин)

**Message:**
```
I want to cancel my subscription. It's getting too expensive for me.
```

**Expected AI Response:**
```
Hi Sarah,

I understand budget concerns are important. Before canceling, I'd like to offer you some options:

💡 SAVE MONEY OPTIONS:
1. **Pause Subscription** (1-3 months) - Take a break and resume later
2. **Change Frequency** - Switch from monthly to bi-monthly (50% savings)
3. **Skip Next Month** - One-time skip without canceling

Your current subscription:
- Frequency: Monthly
- Next charge: April 15, 2024
- Amount: $60.00

Would any of these options work better for you? I'm here to help find the right solution.

If you still prefer to cancel, I can provide you with a self-service link.

Best regards,
Lev Haolam Support
```

**Говорить (пока AI печатает):**
> "Это retention scenario. AI:
> 1. **Не подтверждает cancellation** напрямую (safety rule)
> 2. **Предлагает downsell options** (pause, frequency change, skip)
> 3. **Показывает customer context** (current subscription details)
> 4. **Medium reasoning effort** для сложных retention кейсов"

**После ответа — показать Langfuse:**
- Open trace
- Router: `retention_primary_request`
- Support Agent: **reasoning_effort: "medium"** (deeper analysis)
- Tools: `get_subscription(email)` → показывает active subscription
- Eval Gate: **Decision: SEND** (правильный retention ответ)

**Говорить:**
> "Reasoning effort 'medium' означает что модель тратит больше времени на анализ. Для retention это критично — мы не можем потерять клиента из-за плохого ответа."

---

### Demo 3: Safety Guardrail — Escalation (2 мин)

**Message:**
```
THIS IS THE THIRD TIME MY BOX WAS DAMAGED!!!
I'M GOING TO CONTACT MY LAWYER IF YOU DON'T FIX THIS NOW!!!
```

**Expected AI Response:**
```
I sincerely apologize for the repeated damage to your boxes. This is unacceptable,
and I understand your frustration.

Your case requires immediate attention from our senior support team.
I'm escalating this to a human agent who will contact you within 1 hour to resolve this.

Reference: [Session ID will be shown]

We take this very seriously and will make it right.

Best regards,
Lev Haolam Support
```

**Говорить (пока AI печатает):**
> "AI детектирует:
> 1. **Frustrated sentiment** (CAPS, множественные !!!)
> 2. **Legal threat** ('contact my lawyer')
> 3. **Escalation signal** (требует human agent)"

**После ответа — показать Langfuse:**
- Router:
  - `sentiment: "frustrated"`
  - `escalation_signal: true`
  - `urgency: "critical"`
- Eval Gate: **Decision: ESCALATE** (safety override)

**Говорить:**
> "Eval Gate автоматически escalate кейсы с:
> - Legal threats
> - Death threats
> - Bank disputes
> - Extreme frustration
>
> Это safety guardrail — AI никогда не рискует в sensitive situations."

**Переход:** "Теперь давайте посмотрим на автоматизацию с human oversight."

---

## Сцена 3: Автоматизация с HITL (12 минут)

### Demo 4: Pause Subscription with CopilotKit Form (6 мин)

**Message:**
```
Can you pause my subscription for 2 months?
I'm going on vacation. My email is sarah.cohen@example.com.
```

**Expected Flow:**

1. **AI Response (текст):**
```
I can help you pause your subscription for 2 months while you're on vacation.

Let me prepare the pause request for you to confirm.
```

2. **CopilotKit Form Appears:**
- Form title: "Pause Subscription Confirmation"
- Customer: sarah.cohen@example.com
- Duration: 2 months
- Paused until: [calculated date]
- Buttons: [Confirm Pause] [Cancel]

**Говорить (когда форма появится):**
> "Это CopilotKit HITL (Human-in-the-Loop) форма. AI подготовил действие, но **требует подтверждения** перед execution.
>
> Форма показывает:
> - Customer context (email, current subscription)
> - Action details (pause duration, resume date)
> - Safety info (можно cancel в любой момент)"

**Action: Click [Confirm Pause]**

3. **AI Final Response:**
```
✅ Your subscription has been paused for 2 months.

Details:
- Paused until: June 15, 2024
- Next charge after resuming: $60.00 on June 15
- Confirmation email sent to sarah.cohen@example.com

You can resume anytime by contacting us. Enjoy your vacation!

Best regards,
Lev Haolam Support
```

**Говорить (после подтверждения):**
> "После confirmation:
> 1. **Mock Zoho API** вызывается (в production это будет real Zoho)
> 2. **Customer notification** отправляется (email)
> 3. **Tool execution logged** в database для analytics
>
> Если бы мы нажали Cancel — AI получил бы отказ и предложил альтернативы."

**После ответа — показать Langfuse:**
- Tool call: `pause_subscription(email="sarah.cohen@example.com", duration_months=2)`
- Tool result: `{"status": "completed", "paused_until": "2024-06-15", ...}`
- HITL approval: `approval_status: "approved"` (в database)

---

### Demo 5: Address Change with Validation (6 мин)

**Message:**
```
I moved to a new address. Can you update it to:
456 New Street, Jerusalem, Israel, 12345
```

**Expected Flow:**

1. **AI Response:**
```
I can update your delivery address. Let me validate the new address first.
```

2. **Address Validation Form:**
- Current address: [old address from DB]
- New address:
  - Street: 456 New Street
  - City: Jerusalem
  - Country: Israel
  - Postal Code: 12345
- Validation status: ✅ Valid address (Mock Google Maps API)
- Buttons: [Update Address] [Cancel]

**Говорить:**
> "Address change проходит через:
> 1. **Google Maps API validation** (mock в demo)
> 2. **Customer confirmation** (HITL form)
> 3. **Zoho CRM update** (mock в demo)
>
> Это предотвращает typos и invalid addresses которые приводят к lost packages."

**Action: Click [Update Address]**

3. **AI Final Response:**
```
✅ Your delivery address has been updated.

New address:
📍 456 New Street, Jerusalem, Israel, 12345

This will apply to all future orders starting with your next shipment on April 15.

Confirmation email sent to sarah.cohen@example.com.

Best regards,
Lev Haolam Support
```

**После ответа — показать Analytics:**
- Switch to Analytics tab (http://localhost:9000/docs)
- Execute: `GET /metrics/hitl-stats`

**Expected Response:**
```json
{
  "total_hitl_calls": 2,
  "approved": 2,
  "cancelled": 0,
  "pending": 0,
  "approval_rate_pct": 100.0,
  "by_tool": [
    {
      "tool_name": "pause_subscription",
      "total_calls": 1,
      "approved": 1,
      "cancelled": 0,
      "approval_rate_pct": 100.0
    },
    {
      "tool_name": "change_address",
      "total_calls": 1,
      "approved": 1,
      "cancelled": 0,
      "approval_rate_pct": 100.0
    }
  ]
}
```

**Говорить:**
> "HITL stats показывают:
> - 100% approval rate (оба actions подтверждены)
> - Breakdown по tools
> - В production это поможет identify problematic tools или UX issues"

**Переход:** "Теперь multi-turn intelligence."

---

## Сцена 4: Multi-turn Intelligence (8 минут)

### Demo 6: Context-Aware Conversation (8 мин)

**Message 1:**
```
What products are in my next box?
```

**AI Response 1:**
```
Hi Sarah,

Your next box (shipping April 15, 2024) will include:

🍷 Israeli Wine Collection:
- Red wine from Golan Heights
- White wine from Judean Hills

🫒 Olive Oil Premium:
- Cold-pressed extra virgin
- From Galilee region

🍯 Raw Honey:
- Wildflower blend
- From Negev Desert

Would you like to know anything else about your upcoming box?

Best regards,
Lev Haolam Support
```

**Говорить:**
> "AI использовал tool `get_box_contents(email)` для извлечения реальных данных."

---

**Message 2:**
```
Can I swap the wine for something else?
```

**AI Response 2:**
```
I understand you'd like to customize your box by swapping the wine.

Our customization options include:
- Coffee from Jerusalem
- Dates from Jericho
- Halva assortment
- Tea collection

However, customization requests need to be submitted at least 5 days before
your shipment date (April 15). Since we're within that window, I'll need to
escalate this to our fulfillment team.

Would you like me to create a customization request for you?

Best regards,
Lev Haolam Support
```

**Говорить:**
> "Обратите внимание — AI:
> 1. **Помнит контекст** ('swap the wine' — refers to Message 1)
> 2. **Знает shipment date** (April 15 from previous tool call)
> 3. **Применяет business rules** (5-day customization window)
> 4. **Предлагает escalation** (правильный следующий шаг)"

---

**Message 3:**
```
Yes please. I want coffee instead.
```

**AI Response 3:**
```
I've created a customization request for you:

Request Details:
- Remove: Israeli Wine Collection
- Add: Coffee from Jerusalem
- Box date: April 15, 2024
- Status: Pending fulfillment team review

Our team will review this within 24 hours and confirm if we can accommodate
the change. You'll receive an email update.

Reference: [Request ID]

Is there anything else I can help you with?

Best regards,
Lev Haolam Support
```

**Говорить:**
> "AI:
> 1. **Создал request** через tool (в demo это mock, в production → Zoho)
> 2. **Собрал всю информацию** из conversation history (coffee, wine, date)
> 3. **Установил expectations** (24-hour review)
>
> Всё это БЕЗ того чтобы клиент повторял информацию."

---

**После ответа — показать Langfuse:**
- Find conversation with 3 messages
- Open full trace
- Show conversation history injection:
  - Message 1: "What products..." → tool call `get_box_contents()`
  - Message 2: "Can I swap..." → references "wine" from Message 1
  - Message 3: "Yes please. I want coffee" → creates request with all context

**Говорить:**
> "Conversation history:
> - Stored в PostgreSQL (chat_sessions, chat_messages tables)
> - Injected в agent context (last 10 messages)
> - Agent responses truncated to 500 chars для efficiency
>
> Это позволяет multi-turn conversations без context loss."

**Переход:** "Теперь observability и learning."

---

## Сцена 5: Observability & Learning (8 минут)

### Langfuse Walkthrough (4 мин)

**Switch to Langfuse tab** (http://localhost:3100)

**Show:**

1. **Traces List:**
   - Filter by last 1 hour
   - Show all demo traces (6-7 conversations)
   - Sort by tokens (most expensive first)

**Говорить:**
> "Langfuse — это observability platform для LLM applications. Каждый AI interaction логируется с полным трacing."

2. **Open Expensive Trace** (retention with reasoning_effort="medium"):
   - Total cost: ~$0.15-0.20 (GPT-5.1 with reasoning)
   - Input tokens: ~2,500
   - Output tokens: ~800
   - Reasoning tokens: ~5,000 (показывает deeper analysis)

**Говорить:**
> "Retention scenarios дороже потому что:
> - Reasoning effort 'medium' → больше tokens
> - Customer context injection → дополнительные input tokens
> - Но это worthwhile — мы сохраняем клиентов"

3. **Show Tool Call Trace:**
   - Router → classify_message
   - Support Agent → tool execution
   - Tool result → database query
   - Eval Gate → safety check

**Говорить:**
> "Полный pipeline видимый:
> - Какие tools вызывались
> - Сколько времени заняло (duration_ms)
> - Какие данные вернулись
> - Почему AI принял решение (reasoning)"

4. **Metrics Tab:**
   - Total traces: 150+ (historical data)
   - Avg response time: 2.5 sec
   - Total cost: ~$45 (for 150 conversations)
   - Cost per conversation: ~$0.30

**Говорить:**
> "Langfuse помогает:
> - Debug когда AI делает ошибки
> - Optimize token usage
> - Track costs по categories
> - Identify slow queries или API calls"

---

### Analytics Dashboard (4 мин)

**Switch to Analytics tab** (http://localhost:9000/docs)

**Execute Endpoints:**

1. **GET /metrics/overview?days=7**

```json
{
  "period": "7d",
  "total_sessions": 156,
  "auto_sent": 124,
  "drafted": 24,
  "escalated": 8,
  "resolution_rate_pct": 79.49,
  "escalation_rate_pct": 5.13,
  "draft_rate_pct": 15.38,
  "avg_response_time_ms": 2456
}
```

**Говорить:**
> "Key metrics:
> - **79% auto-send rate** — AI handles большинство cases без human review
> - **5% escalation** — safety-критичные кейсы
> - **15% draft** — low confidence или edge cases
> - **2.5 sec avg response** — быстрее чем email (30-60 min)"

---

2. **GET /metrics/categories?days=7**

```json
[
  {
    "category": "shipping_or_delivery_question",
    "count": 58,
    "percentage": 37.18,
    "resolution_rate": 89.66,
    "avg_response_time_ms": 1850
  },
  {
    "category": "retention_primary_request",
    "count": 34,
    "percentage": 21.79,
    "resolution_rate": 67.65,
    "avg_response_time_ms": 3200
  },
  ...
]
```

**Говорить:**
> "Category breakdown:
> - Shipping questions: **90% auto-send** (простые lookups)
> - Retention: **68% auto-send** (сложнее, требует reasoning)
> - Retention медленнее (3.2 sec) из-за reasoning effort"

---

3. **GET /learning/candidates?days=7&limit=10**

```json
[
  {
    "session_id": "cw_12345",
    "customer_email": "customer@example.com",
    "primary_category": "retention_primary_request",
    "eval_decision": "draft",
    "eval_confidence": "low",
    "total_messages": 3,
    "tools_used_count": 2,
    "created_at": "2024-04-14T10:30:00Z",
    "reason": "Low confidence draft"
  },
  ...
]
```

**Говорить:**
> "Learning candidates:
> - Cases где AI был uncertain (low confidence)
> - Extended conversations (>5 messages)
> - Complex tool usage (>3 calls)
>
> Эти cases используются для:
> - Prompt engineering improvements
> - Edge case identification
> - Training data для будущих моделей"

---

**Переход:** "Теперь roadmap."

---

## Сцена 6: Next Steps & Roadmap (3 минуты)

### Immediate Next Steps (1-2 недели)

**Slide: Roadmap Timeline**

**Phase 1: Zoho Integration (1 week)**
- Replace Mock APIs с real Zoho CRM API
- Test write operations (pause, address change, etc.)
- Verify data sync между systems

**Phase 2: Email Channel Setup (3 days)**
- Configure Chatwoot email inbox
- Test email → AI → response flow
- Migrate existing n8n threads (read-only historical data)

**Phase 3: Pilot with Real Customers (2 weeks)**
- Start with web widget only (5-10 customers)
- Monitor Langfuse traces daily
- Collect feedback + iterate
- Gradual email migration (after widget proves stable)

---

### Success Metrics

**Week 1-2 (Pilot):**
- Auto-send rate: **>70%** ✅
- Escalation rate: **<10%** ✅
- Avg response time: **<10 sec** ✅
- Zero critical safety failures ✅

**Month 1 (Full Rollout):**
- Handle 500+ conversations/month
- Maintain 75%+ auto-send rate
- Customer satisfaction score >4.5/5
- Cost per conversation <$0.50

---

### Risk Mitigation

**"What if AI makes a mistake?"**
- Eval Gate catches 95%+ of errors
- Draft mode для low confidence
- Langfuse traces для debugging
- Human review для all escalations

**"What about data security?"**
- Customer data в Supabase (encrypted at rest)
- No external AI training (OpenAI opt-out configured)
- GDPR-compliant logging (PII redaction rules)

**"What if OpenAI goes down?"**
- Fallback to Claude (already configured)
- Graceful degradation → draft mode
- Email notifications для support team

---

### Q&A Prep

**Common Questions:**

1. **"How much does this cost to run?"**
   - ~$0.30 per conversation (GPT-5.1 + Langfuse + infrastructure)
   - Saves ~30 min human time ($15-20 value)
   - ROI: 50-70x

2. **"Can we customize the AI tone?"**
   - Yes — instructions stored в database (ai_answerer_instructions table)
   - Can A/B test different tones
   - Langfuse evaluations track quality metrics

3. **"What about Hebrew/Russian customers?"**
   - GPT-5.1 supports 100+ languages
   - Can detect language + respond accordingly
   - (Not in current demo but easy to add)

4. **"How do we train the AI on our specific products?"**
   - Pinecone knowledge base per category
   - Can upload product catalogs, FAQ docs
   - AI uses RAG (Retrieval-Augmented Generation)

5. **"Timeline to production?"**
   - 1 week: Zoho integration
   - 3 days: Email setup
   - 2 weeks: Pilot
   - **Total: 3-4 weeks to full production**

---

## Fallback Materials

**If live demo fails:**

1. **Screenshots folder:** `docs/demo-screenshots/`
   - Scene 2: tracking-response.png
   - Scene 3: hitl-pause-form.png
   - Scene 5: langfuse-trace.png

2. **Pre-recorded video:** https://... (15 min highlights)
   - CopilotKit forms в действии
   - Langfuse walkthrough
   - Multi-turn conversation

3. **Postman Collection:** `docs/demo-postman-collection.json`
   - All demo scenarios as API calls
   - Can show raw JSON responses

---

## Post-Demo Follow-Up

**Send to attendees:**
- [ ] This demo script (DEMO-SCRIPT.md)
- [ ] Architecture diagram (high-res PDF)
- [ ] Langfuse sample trace (exported JSON)
- [ ] Cost analysis spreadsheet
- [ ] Roadmap timeline (Gantt chart)
- [ ] Q&A document (20 prepared answers)

**Schedule:**
- [ ] Technical deep-dive session (for engineering team)
- [ ] Pilot kickoff meeting (identify first customers)
- [ ] Weekly status check-ins during rollout

---

## Rehearsal Notes

### Run 1: Solo Walkthrough
- [ ] Time each scene (should total ~40 min)
- [ ] Note any slow API responses
- [ ] Practice speaking points without reading slides

### Run 2: With Colleague (QA)
- [ ] Get feedback on clarity
- [ ] Identify confusing parts
- [ ] Test Q&A responses

### Run 3: Full Dress Rehearsal
- [ ] Simulate real meeting environment
- [ ] Test fallback materials
- [ ] Final timing adjustments

**Target:** Confident delivery, smooth transitions, <42 minutes total
