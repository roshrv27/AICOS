"""Knowledge-ingestion package.

Exports the service class and a ``register_knowledge`` wiring function
that the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .chunking import RecursiveCharacterChunker
from .indexer import DocumentIndexer
from .loaders import MarkdownLoader, PDFLoader, TextLoader
from .metadata import MetadataExtractor
from .service import KnowledgeIngestionService

__all__ = [
    "DocumentIndexer",
    "KnowledgeIngestionService",
    "register_knowledge",
]


def register_knowledge(container: Container, settings: Settings) -> None:
    loaders = [
        TextLoader(),
        MarkdownLoader(),
        PDFLoader(),
    ]

    container.register_instance(list, loaders)
    container.register(RecursiveCharacterChunker, lifetime=ServiceLifetime.SINGLETON)
    container.register(MetadataExtractor, lifetime=ServiceLifetime.SINGLETON)

    container.register_factory(
        DocumentIndexer,
        lambda: DocumentIndexer(
            embedding_service=container.resolve("EmbeddingService"),
            vector_store=container.resolve("VectorStorePort"),
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )

    container.register_factory(
        KnowledgeIngestionService,
        lambda: KnowledgeIngestionService(
            loaders=container.resolve(list),
            chunker=container.resolve(RecursiveCharacterChunker),
            metadata_extractor=container.resolve(MetadataExtractor),
            indexer=container.resolve(DocumentIndexer),
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )
