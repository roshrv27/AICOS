"""Ordered, failure-isolated delivery of Event Bus subscriptions."""

from __future__ import annotations

import inspect
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from .exceptions import EventSubscriberError
from .subscriber import Subscription

if TYPE_CHECKING:
    from .base import BaseEvent


class SubscriberFailure(BaseModel):
    """Diagnostic information for an isolated subscriber exception."""

    handler_name: str
    exception_type: str
    message: str


class PublishResult(BaseModel):
    """Observable outcome of one validated event publication."""

    event_id: str
    event_name: str
    event_version: int
    subscriber_count: int
    delivered_count: int
    failures: list[SubscriberFailure] = Field(default_factory=list)
    execution_duration_ms: float


class EventDispatcher:
    """Delivers an event to a subscription snapshot without coupling subscribers."""

    def __init__(self, logger: Any) -> None:
        self._logger = logger

    async def dispatch(self, event: BaseEvent, subscriptions: tuple[Subscription, ...]) -> PublishResult:
        started_at = time.perf_counter()
        failures: list[SubscriberFailure] = []
        delivered_count = 0
        for subscription in subscriptions:
            try:
                value = subscription.handler(event)
                if inspect.isawaitable(value):
                    await value
                delivered_count += 1
            except Exception as error:  # Subscriber isolation is a core Event Bus guarantee.
                subscriber_error = EventSubscriberError(str(error))
                failures.append(
                    SubscriberFailure(
                        handler_name=_callable_name(subscription.handler),
                        exception_type=type(error).__name__,
                        message=str(subscriber_error),
                    )
                )
                self._logger.exception("event subscriber failed", extra=_event_log_extra(event))

        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        result = PublishResult(
            event_id=str(event.event_id),
            event_name=event.event_name,
            event_version=event.event_version,
            subscriber_count=len(subscriptions),
            delivered_count=delivered_count,
            failures=failures,
            execution_duration_ms=duration_ms,
        )
        self._logger.info(
            "event published",
            extra={**_event_log_extra(event), "execution_duration_ms": duration_ms},
        )
        return result


def _callable_name(handler: Any) -> str:
    return getattr(handler, "__qualname__", getattr(handler, "__name__", type(handler).__name__))


def _event_log_extra(event: BaseEvent) -> dict[str, str]:
    values = {
        "event_id": str(event.event_id),
        "event_type": event.event_name,
        "source": event.source,
    }
    if event.execution_id is not None:
        values["execution_id"] = event.execution_id
    return values
