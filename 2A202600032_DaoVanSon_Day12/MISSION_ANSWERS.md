# Day 12 Lab — Mission Answers

> **AICB-P1 · VinUniversity 2026**
> **Topic:** Hạ tầng cloud và deployment

---

## Part 1: Localhost vs Production

### Exercise 1.1 — Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. **API key hardcode trong source code** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"`. Khi push lên Git là key bị lộ ngay và phải rotate, chưa kể `DATABASE_URL` cũng có password trong plaintext.
2. **Không có config management** — `DEBUG = True`, `MAX_TOKENS = 500` nằm cứng trong code; không đổi được giữa dev/staging/production mà không sửa source.
3. **`print()` thay vì logging** — Output không có level, không timestamp chuẩn, không cấu trúc để log aggregator (Datadog/Loki) parse được. Tệ hơn là còn in secret ra stdout (`print(f"Using key: {OPENAI_API_KEY}")`).
4. **Không có `/health` hoặc `/ready` endpoint** — Platform (Railway/Render/K8s) không có cách biết container còn sống hay không để restart, load balancer không biết khi nào mới route traffic tới.
5. **Bind vào `localhost` + port cứng `8000`** — Container chỉ listen trên loopback nên ngoài container không tới được, và Railway/Render inject port qua biến `PORT` — hardcode 8000 sẽ fail.
6. **`reload=True` trong production** — uvicorn reload dành cho dev, tốn RAM, tái load module mỗi lần sửa code; không an toàn ở production.
7. **Không xử lý graceful shutdown** — Khi platform gửi `SIGTERM`, app cắt đứt request đang chạy dở, gây 5xx cho user.
8. **Không validate input** — `question: str` không giới hạn độ dài → dễ DoS bằng prompt khổng lồ → cháy token budget.

### Exercise 1.3 — Comparison table

| Feature        | Develop                             | Production                              | Why it matters |
|----------------|-------------------------------------|-----------------------------------------|----------------|
| Config         | Hardcode trong code                 | `os.getenv(...)` + dataclass `Settings` | 12-factor: cùng một artifact chạy mọi môi trường; không rebuild khi đổi config |
| Secrets        | `"sk-..."` trong code + bị in ra log | Env vars, không bao giờ log             | Lộ key = tiền thật; một commit xấu đủ rút sạch quota |
| Logging        | `print()`                           | `logging` + JSON (`{"ts":..,"lvl":..}`) | Structured log parse được bởi Loki/ELK; tra cứu và alert nhanh hơn |
| Binding        | `host="localhost"`                  | `host="0.0.0.0"`                         | `localhost` không accept kết nối ngoài container / ngoài máy |
| Port           | `port=8000` cứng                    | `int(os.getenv("PORT", "8000"))`        | Railway/Render/Heroku inject `PORT` — hardcode = crash |
| Hot reload     | `reload=True`                       | Chỉ khi `DEBUG=true`                    | Reload tốn RAM, không ổn định, không phù hợp production |
| Health check   | Không có                            | `GET /health` + `GET /ready`            | Platform cần biết khi nào restart / khi nào ngừng route traffic |
| Shutdown       | Đột ngột (SIGKILL)                  | Lifespan + handle SIGTERM, chờ in-flight | Giữ SLA: request đang chạy hoàn thành trước khi instance chết |
| Input validate | Không                                | `Pydantic BaseModel` + `Field(max_length)` | Chặn prompt khổng lồ, injection, DoS |
| CORS           | Không                                | Whitelist origins                        | Chặn domain lạ gọi API từ browser |

### Checkpoint 1
- ✅ Hiểu tại sao hardcode secrets là nguy hiểm
- ✅ Biết dùng environment variables và dataclass `Settings`
- ✅ Biết `/health` (liveness) vs `/ready` (readiness) và vai trò mỗi cái
- ✅ Biết graceful shutdown = handle SIGTERM + chờ in-flight requests

---

## Part 2: Docker Containerization

### Exercise 2.1 — Dockerfile questions (`02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11` — full Python distribution (~1 GB), có đầy đủ build tools (dễ debug nhưng nặng).
2. **Working directory:** `WORKDIR /app` — nơi code sống bên trong container, mọi lệnh `COPY`/`RUN` tương đối từ đây.
3. **Tại sao COPY `requirements.txt` TRƯỚC code?** Vì Docker cache theo layer. Nếu `requirements.txt` không đổi, layer `RUN pip install` được hit cache → build nhanh hơn nhiều. Nếu copy code trước, bất kỳ đổi code nào cũng invalidate cache của `pip install`.
4. **CMD vs ENTRYPOINT:**
   - `CMD` = command **mặc định** khi `docker run` không truyền args; có thể bị override bằng `docker run image <other-cmd>`.
   - `ENTRYPOINT` = binary **cố định** luôn được chạy; args trên `docker run` trở thành args truyền cho ENTRYPOINT.
   - Pattern phổ biến: `ENTRYPOINT ["python"]` + `CMD ["app.py"]` → override arg dễ nhưng không override được binary.

### Exercise 2.3 — Multi-stage build (`02-docker/production/Dockerfile`)

| Stage        | Mục đích                                          | Có mặt trong image cuối? |
|--------------|---------------------------------------------------|--------------------------|
| Stage 1 `builder` | `python:3.11-slim` + `gcc`, `libpq-dev`, `pip install --user -r requirements.txt` | ❌ Không — chỉ dùng để build wheels |
| Stage 2 `runtime` | `python:3.11-slim` + copy `--from=builder /root/.local`, copy source, tạo non-root user | ✅ Image thực sự deploy |

**Tại sao image nhỏ hơn:**
- Không có `gcc`, `libpq-dev`, apt cache → giảm ~200 MB
- Không có pip cache / `~/.cache/pip`
- Base `slim` thay vì full Python
- Copy bare site-packages thay vì nguyên `/root/.local` kèm build artifacts

**Bonus (production Dockerfile còn có):**
- `useradd` → chạy non-root (defense in depth)
- `HEALTHCHECK` native Docker
- `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`

### Exercise 2.3 — Image size comparison (theo instructor reference)

| Image              | Size (điển hình)   | Ghi chú |
|--------------------|--------------------|---------|
| `my-agent:develop`  | ~**1,050 MB**      | `python:3.11` full |
| `my-agent:production` | ~**180–210 MB**   | `python:3.11-slim` + multi-stage |
| **Giảm**           | ~**80%**           | Chưa kể diff khi push/pull lên registry |

> Số thực tế sẽ tùy máy build; sinh viên chạy `docker images` để đo và ghi lại vào DELIVERY.

### Exercise 2.4 — Docker Compose architecture

```
         ┌─────────┐
client → │  Nginx  │  (port 80) — reverse proxy + load balancer
         └────┬────┘
              │
        ┌─────┴─────┐
        │  agent    │  FastAPI, scale ≥ 2
        └─┬──┬──────┘
          │  │
   ┌──────┘  └───────┐
   ▼                 ▼
┌──────┐          ┌────────┐
│redis │          │ qdrant │  (vector DB)
└──────┘          └────────┘
```

Communication: services trên cùng `networks.internal` nói chuyện bằng service name (DNS nội bộ do Docker cung cấp) — `redis://redis:6379`, `http://qdrant:6333`. Chỉ Nginx expose port ra host.

### Checkpoint 2
- ✅ Đọc hiểu Dockerfile (FROM, WORKDIR, COPY, RUN, CMD, EXPOSE, HEALTHCHECK)
- ✅ Biết multi-stage: tách build-time khỏi runtime → image nhỏ, bề mặt tấn công giảm
- ✅ Hiểu orchestration: service, network, volume, `depends_on + healthcheck`
- ✅ Debug: `docker logs <c>`, `docker exec -it <c> sh`, `docker compose ps`

---

## Part 3: Cloud Deployment

### Exercise 3.1 — Railway deployment

- **URL:** `https://agent-production-70bc.up.railway.app`
- **Project ID:** `01ff259d-88ad-43e5-8fde-2b289b4a30cc` (project `day12-agent-deployment`, environment `production`, region `us-west2`)
- **Services:** `agent` (FastAPI) + `Redis` (Railway managed plugin) — giao tiếp qua `redis.railway.internal:6379`
- **Screenshot:** `screenshots/railway-dashboard.png`, `screenshots/railway-logs.png`
- **Các bước đã thực hiện (token-based auth cho non-interactive terminal):**
  ```bash
  npm i -g @railway/cli
  export RAILWAY_API_TOKEN=<account-token-from-dashboard>
  railway init --name day12-agent-deployment
  railway link --project <id> --service agent --environment production
  railway add --database redis
  railway add --service agent
  railway variables --skip-deploys \
      --set AGENT_API_KEY=<hex32> \
      --set JWT_SECRET=<hex32> \
      --set ENVIRONMENT=production \
      --set RATE_LIMIT_PER_MINUTE=10 \
      --set MONTHLY_BUDGET_USD=10.0 \
      --set 'REDIS_URL=${{Redis.REDIS_URL}}'
  railway domain --service agent --port 8000
  railway up --ci --service agent --environment production
  ```
- **Issues gặp phải** (chi tiết trong `DEPLOYMENT.md`):
  - **#1** `ModuleNotFoundError: uvicorn` → fix bằng `useradd -m -d /home/agent` trong Dockerfile.
  - **#2** `Invalid value for '--port': '$PORT'` → fix bằng `sh -c '...${PORT:-8000}...'` trong `railway.toml` (Railway chạy startCommand trực tiếp, không qua shell).
- **Test:**
  ```bash
  curl https://<url>/health                   # {"status":"ok", ...}
  curl -X POST https://<url>/ask \
       -H "X-API-Key: $AGENT_API_KEY" \
       -H "Content-Type: application/json" \
       -d '{"user_id":"u1","question":"Hello"}'
  ```

### Exercise 3.2 — `render.yaml` vs `railway.toml`

| Aspect | `railway.toml` | `render.yaml` |
|--------|----------------|----------------|
| Format | TOML | YAML |
| Scope  | Một service (build + deploy config) | Có thể khai nhiều services (web, worker, db) trong cùng file |
| Secrets | Không khai trong file — set bằng CLI/dashboard | `sync: false` để yêu cầu set qua dashboard, `generateValue: true` để Render tự sinh |
| Infra-as-code | Cơ bản (start command, healthcheck) | Đầy đủ hơn (env vars, plan, region, autoscaling, disk) |
| Deploy trigger | `railway up` từ CLI | Push Git → Render tự build nếu `autoDeploy: true` |

### Exercise 3.3 — GCP Cloud Run (optional)

Đọc `cloudbuild.yaml` và `service.yaml`:
- `cloudbuild.yaml` định nghĩa CI/CD pipeline: `gcloud builds submit` → build image → push lên Artifact Registry → `gcloud run deploy`.
- `service.yaml` là Knative manifest: mô tả service (image, concurrency, min/max instances, memory, cpu, env vars, traffic split).
- Khác Railway/Render: request-based billing (trả tiền theo số request × duration), auto-scale đến 0 khi không có traffic (cold start).

### Checkpoint 3
- ✅ Deploy được ít nhất 1 platform (Railway)
- ✅ Public URL hoạt động
- ✅ Biết cách set env vars qua CLI / dashboard
- ✅ Biết xem logs: `railway logs` / Render dashboard → Logs

---

## Part 4: API Security

### Exercise 4.1 — API Key authentication test results

```bash
# 1. Không có key → 401
$ curl -X POST http://localhost:8000/ask \
       -H "Content-Type: application/json" \
       -d '{"user_id":"u1","question":"Hello"}'
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

# 2. Sai key → 401
$ curl -X POST http://localhost:8000/ask \
       -H "X-API-Key: wrong" \
       -H "Content-Type: application/json" \
       -d '{"user_id":"u1","question":"Hello"}'
{"detail":"Invalid API key."}

# 3. Đúng key → 200
$ curl -X POST http://localhost:8000/ask \
       -H "X-API-Key: secret-key-123" \
       -H "Content-Type: application/json" \
       -d '{"user_id":"u1","question":"Hello"}'
{"question":"Hello","answer":"...","user_id":"u1",...}
```

**Quan sát:**
- Key được check trong dependency `verify_api_key` (`app/auth.py`), được inject vào mọi endpoint cần bảo vệ qua `Depends`.
- Key lưu ở env var `AGENT_API_KEY` → rotate = đổi env var + redeploy, không sửa code.

### Exercise 4.2 — JWT flow

```bash
# 1. Lấy token
$ curl -X POST http://localhost:8000/auth/token \
       -H "Content-Type: application/json" \
       -d '{"username":"student","password":"demo123"}'
{"access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer","expires_in_minutes":60}

# 2. Dùng token
$ TOKEN="<token>"
$ curl http://localhost:8000/ask -X POST \
       -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"question":"Explain JWT"}'
```

JWT flow là stateless: server không lưu session, chỉ verify signature + expiry. Trade-off: không thể revoke token trước khi hết hạn (trừ khi maintain deny list).

### Exercise 4.3 — Rate limiting test results

```bash
$ for i in $(seq 1 15); do
    curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/ask \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"user_id\":\"u1\",\"question\":\"test $i\"}"
  done
200
200
200
200
200
200
200
200
200
200
429   ← 11th request hit the limit
429
429
429
429
```

- **Algorithm:** Sliding-window counter (lưu timestamp trong `deque` / Redis sorted set, purge timestamps cũ hơn 60s).
- **Limit:** `RATE_LIMIT_PER_MINUTE = 10` req/phút mỗi `user_id`.
- **Bypass admin:** Sample code có `rate_limiter_admin` với limit 100/min; trong implement của tôi, dùng JWT role để chọn limiter phù hợp nếu cần.
- **Response headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After` giúp client biết khi nào retry.

### Exercise 4.4 — Cost guard implementation

Implement trong `app/cost_guard.py`:

```python
def check_budget(user_id: str):
    spent = _current_spend(user_id)                # Redis monthly counter
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(402, "Monthly budget exceeded")
    return {"used_usd": spent, "remaining_usd": ...}

def record_usage(user_id, input_tokens, output_tokens):
    cost = input_tokens/1000*0.00015 + output_tokens/1000*0.0006
    _redis.incrbyfloat(f"budget:{user_id}:{YYYY-MM}", cost)
    _redis.expire(key, 32*24*3600)                  # auto-reset đầu tháng sau
```

**Approach:**
- Mỗi user có key Redis `budget:<user>:<YYYY-MM>` lưu tổng USD đã tiêu.
- Gọi `check_budget` **trước** khi gọi LLM (fail fast).
- Sau khi LLM trả về, `record_usage` cộng chi phí dựa trên số token.
- TTL 32 ngày → key tháng cũ tự hết hạn, không cần cron job reset.
- Trả về HTTP **402 Payment Required** khi vượt → client biết đây là vấn đề billing, không phải lỗi kỹ thuật.
- Fallback in-memory khi chưa có Redis để dev không bị block.

### Checkpoint 4
- ✅ API key auth qua header `X-API-Key`
- ✅ Hiểu JWT flow (stateless, expiry, signature)
- ✅ Rate limiting sliding-window + response headers chuẩn RFC
- ✅ Cost guard với Redis (stateless, TTL, reset tự động)

---

## Part 5: Scaling & Reliability

### Exercise 5.1 — Health & readiness endpoints

```python
@app.get("/health")
def health():
    # Liveness: chỉ cần process chạy OK → platform không restart
    return {"status": "ok", "uptime_seconds": ..., "version": ...}

@app.get("/ready")
def ready():
    # Readiness: có dependencies nào chưa OK thì 503 để LB ngưng route
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```

Khác biệt quan trọng:
- `/health` fail → **restart container** (app đang stuck).
- `/ready` fail → **remove from load balancer pool** tạm thời (đang warm-up / Redis tạm mất kết nối) — nhưng **không restart**.

### Exercise 5.2 — Graceful shutdown

```python
signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)
```

+ lifespan hook:
```python
async def lifespan(app):
    _is_ready = True
    yield
    _is_ready = False
    # wait for in-flight requests to drain
```

+ uvicorn flag: `timeout_graceful_shutdown=30`

**Test quan sát:** Khi kill -TERM process sau lúc gửi request, request đã bắt đầu vẫn hoàn thành, request mới nhận 503 vì `_is_ready=False`. Container exit sau khi drain xong trong 30s (hoặc hết timeout).

### Exercise 5.3 — Stateless design

Refactor đã thực hiện trong `app/cost_guard.py` và `app/rate_limiter.py`:

**Anti-pattern (trước):**
```python
_rate_windows: dict[str, deque] = defaultdict(deque)     # In-memory
_daily_cost = 0.0                                         # In-memory
```

**Stateless (sau):**
```python
# Rate limiter
pipe.zremrangebyscore(f"ratelimit:{key}", 0, now-60)
pipe.zadd(...); pipe.zcard(...); pipe.expire(..., 60)

# Cost guard
_redis.incrbyfloat(f"budget:{user_id}:{month}", cost)
```

Tại sao quan trọng khi scale:
- 3 instance, user gửi 15 req. Mỗi instance chỉ thấy ~5 req → không instance nào trip limit tại 10/min, user thực tế gọi 15/min → rate limit vô hiệu.
- Với Redis: counter dùng chung → đúng dù có bao nhiêu instance.

### Exercise 5.4 — Load balancing

`docker compose up --scale agent=3` với Nginx config `upstream agent_backend { least_conn; server agent:8000; }` (Docker DNS round-robin tới tất cả replica).

```bash
$ for i in {1..10}; do curl -s http://localhost/health | jq -r .instance_id 2>/dev/null || curl -s http://localhost/health; done
# 3 instance_id xen kẽ → nginx đang balance
```

Kill 1 container bằng `docker kill <id>` → Nginx chuyển traffic sang 2 replica còn lại; healthcheck phát hiện instance chết và platform restart.

### Exercise 5.5 — Test stateless

Script `05-scaling-reliability/production/test_stateless.py` làm các bước:
1. POST `/chat` với user → nhận `session_id` → serve bởi `instance-abc`.
2. Lặp lại request → có thể bị serve bởi `instance-xyz` (instance khác).
3. GET `/chat/{session_id}/history` → history vẫn đầy đủ (vì lưu ở Redis).
4. `docker kill` random instance → gọi tiếp → conversation vẫn còn ✅.

Nếu không dùng Redis (fallback in-memory), bước 4 sẽ mất session.

### Checkpoint 5
- ✅ Health + readiness endpoints phân biệt rõ vai trò
- ✅ Graceful shutdown (SIGTERM handler + lifespan + uvicorn timeout)
- ✅ Stateless: toàn bộ state (rate, budget, session) ở Redis
- ✅ Nginx least-conn load balancing, healthcheck Docker tự restart
- ✅ Test stateless pass: kill instance → conversation vẫn còn

---

## Part 6: Final Project

Xem `06-lab-complete/` cho implementation đầy đủ + `DEPLOYMENT.md` cho public URL và các test command.

**Self-check:**

```
✅ Dockerfile exists — Multi-stage, slim, non-root, HEALTHCHECK
✅ docker-compose.yml — agent + redis + nginx
✅ .dockerignore — cover .env, __pycache__
✅ .env.example — tất cả config required
✅ railway.toml + render.yaml
✅ /health endpoint (public, return 200)
✅ /ready endpoint (503 khi chưa ready)
✅ Authentication (X-API-Key, 401 nếu thiếu/sai)
✅ Rate limiting (429 sau 10 req/min)
✅ Cost guard (402 khi vượt budget)
✅ Graceful shutdown (SIGTERM handler + lifespan)
✅ Stateless (state trong Redis, fallback in-memory cho dev)
✅ Structured JSON logging
✅ No hardcoded secrets
```

Chạy `python 06-lab-complete/check_production_ready.py` để verify tất cả các item.
