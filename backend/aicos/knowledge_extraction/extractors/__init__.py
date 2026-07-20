from __future__ import annotations

from .blog import BlogExtractor
from .documentation import DocumentationExtractor
from .github import GitHubExtractor
from .research import ResearchExtractor
from .youtube import YouTubeExtractor

__all__ = [
    "BlogExtractor",
    "DocumentationExtractor",
    "GitHubExtractor",
    "ResearchExtractor",
    "YouTubeExtractor",
]
