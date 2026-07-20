"""Digest domain event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class DigestGenerated(BaseEvent):
    event_name: Literal["digest.generated"] = "digest.generated"
    digest_id: str = Field(min_length=1)
