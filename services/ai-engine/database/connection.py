"""Supabase client singleton.

Provides a shared Supabase client instance for REST API access.
Uses service_role_key to bypass RLS (server-side only).
"""

import structlog
from supabase import create_client, Client

from config import settings

logger = structlog.get_logger()

_client: Client | None = None


def get_client() -> Client:
    """Get or create the Supabase client singleton.

    Returns:
        Supabase Client instance.

    Raises:
        RuntimeError: If SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set.
    """
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set."
            )
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("supabase_client_initialized", url=settings.supabase_url)
    return _client
