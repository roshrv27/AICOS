"""SQLite-backed chat history repository."""

from __future__ import annotations

from ...models import HistoryEntryData
from ..base import BaseRepository


class SQLiteHistoryRepository(BaseRepository):
    """Persists chat history entries in the ``history`` table."""

    def get_by_session(self, session_id: str) -> list[HistoryEntryData]:
        rows = self._fetchall(
            "SELECT * FROM history WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        result = [HistoryEntryData(**dict(r)) for r in rows]
        self._log_operation("get_by_session", rows_affected=len(result))
        return result

    def get_by_topic(self, topic_id: str) -> list[HistoryEntryData]:
        rows = self._fetchall(
            "SELECT * FROM history WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        )
        result = [HistoryEntryData(**dict(r)) for r in rows]
        self._log_operation("get_by_topic", rows_affected=len(result))
        return result

    def add(self, entry: HistoryEntryData) -> None:
        self._execute(
            "INSERT INTO history (id, session_id, role, content, topic_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry.id, entry.session_id, entry.role, entry.content, entry.topic_id, entry.created_at),
        )
        self._log_operation("add", rows_affected=1)

    def delete_by_session(self, session_id: str) -> bool:
        affected = self._rowcount("DELETE FROM history WHERE session_id = ?", (session_id,))
        self._log_operation("delete_by_session", rows_affected=affected)
        return affected > 0

    def delete_older_than(self, before: str) -> int:
        cursor = self._execute("DELETE FROM history WHERE created_at < ?", (before,))
        affected = cursor.rowcount
        self._log_operation("delete_older_than", rows_affected=affected)
        return affected

    def count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM history")
        result = row["cnt"] if row else 0
        self._log_operation("count")
        return result
