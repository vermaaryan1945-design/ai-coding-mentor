"""Sandboxed Python code and test runner with timeout and output bounding.

Requires explicit user confirmation before executing any code, safeguarding
against unintended side effects or destructive commands.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from coding_mentor.permissions import (
    ActionType,
    PathSecurityError,
    PermissionDeniedError,
    PermissionManager,
)
from coding_mentor.tools.base import Tool, ToolResult


def _find_python_executable(project_root: Optional[Path]) -> str:
    """Locate virtual environment Python or fallback to current running interpreter."""
    if project_root:
        # Check standard venv locations
        candidates = [
            project_root / ".venv" / "Scripts" / "python.exe",
            project_root / ".venv" / "bin" / "python",
            project_root / "venv" / "Scripts" / "python.exe",
            project_root / "venv" / "bin" / "python",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
    return sys.executable


class PythonRunnerTool(Tool):
    """Tool to execute a designated Python script with timeouts and bounded output."""

    name = "run_python"
    description = (
        "Execute an approved Python script within the project workspace. "
        "Requires explicit user approval before execution."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the Python file to execute.",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional CLI arguments to pass to the script.",
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds (default 15).",
            },
        },
        "required": ["path"],
    }

    def __init__(self, permissions: PermissionManager, default_timeout: int = 15) -> None:
        super().__init__(permissions)
        self.default_timeout = default_timeout

    def execute(
        self,
        path: str,
        args: Optional[list[str]] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            target = Path(path)
            if not target.is_absolute() and self.permissions.project_root:
                target = self.permissions.project_root / target

            validated_path = self.permissions.validate_path_containment(target)

            # Request mandatory user approval
            desc = f"Execute Python script '{validated_path.name}'"
            if args:
                desc += f" with arguments: {args}"
            self.permissions.request_approval(ActionType.RUN_CODE, desc)

            if not validated_path.is_file():
                return ToolResult(success=False, output="", error=f"File not found: {path}")

            python_exe = _find_python_executable(self.permissions.project_root)
            cmd = [python_exe, str(validated_path)]
            if args:
                cmd.extend(args)

            t_val = timeout or self.default_timeout
            cwd = str(self.permissions.project_root or validated_path.parent)

            # Execute without shell=True to prevent command injection
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=t_val,
                shell=False,
                encoding="utf-8",
                errors="replace",
            )

            # Bound output to avoid memory/context bloat
            max_chars = 4000
            stdout = proc.stdout[:max_chars]
            stderr = proc.stderr[:max_chars]

            combined = f"Exit code: {proc.returncode}\n"
            if stdout:
                combined += f"--- STDOUT ---\n{stdout}\n"
            if stderr:
                combined += f"--- STDERR ---\n{stderr}\n"

            return ToolResult(
                success=(proc.returncode == 0),
                output=combined.strip(),
                error=None if proc.returncode == 0 else f"Process exited with code {proc.returncode}",
                data={
                    "returncode": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution timed out after {timeout or self.default_timeout} seconds.",
            )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Execution error: {e}")


class TestRunnerTool(Tool):
    """Tool to execute pytest in the project workspace with safety gates."""

    name = "run_tests"
    description = (
        "Run pytest on the project test suite or a specific test file. "
        "Requires explicit user approval."
    )
    parameters = {
        "type": "object",
        "properties": {
            "test_target": {
                "type": "string",
                "description": "Specific test file or folder path (optional; defaults to 'tests').",
            },
            "timeout": {
                "type": "integer",
                "description": "Execution timeout in seconds (default 20).",
            },
        },
    }

    def __init__(self, permissions: PermissionManager, default_timeout: int = 20) -> None:
        super().__init__(permissions)
        self.default_timeout = default_timeout

    def execute(
        self,
        test_target: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            target_str = test_target or "tests"
            self.permissions.request_approval(ActionType.RUN_TESTS, f"Run pytest on '{target_str}'")

            base_dir = self.permissions.project_root or Path.cwd()
            python_exe = _find_python_executable(self.permissions.project_root)
            cmd = [python_exe, "-m", "pytest", target_str, "-v", "--tb=short"]

            t_val = timeout or self.default_timeout

            proc = subprocess.run(
                cmd,
                cwd=str(base_dir),
                capture_output=True,
                text=True,
                timeout=t_val,
                shell=False,
                encoding="utf-8",
                errors="replace",
            )

            max_chars = 4000
            stdout = proc.stdout[:max_chars]
            stderr = proc.stderr[:max_chars]

            output = f"Pytest exit code: {proc.returncode}\n"
            if stdout:
                output += f"\n{stdout}"
            if stderr:
                output += f"\nSTDERR:\n{stderr}"

            return ToolResult(
                success=(proc.returncode == 0),
                output=output.strip(),
                error=None if proc.returncode == 0 else f"Tests failed with exit code {proc.returncode}",
                data={"returncode": proc.returncode},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Test run timed out after {timeout or self.default_timeout} seconds.",
            )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Test runner error: {e}")
