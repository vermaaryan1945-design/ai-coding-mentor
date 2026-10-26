"""Conversation state and history manager.

Maintains active assistance mode, bounded chat turns, tool execution
artifacts, and session persistence.
"""

from __future__ import annotations

from typing import Optional

from coding_mentor.providers.base import ChatMessage, ToolCall


class ConversationManager:
    """Manages conversational state, active mode, and message history window."""

    def __init__(self, default_mode: str = "hint", max_history: int = 20) -> None:
        self.mode = default_mode.lower()
        self.max_history = max_history
        self._history: list[ChatMessage] = []

    def set_mode(self, new_mode: str) -> None:
        """Switch active assistance mode."""
        self.mode = new_mode.lower().strip()

    def add_user_message(self, content: str) -> ChatMessage:
        """Record a user query."""
        msg = ChatMessage(role="user", content=content)
        self._history.append(msg)
        self._trim_history()
        return msg

    def add_assistant_message(self, content: str) -> ChatMessage:
        """Record an assistant response."""
        msg = ChatMessage(role="assistant", content=content)
        self._history.append(msg)
        self._trim_history()
        return msg

    def add_tool_result(self, tool_call_id: str, tool_name: str, output: str) -> ChatMessage:
        """Record a tool execution result."""
        msg = ChatMessage(role="tool", content=output, name=tool_name, tool_call_id=tool_call_id)
        self._history.append(msg)
        self._trim_history()
        return msg

    def _trim_history(self) -> None:
        """Ensure message history does not exceed configured boundary."""
        # Each conversational turn consists of 2 messages (user + assistant)
        max_messages = self.max_history * 2
        if len(self._history) > max_messages:
            # Retain the most recent messages
            self._history = self._history[-max_messages:]

    def get_messages_for_llm(self, system_prompt: str) -> list[ChatMessage]:
        """Combine active system prompt with conversation history."""
        messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
        messages.extend(self._history)
        return messages

    def clear(self) -> None:
        """Clear conversation history while preserving active mode."""
        self._history.clear()

    @property
    def turn_count(self) -> int:
        """Count number of user questions in active history."""
        return sum(1 for m in self._history if m.role == "user")

    @property
    def message_count(self) -> int:
        """Total messages in history."""
        return len(self._history)
