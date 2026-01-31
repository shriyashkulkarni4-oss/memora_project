"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://memoryhive:memoryhive@localhost:5432/memoryhive"

    # MinIO / S3 Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "memoryhive"
    minio_secure: bool = False

    # Redis (for future caching, rate limiting)
    redis_url: str | None = None

    # JWT Authentication
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    refresh_token_expire_days: int = 30

    # Encryption (for future use - n8n API keys, etc.)
    encryption_key: str = "dev-encryption-key-32-bytes-long!"

    # Email (optional - for future email verification)
    sendgrid_api_key: str | None = None
    email_from: str = "noreply@memoryhive.app"

    # n8n Integration (for future AI pipeline)
    n8n_webhook_url: str | None = None
    n8n_api_key: str | None = None

    # AI Processing (for future)
    ollama_base_url: str | None = None
    tesseract_cmd: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # File Upload Limits
    max_upload_size_mb: int = 10
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
