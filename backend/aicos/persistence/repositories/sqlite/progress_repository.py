"""SQLite-backed progress repository."""

from __future__ import annotations

from ...models import ProgressData
from ..base import BaseRepository, json_dumps, json_loads


class SQLiteProgressRepository(BaseRepository):
    """Persists user progress in the ``progress`` table."""

    def get_by_topic(self, topic_id: str) -> ProgressData | None:
        row = self._fetchone("SELECT * FROM progress WHERE topic_id = ?", (topic_id,))
        return _row_to_progress(row) if row else None

    def get_all(self) -> list[ProgressData]:
        rows = self._fetchall("SELECT * FROM progress")
        return [_row_to_progress(r) for r in rows]

    def upsert(self, progress: ProgressData) -> None:
        self._execute(
            """INSERT INTO progress (topic_id, status, score, attempts, completed_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(topic_id) DO UPDATE SET
                   status       = excluded.status,
                   score        = excluded.score,
                   attempts     = excluded.attempts,
                   completed_at = excluded.completed_at,
                   metadata     = excluded.metadata""",
            (
                progress.topic_id,
                progress.status,
                progress.score,
                progress.attempts,
                progress.completed_at,
                json_dumps(progress.metadata),
            ),
        )

    def delete_by_topic(self, topic_id: str) -> bool:
        return self._rowcount("DELETE FROM progress WHERE topic_id = ?", (topic_id,)) > 0

    def count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM progress")
        return row["cnt"] if row else 0

    def get_completed_count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM progress WHERE status = 'completed'")
        return row["cnt"] if row else 0


def _row_to_progress(row: object) -> ProgressData:
    raw = dict(row)  # type: ignore[arg-type]
    raw["metadata"] = json_loads(raw.get("metadata", "{}"))
    return ProgressData(**raw)
