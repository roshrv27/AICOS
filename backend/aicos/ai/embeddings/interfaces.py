"""Provider-neutral embedding protocol.

Application code depends **only** on :class:`EmbeddingProvider`.  Concrete
implementations (Ollama, OpenAI, VoyageAI, BGE, Sentence Transformers, …)
implement this protocol and are wired via the DI container.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import EmbeddingBatchResponse, EmbeddingResponse, ModelInfo


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Provider abstraction for generating text embeddings.

    Every method is synchronous.  No provider-specific types appear in the
    signatures — callers depend only on project data models.
    """

    def embed(self, text: str) -> EmbeddingResponse:
        """Embed a single text string.

        Raises :class:`ProviderUnavailableError` when the provider cannot be
        reached, :class:`ModelNotFoundError` when the configured model is
        unavailable, and :class:`EmbeddingGenerationError` on failure.
        """

    def embed_batch(self, texts: list[str]) -> EmbeddingBatchResponse:
        """Embed multiple texts in a single batch call.

        Raises the same exceptions as :meth:`embed`.
        Results must preserve the order of *texts*.
        """

    def health_check(self) -> bool:
        """Return ``True`` when the provider is reachable and the configured
        model is available."""

    def model_info(self) -> ModelInfo:
        """Return metadata about the currently configured model."""
