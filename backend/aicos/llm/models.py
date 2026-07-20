"""Typed model metadata and routing request contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .capabilities import ModelCapability


class RoutingStrategy(StrEnum):
    PREFERRED = "preferred"
    LOCAL_FIRST = "local_first"
    PROVIDER_PREFERENCE = "provider_preference"
    CAPABILITY = "capability"
    FALLBACK = "fallback"


class ChatMessage(BaseModel):
    """One provider-neutral conversational message."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1)


class ModelDefinition(BaseModel):
    """Registry metadata for a routable model endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    capabilities: frozenset[ModelCapability] = Field(default_factory=lambda: frozenset({ModelCapability.CHAT}))
    context_window: int = Field(gt=0)
    supports_streaming: bool = False
    supports_reasoning: bool = False
    supports_structured_output: bool = False
    supports_embeddings: bool = False
    priority: int = Field(default=100, ge=0)
    enabled: bool = True
    local: bool = False

    @property
    def identity(self) -> tuple[str, str]:
        return self.provider, self.model_name

    @field_validator("provider", "model_name")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider and model_name must not be blank")
        return value

    def supports(self, required: frozenset[ModelCapability]) -> bool:
        """Return whether this model advertises every requested capability."""

        advertised = set(self.capabilities)
        if self.supports_reasoning:
            advertised.add(ModelCapability.REASONING)
        if self.supports_structured_output:
            advertised.add(ModelCapability.STRUCTURED_OUTPUT)
        if self.supports_embeddings:
            advertised.add(ModelCapability.EMBEDDINGS)
        return required.issubset(advertised)


class ModelRequest(BaseModel):
    """Provider-neutral request supplied exclusively to the Model Router."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    messages: tuple[ChatMessage, ...] = Field(min_length=1)
    required_capabilities: frozenset[ModelCapability] = Field(
        default_factory=lambda: frozenset({ModelCapability.CHAT})
    )
    preferred_model: str | None = None
    preferred_provider: str | None = None
    provider_preferences: tuple[str, ...] = ()
    strategy: RoutingStrategy = RoutingStrategy.CAPABILITY
    allow_fallback: bool = True
    stream: bool = False
    structured_output: bool = False
    timeout_seconds: float = Field(default=120.0, gt=0)
