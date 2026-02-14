---
name: agno-sdk
description: Agno AgentOS patterns for the Lev Haolam AI Platform. Use when writing or modifying Agno Agent code, configuring models, tools, knowledge, or multi-turn sessions. Contains project-specific architecture + gotchas. For generic SDK docs use context7 with /agno-agi/agno-docs.
---

# Agno SDK — Project Patterns

Project-specific Agno patterns for Lev Haolam AI Platform. For up-to-date generic SDK docs, use context7:

```bash
# Generic Agno SDK docs (always fresh)
bun /Users/glebzavalov/Desktop/Projects/LevHaolam/ai_agent_chat/.agents/skills/gleb-context7/scripts/context7.ts get-library-docs \
  --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "<your topic>"

# Common topics:
#   "Agent tools knowledge"          — agent creation + tools + RAG
#   "OpenAIChat reasoning_effort"    — model config + reasoning
#   "output_schema structured"       — structured output with Pydantic
#   "PostgresDb session storage"     — native multi-turn sessions
#   "HITL confirmation"              — human-in-the-loop patterns
#   "PineconeDb knowledge vector"    — Pinecone integration
#   "Team multi-agent"               — multi-agent teams
#   "guardrails safety"              — built-in guardrails

# Full docs as single file (fallback if context7 result is incomplete):
# https://docs.agno.com/llms-full.txt
```

---

## Project Architecture

### Request Pipeline (`api/routes.py`)

```
POST /api/chat
  1. Red line safety check (regex) -> instant escalate
  2. Router Agent (classify_message) -> RouterOutput (category, urgency, email)
  3. Load conversation history (get_conversation_history)
  4. Support Agent (create_support_agent -> agent.arun) + Outstanding Detection (parallel)
  5. Cancel link injection (retention only)
  6. Response assembly (greeting + opener + body + closer + sign-off in HTML)
  7. Eval Gate (Tier 1: regex + Tier 2: LLM)
  8. Save to DB -> Return ChatResponse
```

### Support Agent Factory (`agents/support.py`)

New agent per request. No persistent state.

```python
def _resolve_model(config: CategoryConfig):
    if config.model_provider in ("openai_chat", "openai_responses"):
        kwargs = {"id": config.model}
        if config.reasoning_effort:
            kwargs["reasoning_effort"] = config.reasoning_effort  # passed to OpenAIChat()
        return OpenAIChat(**kwargs)
    elif config.model_provider == "anthropic":
        return Claude(id=config.model)

def create_support_agent(category: str) -> Agent:
    config = CATEGORY_CONFIG[category]
    return Agent(
        name=f"Support Agent ({category})",
        model=_resolve_model(config),
        instructions=load_instructions(category),  # from DB
        knowledge=create_knowledge(config.pinecone_namespace),
        search_knowledge=True,
        tools=resolve_tools(config.tools),
        markdown=True,
    )
```

### Category Config (`agents/config.py`)

```python
@dataclass(frozen=True)
class CategoryConfig:
    model: str                        # "gpt-5.1"
    model_provider: str               # "openai_chat" | "openai_responses" | "anthropic"
    reasoning_effort: str | None      # None | "low" | "medium" | "high"
    tools: list[str]                  # ["get_subscription", "track_package"]
    pinecone_namespace: str = ""      # "shipping", "retention", etc.
    auto_send_phase: int = 99
```

10 categories: `shipping_or_delivery_question`, `payment_question`, `frequency_change_request`, `skip_or_pause_request`, `recipient_or_address_change`, `customization_request`, `damaged_or_leaking_item_report`, `gratitude`, `retention_primary_request`, `retention_repeated_request`

### Tool Registry (`tools/__init__.py`)

```python
TOOL_REGISTRY = {
    "get_subscription": customer.get_subscription,        # read-only, queries DB
    "get_customer_history": customer.get_customer_history, # read-only
    "get_payment_history": customer.get_payment_history,   # read-only
    "track_package": shipping.track_package,               # read-only
    "get_box_contents": customization.get_box_contents,    # read-only
    "generate_cancel_link": retention.generate_cancel_link,# AES-256 encryption
    "change_frequency": subscription.change_frequency,     # stub, pending_confirmation
    "skip_month": subscription.skip_month,                 # stub
    "pause_subscription": subscription.pause_subscription, # stub
    "change_address": subscription.change_address,         # stub
    "create_damage_claim": damage.create_damage_claim,     # stub
    "request_photos": damage.request_photos,               # stub
}
```

### Multi-turn (Manual, NOT Agno native)

```python
# database/queries.py — load history
history = get_conversation_history(session_id, limit=10)

# api/routes.py — inject into agent_input
if history:
    agent_input_parts.append("[Conversation History]")
    for msg in history:
        role = "Customer" if msg["role"] == "user" else "Agent"
        content = msg["content"][:500] + "..." if role == "Agent" and len(msg["content"]) > 500 else msg["content"]
        agent_input_parts.append(f"{role}: {content}")
    agent_input_parts.append("[End History]")
```

Session IDs: Chatwoot `cw_{conversation_id}`, API from `request.session_id`, fallback `sess_{uuid}`.

### Import Paths (inside Docker)

```python
from config import settings
from agents.router import classify_message
from agents.support import create_support_agent
from database.connection import get_client
from database.queries import get_conversation_history, save_session, save_message
from database.customer_queries import lookup_customer, get_active_subscription_by_email
from guardrails.safety import check_red_lines
from tools import resolve_tools, TOOL_REGISTRY
```

---

## Gotchas (Learned from Production)

1. **`reasoning_effort` goes on `OpenAIChat()`**, not `Agent()`. Values: `"none"`, `"low"`, `"medium"`, `"high"`.

2. **`arun()` takes a single string**, not a messages list. Multi-turn = prepend history to message or use Agno's `db=` + `add_history_to_context=True`.

3. **Agno async session bugs** (2026-02): GitHub #2497 (context loss in arun), #2570 (memory duplication). We use manual history loading instead.

4. **`output_schema` (not `response_model`)** for structured output. `response.content` returns Pydantic object.

5. **`search_knowledge=True`** must be set on Agent. Just `knowledge=` is not enough.

6. **Tool docstrings are the schema.** LLM decides when/how to call tools based on docstring + type hints. Write clear Args.

7. **Factory pattern:** New Agent per request. Don't reuse across requests (state leaks).

8. **`instructions` is `list[str]`**, each element = system prompt section.

9. **Pinecone namespace isolation.** `PineconeDb(namespace="shipping")` per category.

10. **Agno `db=PostgresDb()` creates own tables** (`agno_sessions`, `agno_messages`). Duplicates with custom tables.

---

## Files Reference

| File | Purpose |
|------|---------|
| `agents/config.py` | CATEGORY_CONFIG (10 categories) |
| `agents/support.py` | Factory: create_support_agent() + _resolve_model() |
| `agents/router.py` | Router Agent (classify_message) |
| `agents/instructions.py` | Load instructions from DB |
| `agents/eval_gate.py` | Eval Gate (regex + LLM) |
| `agents/outstanding.py` | Outstanding case detection |
| `agents/name_extractor.py` | Customer name extraction |
| `agents/response_assembler.py` | HTML response assembly |
| `api/routes.py` | Pipeline + Chatwoot webhook |
| `tools/__init__.py` | TOOL_REGISTRY + resolve_tools() |
| `tools/customer.py` | get_subscription, get_customer_history, get_payment_history |
| `tools/shipping.py` | track_package |
| `database/queries.py` | Sessions, messages, history, eval |
| `database/customer_queries.py` | Customer data (8 functions) |
| `guardrails/safety.py` | Red lines + subscription safety |
| `knowledge/pinecone_client.py` | PineconeDb per-namespace |

---

## Testing

```bash
docker compose exec ai-engine pytest tests/ -v                         # all tests
docker compose exec ai-engine pytest tests/ -v --ignore=tests/test_pipeline.py  # unit only (fast)
docker compose build ai-engine && docker compose up -d ai-engine       # rebuild
```

Mock pattern for DB tests:

```python
from unittest.mock import MagicMock, patch

@patch("database.customer_queries.get_client")
def test_lookup(self, mock_get_client):
    client = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(data=[{"email": "test@example.com"}])
    client.table.return_value = chain
    mock_get_client.return_value = client
```
