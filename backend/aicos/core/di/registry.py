"""Thread-safe registration storage for the DI container."""

from __future__ import annotations

from threading import RLock
from typing import Any

from .exceptions import ServiceNotRegisteredError, ServiceRegistrationError
from .provider import ServiceProvider


class ServiceRegistry:
    """Owns service-provider registrations independently from resolution logic."""

    def __init__(self) -> None:
        self._providers: dict[type[Any], ServiceProvider] = {}
        self._lock = RLock()

    def add(self, service_type: type[Any], provider: ServiceProvider) -> None:
        """Add a new provider; replacing requires the explicit ``replace`` method."""

        with self._lock:
            if service_type in self._providers:
                raise ServiceRegistrationError(f"service already registered: {_service_name(service_type)}")
            self._providers[service_type] = provider

    def replace(self, service_type: type[Any], provider: ServiceProvider) -> None:
        """Atomically replace a provider, primarily for isolated tests."""

        with self._lock:
            if service_type not in self._providers:
                raise ServiceNotRegisteredError(f"service is not registered: {_service_name(service_type)}")
            self._providers[service_type] = provider

    def get(self, service_type: type[Any]) -> ServiceProvider:
        """Return a registered provider or raise a domain-specific error."""

        with self._lock:
            provider = self._providers.get(service_type)
        if provider is None:
            raise ServiceNotRegisteredError(f"service is not registered: {_service_name(service_type)}")
        return provider

    def contains(self, service_type: type[Any]) -> bool:
        with self._lock:
            return service_type in self._providers


def _service_name(service_type: type[Any]) -> str:
    return getattr(service_type, "__name__", repr(service_type))
