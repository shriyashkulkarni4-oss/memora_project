"""Composition root for configured AI provider adapters."""

import httpx

from app.ai.gateway import AIGateway, ProviderLimits
from app.ai.providers import (
    HuggingFaceAdapter,
    N8nAdapter,
    OllamaAdapter,
    OpenAICompatibleAdapter,
    OpenRouterAdapter,
)
from app.config import Settings


def build_ai_gateway(
    settings: Settings, *, client: httpx.AsyncClient | None = None
) -> AIGateway:
    def limits(timeout_seconds: float) -> ProviderLimits:
        return ProviderLimits(
            concurrency=settings.ai_provider_concurrency,
            timeout_seconds=timeout_seconds,
            maximum_payload_bytes=settings.ai_provider_max_payload_bytes,
            maximum_attempts=settings.ai_provider_max_attempts,
            circuit_failure_threshold=settings.ai_circuit_failure_threshold,
            circuit_reset_seconds=settings.ai_circuit_reset_seconds,
        )

    adapters = []
    if settings.openai_compatible_enabled:
        if (
            not settings.openai_compatible_base_url
            or not settings.openai_compatible_model
        ):
            raise ValueError(
                "OpenAI-compatible provider is enabled but base URL or model is missing"
            )
        adapters.append(
            OpenAICompatibleAdapter(
                base_url=settings.openai_compatible_base_url,
                api_key=(
                    settings.openai_compatible_api_key.get_secret_value()
                    if settings.openai_compatible_api_key
                    else None
                ),
                default_model=settings.openai_compatible_model,
                embedding_model=settings.openai_compatible_embedding_model,
                endpoint_mode=settings.openai_compatible_endpoint_mode,
                declared_capabilities=settings.openai_compatible_capabilities,
                chat_models=settings.openai_compatible_chat_models,
                embedding_models=settings.openai_compatible_embedding_models,
                allowed_hosts=settings.openai_compatible_allowed_hosts,
                allow_private_network=(
                    settings.openai_compatible_allow_private_network
                ),
                private_hosts=settings.openai_compatible_private_hosts,
                extra_headers=settings.openai_compatible_extra_headers,
                extra_options=settings.openai_compatible_extra_options,
                maximum_tokens=settings.openai_compatible_max_tokens,
                temperature=settings.openai_compatible_temperature,
                deployment_type=settings.openai_compatible_deployment_type,
                client=client,
                limits=limits(settings.openai_compatible_timeout_seconds),
            )
        )
    if settings.huggingface_enabled:
        if not settings.huggingface_token or not (
            settings.huggingface_chat_model or settings.huggingface_embedding_model
        ):
            raise ValueError(
                "Hugging Face is enabled but its token and task model configuration are incomplete"
            )
        adapters.append(
            HuggingFaceAdapter(
                token=settings.huggingface_token.get_secret_value(),
                router_url=settings.huggingface_router_url,
                hub_url=settings.huggingface_hub_url,
                chat_model=settings.huggingface_chat_model,
                embedding_model=settings.huggingface_embedding_model,
                chat_models=settings.huggingface_chat_models,
                embedding_models=settings.huggingface_embedding_models,
                vision_models=settings.huggingface_vision_models,
                allowed_policies=settings.huggingface_allowed_policies,
                allowed_providers=settings.huggingface_allowed_providers,
                embedding_dimensions=settings.huggingface_embedding_dimensions,
                maximum_tokens=settings.huggingface_max_tokens,
                temperature=settings.huggingface_temperature,
                client=client,
                limits=limits(settings.huggingface_timeout_seconds),
            )
        )
    if settings.openrouter_enabled:
        if not settings.openrouter_api_key or not settings.openrouter_model:
            raise ValueError(
                "OpenRouter is enabled but OPENROUTER_API_KEY or OPENROUTER_MODEL is missing"
            )
        adapters.append(
            OpenRouterAdapter(
                api_key=settings.openrouter_api_key.get_secret_value(),
                base_url=settings.openrouter_base_url,
                default_model=settings.openrouter_model,
                embedding_model=settings.openrouter_embedding_model,
                allowed_models=settings.openrouter_allowed_models,
                allowed_providers=settings.openrouter_allowed_providers,
                allow_fallbacks=settings.openrouter_allow_fallbacks,
                require_parameters=settings.openrouter_require_parameters,
                data_collection=settings.openrouter_data_collection,
                app_url=settings.openrouter_app_url,
                app_title=settings.openrouter_app_title,
                maximum_tokens=settings.openrouter_max_tokens,
                temperature=settings.openrouter_temperature,
                client=client,
                limits=limits(settings.openrouter_timeout_seconds),
            )
        )
    if settings.n8n_webhook_url:
        adapters.append(
            N8nAdapter(
                settings.n8n_webhook_url,
                settings.n8n_api_key,
                signing_secret=(
                    settings.n8n_signing_secret.get_secret_value()
                    if settings.n8n_signing_secret
                    else None
                ),
                deployment_type=settings.n8n_deployment_type,
                client=client,
                limits=limits(settings.n8n_timeout_seconds),
            )
        )
    if settings.ollama_base_url:
        adapters.append(
            OllamaAdapter(
                settings.ollama_base_url,
                settings.ollama_model,
                embedding_model=settings.ollama_embedding_model,
                keep_alive=settings.ollama_keep_alive,
                deployment_type=settings.ollama_deployment_type,
                client=client,
                limits=limits(settings.ollama_timeout_seconds),
            )
        )
    return AIGateway(adapters)
