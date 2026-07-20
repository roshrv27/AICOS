# Dependency Injection

`backend.aicos.core.di` is AICOS's lightweight, transport- and framework-free
Dependency Injection framework. It creates infrastructure through stable types
or interfaces, so components receive dependencies through constructors instead
of instantiating them directly.

## Architecture

- `Container` owns registration and recursive resolution.
- `ServiceRegistry` stores providers independently from the resolution flow.
- `ServiceProvider` creates classes, factories, or existing instances according
  to a lifecycle.
- `ServiceLifetime` supports singleton and transient services today; `SCOPED`
  is deliberately reserved for a future scope implementation.
- `interfaces.py` provides future-facing ports for Settings, Event Bus, Event
  History, model routing, databases, scheduling, and agent registration.

The container emits structured lifecycle logs through the existing logging
framework for registration, resolution, replacement, creation failures, and
circular dependencies.

## Registration

```python
from backend.aicos.core.di import Container, ServiceLifetime

container = Container()
container.register(Settings)
container.register(EventBusPort, InProcessEventBus)
container.register_factory(Database, lambda container: Database(container.resolve(Settings)))
container.register_instance(LoggerPort, existing_logger)
```

Without an explicit implementation, `register(MyService)` registers
`MyService` as itself. Register interfaces or protocols against a concrete
implementation to preserve Clean Architecture boundaries.

Decorator registration is also available at composition boundaries:

```python
from backend.aicos.core.di import service

@service(container, lifetime=ServiceLifetime.SINGLETON)
class LocalCache:
    pass
```

## Resolution and lifecycles

```python
class Service:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

container.register(Repository)
container.register(Service)
service = container.resolve(Service)
```

Constructor dependencies must be type annotated and registered. The container
resolves them recursively, detects cycles, and reports missing registrations or
construction failures with DI-specific exceptions. Singleton creation is lazy,
shared, and thread-safe; transient services are newly constructed per request.

## Testing and extension points

Replace an established registration with a fake at test setup:

```python
container.replace(EventBusPort, instance=fake_event_bus)
```

`Container` depends on a `ServiceRegistry`, and future scoped providers can be
added behind `ServiceProvider` without changing consumer constructors. External
infrastructure should be registered through ports such as `EventBusPort`, not
created inside application components.

## Best practices

- Build registrations only in a composition root.
- Depend on the smallest interface practical.
- Keep factories focused on construction, not business workflows.
- Prefer explicit replacements in tests over mocks of global state.
- Do not resolve services from domain code; use constructor injection.
