"""Registry of enabled model metadata, independent from providers and routing."""

from __future__ import annotations

from threading import RLock

from .capabilities import ModelCapability
from .exceptions import ModelNotFoundError
from .models import ModelDefinition


class ModelRegistry:
    """Stores unique model metadata by provider/name identity."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], ModelDefinition] = {}
        self._lock = RLock()

    def register(self, model: ModelDefinition) -> None:
        with self._lock:
            if model.identity in self._models:
                raise ValueError(f"model already registered: {model.provider}/{model.model_name}")
            self._models[model.identity] = model

    def get(self, provider: str, model_name: str) -> ModelDefinition:
        with self._lock:
            model = self._models.get((provider, model_name))
        if model is None:
            raise ModelNotFoundError(f"model is not registered: {provider}/{model_name}")
        return model

    def find_by_name(self, model_name: str, provider: str | None = None) -> tuple[ModelDefinition, ...]:
        with self._lock:
            return tuple(
                model
                for model in self._models.values()
                if model.model_name == model_name and (provider is None or model.provider == provider)
            )

    def candidates(self, required: frozenset[ModelCapability]) -> tuple[ModelDefinition, ...]:
        with self._lock:
            return tuple(model for model in self._models.values() if model.enabled and model.supports(required))

    def all(self) -> tuple[ModelDefinition, ...]:
        with self._lock:
            return tuple(sorted(self._models.values(), key=lambda model: (model.priority, model.provider, model.model_name)))
