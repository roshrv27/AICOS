"""Persistence layer exceptions."""


class PersistenceError(Exception):
    """Base class for all persistence-layer errors."""


class DatabaseConnectionError(PersistenceError):
    """Raised when a database connection cannot be established."""


class MigrationError(PersistenceError):
    """Raised when a database migration fails."""


class TransactionError(PersistenceError):
    """Raised when a transaction operation is invalid."""


class NestedTransactionError(TransactionError):
    """Raised when a nested transaction is attempted."""
