"""Immutable domain models for the career intelligence domain.

All models are frozen dataclasses.  No AI, retrieval, or infrastructure
types appear in this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import (
    CareerTrackCategory,
    Difficulty,
    LearningStyle,
    RecommendationPriority,
    RecommendationType,
    TechnologyLifecycle,
)


# ---------------------------------------------------------------------------
# Career Track
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CareerTrack:
    """A named career pathway with associated metadata."""

    id: str
    name: str
    description: str = ""
    category: CareerTrackCategory = CareerTrackCategory.SOFTWARE
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    estimated_duration: str = ""
    target_roles: list[str] = field(default_factory=list)
    status: str = "active"


# ---------------------------------------------------------------------------
# Career Profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CareerProfile:
    """A user's career profile capturing skills, goals, and preferences."""

    user_id: str
    current_role: str = ""
    years_of_experience: float = 0.0
    education: str = ""
    skills: list[str] = field(default_factory=list)
    skill_levels: dict[str, Difficulty] = field(default_factory=dict)
    interests: list[str] = field(default_factory=list)
    preferred_learning_style: LearningStyle = LearningStyle.MIXED
    weekly_learning_hours: float = 0.0
    career_goals: list[str] = field(default_factory=list)
    target_tracks: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    completed_topics: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Skill:
    """A learnable skill with difficulty and prerequisite metadata."""

    id: str
    name: str
    description: str = ""
    category: str = ""
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    estimated_learning_hours: float = 0.0
    prerequisites: list[str] = field(default_factory=list)
    related_technologies: list[str] = field(default_factory=list)
    status: str = "active"


# ---------------------------------------------------------------------------
# Technology
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Technology:
    """A technology tracked in the ecosystem."""

    id: str
    name: str
    description: str = ""
    category: str = ""
    lifecycle: TechnologyLifecycle = TechnologyLifecycle.EMERGING
    industry_adoption: str = ""
    market_demand: str = ""
    relevant_tracks: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    estimated_learning_hours: float = 0.0


# ---------------------------------------------------------------------------
# Role Blueprint
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleBlueprint:
    """A structured blueprint of skills required for a target role."""

    track: str
    required_skills: list[str] = field(default_factory=list)
    optional_skills: list[str] = field(default_factory=list)
    recommended_order: list[str] = field(default_factory=list)
    minimum_requirements: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    last_updated: str = ""


# ---------------------------------------------------------------------------
# Learning Topic
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningTopic:
    """A specific topic within a skill area."""

    id: str
    title: str
    description: str = ""
    skill: str = ""
    technologies: list[str] = field(default_factory=list)
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    estimated_hours: float = 0.0
    prerequisites: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Learning Resource
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningResource:
    """A curated learning resource (course, article, video, etc.)."""

    id: str
    title: str
    resource_type: str = ""
    provider: str = ""
    language: str = "en"
    quality_score: float = 0.0
    estimated_duration: str = ""
    url: str = ""
    last_verified: str = ""
    status: str = "active"


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Recommendation:
    """A domain-driven recommendation for the user."""

    id: str
    title: str
    description: str = ""
    reason: str = ""
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    recommendation_type: RecommendationType = RecommendationType.LEARN
    relevant_track: str = ""
    estimated_effort: str = ""
    accepted: bool = False


# ---------------------------------------------------------------------------
# Technology Watch Item
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TechnologyWatchItem:
    """A technology being monitored in the watch system."""

    technology: str
    summary: str = ""
    status: str = "monitoring"
    relevant_tracks: list[str] = field(default_factory=list)
    importance: str = ""
    recommended_action: str = ""
    discovered_at: datetime | None = None
