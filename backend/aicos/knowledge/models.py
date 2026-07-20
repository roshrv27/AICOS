"""Immutable data models for the knowledge-ingestion pipeline.

This layer never generates embeddings or interacts with providers — it
transports data between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Document:
    """A raw document loaded from a file."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None


@dataclass(frozen=True)
class DocumentChunk:
    """A single chunk produced by a chunking strategy."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0


@dataclass(frozen=True)
class IngestionRequest:
    """Parameters for a single ingestion operation."""

    source: Path
    collection_name: str = "knowledge"
    chunk_size: int = 1000
    chunk_overlap: int = 200


@dataclass(frozen=True)
class IngestionSummary:
    """High-level result summary for one ingestion."""

    total_chunks: int
    total_characters: int
    total_words: int


@dataclass(frozen=True)
class IngestionResult:
    """Complete result of a single ingestion operation."""

    collection_name: str
    chunks_ingested: int
    summary: IngestionSummary
