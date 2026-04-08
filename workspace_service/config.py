from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_workspace_client_id: str = Field(alias="GOOGLE_WORKSPACE_CLIENT_ID")
    google_workspace_client_secret: str = Field(alias="GOOGLE_WORKSPACE_CLIENT_SECRET")
    google_workspace_refresh_token: str = Field(alias="GOOGLE_WORKSPACE_REFRESH_TOKEN")
    google_workspace_token_uri: str = Field(
        default="https://oauth2.googleapis.com/token",
        alias="GOOGLE_WORKSPACE_TOKEN_URI",
    )
    google_workspace_auth_token: str | None = Field(
        default=None,
        alias="GOOGLE_WORKSPACE_SERVICE_AUTH_TOKEN",
    )
    google_calendar_id: str = Field(default="primary", alias="GOOGLE_CALENDAR_ID")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
