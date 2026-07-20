"""Base repository with SQLite error wrapping and shared helpers."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ..exceptions import PersistenceError
from ...logging import get_logger


class BaseRepository:
    """Provides ``_execute``, ``_fetchone`` and ``_fetchall`` helpers that
    translate :class:`sqlite3.Error` into :class:`PersistenceError`.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._repo_logger = get_logger("database")

    # ── low-level helpers ──────────────────────────────────────────

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        started_at = time.perf_counter()
        try:
            cursor = self._connection.execute(sql, params)
        except sqlite3.Error as exc:
            duration = (time.perf_counter() - started_at) * 1000
            self._repo_logger.error(
                "repository query failed",
                extra={
                    "repository": type(self).__name__,
                    "execution_duration_ms": duration,
                },
            )
            raise PersistenceError(str(exc)) from exc
        return cursor

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        cursor = self._execute(sql, params)
        return cursor.fetchone()

    def _fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        cursor = self._execute(sql, params)
        return cursor.fetchall()

    def _rowcount(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        cursor = self._execute(sql, params)
        return cursor.rowcount

    # ── operation logging helper ───────────────────────────────────

    def _log_operation(self, operation: str, rows_affected: int | None = None) -> None:
        extra: dict[str, Any] = {
            "repository": type(self).__name__,
            "operation": operation,
        }
        if rows_affected is not None:
            extra["rows_affected"] = rows_affected
        self._repo_logger.debug("repository operation", extra=extra)


# ── JSON helpers shared by multiple repositories ──────────────────────


def json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def json_loads(value: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
