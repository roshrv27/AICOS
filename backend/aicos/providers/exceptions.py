"""Provider exception hierarchy.

All exceptions extend :class:`ProviderError` so that upstream code can
catch a single base type.
"""


class ProviderError(Exception):
    """Base exception for all provider operations."""


class ProviderRegistrationError(ProviderError):
    """Raised when provider registration fails (duplicate, invalid, etc.)."""


class ProviderExecutionError(ProviderError):
    """Raised when a provider fails during execution."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is invalid."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is not available for use."""
