"""Citation assembly for RAG.

``CitationBuilder`` creates structured, deduplicated citations from
retrieved context chunks while preserving retrieval order.
"""

from __future__ import annotations

from .models import Citation, ContextChunk


class CitationBuilder:
    """Build deduplicated citations from context chunks."""

    def build(self, context_chunks: list[ContextChunk]) -> list[Citation]:
        seen: set[str] = set()
        citations: list[Citation] = []

        for chunk in context_chunks:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)

            citations.append(
                Citation(
                    chunk_id=chunk.chunk_id,
                    source=chunk.metadata.get("source"),
                    filename=chunk.metadata.get("filename"),
                    score=chunk.score,
                    rank=chunk.rank,
                )
            )

        return citations
