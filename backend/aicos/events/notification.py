"""Notification domain event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class NotificationRequested(BaseEvent):
    event_name: Literal["notification.requested"] = "notification.requested"
    notification_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
