#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-mcp-work-491605}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-content-ops-workspace}"

echo "Using project: $PROJECT_ID"
echo "Using region: $REGION"
echo "Using service: $SERVICE_NAME"

required_vars=(
  GOOGLE_WORKSPACE_CLIENT_ID
  GOOGLE_WORKSPACE_CLIENT_SECRET
  GOOGLE_WORKSPACE_REFRESH_TOKEN
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "$var_name must be set before running this script."
    exit 1
  fi
done

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "SERVICE_TARGET=workspace_service,GOOGLE_WORKSPACE_CLIENT_ID=${GOOGLE_WORKSPACE_CLIENT_ID},GOOGLE_WORKSPACE_CLIENT_SECRET=${GOOGLE_WORKSPACE_CLIENT_SECRET},GOOGLE_WORKSPACE_REFRESH_TOKEN=${GOOGLE_WORKSPACE_REFRESH_TOKEN},GOOGLE_WORKSPACE_TOKEN_URI=${GOOGLE_WORKSPACE_TOKEN_URI:-https://oauth2.googleapis.com/token},GOOGLE_CALENDAR_ID=${GOOGLE_CALENDAR_ID:-primary},GOOGLE_WORKSPACE_SERVICE_AUTH_TOKEN=${GOOGLE_WORKSPACE_SERVICE_AUTH_TOKEN:-}"

echo
echo "Hosted Gmail + Calendar service deployed."
echo "Set WORKSPACE_SERVICE_URL on the ADK app to the deployed Cloud Run URL."
echo "Set WORKSPACE_SERVICE_AUTH_TOKEN on the ADK app if you configured one above."
