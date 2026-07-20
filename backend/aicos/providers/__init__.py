"""Provider infrastructure package.

Exports the registry and a ``register_providers`` wiring function that
the app composition root calls.
"""

from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .integrations import (
    ArxivIntegration,
    DuckDuckGoIntegration,
    GitHubIntegration,
    GoogleSearchIntegration,
    MCPSearchIntegration,
    OfficialDocsIntegration,
    SourceTrustPolicy,
    YouTubeIntegration,
)
from .integrations.trust import SourceTrustPolicy
from .models import ProviderSettings
from .providers.github import GitHubProvider
from .providers.official_docs import OfficialDocsProvider
from .providers.research import ResearchProvider
from .providers.search import (
    DuckDuckGoSearchProvider,
    GoogleSearchProvider,
    MCPSearchProvider,
)
from .providers.youtube import YouTubeProvider
from .registry import ProviderRegistry

__all__ = [
    "ProviderRegistry",
    "register_providers",
    "SourceTrustPolicy",
    "ProviderSettings",
]


def register_providers(
    container: Container,
    settings: Settings,
) -> None:
    provider_config: dict = getattr(settings, "providers", {})

    _placeholder_classes: list[type] = [
        MCPSearchProvider,
        GoogleSearchProvider,
        DuckDuckGoSearchProvider,
        GitHubProvider,
        YouTubeProvider,
        ResearchProvider,
        OfficialDocsProvider,
    ]

    _integration_classes: dict[str, type] = {
        "mcp_search": MCPSearchIntegration,
        "google_search": GoogleSearchIntegration,
        "duckduckgo_search": DuckDuckGoIntegration,
        "github": GitHubIntegration,
        "youtube": YouTubeIntegration,
        "research": ArxivIntegration,
        "official_docs": OfficialDocsIntegration,
    }

    _provider_configs: dict[str, dict] = {}
    for cls in _placeholder_classes:
        name = getattr(cls, "_config_key", cls.__name__.lower())
        _provider_configs[name] = provider_config.get(name, {})

    def _create_registry(ctr: Container) -> ProviderRegistry:
        registry = ProviderRegistry()
        for cls in _placeholder_classes:
            name = getattr(cls, "_config_key", cls.__name__.lower())
            cfg = _provider_configs[name]
            provider = cls(cfg)
            registry.register(provider)

        ps: ProviderSettings = getattr(ctr, "_provider_settings", None) or ProviderSettings()
        for pname, pcls in _integration_classes.items():
            if pname not in ps.enabled_providers:
                continue
            cfg = provider_config.get(pname, {})
            cfg.setdefault("timeout", ps.timeouts.get(pname, ps.timeouts["default"]))
            cfg.setdefault("retry_count", ps.retry_count)
            cfg.setdefault("user_agent", ps.user_agent)
            integration = pcls(cfg)
            registry.register(integration)
        return registry

    container.register_factory(
        ProviderRegistry,
        _create_registry,
        lifetime=ServiceLifetime.SINGLETON,
    )

    container.register_instance(ProviderSettings, ProviderSettings())

    container.register_instance(SourceTrustPolicy, SourceTrustPolicy(
        weights=getattr(settings, "provider_trust_weights", None),
    ))
