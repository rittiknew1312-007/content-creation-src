import logging

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from googleapiclient.errors import HttpError

from workspace_service.config import get_settings
from workspace_service.google_clients import build_message, calendar_service, gmail_service

app = FastAPI(title="Workspace Service", version="0.1.0")
logger = logging.getLogger(__name__)


class CalendarEventCreate(BaseModel):
    calendar_id: str = Field(default="primary")
    summary: str
    description: str = ""
    start_time: str
    end_time: str
    timezone: str = "UTC"
    attendees: list = Field(default_factory=list)


class CalendarEventUpdate(BaseModel):
    calendar_id: str = Field(default="primary")
    summary: str | None = None
    description: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    timezone: str = "UTC"
    attendees: list | None = None


class GmailSendRequest(BaseModel):
    to: list[str]
    cc: list[str] = Field(default_factory=list)
    subject: str
    body_text: str


def _authorize(auth_header: str | None) -> None:
    settings = get_settings()
    expected = settings.google_workspace_auth_token
    if not expected:
        return
    if auth_header != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _raise_google_error(exc: Exception, context: str, extra: dict | None = None) -> None:
    logger.exception("Workspace service failure during %s", context)
    detail = {"context": context}
    if extra:
        detail["extra"] = extra
    if isinstance(exc, HttpError):
        body = exc.content.decode("utf-8", errors="ignore") if exc.content else str(exc)
        detail["google_error"] = body
        raise HTTPException(status_code=502, detail=detail) from exc
    detail["error"] = str(exc)
    raise HTTPException(status_code=500, detail=detail) from exc


def _normalize_attendees(attendees: list | None) -> list[str]:
    if not attendees:
        return []
    normalized = []
    for attendee in attendees:
        if isinstance(attendee, str):
            email = attendee.strip()
            if email:
                normalized.append(email)
        elif isinstance(attendee, dict):
            email = str(attendee.get("email", "")).strip()
            if email:
                normalized.append(email)
    return normalized


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/calendar/calendars")
def list_calendars(authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    try:
        service = calendar_service()
        resp = service.calendarList().list().execute()
        items = [
            {"id": item.get("id"), "summary": item.get("summary"), "primary": item.get("primary", False)}
            for item in resp.get("items", [])
        ]
        return {"items": items}
    except Exception as exc:
        _raise_google_error(exc, "list_calendars")


@app.get("/calendar/events")
def list_events(
    calendar_id: str = "primary",
    time_min: str = "",
    time_max: str = "",
    max_results: int = 10,
    authorization: str | None = Header(default=None),
) -> dict:
    _authorize(authorization)
    settings = get_settings()
    try:
        service = calendar_service()
        response = (
            service.events()
            .list(
                calendarId=calendar_id or settings.google_calendar_id,
                timeMin=time_min or None,
                timeMax=time_max or None,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return {"items": response.get("items", [])}
    except Exception as exc:
        _raise_google_error(exc, "list_events", {"calendar_id": calendar_id or settings.google_calendar_id})


@app.post("/calendar/events")
def create_event(payload: CalendarEventCreate, authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    settings = get_settings()
    try:
        service = calendar_service()
        body = {
            "summary": payload.summary,
            "description": payload.description,
            "start": {"dateTime": payload.start_time, "timeZone": payload.timezone},
            "end": {"dateTime": payload.end_time, "timeZone": payload.timezone},
            "attendees": [{"email": email} for email in _normalize_attendees(payload.attendees)],
        }
        event = (
            service.events()
            .insert(calendarId=payload.calendar_id or settings.google_calendar_id, body=body)
            .execute()
        )
        return {"id": event.get("id"), "htmlLink": event.get("htmlLink"), "event": event}
    except Exception as exc:
        _raise_google_error(
            exc,
            "create_event",
            {
                "calendar_id": payload.calendar_id or settings.google_calendar_id,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "timezone": payload.timezone,
            },
        )


@app.patch("/calendar/events/{event_id}")
def patch_event(
    event_id: str,
    payload: CalendarEventUpdate,
    authorization: str | None = Header(default=None),
) -> dict:
    _authorize(authorization)
    settings = get_settings()
    try:
        service = calendar_service()
        event = (
            service.events()
            .get(calendarId=payload.calendar_id or settings.google_calendar_id, eventId=event_id)
            .execute()
        )
        if payload.summary is not None:
            event["summary"] = payload.summary
        if payload.description is not None:
            event["description"] = payload.description
        if payload.start_time is not None:
            event["start"] = {"dateTime": payload.start_time, "timeZone": payload.timezone}
        if payload.end_time is not None:
            event["end"] = {"dateTime": payload.end_time, "timeZone": payload.timezone}
        if payload.attendees is not None:
            event["attendees"] = [{"email": email} for email in _normalize_attendees(payload.attendees)]
        updated = (
            service.events()
            .update(
                calendarId=payload.calendar_id or settings.google_calendar_id,
                eventId=event_id,
                body=event,
            )
            .execute()
        )
        return {"id": updated.get("id"), "htmlLink": updated.get("htmlLink"), "event": updated}
    except Exception as exc:
        _raise_google_error(exc, "update_event", {"event_id": event_id})


@app.post("/gmail/send")
def send_gmail(payload: GmailSendRequest, authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    try:
        service = gmail_service()
        raw = build_message(payload.to, payload.cc, payload.subject, payload.body_text)
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"id": sent.get("id"), "threadId": sent.get("threadId")}
    except Exception as exc:
        _raise_google_error(exc, "send_gmail", {"to_count": len(payload.to)})
