"""Compatibility exports for the Event Bus package.

New code should import from :mod:`backend.aicos.events`.
"""

from .events import BaseEvent as Event
from .events import EventBusProtocol, InMemoryEventHistory, InProcessEventBus
from .events import EventBusClosedError, EventDispatchError, EventRegistrationError, EventSubscriberError
from .events import EventValidationError, PublishResult

__all__ = [
    "Event",
    "EventBusClosedError",
    "EventBusProtocol",
    "EventDispatchError",
    "EventRegistrationError",
    "EventSubscriberError",
    "EventValidationError",
    "InMemoryEventHistory",
    "InProcessEventBus",
    "PublishResult",
]
