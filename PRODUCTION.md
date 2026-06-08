# Production Deployment

## Docker Compose

Build and run both services:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

Backend health:

```text
http://localhost:8000/health
```

Useful environment variables:

```text
FORCE_CPU=false
CORS_ORIGINS=*
OLLAMA_URL=
OLLAMA_MODEL=llama3.2:3b
ANTHROPIC_API_KEY=
```

## Kubernetes

Build images:

```bash
docker build -t ophthalmoai-backend:latest -f backend/Dockerfile .
docker build -t ophthalmoai-frontend:latest -f frontend/Dockerfile --build-arg VITE_API_URL=/api .
```

Apply manifests:

```bash
kubectl apply -k k8s
```

Check rollout:

```bash
kubectl -n ophthalmoai rollout status deployment/backend
kubectl -n ophthalmoai rollout status deployment/frontend
kubectl -n ophthalmoai get pods,svc,ingress
```

For a local cluster without ingress DNS:

```bash
kubectl -n ophthalmoai port-forward svc/frontend 8080:80
```

Then open:

```text
http://localhost:8080
```

## Notes

The backend image includes the model files from `models/`. Rebuild and redeploy the backend image after replacing model checkpoints.

The frontend is compiled with `VITE_API_URL=/api`; Nginx proxies `/api` to the backend service.
