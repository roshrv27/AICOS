"""Provider-neutral persistence infrastructure for AICOS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.di import ServiceLifetime
from .connection import SQLiteConnectionFactory
from .database import DatabaseManager
from .exceptions import (
    DatabaseConnectionError,
    MigrationError,
    NestedTransactionError,
    PersistenceError,
    TransactionError,
)
from .interfaces import (
    DatabasePort,
    HistoryRepositoryPort,
    ProgressRepositoryPort,
    SettingsRepositoryPort,
    TopicRepositoryPort,
    TransactionManagerPort,
    UnitOfWorkPort,
)
from .migrations import Migration, MigrationManager
from .models import (
    DatabaseInfo,
    HistoryEntryData,
    MigrationHistoryEntry,
    ProgressData,
    SettingData,
    TopicData,
)
from .repositories import REPOSITORY_MIGRATIONS, register_repositories
from .transaction import TransactionManager
from .unit_of_work import PersistenceUnitOfWork

if TYPE_CHECKING:
    from ..core.di import Container
    from ..settings import Settings


__all__ = [
    "DatabaseConnectionError",
    "DatabaseInfo",
    "DatabaseManager",
    "DatabasePort",
    "HistoryEntryData",
    "HistoryRepositoryPort",
    "Migration",
    "MigrationError",
    "MigrationHistoryEntry",
    "MigrationManager",
    "NestedTransactionError",
    "PersistenceError",
    "PersistenceUnitOfWork",
    "ProgressData",
    "ProgressRepositoryPort",
    "REPOSITORY_MIGRATIONS",
    "SQLiteConnectionFactory",
    "SettingData",
    "SettingsRepositoryPort",
    "TopicData",
    "TopicRepositoryPort",
    "TransactionError",
    "TransactionManager",
    "TransactionManagerPort",
    "UnitOfWorkPort",
    "register_persistence",
    "register_repositories",
]


def register_persistence(container: Container, settings: Settings) -> None:
    """Register persistence services in the DI container.

    Call from the composition root after all infrastructure is configured.
    ``DatabaseManager`` is registered as a singleton and automatically
    initialized on first resolution.
    """

    def create_db() -> DatabaseManager:
        db = DatabaseManager(settings.sqlite)
        db.initialize(extra_migrations=REPOSITORY_MIGRATIONS)
        return db

    container.register_factory(DatabaseManager, create_db, lifetime=ServiceLifetime.SINGLETON)
    container.register_factory(
        TransactionManager,
        lambda: TransactionManager(container.resolve(DatabaseManager).connection),
        lifetime=ServiceLifetime.TRANSIENT,
    )
    container.register_factory(
        PersistenceUnitOfWork,
        lambda: PersistenceUnitOfWork(container.resolve(TransactionManager)),
        lifetime=ServiceLifetime.TRANSIENT,
    )
