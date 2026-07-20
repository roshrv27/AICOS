from __future__ import annotations

from .enums import Capability, Category, SourceType
from .exceptions import SourceNotFoundError
from .models import TrustedKnowledgeSource
from .registry import TrustedKnowledgeRegistry
from .seed_data import get_seed_sources
from .validation import validate_trust_score


class TrustedKnowledgeService:
    def __init__(self, registry: TrustedKnowledgeRegistry) -> None:
        self._registry = registry

    def load_seed_data(self) -> int:
        count = 0
        for source in get_seed_sources():
            try:
                self._registry.register_source(source)
                count += 1
            except Exception:
                pass
        return count

    def register(self, source: TrustedKnowledgeSource) -> None:
        self._registry.register_source(source)

    def remove(self, source_id: str) -> None:
        self._registry.remove_source(source_id)

    def lookup(self, source_id: str) -> TrustedKnowledgeSource:
        return self._registry.lookup(source_id)

    def enable(self, source_id: str) -> None:
        source = self._registry.lookup(source_id)
        if source.enabled:
            return
        updated = TrustedKnowledgeSource(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            category=source.category,
            url=source.url,
            display_name=source.display_name,
            organization=source.organization,
            rss_feed=source.rss_feed,
            api_endpoint=source.api_endpoint,
            trust_score=source.trust_score,
            priority=source.priority,
            enabled=True,
            authentication_type=source.authentication_type,
            refresh_frequency=source.refresh_frequency,
            capabilities=source.capabilities,
            tags=source.tags,
            metadata=source.metadata,
        )
        self._registry.remove_source(source_id)
        self._registry.register_source(updated)

    def disable(self, source_id: str) -> None:
        source = self._registry.lookup(source_id)
        if not source.enabled:
            return
        updated = TrustedKnowledgeSource(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            category=source.category,
            url=source.url,
            display_name=source.display_name,
            organization=source.organization,
            rss_feed=source.rss_feed,
            api_endpoint=source.api_endpoint,
            trust_score=source.trust_score,
            priority=source.priority,
            enabled=False,
            authentication_type=source.authentication_type,
            refresh_frequency=source.refresh_frequency,
            capabilities=source.capabilities,
            tags=source.tags,
            metadata=source.metadata,
        )
        self._registry.remove_source(source_id)
        self._registry.register_source(updated)

    def update_trust_score(self, source_id: str, new_score: float) -> TrustedKnowledgeSource:
        validate_trust_score(new_score)
        source = self._registry.lookup(source_id)
        updated = TrustedKnowledgeSource(
            id=source.id,
            name=source.name,
            source_type=source.source_type,
            category=source.category,
            url=source.url,
            display_name=source.display_name,
            organization=source.organization,
            rss_feed=source.rss_feed,
            api_endpoint=source.api_endpoint,
            trust_score=new_score,
            priority=source.priority,
            enabled=source.enabled,
            authentication_type=source.authentication_type,
            refresh_frequency=source.refresh_frequency,
            capabilities=source.capabilities,
            tags=source.tags,
            metadata=source.metadata,
        )
        self._registry.remove_source(source_id)
        self._registry.register_source(updated)
        return updated

    def find_sources(
        self,
        source_type: SourceType | None = None,
        category: Category | None = None,
        capability: Capability | None = None,
        tag: str | None = None,
        enabled_only: bool = True,
    ) -> list[TrustedKnowledgeSource]:
        results: list[TrustedKnowledgeSource] = list(self._registry._sources.values())
        if enabled_only:
            results = [s for s in results if s.enabled]
        if source_type is not None:
            results = [s for s in results if s.source_type == source_type]
        if category is not None:
            results = [s for s in results if s.category == category]
        if capability is not None:
            results = [s for s in results if capability in s.capabilities]
        if tag is not None:
            results = [s for s in results if tag in s.tags]
        return results

    def find_by_capability(self, capability: Capability) -> list[TrustedKnowledgeSource]:
        return self._registry.lookup_by_capability(capability)

    def find_by_category(self, category: Category) -> list[TrustedKnowledgeSource]:
        return self._registry.lookup_by_category(category)

    def find_by_tags(self, tags: list[str]) -> list[TrustedKnowledgeSource]:
        return [
            s for s in self._registry._sources.values()
            if all(t in s.tags for t in tags)
        ]

    def statistics(self) -> dict[str, int]:
        return self._registry.statistics()
