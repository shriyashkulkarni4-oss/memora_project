"""Application configuration using Pydantic Settings."""

import ipaddress
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_CORS_ORIGIN_REGEX = (
    r"^https?://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])"
    r"(?:\.\d{1,3}){2})(?::\d{1,5})?$"
)


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

    # Admin bootstrap. In development the first registered user is also promoted.
    admin_bootstrap_emails: list[str] = []

    # Admin-triggered backup. Disabled until an operator provides a command.
    backup_root: str = "backups"
    backup_retention_days: int = 14
    admin_backup_command: str | None = None
    admin_backup_working_dir: str | None = None
    admin_backup_timeout_seconds: int = 900

    # Optional n8n integration
    n8n_webhook_url: str | None = None
    n8n_api_key: str | None = None
    n8n_signing_secret: SecretStr | None = None
    n8n_deployment_type: Literal["local", "self_hosted", "third_party"] = "self_hosted"

    # Content processing
    ollama_base_url: str | None = None
    ollama_model: str = "qwen2.5:3b"
    ollama_embedding_model: str | None = None
    ollama_keep_alive: str = "5m"
    ollama_deployment_type: Literal["local", "self_hosted", "third_party"] = "local"
    ai_provider_concurrency: int = 4
    ai_provider_max_payload_bytes: int = 512_000
    ai_provider_max_attempts: int = 3
    ai_circuit_failure_threshold: int = 5
    ai_circuit_reset_seconds: float = 60
    ai_summarization_route: str | None = None
    ai_summarization_fallback_routes: list[str] = []
    ai_enrichment_route: str | None = None
    ai_enrichment_fallback_routes: list[str] = []
    ai_embeddings_route: str | None = None
    ai_embeddings_fallback_routes: list[str] = []
    ai_reranking_route: str | None = None
    ai_reranking_fallback_routes: list[str] = []
    ai_vision_route: str | None = None
    ai_vision_fallback_routes: list[str] = []
    ai_cross_provider_fallback_enabled: bool = False
    ai_external_content_allowed: bool = False
    ai_allowed_external_providers: list[str] = []
    ai_daily_request_budget: int = 0
    ai_monthly_request_budget: int = 0
    ai_daily_token_budget: int = 0
    ai_monthly_token_budget: int = 0
    ai_daily_cost_budget_usd: float = 0
    ai_monthly_cost_budget_usd: float = 0
    ai_per_user_daily_request_quota: int = 0
    ai_per_user_monthly_request_quota: int = 0
    ai_per_user_daily_token_quota: int = 0
    ai_per_user_monthly_token_quota: int = 0
    ai_suggestion_auto_apply_threshold: float = 0
    ai_embedding_dimensions: int = 768
    ai_embedding_normalization: Literal["l2", "none"] = "l2"
    ai_embedding_index_version: int = 1
    ai_embedding_chunk_characters: int = 2_000
    ai_embedding_chunk_overlap: int = 200
    ai_embedding_backfill_batch_size: int = 25
    ai_embedding_backfill_max_items_per_minute: int = 30
    ai_hybrid_search_enabled: bool = True
    ai_search_candidate_limit: int = 200
    ai_search_rrf_k: int = 60
    ai_search_keyword_weight: float = 1.25
    ai_search_semantic_weight: float = 1.0
    ai_search_semantic_threshold: float = 0.25
    ai_search_latency_budget_ms: int = 750
    ai_rerank_candidate_limit: int = 20
    ai_rerank_latency_budget_ms: int = 300
    ollama_timeout_seconds: float = 30
    n8n_timeout_seconds: float = 15

    # OpenRouter is opt-in and never inferred from the presence of a key.
    openrouter_enabled: bool = False
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str | None = None
    openrouter_embedding_model: str | None = None
    openrouter_allowed_models: list[str] = []
    openrouter_allowed_providers: list[str] = []
    openrouter_allow_fallbacks: bool = False
    openrouter_require_parameters: bool = True
    openrouter_data_collection: Literal["allow", "deny"] = "deny"
    openrouter_app_url: str | None = None
    openrouter_app_title: str | None = "Memoryhive"
    openrouter_max_tokens: int = 800
    openrouter_temperature: float = 0.1
    openrouter_timeout_seconds: float = 45

    # Hugging Face Inference Providers; the token should have inference-only scope.
    huggingface_enabled: bool = False
    huggingface_token: SecretStr | None = None
    huggingface_router_url: str = "https://router.huggingface.co"
    huggingface_hub_url: str = "https://huggingface.co"
    huggingface_chat_model: str | None = None
    huggingface_embedding_model: str | None = None
    huggingface_chat_models: list[str] = []
    huggingface_embedding_models: list[str] = []
    huggingface_vision_models: list[str] = []
    huggingface_allowed_policies: list[str] = ["fastest", "cheapest", "preferred"]
    huggingface_allowed_providers: list[str] = []
    huggingface_embedding_dimensions: int | None = None
    huggingface_max_tokens: int = 800
    huggingface_temperature: float = 0.1
    huggingface_timeout_seconds: float = 60

    # Restricted final fallback for explicitly declared compatible APIs.
    openai_compatible_enabled: bool = False
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: SecretStr | None = None
    openai_compatible_model: str | None = None
    openai_compatible_embedding_model: str | None = None
    openai_compatible_endpoint_mode: Literal["chat_completions", "responses"] = (
        "chat_completions"
    )
    openai_compatible_capabilities: list[str] = [
        "enrichment",
        "model_listing",
        "token_usage",
        "health",
    ]
    openai_compatible_chat_models: list[str] = []
    openai_compatible_embedding_models: list[str] = []
    openai_compatible_allowed_hosts: list[str] = []
    openai_compatible_allow_private_network: bool = False
    openai_compatible_private_hosts: list[str] = []
    openai_compatible_extra_headers: dict[str, str] = {}
    openai_compatible_extra_options: dict[str, object] = {}
    openai_compatible_max_tokens: int = 800
    openai_compatible_temperature: float = 0.1
    openai_compatible_timeout_seconds: float = 45
    openai_compatible_deployment_type: Literal[
        "local", "self_hosted", "third_party"
    ] = "third_party"
    tesseract_cmd: str | None = None
    processing_poll_seconds: float = 2.0
    worker_metrics_port: int = 9101
    processing_max_attempts: int = 3
    processing_fetch_max_bytes: int = 5 * 1024 * 1024
    processing_fetch_timeout_seconds: float = 12.0

    # Temporal processing pipeline. Disabled unless the Temporal Compose profile
    # or equivalent production infrastructure is explicitly enabled.
    temporal_enabled: bool = False
    temporal_address: str = "localhost:7233"
    temporal_ui_url: str | None = None
    temporal_namespace: str = "default"
    temporal_task_queue: str = "memoryhive-analysis"
    temporal_scheduler_poll_seconds: float = 10.0
    temporal_scheduler_batch_size: int = 25
    temporal_worker_build_id: str = "memoryhive-analysis-v1"
    temporal_payload_encryption_required: bool = False
    temporal_history_retention_days: int = 30
    temporal_backfill_max_items_per_minute: int = 30
    temporal_custom_search_attributes_enabled: bool = False
    temporal_sdk_metrics_port: int = 9102
    temporal_scheduler_metrics_port: int = 9103
    temporal_worker_metrics_port: int = 9104

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_origin_regex: str | None = None
    allowed_hosts: list[str] = ["*"]

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
        if self.is_development and self.cors_origin_regex is None:
            self.cors_origin_regex = DEVELOPMENT_CORS_ORIGIN_REGEX
        errors: list[str] = []
        self._validate_ai_policy(errors)
        if not self.is_production:
            if errors:
                raise ValueError("; ".join(errors))
            return self
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
        if self.cors_origin_regex:
            errors.append("CORS_ORIGIN_REGEX must be disabled in production")
        if not self.allowed_hosts or any(
            value in {"*", "localhost"} for value in self.allowed_hosts
        ):
            errors.append("ALLOWED_HOSTS must contain production hostnames")
        if (
            self.n8n_webhook_url
            and self._n8n_is_external()
            and not (self.n8n_api_key or self.n8n_signing_secret)
        ):
            errors.append(
                "external N8N_WEBHOOK_URL requires N8N_API_KEY or N8N_SIGNING_SECRET"
            )
        if self.openai_compatible_enabled and not self.openai_compatible_allowed_hosts:
            errors.append(
                "OPENAI_COMPATIBLE_ALLOWED_HOSTS is required when the generic provider is enabled"
            )
        if errors:
            raise ValueError("; ".join(errors))
        return self

    def _validate_ai_policy(self, errors: list[str]) -> None:
        if not 0 <= self.ai_suggestion_auto_apply_threshold <= 1:
            errors.append("AI_SUGGESTION_AUTO_APPLY_THRESHOLD must be between 0 and 1")
        if self.ai_embedding_dimensions < 1 or self.ai_embedding_index_version < 1:
            errors.append("AI embedding dimensions and index version must be positive")
        if (
            self.ai_embedding_backfill_batch_size < 1
            or self.ai_embedding_backfill_max_items_per_minute < 1
        ):
            errors.append("AI embedding backfill limits must be positive")
        if (
            self.ai_search_candidate_limit < 1
            or self.ai_search_rrf_k < 1
            or self.ai_search_latency_budget_ms < 1
            or self.ai_rerank_candidate_limit < 1
            or self.ai_rerank_latency_budget_ms < 1
        ):
            errors.append("AI search limits and latency budgets must be positive")
        if self.ai_search_keyword_weight < 0 or self.ai_search_semantic_weight < 0:
            errors.append("AI search fusion weights cannot be negative")
        if not 0 <= self.ai_search_semantic_threshold <= 1:
            errors.append("AI search semantic threshold must be between 0 and 1")
        if (
            not 0
            <= self.ai_embedding_chunk_overlap
            < self.ai_embedding_chunk_characters
        ):
            errors.append("AI embedding chunk overlap must be smaller than chunk size")
        providers = {
            "ollama",
            "openrouter",
            "huggingface",
            "n8n",
            "openai_compatible",
        }
        configured = {
            "ollama": bool(self.ollama_base_url),
            "openrouter": self.openrouter_enabled
            and bool(self.openrouter_api_key)
            and bool(self.openrouter_model),
            "huggingface": self.huggingface_enabled
            and bool(self.huggingface_token)
            and bool(self.huggingface_chat_model or self.huggingface_embedding_model),
            "n8n": bool(self.n8n_webhook_url),
            "openai_compatible": self.openai_compatible_enabled
            and bool(self.openai_compatible_base_url)
            and bool(self.openai_compatible_model),
        }
        external = {
            "openrouter": True,
            "huggingface": True,
            "ollama": self.ollama_deployment_type == "third_party",
            "n8n": self.n8n_deployment_type == "third_party",
            "openai_compatible": (
                self.openai_compatible_deployment_type == "third_party"
            ),
        }
        for provider in self.ai_allowed_external_providers:
            if provider not in providers:
                errors.append(f"unknown external AI provider: {provider}")
        for task in (
            "summarization",
            "enrichment",
            "embeddings",
            "reranking",
            "vision",
        ):
            routes = [
                getattr(self, f"ai_{task}_route"),
                *getattr(self, f"ai_{task}_fallback_routes"),
            ]
            for route in (value for value in routes if value):
                provider = route.partition(":")[0]
                if provider not in providers:
                    errors.append(f"AI_{task.upper()} route has unknown provider")
                    continue
                if not configured[provider]:
                    errors.append(
                        f"AI_{task.upper()} route selects an unconfigured provider"
                    )
                if external[provider] and (
                    not self.ai_external_content_allowed
                    or provider not in self.ai_allowed_external_providers
                ):
                    errors.append(
                        f"AI_{task.upper()} route selects an external provider without consent"
                    )
        budget_values = {
            "AI_DAILY_REQUEST_BUDGET": self.ai_daily_request_budget,
            "AI_MONTHLY_REQUEST_BUDGET": self.ai_monthly_request_budget,
            "AI_DAILY_TOKEN_BUDGET": self.ai_daily_token_budget,
            "AI_MONTHLY_TOKEN_BUDGET": self.ai_monthly_token_budget,
            "AI_DAILY_COST_BUDGET_USD": self.ai_daily_cost_budget_usd,
            "AI_MONTHLY_COST_BUDGET_USD": self.ai_monthly_cost_budget_usd,
            "AI_PER_USER_DAILY_REQUEST_QUOTA": self.ai_per_user_daily_request_quota,
            "AI_PER_USER_MONTHLY_REQUEST_QUOTA": self.ai_per_user_monthly_request_quota,
            "AI_PER_USER_DAILY_TOKEN_QUOTA": self.ai_per_user_daily_token_quota,
            "AI_PER_USER_MONTHLY_TOKEN_QUOTA": self.ai_per_user_monthly_token_quota,
        }
        for name, value in budget_values.items():
            if value < 0:
                errors.append(f"{name} cannot be negative")
        for name, value in {
            "WORKER_METRICS_PORT": self.worker_metrics_port,
            "TEMPORAL_SDK_METRICS_PORT": self.temporal_sdk_metrics_port,
            "TEMPORAL_SCHEDULER_METRICS_PORT": self.temporal_scheduler_metrics_port,
            "TEMPORAL_WORKER_METRICS_PORT": self.temporal_worker_metrics_port,
        }.items():
            if not 1 <= value <= 65535:
                errors.append(f"{name} must be a valid TCP port")

    def _n8n_is_external(self) -> bool:
        hostname = urlparse(self.n8n_webhook_url or "").hostname
        if not hostname or hostname in {"localhost", "temporal", "n8n"}:
            return False
        try:
            return ipaddress.ip_address(hostname).is_global
        except ValueError:
            return not hostname.endswith((".local", ".internal"))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
