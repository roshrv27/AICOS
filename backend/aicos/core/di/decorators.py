"""Decorator-based service registration helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from .container import Container
from .lifecycle import ServiceLifetime


ServiceType = TypeVar("ServiceType")


def service(
    container: Container,
    *,
    interface: type[object] | None = None,
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
) -> Callable[[type[ServiceType]], type[ServiceType]]:
    """Register a class when it is declared.

    ``@service(container, interface=Port)`` registers the decorated concrete
    implementation under ``Port``; omitting ``interface`` registers the class
    as itself.
    """

    def register(implementation: type[ServiceType]) -> type[ServiceType]:
        container.register(interface or implementation, implementation, lifetime=lifetime)
        return implementation

    return register
