import os

from pydantic import SecretStr, field_validator
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

    # Database settings
    DB_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/agentic-rag"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"

    # Embedding service settings
    EMBEDDING_SERVICE_URL: str = "http://localhost:8081/embeddings"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L12-v2"
    REQUEST_TIMEOUT: float = 10.0

    # OpenAI settings
    MODEL_NAME: str = ""
    TEMPERATURE: float = 0.5
    OPENAI_API_KEY: SecretStr = SecretStr("")

    # SMTP settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_FROM_EMAIL: str = ""
    SMTP_TLS: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def validate_debug(cls, v: str) -> int:
        if int(v) in [0, 1]:
            return int(v)
        raise ValueError("DEBUG must be 0 or 1")


settings = Settings()
