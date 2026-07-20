"""Dependency ports that future AICOS infrastructure can register against."""

from typing import Protocol


class SettingsPort(Protocol):
    """Marker protocol for the validated configuration service."""


class LoggerPort(Protocol):
    """Marker protocol for a structured logging service."""


class EventBusPort(Protocol):
    """Marker protocol for an Event Bus implementation."""


class EventHistoryPort(Protocol):
    """Marker protocol for an Event History implementation."""


class ModelRouterPort(Protocol):
    """Marker protocol for the Model Router implementation."""


class SQLiteDatabasePort(Protocol):
    """Marker protocol for a SQLite database implementation."""


class ChromaDatabasePort(Protocol):
    """Marker protocol for a ChromaDB implementation."""


class SchedulerPort(Protocol):
    """Marker protocol for a scheduler implementation."""


class AgentRegistryPort(Protocol):
    """Marker protocol for an Agent Registry implementation."""
