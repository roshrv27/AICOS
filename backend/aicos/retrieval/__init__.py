"""Retrieval package.

Exports the service class and a ``register_retrieval`` wiring function
that the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .filters import MetadataFilterBuilder
from .ranking import SimilarityRanker
from .service import QueryProcessor, RetrievalService

__all__ = [
    "RetrievalService",
    "register_retrieval",
]


def register_retrieval(container: Container, settings: Settings) -> None:
    retrieval_config = settings.retrieval

    container.register(MetadataFilterBuilder, lifetime=ServiceLifetime.SINGLETON)
    container.register(QueryProcessor, lifetime=ServiceLifetime.SINGLETON)
    container.register(SimilarityRanker, lifetime=ServiceLifetime.SINGLETON)

    container.register_factory(
        RetrievalService,
        lambda: RetrievalService(
            embedding_service=container.resolve("EmbeddingService"),
            vector_store=container.resolve("VectorStorePort"),
            ranker=container.resolve(SimilarityRanker),
            filter_builder=container.resolve(MetadataFilterBuilder),
            processor=container.resolve(QueryProcessor),
            default_top_k=retrieval_config.default_top_k,
            max_top_k=retrieval_config.max_top_k,
            similarity_threshold=retrieval_config.similarity_threshold,
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )
