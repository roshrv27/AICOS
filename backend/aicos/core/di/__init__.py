"""Lightweight, production-ready Dependency Injection framework."""

from .container import Container
from .decorators import service
from .exceptions import (
    CircularDependencyError,
    ServiceNotRegisteredError,
    ServiceRegistrationError,
    ServiceResolutionError,
)
from .lifecycle import ServiceLifetime
from .registry import ServiceRegistry

__all__ = [
    "CircularDependencyError",
    "Container",
    "ServiceLifetime",
    "ServiceNotRegisteredError",
    "ServiceRegistrationError",
    "ServiceRegistry",
    "ServiceResolutionError",
    "service",
]
