"""Mock LLM Provider for offline demonstration, reproducible unit testing, and sandbox runs."""

from __future__ import annotations

from typing import Any, Callable, Optional

from coding_mentor.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ToolCall,
)


class MockProvider(LLMProvider):
    """Deterministic mock provider that requires no internet connection or API keys."""

    def __init__(
        self,
        model: str = "mock-mentor",
        canned_responses: Optional[list[LLMResponse | str]] = None,
        generator_func: Optional[Callable[[list[ChatMessage], Optional[list[dict[str, Any]]]], LLMResponse]] = None,
    ) -> None:
        self.model = model
        self.canned_responses = list(canned_responses) if canned_responses else []
        self.generator_func = generator_func
        self.call_history: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def queue_response(self, response: LLMResponse | str) -> None:
        """Add a planned response to the FIFO queue."""
        self.canned_responses.append(response)

    def generate(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        self.call_history.append({"messages": messages, "tools": tools, "temperature": temperature})

        # 1. Check custom generator function
        if self.generator_func is not None:
            return self.generator_func(messages, tools)

        # 2. Check queued canned responses
        if self.canned_responses:
            next_resp = self.canned_responses.pop(0)
            if isinstance(next_resp, LLMResponse):
                return next_resp
            return LLMResponse(content=str(next_resp), model=self.model)

        # 3. Default contextual mock behavior based on last user message and active mode
        last_user_msg = ""
        system_prompt = ""
        for msg in reversed(messages):
            if msg.role == "user" and not last_user_msg:
                last_user_msg = msg.content
            if msg.role == "system" and not system_prompt:
                system_prompt = msg.content

        # Determine mode from system prompt header
        mode = "hint"
        mode_signatures = {
            "debug": "[DEBUGGING ASSISTANT]",
            "review": "[CODE REVIEW MODE]",
            "plan": "[PROJECT PLANNING AGENT]",
            "concept": "[CONCEPT MODE]",
            "pseudocode": "[PSEUDOCODE MODE]",
            "solution": "[SOLUTION MODE]",
            "hint": "[HINT MODE]",
        }
        for candidate_mode, sig in mode_signatures.items():
            if sig in system_prompt:
                mode = candidate_mode
                break

        content = self._generate_default_mock_text(mode, last_user_msg)
        return LLMResponse(content=content, model=self.model)

    def _generate_default_mock_text(self, mode: str, query: str) -> str:
        if mode == "hint":
            return (
                f"💡 [Mentor Hint]: You're exploring '{query[:40]}...'.\n"
                f"Consider breaking the problem down: what data structure preserves the order and provides O(1) lookups?\n"
                f"Try writing out what your inputs and outputs look like first!"
            )
        elif mode == "concept":
            return (
                f"📚 [Mentor Concept]: In Python, understanding data flow and complexity is key.\n"
                f"For example, a dictionary uses hash mapping for average O(1) lookups:\n"
                f"```python\ncounts = {{'apple': 3, 'banana': 5}}\nprint(counts.get('apple', 0))\n```\n"
                f"Notice how `.get()` avoids a KeyError if the key is missing."
            )
        elif mode == "pseudocode":
            return (
                f"📝 [Mentor Pseudocode]:\n"
                f"1. Initialize an empty tracker (e.g., dict or set).\n"
                f"2. Loop through each item in the sequence.\n"
                f"3. Check if condition matches criteria.\n"
                f"4. Update tracker and continue.\n"
                f"5. Return the resulting aggregated output.\n"
                f"Give translating this into Python a try!"
            )
        elif mode == "review":
            return (
                f"🔍 [Mentor Code Review]:\n"
                f"Good structure! Here are two observations:\n"
                f"- Readability: Variable names could be more descriptive.\n"
                f"- Edge Case: What happens if the input list is empty or None?\n"
                f"Consider adding a defensive check at the beginning."
            )
        elif mode == "debug":
            return (
                f"🐛 [Mentor Debugging Analysis]:\n"
                f"- Likely Root Cause: Index or Key reference out of range.\n"
                f"- Why it happened: Python raised this error because the collection does not contain the queried index.\n"
                f"- Recommended Minimal Fix: Check collection bounds with `len()` or `.get()` before accessing.\n"
                f"- Prevention: Always validate input sizes or use safe access methods."
            )
        elif mode == "plan":
            return (
                f"📋 [Mentor Project Plan]:\n"
                f"1. MVP Scope: Minimal CLI with single core algorithm.\n"
                f"2. Folder Structure:\n"
                f"   src/my_project/\n"
                f"     __init__.py\n"
                f"     core.py\n"
                f"   tests/test_core.py\n"
                f"3. Milestones: Setup -> Core Logic -> Unit Tests -> Documentation."
            )
        else:  # solution
            return (
                f"✨ [Mentor Solution]:\n"
                f"Here is a clean implementation:\n"
                f"```python\ndef solve(data: list[int]) -> int:\n    if not data:\n        return 0\n    return sum(data)\n```\n"
                f"Design choices: Handled empty input defensively and used Python built-in `sum()`."
            )
