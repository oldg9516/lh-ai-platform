# Analytics Service

AgentOS-powered analytics service for monitoring AI support platform performance.

## Overview

The analytics service provides three access modes:

1. **AgentOS Control Plane** (`localhost:9000/`) — Interactive chat UI for exploratory analytics
2. **Custom FastAPI Endpoints** (`/metrics/*`, `/charts/*`) — Pre-computed metrics for dashboards
3. **Langfuse** (`localhost:3100`) — Observability for SQL query performance (separate project)

## Architecture

- **Analytics Agent**: Natural language → SQL using PostgresTools + PgVector Knowledge Base
- **Read-Only Database**: PostgreSQL connection with `analytics_readonly` user (SELECT only)
- **Knowledge Base**: Table schemas, sample queries, business rules for RAG-powered SQL generation
- **Plotly Charts**: JSON visualizations for embedding in frontends

## Quick Start

### 1. Create Langfuse Project (one-time setup)

```bash
# Open Langfuse UI
open http://localhost:3100

# Settings → Projects → "Create Project"
# Name: "Analytics Agent"
# Description: "SQL analytics agent observability"

# Copy API keys to .env:
# LANGFUSE_ANALYTICS_PUBLIC_KEY=pk-analytics-...
# LANGFUSE_ANALYTICS_SECRET_KEY=sk-analytics-...
```

### 2. Start the Service

```bash
# Build and start
docker compose build analytics
docker compose up analytics -d

# Check logs
docker compose logs -f analytics
```

### 3. Load Knowledge Base

```bash
# Run inside container
docker compose exec analytics python load_knowledge.py

# Expected output:
# ✅ Loaded schema: chat_sessions
# ✅ Loaded schema: chat_messages
# ✅ Loaded schema: agent_traces
# ✅ Loaded query: resolution_rate
# ✅ Loaded query: category_breakdown
# ✅ Loaded query: customer_patterns
# ✅ Loaded rules: metrics
# ✨ Knowledge base loaded successfully!
```

### 4. Verify Setup

```bash
# Health check
curl http://localhost:9000/api/health

# Swagger UI (all endpoints)
open http://localhost:9000/docs

# Control Plane UI (agent chat)
open http://localhost:9000/

# Langfuse observability (switch to "Analytics Agent" project)
open http://localhost:3100
```

## API Endpoints

### Metrics

```bash
# Overview metrics
curl http://localhost:9000/metrics/overview?days=7

# Category breakdown
curl http://localhost:9000/metrics/categories?days=7

# Customer patterns (repeat sessions)
curl http://localhost:9000/metrics/customer-patterns?days=30
```

### Charts (Plotly JSON)

```bash
# Category distribution bar chart
curl http://localhost:9000/charts/category-distribution?days=7

# Resolution rate trend line chart
curl http://localhost:9000/charts/resolution-trend?days=30

# Eval decision pie chart
curl http://localhost:9000/charts/eval-decision-breakdown?days=7
```

### Natural Language Query

```bash
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many chat sessions were handled automatically last week?"}'

curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the resolution rate for retention categories?"}'

curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me customers with more than 5 sessions in the last month"}'
```

## Key Metrics

### AI Performance
- **Resolution Rate** — % sessions auto-sent (target: >70%)
- **Escalation Rate** — % sessions escalated (target: <15%)
- **Draft Rate** — % sessions drafted for review (target: 10-20%)
- **Average Response Time** — ms to first AI response (target: <5000 ms)

### Category Analytics
- **Category Distribution** — message count by category
- **Category Performance** — resolution rate per category
- **Outstanding Detection** — % flagged as outstanding

### Customer Insights
- **Repeat Issues** — customers with multiple sessions
- **Session Length** — avg messages per session
- **Multi-turn Conversations** — sessions with >1 turn

## Knowledge Base

The analytics agent uses RAG (Retrieval-Augmented Generation) to generate accurate SQL queries:

### Table Schemas (`knowledge/schemas/`)
- `chat_sessions.json` — Session metadata with eval decisions
- `chat_messages.json` — Individual messages (customer + agent)
- `agent_traces.json` — Agent execution traces from Langfuse

### Sample Queries (`knowledge/queries/`)
- `resolution_rate.sql` — AI resolution rate calculation
- `category_breakdown.sql` — Category distribution with metrics
- `customer_patterns.sql` — Customers with repeat sessions

### Business Rules (`knowledge/rules/`)
- `metrics.json` — Metric definitions, formulas, targets, thresholds

## Development

### Local Testing (without Docker)

```bash
cd services/analytics

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANALYTICS_DB_URL="postgresql://analytics_readonly:analytics_pass@localhost:54322/postgres"
export OPENAI_API_KEY="sk-..."
export LANGFUSE_PUBLIC_KEY="pk-analytics-local"
export LANGFUSE_SECRET_KEY="sk-analytics-local"
export LANGFUSE_HOST="http://localhost:3100"

# Load knowledge base
python load_knowledge.py

# Run service
python main.py
```

### Adding New Metrics

1. Add SQL query to `knowledge/queries/new_metric.sql`
2. Add business rules to `knowledge/rules/metrics.json`
3. Create endpoint in `api/metrics.py` or `api/charts.py`
4. Reload knowledge base: `docker compose exec analytics python load_knowledge.py`

## Troubleshooting

### "Connection refused" to PostgreSQL
```bash
# Verify database is running
docker compose ps supabase-db

# Check read-only user exists
docker compose exec supabase-db psql -U postgres -c "\du analytics_readonly"
```

### Knowledge base not loading
```bash
# Verify PgVector extension
docker compose exec supabase-db psql -U postgres -c "\dx"

# Recreate knowledge table
docker compose exec analytics python -c "
from agno.vectordb.pgvector import PgVector
from config import settings
kb = PgVector(table_name='analytics_knowledge', db_url=settings.analytics_db_url)
kb.drop()
kb.create()
"
```

### Langfuse traces not appearing
1. Verify Langfuse project created: `http://localhost:3100`
2. Check API keys in `.env`: `LANGFUSE_ANALYTICS_PUBLIC_KEY`, `LANGFUSE_ANALYTICS_SECRET_KEY`
3. Switch project in Langfuse UI: dropdown → "Analytics Agent"

## Architecture Decisions

### Why AgentOS?
- **Self-hosted Control Plane** — no dependency on os.agno.com
- **Built-in UI** — chat interface for exploratory analytics
- **PostgresTools** — natural language → SQL without manual prompt engineering
- **PgVector Knowledge** — RAG for accurate query generation

### Why Separate Langfuse Project?
- **Isolation** — analytics traces don't mix with support AI traces
- **Clarity** — dedicated dashboard for SQL query performance
- **RBAC** — separate permissions if needed in future

### Why Custom FastAPI Endpoints?
- **Performance** — pre-computed metrics without LLM latency
- **Caching** — can add Redis caching for frequent queries
- **Plotly** — JSON charts for frontend integration

## License

Internal tool for Lev Haolam. Not for public distribution.
