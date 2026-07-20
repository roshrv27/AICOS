"""Provider-neutral protocols for the knowledge intelligence domain.

Application code depends **only** on the protocols defined here.
Concrete implementations are wired via DI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import (
    DiscoveryJob,
    Evidence,
    KnowledgeResource,
    KnowledgeSource,
    KnowledgeVersion,
    TechnologySignal,
    TrendSnapshot,
)


@runtime_checkable
class KnowledgeIntelligenceDomainServiceProtocol(Protocol):
    def validate_sources(self, sources: list[KnowledgeSource]) -> None: ...
    def validate_signals(self, signals: list[TechnologySignal]) -> None: ...
    def validate_evidence(self, evidence_list: list[Evidence]) -> None: ...
    def validate_resources(self, resources: list[KnowledgeResource]) -> None: ...
    def validate_trends(self, trends: list[TrendSnapshot]) -> None: ...
    def validate_versions(self, versions: list[KnowledgeVersion]) -> None: ...
    def validate_jobs(self, jobs: list[DiscoveryJob]) -> None: ...
