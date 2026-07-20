"""Provider-neutral protocols for the career domain.

Application code depends **only** on the protocols defined here.
Concrete implementations are wired via DI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import (
    CareerProfile,
    Recommendation,
    RoleBlueprint,
    Skill,
)


@runtime_checkable
class CareerDomainServiceProtocol(Protocol):
    """Protocol for the career domain service.

    Implementations validate domain entities and enforce business rules
    without AI, retrieval, or infrastructure dependencies.
    """

    def validate_profile(self, profile: CareerProfile) -> None:
        """Validate a :class:`CareerProfile`.

        Raises :class:`ValidationError` or :class:`SkillValidationError`
        when constraints are violated.
        """
        ...

    def validate_blueprint(self, blueprint: RoleBlueprint) -> None:
        """Validate a :class:`RoleBlueprint`.

        Raises :class:`BlueprintValidationError` when constraints are
        violated.
        """
        ...

    def validate_skill_graph(self, skills: list[Skill]) -> None:
        """Validate skill graph consistency.

        Checks for duplicate skill IDs, empty names, and invalid
        learning hours.  Raises :class:`SkillValidationError`.
        """
        ...

    def validate_prerequisite_chains(self, skills: list[Skill]) -> None:
        """Validate that prerequisite chains contain no cycles.

        Each skill's prerequisites must reference existing skills.
        Raises :class:`SkillValidationError` on violations.
        """
        ...

    def validate_recommendations(
        self,
        recommendations: list[Recommendation],
    ) -> None:
        """Validate a list of :class:`Recommendation`.

        Checks for duplicate IDs, empty titles, and valid priorities.
        Raises :class:`RecommendationValidationError`.
        """
        ...
