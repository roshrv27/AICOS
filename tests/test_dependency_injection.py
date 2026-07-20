"""Unit tests for the AICOS Dependency Injection framework."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import unittest

from backend.aicos.core.di import (
    CircularDependencyError,
    Container,
    ServiceLifetime,
    ServiceNotRegisteredError,
    ServiceRegistrationError,
    ServiceResolutionError,
    service,
)
from backend.aicos.logging import shutdown_logging


class Clock:
    pass


class Repository:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock


class Service:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository


class StoragePort:
    pass


class MemoryStorage(StoragePort):
    pass


class CircularA:
    def __init__(self, dependency: CircularB) -> None:
        self.dependency = dependency


class CircularB:
    def __init__(self, dependency: CircularA) -> None:
        self.dependency = dependency


class UnannotatedDependency:
    def __init__(self, dependency) -> None:
        self.dependency = dependency


class DependencyInjectionTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_singleton_is_lazy_and_shared(self) -> None:
        container = Container()
        calls = 0

        def create() -> Clock:
            nonlocal calls
            calls += 1
            return Clock()

        container.register_factory(Clock, create)
        self.assertEqual(calls, 0)

        first = container.resolve(Clock)
        second = container.resolve(Clock)

        self.assertIs(first, second)
        self.assertEqual(calls, 1)

    def test_transient_creates_new_instance_for_each_resolution(self) -> None:
        container = Container()
        container.register(Clock, lifetime=ServiceLifetime.TRANSIENT)

        self.assertIsNot(container.resolve(Clock), container.resolve(Clock))

    def test_constructor_injection_recursively_resolves_dependencies(self) -> None:
        container = Container()
        container.register(Clock)
        container.register(Repository)
        container.register(Service)

        resolved = container.resolve(Service)

        self.assertIsInstance(resolved.repository, Repository)
        self.assertIsInstance(resolved.repository.clock, Clock)

    def test_factory_registration_supports_container_parameter(self) -> None:
        container = Container()
        container.register(Clock)
        container.register_factory(Repository, lambda resolved_container: Repository(resolved_container.resolve(Clock)))

        self.assertIsInstance(container.resolve(Repository).clock, Clock)

    def test_interface_can_be_mapped_to_implementation(self) -> None:
        container = Container()
        container.register(StoragePort, MemoryStorage)

        self.assertIsInstance(container.resolve(StoragePort), MemoryStorage)

    def test_existing_instance_and_replacement_support_testing(self) -> None:
        container = Container()
        production = MemoryStorage()
        replacement = MemoryStorage()
        container.register_instance(StoragePort, production)

        container.replace(StoragePort, instance=replacement)

        self.assertIs(container.resolve(StoragePort), replacement)

    def test_decorator_based_registration(self) -> None:
        container = Container()

        @service(container, lifetime=ServiceLifetime.TRANSIENT)
        class DecoratedService:
            pass

        self.assertIsNot(container.resolve(DecoratedService), container.resolve(DecoratedService))

    def test_circular_dependencies_raise_meaningful_error(self) -> None:
        container = Container()
        container.register(CircularA)
        container.register(CircularB)

        with self.assertRaises(CircularDependencyError) as context:
            container.resolve(CircularA)

        self.assertIn("CircularA -> CircularB -> CircularA", str(context.exception))

    def test_singleton_initialization_is_thread_safe(self) -> None:
        container = Container()
        calls = 0
        counter_lock = Lock()

        def create() -> Clock:
            nonlocal calls
            with counter_lock:
                calls += 1
            return Clock()

        container.register_factory(Clock, create)
        with ThreadPoolExecutor(max_workers=8) as executor:
            instances = list(executor.map(lambda _: container.resolve(Clock), range(32)))

        self.assertEqual(calls, 1)
        self.assertTrue(all(instance is instances[0] for instance in instances))

    def test_registration_and_resolution_failures_are_explicit(self) -> None:
        container = Container()
        container.register(Clock)

        with self.assertRaises(ServiceRegistrationError):
            container.register(Clock)
        with self.assertRaises(ServiceNotRegisteredError):
            container.resolve(Repository)

        container.register(UnannotatedDependency)
        with self.assertRaises(ServiceResolutionError):
            container.resolve(UnannotatedDependency)


if __name__ == "__main__":
    unittest.main()
