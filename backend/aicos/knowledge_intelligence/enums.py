"""Enumerations for the knowledge intelligence domain.

All enums use ``StrEnum`` for consistent serialization.
"""

from __future__ import annotations

from enum import StrEnum


class KnowledgeSourceType(StrEnum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    GITHUB = "github"
    YOUTUBE = "youtube"
    X = "x"
    RESEARCH_PAPER = "research_paper"
    BLOG = "blog"
    CONFERENCE = "conference"
    COMPANY = "company"
    COMMUNITY = "community"


class TechnologyStatus(StrEnum):
    EXPERIMENTAL = "experimental"
    EMERGING = "emerging"
    GROWING = "growing"
    RECOMMENDED = "recommended"
    INDUSTRY_STANDARD = "industry_standard"
    LEGACY = "legacy"
    DEPRECATED = "deprecated"


class ResourceType(StrEnum):
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    REPOSITORY = "repository"
    COURSE = "course"
    BOOK = "book"
    ARTICLE = "article"
    WORKSHOP = "workshop"


class JobType(StrEnum):
    TECHNOLOGY_DISCOVERY = "technology_discovery"
    RESOURCE_REFRESH = "resource_refresh"
    TREND_ANALYSIS = "trend_analysis"
    VERIFICATION = "verification"
    KNOWLEDGE_VERSIONING = "knowledge_versioning"
