"""Persistence-layer data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DatabaseInfo:
    """Snapshot of database connection state and configuration."""

    connected: bool
    version: int
    path: str
    wal_enabled: bool


@dataclass(frozen=True)
class MigrationHistoryEntry:
    """Record of one applied migration."""

    version: int
    description: str


# ── Repository data models ────────────────────────────────────────────


@dataclass(frozen=True)
class TopicData:
    """Persistent representation of a topic."""

    id: str
    name: str
    description: str
    icon: str
    category: str
    order: int
    type: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str | None


@dataclass(frozen=True)
class ProgressData:
    """Persistent representation of user progress on a topic."""

    topic_id: str
    status: str
    score: float
    attempts: int
    completed_at: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SettingData:
    """Persistent representation of a single setting key/value pair."""

    key: str
    value: str
    updated_at: str


@dataclass(frozen=True)
class HistoryEntryData:
    """Persistent representation of a single chat history entry."""

    id: str
    session_id: str
    role: str
    content: str
    topic_id: str
    created_at: str
