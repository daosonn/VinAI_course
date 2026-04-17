"""
Rate limiter — sliding-window counter.

Stores per-key request timestamps in Redis when REDIS_URL is set (stateless,
safe across multiple replicas). Falls back to in-process memory when Redis
is unavailable so the app still boots in local dev.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings

try:
    import redis

    _redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    if _redis:
        _redis.ping()
    USE_REDIS = _redis is not None
except Exception:
    _redis = None
    USE_REDIS = False


# In-memory fallback (not safe for multi-instance deployments)
_windows: dict[str, deque] = defaultdict(deque)


def check_rate_limit(key: str) -> dict:
    """
    Raise 429 when `key` has exceeded `settings.rate_limit_per_minute` in
    the last 60 seconds. Returns usage info when allowed.
    """
    now = time.time()
    window_seconds = 60
    limit = settings.rate_limit_per_minute

    if USE_REDIS:
        redis_key = f"ratelimit:{key}"
        pipe = _redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds)
        _, _, count, _ = pipe.execute()
        used = int(count)
    else:
        window = _windows[key]
        while window and window[0] < now - window_seconds:
            window.popleft()
        window.append(now)
        used = len(window)

    remaining = max(0, limit - used)
    reset_at = int(now) + window_seconds

    if used > limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window_seconds": window_seconds,
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
                "Retry-After": "60",
            },
        )

    return {"limit": limit, "remaining": remaining, "reset_at": reset_at}
