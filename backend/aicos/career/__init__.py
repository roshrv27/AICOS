"""Career intelligence domain package.

Exports the domain service and a ``register_career`` wiring function
that the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .service import CareerDomainService

__all__ = [
    "CareerDomainService",
    "register_career",
]


def register_career(container: Container, settings: Settings) -> None:
    container.register(CareerDomainService, lifetime=ServiceLifetime.SINGLETON)
