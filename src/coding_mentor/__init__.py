"""AI Coding Mentor - A Personal Agentic Python Assistant.

Designed for computer science students and Python developers to build
independent problem-solving skills through progressive scaffolding,
safe tool execution, and guided debugging.
"""

__version__ = "0.1.0"
__author__ = "AI Coding Mentor Team"

from coding_mentor.assistant import CodingMentorAssistant
from coding_mentor.config import MentorConfig
from coding_mentor.conversation import ConversationManager
from coding_mentor.permissions import PermissionManager
from coding_mentor.project_context import ProjectContextManager

__all__ = [
    "CodingMentorAssistant",
    "ConversationManager",
    "MentorConfig",
    "PermissionManager",
    "ProjectContextManager",
    "__version__",
]
