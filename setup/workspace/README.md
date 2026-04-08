# Gmail + Calendar Service Deployment

This repo now uses a small hosted service for only the Google operations needed by the `calendar_agent`:

- list calendars
- list events
- create calendar event
- update calendar event
- send Gmail message

## Service Files

- [`workspace_service/main.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/workspace_service/main.py)
- [`workspace_service/google_clients.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/workspace_service/google_clients.py)
- [`workspace_service/config.py`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/workspace_service/config.py)
- [`workspace_service/Dockerfile`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/workspace_service/Dockerfile)
- [`setup/workspace/deploy.sh`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/workspace/deploy.sh)

## Required Environment Variables On The Hosted Service

- `GOOGLE_WORKSPACE_CLIENT_ID`
- `GOOGLE_WORKSPACE_CLIENT_SECRET`
- `GOOGLE_WORKSPACE_REFRESH_TOKEN`
- `GOOGLE_WORKSPACE_TOKEN_URI`
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_WORKSPACE_SERVICE_AUTH_TOKEN`

## Required Environment Variables On The ADK App

- `WORKSPACE_SERVICE_URL`
- `WORKSPACE_SERVICE_AUTH_TOKEN`

## Endpoints

- `GET /healthz`
- `GET /calendar/calendars`
- `GET /calendar/events`
- `POST /calendar/events`
- `PATCH /calendar/events/{event_id}`
- `POST /gmail/send`

## Deployment Flow

1. Obtain a Google OAuth refresh token for the Google account that will own Calendar and Gmail actions.
2. Deploy the service to Cloud Run with [`setup/workspace/deploy.sh`](/Users/rittik.basumerckgroup.com/Documents/content-creation-src/setup/workspace/deploy.sh).
3. Set `WORKSPACE_SERVICE_URL` on the ADK app to the deployed service URL.
4. Set `WORKSPACE_SERVICE_AUTH_TOKEN` on both services if you want a simple bearer check.
5. Re-deploy `content-ops-api`.
6. Verify:
   - `/workspace-config-check`
   - `/readiness`

## Recommended First-Pass Values

- `GOOGLE_CALENDAR_ID=primary`
- `WORKSPACE_SERVICE_AUTH_TOKEN` set to a shared random string

## Important Implementation Note

This service uses the OAuth `refresh_token` to obtain fresh access tokens server-side. The ADK app never talks to Google directly; it only talks to this hosted service.
