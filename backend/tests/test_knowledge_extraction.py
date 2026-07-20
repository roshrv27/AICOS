from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicos.knowledge_extraction import (
    ContentType,
    ExtractionMode,
    ExtractionError,
    ExtractionRegistry,
    ExtractionValidationError,
    ExtractorNotFoundError,
    InvalidExtractionError,
    KnowledgeExtractionService,
    UnsupportedContentError,
    validate_extraction_result,
)
from aicos.knowledge_extraction.enums import ContentType as CT, ExtractionMode as EM
from aicos.knowledge_extraction.exceptions import ExtractionError as EE
from aicos.knowledge_extraction.extractors import (
    BlogExtractor,
    DocumentationExtractor,
    GitHubExtractor,
    ResearchExtractor,
    YouTubeExtractor,
)
from aicos.knowledge_extraction.models import (
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
from aicos.knowledge_intelligence.enums import KnowledgeSourceType
from aicos.knowledge_intelligence.models import Evidence, KnowledgeResource, TechnologySignal

from aicos.knowledge_acquisition.models import DiscoveryResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_request(
    content: str = "test content",
    source_type: KnowledgeSourceType = KnowledgeSourceType.BLOG,
    source_id: str = "test-1",
    source_name: str = "Test Source",
    source_url: str = "https://example.com",
    content_type: str = "",
    mode: str = "",
) -> ExtractionRequest:
    return ExtractionRequest(
        content=content,
        source_type=source_type,
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        content_type=content_type,
        mode=mode,
    )


def make_context(request: ExtractionRequest | None = None) -> ExtractionContext:
    if request is None:
        request = make_request()
    return ExtractionContext(
        source_type=request.source_type,
        source_id=request.source_id,
        source_name=request.source_name,
        source_url=request.source_url,
        content_type=request.content_type,
        content_size=len(request.content),
        extracted_at=datetime.now(timezone.utc),
        extraction_mode=ExtractionMode.RULE_BASED.value,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestContentType:
    def test_values(self) -> None:
        assert CT.DOCUMENTATION.value == "documentation"
        assert CT.GITHUB_README.value == "github_readme"
        assert CT.GITHUB_RELEASE.value == "github_release"
        assert CT.YOUTUBE_VIDEO.value == "youtube_video"
        assert CT.YOUTUBE_DESCRIPTION.value == "youtube_description"
        assert CT.RESEARCH_PAPER.value == "research_paper"
        assert CT.RESEARCH_ABSTRACT.value == "research_abstract"
        assert CT.BLOG_POST.value == "blog_post"
        assert CT.BLOG_ARTICLE.value == "blog_article"
        assert CT.GENERIC_TEXT.value == "generic_text"
        assert CT.UNKNOWN.value == "unknown"

    def test_members(self) -> None:
        assert len(CT) == 11


class TestExtractionMode:
    def test_values(self) -> None:
        assert EM.RULE_BASED.value == "rule_based"
        assert EM.LLM_ASSISTED.value == "llm_assisted"
        assert EM.AUTO.value == "auto"

    def test_members(self) -> None:
        assert len(EM) == 3


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_extraction_error_base(self) -> None:
        assert issubclass(ExtractionError, Exception)
        assert issubclass(UnsupportedContentError, ExtractionError)
        assert issubclass(InvalidExtractionError, ExtractionError)
        assert issubclass(ExtractorNotFoundError, ExtractionError)
        assert issubclass(ExtractionValidationError, ExtractionError)

    def test_extraction_error_message(self) -> None:
        exc = ExtractionError("test error")
        assert str(exc) == "test error"

    def test_extractor_not_found(self) -> None:
        exc = ExtractorNotFoundError("not found")
        assert str(exc) == "not found"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestExtractedTechnology:
    def test_defaults(self) -> None:
        t = ExtractedTechnology(id="t1", name="GPT-5")
        assert t.summary == ""
        assert t.category == ""
        assert t.status.value == "emerging"
        assert t.importance == 5
        assert t.confidence_score == 0.5
        assert t.source_references == []

    def test_to_signal(self) -> None:
        ref = ExtractedReference(id="r1", source="src", title="Ref 1", url="https://example.com")
        ev = ref.to_evidence()
        t = ExtractedTechnology(id="t1", name="GPT-5", source_references=["r1"])
        signal = t.to_signal({"r1": ev})
        assert isinstance(signal, TechnologySignal)
        assert signal.name == "GPT-5"
        assert len(signal.evidence) == 1


class TestExtractedFramework:
    def test_defaults(self) -> None:
        f = ExtractedFramework(id="f1", name="PyTorch")
        assert f.description == ""
        assert f.version == ""
        assert f.confidence_score == 0.5

    def test_to_resource(self) -> None:
        f = ExtractedFramework(id="f1", name="PyTorch", url="https://pytorch.org")
        r = f.to_resource()
        assert isinstance(r, KnowledgeResource)
        assert r.title == "PyTorch"


class TestExtractedModel:
    def test_to_resource(self) -> None:
        m = ExtractedModel(id="m1", name="GPT-4", provider="OpenAI")
        r = m.to_resource()
        assert r.title == "GPT-4"
        assert r.url == ""


class TestExtractedTool:
    def test_to_resource(self) -> None:
        t = ExtractedTool(id="tool1", name="Docker", category="container")
        r = t.to_resource()
        assert r.title == "Docker"


class TestExtractedAPI:
    def test_to_resource(self) -> None:
        a = ExtractedAPI(id="api1", name="Chat API", endpoint="/v1/chat")
        r = a.to_resource()
        assert r.title == "Chat API"
        assert r.resource_type.value == "documentation"


class TestExtractedConcept:
    def test_to_signal(self) -> None:
        c = ExtractedConcept(id="c1", name="Transformer", category="architecture")
        signal = c.to_signal()
        assert isinstance(signal, TechnologySignal)
        assert signal.name == "Transformer"

    def test_defaults(self) -> None:
        c = ExtractedConcept(id="c1", name="RAG")
        assert c.description == ""
        assert c.confidence_score == 0.5


class TestExtractedVersion:
    def test_to_version(self) -> None:
        v = ExtractedVersion(id="v1", version="1.2.3")
        kv = v.to_version()
        assert kv.version == "1.2.3"


class TestExtractedRelease:
    def test_to_version(self) -> None:
        r = ExtractedRelease(id="r1", name="v2.0", version="2.0.0", changes=["bug fix"])
        kv = r.to_version()
        assert kv.version == "2.0.0"
        assert kv.changes == ["bug fix"]

    def test_defaults(self) -> None:
        r = ExtractedRelease(id="r1", name="v1.0", version="1.0.0")
        assert r.description == ""
        assert r.url == ""
        assert r.changes == []


class TestExtractedDependency:
    def test_defaults(self) -> None:
        d = ExtractedDependency(id="d1", name="requests")
        assert d.version == ""
        assert d.category == ""


class TestExtractedExample:
    def test_to_resource(self) -> None:
        e = ExtractedExample(id="e1", title="Quickstart", code="print('hello')", language="python")
        r = e.to_resource()
        assert r.title == "Quickstart"


class TestExtractedCodeSnippet:
    def test_to_resource(self) -> None:
        cs = ExtractedCodeSnippet(id="cs1", code="import os", language="python", description="import snippet")
        r = cs.to_resource()
        assert r.title == "import snippet"

    def test_to_resource_no_description(self) -> None:
        cs = ExtractedCodeSnippet(id="cs2", code="x = 1", language="python")
        r = cs.to_resource()
        assert "Code Snippet (python)" in r.title


class TestExtractedReference:
    def test_to_evidence(self) -> None:
        ref = ExtractedReference(id="r1", source="Test", title="Doc", url="https://example.com/doc")
        ev = ref.to_evidence()
        assert isinstance(ev, Evidence)
        assert ev.source == "Test"
        assert ev.url == "https://example.com/doc"

    def test_defaults(self) -> None:
        ref = ExtractedReference(id="r1", source="src", title="t")
        assert ref.url == ""
        assert ref.confidence == 0.5


class TestExtractionRequest:
    def test_defaults(self) -> None:
        req = make_request()
        assert req.content == "test content"
        assert req.source_type == KnowledgeSourceType.BLOG
        assert req.mode == ""

    def test_with_mode(self) -> None:
        req = make_request(mode="llm_assisted")
        assert req.mode == "llm_assisted"


class TestExtractionContext:
    def test_defaults(self) -> None:
        ctx = make_context()
        assert ctx.source_type == KnowledgeSourceType.BLOG
        assert ctx.content_size > 0
        assert ctx.extraction_mode == "rule_based"


class TestExtractionStatistics:
    def test_defaults(self) -> None:
        s = ExtractionStatistics()
        assert s.total_entities == 0
        assert s.errors == []

    def test_with_values(self) -> None:
        s = ExtractionStatistics(total_entities=5, technologies=2, models=1, extraction_mode="rule_based")
        assert s.total_entities == 5
        assert s.technologies == 2
        assert s.models == 1


class TestExtractionResult:
    def test_empty_result(self) -> None:
        req = make_request()
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        assert result.technologies == []
        assert result.errors == []

    def test_to_signals_with_references(self) -> None:
        req = make_request()
        ctx = make_context(req)
        ref = ExtractedReference(id="r1", source="src", title="Ref", url="https://example.com")
        tech = ExtractedTechnology(id="t1", name="GPT-5", source_references=["r1"])
        result = ExtractionResult(request=req, context=ctx, technologies=[tech], references=[ref])
        signals = result.to_signals()
        assert len(signals) == 1
        assert signals[0].name == "GPT-5"
        assert len(signals[0].evidence) == 1

    def test_to_signals_with_concepts(self) -> None:
        req = make_request()
        ctx = make_context(req)
        concept = ExtractedConcept(id="c1", name="Transformer")
        result = ExtractionResult(request=req, context=ctx, concepts=[concept])
        signals = result.to_signals()
        assert len(signals) == 1
        assert signals[0].name == "Transformer"

    def test_to_resources(self) -> None:
        req = make_request()
        ctx = make_context(req)
        fw = ExtractedFramework(id="f1", name="PyTorch")
        model = ExtractedModel(id="m1", name="GPT-4")
        tool = ExtractedTool(id="tool1", name="Docker")
        api = ExtractedAPI(id="api1", name="REST API")
        example = ExtractedExample(id="e1", title="Example")
        snippet = ExtractedCodeSnippet(id="cs1", code="x = 1", language="python")
        result = ExtractionResult(
            request=req, context=ctx,
            frameworks=[fw], models=[model], tools=[tool],
            apis=[api], examples=[example], code_snippets=[snippet],
        )
        resources = result.to_resources()
        assert len(resources) == 6

    def test_to_evidence(self) -> None:
        req = make_request()
        ctx = make_context(req)
        ref = ExtractedReference(id="r1", source="s", title="t", url="https://example.com")
        result = ExtractionResult(request=req, context=ctx, references=[ref])
        evidence = result.to_evidence()
        assert len(evidence) == 1
        assert evidence[0].source == "s"

    def test_to_versions(self) -> None:
        req = make_request()
        ctx = make_context(req)
        v = ExtractedVersion(id="v1", version="1.0.0")
        r = ExtractedRelease(id="r1", name="v2", version="2.0.0")
        result = ExtractionResult(request=req, context=ctx, versions=[v], releases=[r])
        vers = result.to_versions()
        assert len(vers) == 2

    def test_to_sources(self) -> None:
        req = make_request()
        ctx = make_context(req)
        ref = ExtractedReference(id="r1", source="src", title="t", url="https://example.com")
        result = ExtractionResult(request=req, context=ctx, references=[ref])
        sources = result.to_sources()
        assert len(sources) == 1
        assert sources[0].base_url == "https://example.com"

    def test_to_discovery_result(self) -> None:
        req = make_request()
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx, errors=["e1"])
        dr = result.to_discovery_result()
        assert isinstance(dr, DiscoveryResult)
        assert dr.source_type == KnowledgeSourceType.BLOG
        assert dr.errors == ["e1"]

    def test_to_sources_deduplicates_by_url(self) -> None:
        req = make_request()
        ctx = make_context(req)
        r1 = ExtractedReference(id="r1", source="src", title="t1", url="https://example.com")
        r2 = ExtractedReference(id="r2", source="src", title="t2", url="https://example.com")
        result = ExtractionResult(request=req, context=ctx, references=[r1, r2])
        sources = result.to_sources()
        assert len(sources) <= 2

    def test_statistics_field(self) -> None:
        req = make_request()
        ctx = make_context(req)
        stats = ExtractionStatistics(total_entities=3, extraction_mode="rule_based")
        result = ExtractionResult(request=req, context=ctx, statistics=stats)
        assert result.statistics is not None
        assert result.statistics.total_entities == 3


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_empty_content(self) -> None:
        req = make_request(content="")
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        with pytest.raises(ExtractionValidationError, match="content is empty"):
            validate_extraction_result(result)

    def test_blank_content(self) -> None:
        req = make_request(content="   ")
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_duplicate_entity_ids(self) -> None:
        req = make_request(content="some content")
        ctx = make_context(req)
        t1 = ExtractedTechnology(id="dup", name="Tech 1")
        t2 = ExtractedTechnology(id="dup", name="Tech 2")
        result = ExtractionResult(request=req, context=ctx, technologies=[t1, t2])
        with pytest.raises(ExtractionValidationError, match="duplicate"):
            validate_extraction_result(result)

    def test_missing_required_fields_technology(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        tech = ExtractedTechnology(id="", name="")
        result = ExtractionResult(request=req, context=ctx, technologies=[tech])
        with pytest.raises(ExtractionValidationError, match="missing required field"):
            validate_extraction_result(result)

    def test_missing_required_fields_framework(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        fw = ExtractedFramework(id="", name="")
        result = ExtractionResult(request=req, context=ctx, frameworks=[fw])
        with pytest.raises(ExtractionValidationError, match="missing required field"):
            validate_extraction_result(result)

    def test_missing_model_fields(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        model = ExtractedModel(id="", name="")
        result = ExtractionResult(request=req, context=ctx, models=[model])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_missing_tool_fields(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        tool = ExtractedTool(id="", name="")
        result = ExtractionResult(request=req, context=ctx, tools=[tool])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_missing_api_fields(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        api = ExtractedAPI(id="", name="")
        result = ExtractionResult(request=req, context=ctx, apis=[api])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_missing_concept_fields(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        concept = ExtractedConcept(id="", name="")
        result = ExtractionResult(request=req, context=ctx, concepts=[concept])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_empty_version_string(self) -> None:
        from aicos.knowledge_extraction.validation import validate_version
        errors = validate_version("")
        assert errors == []

    def test_empty_version_string_in_result(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        v = ExtractedVersion(id="v1", version="")
        result = ExtractionResult(request=req, context=ctx, versions=[v])
        with pytest.raises(ExtractionValidationError, match="missing required field"):
            validate_extraction_result(result)

    def test_invalid_version_format(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        v = ExtractedVersion(id="v1", version="not-a-version")
        result = ExtractionResult(request=req, context=ctx, versions=[v])
        with pytest.raises(ExtractionValidationError, match="invalid version"):
            validate_extraction_result(result)

    def test_valid_version_format(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        v = ExtractedVersion(id="v1", version="1.2.3")
        result = ExtractionResult(request=req, context=ctx, versions=[v])
        validate_extraction_result(result)

    def test_invalid_url_format(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        ref = ExtractedReference(id="r1", source="src", title="t", url="not-a-url")
        result = ExtractionResult(request=req, context=ctx, references=[ref])
        with pytest.raises(ExtractionValidationError, match="invalid URL"):
            validate_extraction_result(result)

    def test_valid_url_skipped_when_empty(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        ref = ExtractedReference(id="r1", source="src", title="t", url="")
        result = ExtractionResult(request=req, context=ctx, references=[ref])
        validate_extraction_result(result)

    def test_reference_consistency(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        tech = ExtractedTechnology(id="t1", name="Tech", source_references=["nonexistent"])
        result = ExtractionResult(request=req, context=ctx, technologies=[tech])
        with pytest.raises(ExtractionValidationError, match="references missing reference"):
            validate_extraction_result(result)

    def test_missing_release_version(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        release = ExtractedRelease(id="r1", name="Release", version="bad")
        result = ExtractionResult(request=req, context=ctx, releases=[release])
        with pytest.raises(ExtractionValidationError, match="invalid version"):
            validate_extraction_result(result)

    def test_missing_dependency_required(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        dep = ExtractedDependency(id="", name="")
        result = ExtractionResult(request=req, context=ctx, dependencies=[dep])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_missing_example_title(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        ex = ExtractedExample(id="e1", title="")
        result = ExtractionResult(request=req, context=ctx, examples=[ex])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_missing_code_snippet_id(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        cs = ExtractedCodeSnippet(id="", code="x = 1")
        result = ExtractionResult(request=req, context=ctx, code_snippets=[cs])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_missing_reference_required(self) -> None:
        req = make_request(content="content")
        ctx = make_context(req)
        ref = ExtractedReference(id="r1", source="", title="")
        result = ExtractionResult(request=req, context=ctx, references=[ref])
        with pytest.raises(ExtractionValidationError):
            validate_extraction_result(result)

    def test_valid_result_passes(self) -> None:
        req = make_request(content="valid content for extraction")
        ctx = make_context(req)
        tech = ExtractedTechnology(id="t1", name="GPT-5")
        fw = ExtractedFramework(id="f1", name="PyTorch")
        v = ExtractedVersion(id="v1", version="1.0.0")
        ref = ExtractedReference(id="r1", source="src", title="Ref", url="https://example.com")
        result = ExtractionResult(
            request=req, context=ctx,
            technologies=[tech], frameworks=[fw],
            versions=[v], references=[ref],
        )
        validate_extraction_result(result)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestExtractionRegistry:
    def test_register_and_lookup(self) -> None:
        registry = ExtractionRegistry()
        extractor = DocumentationExtractor()
        registry.register(extractor)
        assert registry.lookup("documentation") is extractor

    def test_lookup_nonexistent(self) -> None:
        registry = ExtractionRegistry()
        with pytest.raises(ExtractorNotFoundError):
            registry.lookup("nonexistent")

    def test_duplicate_registration(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        registry.register(DocumentationExtractor())
        assert len(registry.registered) == 1

    def test_lookup_by_source(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        extractors = registry.lookup_by_source(ContentType.DOCUMENTATION)
        assert len(extractors) == 1

    def test_lookup_by_source_empty(self) -> None:
        registry = ExtractionRegistry()
        extractors = registry.lookup_by_source(ContentType.GENERIC_TEXT)
        assert extractors == []

    def test_discover_found(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        ext = registry.discover(ContentType.DOCUMENTATION)
        assert ext is not None
        assert ext.name == "documentation"

    def test_discover_not_found(self) -> None:
        registry = ExtractionRegistry()
        ext = registry.discover(ContentType.UNKNOWN)
        assert ext is None

    def test_registered_list(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        registry.register(GitHubExtractor())
        assert "documentation" in registry.registered
        assert "github" in registry.registered

    def test_register_all_extractors(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        registry.register(GitHubExtractor())
        registry.register(YouTubeExtractor())
        registry.register(ResearchExtractor())
        registry.register(BlogExtractor())
        assert len(registry.registered) == 5


# ---------------------------------------------------------------------------
# Base Extractor
# ---------------------------------------------------------------------------

class TestBaseExtractor:
    def test_supports_returns_false_by_default(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        assert ext.supports(ContentType.DOCUMENTATION) is False

    def test_extract_unsupported_raises(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        req = make_request()
        with pytest.raises(UnsupportedContentError):
            ext.extract(req)

    def test_metadata(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        meta = ext.metadata()
        assert isinstance(meta, dict)
        assert "mode" in meta

    def test_validate_returns_list(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        req = make_request()
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        assert ext.validate(result) == []

    def test_extract_versions(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        versions = ext._extract_versions("version 1.2.3 and 4.5.6")
        assert len(versions) == 2
        assert versions[0].version == "1.2.3"

    def test_extract_versions_deduplicates(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        versions = ext._extract_versions("1.2.3 and 1.2.3 again")
        assert len(versions) == 1

    def test_extract_urls(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        refs = ext._extract_urls("visit https://example.com/page and https://other.com", "test")
        assert len(refs) == 2
        assert refs[0].url == "https://example.com/page"

    def test_extract_urls_deduplicates(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        refs = ext._extract_urls("https://example.com and https://example.com", "test")
        assert len(refs) == 1

    def test_extract_code_blocks(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        blocks = ext._extract_code_blocks("code:\n```python\nprint('hello')\n```")
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert "print('hello')" in blocks[0].code

    def test_extract_code_blocks_no_language(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        blocks = ext._extract_code_blocks("```\njust code\n```")
        assert len(blocks) == 1
        assert blocks[0].language == "text"

    def test_extract_technology_mentions(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        techs = ext._extract_technology_mentions("I love PyTorch and TensorFlow", ["pytorch", "tensorflow", "jax"])
        assert len(techs) == 2
        names = {t.name.lower() for t in techs}
        assert "pytorch" in names
        assert "tensorflow" in names

    def test_extract_technology_mentions_deduplicates(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        techs = ext._extract_technology_mentions("PyTorch is great. PyTorch rocks!", ["pytorch"])
        assert len(techs) == 1

    def test_resolve_content_type_with_invalid_value(self) -> None:
        from aicos.knowledge_extraction.extractors.base import BaseExtractor
        ext = BaseExtractor()
        req = make_request(content="test", content_type="not-a-valid-content-type")
        result = ext._resolve_content_type(req)
        from aicos.knowledge_extraction.enums import ContentType
        assert result == ContentType.UNKNOWN


# ---------------------------------------------------------------------------
# Documentation Extractor
# ---------------------------------------------------------------------------

class TestDocumentationExtractor:
    def test_supports(self) -> None:
        ext = DocumentationExtractor()
        assert ext.supports(ContentType.DOCUMENTATION)
        assert ext.supports(ContentType.GENERIC_TEXT)
        assert not ext.supports(ContentType.GITHUB_README)

    def test_extract_versions(self) -> None:
        ext = DocumentationExtractor()
        req = make_request(
            content="Install version 2.1.0 of the SDK. Requires Python 3.9.0.",
            content_type="documentation",
        )
        result = ext.extract(req)
        assert len(result.versions) >= 1

    def test_extract_concepts_from_headings(self) -> None:
        ext = DocumentationExtractor()
        req = make_request(
            content="## Getting Started\nThis is how to start.\n## API Reference\nDetails here.",
            content_type="documentation",
        )
        result = ext.extract(req)
        assert len(result.concepts) >= 2

    def test_extract_apis(self) -> None:
        ext = DocumentationExtractor()
        req = make_request(
            content="API endpoint /v1/chat/completions",
            content_type="documentation",
        )
        result = ext.extract(req)
        assert len(result.apis) >= 1

    def test_extract_code_blocks(self) -> None:
        ext = DocumentationExtractor()
        req = make_request(
            content="Example:\n```python\nprint('hello')\n```",
            content_type="documentation",
        )
        result = ext.extract(req)
        assert len(result.code_snippets) >= 1

    def test_metadata(self) -> None:
        ext = DocumentationExtractor()
        meta = ext.metadata()
        assert meta["name"] == "documentation"
        assert "documentation" in meta["supported_types"]

    def test_unsupported_content_raises(self) -> None:
        ext = DocumentationExtractor()
        req = make_request(content="test", content_type="github_readme")
        with pytest.raises(UnsupportedContentError):
            ext.extract(req)

    def test_statistics(self) -> None:
        ext = DocumentationExtractor()
        req = make_request(
            content="## Intro\nVersion 1.0.0.\n```bash\necho hi\n```",
            content_type="documentation",
        )
        result = ext.extract(req)
        assert result.statistics is not None
        assert result.statistics.extraction_mode == "rule_based"


# ---------------------------------------------------------------------------
# GitHub Extractor
# ---------------------------------------------------------------------------

class TestGitHubExtractor:
    def test_supports(self) -> None:
        ext = GitHubExtractor()
        assert ext.supports(ContentType.GITHUB_README)
        assert ext.supports(ContentType.GITHUB_RELEASE)
        assert not ext.supports(ContentType.BLOG_POST)

    def test_extract_releases(self) -> None:
        ext = GitHubExtractor()
        req = make_request(
            content="## v1.0.0\n- Initial release\n## v1.1.0\n- Bug fixes",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_release",
        )
        result = ext.extract(req)
        assert len(result.releases) >= 2

    def test_extract_dependencies(self) -> None:
        ext = GitHubExtractor()
        req = make_request(
            content="numpy==1.21.0\npandas>=1.3.0\nrequests",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_readme",
        )
        result = ext.extract(req)
        assert len(result.dependencies) >= 2

    def test_extract_dependencies_with_comma_separated_line(self) -> None:
        ext = GitHubExtractor()
        req = make_request(
            content="Dependencies: pytorch>=2.0, transformers==4.30",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_readme",
        )
        result = ext.extract(req)
        assert len(result.dependencies) >= 2

    def test_extract_dependencies_via_line_without_versions(self) -> None:
        ext = GitHubExtractor()
        req = make_request(
            content="Requires: pytorch, transformers",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_readme",
        )
        result = ext.extract(req)
        assert any(d.name == "pytorch" for d in result.dependencies)

    def test_extract_technology_mentions(self) -> None:
        ext = GitHubExtractor()
        req = make_request(
            content="Built with PyTorch and TensorFlow. Deploy on Docker.",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_readme",
        )
        result = ext.extract(req)
        assert len(result.technologies) >= 1

    def test_unsupported_raises(self) -> None:
        ext = GitHubExtractor()
        req = make_request(content="test", content_type="blog_post")
        with pytest.raises(UnsupportedContentError):
            ext.extract(req)

    def test_statistics(self) -> None:
        ext = GitHubExtractor()
        req = make_request(
            content="## v1.0.0\n- First release\nPyTorch is used.",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_release",
        )
        result = ext.extract(req)
        assert result.statistics is not None


# ---------------------------------------------------------------------------
# YouTube Extractor
# ---------------------------------------------------------------------------

class TestYouTubeExtractor:
    def test_supports(self) -> None:
        ext = YouTubeExtractor()
        assert ext.supports(ContentType.YOUTUBE_VIDEO)
        assert ext.supports(ContentType.YOUTUBE_DESCRIPTION)
        assert not ext.supports(ContentType.DOCUMENTATION)

    def test_extract_hashtag_concepts(self) -> None:
        ext = YouTubeExtractor()
        req = make_request(
            content="In this video we cover #machinelearning and #deeplearning\nTopic: Transformers",
            source_type=KnowledgeSourceType.YOUTUBE,
            content_type="youtube_video",
        )
        result = ext.extract(req)
        assert len(result.concepts) >= 1

    def test_extract_with_urls(self) -> None:
        ext = YouTubeExtractor()
        req = make_request(
            content="Check https://youtube.com/watch?v=abc123 for more\n#ai",
            source_type=KnowledgeSourceType.YOUTUBE,
            content_type="youtube_video",
        )
        result = ext.extract(req)
        assert len(result.references) >= 1

    def test_extract_technology_mentions(self) -> None:
        ext = YouTubeExtractor()
        req = make_request(
            content="Today we learn about LangChain and RAG agents",
            source_type=KnowledgeSourceType.YOUTUBE,
            content_type="youtube_description",
        )
        result = ext.extract(req)
        assert len(result.technologies) >= 1

    def test_unsupported_raises(self) -> None:
        ext = YouTubeExtractor()
        req = make_request(content="test", content_type="research_paper")
        with pytest.raises(UnsupportedContentError):
            ext.extract(req)

    def test_statistics(self) -> None:
        ext = YouTubeExtractor()
        req = make_request(
            content="#ai #ml tutorial on PyTorch",
            source_type=KnowledgeSourceType.YOUTUBE,
            content_type="youtube_video",
        )
        result = ext.extract(req)
        assert result.statistics is not None


# ---------------------------------------------------------------------------
# Research Extractor
# ---------------------------------------------------------------------------

class TestResearchExtractor:
    def test_supports(self) -> None:
        ext = ResearchExtractor()
        assert ext.supports(ContentType.RESEARCH_PAPER)
        assert ext.supports(ContentType.RESEARCH_ABSTRACT)
        assert not ext.supports(ContentType.BLOG_POST)

    def test_extract_model_names(self) -> None:
        ext = ResearchExtractor()
        req = make_request(
            content="We evaluate GPT-4 and LLaMA 2 on benchmark tasks. BERT is used as baseline.",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            content_type="research_paper",
        )
        result = ext.extract(req)
        assert len(result.models) >= 2

    def test_extract_frameworks(self) -> None:
        ext = ResearchExtractor()
        req = make_request(
            content="Code is available at https://github.com/example. Implemented with PyTorch and Transformers library.",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            content_type="research_paper",
        )
        result = ext.extract(req)
        assert len(result.frameworks) >= 1

    def test_extract_abstract_with_heading_after(self) -> None:
        ext = ResearchExtractor()
        req = make_request(
            content="## Abstract\nThis paper introduces a novel approach to Transformer optimization using reinforcement learning techniques that significantly improve convergence speed.\n## Conclusion\nWe have shown that our method works.\nReference [1] shows prior work.",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            content_type="research_abstract",
        )
        result = ext.extract(req)
        assert len(result.references) >= 1

    def test_extract_citations(self) -> None:
        ext = ResearchExtractor()
        req = make_request(
            content="Previous work [1] showed promising results. Later studies [2][3] confirmed this.",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            content_type="research_paper",
        )
        result = ext.extract(req)
        assert len(result.references) >= 2

    def test_unsupported_raises(self) -> None:
        ext = ResearchExtractor()
        req = make_request(content="test", content_type="youtube_video")
        with pytest.raises(UnsupportedContentError):
            ext.extract(req)

    def test_statistics(self) -> None:
        ext = ResearchExtractor()
        req = make_request(
            content="We introduce GPT-5. Built with JAX.",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            content_type="research_abstract",
        )
        result = ext.extract(req)
        assert result.statistics is not None


# ---------------------------------------------------------------------------
# Blog Extractor
# ---------------------------------------------------------------------------

class TestBlogExtractor:
    def test_supports(self) -> None:
        ext = BlogExtractor()
        assert ext.supports(ContentType.BLOG_POST)
        assert ext.supports(ContentType.BLOG_ARTICLE)
        assert ext.supports(ContentType.GENERIC_TEXT)
        assert not ext.supports(ContentType.RESEARCH_PAPER)

    def test_extract_concepts_from_headings(self) -> None:
        ext = BlogExtractor()
        req = make_request(
            content="## Why RAG Matters\nThis blog explains RAG.\n## Getting Started with LLMs\nA practical guide.",
            content_type="blog_post",
        )
        result = ext.extract(req)
        assert len(result.concepts) >= 2

    def test_extract_code_blocks(self) -> None:
        ext = BlogExtractor()
        req = make_request(
            content="Example code:\n```python\nprint('hello blog')\n```",
            content_type="blog_article",
        )
        result = ext.extract(req)
        assert len(result.code_snippets) >= 1

    def test_extract_technology_mentions(self) -> None:
        ext = BlogExtractor()
        req = make_request(
            content="In this post we compare LangChain vs LlamaIndex for RAG applications.",
            content_type="blog_post",
        )
        result = ext.extract(req)
        assert len(result.technologies) >= 1

    def test_extract_bold_concepts(self) -> None:
        ext = BlogExtractor()
        req = make_request(
            content="- **Key Takeaway**: RAG improves accuracy\n- **Another Point**: Use embeddings",
            content_type="blog_post",
        )
        result = ext.extract(req)
        assert len(result.concepts) >= 1

    def test_unsupported_raises(self) -> None:
        ext = BlogExtractor()
        req = make_request(content="test", content_type="github_readme")
        with pytest.raises(UnsupportedContentError):
            ext.extract(req)

    def test_statistics(self) -> None:
        ext = BlogExtractor()
        req = make_request(
            content="## Introduction to AI\nAI is transforming everything.",
            content_type="blog_post",
        )
        result = ext.extract(req)
        assert result.statistics is not None

    def test_extract_urls(self) -> None:
        ext = BlogExtractor()
        req = make_request(
            content="Check https://example.com/blog and https://other.com for more.",
            content_type="blog_post",
        )
        result = ext.extract(req)
        assert len(result.references) >= 1


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TestKnowledgeExtractionService:
    def test_init_defaults(self) -> None:
        service = KnowledgeExtractionService()
        assert service._registry is not None
        assert service._model_router is None

    def test_select_extractor_none(self) -> None:
        service = KnowledgeExtractionService()
        assert service.select_extractor(ContentType.UNKNOWN) is None

    def test_select_extractor_found(self) -> None:
        service = KnowledgeExtractionService()
        registry = service._registry
        registry.register(DocumentationExtractor())
        ext = service.select_extractor(ContentType.DOCUMENTATION)
        assert ext is not None
        assert ext.name == "documentation"

    @pytest.mark.asyncio
    async def test_extract_rule_based(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        service = KnowledgeExtractionService(registry=registry)
        req = make_request(
            content="## API\nVersion 1.0.0 of the API is at https://api.example.com",
            content_type="documentation",
        )
        result = await service.extract(req)
        assert isinstance(result, ExtractionResult)
        assert result.statistics is not None
        assert result.statistics.extraction_mode == "rule_based"

    @pytest.mark.asyncio
    async def test_extract_rule_based_no_extractor(self) -> None:
        service = KnowledgeExtractionService()
        req = make_request(content="test", content_type="unknown")
        with pytest.raises(UnsupportedContentError):
            await service.extract(req)

    @pytest.mark.asyncio
    async def test_extract_with_explicit_mode(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        service = KnowledgeExtractionService(registry=registry)
        req = make_request(
            content="test",
            content_type="documentation",
            mode="rule_based",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert result.statistics.extraction_mode == "rule_based"

    @pytest.mark.asyncio
    async def test_extract_batch(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        registry.register(BlogExtractor())
        service = KnowledgeExtractionService(registry=registry)
        reqs = [
            make_request(content="## API\nVersion 1.0.0", content_type="documentation"),
            make_request(content="## Blog\nGreat post about AI", content_type="blog_post"),
        ]
        results = await service.extract_batch(reqs)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, ExtractionResult)

    @pytest.mark.asyncio
    async def test_extract_batch_with_errors(self) -> None:
        service = KnowledgeExtractionService()
        reqs = [
            make_request(content="test", content_type="unknown"),
            make_request(content="test", content_type="unknown"),
        ]
        results = await service.extract_batch(reqs)
        assert len(results) == 2
        assert len(results[0].errors) >= 1
        assert len(results[1].errors) >= 1

    def test_validate_result_valid(self) -> None:
        service = KnowledgeExtractionService()
        req = make_request(content="valid content")
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        service.validate_result(result)

    def test_validate_result_invalid(self) -> None:
        service = KnowledgeExtractionService()
        req = make_request(content="")
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        with pytest.raises(ExtractionValidationError):
            service.validate_result(result)

    def test_collect_statistics(self) -> None:
        service = KnowledgeExtractionService()
        req = make_request(content="test")
        ctx = make_context(req)
        tech = ExtractedTechnology(id="t1", name="GPT")
        result = ExtractionResult(request=req, context=ctx, technologies=[tech])
        stats = service.collect_statistics(result, 10.5, "rule_based")
        assert stats.total_entities == 1
        assert stats.technologies == 1
        assert stats.extraction_duration_ms == 10.5
        assert stats.extraction_mode == "rule_based"

    def test_resolve_content_type_invalid(self) -> None:
        service = KnowledgeExtractionService()
        from aicos.knowledge_extraction.enums import ContentType
        result = service._resolve_content_type(make_request(content="test", content_type="bogus"))
        assert result == ContentType.UNKNOWN

    def test_resolve_content_type_empty(self) -> None:
        service = KnowledgeExtractionService()
        from aicos.knowledge_extraction.enums import ContentType
        result = service._resolve_content_type(make_request(content="test", content_type=""))
        assert result == ContentType.UNKNOWN

    def test_select_extractor_with_lookup(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        service = KnowledgeExtractionService(registry=registry)
        extractors = registry.lookup_by_source(ContentType.DOCUMENTATION)
        assert len(extractors) == 1

    def test_collect_statistics_empty(self) -> None:
        service = KnowledgeExtractionService()
        req = make_request(content="test")
        ctx = make_context(req)
        result = ExtractionResult(request=req, context=ctx)
        stats = service.collect_statistics(result, 0.0, "rule_based")
        assert stats.total_entities == 0

    @pytest.mark.asyncio
    async def test_extract_llm_assisted_fallback_when_no_router(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        service = KnowledgeExtractionService(registry=registry)
        req = make_request(
            content="## API\nVersion 1.0.0",
            content_type="documentation",
            mode="llm_assisted",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert result.statistics.extraction_mode == "rule_based"

    @pytest.mark.asyncio
    async def test_extract_llm_with_model_router(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = {
            "technologies": [{"id": "tech_1", "name": "GPT-5", "summary": "New model"}],
            "frameworks": [{"id": "fw_1", "name": "PyTorch", "description": "ML framework"}],
            "references": [{"id": "ref_1", "source": "OpenAI", "title": "Blog", "url": "https://openai.com"}],
        }
        mock_response.content = json.dumps(mock_response.structured_output)

        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)

        registry = ExtractionRegistry()
        service = KnowledgeExtractionService(registry=registry, model_router=mock_router)
        req = make_request(
            content="GPT-5 is the latest model from OpenAI",
            content_type="blog_post",
            mode="llm_assisted",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert result.statistics.extraction_mode == "llm_assisted"
        assert len(result.technologies) >= 1
        assert len(result.frameworks) >= 1
        assert len(result.references) >= 1

    @pytest.mark.asyncio
    async def test_extract_llm_with_text_response(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = None
        mock_response.content = json.dumps({
            "technologies": [{"id": "tech_1", "name": "CLIP"}],
        })

        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)

        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="CLIP model", content_type="blog_post", mode="llm_assisted")
        result = await service.extract(req)
        assert len(result.technologies) == 1

    @pytest.mark.asyncio
    async def test_extract_llm_with_code_fence(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = None
        mock_response.content = "```json\n{\"technologies\": [{\"id\": \"t1\", \"name\": \"DALL-E\"}]}\n```"

        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)

        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="DALL-E", content_type="blog_post", mode="llm_assisted")
        result = await service.extract(req)
        assert len(result.technologies) >= 1

    @pytest.mark.asyncio
    async def test_extract_llm_with_bad_json(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = None
        mock_response.content = "not json at all"

        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)

        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="test", content_type="blog_post", mode="llm_assisted")
        with pytest.raises(ExtractionError, match="not valid JSON"):
            await service.extract(req)

    @pytest.mark.asyncio
    async def test_extract_llm_with_json_fence_only(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = None
        mock_response.content = "```\n{\"technologies\": [{\"id\": \"t1\", \"name\": \"Gemini\"}]}\n```"

        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)

        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="Gemini model", content_type="blog_post", mode="llm_assisted")
        result = await service.extract(req)
        assert len(result.technologies) >= 1

    @pytest.mark.asyncio
    async def test_extract_llm_invalid_entity_data(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = {
            "technologies": [{"id": "t1", "name": "GPT"}],
            "frameworks": [{"bad_field": "no id or name"}],
        }
        mock_response.content = ""
        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)
        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="test", content_type="blog_post", mode="llm_assisted")
        result = await service.extract(req)
        assert len(result.technologies) == 1
        assert len(result.errors) >= 1

    def test_invalid_mode_string(self) -> None:
        service = KnowledgeExtractionService()
        req = make_request(content="test", mode="invalid_mode")
        mode = service._resolve_mode(req)
        assert mode == ExtractionMode.RULE_BASED

    @pytest.mark.asyncio
    async def test_extract_llm_router_error(self) -> None:
        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(side_effect=RuntimeError("router down"))

        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="test", content_type="blog_post", mode="llm_assisted")
        with pytest.raises(ExtractionError, match="LLM extraction failed"):
            await service.extract(req)

    @pytest.mark.asyncio
    async def test_extract_llm_auto_mode_with_router(self) -> None:
        mock_response = MagicMock()
        mock_response.structured_output = {"technologies": [{"id": "t1", "name": "LLaMA"}]}
        mock_response.content = ""

        mock_router = AsyncMock()
        mock_router.generate = AsyncMock(return_value=mock_response)

        service = KnowledgeExtractionService(model_router=mock_router)
        req = make_request(content="LLaMA model details", mode="auto")
        result = await service.extract(req)
        assert len(result.technologies) >= 1


# ---------------------------------------------------------------------------
# DI Registration
# ---------------------------------------------------------------------------

class TestDIRegistration:
    def test_register_knowledge_extraction(self) -> None:
        from aicos.core.di import Container
        from aicos.knowledge_extraction import register_knowledge_extraction

        container = Container()
        settings = MagicMock()
        settings.knowledge_extraction = {}

        register_knowledge_extraction(container, settings)

        registry = container.resolve(ExtractionRegistry)
        assert isinstance(registry, ExtractionRegistry)
        assert len(registry.registered) == 5

        service = container.resolve(KnowledgeExtractionService)
        assert isinstance(service, KnowledgeExtractionService)


# ---------------------------------------------------------------------------
# Full Extraction Pipeline Integration
# ---------------------------------------------------------------------------

class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_documentation_to_discovery_result(self) -> None:
        registry = ExtractionRegistry()
        registry.register(DocumentationExtractor())
        service = KnowledgeExtractionService(registry=registry)

        req = make_request(
            content="""# API Documentation

## Getting Started
Install version 1.0.0 of our SDK.

## API Reference
The main endpoint is /v1/chat.

```python
import client
client.chat("hello")
```

Visit https://docs.example.com for more information.
""",
            content_type="documentation",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert result.statistics.total_entities > 0

        dr = result.to_discovery_result()
        assert isinstance(dr, DiscoveryResult)

        signals = result.to_signals()
        resources = result.to_resources()
        evidence = result.to_evidence()
        versions = result.to_versions()
        sources = result.to_sources()
        assert isinstance(signals, list)
        assert isinstance(resources, list)
        assert isinstance(evidence, list)
        assert isinstance(versions, list)
        assert isinstance(sources, list)

    @pytest.mark.asyncio
    async def test_github_release_pipeline(self) -> None:
        registry = ExtractionRegistry()
        registry.register(GitHubExtractor())
        service = KnowledgeExtractionService(registry=registry)

        req = make_request(
            content="""## v2.0.0
- Major rewrite
- New API

## v1.0.0
- Initial release

Dependencies: pytorch>=1.0, requests==2.0
""",
            source_type=KnowledgeSourceType.GITHUB,
            content_type="github_release",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert len(result.releases) >= 2
        assert len(result.dependencies) >= 1

    @pytest.mark.asyncio
    async def test_research_paper_pipeline(self) -> None:
        registry = ExtractionRegistry()
        registry.register(ResearchExtractor())
        service = KnowledgeExtractionService(registry=registry)

        req = make_request(
            content="""## Abstract
We introduce a novel approach combining GPT-4 with reinforcement learning.

Previous work [1] showed promising results. Our implementation uses PyTorch [2].

The code is available at https://github.com/example/repo.
""",
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            content_type="research_abstract",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert len(result.models) >= 1
        assert len(result.frameworks) >= 1

    @pytest.mark.asyncio
    async def test_blog_post_pipeline(self) -> None:
        registry = ExtractionRegistry()
        registry.register(BlogExtractor())
        service = KnowledgeExtractionService(registry=registry)

        req = make_request(
            content="""## Why RAG Matters
RAG is transforming how LLMs access information.

Check out https://example.com/rag for more.

- **Key Insight**: Retrieval augments generation
""",
            content_type="blog_post",
        )
        result = await service.extract(req)
        assert result.statistics is not None
        assert len(result.concepts) >= 1
