"""SQLite-backed settings repository."""

from __future__ import annotations

from ...models import SettingData
from ..base import BaseRepository, utc_now


class SQLiteSettingsRepository(BaseRepository):
    """Persists settings as key/value pairs in the ``settings`` table."""

    def get(self, key: str) -> SettingData | None:
        row = self._fetchone("SELECT * FROM settings WHERE key = ?", (key,))
        result = SettingData(**dict(row)) if row else None
        self._log_operation("get", rows_affected=1 if result else 0)
        return result

    def get_all(self) -> list[SettingData]:
        rows = self._fetchall("SELECT * FROM settings ORDER BY key ASC")
        result = [SettingData(**dict(r)) for r in rows]
        self._log_operation("get_all", rows_affected=len(result))
        return result

    def set(self, key: str, value: str) -> None:
        self._execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, utc_now()),
        )
        self._log_operation("set", rows_affected=1)

    def delete(self, key: str) -> bool:
        affected = self._rowcount("DELETE FROM settings WHERE key = ?", (key,))
        self._log_operation("delete", rows_affected=affected)
        return affected > 0

    def count(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM settings")
        result = row["cnt"] if row else 0
        self._log_operation("count")
        return result
