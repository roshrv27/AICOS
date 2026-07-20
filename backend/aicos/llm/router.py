"""Health-aware, registry-driven Model Router."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..logging import get_logger
from .capabilities import ModelCapability
from .exceptions import (
    ModelNotFoundError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RoutingError,
    UnsupportedCapabilityError,
)
from .health import HealthMonitor, ProviderHealth
from .models import ModelDefinition, ModelRequest, RoutingStrategy
from .provider import ProviderRegistry
from .registry import ModelRegistry
from .response import ModelResponse

if TYPE_CHECKING:
    from ..core.di import Container
    from ..settings import Settings
    from .interfaces import LLMProvider


class ModelRouter:
    """The sole provider-neutral entry point for all future AICOS model access."""

    def __init__(
        self,
        *,
        model_registry: ModelRegistry | None = None,
        provider_registry: ProviderRegistry | None = None,
        health_monitor: HealthMonitor | None = None,
    ) -> None:
        self.models = model_registry or ModelRegistry()
        self.providers = provider_registry or ProviderRegistry()
        self.health = health_monitor or HealthMonitor()
        self._logger = get_logger("llm")

    def register_provider(self, provider: LLMProvider) -> None:
        """Register an adapter without exposing it to router consumers."""

        self.providers.register(provider)
        self._logger.info("model provider registered", extra={"provider": provider.name})

    def register_model(self, model: ModelDefinition) -> None:
        """Register routable model metadata; provider identity is validated at request time."""

        self.models.register(model)
        self._logger.info(
            "model registered",
            extra={"provider": model.provider, "model_name": model.model_name},
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Select a healthy route and execute with provider fallback when allowed."""

        candidates = self._route_candidates(request)
        failures: list[str] = []
        for model in candidates:
            started_at = time.perf_counter()
            try:
                provider = self.providers.get(model.provider)
                self._logger.info(
                    "model route selected",
                    extra={
                        "provider": model.provider,
                        "model_name": model.model_name,
                        "routing_strategy": request.strategy.value,
                    },
                )
                response = await provider.generate(request, model)
            except (ProviderUnavailableError, ProviderTimeoutError) as error:
                self.health.record_failure(model.provider)
                failures.append(f"{model.provider}/{model.model_name}: {error}")
                self._logger.warning(
                    "model provider request failed; attempting fallback",
                    extra={"provider": model.provider, "model_name": model.model_name},
                )
                if not request.allow_fallback:
                    raise
                continue
            except Exception as error:
                self.health.record_failure(model.provider)
                self._logger.exception(
                    "model provider request failed",
                    extra={"provider": model.provider, "model_name": model.model_name},
                )
                raise RoutingError(f"model request failed for {model.provider}/{model.model_name}") from error
            latency_ms = (time.perf_counter() - started_at) * 1000
            self.health.record_success(model.provider, latency_ms)
            self._logger.info(
                "model request completed",
                extra={
                    "provider": model.provider,
                    "model_name": model.model_name,
                    "execution_duration_ms": latency_ms,
                },
            )
            return response.model_copy(update={"latency_ms": latency_ms})
        raise RoutingError("all eligible model routes failed: " + "; ".join(failures))

    async def check_health(self) -> tuple[ProviderHealth, ...]:
        """Refresh health for all registered providers."""

        results: list[ProviderHealth] = []
        for provider in self.providers.all():
            results.append(await self.health.check(provider))
        return tuple(results)

    @classmethod
    def from_settings(cls, settings: Settings) -> "ModelRouter":
        """Create configured provider adapters without hardcoding any model names."""

        from .providers import OllamaProvider, OpenRouterProvider

        router = cls()
        if settings.ollama.enabled:
            router.register_provider(
                OllamaProvider(str(settings.ollama.base_url), settings.ollama.timeout_seconds)
            )
        if settings.openrouter.enabled and settings.openrouter.api_key is not None:
            router.register_provider(
                OpenRouterProvider(
                    str(settings.openrouter.base_url),
                    settings.openrouter.api_key.get_secret_value(),
                    settings.openrouter.timeout_seconds,
                )
            )
        return router

    def _route_candidates(self, request: ModelRequest) -> tuple[ModelDefinition, ...]:
        required = set(request.required_capabilities)
        if request.structured_output:
            required.add(ModelCapability.STRUCTURED_OUTPUT)
        candidates = list(self.models.candidates(frozenset(required)))
        if request.stream:
            candidates = [model for model in candidates if model.supports_streaming]
        if request.preferred_model is not None:
            preferred_models = [
                model
                for model in candidates
                if model.model_name == request.preferred_model
                and (request.preferred_provider is None or model.provider == request.preferred_provider)
            ]
            if not preferred_models:
                raise ModelNotFoundError("preferred model is not registered or cannot satisfy the request")
            candidates = (
                preferred_models
                + [model for model in candidates if model not in preferred_models]
                if request.allow_fallback
                else preferred_models
            )
        elif request.preferred_provider is not None and not request.allow_fallback:
            candidates = [model for model in candidates if model.provider == request.preferred_provider]

        if not candidates:
            if self.models.all():
                raise UnsupportedCapabilityError("no enabled model supports the requested capabilities")
            raise RoutingError("no models are registered")

        healthy = [model for model in candidates if self.health.get(model.provider).available]
        if healthy:
            candidates = healthy
        elif not request.allow_fallback:
            raise ProviderUnavailableError("no eligible model provider is healthy")

        return tuple(sorted(candidates, key=lambda model: self._route_key(model, request)))

    @staticmethod
    def _route_key(model: ModelDefinition, request: ModelRequest) -> tuple[object, ...]:
        provider_rank = (
            request.provider_preferences.index(model.provider)
            if model.provider in request.provider_preferences
            else len(request.provider_preferences)
        )
        preferred_provider_rank = 0 if model.provider == request.preferred_provider else 1
        preferred_model_rank = 0 if model.model_name == request.preferred_model else 1
        local_rank = 0 if model.local else 1
        if request.strategy is RoutingStrategy.LOCAL_FIRST:
            return local_rank, provider_rank, model.priority, model.provider, model.model_name
        if request.strategy is RoutingStrategy.PROVIDER_PREFERENCE:
            return preferred_provider_rank, provider_rank, local_rank, model.priority, model.provider, model.model_name
        if request.strategy is RoutingStrategy.PREFERRED:
            return preferred_model_rank, preferred_provider_rank, provider_rank, model.priority, model.provider, model.model_name
        return preferred_provider_rank, model.priority, provider_rank, local_rank, model.provider, model.model_name


def register_model_router(container: Container, settings: Settings) -> None:
    """Register ``ModelRouter`` as the singleton DI service at composition time."""

    container.register_factory(ModelRouter, lambda: ModelRouter.from_settings(settings))
