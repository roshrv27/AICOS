"""Immutable data models for the retrieval pipeline.

This layer never generates embeddings or queries the vector store — it
transports data between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchFilters:
    """Optional metadata filters applied during vector-store search.

    All fields are optional; when ``None`` the filter is not applied.
    ``custom_metadata`` allows arbitrary key-value pairs for
    provider-independent filtering.
    """

    collection_name: str | None = None
    source: str | None = None
    filename: str | None = None
    document_id: str | None = None
    custom_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class QueryRequest:
    """Parameters for a single retrieval operation."""

    query: str
    top_k: int = 10
    filters: SearchFilters | None = None
    collection_name: str = "knowledge"
    similarity_threshold: float | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    """A single chunk returned by retrieval."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    rank: int = 0
    chunk_id: str = ""
    collection_name: str = ""


@dataclass(frozen=True)
class RetrievalSummary:
    """High-level result summary for one retrieval."""

    total_results: int = 0
    total_duration_ms: float = 0.0


@dataclass(frozen=True)
class RetrievalResult:
    """Complete result of a single retrieval operation."""

    query: str
    results: list[RetrievedChunk] = field(default_factory=list)
    summary: RetrievalSummary = field(default_factory=RetrievalSummary)
