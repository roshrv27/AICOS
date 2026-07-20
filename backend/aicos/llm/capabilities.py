"""Provider-independent model capabilities used for routing."""

from enum import StrEnum


class ModelCapability(StrEnum):
    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"
    SUMMARIZATION = "summarization"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STRUCTURED_OUTPUT = "structured_output"
