"""Provider-neutral embedding infrastructure for AICOS.

Usage via DI container::

    register_embeddings(container, settings)
    service = container.resolve(EmbeddingService)
    response = service.embed(EmbeddingRequest(text="hello"))

Direct usage::

    from aicos.ai.embeddings import EmbeddingService, OllamaEmbeddingProvider

    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="Qwen3-Embedding:0.6B",
    )
    service = EmbeddingService(provider)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.di import ServiceLifetime
from .exceptions import (
    ConfigurationError,
    EmbeddingError,
    EmbeddingGenerationError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from .interfaces import EmbeddingProvider
from .models import EmbeddingBatchRequest, EmbeddingBatchResponse, EmbeddingRequest, EmbeddingResponse, ModelInfo
from .ollama import OllamaEmbeddingProvider
from .service import EmbeddingService

if TYPE_CHECKING:
    from ...core.di import Container
    from ...settings import Settings

__all__ = [
    "ConfigurationError",
    "EmbeddingBatchRequest",
    "EmbeddingBatchResponse",
    "EmbeddingError",
    "EmbeddingGenerationError",
    "EmbeddingProvider",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "EmbeddingService",
    "ModelInfo",
    "ModelNotFoundError",
    "OllamaEmbeddingProvider",
    "ProviderUnavailableError",
    "register_embeddings",
]


def register_embeddings(container: Container, settings: Settings) -> None:
    """Register embedding services in the DI container.

    ``OllamaEmbeddingProvider`` is registered as a singleton under the
    ``EmbeddingProvider`` protocol.  ``EmbeddingService`` is registered as
    a singleton with auto-injected ``EmbeddingProvider`` dependency.

    Application code resolves ``EmbeddingService`` only.
    """

    if not settings.ollama.enabled:
        raise ConfigurationError("Ollama provider is disabled in settings")

    def create_provider() -> OllamaEmbeddingProvider:
        return OllamaEmbeddingProvider(
            base_url=str(settings.ollama.base_url),
            model=settings.ollama.embedding_model,
            timeout_seconds=settings.ollama.timeout_seconds,
        )

    container.register_factory(
        OllamaEmbeddingProvider,
        create_provider,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        EmbeddingProvider,
        lambda: container.resolve(OllamaEmbeddingProvider),
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register(
        EmbeddingService,
        lifetime=ServiceLifetime.SINGLETON,
    )
