"""Provider-neutral vector-store abstraction for AICOS.

Usage via DI container::

    register_vector_store(container, settings)
    store = container.resolve(VectorStorePort)

Direct usage::

    import chromadb
    from aicos.persistence.vector_store import ChromaDBVectorStore

    client = chromadb.PersistentClient(path="data/chroma")
    store = ChromaDBVectorStore(client)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.di import ServiceLifetime
from .chroma import ChromaDBVectorStore
from .collections import CollectionManager
from .exceptions import CollectionError, DocumentError, SearchError, VectorStoreError
from .interfaces import VectorStorePort
from .models import EmbeddingDocument, SearchResult

if TYPE_CHECKING:
    from ...core.di import Container
    from ...settings import Settings

__all__ = [
    "ChromaDBVectorStore",
    "CollectionError",
    "CollectionManager",
    "DocumentError",
    "EmbeddingDocument",
    "SearchError",
    "SearchResult",
    "VectorStoreError",
    "VectorStorePort",
    "register_vector_store",
]


def register_vector_store(container: Container, settings: Settings) -> None:
    """Register vector-store services in the DI container.

    ``ChromaDBVectorStore`` is registered as a singleton under the
    ``VectorStorePort`` protocol.  ``CollectionManager`` is registered
    as transient.
    """

    def create_store() -> ChromaDBVectorStore:
        import chromadb

        chroma_config = settings.chromadb
        if chroma_config.use_http:
            client = chromadb.HttpClient(
                host=chroma_config.host,
                port=chroma_config.port,
            )
        else:
            client = chromadb.PersistentClient(
                path=str(chroma_config.persist_directory),
            )
        return ChromaDBVectorStore(client)

    container.register_factory(ChromaDBVectorStore, create_store, lifetime=ServiceLifetime.SINGLETON)
    container.register_factory(
        VectorStorePort,
        lambda: container.resolve(ChromaDBVectorStore),
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        CollectionManager,
        lambda: CollectionManager(container.resolve(ChromaDBVectorStore)._client),
        lifetime=ServiceLifetime.TRANSIENT,
    )
