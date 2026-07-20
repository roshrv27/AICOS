"""Retrieval exception hierarchy.

All exceptions extend :class:`RetrievalError` so that upstream code
can catch a single base type.  No vector-database or provider-specific
exceptions escape this layer.
"""


class RetrievalError(Exception):
    """Base exception for all retrieval operations."""


class QueryValidationError(RetrievalError):
    """Raised when a query is empty, whitespace-only, or otherwise invalid."""


class RankingError(RetrievalError):
    """Raised when result ranking fails."""


class FilterError(RetrievalError):
    """Raised when metadata filter construction or application fails."""


class SearchError(RetrievalError):
    """Raised when embedding generation or vector-store search fails."""
