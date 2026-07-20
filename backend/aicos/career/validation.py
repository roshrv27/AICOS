"""Domain validation for career entities.

Validators are pure functions with no side effects.  Each raises the
appropriate exception from ``.exceptions``.
"""

from __future__ import annotations

from typing import Any

from .enums import Difficulty, TechnologyLifecycle
from .exceptions import (
    BlueprintValidationError,
    RecommendationValidationError,
    SkillValidationError,
    TechnologyValidationError,
    ValidationError,
)
from .models import (
    CareerProfile,
    Recommendation,
    RoleBlueprint,
    Skill,
    Technology,
)


def validate_profile(profile: CareerProfile) -> None:
    """Validate a career profile."""
    if not profile.user_id:
        raise ValidationError("user_id must not be empty")
    if profile.years_of_experience < 0:
        raise ValidationError("years_of_experience must not be negative")
    if profile.weekly_learning_hours < 0:
        raise ValidationError("weekly_learning_hours must not be negative")
    _check_duplicates(profile.skills, "skills", SkillValidationError)


def validate_blueprint(blueprint: RoleBlueprint) -> None:
    """Validate a role blueprint."""
    if not blueprint.track:
        raise BlueprintValidationError("track must not be empty")
    if not blueprint.version:
        raise BlueprintValidationError("version must not be empty")
    _check_duplicates(blueprint.required_skills, "required_skills", BlueprintValidationError)
    _check_duplicates(blueprint.optional_skills, "optional_skills", BlueprintValidationError)


def validate_skills(skills: list[Skill]) -> None:
    """Validate a list of skills."""
    seen: set[str] = set()
    for skill in skills:
        if not skill.id:
            raise SkillValidationError("skill id must not be empty")
        if not skill.name.strip():
            raise SkillValidationError(f"skill name must not be empty (id={skill.id})")
        if skill.id in seen:
            raise SkillValidationError(f"duplicate skill id: {skill.id}")
        seen.add(skill.id)
        if skill.estimated_learning_hours < 0:
            raise SkillValidationError(
                f"estimated_learning_hours must not be negative (skill={skill.id})"
            )
        if skill.difficulty not in Difficulty.__members__.values():
            raise SkillValidationError(
                f"invalid difficulty for skill {skill.id}: {skill.difficulty}"
            )


def validate_prerequisite_chains(skills: list[Skill]) -> None:
    """Validate that prerequisite chains contain no cycles and reference
    existing skills."""
    skill_map = {s.id for s in skills}

    for skill in skills:
        for prereq_id in skill.prerequisites:
            if prereq_id not in skill_map:
                raise SkillValidationError(
                    f"prerequisite {prereq_id} not found for skill {skill.id}"
                )

    _check_cycles(skills)


def validate_technologies(technologies: list[Technology]) -> None:
    """Validate a list of technologies."""
    seen: set[str] = set()
    for tech in technologies:
        if not tech.id:
            raise TechnologyValidationError("technology id must not be empty")
        if not tech.name.strip():
            raise TechnologyValidationError(f"technology name must not be empty (id={tech.id})")
        if tech.id in seen:
            raise TechnologyValidationError(f"duplicate technology id: {tech.id}")
        seen.add(tech.id)
        if tech.estimated_learning_hours < 0:
            raise TechnologyValidationError(
                f"estimated_learning_hours must not be negative (technology={tech.id})"
            )
        if tech.lifecycle not in TechnologyLifecycle.__members__.values():
            raise TechnologyValidationError(
                f"invalid lifecycle for technology {tech.id}: {tech.lifecycle}"
            )


def validate_recommendations(recommendations: list[Recommendation]) -> None:
    """Validate a list of recommendations."""
    seen: set[str] = set()
    for rec in recommendations:
        if not rec.id:
            raise RecommendationValidationError("recommendation id must not be empty")
        if not rec.title.strip():
            raise RecommendationValidationError(
                f"recommendation title must not be empty (id={rec.id})"
            )
        if rec.id in seen:
            raise RecommendationValidationError(f"duplicate recommendation id: {rec.id}")
        seen.add(rec.id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_duplicates(items: list[str], field: str, exc_type: type[Exception]) -> None:
    seen: set[str] = set()
    for item in items:
        if item in seen:
            raise exc_type(f"duplicate {field}: {item}")
        seen.add(item)


def _check_cycles(skills: list[Skill]) -> None:
    """Detect cycles in prerequisite chains using DFS."""
    skill_map = {s.id: s for s in skills}

    def has_cycle(node: str, visited: set[str], path: set[str]) -> bool:
        if node in path:
            return True
        if node in visited:
            return False
        visited.add(node)
        path.add(node)
        if node in skill_map:
            for prereq in skill_map[node].prerequisites:
                if has_cycle(prereq, visited, path):
                    return True
        path.remove(node)
        return False

    visited: set[str] = set()
    for skill in skills:
        if has_cycle(skill.id, visited, set()):
            raise SkillValidationError(f"circular prerequisite detected involving skill: {skill.id}")
