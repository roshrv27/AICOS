"""Event infrastructure exceptions."""


class EventError(Exception):
    """Base class for AICOS Event Bus failures."""


class EventValidationError(EventError):
    """Raised when an event fails validation before dispatch."""


class EventDispatchError(EventError):
    """Raised when the Event Bus cannot dispatch an otherwise valid event."""


class EventRegistrationError(EventError):
    """Raised when an event type cannot be registered safely."""


class EventSubscriberError(EventError):
    """Describes an isolated subscriber failure."""


class EventBusClosedError(EventDispatchError):
    """Raised when an operation is attempted after shutdown begins."""
