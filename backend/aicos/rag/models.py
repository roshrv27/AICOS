"""Immutable data models for the RAG pipeline.

This layer never invokes retrievers, LLMs, or builders — it transports
data between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RAGRequest:
    """Parameters for a single RAG operation."""

    query: str
    top_k: int = 10
    collection_name: str = "knowledge"
    system_prompt: str | None = None


@dataclass(frozen=True)
class ContextChunk:
    """A single retrieved chunk formatted for prompt assembly."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    rank: int = 0
    chunk_id: str = ""


@dataclass(frozen=True)
class Citation:
    """A structured citation referencing a source chunk."""

    chunk_id: str
    source: str | None = None
    filename: str | None = None
    score: float = 0.0
    rank: int = 0


@dataclass(frozen=True)
class PromptSection:
    """A single section of a prompt (system or user)."""

    role: str
    content: str


@dataclass(frozen=True)
class Prompt:
    """A fully assembled prompt ready for generation."""

    sections: list[PromptSection] = field(default_factory=list)
    context_chunks: list[ContextChunk] = field(default_factory=list)
    token_count: int = 0


@dataclass(frozen=True)
class GenerationResult:
    """Result of a single generation call."""

    content: str
    model: str
    provider: str
    latency_ms: float = 0.0


@dataclass(frozen=True)
class RAGResponse:
    """Complete result of a single RAG operation."""

    query: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    retrieval_duration_ms: float = 0.0
    generation_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
