"""PostgreSQL connection pool via psycopg2.

Sync connection pool for Supabase PostgreSQL.
Uses ThreadedConnectionPool for thread-safe access.
"""

from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
import structlog

from config import settings

logger = structlog.get_logger()

_pool: pool.ThreadedConnectionPool | None = None


def init_pool() -> None:
    """Initialize the database connection pool."""
    global _pool
    _pool = pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_pass,
        sslmode="require",
        connect_timeout=10,
    )
    logger.info("database_pool_initialized", host=settings.db_host)


def close_pool() -> None:
    """Close all connections in the pool."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("database_pool_closed")


@contextmanager
def get_connection() -> Generator:
    """Get a connection from the pool.

    Yields:
        psycopg2 connection object. Auto-commits on success, rolls back on error.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")

    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
