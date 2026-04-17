"""
Cost guard — monthly per-user budget in Redis (falls back to in-memory).

Blocks requests when a user exceeds their monthly LLM spend. Uses token-based
cost estimation with GPT-4o-mini pricing; tune the constants to match the
actual model in `settings.llm_model`.
"""
import time
from datetime import datetime

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


PRICE_PER_1K_INPUT = 0.00015
PRICE_PER_1K_OUTPUT = 0.0006

_memory_cost: dict[str, float] = {}


def _month_key(user_id: str) -> str:
    return f"budget:{user_id}:{datetime.now().strftime('%Y-%m')}"


def _current_spend(user_id: str) -> float:
    key = _month_key(user_id)
    if USE_REDIS:
        return float(_redis.get(key) or 0)
    return _memory_cost.get(key, 0.0)


def check_budget(user_id: str) -> dict:
    """
    Raise 402 Payment Required when the user has already exceeded their
    monthly budget. Returns current usage when allowed.
    """
    spent = _current_spend(user_id)
    budget = settings.monthly_budget_usd

    if spent >= budget:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(spent, 4),
                "budget_usd": budget,
                "resets_at": "1st of next month UTC",
            },
        )
    return {
        "used_usd": round(spent, 4),
        "budget_usd": budget,
        "remaining_usd": round(budget - spent, 4),
    }


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """Record LLM cost for the user and return updated monthly spend."""
    cost = (
        input_tokens / 1000 * PRICE_PER_1K_INPUT
        + output_tokens / 1000 * PRICE_PER_1K_OUTPUT
    )
    key = _month_key(user_id)
    if USE_REDIS:
        new_total = float(_redis.incrbyfloat(key, cost))
        # Keep the counter alive for ~32 days so the monthly reset works
        _redis.expire(key, 32 * 24 * 3600)
    else:
        new_total = _memory_cost.get(key, 0.0) + cost
        _memory_cost[key] = new_total
    return new_total
