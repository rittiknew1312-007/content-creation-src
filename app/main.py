import asyncio
import os
import random
import time
from datetime import datetime, timedelta
from urllib import error, request
from uuid import uuid4

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.db import check_database, engine

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from sqlalchemy import text

app = FastAPI(title="Content Ops API", version="0.1.0")
APP_NAME = "content_ops_api"
session_service = InMemorySessionService()
runner: Runner | None = None
WORKFLOW_TIMEOUT_SECONDS = 120
MAX_WORKFLOW_RETRIES = int(os.getenv("WORKFLOW_MAX_RETRIES", "3"))
RETRY_BASE_DELAY_SECONDS = float(os.getenv("WORKFLOW_RETRY_BASE_DELAY_SECONDS", "5"))
RETRY_MAX_DELAY_SECONDS = float(os.getenv("WORKFLOW_RETRY_MAX_DELAY_SECONDS", "60"))
PROCEDURAL_CALENDAR = os.getenv("PROCEDURAL_CALENDAR", "1").lower() in {"1", "true", "yes"}


class CreatorProfilePayload(BaseModel):
    creator_id: str | None = None
    name: str | None = None
    niche: str | None = None
    tone: str | None = None
    platforms: list[str] = Field(default_factory=list)
    goal: str | None = None


class BrandKitPayload(BaseModel):
    tagline: str | None = None
    bio: str | None = None
    avoid: str | None = None
    pillars: list[str] = Field(default_factory=list)
    capstyle: list[str] = Field(default_factory=list)


class CampaignPayload(BaseModel):
    topic: str
    objective: str
    target_platform: str
    posting_cadence: str
    scheduled_for: str
    reminder_email: str
    title: str | None = None
    source_image_url: str | None = None
    notes: str | None = None


class ContentCampaignRequest(BaseModel):
    creator_profile: CreatorProfilePayload | None = None
    brand_kit: BrandKitPayload | None = None
    campaign: CampaignPayload


def _compact_text(value: str | None, *, limit: int = 120) -> str | None:
    if not value:
        return None
    compact = " ".join(str(value).split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _build_workflow_prompt(payload: ContentCampaignRequest) -> str:
    creator = payload.creator_profile or CreatorProfilePayload()
    brand_kit = payload.brand_kit or BrandKitPayload()
    campaign = payload.campaign

    lines = [
        "Create and run a full content workflow.",
        f"Topic: {campaign.topic}",
        f"Objective: {campaign.objective}",
        f"Target platform: {campaign.target_platform}",
        f"Posting cadence: {campaign.posting_cadence}",
        f"Scheduled time: {campaign.scheduled_for}",
        f"Reminder email: {campaign.reminder_email}",
    ]

    if creator.creator_id:
        lines.append(f"Creator ID: {creator.creator_id}")

    style_bits: list[str] = []
    if creator.tone:
        style_bits.append(f"Tone: {creator.tone}")
    if creator.niche:
        style_bits.append(f"Niche: {creator.niche}")
    if brand_kit.avoid:
        style_bits.append(f"Avoid: {_compact_text(brand_kit.avoid, limit=90)}")
    if style_bits:
        lines.append("Style constraints: " + " | ".join(style_bits))

    notes_bits: list[str] = []
    compact_notes = _compact_text(campaign.notes, limit=120)
    compact_bio = _compact_text(brand_kit.bio, limit=100)
    if compact_notes:
        notes_bits.append(f"Notes: {compact_notes}")
    if compact_bio:
        notes_bits.append(f"Brand context: {compact_bio}")
    if notes_bits:
        lines.extend(notes_bits)

    lines.append(
        "Use the provided scheduled time and reminder email exactly. Do not invent missing dates, times, or email addresses."
    )
    lines.append(
        "Keep each step concise. Minimize unnecessary analysis, revisions, and repeated explanations."
    )
    return "\n".join(lines)


def _is_retryable_resource_exhausted(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "resource_exhausted" in message
        or "429" in message
        or "resource exhausted" in message
    )


def _retry_delay_seconds(attempt: int) -> float:
    # Truncated exponential backoff with light jitter for shared-capacity bursts.
    raw_delay = min(
        RETRY_BASE_DELAY_SECONDS * (2 ** attempt),
        RETRY_MAX_DELAY_SECONDS,
    )
    return raw_delay * random.uniform(0.8, 1.2)


def _workspace_request(method: str, path: str, payload: dict | None = None) -> dict:
    if not settings.workspace_service_url:
        raise ValueError("WORKSPACE_SERVICE_URL is not configured.")
    headers = {"Content-Type": "application/json"}
    if settings.workspace_service_auth_token:
        headers["Authorization"] = f"Bearer {settings.workspace_service_auth_token}"
    body = None
    if payload is not None:
        import json

        body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=f"{settings.workspace_service_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    with request.urlopen(req, timeout=30) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def _parse_first_uuid(text_value: str | None) -> str | None:
    if not text_value:
        return None
    import re

    match = re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        text_value,
        re.IGNORECASE,
    )
    return match.group(0) if match else None


def _extract_draft_id(events_summary: list[dict]) -> str | None:
    for event in events_summary:
        if str(event.get("author") or "") != "content_creator_agent":
            continue
        draft_id = _parse_first_uuid(str(event.get("text") or ""))
        if draft_id:
            return draft_id
    return None


def _load_generated_content(draft_id: str | None) -> dict | None:
    if not draft_id:
        return None

    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                  d.draft_id::text AS draft_id,
                  d.caption,
                  d.script,
                  d.visual_prompt,
                  d.platform_notes,
                  d.draft_status,
                  c.title,
                  c.topic,
                  c.target_platform
                FROM drafts d
                JOIN campaigns c ON c.campaign_id = d.campaign_id
                WHERE d.draft_id = CAST(:draft_id AS UUID)
                """
            ),
            {"draft_id": draft_id},
        ).mappings().one_or_none()

    if not row:
        return None

    return {
        "draft_id": row["draft_id"],
        "title": row["title"],
        "topic": row["topic"],
        "target_platform": row["target_platform"],
        "draft_status": row["draft_status"],
        "caption": row["caption"],
        "script": row["script"],
        "visual_prompt": row["visual_prompt"],
        "platform_notes": row["platform_notes"],
    }


def _build_generated_content_email(row: dict, scheduled_for: str) -> str:
    sections = [
        f"Scheduled Time: {scheduled_for}",
        f"Title: {row['title']}",
        f"Platform: {row['target_platform']}",
    ]

    content_fields = [
        ("Caption", row.get("caption")),
        ("Script", row.get("script")),
        ("Visual Prompt", row.get("visual_prompt")),
        ("Platform Notes", row.get("platform_notes")),
    ]

    for label, value in content_fields:
        if not value:
            continue
        sections.extend(["", f"{label}:", str(value).strip()])

    if not sections:
        return "Generated content was not available for this scheduled post."

    return "\n".join(sections)


def _procedural_schedule(payload: ContentCampaignRequest, events_summary: list[dict]) -> list[dict]:
    campaign_id = None
    draft_id = None
    approved = False
    for event in events_summary:
        author = str(event.get("author") or "")
        text_value = str(event.get("text") or "")
        if author == "campaign_manager_agent" and not campaign_id:
            campaign_id = _parse_first_uuid(text_value)
        elif author == "content_creator_agent" and not draft_id:
            draft_id = _parse_first_uuid(text_value)
        elif author == "review_agent" and "approved" in text_value.lower():
            approved = True

    if not (campaign_id and draft_id and approved):
        events_summary.append(
            {
                "stage": "calendar_procedural",
                "author": "calendar_procedural",
                "text": "Procedural scheduling skipped because an approved campaign and draft were not both available.",
            }
        )
        return events_summary

    scheduled_for = payload.campaign.scheduled_for
    reminder_email = payload.campaign.reminder_email
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                  c.title,
                  c.target_platform,
                  d.caption,
                  d.script,
                  d.visual_prompt,
                  d.platform_notes
                FROM campaigns c
                JOIN drafts d ON d.campaign_id = c.campaign_id
                WHERE c.campaign_id = CAST(:campaign_id AS UUID)
                  AND d.draft_id = CAST(:draft_id AS UUID)
                """
            ),
            {"campaign_id": campaign_id, "draft_id": draft_id},
        ).mappings().one()

        schedule_job = connection.execute(
            text(
                """
                INSERT INTO schedule_jobs (
                  campaign_id, draft_id, scheduled_for, channel, reminder_email
                )
                VALUES (
                  CAST(:campaign_id AS UUID),
                  CAST(:draft_id AS UUID),
                  CAST(:scheduled_for AS TIMESTAMPTZ),
                  :channel,
                  NULLIF(:reminder_email, '')
                )
                RETURNING schedule_job_id::text AS schedule_job_id
                """
            ),
            {
                "campaign_id": campaign_id,
                "draft_id": draft_id,
                "scheduled_for": scheduled_for,
                "channel": row["target_platform"],
                "reminder_email": reminder_email,
            },
        ).mappings().one()

        start_dt = datetime.fromisoformat(scheduled_for)
        end_dt = start_dt + timedelta(minutes=30)
        event = _workspace_request(
            "POST",
            "/calendar/events",
            {
                "calendar_id": "primary",
                "summary": row["title"],
                "description": (row["caption"] or row["script"] or "")[:2000],
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "timezone": "Asia/Kolkata",
                "attendees": [reminder_email] if reminder_email else [],
            },
        )

        connection.execute(
            text(
                """
                UPDATE schedule_jobs
                SET schedule_status = 'scheduled',
                    calendar_event_id = :calendar_event_id,
                    updated_at = NOW()
                WHERE schedule_job_id = CAST(:schedule_job_id AS UUID)
                """
            ),
            {
                "schedule_job_id": schedule_job["schedule_job_id"],
                "calendar_event_id": event.get("id", ""),
            },
        )

        if reminder_email:
            _workspace_request(
                "POST",
                "/gmail/send",
                {
                    "to": [reminder_email],
                    "subject": f"Scheduled: {row['title']}",
                    "body_text": _build_generated_content_email(row, scheduled_for),
                },
            )
            connection.execute(
                text(
                    """
                    UPDATE schedule_jobs
                    SET schedule_status = 'sent',
                        updated_at = NOW()
                    WHERE schedule_job_id = CAST(:schedule_job_id AS UUID)
                    """
                ),
                {"schedule_job_id": schedule_job["schedule_job_id"]},
            )

        connection.execute(
            text(
                """
                UPDATE campaigns
                SET status = 'scheduled',
                    updated_at = NOW()
                WHERE campaign_id = CAST(:campaign_id AS UUID)
                """
            ),
            {"campaign_id": campaign_id},
        )

    events_summary.extend(
        [
            {
                "stage": "calendar_procedural",
                "author": "calendar_procedural",
                "text": f"Schedule job created for {scheduled_for}.",
            },
            {
                "stage": "calendar_procedural",
                "author": "calendar_procedural",
                "text": "Calendar event created and campaign marked scheduled.",
            },
            {
                "stage": "calendar_procedural",
                "author": "calendar_procedural",
                "text": "Confirmation email sent." if reminder_email else "No confirmation email requested.",
            },
        ]
    )
    return events_summary


def _get_runner() -> Runner:
    global runner
    if runner is None:
        if settings.gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = settings.gemini_location
        from adk_app.content_ops_agents.agent import root_agent

        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            session_service=session_service,
        )
    return runner


def _workspace_tool_config() -> dict[str, str | None]:
    return {
        "list_calendars": "list_calendars",
        "list_events": "list_events",
        "create_event": "create_event",
        "update_event": "update_event",
        "send_email": "send_email",
    }


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        {
            "status": "error",
            "path": str(request.url.path),
            "error": str(exc),
        },
        status_code=500,
    )


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/config-check")
def config_check() -> dict:
    return {
        "project": settings.google_cloud_project,
        "location": settings.google_cloud_location,
        "gemini_location": settings.gemini_location or settings.google_cloud_location,
        "db_host": settings.db_host,
        "db_port": settings.db_port,
        "db_name": settings.db_name,
        "db_user": settings.db_user,
        "toolbox_url": settings.toolbox_url,
        "workspace_service_url": settings.workspace_service_url,
    }


@app.get("/workspace-config-check")
def workspace_config_check() -> JSONResponse:
    tool_names = _workspace_tool_config()
    missing_fields = []

    if not settings.workspace_service_url:
        missing_fields.append("WORKSPACE_SERVICE_URL")

    return JSONResponse(
        {
            "status": "ok" if not missing_fields else "incomplete",
            "workspace_service_url": settings.workspace_service_url,
            "workspace_service_auth_configured": bool(settings.workspace_service_auth_token),
            "configured_tools": list(tool_names),
            "missing_fields": missing_fields,
        },
        status_code=200 if not missing_fields else 500,
    )


@app.get("/readiness")
def readiness() -> JSONResponse:
    workspace_ready = bool(
        settings.workspace_service_url
    )
    return JSONResponse(
        {
            "status": "ok" if workspace_ready else "degraded",
            "database_configured": all(
                [
                    settings.db_host,
                    settings.db_name,
                    settings.db_user,
                    settings.db_password,
                ]
            ),
            "workspace_service_configured": workspace_ready,
        },
        status_code=200 if workspace_ready else 503,
    )


@app.get("/db-check")
def db_check() -> JSONResponse:
    try:
        result = check_database()
        return JSONResponse(
            {
                "status": "ok",
                "database": result,
            },
            status_code=200,
        )
    except Exception as exc:  # pragma: no cover
        return JSONResponse(
            {
                "status": "error",
                "error": str(exc),
            },
            status_code=500,
        )


@app.post("/workflows/content-campaign")
async def run_content_campaign(payload: ContentCampaignRequest) -> JSONResponse:
    user_id = (
        payload.creator_profile.name
        if payload.creator_profile and payload.creator_profile.name
        else "content_ops_user"
    )
    session_id = str(uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    prompt = _build_workflow_prompt(payload)
    workflow_runner = _get_runner()
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    events_summary: list[dict] = []
    final_response = "No final response returned."
    last_stage = "initializing"
    started_at = time.time()

    async def _collect_events() -> None:
        nonlocal final_response, last_stage
        async for event in workflow_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            event_data = {
                "author": getattr(event, "author", None),
                "branch": getattr(event, "branch", None),
            }
            if event_data["author"]:
                last_stage = str(event_data["author"])
                event_data["stage"] = last_stage
            if getattr(event, "content", None) and getattr(event.content, "parts", None):
                texts = [
                    getattr(part, "text", None)
                    for part in event.content.parts
                    if getattr(part, "text", None)
                ]
                if texts:
                    event_data["text"] = "\n".join(texts)
            events_summary.append(event_data)
            if event.is_final_response() and getattr(event, "content", None):
                texts = [
                    getattr(part, "text", None)
                    for part in event.content.parts
                    if getattr(part, "text", None)
                ]
                if texts:
                    final_response = "\n".join(texts)

    attempt = 0
    while True:
        try:
            await asyncio.wait_for(_collect_events(), timeout=WORKFLOW_TIMEOUT_SECONDS)
            break
        except asyncio.TimeoutError:
            elapsed = round(time.time() - started_at, 2)
            return JSONResponse(
                {
                    "status": "error",
                    "session_id": session_id,
                    "prompt": prompt,
                    "error": f"Workflow timed out after {WORKFLOW_TIMEOUT_SECONDS} seconds.",
                    "last_stage": last_stage,
                    "elapsed_seconds": elapsed,
                    "events": events_summary,
                },
                status_code=504,
            )
        except Exception as exc:
            if _is_retryable_resource_exhausted(exc) and attempt < MAX_WORKFLOW_RETRIES:
                delay = round(_retry_delay_seconds(attempt), 1)
                events_summary.append(
                    {
                        "stage": last_stage,
                        "author": last_stage,
                        "text": f"Model capacity is temporarily exhausted. Retrying in {delay} seconds (attempt {attempt + 2}/{MAX_WORKFLOW_RETRIES + 1}).",
                    }
                )
                attempt += 1
                await asyncio.sleep(delay)
                continue
            elapsed = round(time.time() - started_at, 2)
            return JSONResponse(
                {
                    "status": "error",
                    "session_id": session_id,
                    "prompt": prompt,
                    "error": str(exc),
                    "last_stage": last_stage,
                    "elapsed_seconds": elapsed,
                    "events": events_summary,
                },
                status_code=500,
            )

    elapsed = round(time.time() - started_at, 2)
    generated_content = _load_generated_content(_extract_draft_id(events_summary))
    if PROCEDURAL_CALENDAR:
        try:
            events_summary = _procedural_schedule(payload, events_summary)
            last_stage = "calendar_procedural"
            if final_response == "No final response returned.":
                final_response = "Workflow completed, content approved, and scheduling handled procedurally."
        except Exception as exc:
            return JSONResponse(
                {
                    "status": "error",
                    "session_id": session_id,
                    "prompt": prompt,
                    "error": str(exc),
                    "last_stage": "calendar_procedural",
                    "elapsed_seconds": elapsed,
                    "generated_content": generated_content,
                    "events": events_summary,
                },
                status_code=500,
            )
    return JSONResponse(
        {
            "status": "ok",
            "session_id": session_id,
            "prompt": prompt,
            "response": final_response,
            "last_stage": last_stage,
            "elapsed_seconds": elapsed,
            "generated_content": generated_content,
            "events": events_summary,
        },
        status_code=200,
    )
