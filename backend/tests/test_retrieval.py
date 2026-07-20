"""Tests for the retrieval pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from aicos.retrieval.exceptions import (
    FilterError,
    QueryValidationError,
    RankingError,
    RetrievalError,
    SearchError,
)
from aicos.retrieval.filters import MetadataFilterBuilder
from aicos.retrieval.models import (
    QueryRequest,
    RetrievedChunk,
    RetrievalResult,
    RetrievalSummary,
    SearchFilters,
)
from aicos.retrieval.ranking import SimilarityRanker
from aicos.retrieval.interfaces import QueryValidator
from aicos.retrieval.service import QueryProcessor, RetrievalService


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

@dataclass
class FakeEmbeddingResponse:
    embedding: list[float]
    dimensions: int = 384
    model: str = "test-model"


@dataclass
class FakeEmbeddingService:
    _fail: bool = False

    def embed(self, request: Any) -> FakeEmbeddingResponse:
        if self._fail:
            raise RuntimeError("embedding provider unavailable")
        return FakeEmbeddingResponse(embedding=[0.1, 0.2, 0.3])


@dataclass
class FakeSearchResult:
    document: Any
    score: float
    rank: int


@dataclass
class FakeEmbeddingDocument:
    id: str
    content: str
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class FakeVectorStore:
    def __init__(self) -> None:
        self._fail = False

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[FakeSearchResult]:
        if self._fail:
            raise RuntimeError("vector store unavailable")
        docs = [
            FakeEmbeddingDocument(
                id=f"chunk_{i}",
                content=f"result {i} content",
                metadata={"source": "/path/doc.md", "filename": "doc.md"},
            )
            for i in range(top_k)
        ]
        return [
            FakeSearchResult(doc, score=1.0 - (i * 0.1), rank=i)
            for i, doc in enumerate(docs)
        ]

    def collection_exists(self, name: str) -> bool:
        return True

    def create_collection(self, name: str) -> None:
        pass


class FakeRanker:
    def rank(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
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


class FakeFailingRanker:
    def rank(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        raise RuntimeError("ranker failed")


# ---------------------------------------------------------------------------
# QueryProcessor
# ---------------------------------------------------------------------------

class TestQueryProcessor:
    def test_valid_query(self) -> None:
        result = QueryProcessor().validate_and_normalize("  hello world  ")
        assert result == "hello world"

    def test_empty_query(self) -> None:
        with pytest.raises(QueryValidationError, match="empty"):
            QueryProcessor().validate_and_normalize("")

    def test_whitespace_query(self) -> None:
        with pytest.raises(QueryValidationError):
            QueryProcessor().validate_and_normalize("   \t  \n  ")

    def test_single_word(self) -> None:
        result = QueryProcessor().validate_and_normalize("python")
        assert result == "python"

    def test_conforms_to_query_validator_protocol(self) -> None:
        assert isinstance(QueryProcessor(), QueryValidator)


# ---------------------------------------------------------------------------
# MetadataFilterBuilder
# ---------------------------------------------------------------------------

class TestMetadataFilterBuilder:
    def test_none_filters(self) -> None:
        assert MetadataFilterBuilder().build(None) is None

    def test_empty_filters(self) -> None:
        assert MetadataFilterBuilder().build(SearchFilters()) is None

    def test_source_filter(self) -> None:
        result = MetadataFilterBuilder().build(SearchFilters(source="/path/doc.md"))
        assert result == {"source": "/path/doc.md"}

    def test_filename_filter(self) -> None:
        result = MetadataFilterBuilder().build(SearchFilters(filename="doc.md"))
        assert result == {"filename": "doc.md"}

    def test_document_id_filter(self) -> None:
        result = MetadataFilterBuilder().build(SearchFilters(document_id="doc_0"))
        assert result == {"document_id": "doc_0"}

    def test_custom_metadata(self) -> None:
        result = MetadataFilterBuilder().build(
            SearchFilters(custom_metadata={"category": "math", "level": 3})
        )
        assert result == {"category": "math", "level": 3}

    def test_custom_metadata_empty_key(self) -> None:
        with pytest.raises(FilterError, match="empty"):
            MetadataFilterBuilder().build(SearchFilters(custom_metadata={"": "val"}))

    def test_custom_metadata_non_string_key(self) -> None:
        with pytest.raises(FilterError, match="string"):
            MetadataFilterBuilder().build(SearchFilters(custom_metadata={1: "val"}))

    def test_multiple_filters(self) -> None:
        result = MetadataFilterBuilder().build(
            SearchFilters(source="/path/doc.md", filename="doc.md")
        )
        assert result == {"source": "/path/doc.md", "filename": "doc.md"}


# ---------------------------------------------------------------------------
# SimilarityRanker
# ---------------------------------------------------------------------------

class TestSimilarityRanker:
    def test_empty_list(self) -> None:
        assert SimilarityRanker().rank([]) == []

    def test_sorts_descending(self) -> None:
        chunks = [
            RetrievedChunk(content="a", score=0.3, rank=0),
            RetrievedChunk(content="b", score=0.9, rank=1),
            RetrievedChunk(content="c", score=0.6, rank=2),
        ]
        ranked = SimilarityRanker().rank(chunks)
        assert [c.score for c in ranked] == [0.9, 0.6, 0.3]

    def test_reassigns_ranks(self) -> None:
        chunks = [
            RetrievedChunk(content="a", score=0.3, rank=5),
            RetrievedChunk(content="b", score=0.9, rank=1),
        ]
        ranked = SimilarityRanker().rank(chunks)
        assert ranked[0].rank == 0
        assert ranked[1].rank == 1

    def test_does_not_mutate_input(self) -> None:
        chunks = [
            RetrievedChunk(content="a", score=0.3, rank=0),
            RetrievedChunk(content="b", score=0.9, rank=1),
        ]
        original_ids = [id(c) for c in chunks]
        SimilarityRanker().rank(chunks)
        assert [id(c) for c in chunks] == original_ids

    def test_single_chunk(self) -> None:
        chunks = [RetrievedChunk(content="a", score=0.5, rank=0)]
        ranked = SimilarityRanker().rank(chunks)
        assert len(ranked) == 1
        assert ranked[0].rank == 0


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------

class TestRetrievalService:
    @pytest.fixture
    def service(self) -> RetrievalService:
        return RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
            default_top_k=10,
            max_top_k=100,
            similarity_threshold=0.0,
        )

    def test_retrieve_valid_query(self, service: RetrievalService) -> None:
        request = QueryRequest(query="test query", top_k=5)
        result = service.retrieve(request)
        assert isinstance(result, RetrievalResult)
        assert result.query == "test query"
        assert len(result.results) == 5
        assert isinstance(result.summary, RetrievalSummary)
        assert result.summary.total_results == 5

    def test_retrieve_normalizes_query(self, service: RetrievalService) -> None:
        result = service.retrieve(QueryRequest(query="  hello  "))
        assert result.query == "hello"

    def test_retrieve_empty_query(self, service: RetrievalService) -> None:
        with pytest.raises(QueryValidationError):
            service.retrieve(QueryRequest(query=""))

    def test_retrieve_whitespace_query(self, service: RetrievalService) -> None:
        with pytest.raises(QueryValidationError):
            service.retrieve(QueryRequest(query="   "))

    def test_results_ranked_by_score(self, service: RetrievalService) -> None:
        result = service.retrieve(QueryRequest(query="test", top_k=10))
        scores = [r.score for r in result.results]
        assert scores == sorted(scores, reverse=True)

    def test_retrieve_with_filters(self, service: RetrievalService) -> None:
        filters = SearchFilters(filename="doc.md")
        result = service.retrieve(QueryRequest(query="test", filters=filters, top_k=3))
        assert len(result.results) == 3

    def test_uses_injected_processor(self) -> None:
        custom = QueryProcessor()
        svc = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=custom,
        )
        result = svc.retrieve(QueryRequest(query="  hello  "))
        assert result.query == "hello"

    def test_ranking_failure_translated(self) -> None:
        svc = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=FakeFailingRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
        )
        with pytest.raises(RankingError, match="ranking failed"):
            svc.retrieve(QueryRequest(query="test"))

    def test_explicit_zero_threshold_respected(self) -> None:
        svc = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
            default_top_k=10,
            max_top_k=100,
            similarity_threshold=0.5,
        )
        result = svc.retrieve(
            QueryRequest(query="test", top_k=10, similarity_threshold=0.0)
        )
        assert len(result.results) > 0

    def test_top_k_clamped_to_max(self) -> None:
        service = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
            default_top_k=10,
            max_top_k=5,
            similarity_threshold=0.0,
        )
        result = service.retrieve(QueryRequest(query="test", top_k=100))
        assert len(result.results) == 5

    def test_top_k_uses_default_when_invalid(self) -> None:
        service = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
            default_top_k=3,
            max_top_k=100,
            similarity_threshold=0.0,
        )
        result = service.retrieve(QueryRequest(query="test", top_k=0))
        assert len(result.results) == 3

    def test_similarity_threshold_filters(self) -> None:
        service = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
            default_top_k=10,
            max_top_k=100,
            similarity_threshold=0.5,
        )
        result = service.retrieve(QueryRequest(query="test", top_k=10, similarity_threshold=None))
        for chunk in result.results:
            assert chunk.score >= 0.5

    def test_request_threshold_overrides_default(self) -> None:
        service = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
            default_top_k=10,
            max_top_k=100,
            similarity_threshold=0.0,
        )
        result = service.retrieve(
            QueryRequest(query="test", top_k=10, similarity_threshold=0.8)
        )
        for chunk in result.results:
            assert chunk.score >= 0.8

    def test_chunk_id_and_collection_preserved(self, service: RetrievalService) -> None:
        result = service.retrieve(
            QueryRequest(query="test", collection_name="my_kb", top_k=2)
        )
        for chunk in result.results:
            assert chunk.chunk_id.startswith("chunk_")
            assert chunk.collection_name == "my_kb"

    def test_chunk_metadata_preserved(self, service: RetrievalService) -> None:
        result = service.retrieve(QueryRequest(query="test", top_k=1))
        assert len(result.results) == 1
        assert result.results[0].metadata.get("filename") == "doc.md"

    def test_embedding_failure_translated(self) -> None:
        service = RetrievalService(
            embedding_service=FakeEmbeddingService(_fail=True),
            vector_store=FakeVectorStore(),
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
        )
        with pytest.raises(SearchError, match="failed to generate query embedding"):
            service.retrieve(QueryRequest(query="test"))

    def test_vector_store_failure_translated(self) -> None:
        store = FakeVectorStore()
        store._fail = True
        service = RetrievalService(
            embedding_service=FakeEmbeddingService(),
            vector_store=store,
            ranker=SimilarityRanker(),
            filter_builder=MetadataFilterBuilder(),
            processor=QueryProcessor(),
        )
        with pytest.raises(SearchError, match="vector-store search failed"):
            service.retrieve(QueryRequest(query="test"))

    def test_retrieval_error_base_type(self, service: RetrievalService) -> None:
        with pytest.raises(RetrievalError):
            service.retrieve(QueryRequest(query=""))


# ---------------------------------------------------------------------------
# QueryRequest model
# ---------------------------------------------------------------------------

class TestQueryRequest:
    def test_defaults(self) -> None:
        req = QueryRequest(query="test")
        assert req.top_k == 10
        assert req.filters is None
        assert req.collection_name == "knowledge"
        assert req.similarity_threshold is None

    def test_frozen(self) -> None:
        req = QueryRequest(query="test")
        with pytest.raises(AttributeError):
            req.query = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RetrievedChunk model
# ---------------------------------------------------------------------------

class TestRetrievedChunk:
    def test_defaults(self) -> None:
        chunk = RetrievedChunk(content="hello")
        assert chunk.metadata == {}
        assert chunk.score == 0.0
        assert chunk.rank == 0

    def test_frozen(self) -> None:
        chunk = RetrievedChunk(content="hello")
        with pytest.raises(AttributeError):
            chunk.content = "world"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RetrievalResult model
# ---------------------------------------------------------------------------

class TestRetrievalResult:
    def test_defaults(self) -> None:
        result = RetrievalResult(query="test")
        assert result.results == []
        assert result.summary.total_results == 0


# ---------------------------------------------------------------------------
# SearchFilters model
# ---------------------------------------------------------------------------

class TestSearchFilters:
    def test_defaults(self) -> None:
        filters = SearchFilters()
        assert filters.collection_name is None
        assert filters.source is None
        assert filters.filename is None
        assert filters.document_id is None
        assert filters.custom_metadata is None


# ---------------------------------------------------------------------------
# SimilarityRanker integration with service (DI-like)
# ---------------------------------------------------------------------------

class TestRankingIntegration:
    def test_preserves_content(self) -> None:
        chunks = [
            RetrievedChunk(content="first", score=0.5),
            RetrievedChunk(content="second", score=0.9),
        ]
        ranked = SimilarityRanker().rank(chunks)
        assert ranked[0].content == "second"
        assert ranked[1].content == "first"
