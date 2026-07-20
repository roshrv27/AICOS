"""Discovery domain event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class DiscoveryStarted(BaseEvent):
    event_name: Literal["discovery.started"] = "discovery.started"
    discovery_id: str = Field(min_length=1)


class DiscoveryCompleted(BaseEvent):
    event_name: Literal["discovery.completed"] = "discovery.completed"
    discovery_id: str = Field(min_length=1)
    resource_count: int = Field(ge=0)


class ResourceDiscovered(BaseEvent):
    event_name: Literal["discovery.resource_discovered"] = "discovery.resource_discovered"
    resource_id: str = Field(min_length=1)
    url: str = Field(min_length=1)


class ResourceRanked(BaseEvent):
    event_name: Literal["discovery.resource_ranked"] = "discovery.resource_ranked"
    resource_id: str = Field(min_length=1)
    score: float


class ResourceValidated(BaseEvent):
    event_name: Literal["discovery.resource_validated"] = "discovery.resource_validated"
    resource_id: str = Field(min_length=1)
    valid: bool
