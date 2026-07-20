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
        return [HistoryEntryData(**dict(r)) for r in rows]

    def get_by_topic(self, topic_id: str) -> list[HistoryEntryData]:
        rows = self._fetchall(
            "SELECT * FROM history WHERE topic_id = ? ORDER BY created_at ASC",
            (topic_id,),
        )
        return [HistoryEntryData(**dict(r)) for r in rows]

    def add(self, entry: HistoryEntryData) -> None:
        self._execute(
            "INSERT INTO history (id, session_id, role, content, topic_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry.id, entry.session_id, entry.role, entry.content, entry.topic_id, entry.created_at),
        )

    def delete_by_session(self, session_id: str) -> bool:
        return self._rowcount("DELETE FROM history WHERE session_id = ?", (session_id,)) > 0

    def delete_older_than(self, before: str) -> int:
        cursor = self._execute("DELETE FROM history WHERE created_at < ?", (before,))
        return cursor.rowcount

    def count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM history")
        return row["cnt"] if row else 0
