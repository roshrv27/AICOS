"""Immutable, versioned base event contract."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseEvent(BaseModel):
    """The stable event envelope used by all AICOS transports.

    Concrete events override the default ``event_name`` with a literal string
    and may introduce only their own typed payload fields. The frozen Pydantic
    model prevents event envelopes from changing after publication.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_name: str = "aicos.event"
    event_version: int = Field(default=1, ge=1)
    correlation_id: str | None = None
    execution_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_name", "source")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("event_name and source must not be blank")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Automatically register concrete event types after Pydantic builds them."""

        super().__pydantic_init_subclass__(**kwargs)
        if cls is not BaseEvent:
            from .registry import global_event_registry

            global_event_registry.register(cls)
