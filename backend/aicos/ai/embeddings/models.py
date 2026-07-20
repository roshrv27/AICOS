"""Immutable data models for the embedding infrastructure.

This layer never generates embeddings — it only transports them between the
provider and the application.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmbeddingRequest:
    """A single embedding request."""

    text: str


@dataclass(frozen=True)
class EmbeddingBatchRequest:
    """A batch embedding request."""

    texts: list[str]


@dataclass(frozen=True)
class EmbeddingResponse:
    """The embedding vector for a single text, with metadata."""

    embedding: list[float]
    dimensions: int
    model: str


@dataclass(frozen=True)
class EmbeddingBatchResponse:
    """Embedding vectors for a batch of texts, with metadata."""

    embeddings: list[list[float]]
    dimensions: int
    model: str


@dataclass(frozen=True)
class ModelInfo:
    """Metadata returned by the provider about the active model."""

    name: str
    dimensions: int
    available: bool
