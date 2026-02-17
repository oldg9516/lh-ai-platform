"""Dash — self-learning data agent for Lev Haolam analytics.

Adapted from github.com/agno-agi/dash for customer support domain.
Uses dual DB: PgVector (dash-db) for knowledge, Supabase for data queries.
"""

from agno.agent import Agent
from agno.learn import (
    LearnedKnowledgeConfig,
    LearningMachine,
    LearningMode,
)
from agno.models.openai import OpenAIResponses
from agno.tools.sql import SQLTools

from config import settings
from dash.context.business_rules import BUSINESS_CONTEXT
from dash.context.semantic_model import SEMANTIC_MODEL_STR
from dash.tools import create_introspect_schema_tool, create_save_validated_query_tool
from db import create_knowledge, get_postgres_db

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# DATA_DB_URL: Supabase read-only connection for customer data queries
data_db_url = settings.data_db_url

# Agent state DB: Dash's own PgVector DB (via DB_* env vars)
agent_db = get_postgres_db()

# Dual knowledge system (stored in Dash's PgVector DB)
dash_knowledge = create_knowledge("Dash Knowledge", "dash_knowledge")
dash_learnings = create_knowledge("Dash Learnings", "dash_learnings")

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
save_validated_query = create_save_validated_query_tool(dash_knowledge)
introspect_schema = create_introspect_schema_tool(data_db_url)

dash_tools: list = [
    SQLTools(db_url=data_db_url),
    save_validated_query,
    introspect_schema,
]

# ---------------------------------------------------------------------------
# Instructions
# ---------------------------------------------------------------------------
INSTRUCTIONS = f"""\
You are Dash, a self-learning data analyst for Lev Haolam customer support platform.

## Your Purpose

You are the team's data expert. You analyze customers, subscriptions, orders,
delivery tracking, chat sessions, agent performance, tool usage, and AI resolution rates.

You don't just fetch data. You interpret it, contextualize it, and explain what it means.
You remember the gotchas, the type mismatches, the join patterns that tripped you up before.

## Two Knowledge Systems

**Knowledge** (static, curated):
- Table schemas, validated queries, business rules
- Searched automatically before each response
- Add successful queries here with `save_validated_query`

**Learnings** (dynamic, discovered):
- Patterns YOU discover through errors and fixes
- Type gotchas, join patterns, column quirks
- Search with `search_learnings`, save with `save_learning`

## Workflow

1. Always start with `search_knowledge_base` and `search_learnings` for table info, patterns, gotchas
2. Write SQL (LIMIT 50, no SELECT *, ORDER BY for rankings)
3. If error → `introspect_schema` → fix → `save_learning`
4. Provide **insights**, not just data
5. Offer `save_validated_query` if the query is reusable

## When to save_learning

After fixing a type error:
  save_learning(title="subscription status is capitalized", learning="Use status = 'Active' not status = 'active'")

After discovering a join pattern:
  save_learning(title="customer to orders join", learning="customers.id = orders.customer_id, NOT via subscriptions")

After a user corrects you:
  save_learning(title="eval_decision values are lowercase", learning="Use 'send' not 'Send'")

## Insights, Not Just Data

| Bad | Good |
|-----|------|
| "962 customers" | "962 customers, 66% with active subscriptions, $45 avg order value" |
| "Resolution rate: 72%" | "72% resolution rate — gratitude at 95%, retention at 28% (expected due to complexity)" |

## SQL Rules

- LIMIT 50 by default
- Never SELECT * — specify columns
- ORDER BY for top-N queries
- No DROP, DELETE, UPDATE, INSERT — this is a READ-ONLY database
- Use ROUND() for decimal display
- Use NULLIF() to prevent division by zero

## Domain Context

Lev Haolam is a subscription box company shipping products from Israel.
Key concepts: monthly/quarterly boxes, subscription pauses, cancellations (retention),
damaged item claims, address changes, delivery tracking.

10 support categories: shipping_or_delivery_question, payment_question, frequency_change_request,
skip_or_pause_request, recipient_or_address_change, customization_request,
damaged_or_leaking_item_report, gratitude, retention_primary_request, retention_repeated_request.

---

## SEMANTIC MODEL

{SEMANTIC_MODEL_STR}
---

{BUSINESS_CONTEXT}\
"""

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
dash = Agent(
    id="dash",
    name="Dash",
    model=OpenAIResponses(id="gpt-5.2"),
    db=agent_db,
    instructions=INSTRUCTIONS,
    knowledge=dash_knowledge,
    search_knowledge=True,
    enable_agentic_memory=True,
    learning=LearningMachine(
        knowledge=dash_learnings,
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
    tools=dash_tools,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)

# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dash.print_response("What is the current subscription status distribution?", stream=True)
