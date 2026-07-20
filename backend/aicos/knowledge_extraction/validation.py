from __future__ import annotations

import re
from typing import Any

from .exceptions import ExtractionValidationError
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
    ExtractionResult,
)

_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_URL_PATTERN = re.compile(r"^https?://\S+$")


def validate_required_fields(obj: Any, fields: list[str], label: str) -> list[str]:
    errors: list[str] = []
    for field_name in fields:
        value = getattr(obj, field_name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"{label} missing required field: {field_name}")
    return errors


def validate_duplicate_entities(result: ExtractionResult) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for category, entities in [
        ("technologies", result.technologies),
        ("frameworks", result.frameworks),
        ("models", result.models),
        ("tools", result.tools),
        ("apis", result.apis),
        ("concepts", result.concepts),
        ("versions", result.versions),
        ("releases", result.releases),
        ("dependencies", result.dependencies),
        ("examples", result.examples),
        ("code_snippets", result.code_snippets),
        ("references", result.references),
    ]:
        for entity in entities:
            eid = entity.id
            if eid in seen:
                errors.append(f"duplicate {category} id: {eid}")
            seen[eid] = category
    return errors


def validate_empty_content(content: str) -> list[str]:
    if not content or not content.strip():
        return ["content is empty"]
    return []


def validate_version(version: str) -> list[str]:
    if not version:
        return []
    match = _VERSION_PATTERN.match(version)
    if match is None:
        return [f"invalid version format: {version!r}"]
    return []


def validate_url(url: str) -> list[str]:
    if not url:
        return []
    match = _URL_PATTERN.match(url)
    if match is None:
        return [f"invalid URL format: {url!r}"]
    return []


def validate_reference_consistency(result: ExtractionResult) -> list[str]:
    errors: list[str] = []
    ref_ids = {r.id for r in result.references}
    for tech in result.technologies:
        for ref_id in tech.source_references:
            if ref_id not in ref_ids:
                errors.append(
                    f"technology {tech.id!r} references missing reference {ref_id!r}"
                )
    return errors


def validate_extraction_result(result: ExtractionResult) -> None:
    all_errors: list[str] = []
    all_errors.extend(validate_empty_content(result.request.content))
    all_errors.extend(validate_duplicate_entities(result))
    all_errors.extend(validate_reference_consistency(result))

    for tech in result.technologies:
        all_errors.extend(validate_required_fields(tech, ["id", "name"], "technology"))
    for framework in result.frameworks:
        all_errors.extend(validate_required_fields(framework, ["id", "name"], "framework"))
    for model in result.models:
        all_errors.extend(validate_required_fields(model, ["id", "name"], "model"))
    for tool in result.tools:
        all_errors.extend(validate_required_fields(tool, ["id", "name"], "tool"))
    for api in result.apis:
        all_errors.extend(validate_required_fields(api, ["id", "name"], "api"))
    for concept in result.concepts:
        all_errors.extend(validate_required_fields(concept, ["id", "name"], "concept"))
    for version in result.versions:
        all_errors.extend(validate_required_fields(version, ["id", "version"], "version"))
        all_errors.extend(validate_version(version.version))
    for release in result.releases:
        all_errors.extend(validate_required_fields(release, ["id", "name", "version"], "release"))
        all_errors.extend(validate_version(release.version))
    for dep in result.dependencies:
        all_errors.extend(validate_required_fields(dep, ["id", "name"], "dependency"))
    for example in result.examples:
        all_errors.extend(validate_required_fields(example, ["id", "title"], "example"))
    for snippet in result.code_snippets:
        all_errors.extend(validate_required_fields(snippet, ["id"], "code_snippet"))
    for ref in result.references:
        all_errors.extend(validate_required_fields(ref, ["id", "source", "title"], "reference"))
        all_errors.extend(validate_url(ref.url))

    if all_errors:
        raise ExtractionValidationError("; ".join(all_errors))
