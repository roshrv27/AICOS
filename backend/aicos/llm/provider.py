"""Provider registry shared by Model Router implementations."""

from __future__ import annotations

from threading import RLock

from .exceptions import ProviderUnavailableError
from .interfaces import LLMProvider


class ProviderRegistry:
    """Thread-safe mapping of provider names to provider-neutral adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._lock = RLock()

    def register(self, provider: LLMProvider) -> None:
        with self._lock:
            if provider.name in self._providers:
                raise ValueError(f"provider already registered: {provider.name}")
            self._providers[provider.name] = provider

    def get(self, name: str) -> LLMProvider:
        with self._lock:
            provider = self._providers.get(name)
        if provider is None:
            raise ProviderUnavailableError(f"provider is not registered: {name}")
        return provider

    def all(self) -> tuple[LLMProvider, ...]:
        with self._lock:
            return tuple(self._providers.values())
