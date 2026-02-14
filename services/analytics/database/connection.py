"""PostgreSQL connection helper for direct database access.

Uses psycopg3 for synchronous PostgreSQL queries.
This is separate from Agno's PostgresTools which handles natural language → SQL.
"""

import psycopg
from contextlib import contextmanager

from config import settings


@contextmanager
def get_connection():
    """Get PostgreSQL connection using read-only user.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM chat_sessions LIMIT 10")
                rows = cur.fetchall()

    Yields:
        psycopg.Connection: Database connection
    """
    conn = psycopg.connect(settings.analytics_db_url)
    try:
        yield conn
    finally:
        conn.close()
