"""Comprehensive tests for the AICOS repository layer."""

from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timezone
from typing import Any

from backend.aicos.persistence import (
    REPOSITORY_MIGRATIONS,
    HistoryEntryData,
    HistoryRepositoryPort,
    MigrationHistoryEntry,
    PersistenceError,
    ProgressData,
    ProgressRepositoryPort,
    SettingData,
    SettingsRepositoryPort,
    TopicData,
    TopicRepositoryPort,
    register_persistence,
)
from backend.aicos.persistence.database import DatabaseManager
from backend.aicos.persistence.migrations import MigrationManager
from backend.aicos.persistence.repositories.base import BaseRepository
from backend.aicos.persistence.repositories.sqlite import (
    SQLiteHistoryRepository,
    SQLiteProgressRepository,
    SQLiteSettingsRepository,
    SQLiteTopicRepository,
)
from backend.aicos.settings import Settings


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _setup_tables(conn: sqlite3.Connection) -> None:
    manager = MigrationManager(conn)
    manager.upgrade(REPOSITORY_MIGRATIONS)


def _make_topic(
    topic_id: str = "t1",
    name: str = "Test Topic",
    category: str = "math",
    order: int = 1,
    metadata_: dict[str, Any] | None = None,
) -> TopicData:
    return TopicData(
        id=topic_id,
        name=name,
        description="A test topic",
        icon="📐",
        category=category,
        order=order,
        type="lesson",
        metadata=metadata_ or {},
        created_at=_utcnow(),
        updated_at=None,
    )


def _make_progress(
    topic_id: str = "t1",
    status: str = "completed",
    score: float = 0.95,
    metadata_: dict[str, Any] | None = None,
) -> ProgressData:
    return ProgressData(
        topic_id=topic_id,
        status=status,
        score=score,
        attempts=2,
        completed_at=_utcnow(),
        metadata=metadata_ or {},
    )


def _make_setting(key: str = "theme", value: str = "dark") -> SettingData:
    return SettingData(key=key, value=value, updated_at=_utcnow())


def _make_history(
    entry_id: str = "h1",
    session_id: str = "s1",
    topic_id: str = "t1",
    content: str = "Hello",
    role: str = "user",
    created_at: str | None = None,
) -> HistoryEntryData:
    return HistoryEntryData(
        id=entry_id,
        session_id=session_id,
        role=role,
        content=content,
        topic_id=topic_id,
        created_at=created_at or _utcnow(),
    )


# ── BaseRepository ────────────────────────────────────────────────────


class TestBaseRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        self.repo = BaseRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_execute_returns_cursor(self) -> None:
        cursor = self.repo._execute("INSERT INTO test (val) VALUES ('a')")
        self.assertIsInstance(cursor, sqlite3.Cursor)

    def test_fetchone_returns_row(self) -> None:
        self.conn.execute("INSERT INTO test VALUES (1, 'hello')")
        row = self.repo._fetchone("SELECT * FROM test WHERE id = ?", (1,))
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["val"], "hello")

    def test_fetchone_returns_none_when_missing(self) -> None:
        row = self.repo._fetchone("SELECT * FROM test WHERE id = ?", (999,))
        self.assertIsNone(row)

    def test_fetchall_returns_list(self) -> None:
        self.conn.execute("INSERT INTO test VALUES (1, 'a')")
        self.conn.execute("INSERT INTO test VALUES (2, 'b')")
        rows = self.repo._fetchall("SELECT * FROM test ORDER BY id")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["val"], "a")

    def test_fetchall_returns_empty_list(self) -> None:
        rows = self.repo._fetchall("SELECT * FROM test")
        self.assertEqual(rows, [])

    def test_rowcount_returns_affected_rows(self) -> None:
        self.conn.execute("INSERT INTO test VALUES (1, 'a')")
        self.conn.execute("INSERT INTO test VALUES (2, 'b')")
        count = self.repo._rowcount("DELETE FROM test WHERE id = ?", (1,))
        self.assertEqual(count, 1)

    def test_sqlite_error_wrapped_as_persistence_error(self) -> None:
        with self.assertRaises(PersistenceError):
            self.repo._execute("SELECT * FROM nonexistent")


# ── SQLiteTopicRepository ─────────────────────────────────────────────


class TestSQLiteTopicRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        _setup_tables(self.conn)
        self.repo = SQLiteTopicRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_empty_count_is_zero(self) -> None:
        self.assertEqual(self.repo.count(), 0)

    def test_upsert_and_get_by_id(self) -> None:
        topic = _make_topic()
        self.repo.upsert(topic)
        result = self.repo.get_by_id("t1")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.name, "Test Topic")
        self.assertEqual(result.category, "math")

    def test_get_by_id_returns_none_when_missing(self) -> None:
        result = self.repo.get_by_id("nonexistent")
        self.assertIsNone(result)

    def test_get_all_returns_inserted_topics(self) -> None:
        self.repo.upsert(_make_topic("t1", "A"))
        self.repo.upsert(_make_topic("t2", "B"))
        topics = self.repo.get_all()
        self.assertEqual(len(topics), 2)
        self.assertEqual([t.name for t in topics], ["A", "B"])

    def test_get_all_orders_by_order(self) -> None:
        t1 = _make_topic("t2", "Second", order=2)
        t2 = _make_topic("t1", "First", order=1)
        self.repo.upsert(t1)
        self.repo.upsert(t2)
        topics = self.repo.get_all()
        self.assertEqual([t.id for t in topics], ["t1", "t2"])

    def test_get_by_category(self) -> None:
        self.repo.upsert(_make_topic("t1", "A", category="math"))
        self.repo.upsert(_make_topic("t2", "B", category="science"))
        self.repo.upsert(_make_topic("t3", "C", category="math"))
        math_topics = self.repo.get_by_category("math")
        self.assertEqual(len(math_topics), 2)
        self.assertEqual([t.id for t in math_topics], ["t1", "t3"])

    def test_delete_returns_true(self) -> None:
        self.repo.upsert(_make_topic())
        self.assertTrue(self.repo.delete("t1"))
        self.assertIsNone(self.repo.get_by_id("t1"))

    def test_delete_returns_false_when_missing(self) -> None:
        self.assertFalse(self.repo.delete("nonexistent"))

    def test_upsert_updates_existing(self) -> None:
        self.repo.upsert(_make_topic("t1", "Original"))
        self.repo.upsert(_make_topic("t1", "Updated"))
        result = self.repo.get_by_id("t1")
        assert result is not None
        self.assertEqual(result.name, "Updated")

    def test_metadata_is_preserved(self) -> None:
        meta = {"difficulty": 3, "tags": ["test"]}
        self.repo.upsert(_make_topic("t1", metadata_=meta))
        result = self.repo.get_by_id("t1")
        assert result is not None
        self.assertEqual(result.metadata, meta)

    def test_port_protocol_satisfied(self) -> None:
        self.assertIsInstance(self.repo, TopicRepositoryPort)

    def test_count_returns_correct_number(self) -> None:
        self.repo.upsert(_make_topic("t1"))
        self.repo.upsert(_make_topic("t2"))
        self.assertEqual(self.repo.count(), 2)


# ── SQLiteProgressRepository ──────────────────────────────────────────


class TestSQLiteProgressRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        _setup_tables(self.conn)
        self.repo = SQLiteProgressRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_empty_count_is_zero(self) -> None:
        self.assertEqual(self.repo.count(), 0)

    def test_upsert_and_get_by_topic(self) -> None:
        prog = _make_progress()
        self.repo.upsert(prog)
        result = self.repo.get_by_topic("t1")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.status, "completed")
        self.assertAlmostEqual(result.score, 0.95)

    def test_get_by_topic_returns_none_when_missing(self) -> None:
        result = self.repo.get_by_topic("nonexistent")
        self.assertIsNone(result)

    def test_get_all(self) -> None:
        self.repo.upsert(_make_progress("t1"))
        self.repo.upsert(_make_progress("t2", status="in_progress"))
        all_ = self.repo.get_all()
        self.assertEqual(len(all_), 2)

    def test_upsert_updates_existing(self) -> None:
        self.repo.upsert(_make_progress("t1", score=0.5))
        self.repo.upsert(_make_progress("t1", score=1.0))
        result = self.repo.get_by_topic("t1")
        assert result is not None
        self.assertAlmostEqual(result.score, 1.0)
        self.assertEqual(result.attempts, 2)

    def test_delete_by_topic_returns_true(self) -> None:
        self.repo.upsert(_make_progress())
        self.assertTrue(self.repo.delete_by_topic("t1"))
        self.assertEqual(self.repo.count(), 0)

    def test_delete_by_topic_returns_false_when_missing(self) -> None:
        self.assertFalse(self.repo.delete_by_topic("nonexistent"))

    def test_get_completed_count(self) -> None:
        self.repo.upsert(_make_progress("t1", status="completed"))
        self.repo.upsert(_make_progress("t2", status="in_progress"))
        self.repo.upsert(_make_progress("t3", status="completed"))
        self.assertEqual(self.repo.get_completed_count(), 2)

    def test_metadata_is_preserved(self) -> None:
        meta = {"hints_used": 2}
        self.repo.upsert(_make_progress("t1", metadata_=meta))
        result = self.repo.get_by_topic("t1")
        assert result is not None
        self.assertEqual(result.metadata, meta)

    def test_count_returns_correct_number(self) -> None:
        self.repo.upsert(_make_progress("t1"))
        self.repo.upsert(_make_progress("t2"))
        self.assertEqual(self.repo.count(), 2)

    def test_port_protocol_satisfied(self) -> None:
        self.assertIsInstance(self.repo, ProgressRepositoryPort)


# ── SQLiteSettingsRepository ──────────────────────────────────────────


class TestSQLiteSettingsRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        _setup_tables(self.conn)
        self.repo = SQLiteSettingsRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_empty_count_is_zero(self) -> None:
        self.assertEqual(self.repo.count(), 0)

    def test_set_and_get(self) -> None:
        self.repo.set("theme", "dark")
        result = self.repo.get("theme")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.value, "dark")

    def test_get_returns_none_when_missing(self) -> None:
        result = self.repo.get("nonexistent")
        self.assertIsNone(result)

    def test_set_updates_existing(self) -> None:
        self.repo.set("theme", "dark")
        self.repo.set("theme", "light")
        result = self.repo.get("theme")
        assert result is not None
        self.assertEqual(result.value, "light")

    def test_get_all(self) -> None:
        self.repo.set("theme", "dark")
        self.repo.set("lang", "en")
        all_ = self.repo.get_all()
        self.assertEqual(len(all_), 2)
        self.assertEqual([s.key for s in all_], ["lang", "theme"])

    def test_delete_returns_true(self) -> None:
        self.repo.set("temp", "value")
        self.assertTrue(self.repo.delete("temp"))
        self.assertIsNone(self.repo.get("temp"))

    def test_delete_returns_false_when_missing(self) -> None:
        self.assertFalse(self.repo.delete("nonexistent"))

    def test_count_returns_correct_number(self) -> None:
        self.repo.set("a", "1")
        self.repo.set("b", "2")
        self.assertEqual(self.repo.count(), 2)

    def test_port_protocol_satisfied(self) -> None:
        self.assertIsInstance(self.repo, SettingsRepositoryPort)


# ── SQLiteHistoryRepository ───────────────────────────────────────────


class TestSQLiteHistoryRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        _setup_tables(self.conn)
        self.repo = SQLiteHistoryRepository(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_empty_count_is_zero(self) -> None:
        self.assertEqual(self.repo.count(), 0)

    def test_add_and_get_by_session(self) -> None:
        entry = _make_history()
        self.repo.add(entry)
        results = self.repo.get_by_session("s1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "Hello")

    def test_get_by_session_orders_by_created_at(self) -> None:
        early = _make_history("h1", "s1", content="First")
        later = _make_history("h2", "s1", content="Second")
        self.repo.add(early)
        self.repo.add(later)
        results = self.repo.get_by_session("s1")
        self.assertEqual([r.id for r in results], ["h1", "h2"])

    def test_get_by_session_returns_empty_when_missing(self) -> None:
        self.assertEqual(self.repo.get_by_session("nonexistent"), [])

    def test_get_by_topic(self) -> None:
        self.repo.add(_make_history("h1", "s1", topic_id="t1"))
        self.repo.add(_make_history("h2", "s2", topic_id="t1"))
        self.repo.add(_make_history("h3", "s3", topic_id="t2"))
        results = self.repo.get_by_topic("t1")
        self.assertEqual(len(results), 2)
        self.assertEqual({r.id for r in results}, {"h1", "h2"})

    def test_get_by_topic_orders_by_created_at(self) -> None:
        early = _make_history("h1", "s1", "t1", content="A")
        later = _make_history("h2", "s1", "t1", content="B")
        self.repo.add(early)
        self.repo.add(later)
        results = self.repo.get_by_topic("t1")
        self.assertEqual([r.id for r in results], ["h1", "h2"])

    def test_delete_by_session(self) -> None:
        self.repo.add(_make_history("h1", "s1"))
        self.repo.add(_make_history("h2", "s1"))
        self.assertTrue(self.repo.delete_by_session("s1"))
        self.assertEqual(self.repo.count(), 0)

    def test_delete_by_session_returns_false_when_missing(self) -> None:
        self.assertFalse(self.repo.delete_by_session("nonexistent"))

    def test_delete_older_than(self) -> None:
        old_ts = "2020-01-01T00:00:00"
        recent_ts = "2030-01-01T00:00:00"
        self.repo.add(_make_history("h1", "s1", created_at=old_ts))
        self.repo.add(_make_history("h2", "s1", created_at=recent_ts))
        deleted = self.repo.delete_older_than("2025-01-01T00:00:00")
        self.assertEqual(deleted, 1)
        self.assertEqual(self.repo.count(), 1)
        self.assertEqual(self.repo.get_by_session("s1")[0].id, "h2")

    def test_delete_older_than_returns_zero_when_none_match(self) -> None:
        future_ts = "2040-01-01T00:00:00"
        self.repo.add(_make_history("h1", "s1", created_at=future_ts))
        deleted = self.repo.delete_older_than("2035-01-01T00:00:00")
        self.assertEqual(deleted, 0)
        self.assertEqual(self.repo.count(), 1)

    def test_count_returns_correct_number(self) -> None:
        self.repo.add(_make_history("h1"))
        self.repo.add(_make_history("h2"))
        self.assertEqual(self.repo.count(), 2)

    def test_port_protocol_satisfied(self) -> None:
        self.assertIsInstance(self.repo, HistoryRepositoryPort)


# ── Repository migrations ─────────────────────────────────────────────


class TestRepositoryMigrations(unittest.TestCase):
    def test_all_migrations_have_unique_versions(self) -> None:
        versions = [m.version for m in REPOSITORY_MIGRATIONS]
        self.assertEqual(len(versions), len(set(versions)))

    def test_migrations_apply_successfully(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        manager = MigrationManager(conn)
        manager.upgrade(REPOSITORY_MIGRATIONS)
        versions = manager.applied_versions()
        expected = tuple(m.version for m in REPOSITORY_MIGRATIONS)
        self.assertEqual(versions, expected)
        conn.close()

    def test_all_tables_exist_after_migration(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        manager = MigrationManager(conn)
        manager.upgrade(REPOSITORY_MIGRATIONS)
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in ("topics", "progress", "settings", "history"):
            self.assertIn(table, tables)
        conn.close()

    def test_foreign_key_on_progress(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        manager = MigrationManager(conn)
        manager.upgrade(REPOSITORY_MIGRATIONS)

        conn.execute("INSERT INTO topics (id, name, created_at) VALUES ('t1', 'T', '2024-01-01')")
        conn.execute("INSERT INTO progress (topic_id, status) VALUES ('t1', 'started')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO progress (topic_id, status) VALUES ('bad', 'started')")
        conn.close()

    def test_migration_is_idempotent(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        manager = MigrationManager(conn)
        manager.upgrade(REPOSITORY_MIGRATIONS)
        manager.upgrade(REPOSITORY_MIGRATIONS)
        versions = manager.applied_versions()
        expected = tuple(m.version for m in REPOSITORY_MIGRATIONS)
        self.assertEqual(versions, expected)
        conn.close()


# ── Integration: full persistence stack ───────────────────────────────


class TestRepositoryPersistenceIntegration(unittest.TestCase):
    def test_repositories_work_with_full_stack(self) -> None:
        from backend.aicos.core.di import Container

        container = Container()
        settings = Settings(config_dir="missing-config")
        settings.sqlite.path = ":memory:"
        register_persistence(container, settings)

        db = container.resolve(DatabaseManager)
        topic_repo = SQLiteTopicRepository(db.connection)
        progress_repo = SQLiteProgressRepository(db.connection)
        settings_repo = SQLiteSettingsRepository(db.connection)
        history_repo = SQLiteHistoryRepository(db.connection)

        topic = _make_topic("t1", "Algebra")
        topic_repo.upsert(topic)
        self.assertEqual(topic_repo.count(), 1)

        progress_repo.upsert(_make_progress("t1", score=0.85))
        self.assertEqual(progress_repo.get_completed_count(), 1)

        settings_repo.set("language", "fr")
        self.assertEqual(settings_repo.count(), 1)

        history_repo.add(_make_history("h1", "s1", "t1"))
        self.assertEqual(history_repo.count(), 1)

        db.close()


if __name__ == "__main__":
    unittest.main()
