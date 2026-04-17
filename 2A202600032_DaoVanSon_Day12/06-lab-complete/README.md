# Lab 12 — Production AI Agent

Production-ready AI agent that combines every concept from Day 12:
12-factor config, Docker (multi-stage), API-key auth, rate limiting,
monthly cost guard, health/readiness probes, graceful shutdown,
stateless design (Redis), and Nginx load balancing.

---

## Structure

```
06-lab-complete/
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI entry point
│   ├── config.py       # 12-factor config (env vars)
│   ├── auth.py         # API Key + JWT helpers
│   ├── rate_limiter.py # Sliding-window limiter (Redis)
│   └── cost_guard.py   # Monthly budget guard (Redis)
├── utils/
│   └── mock_llm.py     # Offline stand-in for OpenAI/Anthropic
├── Dockerfile          # Multi-stage, non-root, < 500 MB
├── docker-compose.yml  # agent + redis + nginx
├── nginx.conf          # Load balancer config
├── railway.toml        # Railway deploy config
├── render.yaml         # Render deploy config
├── requirements.txt
├── .env.example
└── .dockerignore
```

---

## Run locally (Docker Compose)

```bash
cd 06-lab-complete
cp .env.example .env
# edit .env → set AGENT_API_KEY + JWT_SECRET to long random strings

docker compose up --build
```

The stack exposes the agent through Nginx on port **80**.

### Smoke test

```bash
# 1. Health (public)
curl http://localhost/health

# 2. No key → 401
curl -X POST http://localhost/ask \
     -H "Content-Type: application/json" \
     -d '{"user_id":"u1","question":"Hello"}'

# 3. With key → 200
API_KEY=$(grep AGENT_API_KEY .env | cut -d= -f2)
curl -X POST http://localhost/ask \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"user_id":"u1","question":"What is deployment?"}'

# 4. Trip rate limit (10 req/min)
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code}\n" \
       -X POST http://localhost/ask \
       -H "X-API-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d '{"user_id":"u1","question":"test"}'
done
# Expect a mix of 200 then 429.
```

---

## Run without Docker (Python only)

```bash
pip install -r requirements.txt
export AGENT_API_KEY=dev-secret-123
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Rate limiter and cost guard will fall back to in-memory storage when
`REDIS_URL` is empty.

---

## Deploy

Railway:
```bash
railway init
railway variables set AGENT_API_KEY=...
railway variables set JWT_SECRET=...
railway variables set REDIS_URL=...
railway up
railway domain
```

Render: push the repo to GitHub → New → Blueprint → pick this folder →
Render reads `render.yaml`. Set `AGENT_API_KEY` and `REDIS_URL` secrets
in the dashboard.

Full write-up in [`DEPLOYMENT.md`](../DEPLOYMENT.md).

---

## Production readiness check

```bash
python check_production_ready.py
```

Reports ✅/❌ for every item in the delivery checklist.
