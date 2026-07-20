"""Knowledge intelligence domain exception hierarchy.

All exceptions extend :class:`KnowledgeDomainError` so that upstream code
can catch a single base type.  No infrastructure exceptions escape this
layer.
"""


class KnowledgeDomainError(Exception):
    """Base exception for all knowledge intelligence domain operations."""


class SourceValidationError(KnowledgeDomainError):
    """Raised when knowledge source validation fails."""


class SignalValidationError(KnowledgeDomainError):
    """Raised when technology signal validation fails."""


class EvidenceValidationError(KnowledgeDomainError):
    """Raised when evidence validation fails."""


class TrendValidationError(KnowledgeDomainError):
    """Raised when trend snapshot validation fails."""


class ResourceValidationError(KnowledgeDomainError):
    """Raised when knowledge resource validation fails."""


class VersionValidationError(KnowledgeDomainError):
    """Raised when knowledge version validation fails."""


class JobValidationError(KnowledgeDomainError):
    """Raised when discovery job validation fails."""
