import ssl

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _database_url() -> str:
    return (
        f"postgresql+pg8000://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


engine: Engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    connect_args={"ssl_context": _ssl_context()},
)


def check_database() -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    inet_server_addr() AS server_ip,
                    inet_server_port() AS server_port
                """
            )
        ).mappings().one()
    result = dict(row)
    if result.get("server_ip") is not None:
        result["server_ip"] = str(result["server_ip"])
    return result
