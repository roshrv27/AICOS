"""Immutable data models for the vector-store layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmbeddingDocument:
    """A document with its vector embedding and associated metadata.

    The ``embedding`` field is supplied by the caller (e.g. an embedding
    model).  This layer never generates embeddings.
    """

    id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    """One search result with similarity score and rank."""

    document: EmbeddingDocument
    score: float
    rank: int
