"""
Simple fixed-window rate limiter.

Uses Redis when REDIS_URL is configured so limits are shared across
worker processes in production. Falls back to a per-process
in-memory counter when Redis isn't available (or the connection
fails), so local development never breaks because Redis isn't
running — see spec: "must not become a single point of failure
during local development."
"""

import time
from collections import defaultdict
from typing import Optional

from fastapi import Request

from app.core.config import settings
from app.core.errors import RateLimitError

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore

_redis_client: Optional["Redis"] = None
_redis_unavailable = False

# In-memory fallback: { key: (window_start_epoch, count) }
_memory_store: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))


async def _get_redis() -> Optional["Redis"]:
    global _redis_client, _redis_unavailable
    if _redis_unavailable or not settings.REDIS_URL or Redis is None:
        return None
    if _redis_client is None:
        try:
            _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception:
            _redis_unavailable = True
            _redis_client = None
            return None
    return _redis_client


async def _check_redis(client: "Redis", key: str, limit: int, window_seconds: int) -> bool:
    pipe = client.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, window_seconds, nx=True)
    count, _ = await pipe.execute()
    return count <= limit


def _check_memory(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    window_start, count = _memory_store[key]
    if now - window_start >= window_seconds:
        _memory_store[key] = (now, 1)
        return True
    count += 1
    _memory_store[key] = (window_start, count)
    return count <= limit


def _client_identity(request: Request) -> str:
    # Prefer the authenticated user (set by dependencies.py) so limits
    # follow the person, not just their IP (shared NAT, cellular, etc.).
    user = getattr(request.state, "current_user", None)
    if user is not None:
        return f"user:{user.id}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def rate_limit(limit: int, window_seconds: int, scope: str):
    """
    FastAPI dependency factory. Usage:

        @router.post("/orders", dependencies=[Depends(rate_limit(10, 60, "create_order"))])
    """

    async def dependency(request: Request) -> None:
        identity = _client_identity(request)
        key = f"ratelimit:{scope}:{identity}"

        redis_client = await _get_redis()
        if redis_client is not None:
            try:
                allowed = await _check_redis(redis_client, key, limit, window_seconds)
            except Exception:
                allowed = _check_memory(key, limit, window_seconds)
        else:
            allowed = _check_memory(key, limit, window_seconds)

        if not allowed:
            raise RateLimitError(
                f"Too many requests. Please try again in a moment.",
            )

    return dependency
