from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(alias="DB_NAME")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")

    google_cloud_project: str = Field(alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", alias="GOOGLE_CLOUD_LOCATION")
    gemini_location: str | None = Field(default=None, alias="GEMINI_LOCATION")

    toolbox_url: str | None = Field(default=None, alias="TOOLBOX_URL")
    workspace_service_url: str | None = Field(default=None, alias="WORKSPACE_SERVICE_URL")
    workspace_service_auth_token: str | None = Field(
        default=None, alias="WORKSPACE_SERVICE_AUTH_TOKEN"
    )


settings = Settings()
