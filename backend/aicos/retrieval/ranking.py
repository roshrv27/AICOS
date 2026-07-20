"""Similarity-based ranking implementation.

The default ranking strategy sorts retrieved chunks by their similarity
score in descending order.  No reranking, cross-encoding, or LLM-based
ranking is performed.
"""

from __future__ import annotations

from .models import RetrievedChunk


class SimilarityRanker:
    """Rank chunks by descending similarity score."""

    def rank(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []

        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
        return [
            RetrievedChunk(
                content=c.content,
                metadata=c.metadata,
                score=c.score,
                rank=i,
                chunk_id=c.chunk_id,
                collection_name=c.collection_name,
            )
            for i, c in enumerate(sorted_chunks)
        ]
