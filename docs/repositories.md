# Repository Layer

The repository layer is the persistence abstraction between application
(business-logic) code and SQLite.  Repositories contain only CRUD logic
— no business rules, no validation, and no transaction management.

## Architecture

```
┌─────────────────────────────┐
│   Application code          │  ← depends on protocol interfaces
│   (business logic)          │
├─────────────────────────────┤
│   RepositoryPort (protocol) │  ← interfaces.py
├─────────────────────────────┤
│   BaseRepository            │  ← error wrapping, shared helpers
├─────────────────────────────┤
│   SQLite*Repository         │  ← concrete implementations
├─────────────────────────────┤
│   PersistenceUnitOfWork     │  ← provides connection
└─────────────────────────────┘
```

## Key Rules

1. **No connection ownership** — repositories never open, commit, or
   rollback connections.  They receive a ``sqlite3.Connection`` from a
   ``PersistenceUnitOfWork``.
2. **No business logic** — repositories do not validate or transform
   data.  They persist and retrieve exactly what they are given.
3. **No raw SQLite exceptions** — all ``sqlite3.Error`` is caught and
   re-raised as ``PersistenceError``.
4. **Parameterised SQL** — all queries use ``?`` placeholders; no
   string concatenation or f-string interpolation in SQL.

## Repositories

| Repository            | Table      | Port                        | Methods |
|-----------------------|------------|-----------------------------|---------|
| ``SQLiteTopicRepository`` | ``topics`` | ``TopicRepositoryPort``  | ``get_all``, ``get_by_id``, ``get_by_category``, ``upsert``, ``delete``, ``count`` |
| ``SQLiteProgressRepository`` | ``progress`` | ``ProgressRepositoryPort`` | ``get_by_topic``, ``get_all``, ``upsert``, ``delete_by_topic``, ``count``, ``get_completed_count`` |
| ``SQLiteSettingsRepository`` | ``settings`` | ``SettingsRepositoryPort`` | ``get``, ``get_all``, ``set``, ``delete``, ``count`` |
| ``SQLiteHistoryRepository`` | ``history`` | ``HistoryRepositoryPort`` | ``get_by_session``, ``get_by_topic``, ``add``, ``delete_by_session``, ``delete_older_than``, ``count`` |

## Data Models

- ``TopicData`` — persistent topic with JSON metadata
- ``ProgressData`` — per-topic user progress
- ``SettingData`` — key/value setting pair
- ``HistoryEntryData`` — single chat history message

## Usage

```python
from aicos.persistence import PersistenceUnitOfWork
from aicos.persistence.repositories import SQLiteTopicRepository
from aicos.persistence.repositories import TopicRepositoryPort

# Via Unit of Work (recommended):
with unit_of_work:
    repo: TopicRepositoryPort = SQLiteTopicRepository(unit_of_work.connection)
    topics = repo.get_all()

# Via DI Container (auto-wired):
container = Container()
register_persistence(container, settings)
register_repositories(container, settings)

repo = container.resolve(TopicRepositoryPort)
```

## Migrations

Repository tables are created by migrations 100–104 defined in
``repositories/__init__.py`` and bundled as ``REPOSITORY_MIGRATIONS``.
They are applied automatically when ``DatabaseManager.initialize()`` is
called through ``register_persistence()``.
