from __future__ import annotations

from ..core.di import Container, ServiceLifetime
from ..settings import Settings
from .enums import ContentType, ExtractionMode
from .exceptions import (
    ExtractionError,
    ExtractionValidationError,
    ExtractorNotFoundError,
    InvalidExtractionError,
    UnsupportedContentError,
)
from .extractors import (
    BlogExtractor,
    DocumentationExtractor,
    GitHubExtractor,
    ResearchExtractor,
    YouTubeExtractor,
)
from .models import (
    ExtractedAPI,
    ExtractedCodeSnippet,
    ExtractedConcept,
    ExtractedDependency,
    ExtractedExample,
    ExtractedFramework,
    ExtractedModel,
    ExtractedReference,
    ExtractedRelease,
    ExtractedTechnology,
    ExtractedTool,
    ExtractedVersion,
    ExtractionContext,
    ExtractionRequest,
    ExtractionResult,
    ExtractionStatistics,
)
from .registry import ExtractionRegistry
from .service import KnowledgeExtractionService
from .validation import validate_extraction_result

__all__ = [
    "ContentType", "ExtractionMode",
    "ExtractionError", "ExtractionValidationError", "ExtractorNotFoundError",
    "InvalidExtractionError", "UnsupportedContentError",
    "ExtractedAPI", "ExtractedCodeSnippet", "ExtractedConcept",
    "ExtractedDependency", "ExtractedExample", "ExtractedFramework",
    "ExtractedModel", "ExtractedReference", "ExtractedRelease",
    "ExtractedTechnology", "ExtractedTool", "ExtractedVersion",
    "ExtractionContext", "ExtractionRequest", "ExtractionResult",
    "ExtractionStatistics",
    "ExtractionRegistry",
    "KnowledgeExtractionService",
    "validate_extraction_result",
    "register_knowledge_extraction",
]


def register_knowledge_extraction(container: Container, settings: Settings) -> None:
    extraction_config: dict = getattr(settings, "knowledge_extraction", {})

    _extractor_classes: list[type] = [
        DocumentationExtractor,
        GitHubExtractor,
        YouTubeExtractor,
        ResearchExtractor,
        BlogExtractor,
    ]

    def _create_registry(ctr: Container) -> ExtractionRegistry:
        registry = ExtractionRegistry()
        for cls in _extractor_classes:
            registry.register(cls())
        return registry

    container.register_factory(
        ExtractionRegistry,
        _create_registry,
        lifetime=ServiceLifetime.SINGLETON,
    )

    container.register(
        KnowledgeExtractionService,
        lifetime=ServiceLifetime.SINGLETON,
    )
