"""Thread-safe SQLite transaction manager.

Rejects nested transactions explicitly with a custom exception.
"""

from __future__ import annotations

import sqlite3
from threading import RLock

from ..logging import get_logger, logging_context
from .exceptions import NestedTransactionError, TransactionError


class TransactionManager:
    """Manages a single active transaction on one connection.

    Every public method is protected by a re-entrant lock to prevent
    concurrent callers from corrupting transaction state.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = RLock()
        self._active = False
        self._logger = get_logger("database")

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def begin(self) -> None:
        with self._lock:
            if self._active:
                raise NestedTransactionError("nested transactions are not supported")
            self._connection.execute("BEGIN")
            self._active = True
            self._logger.info("transaction begin")

    def commit(self) -> None:
        with self._lock:
            if not self._active:
                raise TransactionError("no active transaction to commit")
            self._connection.execute("COMMIT")
            self._active = False
            self._logger.info("transaction commit")

    def rollback(self) -> None:
        with self._lock:
            if not self._active:
                raise TransactionError("no active transaction to roll back")
            self._connection.execute("ROLLBACK")
            self._active = False
            self._logger.info("transaction rollback")
