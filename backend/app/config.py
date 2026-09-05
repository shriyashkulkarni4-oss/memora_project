"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
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
    app_debug: bool = True

    # Database
    database_url: str = (
        "postgresql+asyncpg://memoryhive:memoryhive@localhost:5432/memoryhive"
    )

    # MinIO / S3 Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "memoryhive-uploads"
    minio_secure: bool = False

    # Redis-backed distributed rate limiting
    redis_url: str | None = None
    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 10

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

    # Optional n8n integration
    n8n_webhook_url: str | None = None
    n8n_api_key: str | None = None

    # Content processing
    ollama_base_url: str | None = None
    ollama_model: str = "qwen2.5:3b"
    tesseract_cmd: str | None = None
    processing_poll_seconds: float = 2.0
    processing_max_attempts: int = 3
    processing_fetch_max_bytes: int = 5 * 1024 * 1024
    processing_fetch_timeout_seconds: float = 12.0

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver", "test"]

    # File Upload Limits
    max_upload_size_mb: int = 10
    allowed_image_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.is_production:
            return self
        errors: list[str] = []
        if self.app_debug:
            errors.append("APP_DEBUG must be false")
        if len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith("dev-"):
            errors.append(
                "JWT_SECRET_KEY must be a unique value of at least 32 characters"
            )
        if len(self.encryption_key) < 32 or self.encryption_key.startswith("dev-"):
            errors.append(
                "ENCRYPTION_KEY must be a unique value of at least 32 characters"
            )
        if "memoryhive:memoryhive@" in self.database_url:
            errors.append("DATABASE_URL must not use the development password")
        if (
            self.minio_access_key == "minioadmin"
            or self.minio_secret_key == "minioadmin"
        ):
            errors.append("MinIO credentials must not use development defaults")
        if not self.redis_url:
            errors.append("REDIS_URL is required for distributed rate limiting")
        if not self.cors_origins or any(
            "localhost" in value for value in self.cors_origins
        ):
            errors.append("CORS_ORIGINS must contain production origins")
        if not self.allowed_hosts or any(
            value in {"*", "localhost"} for value in self.allowed_hosts
        ):
            errors.append("ALLOWED_HOSTS must contain production hostnames")
        if errors:
            raise ValueError("; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
