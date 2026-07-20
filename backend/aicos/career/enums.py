"""Enumerations for the career domain.

All enums use ``StrEnum`` for consistent serialization.
"""

from __future__ import annotations

from enum import StrEnum


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TechnologyLifecycle(StrEnum):
    EXPERIMENTAL = "experimental"
    EMERGING = "emerging"
    GROWING = "growing"
    RECOMMENDED = "recommended"
    INDUSTRY_STANDARD = "industry_standard"
    LEGACY = "legacy"
    DEPRECATED = "deprecated"


class RecommendationPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationType(StrEnum):
    LEARN = "learn"
    REVIEW = "review"
    UPGRADE = "upgrade"
    REPLACE = "replace"
    REMOVE = "remove"


class LearningStyle(StrEnum):
    READING = "reading"
    VIDEOS = "videos"
    HANDS_ON = "hands_on"
    MIXED = "mixed"


class CareerTrackCategory(StrEnum):
    AI = "ai"
    CLOUD = "cloud"
    DEVOPS = "devops"
    TESTING = "testing"
    DATA = "data"
    SECURITY = "security"
    SOFTWARE = "software"
    MANAGEMENT = "management"
