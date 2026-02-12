"""Lev Haolam AI Support Engine — Entry Point.

FastAPI application with lifespan management for database pool.
Includes API routes on /api prefix.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from config import settings
from database.connection import init_pool, close_pool

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("starting_ai_engine", version=settings.app_version)
    try:
        init_pool()
    except Exception as e:
        logger.error("database_pool_init_failed", error=str(e))
    yield
    close_pool()
    logger.info("stopped_ai_engine")


app = FastAPI(
    title="Lev Haolam AI Support Engine",
    version=settings.app_version,
    lifespan=lifespan,
)

# Include API routes
from api.routes import router as api_router  # noqa: E402

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
