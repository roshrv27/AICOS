"""Knowledge acquisition exception hierarchy.

All exceptions extend :class:`KnowledgeAcquisitionError` so that upstream
code can catch a single base type.
"""


class KnowledgeAcquisitionError(Exception):
    """Base exception for all knowledge acquisition operations."""


class AdapterRegistrationError(KnowledgeAcquisitionError):
    """Raised when adapter registration fails (duplicate, invalid, etc.)."""


class AdapterExecutionError(KnowledgeAcquisitionError):
    """Raised when an adapter fails during discovery, refresh, or verify."""


class NormalizationError(KnowledgeAcquisitionError):
    """Raised when normalization of adapter output fails."""


class DiscoveryError(KnowledgeAcquisitionError):
    """Raised when the discovery orchestration fails."""
