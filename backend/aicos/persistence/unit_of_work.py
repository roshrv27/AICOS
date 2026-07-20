"""Context-managed Unit of Work for safe transaction boundaries."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

from ..logging import get_logger

if TYPE_CHECKING:
    import sqlite3

    from .transaction import TransactionManager


class PersistenceUnitOfWork:
    """Wraps a ``TransactionManager`` in a context manager.

    Usage::

        with unit_of_work:
            # perform database operations
            ...

    On success the transaction is committed.  On any exception the
    transaction is rolled back automatically.
    """

    def __init__(self, transaction_manager: TransactionManager) -> None:
        self._transaction = transaction_manager
        self._logger = get_logger("database")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._transaction.connection

    def __enter__(self) -> PersistenceUnitOfWork:
        self._transaction.begin()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self._transaction.rollback()
        else:
            self._transaction.commit()

    def begin(self) -> None:
        self._transaction.begin()

    def commit(self) -> None:
        self._transaction.commit()

    def rollback(self) -> None:
        self._transaction.rollback()
