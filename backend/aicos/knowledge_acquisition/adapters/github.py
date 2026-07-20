"""GitHub adapter.

Placeholder implementation that returns mock domain models.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...knowledge_intelligence.enums import (
    KnowledgeSourceType,
    ResourceType,
    TechnologyStatus,
)
from ...knowledge_intelligence.models import (
    Evidence,
    KnowledgeResource,
    KnowledgeSource,
    TechnologySignal,
)
from ...logging import get_logger
from ..models import AdapterHealth, DiscoveryRequest, DiscoveryResult
from .base import KnowledgeAdapter


class GitHubAdapter(KnowledgeAdapter):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def name(self) -> str:
        return "github"

    def supported_source(self) -> KnowledgeSourceType:
        return KnowledgeSourceType.GITHUB

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "github discovery for %s",
            request.target,
        )
        source = KnowledgeSource(
            id=f"github_{request.target}",
            name=f"{request.target} GitHub",
            source_type=KnowledgeSourceType.GITHUB,
            base_url=f"https://github.com/{request.target}",
            last_checked=datetime.now(),
        )
        signal = TechnologySignal(
            id=f"github_sig_{request.target}",
            name=request.target,
            summary=f"{request.target} trending on GitHub",
            status=TechnologyStatus.EMERGING,
            first_seen=datetime.now(),
            evidence=[
                Evidence(
                    id=f"github_ev_{request.target}",
                    source="GitHub",
                    title=f"{request.target} repositories",
                    url=f"https://github.com/topics/{request.target}",
                ),
            ],
        )
        return DiscoveryResult(
            source_type=KnowledgeSourceType.GITHUB,
            sources=[source],
            signals=[signal],
        )

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        self._logger.info(
            "github refresh for %s",
            request.target,
        )
        return self.discover(request)

    def verify(self) -> AdapterHealth:
        return AdapterHealth(
            adapter_name=self.name,
            healthy=True,
            last_check=datetime.now(),
            message="github adapter operational",
        )
