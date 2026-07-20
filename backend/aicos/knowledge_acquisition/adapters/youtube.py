"""YouTube adapter.

Placeholder implementation that returns mock domain models.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...knowledge_intelligence.enums import KnowledgeSourceType, ResourceType
from ...knowledge_intelligence.models import KnowledgeResource, KnowledgeSource
from ...logging import get_logger
from ..models import AdapterHealth, DiscoveryRequest, DiscoveryResult
from .base import KnowledgeAdapter


class YouTubeAdapter(KnowledgeAdapter):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def name(self) -> str:
        return "youtube"

    def supported_source(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.YOUTUBE

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "youtube discovery for %s",
            request.target,
        )
        source = KnowledgeSource(
            id=f"yt_{request.target}",
            name=f"{request.target} YouTube",
            source_type=KnowledgeSourceType.YOUTUBE,
            base_url=f"https://youtube.com/results?q={request.target}",
            last_checked=datetime.now(),
        )
        resource = KnowledgeResource(
            id=f"yt_res_{request.target}",
            title=f"Learn {request.target} - YouTube",
            resource_type=ResourceType.VIDEO,
            url=f"https://youtube.com/results?q={request.target}",
            last_verified=datetime.now(),
        )
        return DiscoveryResult(
            source_type=KnowledgeSourceType.YOUTUBE,
            sources=[source],
            resources=[resource],
        )

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "youtube refresh for %s",
            request.target,
        )
        return self.discover(request)

    def verify(self) -> AdapterHealth:
        return AdapterHealth(
            adapter_name=self.name,
            healthy=True,
            last_check=datetime.now(),
            message="youtube adapter operational",
        )
