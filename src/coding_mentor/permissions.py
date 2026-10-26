"""Security and permission enforcement system.

Guarantees safety boundaries at runtime through strict path containment,
automatic shielding of sensitive files/secrets, and mandatory user confirmation
gates for execution or modification actions.
"""

from __future__ import annotations

import fnmatch
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


class ActionType(str, Enum):
    """Categorization of agentic actions and tool operations."""

    READ_FILE = "read_file"
    LIST_DIR = "list_dir"
    SEARCH_CODE = "search_code"
    CHECK_SYNTAX = "check_syntax"
    PROPOSE_PATCH = "propose_patch"
    APPLY_PATCH = "apply_patch"
    RUN_CODE = "run_code"
    RUN_TESTS = "run_tests"


class PermissionDeniedError(Exception):
    """Raised when an operation is rejected by the permission controller or user."""


class PathSecurityError(PermissionDeniedError):
    """Raised when an operation targets paths outside permitted boundaries or secret files."""


# Patterns for sensitive files that must NEVER be accessed or exposed
PROTECTED_PATTERNS: tuple[str, ...] = (
    ".env*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "credentials.json",
    "token.json",
    "secrets.json",
    "*_rsa",
    "*_dsa",
)

# Directory patterns to protect from deep traversal/inspection
IGNORED_DIRS: tuple[str, ...] = (
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
)


class PermissionManager:
    """Enforces runtime security policies for all agent tool executions."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        auto_approve_reads: bool = True,
        allow_code_execution: bool = False,
        approval_callback: Optional[Callable[[ActionType, str], bool]] = None,
    ) -> None:
        """Initialize the permission controller.

        Args:
            project_root: Canonical root path restricting file access.
            auto_approve_reads: If True, safe read operations within root do not require manual confirmation.
            allow_code_execution: If False, code execution is completely blocked.
            approval_callback: Optional callback `(action, description) -> bool` for user prompts.
        """
        self.project_root = project_root.resolve() if project_root else None
        self.auto_approve_reads = auto_approve_reads
        self.allow_code_execution = allow_code_execution
        self.approval_callback = approval_callback

    def set_project_root(self, root: Path) -> None:
        """Update active project boundary."""
        self.project_root = root.resolve()

    def is_path_safe_from_secrets(self, path: Path) -> bool:
        """Verify that a path does not target sensitive secret files."""
        name = path.name.lower()
        for pattern in PROTECTED_PATTERNS:
            if fnmatch.fnmatch(name, pattern.lower()):
                return False
        return True

    def validate_path_containment(self, target_path: Path) -> Path:
        """Ensure the target path resides strictly inside the approved project root.

        Args:
            target_path: Path to validate.

        Returns:
            Resolved canonical Path.

        Raises:
            PathSecurityError: If path attempts path traversal or accesses secrets.
        """
        resolved = target_path.resolve()

        # Check secret protection
        if not self.is_path_safe_from_secrets(resolved):
            raise PathSecurityError(
                f"Security violation: Access to sensitive file '{resolved.name}' is blocked."
            )

        # Check directory traversal containment
        if self.project_root is not None:
            try:
                resolved.relative_to(self.project_root)
            except ValueError:
                raise PathSecurityError(
                    f"Security violation: Target path '{resolved}' is outside approved project root '{self.project_root}'."
                )

        return resolved

    def request_approval(self, action: ActionType, description: str) -> None:
        """Verify permission for an action, prompting for approval when required.

        Args:
            action: Type of action requested.
            description: Plain-text explanation of the action and its arguments.

        Raises:
            PermissionDeniedError: If permission is rejected or not enabled.
        """
        # Block code execution if global switch is disabled
        if action in (ActionType.RUN_CODE, ActionType.RUN_TESTS):
            if not self.allow_code_execution:
                raise PermissionDeniedError(
                    f"Action '{action.value}' is disabled by configuration (MENTOR_ALLOW_CODE_EXECUTION=False)."
                )

        # Safe read operations can be auto-approved
        if self.auto_approve_reads and action in (
            ActionType.READ_FILE,
            ActionType.LIST_DIR,
            ActionType.SEARCH_CODE,
            ActionType.CHECK_SYNTAX,
            ActionType.PROPOSE_PATCH,
        ):
            return

        # Explicit user confirmation needed for execution, file modification, or manual reads
        if self.approval_callback is not None:
            approved = self.approval_callback(action, description)
            if not approved:
                raise PermissionDeniedError(f"Action '{action.value}' was rejected by user.")
        else:
            # When running without an interactive callback, deny potentially unsafe actions
            if action in (ActionType.RUN_CODE, ActionType.RUN_TESTS, ActionType.APPLY_PATCH):
                raise PermissionDeniedError(
                    f"Action '{action.value}' requires explicit interactive approval, but no callback is configured."
                )
