"""Dash AgentOS — Analytics Data Agent for Lev Haolam.

Replaces the previous analytics service on port 9000.
"""

from os import getenv
import time

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


def _wait_for_db(max_retries: int = 30, delay: float = 2.0) -> None:
    """Wait for dash-db to be reachable before importing agent modules."""
    from db.url import db_url
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url, pool_pre_ping=True)
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("dash-db is ready", attempt=attempt)
            engine.dispose()
            return
        except Exception as exc:
            logger.warning(
                "dash-db not ready, retrying",
                attempt=attempt,
                max_retries=max_retries,
                error=str(exc),
            )
            time.sleep(delay)
    engine.dispose()
    raise RuntimeError(f"dash-db not reachable after {max_retries} attempts")


# Module-level app: deferred until after DB wait at startup
app = None  # type: ignore[assignment]


def _create_app():
    """Create the AgentOS FastAPI app (call after DB is ready)."""
    from agno.os import AgentOS

    from dash.agent import dash
    from db import get_postgres_db

    agent_os = AgentOS(
        name="Dash Analytics",
        agents=[dash],
        tracing=True,
        db=get_postgres_db(),
    )
    return agent_os


if __name__ == "__main__":
    _wait_for_db()
    agent_os = _create_app()
    app = agent_os.get_app()
    logger.info("Starting Dash Analytics Agent", port=9000)
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
    )
