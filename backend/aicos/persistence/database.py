"""Singleton database manager used throughout AICOS persistence."""

from __future__ import annotations

import sqlite3
import time
from typing import TYPE_CHECKING

from ..logging import get_logger
from .connection import SQLiteConnectionFactory
from .exceptions import DatabaseConnectionError
from .migrations import Migration, MigrationManager
from .transaction import TransactionManager

if TYPE_CHECKING:
    from ..settings import SQLiteConfig


class DatabaseManager:
    """High-level database lifecycle and access.

    Call ``initialize()`` once at startup to open the connection and apply
    pending migrations.  Register through the DI container for automatic
    lifecycle management.
    """

    def __init__(self, config: SQLiteConfig) -> None:
        self._config = config
        self._connection: sqlite3.Connection | None = None
        self._transaction: TransactionManager | None = None
        self._logger = get_logger("database")

    def initialize(self, extra_migrations: tuple[Migration, ...] = ()) -> None:
        """Open the connection and run all pending migrations."""
        started_at = time.perf_counter()
        factory = SQLiteConnectionFactory(
            path=self._config.path,
            timeout_seconds=self._config.timeout_seconds,
            wal_enabled=self._config.wal_enabled,
        )
        self._connection = factory.create()
        self._transaction = TransactionManager(self._connection)
        self._logger.info(
            "database opened",
            extra={
                "path": str(self._config.path),
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        self._run_migrations(extra_migrations)

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise DatabaseConnectionError("database is not initialized; call initialize() first")
        return self._connection

    @property
    def transaction(self) -> TransactionManager:
        if self._transaction is None:
            raise DatabaseConnectionError("database is not initialized; call initialize() first")
        return self._transaction

    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection is not None:
            self._logger.info("database close")
            self._connection.close()
            self._connection = None
            self._transaction = None

    def health_check(self) -> bool:
        """Return ``True`` when the database connection is responsive."""
        try:
            self.connection.execute("SELECT 1")
            return True
        except Exception:
            return False

    def version(self) -> int:
        """Return the highest applied migration version (0 if none)."""
        return self._migration_manager()._current_version()

    def _run_migrations(self, extra: tuple[Migration, ...]) -> None:
        manager = MigrationManager(self.connection)
        manager.upgrade(extra)
        try:
            self._connection.execute("COMMIT")
        except sqlite3.OperationalError:
            pass

    def _migration_manager(self) -> MigrationManager:
        return MigrationManager(self.connection)
