"""Event history abstractions; persistence is intentionally deferred."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field

from .base import BaseEvent
from .dispatcher import PublishResult


class EventHistoryEntry(BaseModel):
    """A recorded publication outcome."""

    event: BaseEvent
    result: PublishResult
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventHistory(Protocol):
    """Port for recording published events in any durable or transient store."""

    def record(self, event: BaseEvent, result: PublishResult) -> None: ...

    def entries(self) -> tuple[EventHistoryEntry, ...]: ...


class InMemoryEventHistory:
    """Thread-safe, non-persistent Event History for local development and tests."""

    def __init__(self) -> None:
        self._entries: list[EventHistoryEntry] = []
        self._lock = RLock()

    def record(self, event: BaseEvent, result: PublishResult) -> None:
        with self._lock:
            self._entries.append(EventHistoryEntry(event=event, result=result))

    def entries(self) -> tuple[EventHistoryEntry, ...]:
        with self._lock:
            return tuple(self._entries)
