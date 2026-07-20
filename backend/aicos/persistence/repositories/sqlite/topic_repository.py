"""SQLite-backed topic repository."""

from __future__ import annotations

from ...models import TopicData
from ..base import BaseRepository, json_dumps, json_loads


class SQLiteTopicRepository(BaseRepository):
    """Persists topics in the ``topics`` table."""

    def get_all(self) -> list[TopicData]:
        rows = self._fetchall("SELECT * FROM topics ORDER BY `order` ASC")
        return [_row_to_topic(r) for r in rows]

    def get_by_id(self, topic_id: str) -> TopicData | None:
        row = self._fetchone("SELECT * FROM topics WHERE id = ?", (topic_id,))
        return _row_to_topic(row) if row else None

    def get_by_category(self, category: str) -> list[TopicData]:
        rows = self._fetchall("SELECT * FROM topics WHERE category = ? ORDER BY `order` ASC", (category,))
        return [_row_to_topic(r) for r in rows]

    def upsert(self, topic: TopicData) -> None:
        self._execute(
            """INSERT INTO topics (id, name, description, icon, category, "order", type, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name        = excluded.name,
                   description = excluded.description,
                   icon        = excluded.icon,
                   category    = excluded.category,
                   "order"     = excluded."order",
                   type        = excluded.type,
                   metadata    = excluded.metadata,
                   updated_at  = excluded.updated_at""",
            (
                topic.id,
                topic.name,
                topic.description,
                topic.icon,
                topic.category,
                topic.order,
                topic.type,
                json_dumps(topic.metadata),
                topic.created_at,
                topic.updated_at,
            ),
        )

    def delete(self, topic_id: str) -> bool:
        return self._rowcount("DELETE FROM topics WHERE id = ?", (topic_id,)) > 0

    def count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM topics")
        return row["cnt"] if row else 0


def _row_to_topic(row: object) -> TopicData:
    raw = dict(row)  # type: ignore[arg-type]
    raw["metadata"] = json_loads(raw.get("metadata", "{}"))
    return TopicData(**raw)
