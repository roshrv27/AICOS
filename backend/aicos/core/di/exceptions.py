"""Dependency Injection framework exceptions."""


class DependencyInjectionError(Exception):
    """Base class for Dependency Injection failures."""


class ServiceNotRegisteredError(DependencyInjectionError):
    """Raised when no provider exists for a requested service."""


class CircularDependencyError(DependencyInjectionError):
    """Raised when constructor resolution encounters a dependency cycle."""


class ServiceRegistrationError(DependencyInjectionError):
    """Raised when a service registration is invalid or conflicts with another."""


class ServiceResolutionError(DependencyInjectionError):
    """Raised when a registered service cannot be instantiated."""
