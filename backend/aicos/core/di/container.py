"""Thread-safe, constructor-injecting Dependency Injection container."""

from __future__ import annotations

import inspect
from contextvars import ContextVar
from threading import RLock
from types import UnionType
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

from ...logging import get_logger
from .exceptions import (
    CircularDependencyError,
    ServiceNotRegisteredError,
    ServiceRegistrationError,
    ServiceResolutionError,
)
from .lifecycle import ServiceLifetime
from .provider import Factory, ServiceProvider
from .registry import ServiceRegistry


ServiceType = TypeVar("ServiceType")
_resolution_path: ContextVar[tuple[type[Any], ...]] = ContextVar("aicos_di_resolution_path", default=())


class Container:
    """Registers and resolves application infrastructure through stable types.

    The container is intentionally small: it owns registration, recursive
    constructor injection, lifecycle management, and diagnostics. Application
    code should depend on interfaces and receive them through constructors.
    """

    def __init__(self, registry: ServiceRegistry | None = None) -> None:
        self._registry = registry or ServiceRegistry()
        self._resolution_lock = RLock()
        self._logger = get_logger("system")

    def register(
        self,
        service_type: type[ServiceType],
        implementation: type[ServiceType] | None = None,
        *,
        factory: Factory | None = None,
        instance: ServiceType | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Register a class, interface mapping, factory, or existing instance."""

        provider = self._make_provider(service_type, implementation, factory, instance, lifetime)
        self._registry.add(service_type, provider)
        self._logger.info(
            "service registered",
            extra={"service_type": _service_name(service_type), "lifecycle": lifetime.value},
        )

    def register_factory(
        self,
        service_type: type[ServiceType],
        factory: Factory,
        *,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Register a zero-argument or container-accepting factory."""

        self.register(service_type, factory=factory, lifetime=lifetime)

    def register_instance(self, service_type: type[ServiceType], instance: ServiceType) -> None:
        """Register an already-created singleton instance."""

        self.register(service_type, instance=instance, lifetime=ServiceLifetime.SINGLETON)

    def replace(
        self,
        service_type: type[ServiceType],
        implementation: type[ServiceType] | None = None,
        *,
        factory: Factory | None = None,
        instance: ServiceType | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """Replace an existing registration, typically with a test double."""

        provider = self._make_provider(service_type, implementation, factory, instance, lifetime)
        self._registry.replace(service_type, provider)
        self._logger.info(
            "service replaced",
            extra={"service_type": _service_name(service_type), "lifecycle": lifetime.value},
        )

    def resolve(self, service_type: type[ServiceType]) -> ServiceType:
        """Resolve a registered service and recursively inject its dependencies."""

        with self._resolution_lock:
            path = _resolution_path.get()
            if service_type in path:
                cycle = " -> ".join(_service_name(item) for item in (*path, service_type))
                error = CircularDependencyError(f"circular dependency detected: {cycle}")
                self._logger.error("service resolution failed: circular dependency", extra={"service_type": cycle})
                raise error
            token = _resolution_path.set((*path, service_type))
            try:
                provider = self._registry.get(service_type)
                result = provider.get(self)
                self._logger.debug("service resolved", extra={"service_type": _service_name(service_type)})
                return result
            except (ServiceNotRegisteredError, CircularDependencyError, ServiceResolutionError):
                self._logger.exception("service resolution failed", extra={"service_type": _service_name(service_type)})
                raise
            except Exception as error:
                self._logger.exception("service resolution failed", extra={"service_type": _service_name(service_type)})
                raise ServiceResolutionError(f"could not resolve service {_service_name(service_type)}") from error
            finally:
                _resolution_path.reset(token)

    def _construct(self, implementation: type[ServiceType]) -> ServiceType:
        """Instantiate one implementation by resolving its annotated constructor arguments."""

        try:
            signature = inspect.signature(implementation.__init__)
            type_hints = get_type_hints(implementation.__init__)
        except (TypeError, ValueError, NameError) as error:
            raise ServiceResolutionError(
                f"constructor for {_service_name(implementation)} cannot be inspected"
            ) from error

        arguments: dict[str, Any] = {}
        for parameter in signature.parameters.values():
            if parameter.name == "self" or parameter.kind in (
                parameter.VAR_POSITIONAL,
                parameter.VAR_KEYWORD,
            ):
                continue
            dependency_type = type_hints.get(parameter.name)
            if dependency_type is None:
                if parameter.default is not parameter.empty:
                    continue
                raise ServiceResolutionError(
                    f"dependency {parameter.name!r} on {_service_name(implementation)} needs a type annotation"
                )
            dependency_type = _required_type(dependency_type)
            try:
                arguments[parameter.name] = self.resolve(dependency_type)
            except ServiceNotRegisteredError:
                if parameter.default is not parameter.empty:
                    continue
                raise
        try:
            return implementation(**arguments)
        except Exception as error:
            raise ServiceResolutionError(f"could not construct {_service_name(implementation)}") from error

    @staticmethod
    def _make_provider(
        service_type: type[ServiceType],
        implementation: type[ServiceType] | None,
        factory: Factory | None,
        instance: ServiceType | None,
        lifetime: ServiceLifetime,
    ) -> ServiceProvider:
        if not isinstance(service_type, type):
            raise ServiceRegistrationError("service_type must be a type or interface")
        if lifetime is ServiceLifetime.SCOPED:
            raise ServiceRegistrationError("scoped lifetime is reserved for a future scope implementation")
        if implementation is None and factory is None and instance is None:
            implementation = service_type
        try:
            return ServiceProvider(
                implementation=implementation,
                factory=factory,
                instance=instance,
                lifetime=lifetime,
            )
        except ValueError as error:
            raise ServiceRegistrationError(str(error)) from error


def _required_type(annotation: Any) -> type[Any]:
    """Return a resolvable type, rejecting ambiguous union dependencies."""

    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        candidates = [candidate for candidate in get_args(annotation) if candidate is not type(None)]
        if len(candidates) == 1 and isinstance(candidates[0], type):
            return candidates[0]
        raise ServiceResolutionError("union-typed dependencies must resolve to one concrete service type")
    if not isinstance(annotation, type):
        raise ServiceResolutionError(f"unsupported dependency annotation: {annotation!r}")
    return annotation


def _service_name(service_type: type[Any]) -> str:
    return getattr(service_type, "__name__", repr(service_type))
