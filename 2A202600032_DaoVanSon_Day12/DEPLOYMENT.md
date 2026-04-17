# Deployment Information — Day 12 Production AI Agent

> **AICB-P1 · VinUniversity 2026**
> **Student:** Đào Văn Sơn 

---

## Public URL

```
https://agent-production-70bc.up.railway.app
```

> **Deployment status (17/4/2026):** domain đã cấp, source đã upload, build
> thành công. Healthcheck đang fail do `$PORT` cần expand qua shell — đã
> có fix trong [`railway.toml`](06-lab-complete/railway.toml) (wrap command
> bằng `sh -c`), cần chạy `railway up` thêm một lần để kích hoạt fix.

### Re-deploy lệnh cuối cùng

```bash
cd 06-lab-complete
export RAILWAY_API_TOKEN="<your-token>"
railway up --ci --service agent --environment production
```

## Platform

**Railway** (project `day12-agent-deployment`)

| Resource | Value |
|----------|-------|
| Project ID | `01ff259d-88ad-43e5-8fde-2b289b4a30cc` |
| Environment | `production` |
| Region | `us-west2` |
| Service (app) | `agent` — ID `50ec497e-7a57-4ba3-b8f5-05d20b7973de` |
| Service (cache) | `Redis` — ID `2df7e38a-7d78-421c-ae11-1b05fec9f977` |
| Private Redis URL | `redis://default:***@redis.railway.internal:6379` |
| Public domain | `agent-production-70bc.up.railway.app` |
| Build logs | https://railway.com/project/01ff259d-88ad-43e5-8fde-2b289b4a30cc/service/50ec497e-7a57-4ba3-b8f5-05d20b7973de |

---

## Test commands

Khi service healthy, các lệnh sau sẽ pass:

### 1. Health check (public, no auth)

```bash
curl https://agent-production-70bc.up.railway.app/health
# Expected:
# {
#   "status": "ok",
#   "version": "1.0.0",
#   "environment": "production",
#   "uptime_seconds": ...,
#   "total_requests": ...,
#   "checks": {"llm": "mock"},
#   "timestamp": "..."
# }
```

### 2. Missing key → 401

```bash
curl -X POST https://agent-production-70bc.up.railway.app/ask \
     -H "Content-Type: application/json" \
     -d '{"user_id":"test","question":"Hello"}'
# {"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

### 3. Valid API key → 200

```bash
export API_KEY='<your-api-key>'   # lấy từ Railway dashboard → Variables → AGENT_API_KEY

curl -X POST https://agent-production-70bc.up.railway.app/ask \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"user_id":"test","question":"Hello"}'
```

### 4. Rate limit (10/min) — 429 sau 10 req

```bash
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code}\n" \
       -X POST https://agent-production-70bc.up.railway.app/ask \
       -H "X-API-Key: $API_KEY" \
       -H "Content-Type: application/json" \
       -d '{"user_id":"test","question":"test"}'
done
# Expected: 10×200 then 5×429
```

### 5. Readiness probe

```bash
curl https://agent-production-70bc.up.railway.app/ready
# {"ready": true}
```

---

## Environment variables set (Railway dashboard → Variables)

| Variable | Value | Notes |
|----------|-------|-------|
| `PORT` | auto-injected | Railway runtime |
| `ENVIRONMENT` | `production` | Manual |
| `APP_NAME` | `Production AI Agent` | Manual |
| `APP_VERSION` | `1.0.0` | Manual |
| `LOG_LEVEL` | `INFO` | Manual |
| `AGENT_API_KEY` | `<redacted — 64-char hex>` | Random hex32 |
| `JWT_SECRET` | `<redacted — 64-char hex>` | Random hex32 |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Auto-reference Redis service |
| `RATE_LIMIT_PER_MINUTE` | `10` | Manual |
| `MONTHLY_BUDGET_USD` | `10.0` | Manual |
| `ALLOWED_ORIGINS` | `*` | Manual (thu hẹp khi có frontend cụ thể) |

> **Không** set `OPENAI_API_KEY` — đang dùng `mock_llm` để tránh chi phí.
> Khi cần real LLM: set `OPENAI_API_KEY` và swap `utils/mock_llm.ask` sang
> OpenAI SDK trong `app/main.py`.

---

## Screenshots (cần sinh viên chụp sau khi re-deploy xong)

| File | Mô tả |
|------|-------|
| `screenshots/railway-dashboard.png` | Railway project dashboard — agent + Redis + domain |
| `screenshots/railway-logs.png` | Logs của agent service (JSON structured logs) |
| `screenshots/curl-health.png` | Terminal output `curl /health` → 200 |
| `screenshots/curl-auth.png` | Test auth: 401 khi không có key, 200 khi có key |
| `screenshots/curl-ratelimit.png` | Test rate limit: 429 sau 10 req |
| `screenshots/env-vars.png` | Railway dashboard → Variables (che giá trị secret) |

---

## Deploy steps đã thực hiện

```bash
# 1. Install CLI
npm install -g @railway/cli

# 2. Auth (token từ https://railway.com/account/tokens)
export RAILWAY_API_TOKEN="<account-token>"

# 3. Create project + link
railway init --name day12-agent-deployment
railway link --project 01ff259d-88ad-43e5-8fde-2b289b4a30cc \
             --service agent --environment production

# 4. Add Redis + empty app service
railway add --database redis
railway add --service agent

# 5. Set variables (10 keys)
railway variables --skip-deploys \
  --set ENVIRONMENT=production \
  --set APP_NAME="Production AI Agent" \
  --set APP_VERSION=1.0.0 \
  --set LOG_LEVEL=INFO \
  --set AGENT_API_KEY=<random-hex32> \
  --set JWT_SECRET=<random-hex32> \
  --set RATE_LIMIT_PER_MINUTE=10 \
  --set MONTHLY_BUDGET_USD=10.0 \
  --set ALLOWED_ORIGINS='*' \
  --set 'REDIS_URL=${{Redis.REDIS_URL}}'

# 6. Generate public domain
railway domain --service agent --port 8000
# → https://agent-production-70bc.up.railway.app

# 7. Deploy
railway up --ci --service agent --environment production
```

## Issues gặp phải + fix

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Build fail: `No module named 'uvicorn'` | `useradd -d /app` set `$HOME=/app` → Python user-site không trỏ vào `/home/agent/.local` | Sửa Dockerfile: `useradd -m -d /home/agent`, set `HOME=/home/agent` và thêm site-packages vào `PYTHONPATH` |
| 2 | Healthcheck fail: `Invalid value for '--port': '$PORT' is not a valid integer` | Railway chạy `startCommand` trực tiếp (không qua shell) → `$PORT` không expand | Wrap bằng `sh -c '...${PORT:-8000}...'` trong `railway.toml` |

Fix #2 đã commit vào `railway.toml` nhưng chưa re-deploy (theo yêu cầu).
Chỉ cần một lần `railway up --ci` nữa là service sẽ lên xanh.

---

## Rollback / redeploy

```bash
# Redeploy current source
railway up --ci

# Restart without rebuild
railway restart --service agent

# Rollback: dashboard → Deployments → Redeploy previous build
```

## Local reproduction

```bash
cd 06-lab-complete
cp .env.example .env          # điền secrets
docker compose up --build      # agent + redis + nginx on http://localhost
```

---

## Known limitations

- **Mock LLM** — response random trong `MOCK_RESPONSES`; không gọi OpenAI thật.
- **Token counting heuristic** — dùng `len(text.split()) * 2`; với real LLM cần lấy token count từ response của provider.
- **Rate limit per `user_id` trong body** — không bind vào JWT/auth. Sẵn sàng upgrade khi có user-management thật.
