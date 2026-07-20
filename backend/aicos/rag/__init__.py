"""RAG orchestration package.

Exports the service class and a ``register_rag`` wiring function
that the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .citation import CitationBuilder
from .generation import GenerationService
from .prompt_builder import PromptBuilder
from .service import RAGService

__all__ = [
    "RAGService",
    "register_rag",
]


def register_rag(container: Container, settings: Settings) -> None:
    rag_config = settings.rag

    container.register(PromptBuilder, lifetime=ServiceLifetime.SINGLETON)
    container.register(CitationBuilder, lifetime=ServiceLifetime.SINGLETON)

    container.register_factory(
        GenerationService,
        lambda: GenerationService(
            model_router=container.resolve("ModelRouter"),
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )

    container.register_factory(
        RAGService,
        lambda: RAGService(
            retrieval_service=container.resolve("RetrievalService"),
            prompt_builder=container.resolve(PromptBuilder),
            generation_service=container.resolve(GenerationService),
            citation_builder=container.resolve(CitationBuilder),
            default_top_k=rag_config.default_top_k,
            max_context_chunks=rag_config.max_context_chunks,
            max_prompt_tokens=rag_config.max_prompt_tokens,
            default_system_prompt=rag_config.default_system_prompt,
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )
