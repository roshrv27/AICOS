"""Thread-safe SQLite connection factory.

Prevents direct exposure of the ``sqlite3`` module to callers.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteConnectionFactory:
    """Creates pre-configured SQLite connections from validated settings.

    Every connection has:
    * ``row_factory = sqlite3.Row`` for column-name access.
    * ``PRAGMA foreign_keys = ON`` for referential integrity.
    * ``PRAGMA journal_mode = WAL`` (configurable) for concurrent reads.
    * A configurable busy timeout.
    """

    def __init__(
        self,
        *,
        path: str | Path,
        timeout_seconds: int = 30,
        wal_enabled: bool = True,
    ) -> None:
        self._path = Path(path)
        self._timeout = timeout_seconds
        self._wal = wal_enabled

    def create(self) -> sqlite3.Connection:
        """Open and configure a new SQLite connection."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            str(self._path),
            timeout=self._timeout,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if self._wal:
            connection.execute("PRAGMA journal_mode = WAL")
        return connection
