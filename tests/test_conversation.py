"""Tests for conversation state management, history windowing, and modes."""

from coding_mentor.conversation import ConversationManager


def test_conversation_initial_mode() -> None:
    """Verify default initial mode."""
    cm = ConversationManager(default_mode="hint")
    assert cm.mode == "hint"
    assert cm.turn_count == 0


def test_conversation_mode_switch() -> None:
    """Verify switching modes."""
    cm = ConversationManager()
    cm.set_mode("concept")
    assert cm.mode == "concept"
    cm.set_mode("pseudocode")
    assert cm.mode == "pseudocode"


def test_add_messages_and_count() -> None:
    """Verify adding user and assistant messages."""
    cm = ConversationManager()
    cm.add_user_message("How do I sort a list?")
    cm.add_assistant_message("Consider the built-in sorted() function.")
    assert cm.turn_count == 1
    assert cm.message_count == 2


def test_history_trimming() -> None:
    """Verify that history is capped at max_history turns."""
    cm = ConversationManager(max_history=3)
    for i in range(10):
        cm.add_user_message(f"Question {i}")
        cm.add_assistant_message(f"Answer {i}")

    # 3 turns = 6 messages maximum
    assert cm.message_count <= 6
    messages = cm.get_messages_for_llm("sys")
    # 1 system + 6 history = 7
    assert len(messages) == 7
    assert "Question 9" in messages[-2].content


def test_clear_session() -> None:
    """Clearing session empties history but keeps active mode."""
    cm = ConversationManager(default_mode="solution")
    cm.add_user_message("Query 1")
    cm.clear()
    assert cm.message_count == 0
    assert cm.mode == "solution"
