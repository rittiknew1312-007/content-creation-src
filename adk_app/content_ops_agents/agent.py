import os

from google.adk.agents import Agent, LoopAgent, SequentialAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .tools import (
    get_calendar_tools,
    get_content_creator_tools,
    get_orchestrator_tools,
    get_research_tools,
    get_review_tools,
    get_workspace_tools,
)

orchestrator_tools = get_orchestrator_tools()
research_tools = get_research_tools()
content_creator_tools = get_content_creator_tools()
review_tools = get_review_tools()
calendar_tools = get_calendar_tools() + get_workspace_tools()
DEFAULT_CREATOR_ID = os.getenv(
    "DEFAULT_CREATOR_ID", "11111111-1111-1111-1111-111111111111"
)
ADK_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
ADK_RETRY_ATTEMPTS = int(os.getenv("ADK_RETRY_ATTEMPTS", "3"))
ADK_RETRY_INITIAL_DELAY_SECONDS = float(os.getenv("ADK_RETRY_INITIAL_DELAY_SECONDS", "1"))
FAST_MODE = os.getenv("FAST_MODE", "0").lower() in {"1", "true", "yes"}
ADK_GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=ADK_RETRY_INITIAL_DELAY_SECONDS,
            attempts=ADK_RETRY_ATTEMPTS,
        )
    )
)
PROCEDURAL_CALENDAR = os.getenv("PROCEDURAL_CALENDAR", "1").lower() in {"1", "true", "yes"}


def remember_campaign(campaign_id: str, tool_context: ToolContext) -> str:
    tool_context.state["campaign_id"] = campaign_id
    tool_context.state.setdefault("creator_id", DEFAULT_CREATOR_ID)
    return f"Remembered campaign_id={campaign_id}"


def remember_brief(brief_id: str, tool_context: ToolContext) -> str:
    tool_context.state["brief_id"] = brief_id
    return f"Remembered brief_id={brief_id}"


def remember_draft(draft_id: str, tool_context: ToolContext) -> str:
    tool_context.state["draft_id"] = draft_id
    tool_context.state["review_status"] = "pending"
    return f"Remembered draft_id={draft_id}"


def remember_schedule_job(schedule_job_id: str, tool_context: ToolContext) -> str:
    tool_context.state["schedule_job_id"] = schedule_job_id
    return f"Remembered schedule_job_id={schedule_job_id}"


def seed_default_creator(callback_context):
    callback_context.state.setdefault("creator_id", DEFAULT_CREATOR_ID)
    return None


def mark_review_approved(tool_context: ToolContext) -> str:
    tool_context.state["review_status"] = "approved"
    tool_context.state["required_changes"] = ""
    tool_context.actions.escalate = True
    return "Review marked approved. Exiting revision loop."


def mark_review_rejected(required_changes: str, tool_context: ToolContext) -> str:
    tool_context.state["review_status"] = "rejected"
    tool_context.state["required_changes"] = required_changes
    return "Review marked rejected. Revision required."


def research_instruction(ctx: ReadonlyContext) -> str:
    campaign_id = ctx.state.get("campaign_id", "")
    creator_id = ctx.state.get("creator_id", DEFAULT_CREATOR_ID)
    fast_mode_note = ""
    if FAST_MODE:
        fast_mode_note = """
Fast mode is enabled.
Keep the research output extremely short:
- one trend summary sentence
- one audience insight sentence
- one hook suggestion sentence
Use the fewest tool calls needed to do that.
Do not produce long analysis.
"""
    return f"""
You are the research specialist in a multi-agent content workflow.

Current campaign_id in session state: {campaign_id}
Current creator_id in session state: {creator_id}

Use the available tools to:
- inspect campaign context using the current campaign_id
- inspect recent campaigns for the current creator_id if needed
- inspect brand guidelines for the current creator_id if available
- prepare a concise research summary, audience insight, and creative angle

{fast_mode_note}

When you have enough context, persist the brief using the research brief tool.
Immediately after saving it, call remember_brief with the saved brief ID.
Never ask the user for campaign_id or creator_id. Use the values already in session state.
Do not invent campaign identifiers or creator data.
Always return the saved brief ID after persisting.
"""


def creator_instruction(ctx: ReadonlyContext) -> str:
    campaign_id = ctx.state.get("campaign_id", "")
    brief_id = ctx.state.get("brief_id", "")
    creator_id = ctx.state.get("creator_id", DEFAULT_CREATOR_ID)
    required_changes = ctx.state.get("required_changes", "")
    revision_note = ""
    if required_changes:
        revision_note = f"""
This is a revision pass. You must address these required changes:
{required_changes}
"""
    fast_mode_note = ""
    if FAST_MODE:
        fast_mode_note = """
Fast mode is enabled.
Create one concise draft only.
Prefer:
- a short text-first caption suitable for a LinkedIn post
- a script of at most 2 short lines
- a one-line visual prompt
- one short platform note
Keep the total draft compact.
If the platform is LinkedIn, optimize for a text post first, not a video script.
Do not create variants.
"""
    return f"""
You are the content creation specialist in a multi-agent content workflow.

Current campaign_id in session state: {campaign_id}
Current brief_id in session state: {brief_id}
Current creator_id in session state: {creator_id}

Use the available tools to:
- inspect campaign context using the current campaign_id
- inspect the latest research brief
- inspect brand guidelines

Recovery rules if session state is incomplete:
- if campaign_id is missing, use list_recent_campaigns_for_creator with creator_id and select the most recent relevant campaign
- once you have a campaign_id, use get_latest_research_brief to recover the latest brief if brief_id is missing
- do not ask the user for campaign_id or brief_id unless recovery fails completely

{fast_mode_note}

Then create a draft suitable for the target platform.
The draft should include:
- caption
- script
- visual prompt
- platform notes

{revision_note}

Persist the generated draft using the available draft creation tool.
Immediately after saving it, call remember_draft with the saved draft ID.
Never ask the user for campaign_id or brief_id. Use the values already in session state.
Do not invent campaign IDs or brief IDs. Use tool outputs.
Always return the saved draft ID after persisting.
"""


def review_instruction(ctx: ReadonlyContext) -> str:
    campaign_id = ctx.state.get("campaign_id", "")
    draft_id = ctx.state.get("draft_id", "")
    creator_id = ctx.state.get("creator_id", DEFAULT_CREATOR_ID)
    fast_mode_note = ""
    if FAST_MODE:
        fast_mode_note = """
Fast mode is enabled.
Keep the review very lightweight:
- approve if the draft is broadly clear, on-brand, and safe
- only reject for obvious issues
- do not over-edit
- keep the response to one short decision plus required changes if any
- do not rewrite the draft during review
"""
    return f"""
You are the review specialist in a multi-agent content workflow.

Current campaign_id in session state: {campaign_id}
Current draft_id in session state: {draft_id}
Current creator_id in session state: {creator_id}

Use the available tools to:
- inspect campaign context
- inspect the latest draft
- inspect brand guidelines

Recovery rules if session state is incomplete:
- if campaign_id is missing, use list_recent_campaigns_for_creator with creator_id and select the most recent relevant campaign
- if draft_id is missing, use get_latest_draft_for_campaign with the recovered or current campaign_id
- do not ask the user for campaign_id or draft_id unless recovery fails completely

Then review the draft for:
- brand fit
- tone consistency
- clarity
- safety and compliance

{fast_mode_note}

Always persist your review using the available review tool.
If approved:
- save a review result with approved=true
- update the draft status to approved
- update the campaign status to approved
- call mark_review_approved

If changes are needed:
- save a review result with approved=false
- include concrete required changes
- update the draft status to changes_requested
- update the campaign status to rejected
- call mark_review_rejected with the required changes

Do not invent draft IDs or campaign IDs. Use tool outputs.
Never ask the user for campaign_id, brief_id, or draft_id. Use session state and tool outputs.
Return a concise summary of the review decision.
Your response must clearly state:
- APPROVED or REJECTED
- the draft ID
- any required changes if rejected
"""


def calendar_instruction(ctx: ReadonlyContext) -> str:
    campaign_id = ctx.state.get("campaign_id", "")
    return f"""
You are the scheduling specialist in a multi-agent content workflow.

Current campaign_id in session state: {campaign_id}

Use the available tools to:
- inspect approved unscheduled drafts with list_approved_unscheduled_content
- inspect campaign context with get_campaign_context
- create the database scheduling record with create_schedule_job
- persist external scheduling state with update_schedule_job
- update campaign status with update_campaign_status when scheduling is complete
- use direct workspace service tools list_calendars, list_events, create_event, update_event, and send_email for Google Calendar and Gmail actions

The scheduled time must come from the user input.
Use the user-provided scheduled time exactly as given.
Do not calculate dates or times in Python.
Do not write Python snippets, pseudo-code, or simulated tool calls.
If scheduled time is missing, stop and ask the user to provide it.

Required execution order:
1. Select the approved draft to schedule from list_approved_unscheduled_content.
2. Create the initial schedule record with create_schedule_job using the user-provided scheduled time and channel.
3. Immediately call remember_schedule_job with the saved schedule job ID.
4. Create the Google Calendar event with create_event. Use list_calendars or list_events first only if needed for lookup or conflict checks.
5. Call update_schedule_job with schedule_status set to scheduled and the returned calendar_event_id.
6. Send the Gmail confirmation or reminder email with send_email if an email target is available or implied by the workflow.
7. If the email is sent successfully, call update_schedule_job again with schedule_status set to sent.
8. Call update_campaign_status with status set to scheduled.

If the Google Calendar event creation fails after the schedule job exists:
- call update_schedule_job with schedule_status set to failed
- do not mark the campaign as scheduled

When calling workspace service tools:
- use the exact direct tool names shown above
- capture the returned event identifier from the calendar tool output
- include the scheduled time, campaign title, and draft summary in the email content
- if you need to modify an existing event, use update_event
- call tools directly with structured arguments only

Return the schedule job ID and the chosen scheduled time.
"""


def skip_calendar_if_not_approved(callback_context):
    if callback_context.state.get("review_status") != "approved":
        required_changes = callback_context.state.get("required_changes", "")
        message = "Scheduling skipped because the content is not approved."
        if required_changes:
            message += f" Latest required changes: {required_changes}"
        from google.genai import types

        return types.Content(role="model", parts=[types.Part(text=message)])
    return None


research_agent = Agent(
    model=ADK_MODEL,
    name="research_agent",
    description="Researches campaign context and persists a structured research brief.",
    instruction=research_instruction,
    generate_content_config=ADK_GENERATE_CONTENT_CONFIG,
    tools=research_tools + [remember_brief],
)

content_creator_agent = Agent(
    model=ADK_MODEL,
    name="content_creator_agent",
    description="Creates the first content draft from the campaign brief and persists it.",
    instruction=creator_instruction,
    generate_content_config=ADK_GENERATE_CONTENT_CONFIG,
    tools=content_creator_tools + [remember_draft],
)

review_agent = Agent(
    model=ADK_MODEL,
    name="review_agent",
    description="Reviews the latest draft for quality, brand fit, and persistence of review state.",
    instruction=review_instruction,
    generate_content_config=ADK_GENERATE_CONTENT_CONFIG,
    tools=review_tools + [mark_review_approved, mark_review_rejected],
)

calendar_agent = Agent(
    model=ADK_MODEL,
    name="calendar_agent",
    description="Creates a scheduling record for approved content.",
    instruction=calendar_instruction,
    generate_content_config=ADK_GENERATE_CONTENT_CONFIG,
    tools=calendar_tools + [remember_schedule_job],
    before_agent_callback=skip_calendar_if_not_approved,
)

campaign_manager_agent = Agent(
    model=ADK_MODEL,
    name="campaign_manager_agent",
    description="Creates campaign workflow state from the user's request.",
    generate_content_config=ADK_GENERATE_CONTENT_CONFIG,
    instruction=f"""
You are the campaign initialization specialist.

Use creator_id `{DEFAULT_CREATOR_ID}` unless the user explicitly provides a different creator ID.

Use the available tools to:
- create a campaign from the user's request
- immediately call remember_campaign with the saved campaign ID
- return the created campaign ID clearly

The create_campaign tool requires these fields:
- creator_id
- title
- topic
- objective
- target_platform
- posting_cadence
- source_image_url
- source_image_gcs_uri
- orchestrator_notes

Populate them as follows:
- creator_id: use `{DEFAULT_CREATOR_ID}` unless a different one is explicitly provided
- title: derive a short campaign title from the topic
- source_image_url: use an empty string if none was provided
- source_image_gcs_uri: use an empty string if none was provided
- orchestrator_notes: use a short summary of the user's request

Do not stop to ask the user for campaign title or source image fields unless they are explicitly required for the creative task. Empty strings are acceptable for missing image fields.

Do not invent UUIDs or workflow state. Use tool outputs and persist state through tools.
""",
    tools=orchestrator_tools + [remember_campaign],
    before_agent_callback=seed_default_creator,
)

draft_review_loop = LoopAgent(
    name="draft_review_loop",
    description="Repeats draft creation and review until approved or attempts are exhausted.",
    sub_agents=[content_creator_agent, review_agent],
    max_iterations=1,
)

root_agent = SequentialAgent(
    name="orchestrator_agent",
    description="Runs the content workflow in a fixed sequence from one user prompt.",
    sub_agents=[
        campaign_manager_agent,
        research_agent,
        draft_review_loop,
    ] + ([] if PROCEDURAL_CALENDAR else [calendar_agent]),
)
