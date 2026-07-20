"""System lifecycle event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class AgentStarted(BaseEvent):
    event_name: Literal["system.agent_started"] = "system.agent_started"
    agent_id: str = Field(min_length=1)


class AgentCompleted(BaseEvent):
    event_name: Literal["system.agent_completed"] = "system.agent_completed"
    agent_id: str = Field(min_length=1)


class AgentFailed(BaseEvent):
    event_name: Literal["system.agent_failed"] = "system.agent_failed"
    agent_id: str = Field(min_length=1)
    error: str = Field(min_length=1)
