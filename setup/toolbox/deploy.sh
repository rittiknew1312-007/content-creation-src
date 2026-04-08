#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-mcp-work-491605}"
REGION="${REGION:-us-central1}"
PROJECT_NUMBER="${PROJECT_NUMBER:-$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')}"
IMAGE="${IMAGE:-us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest}"

echo "Using project: $PROJECT_ID"
echo "Using region: $REGION"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  secretmanager.googleapis.com

gcloud iam service-accounts create toolbox-identity \
  --project "$PROJECT_ID" || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:toolbox-identity@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:toolbox-identity@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/alloydb.client"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com" \
  --role="roles/compute.networkUser"

gcloud secrets create toolbox-tools \
  --data-file=mcp-toolbox/tools.yaml || true

gcloud secrets versions add toolbox-tools \
  --data-file=mcp-toolbox/tools.yaml

if [[ -z "${DB_PASSWORD:-}" ]]; then
  echo "DB_PASSWORD must be set in the shell before running this script."
  exit 1
fi

gcloud run deploy content-ops-toolbox \
  --image "$IMAGE" \
  --service-account "toolbox-identity@${PROJECT_ID}.iam.gserviceaccount.com" \
  --region "$REGION" \
  --network easy-alloydb-vpc \
  --subnet easy-alloydb-subnet \
  --vpc-egress private-ranges-only \
  --set-secrets "/app/tools.yaml=toolbox-tools:latest" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},DB_NAME=content_ops,DB_USER=postgres,DB_PASSWORD=${DB_PASSWORD},ALLOYDB_CLUSTER_ID=my-alloydb-cluster,ALLOYDB_INSTANCE_ID=my-primary-inst" \
  --args="--config=/app/tools.yaml","--address=0.0.0.0","--port=8080","--ui"
