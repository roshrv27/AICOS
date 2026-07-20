from __future__ import annotations

from .enums import Capability, Category, SourceType
from .exceptions import DuplicateSourceError, SourceNotFoundError
from .models import TrustedKnowledgeSource
from .validation import validate_source


class TrustedKnowledgeRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, TrustedKnowledgeSource] = {}

    def register_source(self, source: TrustedKnowledgeSource) -> None:
        validate_source(source)
        if source.id in self._sources:
            raise DuplicateSourceError(
                f"source already registered: {source.id}"
            )
        self._sources[source.id] = source

    def remove_source(self, source_id: str) -> None:
        if source_id not in self._sources:
            raise SourceNotFoundError(f"source not found: {source_id}")
        del self._sources[source_id]

    def lookup(self, source_id: str) -> TrustedKnowledgeSource:
        source = self._sources.get(source_id)
        if source is None:
            raise SourceNotFoundError(f"source not found: {source_id}")
        return source

    def lookup_by_type(self, source_type: SourceType) -> list[TrustedKnowledgeSource]:
        return [
            s for s in self._sources.values()
            if s.source_type == source_type
        ]

    def lookup_by_category(self, category: Category) -> list[TrustedKnowledgeSource]:
        return [
            s for s in self._sources.values()
            if s.category == category
        ]

    def lookup_by_capability(
        self, capability: Capability,
    ) -> list[TrustedKnowledgeSource]:
        return [
            s for s in self._sources.values()
            if capability in s.capabilities
        ]

    def lookup_by_tag(self, tag: str) -> list[TrustedKnowledgeSource]:
        return [
            s for s in self._sources.values()
            if tag in s.tags
        ]

    def lookup_enabled(self) -> list[TrustedKnowledgeSource]:
        return [
            s for s in self._sources.values()
            if s.enabled
        ]

    def discover(self, source_id: str) -> TrustedKnowledgeSource:
        return self.lookup(source_id)

    def statistics(self) -> dict[str, int]:
        types: dict[str, int] = {}
        for s in self._sources.values():
            key = str(s.source_type)
            types[key] = types.get(key, 0) + 1
        return {
            "total": len(self._sources),
            "enabled": len(self.lookup_enabled()),
            "by_type": types,
        }
