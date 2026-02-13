"""Chatwoot API client.

Wraps Chatwoot REST API for sending messages, updating conversations,
adding labels, and managing assignments.
"""

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

_http_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx async client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=f"{settings.chatwoot_url}/api/v1",
            headers={
                "api_access_token": settings.chatwoot_api_token,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _http_client


def _account_prefix() -> str:
    """Return the account-scoped URL prefix."""
    return f"/accounts/{settings.chatwoot_account_id}"


async def send_message(
    conversation_id: int,
    content: str,
    private: bool = False,
) -> dict:
    """Send a message (public or private note) to a Chatwoot conversation.

    Args:
        conversation_id: Chatwoot conversation ID.
        content: Message text content.
        private: If True, sends as a private note (only agents can see).

    Returns:
        Chatwoot message response dict.
    """
    client = _get_client()
    url = f"{_account_prefix()}/conversations/{conversation_id}/messages"
    payload = {
        "content": content,
        "message_type": "outgoing",
        "private": private,
    }
    response = await client.post(url, json=payload)
    response.raise_for_status()
    logger.info(
        "chatwoot_message_sent",
        conversation_id=conversation_id,
        private=private,
        message_id=response.json().get("id"),
    )
    return response.json()


async def toggle_conversation_status(
    conversation_id: int,
    status: str,
) -> dict:
    """Change conversation status (open/pending/resolved/snoozed).

    Args:
        conversation_id: Chatwoot conversation ID.
        status: Target status: 'open', 'pending', 'resolved', 'snoozed'.

    Returns:
        Updated conversation dict.
    """
    client = _get_client()
    url = f"{_account_prefix()}/conversations/{conversation_id}/toggle_status"
    payload = {"status": status}
    response = await client.post(url, json=payload)
    response.raise_for_status()
    logger.info(
        "chatwoot_status_changed",
        conversation_id=conversation_id,
        status=status,
    )
    return response.json()


async def add_labels(
    conversation_id: int,
    labels: list[str],
) -> dict:
    """Add labels to a conversation for categorization and routing.

    Args:
        conversation_id: Chatwoot conversation ID.
        labels: List of label strings to add.

    Returns:
        Updated labels dict.
    """
    client = _get_client()
    url = f"{_account_prefix()}/conversations/{conversation_id}/labels"
    payload = {"labels": labels}
    response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()
