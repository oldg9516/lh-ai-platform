---
name: agno-sdk
description: Agno AgentOS Python SDK patterns for building AI agents, teams, and workflows. Use when writing Agno Agent code, creating tools, configuring knowledge bases (Pinecone, PgVector), setting up guardrails, HITL flows, structured output, AgentOS FastAPI deployment, or any agent architecture with Agno framework. Covers Agent, Tool, Knowledge, Guardrails, HITL, Teams, Workflows, AgentOS, structured I/O, memory, storage, and MCP integration.
---

# Agno AgentOS SDK Reference

Build production-ready AI agents with Agno (v2.4+). This skill covers the core API patterns for agents, tools, knowledge, guardrails, HITL, structured output, and AgentOS deployment.

## Installation

```bash
# Core
pip install agno

# With extras (pick what you need)
pip install "agno[openai,anthropic,pinecone,postgres,pdf]"
```

Env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`, `AGNO_TELEMETRY=false` (opt-out telemetry).

---

## 1. Agent Basics

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat, OpenAIResponses

agent = Agent(
    id="support-agent",           # Unique ID (used in AgentOS routing)
    name="Support Agent",
    model=OpenAIChat(id="gpt-5.1"),  # or OpenAIResponses(id="gpt-5.2")
    description="Customer support agent",
    instructions=[                 # List of strings -> system prompt sections
        "You are a helpful customer support agent.",
        "Always be polite and professional.",
        "Never confirm subscription changes directly.",
    ],
    markdown=True,
    show_tool_calls=True,
    debug_mode=False,
)

# Single response
agent.print_response("Hello, how can I help?", stream=True)

# Programmatic
response = agent.run("What is your return policy?")
print(response.content)  # str by default

# Async
import asyncio
asyncio.run(agent.aprint_response("Hello", markdown=True))
```

### Model Providers

```python
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.anthropic import Claude
from agno.models.ollama import Ollama

model = OpenAIChat(id="gpt-5.1")            # OpenAI Chat
model = OpenAIResponses(id="gpt-5.2")       # OpenAI Responses API
model = Claude(id="claude-sonnet-4-5")       # Anthropic
model = Ollama(id="llama3:8b")               # Local via Ollama
```

### Key Agent Parameters

| Parameter                 | Type        | Description                                      |
| ------------------------- | ----------- | ------------------------------------------------ |
| `id`                      | str         | Unique agent identifier                          |
| `name`                    | str         | Display name                                     |
| `model`                   | Model       | LLM model instance                               |
| `description`             | str         | What the agent does (sent to model)              |
| `instructions`            | list[str]   | System prompt rules                              |
| `tools`                   | list        | Tools/Toolkits available                         |
| `knowledge`               | Knowledge   | RAG knowledge base                               |
| `db`                      | AgentDb     | Session/state persistence (SqliteDb, PostgresDb) |
| `output_schema`           | BaseModel   | Pydantic model for structured output             |
| `input_schema`            | BaseModel   | Validate input format                            |
| `markdown`                | bool        | Markdown formatting                              |
| `add_history_to_context`  | bool        | Include chat history                             |
| `num_history_runs`        | int         | Number of past runs in context                   |
| `add_datetime_to_context` | bool        | Add current datetime                             |
| `search_knowledge`        | bool        | Auto-search knowledge base                       |
| `read_chat_history`       | bool        | Enable history reading tool                      |
| `learning`                | bool        | Enable self-learning                             |
| `enable_memories`         | bool        | User memory persistence                          |
| `team`                    | list[Agent] | Sub-agents for delegation                        |

---

## 2. Tools

### Python Functions as Tools

Any Python function with type hints becomes a tool:

```python
import json
from agno.agent import Agent

def search_orders(customer_email: str, days: int = 30) -> str:
    """Search recent orders for a customer.

    Args:
        customer_email: Customer's email address
        days: Number of days to look back (default: 30)

    Returns:
        str: JSON string of matching orders
    """
    orders = db_query(customer_email, days)
    return json.dumps(orders)

agent = Agent(
    tools=[search_orders],
    instructions=["Use search_orders to find customer orders."],
)
```

**Critical:** Docstring + type hints = tool schema for the LLM. Write clear Args descriptions.

### @tool Decorator (Advanced)

```python
from agno.tools import tool

@tool(
    name="cancel_subscription",
    description="Generate cancellation link for customer",
    requires_confirmation=True,    # HITL: pause for approval
    stop_after_tool_call=True,     # Return result immediately
    cache_results=True,
    cache_ttl=300,
    show_result=True,
)
def cancel_subscription(customer_id: str, reason: str) -> str:
    """Generate a personalized cancellation link."""
    link = generate_cancel_link(customer_id)
    return f"Cancellation link: {link}"
```

### @tool Decorator Options

| Option                  | Type           | Description                                     |
| ----------------------- | -------------- | ----------------------------------------------- |
| `requires_confirmation` | bool           | HITL: pause run, wait for approval              |
| `requires_user_input`   | bool           | HITL: collect user input before execution       |
| `user_input_fields`     | list           | Fields the user must fill                       |
| `external_execution`    | bool           | Tool runs outside agent control                 |
| `stop_after_tool_call`  | bool           | Stop agent after tool returns                   |
| `show_result`           | bool           | Include tool output in response (default: True) |
| `cache_results`         | bool           | Cache tool results                              |
| `cache_ttl`             | int            | Cache TTL seconds                               |
| `tool_hooks`            | list[Callable] | Pre/post execution hooks                        |

### Toolkit Class (Grouped Tools)

```python
from agno.tools import Toolkit

class SupportToolkit(Toolkit):
    def __init__(self, db_url: str):
        super().__init__(name="support_tools")
        self.db_url = db_url
        self.register(self.search_orders)
        self.register(self.get_tracking)

    def search_orders(self, email: str) -> str:
        """Search orders by email."""
        return json.dumps(results)

    def get_tracking(self, order_id: str) -> str:
        """Get tracking info for order."""
        return json.dumps(tracking)

agent = Agent(tools=[SupportToolkit(db_url="postgresql://...")])
```

### Built-in Toolkits (100+)

```python
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.mcp import MCPTools
```

---

## 3. Knowledge (RAG)

### Pinecone

```python
import os
from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

vector_db = PineconeDb(
    name="support-examples",
    dimension=1536,
    metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
    api_key=os.getenv("PINECONE_API_KEY"),
    use_hybrid_search=True,      # hybrid (dense + sparse)
    hybrid_alpha=0.5,            # 0=sparse, 1=dense
)

knowledge = Knowledge(
    name="Support Knowledge Base",
    description="Outstanding support examples and response templates",
    vector_db=vector_db,
)

# Load content (do once)
knowledge.insert(
    name="SupportDocs",
    url="https://example.com/docs.pdf",
    metadata={"doc_type": "support_guide"},
)

# Or add content from text
knowledge.add_content(content="Your text here...")

# Delete
vector_db.delete_by_name("SupportDocs")
vector_db.delete_by_metadata({"doc_type": "support_guide"})

agent = Agent(knowledge=knowledge, search_knowledge=True)
```

### PgVector

```python
from agno.vectordb.pgvector import PgVector, SearchType

vector_db = PgVector(
    table_name="support_knowledge",
    db_url="postgresql+psycopg://user:pass@localhost:5432/db",
    search_type=SearchType.hybrid,  # hybrid | vector | keyword
)
knowledge = Knowledge(vector_db=vector_db)
```

### KnowledgeTools (Agentic RAG)

```python
from agno.tools.knowledge import KnowledgeTools

knowledge_tools = KnowledgeTools(
    knowledge=knowledge,
    think=True,         # Reason about search
    search=True,        # Search tool
    analyze=True,       # Analysis tool
    add_few_shot=True,  # Example queries
)
agent = Agent(tools=[knowledge_tools], markdown=True)
```

### Supported VectorDBs (25+)

PgVector, Pinecone, Qdrant, ChromaDB, LanceDB, Milvus, Weaviate, MongoDB Atlas, Redis, SingleStore, SurrealDB, Clickhouse, Upstash, and more. Unified interface - switch by changing one line.

---

## 4. Structured Output

```python
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIResponses

class TicketClassification(BaseModel):
    category: str = Field(description="shipping/payment/retention/etc")
    subcategory: str = Field(description="Specific subcategory")
    priority: str = Field(description="low/medium/high/urgent")
    confidence: float = Field(description="Confidence 0.0-1.0")
    summary: str = Field(description="Brief summary")

agent = Agent(
    model=OpenAIResponses(id="gpt-5.1"),
    output_schema=TicketClassification,
)

response = agent.run("Package not delivered for 2 weeks")
result: TicketClassification = response.content
print(result.category)    # "shipping"
print(result.confidence)  # 0.92

# Per-run schema override
response = agent.run("Classify this", output_schema=OtherSchema)
```

**Important:** `output_schema` -> `response.content` returns Pydantic object, not string. Supported natively by OpenAI, Anthropic, Google. Fallback: `use_json_mode=True`.

---

## 5. Guardrails

```python
from agno.guardrails.pii_detection import PIIDetectionGuardrail
from agno.guardrails.prompt_injection import PromptInjectionGuardrail

agent = Agent(
    guardrails=[PIIDetectionGuardrail(), PromptInjectionGuardrail()],
)
```

### Custom Guardrail via Tool Hooks

```python
from agno.tools import tool
from typing import Any, Callable, Dict

def safety_hook(function_name: str, function_call: Callable, arguments: Dict[str, Any]):
    """Log and monitor sensitive tool calls."""
    sensitive_ops = ["cancel_subscription", "refund_payment"]
    if function_name in sensitive_ops:
        print(f"ALERT: {function_name}({arguments})")
    return function_call(**arguments)

@tool(tool_hooks=[safety_hook])
def process_refund(order_id: str, amount: float) -> str:
    """Process refund."""
    return f"Refunded ${amount} for {order_id}"
```

---

## 6. Human-in-the-Loop (HITL)

```python
from agno.tools import tool
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.os import AgentOS

@tool(requires_confirmation=True)
def send_refund(order_id: str, amount: float) -> str:
    """Process a refund. Args: order_id, amount."""
    return f"Refunded ${amount} for order {order_id}"

@tool(requires_user_input=True, user_input_fields=["reason"])
def escalate_ticket(ticket_id: str, reason: str = "") -> str:
    """Escalate ticket. Requires user reason."""
    return f"Ticket {ticket_id} escalated: {reason}"

agent = Agent(
    id="support_agent",
    tools=[send_refund, escalate_ticket],
    db=PostgresDb(db_url="postgresql+psycopg://..."),
)

# AgentOS flow:
# POST /agents/support_agent/runs -> status: "paused"
# POST /agents/support_agent/runs/{run_id}/confirm -> continues
```

---

## 7. Memory & Storage

```python
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb

db = PostgresDb(db_url="postgresql+psycopg://user:pass@host:5432/db")

agent = Agent(
    db=db,
    add_history_to_context=True,
    num_history_runs=5,
    enable_memories=True,    # Remember user facts
    learning=True,           # Self-learning across users
)
```

Memory types: session history, user memories, user profiles, learned knowledge. Learning modes: `always` or `agentic`.

---

## 8. Teams (Multi-Agent)

```python
shipping_agent = Agent(
    name="Shipping Specialist",
    role="Handle shipping queries",
    tools=[track_package, search_orders],
)

billing_agent = Agent(
    name="Billing Specialist",
    role="Handle payment queries",
    tools=[search_payments, process_refund],
)

team_leader = Agent(
    name="Support Team",
    team=[shipping_agent, billing_agent],
    model=OpenAIChat(id="gpt-5.1"),
    instructions=["Route to the appropriate specialist."],
)

team_leader.print_response("Where is my package?")
```

---

## 9. AgentOS (Production Deployment)

```python
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.os import AgentOS

agent_os = AgentOS(
    id="lev-haolam-support",
    agents=[router_agent, support_agent],
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="main:app", port=7777, reload=True)
```

### Bring Your Own FastAPI

```python
from fastapi import FastAPI
from agno.os import AgentOS

app = FastAPI(title="Support API")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook/chatwoot")
async def chatwoot_webhook(payload: dict):
    ...

agent_os = AgentOS(agents=[support_agent], base_app=app)
app = agent_os.get_app()  # Combined: your routes + AgentOS
```

### Auto-Generated Endpoints

| Endpoint                                   | Method | Description     |
| ------------------------------------------ | ------ | --------------- |
| `/agents/{agent_id}/runs`                  | POST   | Start agent run |
| `/agents/{agent_id}/runs/{run_id}`         | GET    | Run status      |
| `/agents/{agent_id}/runs/{run_id}/confirm` | POST   | Confirm HITL    |
| `/agents/{agent_id}/sessions`              | GET    | List sessions   |
| `/config`                                  | GET    | Configuration   |
| `/docs`                                    | GET    | Swagger UI      |

---

## 10. MCP Integration

```python
from agno.tools.mcp import MCPTools

agent = Agent(
    tools=[MCPTools(transport="streamable-http", url="https://server.com/mcp")],
)
# AgentOS also doubles as MCP server for other systems
```

---

## Support Platform Patterns

### Router Agent (Fast Classification)

```python
class TicketRoute(BaseModel):
    category: str = Field(description="shipping|payment|retention|...")
    subcategory: str
    confidence: float

router = Agent(
    id="router",
    model=OpenAIChat(id="gpt-5.1"),
    output_schema=TicketRoute,
    instructions=["Classify into category and subcategory."],
)
```

### Dynamic Agent Factory

```python
CATEGORY_CONFIG = {
    "shipping": {"model": "gpt-5.1", "tools": [track_package]},
    "retention": {"model": "claude-sonnet-4-5", "tools": [generate_cancel_link]},
}

def create_support_agent(category: str, config: dict) -> Agent:
    model_map = {
        "gpt-5.1": OpenAIChat(id="gpt-5.1"),
        "claude-sonnet-4-5": Claude(id="claude-sonnet-4-5"),
    }
    return Agent(
        id=f"support-{category}",
        model=model_map[config["model"]],
        tools=config["tools"],
        knowledge=support_knowledge,
        db=db,
        instructions=load_instructions_from_db(category),
    )
```

### Safety Tool (Never Confirm Directly)

```python
@tool(requires_confirmation=True, stop_after_tool_call=True)
def generate_cancel_link(customer_id: str) -> str:
    """Generate self-service cancellation link. NEVER confirm cancellation directly."""
    encrypted = encrypt_customer_id(customer_id)
    return f"https://levhaolam.com/cancel?token={encrypted}"
```

### Eval Agent (Quality Gate)

```python
class EvalResult(BaseModel):
    approved: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str]
    suggested_fix: str | None = None

eval_agent = Agent(
    id="eval-gate",
    model=OpenAIChat(id="gpt-5.1"),
    output_schema=EvalResult,
    instructions=["Evaluate draft for quality/safety. 0.8+ = approved."],
)
```

---

## Key Imports Cheat Sheet

```python
# Core
from agno.agent import Agent
from agno.tools import tool, Toolkit
from agno.os import AgentOS

# Models
from agno.models.openai import OpenAIChat, OpenAIResponses
from agno.models.anthropic import Claude

# Knowledge & VectorDB
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb
from agno.vectordb.pgvector import PgVector, SearchType
from agno.tools.knowledge import KnowledgeTools
from agno.knowledge.embedder.openai import OpenAIEmbedder

# Storage
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb

# Tools
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools

# Structured Output
from pydantic import BaseModel, Field
```

---

## Tips & Gotchas

1. **Docstrings = tool descriptions.** LLM uses them to decide when/how to call tools.
2. **`output_schema` -> `response.content` is Pydantic object**, not string.
3. **`requires_confirmation=True`** pauses run in AgentOS. Frontend must call confirm endpoint.
4. **Knowledge.insert() with `name`** is idempotent - use for upserts.
5. **`add_history_to_context=True` + `num_history_runs=5`** for conversations.
6. **AgentOS = FastAPI app.** Use `base_app` for custom routes/middleware/auth.
7. **Model agnostic.** Change `model=` to switch providers, no code changes.
8. **Hybrid search** gives best retrieval: `use_hybrid_search=True` (Pinecone), `SearchType.hybrid` (PgVector).
9. **`learning=True`** enables self-learning from interactions.
10. **Set `AGNO_TELEMETRY=false`** in production `.env`.
11. **Pinecone v5.4.2** recommended for best Agno compatibility.
12. **AgentOS default port: 7777.** Swagger at `/docs`.
