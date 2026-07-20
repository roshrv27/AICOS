"""Composable middleware contracts for Event Bus dispatch."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from .base import BaseEvent
from .dispatcher import PublishResult


NextPublisher = Callable[[BaseEvent], Awaitable[PublishResult]]
EventMiddleware = Callable[[BaseEvent, NextPublisher], Awaitable[PublishResult] | PublishResult]
