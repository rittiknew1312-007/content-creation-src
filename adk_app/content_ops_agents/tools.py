import json
import os
import ssl
from asyncio import new_event_loop, run_coroutine_threadsafe
from threading import Lock, Thread
from urllib import error, request

from aiohttp import ClientSession, TCPConnector
from toolbox_core.client import ToolboxClient
from toolbox_core.sync_tool import ToolboxSyncTool


TOOLBOX_URL = os.getenv(
    "TOOLBOX_URL",
    "https://content-ops-toolbox-972348605933.us-central1.run.app",
)
WORKSPACE_SERVICE_URL = os.getenv("WORKSPACE_SERVICE_URL", "").rstrip("/")
WORKSPACE_SERVICE_AUTH_TOKEN = os.getenv("WORKSPACE_SERVICE_AUTH_TOKEN", "").strip()
WORKSPACE_SERVICE_VERIFY_SSL = os.getenv("WORKSPACE_SERVICE_VERIFY_SSL", "false").lower() == "true"
WORKSPACE_SERVICE_TIMEOUT_SECONDS = int(os.getenv("WORKSPACE_SERVICE_TIMEOUT_SECONDS", "30"))


class DevToolboxSyncClient:
    """Minimal sync wrapper that disables TLS verification for local dev."""

    _loop = None
    _thread = None
    _lock = Lock()

    def __init__(self, url: str):
        if self.__class__._loop is None:
            with self.__class__._lock:
                if self.__class__._loop is None:
                    loop = new_event_loop()
                    thread = Thread(target=loop.run_forever, daemon=True)
                    thread.start()
                    self.__class__._loop = loop
                    self.__class__._thread = thread

        async def create_client():
            session = ClientSession(connector=TCPConnector(ssl=False))
            return ToolboxClient(url, session=session)

        self._async_client = run_coroutine_threadsafe(
            create_client(), self.__class__._loop
        ).result()

    def load_toolset(self, name: str):
        async_tools = run_coroutine_threadsafe(
            self._async_client.load_toolset(name), self.__class__._loop
        ).result()
        return [
            ToolboxSyncTool(async_tool, self.__class__._loop, self.__class__._thread)
            for async_tool in async_tools
        ]


def _workspace_request(method: str, path: str, payload: dict | None = None) -> dict:
    if not WORKSPACE_SERVICE_URL:
        raise ValueError("WORKSPACE_SERVICE_URL is not configured.")

    body = None
    headers = {"Content-Type": "application/json"}
    if WORKSPACE_SERVICE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {WORKSPACE_SERVICE_AUTH_TOKEN}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url=f"{WORKSPACE_SERVICE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        ssl_context = None
        if not WORKSPACE_SERVICE_VERIFY_SSL:
            ssl_context = ssl._create_unverified_context()
        with request.urlopen(req, timeout=WORKSPACE_SERVICE_TIMEOUT_SECONDS, context=ssl_context) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Workspace service error {exc.code}: {detail}") from exc


def _normalize_attendees(attendees: list) -> list[str]:
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


def list_calendars() -> str:
    """List available Google calendars from the hosted workspace service."""

    return json.dumps(_workspace_request("GET", "/calendar/calendars"))


def list_events(
    calendar_id: str = "primary",
    time_min: str = "",
    time_max: str = "",
    max_results: int = 10,
) -> str:
    """List Google Calendar events for a calendar and optional time range."""

    query = (
        f"/calendar/events?calendar_id={calendar_id}"
        f"&time_min={time_min}&time_max={time_max}&max_results={max_results}"
    )
    return json.dumps(_workspace_request("GET", query))


def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    calendar_id: str = "primary",
    timezone: str = "UTC",
    attendees_json: str = "[]",
) -> str:
    """Create a Google Calendar event and return the event payload."""

    return json.dumps(
        _workspace_request(
            "POST",
            "/calendar/events",
            {
                "calendar_id": calendar_id,
                "summary": summary,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "timezone": timezone,
                "attendees": _normalize_attendees(json.loads(attendees_json or "[]")),
            },
        )
    )


def update_event(
    event_id: str,
    summary: str = "",
    start_time: str = "",
    end_time: str = "",
    description: str = "",
    calendar_id: str = "primary",
    timezone: str = "UTC",
    attendees_json: str = "",
) -> str:
    """Update a Google Calendar event and return the updated event payload."""

    payload = {
        "calendar_id": calendar_id,
        "timezone": timezone,
    }
    if summary:
        payload["summary"] = summary
    if start_time:
        payload["start_time"] = start_time
    if end_time:
        payload["end_time"] = end_time
    if description:
        payload["description"] = description
    if attendees_json:
        payload["attendees"] = _normalize_attendees(json.loads(attendees_json))
    return json.dumps(_workspace_request("PATCH", f"/calendar/events/{event_id}", payload))


def send_email(
    to: str,
    subject: str,
    body_text: str,
    cc_json: str = "[]",
) -> str:
    """Send an email through Gmail and return the Gmail API response."""

    return json.dumps(
        _workspace_request(
            "POST",
            "/gmail/send",
            {
                "to": [addr for addr in [email.strip() for email in to.split(",")] if addr],
                "cc": json.loads(cc_json or "[]"),
                "subject": subject,
                "body_text": body_text,
            },
        )
    )


def get_orchestrator_tools():
    toolbox = DevToolboxSyncClient(TOOLBOX_URL)
    return toolbox.load_toolset("orchestrator_toolset")


def get_research_tools():
    toolbox = DevToolboxSyncClient(TOOLBOX_URL)
    return toolbox.load_toolset("research_toolset")


def get_content_creator_tools():
    toolbox = DevToolboxSyncClient(TOOLBOX_URL)
    return toolbox.load_toolset("content_creator_toolset")


def get_review_tools():
    toolbox = DevToolboxSyncClient(TOOLBOX_URL)
    return toolbox.load_toolset("review_toolset")


def get_calendar_tools():
    toolbox = DevToolboxSyncClient(TOOLBOX_URL)
    return toolbox.load_toolset("calendar_toolset")


def get_workspace_tools():
    if not WORKSPACE_SERVICE_URL:
        return []
    return [list_calendars, list_events, create_event, update_event, send_email]
