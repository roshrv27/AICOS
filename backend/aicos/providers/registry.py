"""Provider registry for the provider infrastructure.

The registry maintains a mapping of provider names to provider instances,
preventing duplicates and providing lookup by name and capability.
"""

from __future__ import annotations

from .exceptions import ProviderRegistrationError
from .interfaces import ProviderProtocol


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderProtocol] = {}

    def register(self, provider: ProviderProtocol) -> None:
        if not isinstance(provider, ProviderProtocol):
            raise ProviderRegistrationError(
                f"provider {provider} does not implement ProviderProtocol"
            )
        name = self._resolve_name(provider)
        if name in self._providers:
            existing = self._providers[name]
            raise ProviderRegistrationError(
                f"provider '{name}' already registered: {type(existing).__name__}"
            )
        self._providers[name] = provider

    def lookup(self, name: str) -> ProviderProtocol | None:
        return self._providers.get(name)

    def discover(self, name: str) -> ProviderProtocol:
        provider = self.lookup(name)
        if provider is None:
            raise ProviderRegistrationError(
                f"no provider registered with name: {name}"
            )
        return provider

    def lookup_by_capability(self, capability: str) -> list[ProviderProtocol]:
        return [
            p for p in self._providers.values()
            if capability in p.capabilities()
        ]

    @property
    def registered_names(self) -> list[str]:
        return list(self._providers.keys())

    @property
    def registered_providers(self) -> list[ProviderProtocol]:
        return list(self._providers.values())

    @property
    def count(self) -> int:
        return len(self._providers)

    @staticmethod
    def _resolve_name(provider: ProviderProtocol) -> str:
        for attr in ("name", "provider_name"):
            val = getattr(provider, attr, None)
            if val is not None:
                return str(val)
        return type(provider).__name__
