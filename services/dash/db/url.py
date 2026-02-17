"""Build database connection URL from environment variables.

This URL points to Dash's own PgVector database (NOT Supabase).
Used for: agent state, knowledge vectors, learnings vectors.
"""

from os import getenv
from urllib.parse import quote


def build_db_url() -> str:
    """Build database URL from environment variables."""
    driver = getenv("DB_DRIVER", "postgresql+psycopg")
    user = getenv("DB_USER", "dash")
    password = quote(getenv("DB_PASS", "dash"), safe="")
    host = getenv("DB_HOST", "localhost")
    port = getenv("DB_PORT", "5432")
    database = getenv("DB_DATABASE", "dash")

    return f"{driver}://{user}:{password}@{host}:{port}/{database}"


db_url = build_db_url()
