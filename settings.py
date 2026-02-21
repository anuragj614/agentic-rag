import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "local"
    DEBUG: int = 1
    APP_NAME: str = "Agentic RAG"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def validate_debug(cls, v: str) -> int:
        if int(v) in [0, 1]:
            return int(v)
        raise ValueError("DEBUG must be 0 or 1")


settings = Settings()
