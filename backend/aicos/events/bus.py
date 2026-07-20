"""In-process Event Bus implementation behind transport-neutral ports."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from threading import RLock
from typing import Any, Protocol, TypeVar

from pydantic import ValidationError

from ..logging import get_correlation_id, get_execution_id, get_logger, logging_context
from .base import BaseEvent
from .dispatcher import EventDispatcher, PublishResult
from .exceptions import EventBusClosedError, EventDispatchError, EventValidationError
from .history import EventHistory, InMemoryEventHistory
from .middleware import EventMiddleware
from .registry import EventRegistry, global_event_registry
from .subscriber import EventHandler, Subscription


EventType = TypeVar("EventType", bound=BaseEvent)


class EventBusProtocol(Protocol):
    """Stable port for in-process and future distributed Event Bus adapters."""

    def subscribe(
        self,
        event_selector: type[EventType] | str,
        handler: EventHandler,
        *,
        priority: int = 0,
        event_version: int | None = None,
        latest_compatible: bool = False,
    ) -> str: ...

    def unsubscribe(self, subscription_id: str) -> bool: ...

    def publish(self, event: BaseEvent) -> PublishResult: ...

    async def publish_async(self, event: BaseEvent) -> PublishResult: ...

    def shutdown(self) -> None: ...

    async def shutdown_async(self) -> None: ...


class InProcessEventBus:
    """Thread-safe Event Bus suitable for local, single-process AICOS operation."""

    def __init__(
        self,
        *,
        registry: EventRegistry | None = None,
        history: EventHistory | None = None,
    ) -> None:
        self._registry = registry or global_event_registry
        self._history = history or InMemoryEventHistory()
        self._logger = get_logger("event_bus")
        self._dispatcher = EventDispatcher(self._logger)
        self._subscriptions: dict[str, Subscription] = {}
        self._middleware: list[EventMiddleware] = []
        self._active_dispatches: set[asyncio.Task[Any]] = set()
        self._lock = RLock()
        self._next_order = 0
        self._closed = False

    @property
    def history(self) -> EventHistory:
        """Expose the configured Event History through its abstraction."""

        return self._history

    def subscribe(
        self,
        event_selector: type[EventType] | str,
        handler: EventHandler,
        *,
        priority: int = 0,
        event_version: int | None = None,
        latest_compatible: bool = False,
    ) -> str:
        """Register a sync or async subscriber for a type or wildcard selector."""

        self._validate_subscription(event_selector, handler, event_version, latest_compatible)
        with self._lock:
            self._assert_open()
            subscription = Subscription.create(
                event_selector,
                handler,
                priority,
                self._next_order,
                event_version,
                latest_compatible,
            )
            self._subscriptions[subscription.identifier] = subscription
            self._next_order += 1
            return subscription.identifier

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscriber without affecting other subscriptions."""

        with self._lock:
            return self._subscriptions.pop(subscription_id, None) is not None

    def add_middleware(self, middleware: EventMiddleware) -> None:
        """Add a middleware interceptor; execution order is registration order."""

        if not callable(middleware):
            raise TypeError("middleware must be callable")
        with self._lock:
            self._assert_open()
            self._middleware.append(middleware)

    def publish(self, event: BaseEvent) -> PublishResult:
        """Publish from synchronous code; use ``publish_async`` inside an event loop."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            running_loop = False
        else:
            running_loop = True
        if running_loop:
            raise RuntimeError("publish() cannot run inside an event loop; use await publish_async()")
        return asyncio.run(self.publish_async(event))

    async def publish_async(self, event: BaseEvent) -> PublishResult:
        """Validate, enrich, dispatch, and record a publication."""

        event = self._validate_and_enrich(event)
        task = asyncio.current_task()
        if task is None:  # pragma: no cover - asyncio supplies a task for coroutines
            raise EventDispatchError("publish_async requires an asyncio task")
        with self._lock:
            self._assert_open()
            self._active_dispatches.add(task)
            middleware = tuple(self._middleware)
        try:
            async def dispatch_from(index: int, current_event: BaseEvent) -> PublishResult:
                if index == len(middleware):
                    return await self._dispatch(current_event)
                try:
                    result = middleware[index](
                        current_event,
                        lambda next_event: dispatch_from(index + 1, next_event),
                    )
                    if isinstance(result, Awaitable):
                        return await result
                    return result
                except EventDispatchError:
                    raise
                except Exception as error:
                    raise EventDispatchError("event middleware failed") from error

            result = await dispatch_from(0, event)
            self._history.record(event, result)
            return result
        finally:
            with self._lock:
                self._active_dispatches.discard(task)

    def shutdown(self) -> None:
        """Synchronously stop intake and release Event Bus resources."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            running_loop = False
        else:
            running_loop = True
        if running_loop:
            raise RuntimeError("shutdown() cannot run inside an event loop; use await shutdown_async()")
        asyncio.run(self.shutdown_async())

    async def shutdown_async(self) -> None:
        """Reject new work, await current dispatches, and clear registrations."""

        current_task = asyncio.current_task()
        with self._lock:
            if self._closed:
                return
            self._closed = True
            active = [task for task in self._active_dispatches if task is not current_task]
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        with self._lock:
            self._subscriptions.clear()
            self._middleware.clear()
        self._logger.info("event bus shut down")

    async def _dispatch(self, event: BaseEvent) -> PublishResult:
        with self._lock:
            subscriptions = tuple(
                sorted(
                    (
                        subscription
                        for subscription in self._subscriptions.values()
                        if subscription.matches(event, self._latest_version(event.event_name))
                    ),
                    key=lambda subscription: (-subscription.priority, subscription.order),
                )
            )
        with logging_context(correlation_id=event.correlation_id, execution_id=event.execution_id):
            return await self._dispatcher.dispatch(event, subscriptions)

    def _validate_and_enrich(self, event: BaseEvent) -> BaseEvent:
        if not isinstance(event, BaseEvent):
            raise EventValidationError("event must inherit BaseEvent")
        try:
            validated_event = type(event).model_validate(event.model_dump(mode="python"))
        except ValidationError as error:
            raise EventValidationError("event validation failed") from error
        if self._registry.get(validated_event.event_name, validated_event.event_version) is None:
            raise EventValidationError(
                f"unregistered event {validated_event.event_name!r} v{validated_event.event_version}"
            )
        updates: dict[str, str] = {}
        if validated_event.correlation_id is None and (correlation_id := get_correlation_id()) is not None:
            updates["correlation_id"] = correlation_id
        if validated_event.execution_id is None and (execution_id := get_execution_id()) is not None:
            updates["execution_id"] = execution_id
        return validated_event.model_copy(update=updates) if updates else validated_event

    def _latest_version(self, event_name: str) -> int | None:
        event_type = self._registry.latest(event_name)
        return event_type.model_fields["event_version"].default if event_type is not None else None

    def _validate_subscription(
        self,
        selector: type[BaseEvent] | str,
        handler: EventHandler,
        event_version: int | None,
        latest_compatible: bool,
    ) -> None:
        if not callable(handler):
            raise TypeError("handler must be callable")
        if isinstance(selector, str):
            if not selector.strip():
                raise ValueError("event selector must not be blank")
        elif not isinstance(selector, type) or not issubclass(selector, BaseEvent):
            raise TypeError("event selector must be a BaseEvent subclass or wildcard string")
        if event_version is not None and event_version < 1:
            raise ValueError("event_version must be positive")
        if latest_compatible and event_version is not None:
            raise ValueError("latest_compatible cannot be combined with event_version")

    def _assert_open(self) -> None:
        if self._closed:
            raise EventBusClosedError("event bus is shut down")
