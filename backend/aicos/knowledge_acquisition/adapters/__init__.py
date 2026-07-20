"""Knowledge acquisition adapters package.

All concrete adapters are exported here so the registry can discover them
via a single import path.
"""

from __future__ import annotations

from .base import KnowledgeAdapter
from .github import GitHubAdapter
from .official_docs import OfficialDocsAdapter
from .research import ResearchAdapter
from .x import XAdapter
from .youtube import YouTubeAdapter

__all__ = [
    "GitHubAdapter",
    "KnowledgeAdapter",
    "OfficialDocsAdapter",
    "ResearchAdapter",
    "XAdapter",
    "YouTubeAdapter",
]
