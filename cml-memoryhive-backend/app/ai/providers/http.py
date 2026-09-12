"""Credential-safe HTTP behavior shared by provider adapters."""

from __future__ import annotations

from typing import Any

import httpx

from app.ai.contracts import EmbeddingRequest, EmbeddingResult
from app.ai.gateway import (
    ProviderError,
    ProviderErrorCode,
    ProviderHealth,
    ProviderModel,
    ProviderType,
    VisionRequest,
    VisionResponse,
)


def raise_for_provider_status(response: httpx.Response, provider: ProviderType) -> None:
    if response.is_success:
        return
    if response.status_code == 401:
        code = ProviderErrorCode.AUTHENTICATION
    elif response.status_code == 403:
        code = ProviderErrorCode.AUTHORIZATION
    elif response.status_code == 429:
        code = ProviderErrorCode.RATE_LIMIT
    elif response.status_code == 402:
        code = ProviderErrorCode.BUDGET_EXCEEDED
    elif response.status_code >= 500:
        code = ProviderErrorCode.UNAVAILABLE
    else:
        code = ProviderErrorCode.INVALID_REQUEST
    retry_after: float | None = None
    if response.headers.get("retry-after"):
        try:
            retry_after = float(response.headers["retry-after"])
        except ValueError:
            pass
    raise ProviderError(code, provider, retry_after_seconds=retry_after)


class HttpProviderAdapter:
    provider_type: ProviderType

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        kwargs["follow_redirects"] = False
        try:
            if self.client:
                response = await self.client.request(method, url, **kwargs)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException:
            raise ProviderError(ProviderErrorCode.TIMEOUT, self.provider_type) from None
        except httpx.HTTPError:
            raise ProviderError(
                ProviderErrorCode.UNAVAILABLE, self.provider_type
            ) from None
        raise_for_provider_status(response, self.provider_type)
        return response

    async def embed(self, _request: EmbeddingRequest) -> EmbeddingResult:
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )

    async def list_models(self) -> tuple[ProviderModel, ...]:
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )

    async def vision(self, _request: VisionRequest) -> VisionResponse:
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )

    async def health(self) -> ProviderHealth:
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )
