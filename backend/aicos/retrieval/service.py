"""Application-facing retrieval pipeline.

``RetrievalService`` is the single entry point for semantic retrieval.
It orchestrates query validation, embedding, vector-store search,
metadata filtering, and ranking while remaining completely provider
independent.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..ai.embeddings.models import EmbeddingRequest
from ..logging import get_logger
from ..persistence.vector_store import SearchResult
from .exceptions import QueryValidationError, RankingError, SearchError
from .models import QueryRequest, RetrievedChunk, RetrievalResult, RetrievalSummary

if TYPE_CHECKING:
    from ..ai.embeddings import EmbeddingService
    from ..persistence.vector_store import VectorStorePort
    from .filters import MetadataFilterBuilder
    from .interfaces import QueryValidator, RankingStrategy


class QueryProcessor:
    """Validate and normalize query strings.

    Strips leading/trailing whitespace and rejects empty or
    whitespace-only queries.  No AI rewriting, expansion, or
    summarization is performed.
    """

    def validate_and_normalize(self, query: str) -> str:
        normalized = query.strip()
        if not normalized:
            raise QueryValidationError("query must not be empty or whitespace only")
        return normalized


class RetrievalService:
    """Orchestrate semantic retrieval: validate -> embed -> search -> rank.

    Depends only on protocols and project services — never on concrete
    providers or infrastructure.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStorePort,
        ranker: RankingStrategy,
        filter_builder: MetadataFilterBuilder,
        processor: QueryValidator,
        default_top_k: int = 10,
        max_top_k: int = 100,
        similarity_threshold: float = 0.0,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._ranker = ranker
        self._filter_builder = filter_builder
        self._processor = processor
        self._default_top_k = default_top_k
        self._max_top_k = max_top_k
        self._similarity_threshold = similarity_threshold
        self._logger = get_logger("retrieval")

    def retrieve(self, request: QueryRequest) -> RetrievalResult:
        started_at = time.perf_counter()

        try:
            normalized_query = self._processor.validate_and_normalize(request.query)
        except QueryValidationError:
            raise

        top_k = self._resolve_top_k(request.top_k)
        threshold = request.similarity_threshold if request.similarity_threshold is not None else self._similarity_threshold

        try:
            embedding_response = self._embedding_service.embed(
                EmbeddingRequest(text=normalized_query)
            )
        except Exception as exc:
            raise SearchError(f"failed to generate query embedding: {exc}") from exc

        store_filter = self._filter_builder.build(request.filters)

        try:
            search_results: list[SearchResult] = self._vector_store.search(
                collection=request.collection_name,
                query_vector=embedding_response.embedding,
                top_k=top_k,
                filter=store_filter,
            )
        except Exception as exc:
            raise SearchError(f"vector-store search failed: {exc}") from exc

        retrieved = self._to_chunks(search_results, request.collection_name)

        if threshold > 0.0:
            retrieved = [c for c in retrieved if c.score >= threshold]

        try:
            ranked = self._ranker.rank(retrieved)
        except Exception as exc:
            raise RankingError(f"ranking failed: {exc}") from exc

        duration_ms = (time.perf_counter() - started_at) * 1000
        summary = RetrievalSummary(
            total_results=len(ranked),
            total_duration_ms=duration_ms,
        )

        self._logger.info(
            "retrieval completed",
            extra={
                "top_k": top_k,
                "threshold": threshold,
                "retrieved_count": len(ranked),
                "duration_ms": duration_ms,
            },
        )

        return RetrievalResult(
            query=normalized_query,
            results=ranked,
            summary=summary,
        )

    def _resolve_top_k(self, requested: int) -> int:
        if requested < 1:
            return self._default_top_k
        return min(requested, self._max_top_k)

    @staticmethod
    def _to_chunks(
        search_results: list[SearchResult],
        collection_name: str,
    ) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                content=res.document.content,
                metadata=dict(res.document.metadata),
                score=res.score,
                rank=res.rank,
                chunk_id=res.document.id,
                collection_name=collection_name,
            )
            for res in search_results
        ]
