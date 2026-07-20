from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .registry import TrustedKnowledgeRegistry
from .service import TrustedKnowledgeService

__all__ = [
    "TrustedKnowledgeRegistry",
    "TrustedKnowledgeService",
    "register_trusted_sources",
]


def register_trusted_sources(container: Container, settings: Settings) -> None:
    registry = TrustedKnowledgeRegistry()
    service = TrustedKnowledgeService(registry)

    container.register_instance(TrustedKnowledgeRegistry, registry)
    container.register_instance(TrustedKnowledgeService, service)
