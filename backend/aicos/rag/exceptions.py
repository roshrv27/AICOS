"""RAG exception hierarchy.

All exceptions extend :class:`RAGError` so that upstream code
can catch a single base type.  No LLM, retrieval, or provider-specific
exceptions escape this layer.
"""


class RAGError(Exception):
    """Base exception for all RAG operations."""


class PromptBuildError(RAGError):
    """Raised when prompt assembly fails (e.g. context too large)."""


class GenerationError(RAGError):
    """Raised when LLM generation fails."""


class CitationError(RAGError):
    """Raised when citation assembly fails."""


class ContextError(RAGError):
    """Raised when retrieval returns no context."""
