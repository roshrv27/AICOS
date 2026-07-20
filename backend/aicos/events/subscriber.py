"""Subscription contracts for Event Bus implementations."""

from __future__ import annotations

import fnmatch
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .base import BaseEvent


EventHandler = Callable[[BaseEvent], Any]


@dataclass(frozen=True, slots=True)
class Subscription:
    """An isolated subscriber registration with matching policy."""

    identifier: str
    selector: type[BaseEvent] | str
    handler: EventHandler
    priority: int
    order: int
    event_version: int | None = None
    latest_compatible: bool = False

    @classmethod
    def create(
        cls,
        selector: type[BaseEvent] | str,
        handler: EventHandler,
        priority: int,
        order: int,
        event_version: int | None,
        latest_compatible: bool,
    ) -> "Subscription":
        return cls(str(uuid4()), selector, handler, priority, order, event_version, latest_compatible)

    def matches(self, event: BaseEvent, latest_version: int | None = None) -> bool:
        if isinstance(self.selector, str):
            selector_matches = fnmatch.fnmatchcase(event.event_name, self.selector)
        else:
            selector_matches = isinstance(event, self.selector)
        if not selector_matches:
            return False
        if self.latest_compatible:
            return latest_version is not None and event.event_version == latest_version
        return self.event_version is None or event.event_version == self.event_version
