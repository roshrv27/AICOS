"""Vector store exception hierarchy.

All vector-store exceptions extend :class:`PersistenceError` so that upstream
code can catch a single base type.
"""

from ..exceptions import PersistenceError


class VectorStoreError(PersistenceError):
    """Base exception for all vector-store operations."""


class CollectionError(VectorStoreError):
    """Raised when a collection operation fails."""


class DocumentError(VectorStoreError):
    """Raised when a document operation fails."""


class SearchError(VectorStoreError):
    """Raised when a search operation fails."""
