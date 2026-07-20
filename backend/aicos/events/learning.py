"""Knowledge, learning, and quiz event contracts."""

from typing import Literal

from pydantic import Field

from .base import BaseEvent


class KnowledgeGraphUpdated(BaseEvent):
    event_name: Literal["knowledge.graph_updated"] = "knowledge.graph_updated"
    graph_id: str = Field(min_length=1)


class LearningSessionStarted(BaseEvent):
    event_name: Literal["learning.session_started"] = "learning.session_started"
    session_id: str = Field(min_length=1)


class LearningSessionCompleted(BaseEvent):
    event_name: Literal["learning.session_completed"] = "learning.session_completed"
    session_id: str = Field(min_length=1)


class QuizGenerated(BaseEvent):
    event_name: Literal["quiz.generated"] = "quiz.generated"
    quiz_id: str = Field(min_length=1)


class QuizCompleted(BaseEvent):
    event_name: Literal["quiz.completed"] = "quiz.completed"
    quiz_id: str = Field(min_length=1)
