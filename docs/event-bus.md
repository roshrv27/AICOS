# Event Bus

`backend.aicos.events` provides versioned event contracts and the
production-oriented in-process implementation. Components should type their
dependency as `EventBusProtocol`; this keeps publish/subscribe code unchanged
if the implementation is later replaced by Redis, Kafka, RabbitMQ, or NATS.

## Define and publish a typed event

```python
from typing import Literal
from backend.aicos.events import BaseEvent, InProcessEventBus

class WorkRequested(BaseEvent):
    event_name: Literal["work.requested"] = "work.requested"
    work_id: str

bus = InProcessEventBus()
bus.publish(WorkRequested(work_id="work-123"))
```

Every event carries immutable metadata: an event ID, name, positive version,
UTC timestamp, source, optional execution ID, optional correlation ID, and an
extensible metadata mapping. If correlation or execution IDs are bound through
`logging_context`, publishing automatically copies them into the event.

Event classes register automatically using their `(event_name, event_version)`
identity. Subscribers may select a precise version or the latest registered
version without a hardcoded event mapping.

The package contains reusable base infrastructure (`base`, `bus`, `dispatcher`,
`registry`, `subscriber`, `publisher`, `middleware`, `history`, and
`exceptions`) plus typed contracts grouped by domain. Importing
`backend.aicos.events` registers all built-in contracts; plugins register
automatically when their `BaseEvent` subclasses are imported.

## Subscribe

```python
bus.subscribe(WorkRequested, handle_work, priority=100)
bus.subscribe("work.*", audit_work)
bus.subscribe("work.requested", handle_current_work, latest_compatible=True)
```

Higher priorities run first; equal priorities preserve subscription order.
Handlers may be synchronous or `async def`. Use `publish()` outside an asyncio
event loop and `await publish_async()` inside one. A failing subscriber is
recorded and logged but never prevents later subscribers from running.

## Middleware and shutdown

Middleware receives an event and a `next_publisher` callable, allowing it to
observe, enrich, or short-circuit dispatch without coupling components.

```python
async def middleware(event, next_publisher):
    return await next_publisher(event)

bus.add_middleware(middleware)
await bus.shutdown_async()
```

Shutdown rejects new publications, waits for active async dispatches, clears
subscriptions and middleware, and writes a structured lifecycle log entry.

## History and validation

Every event is revalidated with Pydantic immediately before dispatch. Invalid
or unregistered events are rejected and are never delivered. The default
`InMemoryEventHistory` records each successfully dispatched event and its
`PublishResult` through the `EventHistory` port. A persistent history adapter
can be added later without changing publishers or subscribers.
