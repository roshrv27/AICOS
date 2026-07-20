"""Model-routing domain event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class ModelSelected(BaseEvent):
    event_name: Literal["models.selected"] = "models.selected"
    route_id: str = Field(min_length=1)
