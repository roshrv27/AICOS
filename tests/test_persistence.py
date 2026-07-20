"""Comprehensive tests for the AICOS persistence layer."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from backend.aicos.core.di import Container
from backend.aicos.logging import shutdown_logging
from backend.aicos.persistence import (
    DatabaseConnectionError,
    DatabaseManager,
    DatabasePort,
    Migration,
    MigrationError,
    MigrationManager,
    NestedTransactionError,
    PersistenceUnitOfWork,
    SQLiteConnectionFactory,
    TransactionError,
    TransactionManager,
    TransactionManagerPort,
    UnitOfWorkPort,
    register_persistence,
)
from backend.aicos.persistence.exceptions import PersistenceError
from backend.aicos.settings import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def memory_factory() -> SQLiteConnectionFactory:
    """Return a factory that creates in-memory databases for testing."""
    return SQLiteConnectionFactory(path=":memory:", timeout_seconds=1)


def memory_db_manager() -> DatabaseManager:
    """Return an initialized DatabaseManager backed by an in-memory database."""
    settings = Settings(config_dir="missing-config")
    settings.sqlite.path = ":memory:"
    db = DatabaseManager(settings.sqlite)
    db.initialize()
    return db


# ---------------------------------------------------------------------------
# SQLiteConnectionFactory
# ---------------------------------------------------------------------------

class SQLiteConnectionFactoryTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_create_returns_open_connection(self) -> None:
        factory = memory_factory()
        conn = factory.create()
        self.assertIsInstance(conn, sqlite3.Connection)
        row = conn.execute("SELECT 1 AS val").fetchone()
        self.assertEqual(row["val"], 1)
        conn.close()

    def test_foreign_keys_are_enabled(self) -> None:
        factory = memory_factory()
        conn = factory.create()
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        self.assertEqual(row[0], 1)
        conn.close()

    def test_row_factory_is_sqlite3_row(self) -> None:
        factory = memory_factory()
        conn = factory.create()
        self.assertIs(conn.row_factory, sqlite3.Row)
        conn.close()

    def test_wal_mode_is_set_when_enabled(self) -> None:
        factory = SQLiteConnectionFactory(path=":memory:", wal_enabled=True)
        conn = factory.create()
        row = conn.execute("PRAGMA journal_mode").fetchone()
        self.assertIn(row[0].upper(), ("WAL", "MEMORY"))
        conn.close()

    def test_wal_mode_can_be_disabled(self) -> None:
        factory = SQLiteConnectionFactory(path=":memory:", wal_enabled=False)
        conn = factory.create()
        row = conn.execute("PRAGMA journal_mode").fetchone()
        self.assertNotEqual(row[0].upper(), "WAL")
        conn.close()

    def test_creates_directory_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "sub", "test.db")
            factory = SQLiteConnectionFactory(path=db_path, wal_enabled=False)
            conn = factory.create()
            self.assertTrue(os.path.isfile(db_path))
            conn.close()


# ---------------------------------------------------------------------------
# MigrationManager
# ---------------------------------------------------------------------------

SAMPLE_MIGRATIONS = (
    Migration(1, "create table a", ["CREATE TABLE a (id INTEGER PRIMARY KEY, name TEXT)"]),
    Migration(2, "create table b", ["CREATE TABLE b (id INTEGER PRIMARY KEY, value TEXT)"]),
    Migration(3, "add column", ["ALTER TABLE a ADD COLUMN email TEXT"]),
)


class MigrationManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.manager = MigrationManager(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        shutdown_logging()

    def test_upgrade_applies_all_migrations(self) -> None:
        self.manager.upgrade(SAMPLE_MIGRATIONS)
        versions = self.manager.applied_versions()
        self.assertEqual(versions, (1, 2, 3))

    def test_upgrade_is_idempotent(self) -> None:
        self.manager.upgrade(SAMPLE_MIGRATIONS)
        self.manager.upgrade(SAMPLE_MIGRATIONS)
        versions = self.manager.applied_versions()
        self.assertEqual(versions, (1, 2, 3))

    def test_applied_versions_empty_initially(self) -> None:
        versions = self.manager.applied_versions()
        self.assertEqual(versions, ())

    def test_partial_upgrade_skips_applied(self) -> None:
        partial = (Migration(1, "first", ["CREATE TABLE IF NOT EXISTS x (id INTEGER PRIMARY KEY)"]),)
        self.manager.upgrade(partial)

        full = partial + (Migration(2, "second", ["CREATE TABLE IF NOT EXISTS y (id INTEGER PRIMARY KEY)"]),)
        self.manager.upgrade(full)

        self.assertEqual(self.manager.applied_versions(), (1, 2))

    def test_migration_creates_schema_version_table(self) -> None:
        self.manager.upgrade(SAMPLE_MIGRATIONS)
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_versions'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_migration_with_invalid_sql_raises_error(self) -> None:
        bad = (Migration(1, "bad", ["CREATE TABLE"]),)
        with self.assertRaises(MigrationError):
            self.manager.upgrade(bad)

    def test_current_version_returns_zero_without_migrations(self) -> None:
        self.manager.upgrade(())
        self.assertEqual(self.manager.applied_versions(), ())

    def test_migration_version_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            Migration(0, "zero", ["SELECT 1"])

    def test_migration_description_must_not_be_empty(self) -> None:
        with self.assertRaises(ValueError):
            Migration(1, "", ["SELECT 1"])

    def test_migration_must_have_statements(self) -> None:
        with self.assertRaises(ValueError):
            Migration(1, "empty", [])


# ---------------------------------------------------------------------------
# TransactionManager
# ---------------------------------------------------------------------------

class TransactionManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)"
        )
        self.tx = TransactionManager(self.conn)

    def tearDown(self) -> None:
        if self.tx.is_active:
            self.conn.execute("ROLLBACK")
        self.conn.close()
        shutdown_logging()

    def test_begin_starts_transaction(self) -> None:
        self.tx.begin()
        self.assertTrue(self.tx.is_active)

    def test_commit_persists_changes(self) -> None:
        self.tx.begin()
        self.conn.execute("INSERT INTO test (val) VALUES ('hello')")
        self.tx.commit()
        self.assertFalse(self.tx.is_active)
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 1)

    def test_rollback_undoes_changes(self) -> None:
        self.tx.begin()
        self.conn.execute("INSERT INTO test (val) VALUES ('hello')")
        self.tx.rollback()
        self.assertFalse(self.tx.is_active)
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 0)

    def test_nested_begin_raises_error(self) -> None:
        self.tx.begin()
        with self.assertRaises(NestedTransactionError):
            self.tx.begin()

    def test_commit_without_active_transaction_raises_error(self) -> None:
        with self.assertRaises(TransactionError):
            self.tx.commit()

    def test_rollback_without_active_transaction_raises_error(self) -> None:
        with self.assertRaises(TransactionError):
            self.tx.rollback()

    def test_is_active_returns_false_initially(self) -> None:
        self.assertFalse(self.tx.is_active)

    def test_is_active_returns_true_during_transaction(self) -> None:
        self.tx.begin()
        self.assertTrue(self.tx.is_active)

    def test_multiple_begin_commit_cycles(self) -> None:
        for i in range(3):
            self.tx.begin()
            self.conn.execute("INSERT INTO test (val) VALUES (?)", (str(i),))
            self.tx.commit()
            self.assertFalse(self.tx.is_active)
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 3)


# ---------------------------------------------------------------------------
# PersistenceUnitOfWork
# ---------------------------------------------------------------------------

class PersistenceUnitOfWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)"
        )
        self.tx = TransactionManager(self.conn)
        self.uow = PersistenceUnitOfWork(self.tx)

    def tearDown(self) -> None:
        if self.tx.is_active:
            self.conn.execute("ROLLBACK")
        self.conn.close()
        shutdown_logging()

    def test_context_manager_commits_on_success(self) -> None:
        with self.uow:
            self.conn.execute("INSERT INTO test (val) VALUES ('success')")
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 1)

    def test_context_manager_rolls_back_on_exception(self) -> None:
        try:
            with self.uow:
                self.conn.execute("INSERT INTO test (val) VALUES ('will_rollback')")
                raise ValueError("simulated failure")
        except ValueError:
            pass
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 0)

    def test_explicit_begin_commit(self) -> None:
        self.uow.begin()
        self.conn.execute("INSERT INTO test (val) VALUES ('explicit')")
        self.uow.commit()
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 1)

    def test_explicit_begin_rollback(self) -> None:
        self.uow.begin()
        self.conn.execute("INSERT INTO test (val) VALUES ('rolled')")
        self.uow.rollback()
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 0)

    def test_context_manager_is_reusable(self) -> None:
        for i in range(3):
            with self.uow:
                self.conn.execute("INSERT INTO test (val) VALUES (?)", (str(i),))
        count = self.conn.execute("SELECT COUNT(*) AS cnt FROM test").fetchone()["cnt"]
        self.assertEqual(count, 3)

    def test_nested_context_manager_raises_nested_error(self) -> None:
        with self.assertRaises(NestedTransactionError):
            with self.uow:
                with self.uow:
                    pass


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManagerTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_initialize_opens_connection(self) -> None:
        db = memory_db_manager()
        self.assertTrue(db.health_check())
        db.close()

    def test_health_check_returns_true_when_connected(self) -> None:
        db = memory_db_manager()
        self.assertTrue(db.health_check())
        db.close()

    def test_health_check_returns_false_when_closed(self) -> None:
        db = memory_db_manager()
        db.close()
        self.assertFalse(db.health_check())

    def test_version_returns_zero_initially(self) -> None:
        db = memory_db_manager()
        self.assertEqual(db.version(), 0)
        db.close()

    def test_version_returns_highest_migration(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        db = DatabaseManager(settings.sqlite)
        db.initialize(SAMPLE_MIGRATIONS)
        self.assertEqual(db.version(), 3)
        db.close()

    def test_connection_property_raises_before_initialize(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        db = DatabaseManager(settings.sqlite)
        with self.assertRaises(DatabaseConnectionError):
            _ = db.connection

    def test_transaction_property_raises_before_initialize(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        db = DatabaseManager(settings.sqlite)
        with self.assertRaises(DatabaseConnectionError):
            _ = db.transaction

    def test_close_cleans_up_connection(self) -> None:
        db = memory_db_manager()
        db.close()
        with self.assertRaises(DatabaseConnectionError):
            _ = db.connection

    def test_initialize_runs_migrations(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        db = DatabaseManager(settings.sqlite)
        db.initialize(SAMPLE_MIGRATIONS)
        self.assertEqual(db.version(), 3)
        db.close()

    def test_initialize_is_idempotent(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        db = DatabaseManager(settings.sqlite)
        db.initialize(SAMPLE_MIGRATIONS)
        db.initialize(SAMPLE_MIGRATIONS)
        self.assertEqual(db.version(), 3)
        db.close()

    def test_transaction_manager_works(self) -> None:
        db = memory_db_manager()
        db.transaction.begin()
        db.connection.execute(
            "CREATE TABLE IF NOT EXISTS verify (id INTEGER PRIMARY KEY)"
        )
        db.transaction.commit()
        self.assertTrue(db.health_check())
        db.close()


# ---------------------------------------------------------------------------
# DI Registration
# ---------------------------------------------------------------------------

class PersistenceDIRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.container = Container()

    def tearDown(self) -> None:
        shutdown_logging()

    def test_register_persistence_resolves_singleton(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        register_persistence(self.container, settings)

        db = self.container.resolve(DatabaseManager)
        self.assertIsInstance(db, DatabaseManager)
        self.assertTrue(db.health_check())
        db.close()

    def test_database_manager_is_singleton(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        register_persistence(self.container, settings)

        db1 = self.container.resolve(DatabaseManager)
        db2 = self.container.resolve(DatabaseManager)
        self.assertIs(db1, db2)
        db1.close()

    def test_transaction_manager_is_transient(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        register_persistence(self.container, settings)

        tx1 = self.container.resolve(TransactionManager)
        tx2 = self.container.resolve(TransactionManager)
        self.assertIsNot(tx1, tx2)

    def test_unit_of_work_is_transient(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        register_persistence(self.container, settings)

        uow1 = self.container.resolve(PersistenceUnitOfWork)
        uow2 = self.container.resolve(PersistenceUnitOfWork)
        self.assertIsNot(uow1, uow2)

    def test_di_integration_with_uow(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        register_persistence(self.container, settings)

        db = self.container.resolve(DatabaseManager)
        db.connection.execute(
            "CREATE TABLE IF NOT EXISTS di_test (id INTEGER PRIMARY KEY, val TEXT)"
        )

        uow = self.container.resolve(PersistenceUnitOfWork)
        with uow:
            db.connection.execute(
                "INSERT INTO di_test (val) VALUES ('di_works')"
            )

        count = db.connection.execute(
            "SELECT COUNT(*) AS cnt FROM di_test"
        ).fetchone()["cnt"]
        self.assertEqual(count, 1)
        db.close()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PersistenceExceptionHierarchyTests(unittest.TestCase):
    def test_persistence_error_is_base(self) -> None:
        self.assertTrue(issubclass(DatabaseConnectionError, PersistenceError))
        self.assertTrue(issubclass(MigrationError, PersistenceError))
        self.assertTrue(issubclass(TransactionError, PersistenceError))

    def test_nested_transaction_error_is_transaction_error(self) -> None:
        self.assertTrue(issubclass(NestedTransactionError, TransactionError))


# ---------------------------------------------------------------------------
# Interfaces (Protocols)
# ---------------------------------------------------------------------------

class PersistenceInterfacesTests(unittest.TestCase):
    def test_database_port_is_protocol(self) -> None:
        db = memory_db_manager()
        self.assertIsInstance(db, DatabasePort)
        db.close()

    def test_transaction_manager_port_is_protocol(self) -> None:
        conn = sqlite3.connect(":memory:")
        tx = TransactionManager(conn)
        self.assertIsInstance(tx, TransactionManagerPort)
        conn.close()

    def test_unit_of_work_port_is_protocol(self) -> None:
        conn = sqlite3.connect(":memory:")
        tx = TransactionManager(conn)
        uow = PersistenceUnitOfWork(tx)
        self.assertIsInstance(uow, UnitOfWorkPort)
        conn.close()


# ---------------------------------------------------------------------------
# SQLiteConnectionFactory file-based lifecycle
# ---------------------------------------------------------------------------

class ConnectionLifecycleTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_file_based_database_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "lifecycle.db")
            factory = SQLiteConnectionFactory(path=db_path, wal_enabled=False)
            conn = factory.create()
            self.assertTrue(os.path.isfile(db_path))
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            conn.close()

    def test_multiple_connections_to_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "multi.db")
            factory = SQLiteConnectionFactory(path=db_path, wal_enabled=False)
            c1 = factory.create()
            c1.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
            c1.execute("INSERT INTO t VALUES (1, 'hello')")
            c1.commit()

            c2 = factory.create()
            row = c2.execute("SELECT val FROM t WHERE id = 1").fetchone()
            self.assertEqual(row["val"], "hello")

            c1.close()
            c2.close()


if __name__ == "__main__":
    unittest.main()
