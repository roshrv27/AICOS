"""Embedding infrastructure exception hierarchy.

All embedding exceptions extend :class:`EmbeddingError` so upstream code can
catch a single base type.
"""


class EmbeddingError(Exception):
    """Base exception for all embedding operations."""


class ProviderUnavailableError(EmbeddingError):
    """Raised when the embedding provider cannot be reached."""


class ModelNotFoundError(EmbeddingError):
    """Raised when the specified model is not available on the provider."""


class EmbeddingGenerationError(EmbeddingError):
    """Raised when embedding generation fails after a valid request."""


class ConfigurationError(EmbeddingError):
    """Raised when embedding configuration is invalid."""
