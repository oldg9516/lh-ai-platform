"""Natural language query endpoint.

Allows users to ask analytics questions in plain language.
The analytics agent converts questions to SQL and returns results.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from agent import analytics_agent

router = APIRouter()


class QueryRequest(BaseModel):
    """Natural language query request."""

    question: str


class QueryResponse(BaseModel):
    """Natural language query response."""

    question: str
    answer: str
    sql_query: str | None = None


@router.post("/query", response_model=QueryResponse)
async def natural_language_query(req: QueryRequest):
    """Natural language interface to analytics agent.

    The agent uses PostgresTools to:
    1. Search knowledge base for table schemas and sample queries
    2. Generate SQL query based on the question
    3. Execute the query on read-only database
    4. Return results in natural language

    Example questions:
    - "How many chat sessions were handled automatically last week?"
    - "What's the most popular category?"
    - "Show me customers with multiple escalations"
    - "What's the resolution rate trend for the last month?"
    - "Which category has the highest escalation rate?"

    Returns:
        QueryResponse with:
            - question: Original question
            - answer: Natural language answer with data
            - sql_query: Generated SQL (if extractable from response)
    """
    # Run agent (uses PostgresTools to generate and execute SQL)
    response = await analytics_agent.arun(req.question)

    # Try to extract SQL query from response
    # PostgresTools often includes the SQL in markdown code blocks
    sql_query = None
    if "```sql" in response.content:
        try:
            sql_start = response.content.find("```sql") + 6
            sql_end = response.content.find("```", sql_start)
            sql_query = response.content[sql_start:sql_end].strip()
        except Exception:
            pass  # Could not extract SQL, not critical

    return QueryResponse(
        question=req.question,
        answer=response.content,
        sql_query=sql_query,
    )
