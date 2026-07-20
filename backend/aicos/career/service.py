"""Career domain service.

``CareerDomainService`` validates domain entities and enforces business
rules without AI, retrieval, or infrastructure dependencies.
"""

from __future__ import annotations

from ..logging import get_logger
from .exceptions import (
    BlueprintValidationError,
    RecommendationValidationError,
    SkillValidationError,
    ValidationError,
)
from .models import CareerProfile, Recommendation, RoleBlueprint, Skill
from .validation import (
    validate_blueprint,
    validate_prerequisite_chains,
    validate_profile,
    validate_recommendations,
    validate_skills,
)


class CareerDomainService:
    """Domain service for career intelligence business rules.

    All methods are pure validation with no side effects, no AI, and no
    external dependencies.
    """

    def __init__(self) -> None:
        self._logger = get_logger("career")

    def validate_profile(self, profile: CareerProfile) -> None:
        try:
            validate_profile(profile)
            self._logger.debug(
                "profile validation passed",
                extra={"user_id": profile.user_id, "skill_count": len(profile.skills)},
            )
        except (ValidationError, SkillValidationError):
            self._logger.warning(
                "profile validation failed",
                extra={"user_id": profile.user_id},
            )
            raise

    def validate_blueprint(self, blueprint: RoleBlueprint) -> None:
        try:
            validate_blueprint(blueprint)
            self._logger.debug(
                "blueprint validation passed",
                extra={"track": blueprint.track, "version": blueprint.version},
            )
        except BlueprintValidationError:
            self._logger.warning(
                "blueprint validation failed",
                extra={"track": blueprint.track},
            )
            raise

    def validate_skill_graph(self, skills: list[Skill]) -> None:
        try:
            validate_skills(skills)
            self._logger.debug(
                "skill graph validation passed",
                extra={"skill_count": len(skills)},
            )
        except SkillValidationError:
            self._logger.warning(
                "skill graph validation failed",
                extra={"skill_count": len(skills)},
            )
            raise

    def validate_prerequisite_chains(self, skills: list[Skill]) -> None:
        try:
            validate_prerequisite_chains(skills)
            self._logger.debug(
                "prerequisite chain validation passed",
                extra={"skill_count": len(skills)},
            )
        except SkillValidationError:
            self._logger.warning(
                "prerequisite chain validation failed",
                extra={"skill_count": len(skills)},
            )
            raise

    def validate_recommendations(
        self,
        recommendations: list[Recommendation],
    ) -> None:
        try:
            validate_recommendations(recommendations)
            self._logger.debug(
                "recommendation validation passed",
                extra={"recommendation_count": len(recommendations)},
            )
        except RecommendationValidationError:
            self._logger.warning(
                "recommendation validation failed",
                extra={"recommendation_count": len(recommendations)},
            )
            raise
