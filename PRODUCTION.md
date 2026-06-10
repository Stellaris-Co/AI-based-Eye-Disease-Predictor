# Production Deployment Guide

This guide covers all production deployment paths for OphthalmoAI: Docker Compose (single server), and Kubernetes (cluster).

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Docker Compose (Recommended)](#docker-compose-recommended)
- [Kubernetes](#kubernetes)
- [Nginx Configuration Notes](#nginx-configuration-notes)
- [Model Management](#model-management)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Security Hardening](#security-hardening)
- [Performance Tuning](#performance-tuning)
- [Upgrading](#upgrading)

---

## Prerequisites

- Docker ≥ 24 and Docker Compose v2
- (Optional) A Kubernetes cluster with `kubectl` and `kustomize`
- Trained model files in `models/` (see [README — Model Training](README.md#3-model-training))
- An Anthropic API key **or** Ollama running and accessible

---

## Environment Variables

Create a `.env` file in the project root before deploying:

```env
# ── LLM ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...       # Takes priority over Ollama
OLLAMA_URL=                        # e.g. http://ollama-host:11434
OLLAMA_MODEL=llama3.2:3b

# ── Inference ────────────────────────────────────────────────────────────
FORCE_CPU=false                    # true = disable GPU for PyTorch models
MODELS_DIR=/app/models             # Container-internal path (do not change for Docker)

# ── Server ───────────────────────────────────────────────────────────────
CORS_ORIGINS=https://yourdomain.com  # Comma-separated; use * for open dev only
PORT=8000
```

> **Security:** Never commit `.env` to source control. Use secrets management (Docker secrets, K8s Secrets, Vault) in production.

---

## Docker Compose (Recommended)

### Build and Start

```bash
docker compose up --build -d
```

This builds both images and starts:
- **Backend** on internal port 8000 (mapped to host 8000)
- **Frontend** (Nginx) on port 8080

Open: **http://localhost:8080**

Backend health: **http://localhost:8000/health**

### Stop

```bash
docker compose down
```

### View logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Rebuild a single service

```bash
docker compose up --build backend -d
```

### Production docker-compose overrides

For production, consider creating `docker-compose.prod.yml`:

```yaml
services:
  backend:
    restart: always
    environment:
      CORS_ORIGINS: "https://yourdomain.com"
      FORCE_CPU: "false"
    deploy:
      resources:
        limits:
          memory: 8g

  frontend:
    restart: always
    ports:
      - "80:8080"   # serve on port 80 directly
```

Run with:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Kubernetes

### 1. Build Images

```bash
docker build -t ophthalmoai-backend:latest -f backend/Dockerfile .
docker build -t ophthalmoai-frontend:latest -f frontend/Dockerfile --build-arg VITE_API_URL=/api .
```

For a remote registry (e.g. Docker Hub, GCR, ECR):
```bash
docker tag ophthalmoai-backend:latest your-registry/ophthalmoai-backend:v1.0.0
docker push your-registry/ophthalmoai-backend:v1.0.0
```

Update `image:` fields in `k8s/backend-deployment.yaml` and `k8s/frontend-deployment.yaml` to reference your registry.

### 2. Configure Secrets

```bash
# Create secrets from .env values (do not use the example file in production)
kubectl create namespace ophthalmoai

kubectl create secret generic ophthalmoai-secrets \
  --namespace ophthalmoai \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Apply Manifests

```bash
kubectl apply -k k8s
```

### 4. Monitor Rollout

```bash
kubectl -n ophthalmoai rollout status deployment/backend
kubectl -n ophthalmoai rollout status deployment/frontend
kubectl -n ophthalmoai get pods,svc,ingress
```

Expected output:
```
NAME                            READY   STATUS    RESTARTS
pod/backend-xxx                 1/1     Running   0
pod/frontend-xxx                1/1     Running   0
pod/frontend-yyy                1/1     Running   0
```

### 5. Local Cluster (no DNS / Ingress)

```bash
kubectl -n ophthalmoai port-forward svc/frontend 8080:80
```

Open: **http://localhost:8080**

### 6. GPU Node Scheduling (optional)

To pin the backend to a GPU node, add to `k8s/backend-deployment.yaml`:

```yaml
spec:
  template:
    spec:
      nodeSelector:
        accelerator: nvidia-tesla-t4    # match your node label
      containers:
        - name: backend
          resources:
            limits:
              nvidia.com/gpu: 1
```

And remove `FORCE_CPU: "true"` from the ConfigMap.

---

## Nginx Configuration Notes

The production frontend Nginx config (`frontend/nginx.conf`) handles:

| Path | Behaviour |
|------|-----------|
| `/api/*` | Proxied to `http://backend:8000/` (strips `/api` prefix) |
| `/healthz` | Returns 200 `ok` (used by Kubernetes readiness probe) |
| `/*` | Serves SPA — falls back to `index.html` for client-side routing |
| `*.js, *.css, *.png, ...` | Served with 30-day cache headers |

**Proxy timeout** is set to 180 s to accommodate long inference requests.

To serve behind a reverse proxy (e.g. Traefik, AWS ALB), ensure `proxy_set_header X-Forwarded-For` and `X-Forwarded-Proto` headers are forwarded correctly.

---

## Model Management

The backend Docker image **copies `models/` at build time** (see `backend/Dockerfile` line: `COPY models /app/models`).

### Workflow for updating models

1. Re-train locally: `python scripts/train_*.py`
2. Rebuild the backend image: `docker compose build backend`
3. Redeploy: `docker compose up -d backend`

### Using a volume mount (development / staging)

To avoid rebuilding the image on every training run, mount models as a volume:

```yaml
# docker-compose.override.yml
services:
  backend:
    volumes:
      - ./models:/app/models:ro
```

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

> **Warning:** Do not use volume mounts in Kubernetes production — bake models into the image for immutable deployments.

---

## Health Checks & Monitoring

### Endpoints

| Endpoint | Type | Returns |
|----------|------|---------|
| `GET /health` | Liveness | `{ "ok": true, "device": "cuda" }` |
| `GET /ready` | Readiness | `{ "ok": true/false, "router_loaded": bool }` — 503 if not ready |

### Docker Compose health check

Defined in `docker-compose.yml`. The frontend waits for `backend` to be healthy before starting:

```yaml
depends_on:
  backend:
    condition: service_healthy
```

### Kubernetes probes

Configured in `k8s/backend-deployment.yaml`:
- **readinessProbe:** `GET /ready` — starts after 60 s, retries 6×
- **livenessProbe:** `GET /health` — starts after 90 s

### Recommended monitoring stack

- **Prometheus + Grafana** for request rates, latency, GPU utilisation
- **Loki** for log aggregation from Docker/K8s
- **Sentry** (add `sentry-sdk` to `requirements.txt`) for backend error tracking

---

## Security Hardening

| Area | Recommendation |
|------|---------------|
| `CORS_ORIGINS` | Set to your exact domain(s) — never use `*` in production |
| API Key | Store in K8s Secrets or Docker secrets — never in ConfigMaps or images |
| Container user | Backend and frontend both run as non-root (`appuser` / `nginx`) |
| `readOnlyRootFilesystem` | Set to `false` for backend (temp files); `true` for frontend |
| Rate limiting | Add `slowapi` to backend for `/predict` and `/chat` endpoints |
| HTTPS | Terminate TLS at the load balancer or Nginx; use Let's Encrypt |
| Image scanning | Run `docker scout cves` or `trivy image` on both images before pushing |
| Dependency updates | Run `pip-audit` and `npm audit` regularly |

---

## Performance Tuning

### Backend

| Setting | Default | Tuning |
|---------|---------|--------|
| `OMP_NUM_THREADS` | 4 | Match physical CPU cores |
| `FORCE_CPU` | false | Set true only if GPU is unavailable |
| Uvicorn workers | 1 | Increase for CPU-only; keep 1 for GPU (model is not thread-safe without locking) |
| Image quality (heatmap) | JPEG 85 | Reduce to 70 for faster uploads |

### Frontend

| Setting | Impact |
|---------|--------|
| `VITE_API_URL` pointing to CDN/LB | Reduces latency |
| Nginx `gzip` compression | Add to `nginx.conf` for text assets |
| Nginx caching headers | Already set to 30 days for static assets |

---

## Upgrading

### Backend only

```bash
docker compose build backend
docker compose up -d backend
```

### Full stack

```bash
git pull origin main
docker compose up --build -d
```

### Kubernetes rolling update

```bash
# After pushing new image to registry
kubectl -n ophthalmoai set image deployment/backend \
  backend=your-registry/ophthalmoai-backend:v1.1.0

kubectl -n ophthalmoai rollout status deployment/backend
```

To roll back:
```bash
kubectl -n ophthalmoai rollout undo deployment/backend
```
