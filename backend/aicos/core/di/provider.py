"""Provider definitions responsible for constructing registered services."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import RLock
from typing import TYPE_CHECKING, Any

from .exceptions import ServiceResolutionError
from .lifecycle import ServiceLifetime

if TYPE_CHECKING:
    from .container import Container


Factory = Callable[["Container"], Any] | Callable[[], Any]


@dataclass(slots=True)
class ServiceProvider:
    """A registration strategy and lifecycle policy for one service key."""

    implementation: type[Any] | None = None
    factory: Factory | None = None
    instance: Any | None = None
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    _initialized: bool = field(default=False, init=False, repr=False)
    _singleton: Any | None = field(default=None, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        choices = sum(value is not None for value in (self.implementation, self.factory, self.instance))
        if choices != 1:
            raise ValueError("a provider requires exactly one of implementation, factory, or instance")
        if self.instance is not None:
            self._singleton = self.instance
            self._initialized = True

    def get(self, container: Container) -> Any:
        """Return an instance according to the provider lifecycle."""

        if self.lifetime is ServiceLifetime.TRANSIENT:
            return self._create(container)
        with self._lock:
            if not self._initialized:
                self._singleton = self._create(container)
                self._initialized = True
            return self._singleton

    def _create(self, container: Container) -> Any:
        if self.implementation is not None:
            return container._construct(self.implementation)
        if self.factory is not None:
            return _invoke_factory(self.factory, container)
        return self.instance


def _invoke_factory(factory: Factory, container: Container) -> Any:
    """Support either a zero-argument factory or one accepting the container."""

    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError) as error:
        raise ServiceResolutionError("factory signature cannot be inspected") from error
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        and parameter.default is parameter.empty
    ]
    if len(positional) == 0:
        return factory()  # type: ignore[call-arg]
    if len(positional) == 1:
        return factory(container)  # type: ignore[call-arg]
    raise ServiceResolutionError("factory must accept zero arguments or one Container argument")
