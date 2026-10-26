"""End-to-end integration tests for CodingMentorAssistant workflows and tool loops."""

from pathlib import Path
from coding_mentor.assistant import CodingMentorAssistant
from coding_mentor.config import MentorConfig
from coding_mentor.providers.base import LLMResponse, ProviderError, ToolCall
from coding_mentor.providers.mock_provider import MockProvider


def test_assistant_modes_flow(temp_project: Path) -> None:
    """Verify progressive assistance across different modes."""
    config = MentorConfig(llm_provider="mock", project_path=temp_project)
    provider = MockProvider()
    assistant = CodingMentorAssistant(config=config, provider=provider)

    # 1. Hint Mode (Default)
    hint_res = assistant.ask("How to reverse a string in Python?")
    assert "💡 [Mentor Hint]" in hint_res

    # 2. Concept Mode
    assistant.set_mode("concept")
    concept_res = assistant.ask("Explain dictionaries")
    assert "📚 [Mentor Concept]" in concept_res

    # 3. Pseudocode Mode
    assistant.set_mode("pseudocode")
    pseudo_res = assistant.ask("Two sum problem")
    assert "📝 [Mentor Pseudocode]" in pseudo_res

    # 4. Solution Mode
    assistant.set_mode("solution")
    sol_res = assistant.ask("Write a function to sum numbers")
    assert "✨ [Mentor Solution]" in sol_res


def test_assistant_specialized_workflows(temp_project: Path) -> None:
    """Verify debug, review, and plan convenience methods."""
    config = MentorConfig(llm_provider="mock", project_path=temp_project)
    provider = MockProvider()
    assistant = CodingMentorAssistant(config=config, provider=provider)

    # Debug workflow
    debug_res = assistant.debug("IndexError: list index out of range at line 10")
    assert "🐛 [Mentor Debugging Analysis]" in debug_res

    # Review workflow
    review_res = assistant.review("def f(x):\n    return x + 1\n")
    assert "🔍 [Mentor Code Review]" in review_res

    # Plan workflow
    plan_res = assistant.plan("Build a command line flashcard app")
    assert "📋 [Mentor Project Plan]" in plan_res


def test_assistant_tool_calling_loop(temp_project: Path) -> None:
    """Verify agentic tool call execution and subsequent response generation."""
    config = MentorConfig(llm_provider="mock", project_path=temp_project)
    provider = MockProvider()

    # Queue a tool call followed by a final synthesis response
    tool_call = ToolCall(
        id="call_read_1",
        name="read_file",
        arguments={"path": "src/calculator.py", "start_line": 1, "end_line": 5},
    )
    resp1 = LLMResponse(content="", tool_calls=[tool_call])
    resp2 = LLMResponse(content="I inspected src/calculator.py and found the Calculator class definition.")

    provider.queue_response(resp1)
    provider.queue_response(resp2)

    assistant = CodingMentorAssistant(config=config, provider=provider)
    result = assistant.ask("What classes are defined in src/calculator.py?")

    assert "Calculator class definition" in result
    # Check that tool was recorded in conversation history
    assert any(m.role == "tool" and m.name == "read_file" for m in assistant.conversation._history)


def test_assistant_handles_provider_error(temp_project: Path) -> None:
    """Assistant must catch ProviderError gracefully without crashing."""
    config = MentorConfig(llm_provider="mock", project_path=temp_project)

    class FailingProvider(MockProvider):
        def generate(self, *args, **kwargs):
            raise ProviderError("Network timeout connecting to LLM")

    assistant = CodingMentorAssistant(config=config, provider=FailingProvider())
    result = assistant.ask("Hello?")
    assert "⚠️ [LLM Provider Error]" in result
    assert "Network timeout" in result
