"""Vector-store protocol interface.

Application code depends **only** on ``VectorStorePort``.  Concrete
implementations (ChromaDB, FAISS, Qdrant, …) implement this protocol
and are wired via the DI container.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .models import EmbeddingDocument, SearchResult


@runtime_checkable
class VectorStorePort(Protocol):
    """Storage abstraction for vector databases.

    Every method operates on a named collection.  Collections are created
    implicitly on first use or explicitly via ``create_collection``.
    """

    def create_collection(self, name: str) -> None:
        """Create a new collection.

        Raises :class:`CollectionError` if the collection already exists.
        """
        ...

    def delete_collection(self, name: str) -> None:
        """Delete a collection and all its documents.

        Raises :class:`CollectionError` if the collection does not exist.
        """
        ...

    def collection_exists(self, name: str) -> bool:
        """Return ``True`` when a collection with *name* exists."""
        ...

    def list_collections(self) -> list[str]:
        """Return the name of every collection."""
        ...

    def add_document(self, collection: str, document: EmbeddingDocument) -> None:
        """Insert one document into *collection*.

        Raises :class:`DocumentError` when a document with the same id
        already exists.
        """
        ...

    def update_document(self, collection: str, document: EmbeddingDocument) -> None:
        """Replace an existing document in *collection*.

        Raises :class:`DocumentError` when *id* is not found.
        """
        ...

    def delete_document(self, collection: str, document_id: str) -> None:
        """Remove one document by id from *collection*.

        Raises :class:`DocumentError` when *document_id* is not found.
        """
        ...

    def get_document(self, collection: str, document_id: str) -> EmbeddingDocument | None:
        """Retrieve a single document by id, or ``None``."""
        ...

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Semantic (vector) search over *collection*.

        :param collection: Target collection name.
        :param query_vector: Embedding vector to search with.
        :param top_k: Maximum number of results to return.
        :param filter: Optional metadata filter dict (exact-match).
        :returns: Ranked results ordered by descending similarity.
        """
        ...
