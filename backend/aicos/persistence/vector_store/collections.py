"""Collection lifecycle manager backed by ChromaDB."""

from __future__ import annotations

from ...logging import get_logger
from .exceptions import CollectionError


class CollectionManager:
    """High-level collection CRUD with idempotent helpers.

    Wraps a ChromaDB client and delegates every operation to it.
    """

    def __init__(self, client: object) -> None:
        self._client = client
        self._logger = get_logger("database")

    def create(self, name: str) -> None:
        """Create *name* or raise if it already exists."""
        if self.exists(name):
            raise CollectionError(f"collection '{name}' already exists")
        self._client.create_collection(name=name, embedding_function=None)
        self._logger.debug("collection created", extra={"collection": name})

    def create_if_not_exists(self, name: str) -> None:
        """Idempotent create."""
        try:
            self._client.create_collection(name=name, embedding_function=None)
            self._logger.debug("collection created", extra={"collection": name})
        except Exception as exc:
            if "already exists" in str(exc).lower():
                return
            raise CollectionError(str(exc)) from exc

    def delete(self, name: str) -> None:
        """Delete *name* or raise if it does not exist."""
        if not self.exists(name):
            raise CollectionError(f"collection '{name}' not found")
        self._client.delete_collection(name=name)
        self._logger.debug("collection deleted", extra={"collection": name})

    def exists(self, name: str) -> bool:
        """Return ``True`` when *name* exists."""
        try:
            self._client.get_collection(name=name)
            return True
        except Exception:
            return False

    def get(self, name: str) -> object:
        """Return the raw collection object or raise."""
        try:
            return self._client.get_collection(name=name)
        except Exception as exc:
            raise CollectionError(str(exc)) from exc

    def list(self) -> list[str]:
        """Return every collection name."""
        return [c.name for c in self._client.list_collections()]
