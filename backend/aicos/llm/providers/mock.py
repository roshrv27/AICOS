"""Deterministic in-memory provider for unit tests and local integration tests."""

from __future__ import annotations

from datetime import UTC, datetime

from ..exceptions import ProviderUnavailableError
from ..health import ProviderHealth
from ..models import ModelDefinition, ModelRequest
from ..response import ModelResponse


class MockProvider:
    """Configurable provider adapter that never performs network calls."""

    name = "mock"

    def __init__(self, *, response_content: str = "mock response", available: bool = True) -> None:
        self.response_content = response_content
        self.available = available
        self.requests: list[tuple[ModelRequest, ModelDefinition]] = []

    async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse:
        if not self.available:
            raise ProviderUnavailableError("mock provider is unavailable")
        self.requests.append((request, model))
        return ModelResponse(provider=self.name, model_name=model.model_name, content=self.response_content, latency_ms=0)

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            available=self.available,
            latency_ms=0,
            last_successful_request=datetime.now(UTC) if self.available else None,
            failures=0 if self.available else 1,
        )
