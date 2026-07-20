from __future__ import annotations


class TrustedSourceError(Exception):
    """Base exception for all trusted source operations."""


class DuplicateSourceError(TrustedSourceError):
    """Raised when registering a source with a duplicate ID."""


class InvalidTrustScoreError(TrustedSourceError):
    """Raised when a trust score is outside [0.0, 1.0]."""


class InvalidSourceError(TrustedSourceError):
    """Raised when a source object fails validation."""


class SourceNotFoundError(TrustedSourceError):
    """Raised when looking up a source that does not exist."""
