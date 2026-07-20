"""Version-aware event type registry with plugin-friendly registration."""

from __future__ import annotations

from threading import RLock
from typing import TYPE_CHECKING

from pydantic_core import PydanticUndefined

from .exceptions import EventRegistrationError

if TYPE_CHECKING:
    from .base import BaseEvent


class EventRegistry:
    """Registers event classes by their stable ``(name, version)`` identity."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, int], type[BaseEvent]] = {}
        self._lock = RLock()

    def register(self, event_type: type[BaseEvent]) -> None:
        """Register an event type; re-registering the same class is harmless."""

        name, version = self.identity_for(event_type)
        key = (name, version)
        with self._lock:
            existing = self._events.get(key)
            if existing is not None and existing is not event_type:
                raise EventRegistrationError(
                    f"event {name!r} version {version} is already registered by {existing.__name__}"
                )
            self._events[key] = event_type

    def get(self, event_name: str, event_version: int) -> type[BaseEvent] | None:
        """Return the concrete event class for an exact name/version pair."""

        with self._lock:
            return self._events.get((event_name, event_version))

    def latest(self, event_name: str) -> type[BaseEvent] | None:
        """Return the highest registered version for an event name."""

        with self._lock:
            candidates = [
                (version, event_type)
                for (name, version), event_type in self._events.items()
                if name == event_name
            ]
        return max(candidates, default=(None, None), key=lambda candidate: candidate[0])[1]

    def all(self) -> tuple[type[BaseEvent], ...]:
        """Return every registered event class in deterministic identity order."""

        with self._lock:
            return tuple(event for _, event in sorted(self._events.items()))

    @staticmethod
    def identity_for(event_type: type[BaseEvent]) -> tuple[str, int]:
        """Read and validate an event class's stable identity defaults."""

        try:
            name = event_type.model_fields["event_name"].default
            version = event_type.model_fields["event_version"].default
        except KeyError as error:  # pragma: no cover - protects third-party plugins
            raise EventRegistrationError("event types must inherit BaseEvent") from error
        if name is PydanticUndefined or not isinstance(name, str) or not name.strip():
            raise EventRegistrationError("event_name must have a non-empty string default")
        if version is PydanticUndefined or not isinstance(version, int) or version < 1:
            raise EventRegistrationError("event_version must have a positive integer default")
        return name, version


global_event_registry = EventRegistry()
