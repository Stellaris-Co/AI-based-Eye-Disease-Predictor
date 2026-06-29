# PRODUCTION.md — OphthalmoAI Production Deployment Guide

This guide covers three production deployment paths:

| Path | Best for |
|------|---------|
| **Docker Compose** | Single VM or VPS (fastest to set up) |
| **Azure Container Apps** | Cloud-hosted; GitHub Student Developer Pack |
| **Kubernetes / AKS** | High-availability, multi-replica cluster |

For full Azure step-by-step instructions, see **[AZURE_DEPLOY.md](AZURE_DEPLOY.md)**.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Docker Compose (Recommended for VPS)](#docker-compose)
- [Azure Container Apps](#azure-container-apps)
- [Kubernetes / AKS](#kubernetes--aks)
- [Nginx Configuration Notes](#nginx-configuration-notes)
- [Model Management](#model-management)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Security Hardening](#security-hardening)
- [Performance Tuning](#performance-tuning)
- [Upgrading](#upgrading)

---

## Prerequisites

- Docker ≥ 24 and Docker Compose v2
- Trained model files in `models/` (see README — Model Training)
- A Google Gemini API key **or** Ollama running and accessible
- A JWT secret key: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Environment Variables

Create `.env` in the project root (copy `.env.example`):

```env
# ── Auth (REQUIRED in production) ──────────────────────────────
JWT_SECRET_KEY=<32-byte-hex>              # generate: python -c "import secrets; print(secrets.token_hex(32))"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
ENVIRONMENT=production                    # enables startup guards + HSTS + safe errors

# ── LLM Chat (choose one) ───────────────────────────────────────
GEMINI_API_KEY=AIza...                    # takes priority over Ollama
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_URL=                               # e.g. http://ollama-host:11434
OLLAMA_MODEL=llama3.2:3b

# ── Database ────────────────────────────────────────────────────
# Dev (SQLite, no setup needed):
DATABASE_URL=sqlite:///./ophthalmoai.db
# Prod (PostgreSQL):
# DATABASE_URL=postgresql://user:pass@host:5432/ophthalmoai?sslmode=require

# ── Inference ───────────────────────────────────────────────────
FORCE_CPU=false
MAX_FILE_SIZE_BYTES=20971520              # 20 MB upload limit
MODELS_DIR=./models

# ── Networking ──────────────────────────────────────────────────
CORS_ORIGINS=https://yourdomain.com       # comma-separated; NEVER use * in production
CORS_ALLOW_CREDENTIALS=false              # must stay false while CORS_ORIGINS=*
PORT=8000
HOST=0.0.0.0

# ── Rate Limiting ───────────────────────────────────────────────
PREDICT_RATE_LIMIT=10/minute
CHAT_RATE_LIMIT=30/minute
AUTH_RATE_LIMIT=20/minute

# ── Calibration & Uncertainty ───────────────────────────────────
MC_DROPOUT_PASSES=8
ENABLE_UNCERTAINTY=true
ENABLE_IQA=true
PERSIST_SCANS=true

# ── Image Storage (optional, S3-compatible) ─────────────────────
# SCAN_STORAGE_BUCKET=ophthalmoai-scans
# SCAN_STORAGE_KMS_KEY_ID=arn:aws:kms:...
# AWS_REGION=us-east-1
```

> **Security:** Never commit `.env` to source control. Use secrets managers (Docker secrets, Azure Container Apps secrets, K8s Secrets, Vault) in production.

---

## Docker Compose

Suitable for a single Linux VM (e.g., $6/month DigitalOcean Droplet).

### Start

```bash
docker compose up --build -d
```

- Backend: http://localhost:8000
- Frontend: http://localhost:8080

### Production overrides

Create `docker-compose.prod.yml`:

```yaml
services:
  backend:
    restart: always
    environment:
      ENVIRONMENT: production
      CORS_ORIGINS: "https://yourdomain.com"
      CORS_ALLOW_CREDENTIALS: "false"
    deploy:
      resources:
        limits:
          memory: 8g

  frontend:
    restart: always
    ports:
      - "80:8080"
```

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Startup guards in production

When `ENVIRONMENT=production`, the backend enforces these at startup and will **refuse to start** if violated:

1. `JWT_SECRET_KEY` must not equal `"CHANGE_ME_BEFORE_PRODUCTION_DEPLOYMENT"`
2. `CORS_ORIGINS` must not be `"*"` (wildcard)
3. `CORS_ORIGINS=*` combined with `CORS_ALLOW_CREDENTIALS=true` is always rejected
4. `OLLAMA_URL` (if set) must not resolve to a private/reserved IP address

### Useful commands

```bash
docker compose logs -f backend          # stream backend logs
docker compose logs -f frontend         # stream frontend logs
docker compose pull && docker compose up -d   # update to latest images
docker compose down                     # stop
```

---

## Azure Container Apps

See **[AZURE_DEPLOY.md](AZURE_DEPLOY.md)** for the complete guide including the automated `infra/azure/deploy.sh` script.

**Quick reference:**

```bash
# One-time setup
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export GEMINI_API_KEY="your-key"
export PG_PASSWORD="StrongPass123!"
bash infra/azure/deploy.sh

# View live logs
az containerapp logs show --name ophthalmoai-backend --resource-group ophthalmoai-rg --follow

# Restart after model update
az containerapp update \
  --name ophthalmoai-backend \
  --resource-group ophthalmoai-rg \
  --image <acr-server>/ophthalmoai-backend:latest

# Stop PostgreSQL to save credit
az postgres flexible-server stop \
  --name <pg-server> --resource-group ophthalmoai-rg
```

---

## Kubernetes / AKS

### 1. Build & tag images

```bash
docker build -t ophthalmoai-backend:latest -f backend/Dockerfile .
docker build -t ophthalmoai-frontend:latest -f frontend/Dockerfile \
  --build-arg VITE_API_URL=/api .
```

For a registry:
```bash
docker tag ophthalmoai-backend:latest your-registry/ophthalmoai-backend:v2.1.0
docker push your-registry/ophthalmoai-backend:v2.1.0
```

Update `image:` in `k8s/backend-deployment.yaml` and `k8s/frontend-deployment.yaml`.

### 2. Create namespace and secrets

```bash
kubectl create namespace ophthalmoai

kubectl create secret generic ophthalmoai-secrets \
  --namespace ophthalmoai \
  --from-literal=GEMINI_API_KEY=AIza... \
  --from-literal=JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Apply manifests

```bash
kubectl apply -k k8s
```

### 4. Monitor rollout

```bash
kubectl -n ophthalmoai rollout status deployment/backend
kubectl -n ophthalmoai rollout status deployment/frontend
kubectl -n ophthalmoai get pods,svc,ingress
```

### 5. Local port-forward (no Ingress needed)

```bash
kubectl -n ophthalmoai port-forward svc/frontend 8080:80
```

Open: http://localhost:8080

### 6. GPU scheduling (AKS)

> **Important:** `backend/Dockerfile` uses the **CPU-only** PyTorch wheel.
> GPU support requires a separate `backend/Dockerfile.gpu` using an `nvidia/cuda`
> base image with the `cu124` torch wheel.

To use GPU on AKS with a CUDA-enabled image:

```yaml
# k8s/backend-deployment.yaml
spec:
  template:
    spec:
      nodeSelector:
        accelerator: nvidia-tesla-t4
      containers:
        - name: backend
          image: your-registry/ophthalmoai-backend-gpu:v2.1.0
          resources:
            limits:
              nvidia.com/gpu: 1
          env:
            - name: FORCE_CPU
              value: "false"
```

---

## Nginx Configuration Notes

The frontend Nginx config (`frontend/nginx.conf`) handles:

| Path | Behaviour |
|------|-----------|
| `/api/*` | Proxied to `http://backend:8000/` (strips `/api` prefix) |
| `/healthz` | Returns 200 `ok` (Kubernetes readiness probe) |
| `/*` | SPA fallback to `index.html` |
| `*.js, *.css, *.png, …` | 30-day cache headers |

Proxy timeout is 180 s. When behind a load balancer, forward `X-Forwarded-For` and `X-Forwarded-Proto`.

---

## Model Management

The backend Dockerfile copies `models/` at build time:
```dockerfile
COPY models /app/models
```

### Updating models

1. Re-train: `python scripts/train_*.py`
2. Calibrate: `python scripts/calibrate_models.py`
3. Rebuild backend image: `docker compose build backend` (or push to ACR)
4. Redeploy

### Development: volume mount (skip rebuild)

```yaml
# docker-compose.override.yml
services:
  backend:
    volumes:
      - ./models:/app/models:ro
```

> Do not use volume mounts in Kubernetes — bake models into the image for immutable deployments.

---

## Health Checks & Monitoring

### Endpoints

| Endpoint | Type | Returns |
|----------|------|---------|
| `GET /health` | Liveness | `{"ok": true, "device": "cpu"}` — always 200 if process is alive |
| `GET /ready` | Readiness | `{"ok": true, "router_loaded": true}` — 503 if models not loaded |

### Docker Compose health check

Defined in `docker-compose.yml`. Frontend waits for backend to be healthy:

```yaml
depends_on:
  backend:
    condition: service_healthy
```

### Kubernetes probes (k8s/backend-deployment.yaml)

```yaml
readinessProbe:
  httpGet: {path: /ready, port: 8000}
  initialDelaySeconds: 60
  periodSeconds: 15
  failureThreshold: 6
livenessProbe:
  httpGet: {path: /health, port: 8000}
  initialDelaySeconds: 90
  periodSeconds: 30
  failureThreshold: 3
```

### Structured logging

The backend emits JSON logs when `LOG_FORMAT=json` (default in production). Useful log events:

```bash
# Backend inference results
docker compose logs backend | jq 'select(.event == "inference.complete")'

# Authentication events
docker compose logs backend | jq 'select(.event == "audit.event" and .action == "login")'

# Errors only
docker compose logs backend | jq 'select(.level == "error")'
```

### Recommended monitoring stack

- **Prometheus + Grafana** for request rates, latency, memory
- **Loki** for log aggregation
- **Azure Monitor / Log Analytics** for Azure deployments (built-in with Container Apps)

---

## Security Hardening

| Area | Setting |
|------|---------|
| `ENVIRONMENT` | Set `production` — enables all startup guards |
| `CORS_ORIGINS` | Exact domain(s) only — never `*` |
| `JWT_SECRET_KEY` | 32-byte random hex — never the placeholder |
| Container user | Non-root: `appuser` (backend), `nginx uid=101` (frontend) |
| File uploads | Magic-byte validated; 20 MB limit; decompression-bomb guard |
| Rate limiting | `slowapi` required in production; raises `RuntimeError` if absent |
| Security headers | CSP, HSTS (prod), X-Frame-Options, Referrer-Policy — applied by `SecurityHeadersMiddleware` |
| Chat input | Prompt-injection patterns blocked by `sanitise_chat_message()` |
| Login | 5 failures → 15-minute lockout; constant-time comparison |
| Tokens | JTI-based blacklist on logout; tamper-resistant via HMAC-SHA256 |
| Dependency scanning | `pip-audit` + `npm audit` in CI |
| Container scanning | Trivy in `.github/workflows/security.yml` |

For the full audit report, see [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md).

---

## Performance Tuning

### Backend

| Setting | Default | Notes |
|---------|---------|-------|
| `OMP_NUM_THREADS` | 4 | Match physical CPU cores |
| `FORCE_CPU` | false | Keep false if GPU available |
| `MC_DROPOUT_PASSES` | 8 | Reduce to 4 for faster inference on CPU |
| Uvicorn workers | 1 | Keep 1 for GPU; increase for CPU-only with asyncio lock |

### Frontend

| Setting | Impact |
|---------|--------|
| `VITE_API_URL=/api` | Eliminates CORS; proxied by Nginx |
| Nginx `gzip` | Add to `nginx.conf` for ~70% CSS/JS reduction |
| Nginx cache headers | Already 30 days for static assets |

---

## Upgrading

### Docker Compose

```bash
git pull origin main
docker compose up --build -d
```

### Azure Container Apps

```bash
# Rebuild and push
docker build -t <acr>/ophthalmoai-backend:latest -f backend/Dockerfile .
docker push <acr>/ophthalmoai-backend:latest

# Deploy
az containerapp update \
  --name ophthalmoai-backend \
  --resource-group ophthalmoai-rg \
  --image <acr>/ophthalmoai-backend:latest
```

Or just push to `main` — the GitHub Actions pipeline in `.github/workflows/azure-deploy.yml` handles it automatically.

### Kubernetes rolling update

```bash
kubectl -n ophthalmoai set image deployment/backend \
  backend=your-registry/ophthalmoai-backend:v2.2.0

kubectl -n ophthalmoai rollout status deployment/backend

# Roll back if needed
kubectl -n ophthalmoai rollout undo deployment/backend
```
