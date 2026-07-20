"""Typed provider-neutral Model Router response contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UsageMetadata(BaseModel):
    """Normalized provider usage counters when supplied by a provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class StreamChunk(BaseModel):
    """Future-ready normalized streamed content chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    finished: bool = False


class ModelResponse(BaseModel):
    """Normalized completion response returned by every provider adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model_name: str
    content: str
    structured_output: dict[str, Any] | None = None
    usage: UsageMetadata = Field(default_factory=UsageMetadata)
    latency_ms: float = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
