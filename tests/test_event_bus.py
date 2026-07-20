"""Unit tests for the versioned AICOS in-process Event Bus."""

from __future__ import annotations

import asyncio
import unittest
from typing import Literal

from backend.aicos.events import (
    BaseEvent,
    EventBusClosedError,
    EventValidationError,
    InMemoryEventHistory,
    InProcessEventBus,
    global_event_registry,
)
from backend.aicos.logging import logging_context, shutdown_logging


class TaskCreated(BaseEvent):
    event_name: Literal["test.task_created"] = "test.task_created"
    task_id: str


class VersionedEventV1(BaseEvent):
    event_name: Literal["test.versioned"] = "test.versioned"
    event_version: Literal[1] = 1
    value: str


class VersionedEventV2(BaseEvent):
    event_name: Literal["test.versioned"] = "test.versioned"
    event_version: Literal[2] = 2
    value: str


class EventBusTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_typed_subscribers_run_by_priority(self) -> None:
        bus = InProcessEventBus()
        calls: list[str] = []
        bus.subscribe(TaskCreated, lambda event: calls.append(f"low:{event.task_id}"), priority=1)
        bus.subscribe(TaskCreated, lambda event: calls.append(f"high:{event.task_id}"), priority=10)

        result = bus.publish(TaskCreated(task_id="t-1"))

        self.assertEqual(calls, ["high:t-1", "low:t-1"])
        self.assertEqual(result.subscriber_count, 2)
        self.assertEqual(result.delivered_count, 2)
        self.assertFalse(result.failures)
        bus.shutdown()

    def test_wildcard_subscription_and_unsubscribe(self) -> None:
        bus = InProcessEventBus()
        calls: list[str] = []
        subscription_id = bus.subscribe("test.*", lambda event: calls.append(event.event_name))

        bus.publish(TaskCreated(task_id="t-1"))
        self.assertTrue(bus.unsubscribe(subscription_id))
        bus.publish(TaskCreated(task_id="t-2"))

        self.assertEqual(calls, ["test.task_created"])
        bus.shutdown()

    def test_specific_and_latest_compatible_versions_can_coexist(self) -> None:
        bus = InProcessEventBus()
        received: list[str] = []
        bus.subscribe("test.versioned", lambda event: received.append(f"v1:{event.event_version}"), event_version=1)
        bus.subscribe("test.versioned", lambda event: received.append(f"latest:{event.event_version}"), latest_compatible=True)

        bus.publish(VersionedEventV1(value="one"))
        bus.publish(VersionedEventV2(value="two"))

        self.assertEqual(received, ["v1:1", "latest:2"])
        self.assertIs(global_event_registry.get("test.versioned", 1), VersionedEventV1)
        self.assertIs(global_event_registry.latest("test.versioned"), VersionedEventV2)
        bus.shutdown()

    def test_failing_subscriber_does_not_stop_other_subscribers(self) -> None:
        bus = InProcessEventBus()
        calls: list[str] = []

        def fail(_: BaseEvent) -> None:
            raise ValueError("subscriber failure")

        bus.subscribe(TaskCreated, fail, priority=10)
        bus.subscribe(TaskCreated, lambda _: calls.append("completed"))
        result = bus.publish(TaskCreated(task_id="t-1"))

        self.assertEqual(calls, ["completed"])
        self.assertEqual(result.delivered_count, 1)
        self.assertEqual(result.failures[0].exception_type, "ValueError")
        bus.shutdown()

    def test_correlation_and_execution_ids_are_propagated(self) -> None:
        bus = InProcessEventBus()
        observed: list[tuple[str | None, str | None]] = []
        bus.subscribe(TaskCreated, lambda event: observed.append((event.correlation_id, event.execution_id)))

        with logging_context(correlation_id="request-42", execution_id="execution-7"):
            bus.publish(TaskCreated(task_id="t-1"))

        self.assertEqual(observed, [("request-42", "execution-7")])
        bus.shutdown()

    def test_middleware_can_intercept_and_continue_dispatch(self) -> None:
        bus = InProcessEventBus()
        calls: list[str] = []

        async def middleware(event: BaseEvent, next_publisher):
            calls.append("before")
            result = await next_publisher(event)
            calls.append("after")
            return result

        bus.add_middleware(middleware)
        bus.subscribe(TaskCreated, lambda _: calls.append("handler"))
        bus.publish(TaskCreated(task_id="t-1"))

        self.assertEqual(calls, ["before", "handler", "after"])
        bus.shutdown()

    def test_history_records_every_successfully_published_event(self) -> None:
        history = InMemoryEventHistory()
        bus = InProcessEventBus(history=history)
        event = TaskCreated(task_id="t-1")

        bus.publish(event)

        entry = history.entries()[0]
        self.assertEqual(entry.event, event)
        self.assertEqual(entry.result.event_id, str(event.event_id))
        bus.shutdown()

    def test_invalid_event_is_not_dispatched(self) -> None:
        bus = InProcessEventBus()
        invalid_event = TaskCreated.model_construct(event_name="", task_id="t-1")

        with self.assertRaises(EventValidationError):
            bus.publish(invalid_event)
        self.assertFalse(bus.history.entries())
        bus.shutdown()

    def test_shutdown_rejects_new_operations(self) -> None:
        bus = InProcessEventBus()
        bus.shutdown()

        with self.assertRaises(EventBusClosedError):
            bus.subscribe(TaskCreated, lambda _: None)
        with self.assertRaises(EventBusClosedError):
            bus.publish(TaskCreated(task_id="t-1"))


class AsyncEventBusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        shutdown_logging()

    async def test_async_handler_and_graceful_shutdown(self) -> None:
        bus = InProcessEventBus()
        calls: list[str] = []

        async def handler(event: BaseEvent) -> None:
            await asyncio.sleep(0)
            calls.append(event.task_id)

        bus.subscribe(TaskCreated, handler)
        result = await bus.publish_async(TaskCreated(task_id="async-1"))
        await bus.shutdown_async()

        self.assertEqual(calls, ["async-1"])
        self.assertEqual(result.delivered_count, 1)
