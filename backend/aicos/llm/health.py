"""Provider health state and measurement utilities."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from threading import RLock
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from .interfaces import LLMProvider


class ProviderHealth(BaseModel):
    """Health state used by the router to avoid unhealthy providers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    available: bool = True
    latency_ms: float | None = Field(default=None, ge=0)
    failures: int = Field(default=0, ge=0)
    last_successful_request: datetime | None = None
    last_checked: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthMonitor:
    """Thread-safe provider health state used as routing input."""

    def __init__(self) -> None:
        self._health: dict[str, ProviderHealth] = {}
        self._lock = RLock()

    def get(self, provider: str) -> ProviderHealth:
        with self._lock:
            return self._health.get(provider, ProviderHealth(provider=provider))

    def record_success(self, provider: str, latency_ms: float) -> ProviderHealth:
        health = ProviderHealth(
            provider=provider,
            available=True,
            latency_ms=latency_ms,
            failures=0,
            last_successful_request=datetime.now(UTC),
        )
        with self._lock:
            self._health[provider] = health
        return health

    def record_failure(self, provider: str) -> ProviderHealth:
        previous = self.get(provider)
        health = ProviderHealth(
            provider=provider,
            available=False,
            latency_ms=previous.latency_ms,
            failures=previous.failures + 1,
            last_successful_request=previous.last_successful_request,
        )
        with self._lock:
            self._health[provider] = health
        return health

    async def check(self, provider: LLMProvider) -> ProviderHealth:
        """Actively probe one provider and persist its returned health state."""

        started_at = time.perf_counter()
        try:
            measured = await provider.health_check()
            health = measured.model_copy(update={"latency_ms": (time.perf_counter() - started_at) * 1000})
        except Exception:
            health = self.record_failure(provider.name)
        else:
            with self._lock:
                self._health[provider.name] = health
        return health
