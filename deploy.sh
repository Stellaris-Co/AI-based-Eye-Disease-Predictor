#!/usr/bin/env bash
# infra/azure/deploy.sh
# Full OphthalmoAI Azure deployment using Azure Container Apps.
# Compatible with the GitHub Student Developer Pack ($100 Azure credit).
#
# Usage:
#   export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
#   export GEMINI_API_KEY="your-gemini-key"
#   export PG_PASSWORD="YourStr0ng!Pass"
#   bash infra/azure/deploy.sh
#
# Optional overrides (set before running):
#   export AZURE_RG="my-resource-group"
#   export AZURE_LOCATION="westeurope"
#   export AZURE_ACR="myCRName"

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}"; }

: "${JWT_SECRET_KEY:?Please set JWT_SECRET_KEY (run: python -c \"import secrets; print(secrets.token_hex(32))\")}"
: "${GEMINI_API_KEY:?Please set GEMINI_API_KEY (get from aistudio.google.com/app/apikey)}"
: "${PG_PASSWORD:?Please set PG_PASSWORD (strong password for PostgreSQL admin)}"

RG="${AZURE_RG:-ophthalmoai-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
SUFFIX="${AZURE_SUFFIX:-$(tr -dc 'a-z0-9' </dev/urandom | head -c 6)}"
ACR_NAME="${AZURE_ACR:-ophthalmoaiacr${SUFFIX}}"
APP_ENV="ophthalmoai-env"
BACKEND_APP="ophthalmoai-backend"
FRONTEND_APP="ophthalmoai-frontend"
PG_SERVER="${AZURE_PG:-ophthalmoaipg${SUFFIX}}"
LOG_WORKSPACE="ophthalmoai-logs"

step "Preflight checks"
command -v az     >/dev/null || die "Azure CLI not found. Install: https://aka.ms/InstallAzureCLIDeb"
command -v docker >/dev/null || die "Docker not found. Install Docker Desktop."

[ -f "models/router.pth" ]              || die "models/router.pth not found. Run train_router.py first."
[ -f "models/specialist_anterior.pth" ] || die "models/specialist_anterior.pth not found."
[ -f "models/specialist_surface.pth" ]  || die "models/specialist_surface.pth not found."

az account show >/dev/null 2>&1 || die "Not logged in to Azure. Run: az login"

SUBSCRIPTION=$(az account show --query "[name, id]" -o tsv | tr '\t' ' / ')
info "Azure subscription: $SUBSCRIPTION"
info "Resource group   : $RG"
info "Location         : $LOCATION"
info "ACR name         : $ACR_NAME"
echo ""
read -r -p "Continue with these settings? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }

az extension add --name containerapp --upgrade --yes >/dev/null 2>&1
az provider register --namespace Microsoft.App --wait >/dev/null 2>&1
az provider register --namespace Microsoft.OperationalInsights --wait >/dev/null 2>&1

step "1/9 — Resource group"
az group create --name "$RG" --location "$LOCATION" -o none
success "Resource group '$RG' ready"

step "2/9 — Log Analytics workspace"
az monitor log-analytics workspace create \
  --resource-group "$RG" --workspace-name "$LOG_WORKSPACE" \
  --location "$LOCATION" -o none

LOG_WS_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RG" --workspace-name "$LOG_WORKSPACE" \
  --query customerId -o tsv)
LOG_WS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RG" --workspace-name "$LOG_WORKSPACE" \
  --query primarySharedKey -o tsv)
success "Log Analytics workspace ready"

step "3/9 — Container Apps environment"
az containerapp env create \
  --name "$APP_ENV" --resource-group "$RG" --location "$LOCATION" \
  --logs-workspace-id "$LOG_WS_ID" --logs-workspace-key "$LOG_WS_KEY" -o none
success "Container Apps environment '$APP_ENV' ready"

step "4/9 — Azure Container Registry"
az acr create \
  --name "$ACR_NAME" --resource-group "$RG" \
  --sku Basic --admin-enabled true -o none

ACR_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USER=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASS=$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)
success "ACR '$ACR_SERVER' ready"

step "5/9 — Build and push Docker images"
info "Logging in to ACR..."
docker login "$ACR_SERVER" -u "$ACR_USER" -p "$ACR_PASS" >/dev/null 2>&1

info "Building backend image (this may take 3–5 minutes)..."
docker build \
  -t "$ACR_SERVER/ophthalmoai-backend:latest" \
  -f backend/Dockerfile \
  .
docker push "$ACR_SERVER/ophthalmoai-backend:latest"
success "Backend image pushed"

info "Building frontend image..."
docker build \
  -t "$ACR_SERVER/ophthalmoai-frontend:latest" \
  -f frontend/Dockerfile \
  --build-arg VITE_API_URL=/api \
  .
docker push "$ACR_SERVER/ophthalmoai-frontend:latest"
success "Frontend image pushed"

step "6/9 — PostgreSQL Flexible Server (this takes ~5 min)"
az postgres flexible-server create \
  --name "$PG_SERVER" --resource-group "$RG" --location "$LOCATION" \
  --admin-user ophthalmo --admin-password "$PG_PASSWORD" \
  --sku-name Standard_B1ms --tier Burstable --version 16 \
  --storage-size 32 --public-access 0.0.0.0 -o none

az postgres flexible-server db create \
  --server-name "$PG_SERVER" --resource-group "$RG" \
  --database-name ophthalmoai -o none

PG_HOST=$(az postgres flexible-server show \
  --name "$PG_SERVER" --resource-group "$RG" \
  --query fullyQualifiedDomainName -o tsv)
success "PostgreSQL server at $PG_HOST"

DATABASE_URL="postgresql://ophthalmo:${PG_PASSWORD}@${PG_HOST}:5432/ophthalmoai?sslmode=require"

step "7/9 — Backend Container App"
az containerapp create \
  --name "$BACKEND_APP" --resource-group "$RG" --environment "$APP_ENV" \
  --image "$ACR_SERVER/ophthalmoai-backend:latest" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 3 \
  --cpu 1.0 --memory 2.0Gi \
  --secrets \
    jwt-secret-key="$JWT_SECRET_KEY" \
    gemini-api-key="$GEMINI_API_KEY" \
    database-url="$DATABASE_URL" \
  --env-vars \
    ENVIRONMENT=production \
    FORCE_CPU=true \
    PORT=8000 HOST=0.0.0.0 \
    MODELS_DIR=/app/models \
    MAX_FILE_SIZE_BYTES=20971520 \
    PREDICT_RATE_LIMIT="10/minute" \
    CHAT_RATE_LIMIT="30/minute" \
    LOG_FORMAT=json \
    GEMINI_MODEL=gemini-2.0-flash \
    JWT_SECRET_KEY=secretref:jwt-secret-key \
    GEMINI_API_KEY=secretref:gemini-api-key \
    DATABASE_URL=secretref:database-url \
  -o none

BACKEND_URL=$(az containerapp show \
  --name "$BACKEND_APP" --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)
success "Backend deployed at https://$BACKEND_URL"

step "8/9 — Frontend Container App"
az containerapp create \
  --name "$FRONTEND_APP" --resource-group "$RG" --environment "$APP_ENV" \
  --image "$ACR_SERVER/ophthalmoai-frontend:latest" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
  --target-port 8080 --ingress external \
  --min-replicas 1 --max-replicas 2 \
  --cpu 0.5 --memory 1.0Gi \
  -o none

FRONTEND_URL=$(az containerapp show \
  --name "$FRONTEND_APP" --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)
success "Frontend deployed at https://$FRONTEND_URL"

step "9/9 — Update CORS settings"
az containerapp update \
  --name "$BACKEND_APP" --resource-group "$RG" \
  --set-env-vars "CORS_ORIGINS=https://$FRONTEND_URL" \
  -o none
success "CORS updated with frontend URL"

cat > infra/azure/deployed-config.env <<EOF
# Generated by infra/azure/deploy.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT commit this file — it contains sensitive references
AZURE_RG=$RG
AZURE_LOCATION=$LOCATION
AZURE_ACR=$ACR_NAME
ACR_SERVER=$ACR_SERVER
ACR_USERNAME=$ACR_USER
BACKEND_APP=$BACKEND_APP
FRONTEND_APP=$FRONTEND_APP
PG_SERVER=$PG_SERVER
PG_HOST=$PG_HOST
LOG_WORKSPACE=$LOG_WORKSPACE
BACKEND_URL=https://$BACKEND_URL
FRONTEND_URL=https://$FRONTEND_URL
EOF
warn "Config saved to infra/azure/deployed-config.env — add this file to .gitignore!"

echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN} ✅  OphthalmoAI successfully deployed to Azure!${NC}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e " ${BOLD}Frontend${NC}  : https://$FRONTEND_URL"
echo -e " ${BOLD}Backend${NC}   : https://$BACKEND_URL"
echo -e " ${BOLD}Health${NC}    : https://$BACKEND_URL/health"
echo -e " ${BOLD}Swagger${NC}   : (disabled in production)"
echo ""
echo -e " ${BOLD}Next steps:${NC}"
echo "  1. Open https://$FRONTEND_URL in your browser"
echo "  2. Run: curl https://$BACKEND_URL/health"
echo "  3. Add GitHub Actions secrets (see AZURE_DEPLOY.md §10)"
echo "  4. Set a cost alert (see AZURE_DEPLOY.md §12)"
echo ""
echo -e " ${YELLOW}Tip:${NC} Stop PostgreSQL when not in use to save credit:"
echo "  az postgres flexible-server stop --name $PG_SERVER --resource-group $RG"
echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════${NC}"
