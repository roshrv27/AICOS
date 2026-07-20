"""Adapter registry for the knowledge acquisition engine.

The registry maintains a mapping of :class:`KnowledgeSourceType` to
:class:`KnowledgeAdapter` instances, preventing duplicates and
providing lookup by source type.
"""

from __future__ import annotations

from ..knowledge_intelligence.enums import KnowledgeSourceType
from .adapters.base import KnowledgeAdapter
from .exceptions import AdapterRegistrationError
from .interfaces import KnowledgeAdapterProtocol


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[KnowledgeSourceType, KnowledgeAdapterProtocol] = {}

    def register(self, adapter: KnowledgeAdapterProtocol) -> None:
        if not isinstance(adapter, KnowledgeAdapterProtocol):
            raise AdapterRegistrationError(
                f"adapter {adapter} does not implement KnowledgeAdapterProtocol"
            )
        source_type = adapter.supported_source()
        if source_type in self._adapters:
            existing = self._adapters[source_type]
            raise AdapterRegistrationError(
                f"adapter for {source_type.value} already registered: "
                f"{existing.name}"
            )
        self._adapters[source_type] = adapter

    def lookup(self, source_type: KnowledgeSourceType) -> KnowledgeAdapterProtocol | None:
        return self._adapters.get(source_type)

    def discover(self, source_type: KnowledgeSourceType) -> KnowledgeAdapterProtocol:
        adapter = self.lookup(source_type)
        if adapter is None:
            raise AdapterRegistrationError(
                f"no adapter registered for source type: {source_type.value}"
            )
        return adapter

    @property
    def registered_types(self) -> list[KnowledgeSourceType]:
        return list(self._adapters.keys())

    @property
    def registered_adapters(self) -> list[KnowledgeAdapterProtocol]:
        return list(self._adapters.values())

    @property
    def count(self) -> int:
        return len(self._adapters)
