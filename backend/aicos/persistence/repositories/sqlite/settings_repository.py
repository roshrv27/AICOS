"""SQLite-backed settings repository."""

from __future__ import annotations

from ...models import SettingData
from ..base import BaseRepository, utc_now


class SQLiteSettingsRepository(BaseRepository):
    """Persists settings as key/value pairs in the ``settings`` table."""

    def get(self, key: str) -> SettingData | None:
        row = self._fetchone("SELECT * FROM settings WHERE key = ?", (key,))
        return SettingData(**dict(row)) if row else None

    def get_all(self) -> list[SettingData]:
        rows = self._fetchall("SELECT * FROM settings ORDER BY key ASC")
        return [SettingData(**dict(r)) for r in rows]

    def set(self, key: str, value: str) -> None:
        self._execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, utc_now()),
        )

    def delete(self, key: str) -> bool:
        return self._rowcount("DELETE FROM settings WHERE key = ?", (key,)) > 0

    def count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM settings")
        return row["cnt"] if row else 0
