"""Lev Haolam AI Support Engine — Entry Point.

FastAPI application with lifespan management.
Includes Langfuse tracing via AgnoInstrumentor + OpenTelemetry.
"""

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from config import settings

# --- Logging ---

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

# --- Langfuse Tracing via OpenTelemetry ---

os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

try:
    from openinference.instrumentation.agno import AgnoInstrumentor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry import trace as trace_api
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    endpoint = f"{settings.langfuse_host}/api/public/otel/v1/traces"
    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    )
    trace_api.set_tracer_provider(tracer_provider)
    AgnoInstrumentor().instrument()
    logger.info("langfuse_tracing_enabled", endpoint=endpoint)
except Exception as e:
    logger.warning("langfuse_tracing_disabled", error=str(e))


# --- FastAPI App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("starting_ai_engine", version=settings.app_version)
    yield
    # Flush remaining traces
    try:
        provider = trace_api.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()
    except Exception:
        pass
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
