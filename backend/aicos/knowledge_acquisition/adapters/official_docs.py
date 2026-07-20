"""Official documentation adapter.

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


class OfficialDocsAdapter(KnowledgeAdapter):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def name(self) -> str:
        return "official_docs"

    def supported_source(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.OFFICIAL_DOCUMENTATION

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "official_docs discovery for %s",
            request.target,
        )
        source = KnowledgeSource(
            id=f"docs_{request.target}",
            name=f"{request.target} Documentation",
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            base_url=f"https://docs.{request.target}.example.com",
            last_checked=datetime.now(),
        )
        return DiscoveryResult(
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            sources=[source],
        )

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "official_docs refresh for %s",
            request.target,
        )
        return self.discover(request)

    def verify(self) -> AdapterHealth:
        return AdapterHealth(
            adapter_name=self.name,
            healthy=True,
            last_check=datetime.now(),
            message="official_docs adapter operational",
        )
