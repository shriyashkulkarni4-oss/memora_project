"""Explicit task routing, privacy classification, fallback, and budget policy."""

from dataclasses import asdict, dataclass
from enum import Enum

from app.ai.gateway import AIGateway, ProviderCapability, ProviderType
from app.config import Settings


class AITask(str, Enum):
    SUMMARIZATION = "summarization"
    ENRICHMENT = "enrichment"
    EMBEDDINGS = "embeddings"
    RERANKING = "reranking"
    RECALL = "recall"
    VISION = "vision"


class CredentialScope(str, Enum):
    SYSTEM = "system"
    USER = "user"


@dataclass(frozen=True)
class CredentialReference:
    """Opaque credential lookup metadata; never contains credential material."""

    scope: CredentialScope
    provider: ProviderType
    reference: str


TASK_CAPABILITY = {
    AITask.SUMMARIZATION: ProviderCapability.ENRICHMENT,
    AITask.ENRICHMENT: ProviderCapability.ENRICHMENT,
    AITask.EMBEDDINGS: ProviderCapability.EMBEDDINGS,
    AITask.RERANKING: ProviderCapability.RERANKING,
    AITask.RECALL: ProviderCapability.ENRICHMENT,
    AITask.VISION: ProviderCapability.VISION,
}


@dataclass(frozen=True)
class ProviderRoute:
    provider: ProviderType
    model: str | None
    external: bool


@dataclass(frozen=True)
class RoutingDecision:
    task: AITask
    primary: ProviderRoute | None
    fallbacks: tuple[ProviderRoute, ...] = ()
    external_content_allowed: bool = False
    external_user_allowed: bool = True

    def to_payload(self) -> dict[str, object]:
        return {
            "task": self.task.value,
            "primary": asdict(self.primary) if self.primary else None,
            "fallbacks": [asdict(route) for route in self.fallbacks],
            "external_content_allowed": self.external_content_allowed,
            "external_user_allowed": self.external_user_allowed,
        }


def _route_fields(settings: Settings, task: AITask) -> tuple[str | None, list[str]]:
    name = task.value
    return (
        getattr(settings, f"ai_{name}_route"),
        getattr(settings, f"ai_{name}_fallback_routes"),
    )


def _default_model(
    settings: Settings, provider: ProviderType, task: AITask
) -> str | None:
    if task == AITask.EMBEDDINGS:
        return {
            ProviderType.OLLAMA: settings.ollama_embedding_model,
            ProviderType.OPENROUTER: settings.openrouter_embedding_model,
            ProviderType.HUGGINGFACE: settings.huggingface_embedding_model,
            ProviderType.N8N: None,
            ProviderType.OPENAI_COMPATIBLE: settings.openai_compatible_embedding_model,
        }[provider]
    return {
        ProviderType.OLLAMA: settings.ollama_model,
        ProviderType.OPENROUTER: settings.openrouter_model,
        ProviderType.HUGGINGFACE: settings.huggingface_chat_model,
        ProviderType.N8N: None,
        ProviderType.OPENAI_COMPATIBLE: settings.openai_compatible_model,
    }[provider]


def _is_external(settings: Settings, provider: ProviderType) -> bool:
    if provider in {ProviderType.OPENROUTER, ProviderType.HUGGINGFACE}:
        return True
    if provider == ProviderType.OLLAMA:
        return settings.ollama_deployment_type == "third_party"
    if provider == ProviderType.N8N:
        return settings.n8n_deployment_type == "third_party"
    return settings.openai_compatible_deployment_type == "third_party"


def _provider_enabled(settings: Settings, provider: ProviderType) -> bool:
    return {
        ProviderType.OLLAMA: settings.ollama_enabled,
        ProviderType.N8N: settings.n8n_enabled,
        ProviderType.OPENROUTER: settings.openrouter_enabled,
        ProviderType.HUGGINGFACE: settings.huggingface_enabled,
        ProviderType.OPENAI_COMPATIBLE: settings.openai_compatible_enabled,
    }[provider]


def _parse_route(
    value: str, settings: Settings, gateway: AIGateway, task: AITask
) -> ProviderRoute:
    provider_name, separator, configured_model = value.partition(":")
    provider = ProviderType(provider_name)
    gateway.require_capability(provider, TASK_CAPABILITY[task])
    model = (
        configured_model
        if separator and configured_model
        else _default_model(settings, provider, task)
    )
    external = _is_external(settings, provider)
    if external and (
        not settings.ai_external_content_allowed
        or provider.value not in settings.ai_allowed_external_providers
    ):
        raise ValueError(f"external AI provider is not permitted for {task.value}")
    return ProviderRoute(provider, model, external)


def resolve_task_policy(
    settings: Settings,
    gateway: AIGateway,
    task: AITask,
    *,
    external_allowed_for_user: bool = True,
) -> RoutingDecision:
    primary_value, fallback_values = _route_fields(settings, task)
    if not primary_value:
        return RoutingDecision(
            task, None, external_user_allowed=external_allowed_for_user
        )
    route_values = [primary_value]
    if settings.ai_cross_provider_fallback_enabled:
        route_values.extend(fallback_values)
    configured_routes = [
        _parse_route(value, settings, gateway, task)
        for value in route_values
        if _provider_enabled(settings, ProviderType(value.partition(":")[0]))
    ]
    allowed_routes = [
        route
        for route in configured_routes
        if external_allowed_for_user or not route.external
    ]
    primary = allowed_routes[0] if allowed_routes else None
    fallbacks = tuple(allowed_routes[1:])
    return RoutingDecision(
        task,
        primary,
        fallbacks,
        external_content_allowed=(
            settings.ai_external_content_allowed and external_allowed_for_user
        ),
        external_user_allowed=external_allowed_for_user,
    )
