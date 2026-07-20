"""MCP infrastructure event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class MCPServerRegistered(BaseEvent):
    event_name: Literal["mcp.server_registered"] = "mcp.server_registered"
    server_id: str = Field(min_length=1)


class MCPServerHealthChanged(BaseEvent):
    event_name: Literal["mcp.server_health_changed"] = "mcp.server_health_changed"
    server_id: str = Field(min_length=1)
    healthy: bool
