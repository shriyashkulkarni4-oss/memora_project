"""Built-in AI provider adapters."""

from app.ai.providers.huggingface import HuggingFaceAdapter
from app.ai.providers.n8n import N8nAdapter
from app.ai.providers.ollama import OllamaAdapter
from app.ai.providers.openai_compatible import OpenAICompatibleAdapter
from app.ai.providers.openrouter import OpenRouterAdapter

__all__ = [
    "HuggingFaceAdapter",
    "N8nAdapter",
    "OllamaAdapter",
    "OpenAICompatibleAdapter",
    "OpenRouterAdapter",
]
