"""Base classes and schemas for the controlled tool system."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from coding_mentor.permissions import PermissionManager


@dataclass
class ToolResult:
    """Standard execution result returned by a tool."""

    success: bool
    output: str
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_tool_message(self, tool_call_id: str) -> dict[str, Any]:
        """Convert result into standard tool message format."""
        content = self.output if self.success else f"Error: {self.error or self.output}"
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }


class Tool(ABC):
    """Abstract base class for all agentic tools."""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    def __init__(self, permissions: PermissionManager) -> None:
        self.permissions = permissions

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic with validated arguments."""

    def to_openai_schema(self) -> dict[str, Any]:
        """Return the tool schema formatted for the OpenAI Tools API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry maintaining active tools and routing calls."""

    def __init__(self, permissions: PermissionManager) -> None:
        self.permissions = permissions
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def describe_tools(self) -> str:
        """Generate human-readable summary of available tools for system prompt."""
        lines = []
        for tool in self._tools.values():
            params = ", ".join(tool.parameters.get("properties", {}).keys())
            lines.append(f"- {tool.name}({params}): {tool.description}")
        return "\n".join(lines)

    def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name, returning a safe ToolResult."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' is not registered or recognized.",
            )
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution of tool '{name}' failed: {e}",
            )
