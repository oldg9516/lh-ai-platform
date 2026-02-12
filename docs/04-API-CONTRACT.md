# API Contract: Inter-Service Communication

## 1. AI Engine API (services/ai-engine)

### POST /api/chat
Основной endpoint для обработки сообщений.

**Request:**
```json
{
  "message": "I want to cancel my subscription",
  "session_id": "sess_abc123",           // optional, создаётся если нет
  "conversation_id": "chatwoot_conv_456", // optional, от Chatwoot
  "contact": {                            // optional, от Chatwoot
    "email": "john@example.com",
    "name": "John Smith"
  },
  "metadata": {                           // optional
    "channel": "widget",                  // widget | whatsapp | facebook | email | telegram
    "language": "en"
  }
}
```

**Response (success):**
```json
{
  "response": "I understand you'd like to cancel your subscription. Let me help you with that...",
  "session_id": "sess_abc123",
  "category": "retention_primary_request",
  "decision": "send",                     // send | draft | escalate
  "confidence": "high",                   // high | medium | low
  "actions_taken": [],                     // list of executed tools
  "actions_pending": [                     // HITL approvals needed
    {
      "tool": "generate_cancel_link",
      "description": "Generate personalized cancellation link",
      "requires_approval": true
    }
  ],
  "metadata": {
    "model_used": "claude-sonnet-4-5",
    "reasoning_effort": "extended",
    "processing_time_ms": 3200,
    "is_outstanding": false,
    "outstanding_trigger": "none"
  }
}
```

**Response (escalation):**
```json
{
  "response": "I'm connecting you with a support agent who can better assist you.",
  "session_id": "sess_abc123",
  "category": "retention_primary_request",
  "decision": "escalate",
  "escalation_reason": "death_threat_detected",
  "context_for_agent": {
    "category": "retention_primary_request",
    "customer_email": "john@example.com",
    "subscription_id": "sub_12345",
    "conversation_summary": "Customer requesting cancellation due to...",
    "ai_draft": "..."
  }
}
```

### POST /api/chat/approve
Подтверждение HITL action.

**Request:**
```json
{
  "session_id": "sess_abc123",
  "action_id": "act_789",
  "approved": true
}
```

**Response:**
```json
{
  "response": "Done! I've generated your personalized link: https://levhaolam.com/pay/subscriptions/cancel?al=...",
  "action_result": {
    "tool": "generate_cancel_link",
    "status": "completed",
    "result": "https://levhaolam.com/pay/subscriptions/cancel?al=abc123"
  }
}
```

### POST /api/webhook/chatwoot
Webhook от Chatwoot при новом сообщении.

**Request (from Chatwoot):**
```json
{
  "event": "message_created",
  "message_type": "incoming",
  "content": "Where is my package?",
  "conversation": {
    "id": 456,
    "contact_inbox": {
      "contact": {
        "email": "john@example.com",
        "name": "John Smith"
      }
    }
  },
  "account": {
    "id": 1
  }
}
```

**Response:**
```json
{
  "status": "processed"
}
```
(AI отвечает асинхронно через Chatwoot API)

### GET /api/health
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "pinecone": "connected",
    "openai": "available",
    "anthropic": "available"
  },
  "version": "0.1.0"
}
```

### GET /api/sessions/{session_id}
```json
{
  "session_id": "sess_abc123",
  "customer_email": "john@example.com",
  "category": "shipping_or_delivery_question",
  "status": "active",
  "messages": [
    {
      "role": "user",
      "content": "Where is my package?",
      "timestamp": "2026-02-12T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Let me check your tracking...",
      "timestamp": "2026-02-12T10:00:03Z",
      "metadata": {
        "model": "gpt-5.1",
        "tools_used": ["track_package"]
      }
    }
  ],
  "created_at": "2026-02-12T10:00:00Z"
}
```

---

## 2. Chatwoot API (used by AI Engine)

### Отправка сообщения AI → клиенту

**POST** `{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{CONVERSATION_ID}/messages`

```json
{
  "content": "Your package is currently in transit...",
  "message_type": "outgoing",
  "private": false
}
```

Headers:
```
api_access_token: {CHATWOOT_API_TOKEN}
Content-Type: application/json
```

### Assign conversation к human agent (escalation)

**POST** `{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{CONVERSATION_ID}/assignments`

```json
{
  "assignee_id": null,  // unassign from bot → goes to human queue
  "team_id": 1          // assign to support team
}
```

### Добавить label к conversation

**POST** `{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{CONVERSATION_ID}/labels`

```json
{
  "labels": ["ai_escalation", "retention", "high_priority"]
}
```

### Добавить приватную заметку (контекст для агента)

**POST** `{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{CONVERSATION_ID}/messages`

```json
{
  "content": "**AI Context:**\nCategory: retention_primary_request\nCustomer: John Smith (sub_12345)\nReason: Customer wants to cancel due to...\nAI Draft: ...",
  "message_type": "outgoing",
  "private": true
}
```

---

## 3. Internal Tool APIs (AI Engine ↔ External Services)

### Zoho API (Customer lookup)
```
GET /api/v2/Contacts/search?email={email}
→ { data: [{ id, Full_Name, Email, Subscription_Status, ... }] }
```

### Supabase (Direct DB)
Через `psycopg2` connection pool. Не через REST API — для скорости.

### Pinecone (Vector Search)
```python
index.query(
    vector=embedding,
    top_k=5,
    namespace="outstanding-cases",
    filter={"request_subtype": category},
    include_metadata=True
)
```

### LH Pay API (Subscription actions)
```
POST /api/subscriptions/{id}/pause    → { success: true }
POST /api/subscriptions/{id}/skip     → { success: true }
PUT  /api/subscriptions/{id}/address  → { success: true }
POST /api/claims                      → { claim_id: "CLM_123" }
```

---

## 4. Webhook Flow Diagram

```
Customer types "Cancel my subscription"
         │
         ▼
┌─────────────────┐
│    CHATWOOT      │ ← receives message from widget/WhatsApp/etc
│                  │
│  event:          │
│  message_created │
└────────┬────────┘
         │ POST /api/webhook/chatwoot
         ▼
┌─────────────────┐
│   AI ENGINE      │
│                  │
│  1. Router       │ → retention_primary_request
│  2. Identify     │ → john@example.com → sub_12345
│  3. Support      │ → Claude Sonnet 4.5 + tools
│  4. Outstanding  │ → is_outstanding: false
│  5. Eval Gate    │ → decision: send
│                  │
└────────┬────────┘
         │ POST /conversations/{id}/messages
         ▼
┌─────────────────┐
│    CHATWOOT      │ → delivers AI response to customer
└─────────────────┘
```

---

## 5. Error Handling

### AI Engine errors → Chatwoot
```json
{
  "content": "I'm sorry, I'm having trouble processing your request right now. Let me connect you with a support agent.",
  "message_type": "outgoing"
}
```
+ Assign to human team + Private note with error details.

### Timeouts
- Router: 5s timeout → default category "general"
- Support Agent: 120s timeout → escalate to human
- Tool execution: 30s timeout → skip tool, respond without it

### Rate limits
- OpenAI: retry with exponential backoff (max 3 retries)
- Anthropic: retry with exponential backoff (max 3 retries)
- Chatwoot API: 100 req/min → queue if needed
