---
name: context7
description: Fetch up-to-date documentation and code examples for any library or framework. Use when needing API references, code examples, library documentation, or framework guides. Optimized for Lev Haolam AI Platform stack: Agno AgentOS, Chatwoot, Pinecone, FastAPI, Pydantic, Supabase.
---

# Context7

Base directory for this skill: /home/hazeruno/.config/opencode/skills/context7

Retrieve up-to-date documentation and code examples for any library via the Context7 MCP service.

## Quick Start

Run the CLI script with bun (use absolute path):

```bash
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts <command> [options]
```

## Available Commands

### resolve-library-id

Resolve a package/product name to a Context7-compatible library ID.

```bash
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts resolve-library-id --library-name "agno"
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts resolve-library-id --library-name "chatwoot"
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts resolve-library-id --library-name "pinecone"
```

**Required before `get-library-docs`** unless you already know the library ID in `/org/project` format.

Selection criteria: name similarity → description relevance → snippet count → reputation → benchmark score (max 100).

### get-library-docs

Fetch documentation for a library. Requires a Context7-compatible library ID from `resolve-library-id` or known `/org/project` format.

```bash
# Basic usage — Agno docs
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts get-library-docs \
  --context7-compatible-library-i-d "/agno-agi/agno-docs"

# With topic focus — HITL patterns
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts get-library-docs \
  --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "tools HITL requires_confirmation"

# Info mode — conceptual/architectural guides
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts get-library-docs \
  --context7-compatible-library-i-d "/agno-agi/agno-docs" --mode "info" --topic "AgentOS architecture"

# Pagination — if first page not enough
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts get-library-docs \
  --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "guardrails" --page 2

# Raw JSON mode — bypass flag parsing
bun /home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts get-library-docs \
  --raw '{"context7CompatibleLibraryID": "/agno-agi/agno-docs", "topic": "PineconeDb", "mode": "code"}'
```

**Parameters:**

- `--context7-compatible-library-i-d` (required): Library ID (e.g., `/agno-agi/agno-docs`, `/supabase/supabase`)
- `--mode`: `code` (default) for API references & code examples, `info` for conceptual guides & architecture
- `--topic`: Focus on specific topic (e.g., `hooks`, `routing`, `authentication`)
- `--page`: Pagination 1-10 (default: 1). If context insufficient, try page=2, 3, etc. with same topic
- `--raw <json>`: Pass raw JSON args directly, bypassing flag parsing

## Global Options

- `-t, --timeout <ms>`: Call timeout (default: 30000)
- `-o, --output <format>`: Output format: `text` | `markdown` | `json` | `raw`

---

## Project Library IDs (Lev Haolam AI Platform)

### Core Stack — Verified on Context7

| Library           | Context7 ID                 | Notes                                                                                                          |
| ----------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Agno (docs)**   | `/agno-agi/agno-docs`       | 951K tokens, 5,747 snippets, score 91.1/100. **PRIMARY** — agents, tools, knowledge, guardrails, HITL, AgentOS |
| **Agno (source)** | `/agno-agi/agno`            | Source code examples from GitHub repo                                                                          |
| **Supabase**      | `/supabase/supabase`        | Database, auth, storage, realtime                                                                              |
| **OpenAI API**    | `/websites/platform_openai` | GPT-5.x, function calling, structured outputs                                                                  |
| **Pydantic**      | `/pydantic/pydantic`        | BaseModel, validation, serialization                                                                           |
| **Pydantic AI**   | `/pydantic/pydantic-ai`     | Agent framework reference (concepts overlap with Agno)                                                         |

### Resolve at Runtime — Use `resolve-library-id` first

| Library            | Search name      | Likely ID                              |
| ------------------ | ---------------- | -------------------------------------- |
| **FastAPI**        | `fastapi`        | `/fastapi/fastapi`                     |
| **Pinecone**       | `pinecone`       | `/pinecone-io/pinecone-python-client`  |
| **Chatwoot**       | `chatwoot`       | May not be indexed — use fallback docs |
| **Docker Compose** | `docker compose` | `/docker/compose`                      |
| **psycopg**        | `psycopg`        | `/psycopg/psycopg`                     |

### Fallback Documentation (not on Context7 or insufficient)

For libraries not well covered by Context7, use these direct documentation URLs:

| Library                  | Documentation URL                                   | Format                                                |
| ------------------------ | --------------------------------------------------- | ----------------------------------------------------- |
| **Agno (LLM-optimized)** | https://docs.agno.com/llms-full.txt                 | Full docs as single text file — ideal for LLM context |
| **Agno Docs**            | https://docs.agno.com/                              | Official web docs                                     |
| **Agno GitHub Docs**     | https://github.com/agno-agi/agno-docs               | Markdown source of all docs                           |
| **Agno Cookbook**        | https://github.com/agno-agi/agno/tree/main/cookbook | Working code examples                                 |
| **Agno MCP Server**      | https://docs.agno.com/mcp                           | Agno's own MCP endpoint for live docs                 |
| **Chatwoot API**         | https://www.chatwoot.com/developers/api/            | REST API reference                                    |
| **Chatwoot GitHub**      | https://github.com/chatwoot/chatwoot                | Source + docs                                         |
| **Pinecone Python**      | https://docs.pinecone.io/reference/python-sdk       | Python SDK reference                                  |
| **Agenta (Eval Lab)**    | https://docs.agenta.ai/                             | Evaluation platform docs                              |

---

## Common Queries for This Project

### Agno AgentOS

```bash
# Agent creation with tools and knowledge
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "Agent tools knowledge" --mode "code"

# HITL (Human-in-the-Loop) patterns
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "HITL confirmation requires_confirmation"

# Guardrails
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "guardrails safety"

# AgentOS deployment and FastAPI app
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "AgentOS get_app serve"

# Structured output with Pydantic
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "output_schema structured output pydantic"

# Teams and multi-agent
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "Team multi-agent members"

# Pinecone vector DB integration
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "PineconeDb knowledge vector"

# Session storage with PostgreSQL
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "PostgresDb session storage"

# Learning agents
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "learning memory user_profiles"

# MCP tools integration
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/agno-agi/agno-docs" --topic "MCPTools MCP server"
```

### Supabase (Database)

```bash
# PostgreSQL queries and connection
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/supabase/supabase" --topic "database query postgres"

# Row Level Security
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/supabase/supabase" --topic "RLS row level security"

# Realtime subscriptions
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/supabase/supabase" --topic "realtime subscribe"
```

### OpenAI API

```bash
# GPT-5.x structured outputs
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/websites/platform_openai" --topic "structured outputs function calling"

# Reasoning effort control
bun .../context7.ts get-library-docs --context7-compatible-library-i-d "/websites/platform_openai" --topic "reasoning effort"
```

---

## Workflow: Agno Development with Context7

When working on the Lev Haolam AI Platform, use this priority order:

1. **Agno-specific code** → `/agno-agi/agno-docs` (Context7) — agents, tools, knowledge, HITL, guardrails
2. **Agno latest API changes** → https://docs.agno.com/llms-full.txt (direct fetch if Context7 result seems outdated)
3. **Database/Supabase** → `/supabase/supabase` (Context7)
4. **OpenAI API** → `/websites/platform_openai` (Context7)
5. **Chatwoot integration** → https://www.chatwoot.com/developers/api/ (direct — not indexed on Context7)
6. **Pinecone** → Try `resolve-library-id` first, fallback to https://docs.pinecone.io/reference/python-sdk

### Pro Tips

- **Always use `/agno-agi/agno-docs` over `/agno-agi/agno`** — the docs repo has curated, structured docs (951K tokens); the code repo has raw source
- **Use `--topic` for focused results** — "HITL tools" is better than a general "agent" query
- **Combine Context7 + llms-full.txt** — if Context7 gives partial info, fetch `https://docs.agno.com/llms-full.txt` for comprehensive coverage
- **Agno has its own MCP server** — for live, always-fresh docs you can also use `MCPTools(url="https://docs.agno.com/mcp", transport="streamable-http")`
- **Pinecone v5.4.2** — Agno requires Pinecone SDK v5.4.2, NOT v6.x. Check version-specific docs if available

## Requirements

- [Bun](https://bun.sh) runtime
- `mcporter` package (embedded in script)

## Script Details

The CLI script is at: `/home/hazeruno/.config/opencode/skills/context7/scripts/context7.ts`

- Generated by `mcporter@0.0.0` — a CLI wrapper over the Context7 MCP server
- Connects to `https://mcp.context7.com/mcp` via HTTP transport
- Two tools: `resolve-library-id` and `get-library-docs`
- Default timeout: 30000ms (override with `-t`)
- Output formats: `text` (default), `markdown`, `json`, `raw`
- The `--raw` flag on any command accepts a JSON string and bypasses flag parsing
