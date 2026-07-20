"""LLM generation for RAG.

``GenerationService`` is the ONLY component that invokes ``ModelRouter``.
It translates provider/LLM exceptions into ``GenerationError`` and
returns a provider-independent ``GenerationResult``.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from aicos.llm.models import ChatMessage, ModelRequest

from ..logging import get_logger
from .exceptions import GenerationError
from .models import GenerationResult, Prompt

if TYPE_CHECKING:
    from aicos.llm import ModelRouter


class GenerationService:
    """Generate answers via ModelRouter, translating exceptions."""

    def __init__(self, model_router: ModelRouter) -> None:
        self._model_router = model_router
        self._logger = get_logger("rag.generation")

    async def generate(self, prompt: Prompt) -> GenerationResult:
        started_at = time.perf_counter()

        messages = tuple(
            ChatMessage(role=s.role, content=s.content) for s in prompt.sections
        )

        request = ModelRequest(
            messages=messages,
            stream=False,
        )

        try:
            response = await self._model_router.generate(request)
        except Exception as exc:
            raise GenerationError(f"generation failed: {exc}") from exc

        latency_ms = (time.perf_counter() - started_at) * 1000

        self._logger.info(
            "generation completed",
            extra={
                "model": response.model_name,
                "provider": response.provider,
                "duration_ms": latency_ms,
            },
        )

        return GenerationResult(
            content=response.content,
            model=response.model_name,
            provider=response.provider,
            latency_ms=latency_ms,
        )
