import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import Depends, Header, HTTPException, status

from app.core.dependencies import get_db_cursor
from app.repositories.api_key_repository import ApiKeyRepository
from app.services.api_key_service import ApiKeyService

RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass
class ApiKeyContext:
    """Authenticated context resolved from an ingestion API key."""
    tenant_id: int
    api_key_id: int


class SlidingWindowRateLimiter:
    """Sliding-window in-memory rate limiter per API key identifier."""

    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[int, deque] = defaultdict(deque)

    def is_allowed(self, key_id: int) -> bool:
        """Check if request is permitted under rate limit window."""
        now = time.time()
        timestamps = self._history[key_id]

        while timestamps and timestamps[0] <= now - self.window_seconds:
            timestamps.popleft()

        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        return True

    def reset(self) -> None:
        """Clear rate limit history (useful for testing)."""
        self._history.clear()


rate_limiter = SlidingWindowRateLimiter()


def get_api_key_context(
    x_helios_api_key: Optional[str] = Header(None, alias="X-Helios-Api-Key"),
    cursor: Cursor = Depends(get_db_cursor),
) -> ApiKeyContext:
    """
    Authenticate programmatic requests to ingestion endpoints via X-Helios-Api-Key header.
    
    Verifies key hash, checks tenant rate limits, and updates last_used_at.
    """
    if not x_helios_api_key or not x_helios_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing. Provide your organization key in the 'X-Helios-Api-Key' request header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = ApiKeyService.hash_api_key(x_helios_api_key)
    repo = ApiKeyRepository(cursor)
    record = repo.get_by_hash(key_hash)

    if not record or not record.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    api_key_id = int(record["api_key_id"])
    tenant_id = int(record["tenant_id"])

    if not rate_limiter.is_allowed(api_key_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {rate_limiter.max_requests} requests per minute allowed.",
            headers={"Retry-After": "60"},
        )

    try:
        repo.update_last_used(api_key_id)
    except Exception:
        pass

    return ApiKeyContext(tenant_id=tenant_id, api_key_id=api_key_id)


def get_api_key_tenant_id(
    ctx: ApiKeyContext = Depends(get_api_key_context),
) -> int:
    """Convenience dependency returning just the tenant_id from API key context."""
    return ctx.tenant_id
