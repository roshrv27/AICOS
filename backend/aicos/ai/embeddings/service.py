"""Application-facing embedding service.

``EmbeddingService`` is the single entry point that application code uses.
It depends only on ``EmbeddingProvider`` and contains zero business logic.
"""

from __future__ import annotations

import time

from ...logging import get_logger
from .exceptions import ConfigurationError
from .interfaces import EmbeddingProvider
from .models import EmbeddingBatchRequest, EmbeddingBatchResponse, EmbeddingRequest, EmbeddingResponse


class EmbeddingService:
    """Provider-independent service for generating text embeddings.

    Validates inputs and delegates to the configured ``EmbeddingProvider``.
    Future capabilities (caching, retries, telemetry) belong here but are
    intentionally out of scope for this milestone.
    """

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider
        self._logger = get_logger("embeddings")

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        started_at = time.perf_counter()
        self._validate_text(request.text)
        response = self._provider.embed(request.text)
        self._logger.debug(
            "embedding request completed",
            extra={
                "model": response.model,
                "dimensions": response.dimensions,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return response

    def embed_batch(self, request: EmbeddingBatchRequest) -> EmbeddingBatchResponse:
        started_at = time.perf_counter()
        self._validate_batch(request.texts)
        response = self._provider.embed_batch(request.texts)
        self._logger.debug(
            "batch embedding request completed",
            extra={
                "count": len(response.embeddings),
                "model": response.model,
                "dimensions": response.dimensions,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return response

    @staticmethod
    def _validate_text(text: str) -> None:
        if not text or not text.strip():
            raise ConfigurationError("text must be a non-empty string")

    @staticmethod
    def _validate_batch(texts: list[str]) -> None:
        if not texts:
            raise ConfigurationError("texts list must not be empty")
        for i, t in enumerate(texts):
            if not t or not t.strip():
                raise ConfigurationError(
                    f"text at index {i} must be a non-empty string"
                )
