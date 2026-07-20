"""Model Router exceptions."""


class ModelRouterError(Exception):
    """Base class for model-routing errors."""


class ProviderUnavailableError(ModelRouterError):
    """Raised when a provider cannot accept a request."""


class ModelNotFoundError(ModelRouterError):
    """Raised when no registered model matches an explicit selection."""


class RoutingError(ModelRouterError):
    """Raised when no healthy route can satisfy a request."""


class ProviderTimeoutError(ProviderUnavailableError):
    """Raised when a provider request exceeds its configured timeout."""


class UnsupportedCapabilityError(RoutingError):
    """Raised when registered models cannot meet requested capabilities."""
