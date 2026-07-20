"""Application-facing RAG orchestration service.

``RAGService`` is the single entry point for retrieval-augmented
generation.  It orchestrates retrieval, prompt assembly, generation,
and citation building while remaining completely provider independent.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..logging import get_logger
from ..retrieval.models import QueryRequest, RetrievedChunk
from .exceptions import ContextError
from .models import (
    Citation,
    ContextChunk,
    RAGRequest,
    RAGResponse,
)

if TYPE_CHECKING:
    from ..retrieval.service import RetrievalService
    from .citation import CitationBuilder
    from .generation import GenerationService
    from .interfaces import PromptBuilderProtocol


class RAGService:
    """Orchestrate RAG: retrieve → build prompt → generate → cite.

    Depends only on protocols and project services — never on concrete
    providers or infrastructure.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        prompt_builder: PromptBuilderProtocol,
        generation_service: GenerationService,
        citation_builder: CitationBuilder,
        default_top_k: int = 10,
        max_context_chunks: int = 5,
        max_prompt_tokens: int = 4096,
        default_system_prompt: str | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._prompt_builder = prompt_builder
        self._generation_service = generation_service
        self._citation_builder = citation_builder
        self._default_top_k = default_top_k
        self._max_context_chunks = max_context_chunks
        self._max_prompt_tokens = max_prompt_tokens
        self._default_system_prompt = default_system_prompt
        self._logger = get_logger("rag")

    async def answer(self, request: RAGRequest) -> RAGResponse:
        started_at = time.perf_counter()

        retrieval_start = time.perf_counter()
        retrieval_result = self._retrieval_service.retrieve(
            QueryRequest(
                query=request.query,
                top_k=request.top_k or self._default_top_k,
                collection_name=request.collection_name,
            )
        )
        retrieval_duration_ms = (time.perf_counter() - retrieval_start) * 1000

        context_chunks = self._to_context_chunks(retrieval_result.results)

        if not context_chunks:
            raise ContextError("retrieval returned no context chunks")

        system_prompt = request.system_prompt or self._default_system_prompt or ""

        prompt = self._prompt_builder.build(
            system_prompt=system_prompt,
            query=request.query,
            context_chunks=context_chunks,
            max_context_chunks=self._max_context_chunks,
            max_prompt_tokens=self._max_prompt_tokens,
        )

        logger_extra: dict = {
            "retrieved_count": len(context_chunks),
            "prompt_tokens": prompt.token_count,
        }

        generation_start = time.perf_counter()
        generation_result = await self._generation_service.generate(prompt)
        generation_duration_ms = (time.perf_counter() - generation_start) * 1000

        logger_extra["model"] = generation_result.model
        logger_extra["generation_duration_ms"] = generation_duration_ms

        citations = self._citation_builder.build(context_chunks)

        total_duration_ms = (time.perf_counter() - started_at) * 1000

        self._logger.info(
            "rag completed",
            extra={
                **logger_extra,
                "total_duration_ms": total_duration_ms,
            },
        )

        return RAGResponse(
            query=request.query,
            answer=generation_result.content,
            citations=citations,
            model=generation_result.model,
            provider=generation_result.provider,
            retrieval_duration_ms=retrieval_duration_ms,
            generation_duration_ms=generation_duration_ms,
            total_duration_ms=total_duration_ms,
        )

    @staticmethod
    def _to_context_chunks(
        retrieved: list[RetrievedChunk],
    ) -> list[ContextChunk]:
        return [
            ContextChunk(
                content=r.content,
                metadata=dict(r.metadata),
                score=r.score,
                rank=r.rank,
                chunk_id=r.chunk_id,
            )
            for r in retrieved
        ]
