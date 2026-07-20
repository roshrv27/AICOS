"""X (formerly Twitter) adapter.

Placeholder implementation that returns mock domain models.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...knowledge_intelligence.enums import KnowledgeSourceType
from ...knowledge_intelligence.models import (
    Evidence,
    KnowledgeSource,
    TechnologySignal,
)
from ...logging import get_logger
from ..models import AdapterHealth, DiscoveryRequest, DiscoveryResult
from .base import KnowledgeAdapter


class XAdapter(KnowledgeAdapter):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def name(self) -> str:
        return "x"

    def supported_source(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.X

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "x discovery for %s",
            request.target,
        )
        source = KnowledgeSource(
            id=f"x_{request.target}",
            name=f"{request.target} on X",
            source_type=KnowledgeSourceType.X,
            base_url=f"https://x.com/search?q={request.target}",
            last_checked=datetime.now(),
        )
        signal = TechnologySignal(
            id=f"x_sig_{request.target}",
            name=request.target,
            summary=f"{request.target} discussions on X",
            first_seen=datetime.now(),
            evidence=[
                Evidence(
                    id=f"x_ev_{request.target}",
                    source="X",
                    title=f"Trending: {request.target}",
                    url=f"https://x.com/search?q={request.target}",
                ),
            ],
        )
        return DiscoveryResult(
            source_type=KnowledgeSourceType.X,
            sources=[source],
            signals=[signal],
        )

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "x refresh for %s",
            request.target,
        )
        return self.discover(request)

    def verify(self) -> AdapterHealth:
        return AdapterHealth(
            adapter_name=self.name,
            healthy=True,
            last_check=datetime.now(),
            message="x adapter operational",
        )
