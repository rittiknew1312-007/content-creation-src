# AlloyDB Setup

This document describes the exact setup path for provisioning AlloyDB and loading the current project schema.

It assumes:

- you are using Cloud Shell
- you have billing enabled
- you want a fast hackathon path first
- you may temporarily enable public IP for initial SQL loading

## Files Used

- [`db/schema.sql`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/db/schema.sql)
- [`db/seed.sql`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/db/seed.sql)
- [`setup/alloydb/ai_setup.sql`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/alloydb/ai_setup.sql)
- [`mcp-toolbox/tools.yaml`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/mcp-toolbox/tools.yaml)
- [`.env.example`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/.env.example)

## Recommended Initial Values

Use one region consistently. For hackathon speed, use `us-central1` unless you already know quota is blocked there.

Suggested IDs:

- project: your existing Google Cloud project
- region: `us-central1`
- network: `default`
- cluster: `content-ops-cluster`
- primary instance: `content-ops-primary`
- database: `content_ops`
- db user: `postgres`

## 1. Set environment variables in Cloud Shell

```bash
export PROJECT_ID="YOUR_PROJECT_ID"
export REGION="us-central1"
export NETWORK="default"
export CLUSTER_ID="content-ops-cluster"
export INSTANCE_ID="content-ops-primary"
export DB_NAME="content_ops"
export DB_PASSWORD="CHANGE_ME_STRONG_PASSWORD"
export MY_IP="$(curl -s https://api.ipify.org)/32"

gcloud config set project "$PROJECT_ID"
```

## 2. Enable required APIs

```bash
gcloud services enable \
  alloydb.googleapis.com \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  servicenetworking.googleapis.com \
  aiplatform.googleapis.com
```

## 3. Create the AlloyDB cluster

Official references:

- [AlloyDB quickstart](https://docs.cloud.google.com/alloydb/docs/quickstart/create-and-connect)
- [gcloud alloydb clusters create](https://docs.cloud.google.com/sdk/gcloud/reference/alloydb/clusters/create)

```bash
gcloud alloydb clusters create "$CLUSTER_ID" \
  --region="$REGION" \
  --password="$DB_PASSWORD" \
  --network="projects/$PROJECT_ID/global/networks/$NETWORK"
```

Notes:

- This creates the cluster and configures private networking.
- If the command asks you to set up private services access first in your environment, use the console quickstart once, or create the private connection in the console and rerun.

## 4. Create the primary instance

Official references:

- [gcloud alloydb instances create](https://docs.cloud.google.com/sdk/gcloud/reference/alloydb/instances/create)
- [Connect using public IP](https://docs.cloud.google.com/alloydb/docs/connect-public-ip)

For initial setup and schema loading, you can temporarily allow public IP:

```bash
gcloud alloydb instances create "$INSTANCE_ID" \
  --cluster="$CLUSTER_ID" \
  --region="$REGION" \
  --instance-type=PRIMARY \
  --cpu-count=2 \
  --availability-type=ZONAL \
  --assign-inbound-public-ip=TRUE \
  --authorized-external-networks="$MY_IP"
```

Important:

- this is for hackathon setup speed
- later, for Cloud Run deployment, use private IP connectivity and remove broad public access

## 5. Create the application database

Use AlloyDB Studio in the console:

1. Open the cluster.
2. Open `AlloyDB Studio`.
3. Authenticate as `postgres`.
4. Run:

```sql
CREATE DATABASE content_ops;
```

## 6. Load schema and seed data

Still in AlloyDB Studio, switch to the `content_ops` database and run:

```sql
\i db/schema.sql
```

If AlloyDB Studio does not support `\i`, copy-paste the contents of:

- [`db/schema.sql`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/db/schema.sql)
- [`db/seed.sql`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/db/seed.sql)

Run the schema first, then the seed.

## 7. Enable Vertex AI integration for AlloyDB AI features

Official references:

- [Integrate with Vertex AI](https://cloud.google.com/alloydb/docs/ai/configure-vertex-ai)
- [Generate text embeddings](https://docs.cloud.google.com/alloydb/docs/ai/work-with-embeddings)

Get your project number and grant the AlloyDB service agent access to Vertex AI:

```bash
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Wait a minute or two for IAM propagation if needed.

## 8. Enable AI-related extensions and permissions

In AlloyDB Studio, connected to the `content_ops` database, run:

```sql
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
GRANT EXECUTE ON FUNCTION embedding TO postgres;
```

Or run the file:

- [`setup/alloydb/ai_setup.sql`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/alloydb/ai_setup.sql)

## 9. Optional: register a Gemini model endpoint in AlloyDB

If you want in-database LLM calls later, update the placeholder in `ai_setup.sql` and run the registration block.

This is optional for the current project phase because the current schema and MCP tools do not require model registration yet.

## 10. Capture connection details for the app and MCP Toolbox

In the instance Connectivity page, collect:

- public IP for initial development if you enabled it
- private IP for Cloud Run deployment later
- port, usually `5432`

Populate your real `.env` from [`.env.example`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/.env.example):

```env
DB_HOST=ALLOYDB_HOST
DB_PORT=5432
DB_NAME=content_ops
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
```

## 11. Validate the loaded schema

Run these in AlloyDB Studio:

```sql
SELECT * FROM creator_profiles;
SELECT * FROM brand_guidelines;
SELECT * FROM campaigns;
```

You should see the seeded demo rows.

## 12. What to do after setup

Once AlloyDB is ready:

1. run MCP Toolbox against [`mcp-toolbox/tools.yaml`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/mcp-toolbox/tools.yaml)
2. scaffold the ADK agents
3. wire the agents to the database toolsets
4. add Google Workspace MCP for the `Calendar Agent`

## Security cleanup after initial setup

After local validation:

- remove or narrow public IP access
- keep only your IP if still needed
- prefer private IP for Cloud Run
- avoid leaving `0.0.0.0/0` authorized
