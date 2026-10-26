"""Python syntax and AST validation tool.

Inspects Python code or files for syntax, indentation, and structure errors,
providing beginner-friendly diagnostics with visual indicators.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Optional

from coding_mentor.permissions import (
    ActionType,
    PathSecurityError,
    PermissionDeniedError,
    PermissionManager,
)
from coding_mentor.tools.base import Tool, ToolResult


class SyntaxCheckerTool(Tool):
    """Tool to validate Python syntax and pinpoint syntax/indentation errors."""

    name = "check_syntax"
    description = (
        "Check Python code or a project file for syntax and indentation errors. "
        "Provides precise line, column, and diagnostic feedback."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python source code string to validate.",
            },
            "path": {
                "type": "string",
                "description": "Optional path to a project Python file to validate.",
            },
        },
    }

    def execute(self, code: Optional[str] = None, path: Optional[str] = None, **kwargs: Any) -> ToolResult:
        try:
            filename = "<snippet>"
            source_code = code

            if path:
                target = Path(path)
                if not target.is_absolute() and self.permissions.project_root:
                    target = self.permissions.project_root / target
                validated = self.permissions.validate_path_containment(target)
                self.permissions.request_approval(ActionType.CHECK_SYNTAX, f"Check syntax of: {validated}")

                if not validated.exists():
                    return ToolResult(success=False, output="", error=f"File not found: {path}")
                filename = str(validated)
                source_code = validated.read_text(encoding="utf-8", errors="replace")

            if source_code is None:
                return ToolResult(
                    success=False,
                    output="",
                    error="Either 'code' or 'path' must be provided to check_syntax.",
                )

            # Perform AST parse
            try:
                ast.parse(source_code, filename=filename)
                return ToolResult(
                    success=True,
                    output=f"✓ Syntax valid: No syntax or indentation errors detected in {filename}.",
                    data={"valid": True, "filename": filename},
                )
            except SyntaxError as e:
                lineno = e.lineno or 1
                offset = e.offset or 1
                text = e.text or ""
                caret = " " * (max(1, offset) - 1) + "^"

                err_kind = type(e).__name__
                diagnostic = (
                    f"✗ {err_kind} in {filename} at line {lineno}, column {offset}:\n"
                    f"    {text.rstrip()}\n"
                    f"    {caret}\n"
                    f"Message: {e.msg}\n\n"
                    f"Tip: Common causes include unclosed parentheses, missing colons ':', "
                    f"or mixing tabs and spaces."
                )
                return ToolResult(
                    success=False,
                    output=diagnostic,
                    error=f"{err_kind}: {e.msg}",
                    data={
                        "valid": False,
                        "line": lineno,
                        "column": offset,
                        "error_type": err_kind,
                        "msg": e.msg,
                    },
                )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Syntax inspection failed: {e}")
