"""Core agentic assistant orchestrating LLM, progressive modes, context, and safe tools."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from coding_mentor.config import MentorConfig
from coding_mentor.conversation import ConversationManager
from coding_mentor.permissions import ActionType, PermissionManager
from coding_mentor.project_context import ProjectContextManager
from coding_mentor.prompts import build_system_prompt
from coding_mentor.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderError,
    get_provider,
)
from coding_mentor.tools.base import ToolRegistry
from coding_mentor.tools.code_search import CodeSearchTool, SymbolSearchTool
from coding_mentor.tools.file_reader import ListFilesTool, ReadFileTool
from coding_mentor.tools.patch_tool import ProposePatchTool
from coding_mentor.tools.python_runner import PythonRunnerTool, TestRunnerTool
from coding_mentor.tools.syntax_checker import SyntaxCheckerTool

logger = logging.getLogger("coding_mentor.assistant")


class CodingMentorAssistant:
    """The central agentic assistant coordinating pedagogical guidance and tool actions."""

    def __init__(
        self,
        config: Optional[MentorConfig] = None,
        provider: Optional[LLMProvider] = None,
        approval_callback: Optional[Callable[[ActionType, str], bool]] = None,
    ) -> None:
        self.config = config or MentorConfig.from_env()
        self.permissions = PermissionManager(
            project_root=self.config.project_path,
            auto_approve_reads=self.config.auto_approve_reads,
            allow_code_execution=self.config.allow_code_execution,
            approval_callback=approval_callback,
        )
        self.context = ProjectContextManager(project_root=self.config.project_path)
        self.conversation = ConversationManager(
            default_mode=self.config.default_mode,
            max_history=self.config.max_history,
        )
        self.tools = ToolRegistry(permissions=self.permissions)
        self._register_default_tools()

        # Initialize LLM provider
        self.provider = provider or get_provider(self.config)

    def _register_default_tools(self) -> None:
        """Register the built-in controlled tools."""
        self.tools.register(ReadFileTool(self.permissions))
        self.tools.register(ListFilesTool(self.permissions))
        self.tools.register(SymbolSearchTool(self.permissions))
        self.tools.register(CodeSearchTool(self.permissions))
        self.tools.register(SyntaxCheckerTool(self.permissions))
        self.tools.register(ProposePatchTool(self.permissions))
        self.tools.register(
            PythonRunnerTool(self.permissions, default_timeout=self.config.runner_timeout)
        )
        self.tools.register(
            TestRunnerTool(self.permissions, default_timeout=self.config.runner_timeout)
        )

    @property
    def mode(self) -> str:
        """Current progressive assistance mode."""
        return self.conversation.mode

    def set_mode(self, mode: str) -> None:
        """Switch active assistance mode."""
        self.conversation.set_mode(mode)

    def set_project_path(self, path: Path | str) -> None:
        """Set or change the active project workspace directory."""
        p = Path(path).resolve()
        self.permissions.set_project_root(p)
        self.context.set_project_root(p)
        self.config.project_path = p

    def clear_session(self) -> None:
        """Reset conversation memory for a fresh session."""
        self.conversation.clear()

    def ask(self, user_query: str, max_tool_iterations: int = 5) -> str:
        """Main interaction pipeline: processes student query, triggers tools if needed, returns mentor response.

        Args:
            user_query: The question, code snippet, or prompt from the student.
            max_tool_iterations: Safety ceiling on consecutive tool executions.

        Returns:
            The mentor's formatted pedagogical response.
        """
        self.conversation.add_user_message(user_query)

        # Context & tool descriptors
        context_summary = self.context.get_context_summary()
        tools_desc = self.tools.describe_tools()

        # Tool calling loop
        for iteration in range(max_tool_iterations):
            system_prompt = build_system_prompt(
                mode=self.conversation.mode,
                project_context_summary=context_summary,
                available_tools_desc=tools_desc,
            )
            messages = self.conversation.get_messages_for_llm(system_prompt)
            tool_schemas = self.tools.get_openai_tools()

            try:
                response: LLMResponse = self.provider.generate(
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                )
            except ProviderError as e:
                logger.error("Provider generation error: %s", e)
                return f"⚠️ [LLM Provider Error]: {e}"

            # Check if model requested tools
            if response.has_tool_calls:
                logger.info("Assistant invoked %d tools: %s", len(response.tool_calls), [t.name for t in response.tool_calls])
                for tc in response.tool_calls:
                    tool_result = self.tools.dispatch(tc.name, tc.arguments)
                    result_text = tool_result.output if tool_result.success else f"Error: {tool_result.error}"
                    self.conversation.add_tool_result(
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                        output=result_text,
                    )
                # Continue loop to give model tool results
                continue

            # Model generated final text
            mentor_text = response.content.strip()
            self.conversation.add_assistant_message(mentor_text)
            return mentor_text

        return "⚠️ [Mentor Notice]: Reached maximum tool execution limit for this request."

    def debug(self, code_or_traceback: str) -> str:
        """Dedicated debugging workflow: analyzes errors or tracebacks."""
        previous_mode = self.conversation.mode
        self.conversation.set_mode("debug")
        prompt = (
            f"Please help me debug the following Python error or code:\n\n"
            f"```\n{code_or_traceback}\n```\n\n"
            f"Explain the root cause in simple terms and propose the smallest reasonable fix."
        )
        try:
            return self.ask(prompt)
        finally:
            self.conversation.set_mode(previous_mode)

    def review(self, code: str, file_path: Optional[str] = None) -> str:
        """Dedicated code review workflow."""
        previous_mode = self.conversation.mode
        self.conversation.set_mode("review")
        header = f"Code Review for '{file_path}':\n" if file_path else "Code Review Request:\n"
        prompt = (
            f"{header}```python\n{code}\n```\n\n"
            f"Please review this code for correctness, edge cases, readability, and modularity."
        )
        try:
            return self.ask(prompt)
        finally:
            self.conversation.set_mode(previous_mode)

    def plan(self, project_idea: str) -> str:
        """Dedicated project planning workflow."""
        previous_mode = self.conversation.mode
        self.conversation.set_mode("plan")
        prompt = (
            f"I want to plan the following project:\n"
            f"\"{project_idea}\"\n\n"
            f"Please help me clarify requirements, identify an MVP, structure the folders, "
            f"and define manageable milestones."
        )
        try:
            return self.ask(prompt)
        finally:
            self.conversation.set_mode(previous_mode)
