"""Career domain exception hierarchy.

All exceptions extend :class:`CareerDomainError` so that upstream code
can catch a single base type.  No infrastructure exceptions escape this
layer.
"""


class CareerDomainError(Exception):
    """Base exception for all career domain operations."""


class ValidationError(CareerDomainError):
    """Raised when general domain validation fails."""


class SkillValidationError(CareerDomainError):
    """Raised when skill validation fails (duplicate, invalid hours, etc.)."""


class TechnologyValidationError(CareerDomainError):
    """Raised when technology validation fails."""


class BlueprintValidationError(CareerDomainError):
    """Raised when role blueprint validation fails."""


class RecommendationValidationError(CareerDomainError):
    """Raised when recommendation validation fails."""
