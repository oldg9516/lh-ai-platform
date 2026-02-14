"""Analytics agent with PostgresTools for natural language → SQL queries."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.postgres import PostgresTools
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

from config import settings

# PostgresTools for direct SQL execution
# Parse db_url components for PostgresTools (it doesn't accept db_url in current SDK version)
postgres_tools = PostgresTools(
    host=settings.db_host,
    port=settings.db_port,
    db_name=settings.db_name,
    user=settings.db_user,
    password=settings.db_password,
)

# Knowledge Base with table schemas + sample queries + business rules
# Using Pinecone instead of PgVector (pgvector extension not installed in Supabase)
vector_db = PineconeDb(
    name=settings.pinecone_index,
    dimension=1536,
    metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
    api_key=settings.pinecone_api_key,
    namespace="analytics-knowledge",  # Separate namespace for analytics KB
    use_hybrid_search=True,
)
knowledge = Knowledge(vector_db=vector_db)

analytics_agent = Agent(
    name="analytics_agent",
    model=OpenAIChat(id="gpt-5-mini"),  # Cheap model for SQL generation
    tools=[postgres_tools],
    knowledge=knowledge,
    search_knowledge=True,  # Always search KB before generating SQL
    instructions=[
        "You are an analytics assistant for Lev Haolam AI support platform.",
        "Your role is to help analyze chat sessions, agent performance, and customer patterns.",
        "",
        "## Guidelines:",
        "1. Always search your knowledge base FIRST for table schemas and sample queries",
        "2. Generate SQL queries to answer questions about platform metrics",
        "3. Use read-only access — SELECT queries only, no INSERT/UPDATE/DELETE",
        "4. Explain query results in plain language with numbers and percentages",
        "5. If asked for trends, use DATE_TRUNC for time-based aggregations",
        "6. For performance metrics, filter by created_at to limit time range",
        "",
        "## Available Tables:",
        "- chat_sessions: Session metadata with eval decisions and metrics",
        "- chat_messages: Individual messages (customer + agent)",
        "- agent_traces: LangSmith traces for agent executions",
        "- tool_executions: Tool calls and results",
        "- eval_results: Eval gate decisions and reasoning",
        "- customers: Customer profiles",
        "- subscriptions: Active subscriptions",
        "- orders: Order history",
        "",
        "## Common Queries:",
        "- Resolution rate: % of sessions with eval_decision='send'",
        "- Escalation rate: % of sessions with eval_decision='escalate'",
        "- Category distribution: GROUP BY primary_category",
        "- Response time: AVG(first_response_time_ms)",
    ],
    markdown=True,
)
