# Multi-Agent Content Ops

Foundation for a Google ADK multi-agent content orchestration system.

This first cut focuses on:

- shared database setup for campaign memory and workflow state
- MCP Toolbox configuration for database-backed tools
- hosted Gmail and Google Calendar integration service
- Cloud Run validation service for AlloyDB connectivity
- environment templates for local development and Cloud Run

## Architecture Scope

The system is designed around:

- `Orchestrator Agent`
- `Research Agent`
- `Content Creator Agent`
- `Content Review Agent`
- `Calendar Agent`

Shared state is stored in AlloyDB for PostgreSQL. For local development, the schema is standard PostgreSQL-compatible except for the `vector` extension, which is expected in AlloyDB or pgvector-enabled Postgres.

## Repo Layout

- `db/schema.sql`
  Base schema, indexes, and workflow tables.
- `db/seed.sql`
  Optional starter data for local validation.
- `mcp-toolbox/tools.yaml`
  MCP Toolbox configuration for database-backed tools.
- `.env.example`
  Environment variables used by toolbox and the future ADK/FastAPI app.

## Database Setup

Apply the schema against AlloyDB or PostgreSQL:

```sql
\i db/schema.sql
\i db/seed.sql
```

If you are using AlloyDB:

- enable `vector`
- keep the database in the same region as Cloud Run
- use a private IP for deployed workloads

## MCP Layers

This project uses two MCP capability layers:

- `mcp-toolbox/tools.yaml`
  Database-backed tools for campaign memory, drafts, reviews, and scheduling queues.
- `workspace_service/`
  Hosted Gmail and Calendar service used by the `Calendar Agent`.

The intended runtime split is:

- `Research Agent`, `Review Agent`, and `Orchestrator Agent`
  primarily use the database toolsets.
- `Calendar Agent`
  uses both:
  - database toolsets for approved content and schedule queues
  - hosted Gmail and Calendar service tools for scheduling actions

## MCP Toolbox Setup

Install Toolbox and run it with:

```bash
toolbox --tools-file mcp-toolbox/tools.yaml
```

The configuration uses environment variables from `.env.example`.

For transient Vertex AI capacity errors (`429 RESOURCE_EXHAUSTED`), the API layer supports retry settings:

- `WORKFLOW_MAX_RETRIES`
- `WORKFLOW_RETRY_BASE_DELAY_SECONDS`
- `WORKFLOW_RETRY_MAX_DELAY_SECONDS`
- `ADK_RETRY_ATTEMPTS`
- `ADK_RETRY_INITIAL_DELAY_SECONDS`
- `GEMINI_LOCATION`

These control truncated exponential backoff for workflow execution retries.
Set `GEMINI_LOCATION=global` if you want model requests to use the Vertex AI global endpoint while keeping the rest of the application on its existing infrastructure region.

For AlloyDB, the source is configured as an AlloyDB-native Toolbox source using:

- `type: alloydb-postgres`
- `ipType: private`
- `project`, `region`, `cluster`, and `instance`

This matches the current environment:

- project: `mcp-work-491605`
- region: `us-central1`
- cluster: `my-alloydb-cluster`
- instance: `my-primary-inst`

## Initial Toolsets

- `research_toolset`
  Brand context, campaign retrieval, and research brief persistence.
- `review_toolset`
  Draft creation, review persistence, and review queue access.
- `calendar_toolset`
  Scheduling queue, approved content retrieval, and schedule-job persistence from the database.
- `orchestrator_toolset`
  Cross-workflow lookup tools plus campaign lifecycle creation and status updates.

## Gmail + Calendar Service

For Gmail and Calendar, use a small hosted service instead of trying to model those as SQL tools.

The recommended direction is:

- keep database reads/writes in MCP Toolbox
- use a separate hosted service for:
  - listing calendar events
  - creating calendar events
  - updating calendar events
  - sending scheduling notifications

See:

- [`setup/workspace/README.md`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/workspace/README.md)
- [`setup/workspace/deploy.sh`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/workspace/deploy.sh)
- [`workspace_service/main.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/workspace_service/main.py)

This separation keeps the architecture clean:

- Toolbox for structured data
- hosted service for Gmail/Calendar actions

## Workflow Mutations

The database toolsets now support the minimum write path needed for the MVP:

- `create_campaign`
- `update_campaign_status`
- `create_research_brief`
- `create_draft`
- `update_draft_status`
- `create_review_result`
- `create_schedule_job`
- `update_schedule_job`

Expected flow:

1. `Orchestrator Agent` creates a campaign.
2. `Research Agent` saves the research brief.
3. `Content Creator Agent` saves a new draft version.
4. `Content Review Agent` saves a review result and updates draft/campaign status.
5. `Calendar Agent` creates a schedule job, then updates it after Google Calendar event creation.

## Next Step

After this foundation, the next implementation step is:

1. ADK app scaffold
2. agent definitions
3. FastAPI workflow endpoints

## Cloud Run Validation Service

This repo now includes a minimal FastAPI app to validate Cloud Run to AlloyDB connectivity before the full multi-agent implementation is added.

Files:

- [`app/main.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/app/main.py)
- [`app/db.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/app/db.py)
- [`requirements.txt`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/requirements.txt)
- [`Dockerfile`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/Dockerfile)

Endpoints:

- `/healthz`
- `/config-check`
- `/db-check`
- `/workspace-config-check`
- `/readiness`

Deploy with Direct VPC egress so Cloud Run can reach the AlloyDB private IP:

```bash
gcloud run deploy content-ops-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --network easy-alloydb-vpc \
  --vpc-egress private-ranges-only \
  --set-env-vars DB_HOST=10.21.0.8,DB_PORT=5432,DB_NAME=content_ops,DB_USER=postgres,DB_PASSWORD=YOUR_PASSWORD,GOOGLE_CLOUD_PROJECT=mcp-work-491605,GOOGLE_CLOUD_LOCATION=us-central1,TOOLBOX_URL=https://YOUR_TOOLBOX_URL,WORKSPACE_SERVICE_URL=https://YOUR_WORKSPACE_SERVICE_URL,WORKSPACE_SERVICE_AUTH_TOKEN=YOUR_SHARED_TOKEN
```

If your VPC requires a specific subnet for Direct VPC egress, add:

```bash
--subnet YOUR_SUBNET_NAME
```

After deploy:

- open `/healthz`
- open `/config-check`
- open `/db-check`
- open `/workspace-config-check`
- open `/readiness`

Expected validation sequence for hosted deployment:

1. `/config-check` shows the base DB and service URLs.
2. `/db-check` confirms AlloyDB connectivity.
3. `/workspace-config-check` confirms the hosted Gmail + Calendar service URL is present.
4. `/readiness` returns `ok` only when the hosted service configuration is complete.

Current Cloud Run VPC guidance:

- [Direct VPC egress](https://cloud.google.com/run/docs/configuring/vpc-direct-vpc)

## MCP Toolbox Deployment

Toolbox deployment files are included here:

- [`setup/toolbox/README.md`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/toolbox/README.md)
- [`setup/toolbox/deploy.sh`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/toolbox/deploy.sh)

This deploy path:

- uses a pinned Toolbox Cloud Run container image
- mounts `mcp-toolbox/tools.yaml` from Secret Manager
- connects to AlloyDB over private IP in the same VPC

The bundled Toolbox UI may show `404` for `/api/toolset/` in the current image. Treat Toolbox as a backend service and connect ADK directly to it.

## Workspace Service Deployment

Hosted Gmail + Calendar service deployment files are included here:

- [`setup/workspace/README.md`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/workspace/README.md)
- [`setup/workspace/deploy.sh`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/workspace/deploy.sh)

Use these to deploy the hosted Gmail + Calendar service, then set `WORKSPACE_SERVICE_URL` on the ADK app to the deployed Cloud Run URL.

## ADK App

A minimal ADK app scaffold is included:

- [`adk_app/content_ops_agents/agent.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/adk_app/content_ops_agents/agent.py)
- [`adk_app/content_ops_agents/tools.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/adk_app/content_ops_agents/tools.py)
- [`adk_app/.env.example`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/adk_app/.env.example)

Current agents:

- `orchestrator_agent`
- `research_agent`
- `content_creator_agent`
- `review_agent`
- `calendar_agent`

The ADK app is wired to the deployed Toolbox backend:

- `https://content-ops-toolbox-972348605933.us-central1.run.app`

Suggested run flow:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp adk_app/.env.example adk_app/.env
cd adk_app
adk run content_ops_agents/
```
