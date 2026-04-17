"""
Authentication module — API Key + optional JWT.

- verify_api_key: FastAPI dependency to protect endpoints with X-API-Key header.
- create_token / verify_token: helpers for JWT-based stateless auth (optional,
  shown for completeness — the main agent uses API key auth for simplicity).
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyHeader

from app.config import settings


# ──────────────────────────────────────────────────────────
# API Key Authentication (primary)
# ──────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Reject requests without a valid X-API-Key header.
    Returns the key (used as rate-limit bucket + cost bucket).
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include header: X-API-Key: <your-key>",
        )
    if api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return api_key


# ──────────────────────────────────────────────────────────
# JWT Authentication (optional — for token-based flows)
# ──────────────────────────────────────────────────────────
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
bearer_scheme = HTTPBearer(auto_error=False)


def create_token(username: str, role: str = "user") -> str:
    payload = {
        "sub": username,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Include: Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[JWT_ALGORITHM]
        )
        return {"username": payload["sub"], "role": payload.get("role", "user")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")
