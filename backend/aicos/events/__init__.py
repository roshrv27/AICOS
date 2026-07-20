"""Versioned event contracts and transport-neutral Event Bus APIs."""

from .base import BaseEvent
from .bus import EventBusProtocol, InProcessEventBus
from .dispatcher import PublishResult, SubscriberFailure
from .exceptions import (
    EventBusClosedError,
    EventDispatchError,
    EventRegistrationError,
    EventSubscriberError,
    EventValidationError,
)
from .history import EventHistory, EventHistoryEntry, InMemoryEventHistory
from .middleware import EventMiddleware
from .publisher import EventPublisher
from .registry import EventRegistry, global_event_registry
from .subscriber import Subscription

# Importing event modules automatically registers their typed contracts.
from .curriculum import CurriculumUpdated, TopicAdded, TopicArchived
from .digest import DigestGenerated
from .discovery import (
    DiscoveryCompleted,
    DiscoveryStarted,
    ResourceDiscovered,
    ResourceRanked,
    ResourceValidated,
)
from .learning import (
    KnowledgeGraphUpdated,
    LearningSessionCompleted,
    LearningSessionStarted,
    QuizCompleted,
    QuizGenerated,
)
from .mcp import MCPServerHealthChanged, MCPServerRegistered
from .models import ModelSelected
from .notification import NotificationRequested
from .portfolio import PortfolioGenerated
from .system import AgentCompleted, AgentFailed, AgentStarted

__all__ = [
    "AgentCompleted", "AgentFailed", "AgentStarted", "BaseEvent", "CurriculumUpdated",
    "DigestGenerated", "DiscoveryCompleted", "DiscoveryStarted", "EventBusClosedError",
    "EventBusProtocol", "EventDispatchError", "EventHistory", "EventHistoryEntry", "EventMiddleware",
    "EventPublisher",
    "EventRegistrationError", "EventRegistry", "EventSubscriberError", "EventValidationError",
    "InMemoryEventHistory", "InProcessEventBus", "KnowledgeGraphUpdated",
    "LearningSessionCompleted", "LearningSessionStarted", "MCPServerHealthChanged",
    "MCPServerRegistered", "ModelSelected", "NotificationRequested", "PortfolioGenerated",
    "PublishResult", "QuizCompleted", "QuizGenerated", "ResourceDiscovered", "ResourceRanked",
    "ResourceValidated", "SubscriberFailure", "Subscription", "TopicAdded", "TopicArchived",
    "global_event_registry",
]
