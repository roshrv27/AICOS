"""Tests for the RAG orchestration pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from aicos.rag.citation import CitationBuilder
from aicos.rag.exceptions import (
    ContextError,
    GenerationError,
    PromptBuildError,
    RAGError,
)
from aicos.rag.generation import GenerationService
from aicos.rag.models import (
    Citation,
    ContextChunk,
    GenerationResult,
    Prompt,
    PromptSection,
    RAGRequest,
    RAGResponse,
)
from aicos.rag.prompt_builder import PromptBuilder
from aicos.rag.service import RAGService
from aicos.retrieval.models import RetrievedChunk, RetrievalResult, RetrievalSummary


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

@dataclass
class FakeRetrievalService:
    _empty: bool = False

    def retrieve(self, request: Any) -> RetrievalResult:
        if self._empty:
            return RetrievalResult(
                query=request.query,
                results=[],
                summary=RetrievalSummary(),
            )
        chunks = [
            RetrievedChunk(
                content=f"chunk {i} content for answering",
                metadata={"source": f"/path/doc{i}.md", "filename": f"doc{i}.md"},
                score=1.0 - (i * 0.1),
                rank=i,
                chunk_id=f"chunk_{i}",
                collection_name=request.collection_name,
            )
            for i in range(3)
        ]
        return RetrievalResult(
            query=request.query,
            results=chunks,
            summary=RetrievalSummary(total_results=len(chunks)),
        )


@dataclass
class FakeModelRouter:
    _fail: bool = False

    async def generate(self, request: Any) -> Any:
        if self._fail:
            raise RuntimeError("model unavailable")
        return FakeModelResponse(
            content="This is the generated answer based on the context.",
            model_name="test-model",
            provider="test-provider",
        )


@dataclass
class FakeModelResponse:
    content: str
    model_name: str
    provider: str
    latency_ms: float = 100.0


class FakeFailingModelRouter:
    async def generate(self, request: Any) -> Any:
        raise RuntimeError("LLM provider unavailable")


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def test_build_basic(self) -> None:
        chunks = [
            ContextChunk(content="content one", chunk_id="c1"),
            ContextChunk(content="content two", chunk_id="c2"),
        ]
        prompt = PromptBuilder().build(
            system_prompt="You are a helper.",
            query="what is this?",
            context_chunks=chunks,
        )
        assert len(prompt.sections) == 2
        assert prompt.sections[0].role == "system"
        assert prompt.sections[1].role == "user"
        assert "content one" in prompt.sections[1].content
        assert "content two" in prompt.sections[1].content
        assert "what is this?" in prompt.sections[1].content

    def test_empty_query(self) -> None:
        with pytest.raises(PromptBuildError, match="empty"):
            PromptBuilder().build(
                system_prompt="You are a helper.",
                query="",
                context_chunks=[],
            )

    def test_empty_system_prompt(self) -> None:
        with pytest.raises(PromptBuildError, match="empty"):
            PromptBuilder().build(
                system_prompt="",
                query="hello",
                context_chunks=[],
            )

    def test_max_context_chunks(self) -> None:
        chunks = [ContextChunk(content=f"chunk {i}", chunk_id=f"c{i}") for i in range(10)]
        prompt = PromptBuilder().build(
            system_prompt="You are a helper.",
            query="hello",
            context_chunks=chunks,
            max_context_chunks=3,
        )
        context_text = prompt.sections[1].content
        assert "chunk 0" in context_text
        assert "chunk 2" in context_text
        assert "chunk 3" not in context_text

    def test_max_prompt_tokens_truncates(self) -> None:
        chunks = [ContextChunk(content="A" * 2000, chunk_id=f"c{i}") for i in range(5)]
        prompt = PromptBuilder().build(
            system_prompt="System prompt.",
            query="hello",
            context_chunks=chunks,
            max_context_chunks=5,
            max_prompt_tokens=100,
        )
        assert prompt.token_count <= 100

    def test_no_context(self) -> None:
        prompt = PromptBuilder().build(
            system_prompt="You are a helper.",
            query="hello",
            context_chunks=[],
        )
        assert len(prompt.sections) == 2
        assert prompt.sections[1].content == "hello"

    def test_prompt_frozen(self) -> None:
        prompt = PromptBuilder().build(
            system_prompt="sys", query="q", context_chunks=[]
        )
        with pytest.raises(AttributeError):
            prompt.sections = []  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CitationBuilder
# ---------------------------------------------------------------------------

class TestCitationBuilder:
    def test_build_basic(self) -> None:
        chunks = [
            ContextChunk(content="a", chunk_id="c1", metadata={"source": "/a.md", "filename": "a.md"}, score=0.9, rank=0),
            ContextChunk(content="b", chunk_id="c2", metadata={"source": "/b.md", "filename": "b.md"}, score=0.8, rank=1),
        ]
        citations = CitationBuilder().build(chunks)
        assert len(citations) == 2
        assert citations[0].chunk_id == "c1"
        assert citations[0].source == "/a.md"
        assert citations[1].chunk_id == "c2"

    def test_deduplicates(self) -> None:
        chunks = [
            ContextChunk(content="a", chunk_id="c1"),
            ContextChunk(content="b", chunk_id="c1"),
            ContextChunk(content="c", chunk_id="c2"),
        ]
        citations = CitationBuilder().build(chunks)
        assert len(citations) == 2
        assert citations[0].chunk_id == "c1"
        assert citations[1].chunk_id == "c2"

    def test_empty(self) -> None:
        assert CitationBuilder().build([]) == []

    def test_preserves_order(self) -> None:
        chunks = [
            ContextChunk(content="first", chunk_id="c3"),
            ContextChunk(content="second", chunk_id="c1"),
            ContextChunk(content="third", chunk_id="c2"),
        ]
        citations = CitationBuilder().build(chunks)
        assert [c.chunk_id for c in citations] == ["c3", "c1", "c2"]

    def test_frozen(self) -> None:
        citations = CitationBuilder().build(
            [ContextChunk(content="a", chunk_id="c1")]
        )
        with pytest.raises(AttributeError):
            citations[0].chunk_id = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GenerationService
# ---------------------------------------------------------------------------

class TestGenerationService:
    @pytest.mark.asyncio
    async def test_generate_basic(self) -> None:
        router = FakeModelRouter()
        service = GenerationService(model_router=router)
        prompt = Prompt(
            sections=[
                PromptSection(role="system", content="You are a helper."),
                PromptSection(role="user", content="What is this?"),
            ],
        )
        result = await service.generate(prompt)
        assert isinstance(result, GenerationResult)
        assert result.content == "This is the generated answer based on the context."
        assert result.model == "test-model"
        assert result.provider == "test-provider"

    @pytest.mark.asyncio
    async def test_generate_failure_translated(self) -> None:
        service = GenerationService(model_router=FakeFailingModelRouter())
        prompt = Prompt(
            sections=[
                PromptSection(role="system", content="sys"),
                PromptSection(role="user", content="q"),
            ],
        )
        with pytest.raises(GenerationError, match="generation failed"):
            await service.generate(prompt)

    @pytest.mark.asyncio
    async def test_generation_error_base_type(self) -> None:
        service = GenerationService(model_router=FakeFailingModelRouter())
        prompt = Prompt(
            sections=[
                PromptSection(role="system", content="sys"),
                PromptSection(role="user", content="q"),
            ],
        )
        with pytest.raises(RAGError):
            await service.generate(prompt)


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------

class TestRAGService:
    @pytest.fixture
    def service(self) -> RAGService:
        return RAGService(
            retrieval_service=FakeRetrievalService(),
            prompt_builder=PromptBuilder(),
            generation_service=GenerationService(model_router=FakeModelRouter()),
            citation_builder=CitationBuilder(),
            default_top_k=10,
            max_context_chunks=5,
            max_prompt_tokens=4096,
            default_system_prompt="You are a helpful assistant.",
        )

    @pytest.mark.asyncio
    async def test_answer_basic(self, service: RAGService) -> None:
        response = await service.answer(RAGRequest(query="test query"))
        assert isinstance(response, RAGResponse)
        assert response.query == "test query"
        assert response.answer == "This is the generated answer based on the context."
        assert len(response.citations) > 0
        assert response.model == "test-model"
        assert response.provider == "test-provider"

    @pytest.mark.asyncio
    async def test_answer_empty_query(self, service: RAGService) -> None:
        with pytest.raises(PromptBuildError):
            await service.answer(RAGRequest(query=""))

    @pytest.mark.asyncio
    async def test_answer_empty_context(self) -> None:
        svc = RAGService(
            retrieval_service=FakeRetrievalService(_empty=True),
            prompt_builder=PromptBuilder(),
            generation_service=GenerationService(model_router=FakeModelRouter()),
            citation_builder=CitationBuilder(),
        )
        with pytest.raises(ContextError, match="no context"):
            await svc.answer(RAGRequest(query="test"))

    @pytest.mark.asyncio
    async def test_answer_citations_preserved(self, service: RAGService) -> None:
        response = await service.answer(RAGRequest(query="test"))
        for citation in response.citations:
            assert isinstance(citation, Citation)
            assert citation.chunk_id

    @pytest.mark.asyncio
    async def test_answer_system_prompt_override(self) -> None:
        svc = RAGService(
            retrieval_service=FakeRetrievalService(),
            prompt_builder=PromptBuilder(),
            generation_service=GenerationService(model_router=FakeModelRouter()),
            citation_builder=CitationBuilder(),
            default_system_prompt="Default prompt.",
        )
        response = await svc.answer(
            RAGRequest(query="test", system_prompt="Custom prompt.")
        )
        assert response.answer

    @pytest.mark.asyncio
    async def test_answer_generation_failure(self) -> None:
        svc = RAGService(
            retrieval_service=FakeRetrievalService(),
            prompt_builder=PromptBuilder(),
            generation_service=GenerationService(
                model_router=FakeFailingModelRouter()
            ),
            citation_builder=CitationBuilder(),
            default_system_prompt="You are a helper.",
        )
        with pytest.raises(GenerationError):
            await svc.answer(RAGRequest(query="test"))

    @pytest.mark.asyncio
    async def test_answer_top_k_default(self) -> None:
        svc = RAGService(
            retrieval_service=FakeRetrievalService(),
            prompt_builder=PromptBuilder(),
            generation_service=GenerationService(model_router=FakeModelRouter()),
            citation_builder=CitationBuilder(),
            default_top_k=5,
            default_system_prompt="You are a helper.",
        )
        response = await svc.answer(RAGRequest(query="test"))
        assert response.answer

    @pytest.mark.asyncio
    async def test_answer_timing(self, service: RAGService) -> None:
        response = await service.answer(RAGRequest(query="test"))
        assert response.retrieval_duration_ms > 0
        assert response.generation_duration_ms > 0
        assert response.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_rag_error_base_type(self, service: RAGService) -> None:
        with pytest.raises(RAGError):
            await service.answer(RAGRequest(query=""))


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestRAGRequest:
    def test_defaults(self) -> None:
        req = RAGRequest(query="hello")
        assert req.top_k == 10
        assert req.collection_name == "knowledge"
        assert req.system_prompt is None

    def test_frozen(self) -> None:
        req = RAGRequest(query="hello")
        with pytest.raises(AttributeError):
            req.query = "world"  # type: ignore[misc]


class TestContextChunk:
    def test_defaults(self) -> None:
        chunk = ContextChunk(content="hello")
        assert chunk.metadata == {}
        assert chunk.score == 0.0
        assert chunk.rank == 0
        assert chunk.chunk_id == ""


class TestCitation:
    def test_defaults(self) -> None:
        cite = Citation(chunk_id="c1")
        assert cite.source is None
        assert cite.score == 0.0


class TestPromptSection:
    def test_creation(self) -> None:
        section = PromptSection(role="user", content="hello")
        assert section.role == "user"
        assert section.content == "hello"


class TestPrompt:
    def test_defaults(self) -> None:
        prompt = Prompt()
        assert prompt.sections == []
        assert prompt.context_chunks == []
        assert prompt.token_count == 0


class TestGenerationResult:
    def test_defaults(self) -> None:
        result = GenerationResult(content="answer", model="m", provider="p")
        assert result.latency_ms == 0.0


class TestRAGResponse:
    def test_defaults(self) -> None:
        resp = RAGResponse(query="q", answer="a")
        assert resp.citations == []
        assert resp.model == ""
