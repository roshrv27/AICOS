"""Curriculum domain event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class CurriculumUpdated(BaseEvent):
    event_name: Literal["curriculum.updated"] = "curriculum.updated"
    curriculum_id: str = Field(min_length=1)


class TopicAdded(BaseEvent):
    event_name: Literal["curriculum.topic_added"] = "curriculum.topic_added"
    curriculum_id: str = Field(min_length=1)
    topic_id: str = Field(min_length=1)


class TopicArchived(BaseEvent):
    event_name: Literal["curriculum.topic_archived"] = "curriculum.topic_archived"
    topic_id: str = Field(min_length=1)
