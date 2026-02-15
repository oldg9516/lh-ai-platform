"""Analytics Service main entry point.

Combines AgentOS (analytics agent + Control Plane) with custom FastAPI routes
for pre-computed metrics and Plotly visualizations.
"""

import structlog
from fastapi import FastAPI
from agno.os import AgentOS

from config import settings
from agent import analytics_agent

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Create custom FastAPI app
app = FastAPI(
    title="Lev Haolam Analytics",
    version="1.0.0",
    description="Analytics service for AI support platform monitoring",
)


# Health check endpoint
@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "analytics"}


# Import custom routers
from api import metrics, charts, query, learning

app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(charts.router, prefix="/charts", tags=["charts"])
app.include_router(query.router, tags=["query"])
app.include_router(learning.router, prefix="/learning", tags=["learning"])

# Initialize AgentOS with analytics agent and custom app
agent_os = AgentOS(
    name="Lev Haolam Analytics OS",
    agents=[analytics_agent],
    base_app=app,  # Pass custom FastAPI app to combine routes
)

# Get the combined app with both AgentOS and custom routes
app = agent_os.get_app()

if __name__ == "__main__":
    logger.info("Starting Analytics Service", port=9000)
    agent_os.serve(app="main:app", host="0.0.0.0", port=9000, reload=settings.debug)
