"""Transport-neutral publisher port."""

from __future__ import annotations

from typing import Protocol

from .base import BaseEvent
from .dispatcher import PublishResult


class EventPublisher(Protocol):
    """Port used by components that only need to publish events."""

    def publish(self, event: BaseEvent) -> PublishResult: ...

    async def publish_async(self, event: BaseEvent) -> PublishResult: ...
