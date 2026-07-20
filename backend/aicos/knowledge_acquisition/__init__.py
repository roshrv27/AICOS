"""Knowledge acquisition engine package.

Exports the orchestrator and a ``register_knowledge_acquisition`` wiring
function that the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .adapters.github import GitHubAdapter
from .adapters.official_docs import OfficialDocsAdapter
from .adapters.research import ResearchAdapter
from .adapters.x import XAdapter
from .adapters.youtube import YouTubeAdapter
from .normalizer import NormalizationService
from .orchestrator import DiscoveryOrchestrator
from .registry import AdapterRegistry

__all__ = [
    "DiscoveryOrchestrator",
    "register_knowledge_acquisition",
]


def register_knowledge_acquisition(
    container: Container,
    settings: Settings,
) -> None:
    acquisition_config: dict = getattr(settings, "knowledge_acquisition", {})

    container.register(NormalizationService, lifetime=ServiceLifetime.SINGLETON)

    _adapter_pairs: list[tuple[str, type]] = [
        ("official_docs", OfficialDocsAdapter),
        ("github", GitHubAdapter),
        ("youtube", YouTubeAdapter),
        ("research", ResearchAdapter),
        ("x", XAdapter),
    ]

    def _create_registry(ctr: Container) -> AdapterRegistry:
        registry = AdapterRegistry()
        for name, cls in _adapter_pairs:
            adapter_cfg = acquisition_config.get(name, {})
            adapter = cls(adapter_cfg)
            registry.register(adapter)
        return registry

    container.register_factory(
        AdapterRegistry,
        _create_registry,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register(
        DiscoveryOrchestrator,
        lifetime=ServiceLifetime.SINGLETON,
    )
