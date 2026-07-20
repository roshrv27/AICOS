"""Ordered, idempotent schema migration manager."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from ..logging import get_logger
from .exceptions import MigrationError

if TYPE_CHECKING:
    from collections.abc import Sequence


_SCHEMA_TABLE = "_schema_versions"
_CREATE_SCHEMA_TABLE = (
    f"CREATE TABLE IF NOT EXISTS {_SCHEMA_TABLE} ("
    "version INTEGER PRIMARY KEY,"
    "description TEXT NOT NULL,"
    "applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    ")"
)
_SELECT_CURRENT = f"SELECT COALESCE(MAX(version), 0) FROM {_SCHEMA_TABLE}"
_INSERT_VERSION = f"INSERT INTO {_SCHEMA_TABLE} (version, description) VALUES (?, ?)"


class Migration:
    """One ordered, named schema change consisting of one or more SQL statements."""

    def __init__(self, version: int, description: str, statements: Sequence[str]) -> None:
        if version < 1:
            raise ValueError("migration version must be >= 1")
        if not description:
            raise ValueError("migration description must not be empty")
        if not statements:
            raise ValueError("migration must contain at least one statement")
        self.version = version
        self.description = description
        self.statements = tuple(statements)


class MigrationManager:
    """Applies outstanding migrations idempotently.

    Migration order is determined by the version number (ascending).
    Already-applied migrations are skipped on subsequent ``upgrade()`` calls.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._logger = get_logger("database")

    def upgrade(self, migrations: Sequence[Migration] = ()) -> None:
        """Apply every pending migration in version order.

        Pass ``migrations`` to supply the full migration set.  If omitted the
        manager looks for a module-level ``MIGRATIONS`` variable (useful for
        composition-root wiring).
        """
        pending = self._pending(migrations)
        for migration in pending:
            self._apply(migration)

    def applied_versions(self) -> tuple[int, ...]:
        """Return every version that has already been applied."""
        self._ensure_schema_table()
        rows = self._connection.execute(
            f"SELECT version FROM {_SCHEMA_TABLE} ORDER BY version"
        ).fetchall()
        return tuple(row["version"] for row in rows)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_schema_table(self) -> None:
        self._connection.execute(_CREATE_SCHEMA_TABLE)

    def _current_version(self) -> int:
        self._ensure_schema_table()
        row = self._connection.execute(_SELECT_CURRENT).fetchone()
        return row[0]  # COALESCE guarantees a value

    def _pending(self, migrations: Sequence[Migration]) -> Sequence[Migration]:
        current = self._current_version()
        return tuple(m for m in migrations if m.version > current)

    def _apply(self, migration: Migration) -> None:
        self._logger.info(
            "migration start",
            extra={"version": migration.version, "description": migration.description},
        )
        try:
            for statement in migration.statements:
                self._connection.execute(statement)
            self._connection.execute(_INSERT_VERSION, (migration.version, migration.description))
        except sqlite3.Error as error:
            msg = f"migration {migration.version} failed: {error}"
            self._logger.exception(msg, extra={"version": migration.version})
            raise MigrationError(msg) from error
        self._logger.info(
            "migration finish",
            extra={"version": migration.version, "description": migration.description},
        )
