"""Ports used by Model Router consumers and provider adapters."""

from __future__ import annotations

from typing import Protocol

from .health import ProviderHealth
from .models import ModelDefinition, ModelRequest
from .response import ModelResponse


class LLMProvider(Protocol):
    """Provider adapter contract implemented without exposing provider SDKs to callers."""

    name: str

    async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse: ...

    async def health_check(self) -> ProviderHealth: ...


class ModelRouterPort(Protocol):
    """Port that future agents and services depend on for model access."""

    async def generate(self, request: ModelRequest) -> ModelResponse: ...
