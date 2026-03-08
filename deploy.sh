#!/bin/bash
set -e

# Configuration
API_SERVICE="house-of-accusations-api"
API_SOURCE="api"
API_PORT="8080"

UI_SERVICE="house-of-accusations-web"
UI_SOURCE="web"
UI_PORT="3000"

REGION="us-east1"

SEPARATOR="=================================================="

# Check dependencies
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed." >&2
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ "$PROJECT_ID" == "(unset)" ]] || [[ -z "$PROJECT_ID" ]]; then
    echo "Error: No Google Cloud Project ID set." >&2
    exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "$SEPARATOR"
echo "DEPLOYMENT CONFIGURATIONS"
echo "$SEPARATOR"
echo "Project: $PROJECT_ID ($PROJECT_NUMBER)"
echo "Region:  $REGION"
echo "API:     $API_SERVICE ($API_SOURCE)"
echo "UI:      $UI_SERVICE ($UI_SOURCE)"
echo "$SEPARATOR"

# Enable required services
echo "Enabling required Google Cloud APIs..."
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com \
    --project "$PROJECT_ID" --quiet

# Define Service Accounts
API_SA="house-of-accusations-api@$PROJECT_ID.iam.gserviceaccount.com"
UI_SA="house-of-accusations-web@$PROJECT_ID.iam.gserviceaccount.com"

# Load env vars
if [[ -f ".env" ]]; then
    set -a
    # shellcheck disable=SC1091
    . ".env"
    set +a
fi

# ==========================================
# Deployment Function
# ==========================================
deploy_service() {
    local service_name=$1
    local source_dir=$2
    local port=$3
    local service_account=$4
    local env_vars=$5

    echo ""
    echo "--- Deploying $service_name ---"

    # 1. Ensure Artifact Registry Repo exists
    if ! gcloud artifacts repositories describe "$service_name" \
            --location="$REGION" --project "$PROJECT_ID" --quiet &>/dev/null; then
        echo "Creating Artifact Registry repository: $service_name..."
        gcloud artifacts repositories create "$service_name" \
            --repository-format=docker \
            --location="$REGION" \
            --project "$PROJECT_ID" \
            --description="Docker repository for $service_name"
    fi

    # 2. Build and Push Image
    local image_uri="$REGION-docker.pkg.dev/$PROJECT_ID/$service_name/$service_name:latest"
    echo "Building: $image_uri"

    gcloud beta builds submit --tag "$image_uri" "$source_dir" --project "$PROJECT_ID"

    # 3. Deploy to Cloud Run
    echo "Deploying to Cloud Run..."

    DEPLOY_ARGS=(
        "deploy" "$service_name"
        "--image" "$image_uri"
        "--region" "$REGION"
        "--project" "$PROJECT_ID"
        "--allow-unauthenticated"
        "--port" "$port"
    )

    if [[ -n "$service_account" ]]; then
        DEPLOY_ARGS+=("--service-account" "$service_account")
    fi

    if [[ -n "$env_vars" ]]; then
        DEPLOY_ARGS+=("--set-env-vars" "$env_vars")
    fi

    if [[ "$service_name" = "$UI_SERVICE" ]]; then
        DEPLOY_ARGS+=("--cpu-boost")
    fi

    gcloud run "${DEPLOY_ARGS[@]}"
    return 0
}

# ==========================================
# Execution
# ==========================================

# 1. Deploy API
deploy_service "$API_SERVICE" "$API_SOURCE" "$API_PORT" "$API_SA"

# 2. Get API URL
API_URL=$(gcloud run services describe "$API_SERVICE" \
    --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')
if [[ -z "$API_URL" ]]; then
    echo "Error: Failed to resolve API_URL from Cloud Run service '$API_SERVICE'." >&2
    exit 1
fi
echo "API URL: $API_URL"

# 3. Deploy UI
deploy_service "$UI_SERVICE" "$UI_SOURCE" "$UI_PORT" "$UI_SA"

echo ""
echo "$SEPARATOR"
echo "DEPLOYMENT COMPLETE"
echo "$SEPARATOR"
