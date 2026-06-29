# AZURE_DEPLOY.md — Hosting OphthalmoAI on Azure
## Using the GitHub Student Developer Pack

This guide takes you from zero to a live, production-grade OphthalmoAI deployment on
Microsoft Azure using the **GitHub Student Developer Pack** free credit ($100 Azure
credit + free-tier services). Every command is copy-pasteable.

---

## Table of Contents

1. [What You'll Get](#1-what-youll-get)
2. [Costs & Credit Estimate](#2-costs--credit-estimate)
3. [Prerequisites](#3-prerequisites)
4. [Step 1 — Activate Your Azure Student Credit](#4-step-1--activate-your-azure-student-credit)
5. [Step 2 — Install Tools](#5-step-2--install-tools)
6. [Step 3 — Prepare the Codebase](#6-step-3--prepare-the-codebase)
7. [Step 4 — Provision Azure Resources (CLI)](#7-step-4--provision-azure-resources-cli)
8. [Step 5 — Build & Push Docker Images](#8-step-5--build--push-docker-images)
9. [Step 6 — Deploy Azure Container Apps](#9-step-6--deploy-azure-container-apps)
10. [Step 7 — Configure Environment Variables & Secrets](#10-step-7--configure-environment-variables--secrets)
11. [Step 8 — Set Up the Database (PostgreSQL Flexible Server)](#11-step-8--set-up-the-database-postgresql-flexible-server)
12. [Step 9 — Verify the Deployment](#12-step-9--verify-the-deployment)
13. [Step 10 — Configure GitHub Actions CD Pipeline](#13-step-10--configure-github-actions-cd-pipeline)
14. [Step 11 — Custom Domain & HTTPS (Optional)](#14-step-11--custom-domain--https-optional)
15. [Step 12 — Monitoring & Logs](#15-step-12--monitoring--logs)
16. [Automated One-Click Deployment Script](#16-automated-one-click-deployment-script)
17. [Tear Down / Stop Billing](#17-tear-down--stop-billing)
18. [Troubleshooting Azure Issues](#18-troubleshooting-azure-issues)

---

## 1. What You'll Get

| Resource | Azure Service | Purpose |
|----------|--------------|---------|
| Backend API | Azure Container Apps | FastAPI + PyTorch inference (CPU) |
| Frontend | Azure Container Apps | React/Nginx SPA |
| Container Registry | Azure Container Registry (Basic) | Docker image store |
| Database | Azure Database for PostgreSQL Flexible Server (Burstable B1ms) | Persistent scan results, users, audit log |
| Secrets | Azure Container Apps Secrets | API keys, JWT secret, DB password |
| Logs | Azure Log Analytics | Structured log aggregation |
| CI/CD | GitHub Actions | Auto-rebuild on push to `main` |
| HTTPS | Azure Container Apps built-in | Automatic TLS certificate |

---

## 2. Costs & Credit Estimate

| Service | SKU | Est. monthly cost |
|---------|-----|------------------|
| Container Apps — Backend | Consumption (0.5 vCPU / 1 GB, ~720 hrs) | ~$12 |
| Container Apps — Frontend | Consumption (0.25 vCPU / 0.5 GB, ~720 hrs) | ~$6 |
| Container Registry | Basic | $5 |
| PostgreSQL Flexible Server | Burstable B1ms (1 vCPU / 2 GB RAM) | ~$12 |
| Log Analytics Workspace | Pay-per-GB (minimal ingestion) | ~$2 |
| **Total** | | **~$37/month** |

The $100 Azure for Students credit covers roughly **2–3 months** of full operation. After credit exhaustion, switch to the Azure free tier or pause resources.

> **Tip:** Stop the PostgreSQL server when not actively using the app — it accrues charges when idle. Container Apps in Consumption mode scale to zero automatically and cost nothing when idle.

---

## 3. Prerequisites

Before starting, confirm you have:

- [ ] A GitHub account enrolled in the **GitHub Student Developer Pack** (verify at [education.github.com](https://education.github.com/pack))
- [ ] Your repository pushed to GitHub (public or private)
- [ ] Trained model files in `models/` (`router.pth`, `specialist_anterior.pth`, `specialist_surface.pth`)
- [ ] Docker Desktop installed and running locally
- [ ] A Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com/app/apikey)) **or** an Ollama endpoint
- [ ] `git` installed

---

## 4. Step 1 — Activate Your Azure Student Credit

### 4.1 Claim via GitHub Student Developer Pack

1. Go to [education.github.com/pack](https://education.github.com/pack)
2. Sign in with your GitHub student account
3. Find **Microsoft Azure** in the pack list
4. Click **Get access** → you'll be redirected to Azure
5. Sign in with a **Microsoft account** (create one free if needed — use your `.edu` email)
6. Complete the Azure for Students sign-up — you'll see **$100 credit** applied

### 4.2 Verify the credit

```bash
# After installing the Azure CLI (Step 2), run:
az account show
az consumption budget list --all   # or check portal.azure.com → Cost Management
```

### 4.3 Alternative — Azure for Students directly

If you don't see Azure in your pack, go to:
**[azure.microsoft.com/free/students](https://azure.microsoft.com/free/students)**

Sign in with your `.edu` email. No credit card required.

---

## 5. Step 2 — Install Tools

### Azure CLI

**Windows (PowerShell as Admin):**
```powershell
winget install Microsoft.AzureCLI
```

**macOS:**
```bash
brew install azure-cli
```

**Linux (Ubuntu/Debian):**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Verify install & login
```bash
az --version          # should show 2.60+
az login              # opens browser for Microsoft account login
az account set --subscription "Azure for Students"
```

### Install Container Apps extension
```bash
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

---

## 6. Step 3 — Prepare the Codebase

### 3.1 Generate a JWT secret
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Copy the output — you'll need it in Step 7
```

### 3.2 Set ENVIRONMENT in .env
```bash
cp .env.example .env
```

Edit `.env`:
```env
ENVIRONMENT=production
JWT_SECRET_KEY=<your-32-byte-hex-from-above>
GEMINI_API_KEY=<your-gemini-key>
CORS_ORIGINS=https://<your-app>.azurecontainerapps.io
CORS_ALLOW_CREDENTIALS=false
DATABASE_URL=postgresql://ophthalmo:<db-password>@<pg-host>:5432/ophthalmoai
```

> You'll fill in `<your-app>` and `<pg-host>` after running Step 4.

### 3.3 Create a resource group name

Pick a short name — you'll use it throughout:
```bash
export RG="ophthalmoai-rg"
export LOCATION="eastus"              # pick the nearest region
export ACR_NAME="ophthalmoaiacr$RANDOM"   # must be globally unique
export APP_ENV="ophthalmoai-env"
export BACKEND_APP="ophthalmoai-backend"
export FRONTEND_APP="ophthalmoai-frontend"
export PG_SERVER="ophthalmoai-pg-$RANDOM"
export PG_PASSWORD="<strong-password-here>"
export LOG_WORKSPACE="ophthalmoai-logs"
```

> **Windows (PowerShell):** Replace `export VAR=value` with `$env:VAR = "value"` throughout.

---

## 7. Step 4 — Provision Azure Resources (CLI)

Run these commands in order. Each takes 30–120 seconds.

### 4.1 Create the resource group
```bash
az group create \
  --name $RG \
  --location $LOCATION
```

### 4.2 Create the Log Analytics workspace
```bash
az monitor log-analytics workspace create \
  --resource-group $RG \
  --workspace-name $LOG_WORKSPACE \
  --location $LOCATION

LOG_WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group $RG \
  --workspace-name $LOG_WORKSPACE \
  --query customerId -o tsv)

LOG_WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group $RG \
  --workspace-name $LOG_WORKSPACE \
  --query primarySharedKey -o tsv)
```

### 4.3 Create the Container Apps environment
```bash
az containerapp env create \
  --name $APP_ENV \
  --resource-group $RG \
  --location $LOCATION \
  --logs-workspace-id $LOG_WORKSPACE_ID \
  --logs-workspace-key $LOG_WORKSPACE_KEY
```

### 4.4 Create the Azure Container Registry
```bash
az acr create \
  --name $ACR_NAME \
  --resource-group $RG \
  --sku Basic \
  --admin-enabled true

# Store credentials
ACR_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

echo "ACR Server: $ACR_SERVER"
echo "ACR Username: $ACR_USERNAME"
```

---

## 8. Step 5 — Build & Push Docker Images

### 5.1 Login to ACR
```bash
docker login $ACR_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD
```

### 5.2 Build and push the backend image

> Make sure `models/` contains your trained `.pth` files before building.

```bash
docker build \
  -t $ACR_SERVER/ophthalmoai-backend:latest \
  -f backend/Dockerfile \
  .

docker push $ACR_SERVER/ophthalmoai-backend:latest
```

### 5.3 Build and push the frontend image
```bash
docker build \
  -t $ACR_SERVER/ophthalmoai-frontend:latest \
  -f frontend/Dockerfile \
  --build-arg VITE_API_URL=/api \
  .

docker push $ACR_SERVER/ophthalmoai-frontend:latest
```

### 5.4 Verify images in ACR
```bash
az acr repository list --name $ACR_NAME --output table
```

---

## 9. Step 6 — Deploy Azure Container Apps

### 6.1 Deploy the backend Container App

```bash
az containerapp create \
  --name $BACKEND_APP \
  --resource-group $RG \
  --environment $APP_ENV \
  --image $ACR_SERVER/ophthalmoai-backend:latest \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars \
    ENVIRONMENT=production \
    FORCE_CPU=true \
    PORT=8000 \
    HOST=0.0.0.0 \
    MODELS_DIR=/app/models \
    MAX_FILE_SIZE_BYTES=20971520 \
    PREDICT_RATE_LIMIT="10/minute" \
    CHAT_RATE_LIMIT="30/minute" \
    LOG_FORMAT=json

# Get the backend URL
BACKEND_URL=$(az containerapp show \
  --name $BACKEND_APP \
  --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Backend URL: https://$BACKEND_URL"
```

### 6.2 Deploy the frontend Container App

```bash
az containerapp create \
  --name $FRONTEND_APP \
  --resource-group $RG \
  --environment $APP_ENV \
  --image $ACR_SERVER/ophthalmoai-frontend:latest \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8080 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi

FRONTEND_URL=$(az containerapp show \
  --name $FRONTEND_APP \
  --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Frontend URL: https://$FRONTEND_URL"
echo ""
echo "Open your app at: https://$FRONTEND_URL"
```

---

## 10. Step 7 — Configure Environment Variables & Secrets

Set the sensitive values as Container Apps secrets (not plain env vars):

```bash
# Add secrets to the backend
az containerapp secret set \
  --name $BACKEND_APP \
  --resource-group $RG \
  --secrets \
    jwt-secret-key=<YOUR_JWT_SECRET_KEY> \
    gemini-api-key=<YOUR_GEMINI_API_KEY> \
    database-url="postgresql://ophthalmo:${PG_PASSWORD}@${PG_SERVER}.postgres.database.azure.com:5432/ophthalmoai?sslmode=require"

# Reference those secrets as environment variables
az containerapp update \
  --name $BACKEND_APP \
  --resource-group $RG \
  --set-env-vars \
    JWT_SECRET_KEY=secretref:jwt-secret-key \
    GEMINI_API_KEY=secretref:gemini-api-key \
    DATABASE_URL=secretref:database-url \
    CORS_ORIGINS="https://$FRONTEND_URL" \
    CORS_ALLOW_CREDENTIALS=false \
    ENVIRONMENT=production \
    GEMINI_MODEL=gemini-2.0-flash
```

---

## 11. Step 8 — Set Up the Database (PostgreSQL Flexible Server)

### 8.1 Create PostgreSQL Flexible Server

```bash
az postgres flexible-server create \
  --name $PG_SERVER \
  --resource-group $RG \
  --location $LOCATION \
  --admin-user ophthalmo \
  --admin-password $PG_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --public-access 0.0.0.0

# Get the server hostname
PG_HOST=$(az postgres flexible-server show \
  --name $PG_SERVER \
  --resource-group $RG \
  --query fullyQualifiedDomainName -o tsv)

echo "PostgreSQL host: $PG_HOST"
```

### 8.2 Create the database

```bash
az postgres flexible-server db create \
  --server-name $PG_SERVER \
  --resource-group $RG \
  --database-name ophthalmoai
```

### 8.3 Allow the Container Apps environment to connect

```bash
# Get the Container Apps environment's outbound IPs
OUTBOUND_IPS=$(az containerapp env show \
  --name $APP_ENV \
  --resource-group $RG \
  --query properties.staticIp -o tsv)

# Add a firewall rule for each outbound IP
az postgres flexible-server firewall-rule create \
  --name $PG_SERVER \
  --resource-group $RG \
  --rule-name allow-container-apps \
  --start-ip-address $OUTBOUND_IPS \
  --end-ip-address $OUTBOUND_IPS
```

### 8.4 Update the backend DATABASE_URL secret

```bash
az containerapp secret set \
  --name $BACKEND_APP \
  --resource-group $RG \
  --secrets \
    database-url="postgresql://ophthalmo:${PG_PASSWORD}@${PG_HOST}:5432/ophthalmoai?sslmode=require"
```

> The SQLAlchemy `create_tables()` call in `backend/db.py` runs at startup and creates all tables automatically via `Base.metadata.create_all()`. No migration scripts needed for initial deployment.

---

## 12. Step 9 — Verify the Deployment

```bash
# Health check — should return {"ok": true, "device": "cpu"}
curl https://$BACKEND_URL/health

# Readiness check — should return {"ok": true} once models are loaded
curl https://$BACKEND_URL/ready

# System status
curl https://$BACKEND_URL/ | python3 -m json.tool

# Open the frontend
echo "Open: https://$FRONTEND_URL"
```

### Expected health response:
```json
{
  "ok": true,
  "device": "cpu"
}
```

### Expected root response:
```json
{
  "status": "OphthalmoAI System Ready",
  "device": "cpu",
  "router_loaded": true,
  "specialists_loaded": 3,
  "chat_backend": "Google Gemini (gemini-2.0-flash)",
  "version": "2.1.0"
}
```

> **If `router_loaded` is `false`:** The models weren't copied into the Docker image. Verify `models/router.pth` exists before `docker build`, then rebuild and push.

---

## 13. Step 10 — Configure GitHub Actions CD Pipeline

This sets up automatic deploy on every push to `main`.

### 10.1 Add GitHub repository secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|-------------|-------|
| `AZURE_CLIENT_ID` | from service principal (below) |
| `AZURE_CLIENT_SECRET` | from service principal (below) |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |
| `ACR_SERVER` | your ACR login server (e.g. `ophthalmoaiacr12345.azurecr.io`) |
| `ACR_USERNAME` | your ACR admin username |
| `ACR_PASSWORD` | your ACR admin password |
| `RESOURCE_GROUP` | `ophthalmoai-rg` |
| `BACKEND_APP_NAME` | `ophthalmoai-backend` |
| `FRONTEND_APP_NAME` | `ophthalmoai-frontend` |

### 10.2 Create a service principal for GitHub Actions

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az ad sp create-for-rbac \
  --name "ophthalmoai-github-actions" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG \
  --json-auth
```

Copy the entire JSON output. From it, extract:
- `clientId` → `AZURE_CLIENT_ID` secret
- `clientSecret` → `AZURE_CLIENT_SECRET` secret
- `tenantId` → `AZURE_TENANT_ID` secret

### 10.3 The CD pipeline file

The file `.github/workflows/azure-deploy.yml` is included in this repository. It:

1. Logs into Azure using the service principal
2. Builds both Docker images with `docker build`
3. Pushes to ACR
4. Runs `az containerapp update` to deploy the new image

After adding the secrets, every `git push origin main` triggers a deployment.

---

## 14. Step 11 — Custom Domain & HTTPS (Optional)

Azure Container Apps provides automatic HTTPS on the default `*.azurecontainerapps.io` domain. To use your own domain:

```bash
# 1. Add a custom domain to the frontend app
az containerapp hostname add \
  --name $FRONTEND_APP \
  --resource-group $RG \
  --hostname yourdomain.com

# 2. Bind a managed certificate (free)
az containerapp hostname bind \
  --name $FRONTEND_APP \
  --resource-group $RG \
  --hostname yourdomain.com \
  --certificate-name ophthalmoai-cert \
  --validation-method CNAME

# 3. Update your DNS: add a CNAME record pointing yourdomain.com to $FRONTEND_URL
```

After DNS propagation (~5–10 min), `https://yourdomain.com` will serve the app with a free Azure-managed certificate.

---

## 15. Step 12 — Monitoring & Logs

### View live logs

```bash
# Backend logs (last 100 lines, streaming)
az containerapp logs show \
  --name $BACKEND_APP \
  --resource-group $RG \
  --follow \
  --tail 100

# Frontend logs
az containerapp logs show \
  --name $FRONTEND_APP \
  --resource-group $RG \
  --follow \
  --tail 50
```

### Query logs via Azure Monitor (Log Analytics)

In the Azure Portal:
1. Go to your **Log Analytics workspace** → **Logs**
2. Run a KQL query:

```kql
// All backend errors in the last hour
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ophthalmoai-backend"
| where Log_s contains "error" or Log_s contains "ERROR"
| where TimeGenerated > ago(1h)
| project TimeGenerated, Log_s
| order by TimeGenerated desc
```

```kql
// Prediction requests with diagnosis + confidence
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ophthalmoai-backend"
| where Log_s contains "inference.complete"
| extend parsed = parse_json(Log_s)
| project TimeGenerated, diagnosis=parsed.diagnosis, confidence=parsed.confidence
| order by TimeGenerated desc
```

### Set up a cost alert (recommended)

```bash
az consumption budget create \
  --budget-name ophthalmoai-budget \
  --amount 80 \
  --category Cost \
  --time-grain Monthly \
  --resource-group $RG \
  --notifications \
    "enabled=true threshold=80 operator=GreaterThan contactEmails=['you@example.com']" \
    "enabled=true threshold=100 operator=GreaterThan contactEmails=['you@example.com']"
```

---

## 16. Automated One-Click Deployment Script

Save the following as `infra/azure/deploy.sh` and run it **after** training your models:

```bash
#!/usr/bin/env bash
# infra/azure/deploy.sh — Full OphthalmoAI Azure deployment
# Usage: bash infra/azure/deploy.sh
set -euo pipefail

# ─── Configuration ───────────────────────────────────────────
RG="${AZURE_RG:-ophthalmoai-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
ACR_NAME="${AZURE_ACR:-ophthalmoaiacr$(echo $RANDOM | tr '[0-9]' '[a-z]')}"
APP_ENV="ophthalmoai-env"
BACKEND_APP="ophthalmoai-backend"
FRONTEND_APP="ophthalmoai-frontend"
PG_SERVER="ophthalmoai-pg-$(echo $RANDOM)"
LOG_WORKSPACE="ophthalmoai-logs"

: "${JWT_SECRET_KEY:?Set JWT_SECRET_KEY in your environment}"
: "${GEMINI_API_KEY:?Set GEMINI_API_KEY in your environment}"
: "${PG_PASSWORD:?Set PG_PASSWORD in your environment}"

echo "=== OphthalmoAI Azure Deployment ==="
echo "Resource group : $RG"
echo "Location       : $LOCATION"
echo "ACR name       : $ACR_NAME"

# ─── Step 1: Resource group ──────────────────────────────────
echo "[1/9] Creating resource group..."
az group create --name $RG --location $LOCATION -o none

# ─── Step 2: Log Analytics workspace ─────────────────────────
echo "[2/9] Creating Log Analytics workspace..."
az monitor log-analytics workspace create \
  --resource-group $RG --workspace-name $LOG_WORKSPACE \
  --location $LOCATION -o none

LOG_WS_ID=$(az monitor log-analytics workspace show \
  --resource-group $RG --workspace-name $LOG_WORKSPACE \
  --query customerId -o tsv)
LOG_WS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group $RG --workspace-name $LOG_WORKSPACE \
  --query primarySharedKey -o tsv)

# ─── Step 3: Container Apps environment ──────────────────────
echo "[3/9] Creating Container Apps environment..."
az containerapp env create \
  --name $APP_ENV --resource-group $RG --location $LOCATION \
  --logs-workspace-id $LOG_WS_ID --logs-workspace-key $LOG_WS_KEY -o none

# ─── Step 4: Container Registry ──────────────────────────────
echo "[4/9] Creating Container Registry..."
az acr create --name $ACR_NAME --resource-group $RG \
  --sku Basic --admin-enabled true -o none

ACR_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USER=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASS=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# ─── Step 5: Build & push images ─────────────────────────────
echo "[5/9] Building and pushing Docker images..."
docker login $ACR_SERVER -u $ACR_USER -p $ACR_PASS

docker build -t $ACR_SERVER/ophthalmoai-backend:latest -f backend/Dockerfile .
docker push $ACR_SERVER/ophthalmoai-backend:latest

docker build -t $ACR_SERVER/ophthalmoai-frontend:latest \
  -f frontend/Dockerfile --build-arg VITE_API_URL=/api .
docker push $ACR_SERVER/ophthalmoai-frontend:latest

# ─── Step 6: PostgreSQL ──────────────────────────────────────
echo "[6/9] Creating PostgreSQL Flexible Server..."
az postgres flexible-server create \
  --name $PG_SERVER --resource-group $RG --location $LOCATION \
  --admin-user ophthalmo --admin-password $PG_PASSWORD \
  --sku-name Standard_B1ms --tier Burstable --version 16 \
  --storage-size 32 --public-access 0.0.0.0 -o none

az postgres flexible-server db create \
  --server-name $PG_SERVER --resource-group $RG \
  --database-name ophthalmoai -o none

PG_HOST=$(az postgres flexible-server show \
  --name $PG_SERVER --resource-group $RG \
  --query fullyQualifiedDomainName -o tsv)

# ─── Step 7: Deploy backend ───────────────────────────────────
echo "[7/9] Deploying backend Container App..."
az containerapp create \
  --name $BACKEND_APP --resource-group $RG --environment $APP_ENV \
  --image $ACR_SERVER/ophthalmoai-backend:latest \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USER --registry-password $ACR_PASS \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 3 --cpu 1.0 --memory 2.0Gi \
  --secrets \
    jwt-secret-key=$JWT_SECRET_KEY \
    gemini-api-key=$GEMINI_API_KEY \
    database-url="postgresql://ophthalmo:${PG_PASSWORD}@${PG_HOST}:5432/ophthalmoai?sslmode=require" \
  --env-vars \
    ENVIRONMENT=production \
    FORCE_CPU=true PORT=8000 HOST=0.0.0.0 \
    MODELS_DIR=/app/models \
    MAX_FILE_SIZE_BYTES=20971520 \
    PREDICT_RATE_LIMIT="10/minute" CHAT_RATE_LIMIT="30/minute" \
    LOG_FORMAT=json GEMINI_MODEL=gemini-2.0-flash \
    JWT_SECRET_KEY=secretref:jwt-secret-key \
    GEMINI_API_KEY=secretref:gemini-api-key \
    DATABASE_URL=secretref:database-url -o none

BACKEND_URL=$(az containerapp show \
  --name $BACKEND_APP --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

# ─── Step 8: Deploy frontend ──────────────────────────────────
echo "[8/9] Deploying frontend Container App..."
az containerapp create \
  --name $FRONTEND_APP --resource-group $RG --environment $APP_ENV \
  --image $ACR_SERVER/ophthalmoai-frontend:latest \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USER --registry-password $ACR_PASS \
  --target-port 8080 --ingress external \
  --min-replicas 1 --max-replicas 2 --cpu 0.5 --memory 1.0Gi -o none

FRONTEND_URL=$(az containerapp show \
  --name $FRONTEND_APP --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

# ─── Step 9: Update CORS ──────────────────────────────────────
echo "[9/9] Updating CORS with frontend URL..."
az containerapp update \
  --name $BACKEND_APP --resource-group $RG \
  --set-env-vars CORS_ORIGINS="https://$FRONTEND_URL" -o none

# ─── Summary ──────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo " ✅  OphthalmoAI deployed to Azure!"
echo "════════════════════════════════════════════════════════"
echo ""
echo " Frontend  : https://$FRONTEND_URL"
echo " Backend   : https://$BACKEND_URL"
echo " Health    : https://$BACKEND_URL/health"
echo " ACR       : $ACR_SERVER"
echo ""
echo " Next steps:"
echo "  1. Test the health endpoint above"
echo "  2. Add GitHub Actions secrets (see AZURE_DEPLOY.md Step 10)"
echo "  3. Set up cost alerts (see AZURE_DEPLOY.md Step 12)"
echo "════════════════════════════════════════════════════════"
```

Make it executable and run:
```bash
chmod +x infra/azure/deploy.sh

export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export GEMINI_API_KEY="your-gemini-key"
export PG_PASSWORD="YourStr0ng!Pass"

bash infra/azure/deploy.sh
```

---

## 17. Tear Down / Stop Billing

### Pause PostgreSQL (saves ~$0.40/day while not in use)
```bash
az postgres flexible-server stop \
  --name $PG_SERVER \
  --resource-group $RG
```

### Scale Container Apps to zero (Consumption plan already scales automatically)
```bash
az containerapp update \
  --name $BACKEND_APP --resource-group $RG \
  --min-replicas 0 --max-replicas 0
```

### Delete everything (when done)
```bash
az group delete --name $RG --yes --no-wait
```

> This permanently deletes all resources and data in the group. Run `pg_dump` first if you want to keep scan data.

---

## 18. Troubleshooting Azure Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `router_loaded: false` in `/ready` | Models not baked into image | Confirm `models/router.pth` exists before `docker build` |
| `502 Bad Gateway` on frontend | Backend not ready yet | Wait 60–90 s after deploy; check backend logs |
| `CORS error` in browser | `CORS_ORIGINS` missing or wrong | Update backend env var with exact frontend URL |
| `500` on `/predict` with "JWT secret is default placeholder" | `JWT_SECRET_KEY` not set as secret | Run `az containerapp secret set` (Step 7) |
| PostgreSQL connection refused | Firewall rule missing | Add Container Apps outbound IP to PG firewall (Step 8.3) |
| `ProvisioningState: Failed` on Container App | Image not found in ACR | Re-push images; verify ACR credentials in app settings |
| High cost warning | PostgreSQL always running | Stop PG server when not needed (Step 17) |
| `401 Unauthorized` on API calls | JWT not included in request or expired | Confirm frontend is sending `Authorization: Bearer <token>` |
| App cold-start takes 30–60 s | Model loading on first request | Pre-warm with a `/ready` poll; consider min-replicas=1 |

---

## Reference — Useful Azure Commands

```bash
# List all Container Apps
az containerapp list --resource-group $RG --output table

# Restart a Container App (forces fresh model load)
az containerapp revision restart \
  --name $BACKEND_APP --resource-group $RG \
  --revision $(az containerapp revision list --name $BACKEND_APP \
               --resource-group $RG --query "[0].name" -o tsv)

# Update an environment variable without redeploying
az containerapp update \
  --name $BACKEND_APP --resource-group $RG \
  --set-env-vars MY_VAR=new-value

# View current environment variable values
az containerapp show \
  --name $BACKEND_APP --resource-group $RG \
  --query properties.template.containers[0].env

# Check PostgreSQL status
az postgres flexible-server show \
  --name $PG_SERVER --resource-group $RG \
  --query state -o tsv

# Get current cost to date
az consumption usage list \
  --billing-period-name $(date +%Y%m) \
  --query "sum([].pretaxCost)" -o tsv
```
