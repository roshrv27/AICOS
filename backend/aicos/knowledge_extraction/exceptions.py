from __future__ import annotations


class ExtractionError(Exception):
    pass


class UnsupportedContentError(ExtractionError):
    pass


class InvalidExtractionError(ExtractionError):
    pass


class ExtractorNotFoundError(ExtractionError):
    pass


class ExtractionValidationError(ExtractionError):
    pass
