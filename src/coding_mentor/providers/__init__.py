"""LLM Provider abstraction layer supporting OpenAI, OpenAI-compatible APIs, and Mocks."""

from coding_mentor.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderError,
    ToolCall,
    get_provider,
)
from coding_mentor.providers.mock_provider import MockProvider
from coding_mentor.providers.openai_provider import OpenAIProvider

__all__ = [
    "ChatMessage",
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "OpenAIProvider",
    "ProviderError",
    "ToolCall",
    "get_provider",
]
