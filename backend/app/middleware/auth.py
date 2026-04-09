"""Authentication dependencies for agent API keys and webhook secrets."""

import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.connection import get_async_session
from app.models.agent import Agent

API_KEY_PREFIX = "pp_"
API_KEY_HEX_LENGTH = 64  # secrets.token_hex(32) → 64 hex chars

bearer_scheme = HTTPBearer()


def generate_api_key() -> str:
    """Generate a new agent API key: pp_ prefix + 64 hex chars."""
    return f"{API_KEY_PREFIX}{secrets.token_hex(32)}"


def hash_api_key(api_key: str) -> str:
    """SHA-256 hash of the full API key string."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> Agent:
    """Dependency: resolve Bearer token to an Agent or raise 401."""
    token = credentials.credentials
    if not token.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    key_hash = hash_api_key(token)
    result = await session.execute(select(Agent).where(Agent.api_key_hash == key_hash))
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return agent


async def verify_webhook_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> None:
    """Dependency: verify the webhook shared secret or raise 401."""
    if not credentials.credentials or not secrets.compare_digest(credentials.credentials, settings.WEBHOOK_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook key",
        )
