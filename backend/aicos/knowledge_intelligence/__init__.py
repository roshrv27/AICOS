"""Knowledge intelligence domain package.

Exports the domain service and a ``register_knowledge_intelligence``
wiring function that the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .service import KnowledgeIntelligenceDomainService

__all__ = [
    "KnowledgeIntelligenceDomainService",
    "register_knowledge_intelligence",
]


def register_knowledge_intelligence(container: Container, settings: Settings) -> None:
    container.register(
        KnowledgeIntelligenceDomainService,
        lifetime=ServiceLifetime.SINGLETON,
    )
