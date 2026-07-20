"""Research paper adapter.

Placeholder implementation that returns mock domain models.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...knowledge_intelligence.enums import KnowledgeSourceType, ResourceType
from ...knowledge_intelligence.models import (
    KnowledgeResource,
    KnowledgeSource,
    TechnologySignal,
)
from ...logging import get_logger
from ..models import AdapterHealth, DiscoveryRequest, DiscoveryResult
from .base import KnowledgeAdapter


class ResearchAdapter(KnowledgeAdapter):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def name(self) -> str:
        return "research"

    def supported_source(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.RESEARCH_PAPER

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "research discovery for %s",
            request.target,
        )
        source = KnowledgeSource(
            id=f"research_{request.target}",
            name=f"{request.target} Research",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            base_url=f"https://scholar.example.com?q={request.target}",
            last_checked=datetime.now(),
        )
        signal = TechnologySignal(
            id=f"research_sig_{request.target}",
            name=request.target,
            summary=f"New research published on {request.target}",
            first_seen=datetime.now(),
        )
        return DiscoveryResult(
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            sources=[source],
            signals=[signal],
        )

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "research refresh for %s",
            request.target,
        )
        return self.discover(request)

    def verify(self) -> AdapterHealth:
        return AdapterHealth(
            adapter_name=self.name,
            healthy=True,
            last_check=datetime.now(),
            message="research adapter operational",
        )
