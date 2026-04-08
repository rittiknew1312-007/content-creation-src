# MCP Toolbox Deployment

This document describes how to deploy MCP Toolbox for Databases to Cloud Run for the current project.

It is based on the official Cloud Run deployment guidance for MCP Toolbox and adapted to the current AlloyDB setup.

References:

- [Deploy to Cloud Run](https://googleapis.github.io/genai-toolbox/how-to/deploy_toolbox/)
- [AlloyDB for PostgreSQL source docs](https://googleapis.github.io/genai-toolbox/resources/sources/alloydb-pg/)

## Current Environment

- project: `mcp-work-491605`
- region: `us-central1`
- vpc: `easy-alloydb-vpc`
- subnet: `easy-alloydb-subnet`
- AlloyDB cluster: `my-alloydb-cluster`
- AlloyDB instance: `my-primary-inst`
- database: `content_ops`

## Files Used

- [`mcp-toolbox/tools.yaml`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/mcp-toolbox/tools.yaml)
- [`setup/toolbox/deploy.sh`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/toolbox/deploy.sh)

## 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  secretmanager.googleapis.com
```

## 2. Create a service account for Toolbox

```bash
export PROJECT_ID="mcp-work-491605"

gcloud iam service-accounts create toolbox-identity \
  --project "$PROJECT_ID"
```

If it already exists, continue.

## 3. Grant Secret Manager access to the service account

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:toolbox-identity@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 4. Grant AlloyDB access permissions to the service account

For AlloyDB-backed Toolbox sources, grant AlloyDB Client:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:toolbox-identity@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/alloydb.client"
```

## 5. Grant VPC access permission to the Cloud Run service agent if needed

You already needed this for the API service. Keep it if not already granted:

```bash
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com" \
  --role="roles/compute.networkUser"
```

## 6. Store `tools.yaml` in Secret Manager

Create the secret:

```bash
gcloud secrets create toolbox-tools \
  --data-file=mcp-toolbox/tools.yaml
```

If the secret already exists, add a new version:

```bash
gcloud secrets versions add toolbox-tools \
  --data-file=mcp-toolbox/tools.yaml
```

## 7. Deploy Toolbox to Cloud Run

Use the published Toolbox image:

```bash
export IMAGE="us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest"
```

Deploy:

```bash
gcloud run deploy content-ops-toolbox \
  --image "$IMAGE" \
  --service-account "toolbox-identity@${PROJECT_ID}.iam.gserviceaccount.com" \
  --region us-central1 \
  --network easy-alloydb-vpc \
  --subnet easy-alloydb-subnet \
  --vpc-egress private-ranges-only \
  --set-secrets "/app/tools.yaml=toolbox-tools:latest" \
  --set-env-vars GOOGLE_CLOUD_PROJECT=mcp-work-491605,GOOGLE_CLOUD_LOCATION=us-central1,DB_NAME=content_ops,DB_USER=postgres,DB_PASSWORD=YOUR_PASSWORD,ALLOYDB_CLUSTER_ID=my-alloydb-cluster,ALLOYDB_INSTANCE_ID=my-primary-inst \
  --args="--config=/app/tools.yaml","--address=0.0.0.0","--port=8080","--ui"
```

Replace `YOUR_PASSWORD`.

Notes:

- Toolbox uses the mounted secret file `/app/tools.yaml`.
- AlloyDB source settings are supplied through environment variables referenced inside `tools.yaml`.
- `--config` is preferred over the deprecated `--tools-file`.
- `--ui` is enabled, but the bundled UI may show `404` for `/api/toolset/` in the current image.

## Current Recommendation

Use Toolbox as a backend service:

- keep `type: alloydb-postgres`
- keep the newer working image
- do not block on the bundled UI
- connect ADK directly to the Toolbox service URL

## 8. Optional: restrict host/origin after first successful deploy

After the first working deploy, you can redeploy with:

- `--allowed-hosts`
- `--allowed-origins`

That tightens security against DNS rebinding and cross-origin misuse.

## 9. Validate the Toolbox deployment

After deploy, open:

- `https://YOUR_TOOLBOX_URL/`

The root route should respond, and logs should show initialized tools and toolsets.

Expected toolsets:

- `orchestrator_toolset`
- `research_toolset`
- `review_toolset`
- `calendar_toolset`

## 10. What comes next

Once Toolbox is deployed and reachable:

1. confirm Toolbox is running
2. scaffold the ADK agents
3. wire the agents to the Toolbox endpoint
4. add Google Workspace MCP for the `Calendar Agent`
