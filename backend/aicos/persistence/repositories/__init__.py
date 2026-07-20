"""Repository layer for AICOS persistence.

All repositories obtain their connection through a
:class:`~aicos.persistence.unit_of_work.PersistenceUnitOfWork`
and must never manage transactions themselves.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..migrations import Migration
from ..interfaces import (
    HistoryRepositoryPort,
    ProgressRepositoryPort,
    SettingsRepositoryPort,
    TopicRepositoryPort,
)
from .sqlite import (
    SQLiteHistoryRepository,
    SQLiteProgressRepository,
    SQLiteSettingsRepository,
    SQLiteTopicRepository,
)

if TYPE_CHECKING:
    from ...core.di import Container
    from ...settings import Settings

# ── Table definitions as migration objects ────────────────────────────

TOPICS_TABLE_SQL = """CREATE TABLE IF NOT EXISTS topics (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon        TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '',
    "order"     INTEGER NOT NULL DEFAULT 0,
    type        TEXT NOT NULL DEFAULT 'lesson',
    metadata    TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL,
    updated_at  TEXT
)"""

PROGRESS_TABLE_SQL = """CREATE TABLE IF NOT EXISTS progress (
    topic_id     TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'not_started',
    score        REAL NOT NULL DEFAULT 0.0,
    attempts     INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    metadata     TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (topic_id) REFERENCES topics(id)
)"""

SETTINGS_TABLE_SQL = """CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
)"""

HISTORY_TABLE_SQL = """CREATE TABLE IF NOT EXISTS history (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    topic_id   TEXT NOT NULL,
    created_at TEXT NOT NULL
)"""

CREATE_HISTORY_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id)"
CREATE_HISTORY_TOPIC_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_history_topic ON history(topic_id)"


MIGRATION_TOPICS = Migration(100, "create topics table", [TOPICS_TABLE_SQL])
MIGRATION_PROGRESS = Migration(101, "create progress table", [PROGRESS_TABLE_SQL])
MIGRATION_SETTINGS = Migration(102, "create settings table", [SETTINGS_TABLE_SQL])
MIGRATION_HISTORY = Migration(103, "create history table", [HISTORY_TABLE_SQL])
MIGRATION_HISTORY_INDEX = Migration(104, "create history indexes", [CREATE_HISTORY_INDEX_SQL, CREATE_HISTORY_TOPIC_INDEX_SQL])

REPOSITORY_MIGRATIONS = (
    MIGRATION_TOPICS,
    MIGRATION_PROGRESS,
    MIGRATION_SETTINGS,
    MIGRATION_HISTORY,
    MIGRATION_HISTORY_INDEX,
)

__all__ = [
    "HistoryRepositoryPort",
    "ProgressRepositoryPort",
    "REPOSITORY_MIGRATIONS",
    "SettingsRepositoryPort",
    "SQLiteHistoryRepository",
    "SQLiteProgressRepository",
    "SQLiteSettingsRepository",
    "SQLiteTopicRepository",
    "TopicRepositoryPort",
    "register_repositories",
]


def register_repositories(container: Container, settings: Settings) -> None:
    """Register repository implementations in the DI container.

    Each repository is registered as transient under both its concrete
    type and its protocol interface so that consumers may depend on
    either.
    """
    from ..unit_of_work import PersistenceUnitOfWork

    def _factory(
        repo_cls: type[SQLiteTopicRepository | SQLiteProgressRepository | SQLiteSettingsRepository | SQLiteHistoryRepository],
    ) -> object:
        uow: PersistenceUnitOfWork = container.resolve(PersistenceUnitOfWork)
        return repo_cls(uow.connection)

    for cls, port in [
        (SQLiteTopicRepository, TopicRepositoryPort),
        (SQLiteProgressRepository, ProgressRepositoryPort),
        (SQLiteSettingsRepository, SettingsRepositoryPort),
        (SQLiteHistoryRepository, HistoryRepositoryPort),
    ]:
        container.register_factory(cls, lambda _cls=cls: _factory(_cls))
        container.register_factory(port, lambda _cls=cls: _factory(_cls))
