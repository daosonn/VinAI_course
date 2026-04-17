"""
Production AI Agent — Day 12 final lab.

Combines everything we built through the week:
  ✅ Config from environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication (app/auth.py)
  ✅ Rate limiting, Redis-backed (app/rate_limiter.py)
  ✅ Cost guard, Redis-backed (app/cost_guard.py)
  ✅ Input validation (Pydantic)
  ✅ Health check + readiness probe
  ✅ Graceful SIGTERM shutdown
  ✅ Security headers + CORS
"""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_usage
from app.rate_limiter import check_rate_limit
from utils.mock_llm import ask as llm_ask


# ──────────────────────────────────────────────────────────
# Logging — JSON structured
# ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0


# ──────────────────────────────────────────────────────────
# Lifespan — startup/shutdown hooks
# ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    time.sleep(0.1)  # simulate warm-up (model/cache init)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))


# ──────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers.pop("server", None)
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception:
        _error_count += 1
        raise


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    user_id: str
    timestamp: str
    usage: dict


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent.

    **Authentication:** header `X-API-Key: <your-key>`.
    Rate limit and monthly budget are enforced per `user_id`.
    """
    check_rate_limit(body.user_id)
    check_budget(body.user_id)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    answer = llm_ask(body.question)

    input_tokens = len(body.question.split()) * 2
    output_tokens = len(answer.split()) * 2
    total_spent = record_usage(body.user_id, input_tokens, output_tokens)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        user_id=body.user_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        usage={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "monthly_spend_usd": round(total_spent, 6),
            "monthly_budget_usd": settings.monthly_budget_usd,
        },
    )


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts the container if this fails."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {"llm": "mock" if not settings.openai_api_key else "openai"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "monthly_budget_usd": settings.monthly_budget_usd,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }


# ──────────────────────────────────────────────────────────
# Graceful Shutdown
# ──────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
