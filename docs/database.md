# Database Infrastructure

`backend.aicos.persistence` provides the SQLite persistence foundation for
AICOS.  It cleanly separates connection management, transaction control,
schema migration, and the Unit of Work pattern.  Future repository
implementations depend on this layer and never touch raw `sqlite3`.

## Architecture

| Component | Responsibility |
|---|---|
| `SQLiteConnectionFactory` | Creates pre-configured connections (WAL, foreign keys, `Row` factory) |
| `DatabaseManager` | High-level lifecycle — open, close, health check, version, migrations |
| `MigrationManager` | Ordered, idempotent schema upgrades via versioned `Migration` objects |
| `TransactionManager` | Thread-safe `BEGIN` / `COMMIT` / `ROLLBACK`; rejects nesting |
| `PersistenceUnitOfWork` | Context manager wrapping a transaction; auto-rollback on exception |

### Package Layout

```
backend/aicos/persistence/
    __init__.py          # Public API + register_persistence() for DI
    connection.py        # SQLiteConnectionFactory
    database.py          # DatabaseManager
    exceptions.py        # PersistenceError hierarchy
    interfaces.py        # DatabasePort, TransactionManagerPort, UnitOfWorkPort
    migrations.py        # Migration, MigrationManager
    models.py            # DatabaseInfo, MigrationHistoryEntry
    transaction.py       # TransactionManager
    unit_of_work.py      # PersistenceUnitOfWork
```

## Database Lifecycle

```
  Application startup
         │
         ▼
  DatabaseManager(config)
         │
         ▼
  .initialize()
    ├── SQLiteConnectionFactory.create()   ← WAL, foreign keys, Row
    ├── MigrationManager.upgrade()         ← apply pending migrations
    │
    ▼
  Ready for repositories
         │
         ▼
  .close()
```

The `DatabaseManager` is registered as a singleton in the DI container and
is auto-initialized on first resolution.

```python
from backend.aicos.persistence import register_persistence

register_persistence(container, settings)
# On first container.resolve(DatabaseManager) → initialize()
```

## Migration Lifecycle

Migrations are defined as `Migration` objects:

```python
from backend.aicos.persistence import Migration

MIGRATIONS = [
    Migration(1, "create agent table", [
        "CREATE TABLE agents (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
    ]),
    Migration(2, "add email column", [
        "ALTER TABLE agents ADD COLUMN email TEXT",
    ]),
]
```

- Applied once and recorded in the `_schema_versions` table.
- `upgrade()` skips already-applied versions (idempotent).
- Order is determined by ascending version number.

Pass migrations to `register_persistence` or `DatabaseManager.initialize()`:

```python
db = DatabaseManager(config)
db.initialize(MIGRATIONS)
```

Or pass them through the DI factory if customising the composition root.

## Transaction Lifecycle

```
  TransactionManager.begin()
         │
         ▼
  (operations)
         │
         ├── TransactionManager.commit()
         └── TransactionManager.rollback()
```

- Nested transactions raise `NestedTransactionError`.
- All transaction operations are thread-safe (re-entrant lock).

## Unit of Work

The recommended way to manage transactions:

```python
with unit_of_work:
    # write operations
    ...
# auto-committed on success, auto-rolled-back on exception
```

Equivalent to:

```python
unit_of_work.begin()
try:
    ...
    unit_of_work.commit()
except Exception:
    unit_of_work.rollback()
    raise
```

## Future Repository Layer

Repositories will depend on `DatabaseManager` for connection access, not on
`sqlite3` directly.  Each repository method will typically:

```python
class AgentRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def find_by_id(self, agent_id: int) -> Agent | None:
        cursor = self._db.connection.execute(
            "SELECT * FROM agents WHERE id = ?", (agent_id,)
        )
        row = cursor.fetchone()
        return Agent(**row) if row else None
```

The Unit of Work pattern will wrap multi-repository operations:

```python
with uow:
    agent_repo.save(agent)
    event_repo.save(created_event)
```

## Configuration

Reuses the existing `SQLiteConfig` from `backend.aicos.settings`:

| Field | Default | Description |
|---|---|---|
| `path` | `data/aicos.db` | Database file path |
| `timeout_seconds` | `30` | Busy timeout in seconds |
| `wal_enabled` | `True` | Enable WAL journaling mode |

Foreign keys are always enabled via `PRAGMA foreign_keys = ON`.
