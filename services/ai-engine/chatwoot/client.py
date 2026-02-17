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


async def assign_conversation(
    conversation_id: int,
    assignee_id: int,
) -> dict:
    """Assign a conversation to a specific agent.

    Args:
        conversation_id: Chatwoot conversation ID.
        assignee_id: Chatwoot agent user ID to assign to.

    Returns:
        Updated conversation dict.
    """
    client = _get_client()
    url = f"{_account_prefix()}/conversations/{conversation_id}"
    payload = {"assignee_id": assignee_id}
    response = await client.patch(url, json=payload)
    response.raise_for_status()
    logger.info(
        "chatwoot_conversation_assigned",
        conversation_id=conversation_id,
        assignee_id=assignee_id,
    )
    return response.json()


# --- Contact & Conversation Management (CopilotKit sync) ---


async def search_contact(email: str) -> dict | None:
    """Search for an existing contact by email.

    Args:
        email: Customer email address.

    Returns:
        Contact dict if found, None otherwise.
    """
    client = _get_client()
    url = f"{_account_prefix()}/contacts/search"
    response = await client.get(url, params={"q": email})
    response.raise_for_status()
    data = response.json()
    payload = data.get("payload", [])
    for contact in payload:
        if contact.get("email", "").lower() == email.lower():
            return contact
    return None


async def create_contact(email: str, name: str | None = None) -> dict:
    """Create a new contact in Chatwoot.

    Args:
        email: Customer email address.
        name: Customer name (optional).

    Returns:
        Created contact dict.
    """
    client = _get_client()
    url = f"{_account_prefix()}/contacts"
    payload: dict = {"email": email}
    if name:
        payload["name"] = name
    response = await client.post(url, json=payload)
    response.raise_for_status()
    result = response.json()
    contact = result.get("payload", {}).get("contact", result)
    logger.info("chatwoot_contact_created", email=email, contact_id=contact.get("id"))
    return contact


async def find_or_create_contact(email: str, name: str | None = None) -> dict:
    """Find existing contact or create a new one.

    Args:
        email: Customer email address.
        name: Customer name (optional, used for creation).

    Returns:
        Contact dict with at least 'id' field.
    """
    contact = await search_contact(email)
    if contact:
        return contact
    return await create_contact(email, name)


async def create_conversation(
    contact_id: int,
    inbox_id: int,
    source_id: str | None = None,
) -> dict:
    """Create a new conversation for a contact.

    Args:
        contact_id: Chatwoot contact ID.
        inbox_id: Chatwoot inbox ID.
        source_id: Optional external ID for tracking (e.g. CopilotKit thread_id).

    Returns:
        Created conversation dict with 'id' field.
    """
    client = _get_client()
    url = f"{_account_prefix()}/conversations"
    payload: dict = {
        "contact_id": contact_id,
        "inbox_id": inbox_id,
    }
    if source_id:
        payload["additional_attributes"] = {"copilot_thread_id": source_id}
    response = await client.post(url, json=payload)
    response.raise_for_status()
    result = response.json()
    logger.info(
        "chatwoot_conversation_created",
        contact_id=contact_id,
        conversation_id=result.get("id"),
    )
    return result
