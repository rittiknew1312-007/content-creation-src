# Google Workspace MCP Integration

This project uses a dedicated Google Workspace MCP server for:

- Gmail
- Google Calendar

These integrations should not be implemented as SQL tools in MCP Toolbox.

## Why Separate It

`mcp-toolbox/tools.yaml` is for database-backed tools.

Gmail and Calendar are external operational systems, so they belong in a separate MCP server layer that the `Calendar Agent` can call directly.

## Recommended Server Choice

Use the Google Workspace MCP server/extension referenced by the Google MCP repository.

Reference:

- Google MCP repository lists Google Workspace as an open-source MCP server category:
  [google/mcp](https://github.com/google/mcp)
- Google Workspace Gemini CLI extension repository:
  [gemini-cli-extensions/workspace](https://github.com/gemini-cli-extensions/workspace)

## Intended Agent Usage

The `Calendar Agent` should combine:

1. `calendar_toolset` from MCP Toolbox
   - approved drafts waiting to be scheduled
   - scheduling queue state
   - campaign context

2. Google Workspace MCP tools
  - list calendars
  - list events
  - create event
  - update event
  - send email
  - read or search relevant emails when needed

## Deployment Model

For this repo, prefer a hosted Workspace MCP service instead of a local MCP process.

- deploy the Google Workspace MCP server as its own Cloud Run service
- expose a Streamable HTTP endpoint such as `/mcp`
- configure the ADK app to connect to that hosted endpoint

The ADK app now expects these environment variables:

- `WORKSPACE_MCP_URL`
  Full hosted MCP endpoint, for example `https://your-workspace-mcp-service.run.app/mcp`
- `WORKSPACE_MCP_AUTH_TOKEN`
  Optional bearer token sent by the ADK app when calling the Workspace MCP service
- `WORKSPACE_MCP_LIST_CALENDARS_TOOL`
  Exact deployed MCP tool name for calendar listing
- `WORKSPACE_MCP_LIST_EVENTS_TOOL`
  Exact deployed MCP tool name for event listing
- `WORKSPACE_MCP_CREATE_EVENT_TOOL`
  Exact deployed MCP tool name for event creation
- `WORKSPACE_MCP_UPDATE_EVENT_TOOL`
  Exact deployed MCP tool name for event updates
- `WORKSPACE_MCP_SEND_EMAIL_TOOL`
  Exact deployed MCP tool name for Gmail send

The ADK app derives its MCP tool filter from those configured names, so the prompt and the exposed tools stay aligned.

This keeps the first implementation narrow and focused on scheduling plus notification flows.

## Suggested Tool Boundaries

Use database tools for:

- finding approved unscheduled drafts
- reading campaign cadence
- storing scheduling metadata
- tracking schedule status

Use Workspace MCP for:

- creating Google Calendar reminder events
- updating or cancelling reminders
- sending approval reminders or content notifications through Gmail

## OAuth / Scopes

Minimum expected scopes:

- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.readonly`

Use least privilege if your chosen Workspace MCP server supports narrower scope selection.

## Integration Plan

When the ADK layer is added, the `Calendar Agent` should be wired to both:

- the Toolbox `calendar_toolset`
- the Workspace MCP server connection

The operational flow should be:

1. Load approved unscheduled content from the database.
2. Compute the target schedule time from cadence and creator timezone.
3. Create or update the corresponding Google Calendar event.
4. Send reminder or confirmation email through Gmail if required.
5. Persist the resulting `calendar_event_id` and delivery state into `schedule_jobs`.

That wiring is now started in the ADK app:

- Toolbox database tools remain in `calendar_toolset`
- hosted Workspace MCP tools are loaded separately and merged into `calendar_agent`

Next implementation step after server deployment:

1. set the five `WORKSPACE_MCP_*_TOOL` variables to match the actual hosted Workspace MCP server
2. verify those tool names exist on the deployed server
3. persist `calendar_event_id` and email delivery state through the existing schedule job update path

## Current ADK Scheduling Flow

The `calendar_agent` is now instructed to use this sequence:

1. `list_approved_unscheduled_content`
2. `create_schedule_job`
3. `remember_schedule_job`
4. Workspace Calendar event creation
5. `update_schedule_job(schedule_status="scheduled", calendar_event_id=...)`
6. Workspace Gmail send
7. `update_schedule_job(schedule_status="sent")`
8. `update_campaign_status(status="scheduled")`

Failure handling currently expected:

- if Calendar event creation fails after the database job is created, mark the schedule job as `failed`
- do not mark the campaign as `scheduled` unless the Calendar step succeeds

This gives you a clean hosted control path:

- AlloyDB remains the source of workflow truth
- Google Calendar returns the external event identifier
- Gmail remains an operational notification step layered on top

## Notes

- Keep Gmail/Calendar actions behind the `Calendar Agent` only.
- Do not give broad Workspace access to every agent.
- The orchestrator should delegate calendar/email actions instead of calling them directly.
