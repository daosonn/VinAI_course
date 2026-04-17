# ============================================================
# Production Dockerfile — multi-stage, slim runtime, non-root
# Target image size: < 500 MB
# ============================================================

# ── Stage 1: builder — pip + build deps only, never shipped
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: runtime — just Python + site-packages + source
FROM python:3.11-slim AS runtime

# Non-root user — running as root inside a container is a bad default
RUN groupadd -r agent && useradd -r -g agent -m -d /home/agent agent

WORKDIR /app

# Copy pre-built packages from builder stage
COPY --from=builder /root/.local /home/agent/.local

# Copy application source
COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R agent:agent /app /home/agent/.local

USER agent

ENV HOME=/home/agent \
    PATH=/home/agent/.local/bin:$PATH \
    PYTHONPATH=/app:/home/agent/.local/lib/python3.11/site-packages \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Docker-native health probe — restarts the container on persistent failure
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
        || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
