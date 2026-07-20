"""Provider adapters available to the AICOS Model Router."""

from .mock import MockProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider

__all__ = ["MockProvider", "OllamaProvider", "OpenRouterProvider"]
