"""Project-local database configuration; importing never opens a connection."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    db_host: str = "127.0.0.1"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: Literal["finance_demo"] = "finance_demo"
    db_user: str = "finance_demo_app"
    # Empty password permits configuration-free startup, never a fabricated secret.
    db_password: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    return Settings()
