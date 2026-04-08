from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from workspace_service.config import get_settings


def _credentials() -> Credentials:
    settings = get_settings()
    creds = Credentials(
        token=None,
        refresh_token=settings.google_workspace_refresh_token,
        token_uri=settings.google_workspace_token_uri,
        client_id=settings.google_workspace_client_id,
        client_secret=settings.google_workspace_client_secret,
        scopes=[
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
    )
    creds.refresh(Request())
    return creds


def calendar_service():
    settings = get_settings()
    return build("calendar", "v3", credentials=_credentials(), cache_discovery=False)


def gmail_service():
    settings = get_settings()
    return build("gmail", "v1", credentials=_credentials(), cache_discovery=False)


def build_message(to: list[str], cc: list[str], subject: str, body_text: str) -> str:
    message = EmailMessage()
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    message.set_content(body_text)
    import base64

    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
