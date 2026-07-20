"""Portfolio domain event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class PortfolioGenerated(BaseEvent):
    event_name: Literal["portfolio.generated"] = "portfolio.generated"
    portfolio_id: str = Field(min_length=1)
