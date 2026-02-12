"""Retention tools — cancel link generation.

Generates AES-256-GCM encrypted cancel links matching n8n production format.
URL: https://levhaolam.com/pay/subscriptions/cancel?al={token}
"""

import base64
import json
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import settings

import structlog

logger = structlog.get_logger()

CANCEL_BASE_URL = "https://levhaolam.com/pay/subscriptions/cancel"


def generate_cancel_link(
    subscription_id: str,
    customer_email: str,
) -> str | None:
    """Generate an encrypted cancel link for a subscription.

    Args:
        subscription_id: The subscription ID to encode.
        customer_email: Customer email for verification.

    Returns:
        Full cancel URL with encrypted token, or None if encryption fails.
    """
    password = settings.cancel_link_password
    if not password:
        logger.error("cancel_link_password_not_set")
        return None

    try:
        # Payload matches n8n format
        payload = json.dumps({
            "subscription_id": subscription_id,
            "email": customer_email,
        })

        # Derive 256-bit key from password (SHA-256)
        import hashlib

        key = hashlib.sha256(password.encode()).digest()

        # Encrypt with AES-256-GCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, payload.encode(), None)

        # Combine nonce + ciphertext and base64url-encode
        token = base64.urlsafe_b64encode(nonce + ciphertext).decode()

        url = f"{CANCEL_BASE_URL}?al={token}"
        logger.info(
            "cancel_link_generated",
            subscription_id=subscription_id,
        )
        return url

    except Exception as e:
        logger.error("cancel_link_generation_failed", error=str(e))
        return None


def inject_cancel_link(response: str, cancel_url: str) -> str:
    """Replace cancel link placeholders in AI response with the actual URL.

    Looks for patterns like [CANCEL_LINK], {cancel_link}, or
    generic 'cancellation page' mentions and injects the URL.

    Args:
        response: AI-generated response text.
        cancel_url: The encrypted cancel URL.

    Returns:
        Response with cancel link injected.
    """
    # Replace explicit placeholders
    result = response.replace("[CANCEL_LINK]", cancel_url)
    result = result.replace("{cancel_link}", cancel_url)
    result = result.replace("{{cancel_link}}", cancel_url)

    # If no placeholder was found, check for generic references
    if cancel_url not in result:
        # Replace "cancellation page" / "cancel page" mentions with linked version
        pattern = r'(cancellation page|cancel page|cancellation link|cancel link)'
        replacement = f'<a href="{cancel_url}">cancellation page</a>'
        result = re.sub(pattern, replacement, result, count=1, flags=re.IGNORECASE)

    return result
