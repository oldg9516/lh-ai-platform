"""Automate Chatwoot Agent Bot setup via API.

Usage: python services/chatwoot/setup_bot.py

Requires CHATWOOT_API_TOKEN in .env (generated after first login).
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

CHATWOOT_URL = os.getenv("CHATWOOT_FRONTEND_URL", "http://localhost:3010")
API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "")
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "1")

if not API_TOKEN:
    print("Error: CHATWOOT_API_TOKEN not set in .env")
    print("1. Login to Chatwoot at", CHATWOOT_URL)
    print("2. Go to Profile → Access Token → Create")
    print("3. Add to .env: CHATWOOT_API_TOKEN=your_token")
    sys.exit(1)

headers = {
    "api_access_token": API_TOKEN,
    "Content-Type": "application/json",
}

bot_payload = {
    "name": "AI Support Bot",
    "description": "Lev Haolam AI-powered customer support agent",
    "outgoing_url": "http://ai-engine:8000/api/webhook/chatwoot",
}

print(f"Creating Agent Bot on {CHATWOOT_URL}...")
resp = httpx.post(
    f"{CHATWOOT_URL}/api/v1/accounts/{ACCOUNT_ID}/agent_bots",
    json=bot_payload,
    headers=headers,
    timeout=10.0,
)

if resp.status_code in (200, 201):
    data = resp.json()
    print(f"Agent Bot created successfully!")
    print(f"  ID: {data.get('id')}")
    print(f"  Name: {data.get('name')}")
    print(f"  Webhook: {data.get('outgoing_url')}")
    print()
    print("Next step: Go to Settings → Inboxes → your inbox → Configuration")
    print("           Select 'AI Support Bot' under Agent Bot and save.")
else:
    print(f"Error: {resp.status_code}")
    print(resp.text)
