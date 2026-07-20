"""Provider-neutral protocols for the knowledge acquisition engine.

Application code depends **only** on the protocols defined here.
Concrete implementations are wired via DI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..knowledge_intelligence.enums import KnowledgeSourceType
from .models import (
    AdapterHealth,
    DiscoveryRequest,
    DiscoveryResult,
)


@runtime_checkable
class KnowledgeAdapterProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def supported_source(self) -> KnowledgeSourceType: ...

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult: ...

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult: ...

    def verify(self) -> AdapterHealth: ...


@runtime_checkable
class NormalizationServiceProtocol(Protocol):
    def normalize(self, result: DiscoveryResult) -> DiscoveryResult: ...


@runtime_checkable
class DiscoveryOrchestratorProtocol(Protocol):
    def discover(self, request: DiscoveryRequest) -> DiscoveryResult: ...

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult: ...

    def verify_source(self, source_type: KnowledgeSourceType) -> AdapterHealth: ...

    def verify_all(self) -> list[AdapterHealth]: ...
