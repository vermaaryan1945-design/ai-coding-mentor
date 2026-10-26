"""Safe file reader and directory listing tools enforcing security containment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from coding_mentor.permissions import (
    IGNORED_DIRS,
    ActionType,
    PathSecurityError,
    PermissionDeniedError,
    PermissionManager,
)
from coding_mentor.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    """Tool to read the contents of an approved project file."""

    name = "read_file"
    description = (
        "Read the contents of an approved project file. "
        "Supports optional start_line and end_line parameters for targeted inspection."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file (relative to project root or absolute).",
            },
            "start_line": {
                "type": "integer",
                "description": "1-indexed starting line number (optional).",
            },
            "end_line": {
                "type": "integer",
                "description": "1-indexed ending line number (optional).",
            },
        },
        "required": ["path"],
    }

    def execute(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs: Any) -> ToolResult:
        try:
            target = Path(path)
            if not target.is_absolute() and self.permissions.project_root:
                target = self.permissions.project_root / target

            validated_path = self.permissions.validate_path_containment(target)
            self.permissions.request_approval(ActionType.READ_FILE, f"Read file: {validated_path}")

            if not validated_path.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")
            if not validated_path.is_file():
                return ToolResult(success=False, output="", error=f"Target is not a file: {path}")

            # Read file with UTF-8 and graceful replacement
            with open(validated_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_idx = max(0, (start_line - 1)) if start_line is not None else 0
            e_idx = min(total_lines, end_line) if end_line is not None else total_lines

            # Bounded output guardrail
            max_lines = 400
            if (e_idx - s_idx) > max_lines:
                e_idx = s_idx + max_lines
                truncated = True
            else:
                truncated = False

            selected_lines = lines[s_idx:e_idx]
            formatted_lines = [
                f"{idx + 1:4d} | {line.rstrip()}"
                for idx, line in enumerate(selected_lines, start=s_idx)
            ]
            content = "\n".join(formatted_lines)
            if truncated:
                content += f"\n... [Output truncated at {max_lines} lines. Specify start_line/end_line to inspect further]"

            return ToolResult(
                success=True,
                output=content,
                data={
                    "path": str(validated_path),
                    "total_lines": total_lines,
                    "start_line": s_idx + 1,
                    "end_line": e_idx,
                },
            )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error reading file: {e}")


class ListFilesTool(Tool):
    """Tool to inspect project files and directories while filtering build artifacts and secrets."""

    name = "list_files"
    description = (
        "List files and directories in the project workspace, respecting ignore rules "
        "and shielding secrets."
    )
    parameters = {
        "type": "object",
        "properties": {
            "subpath": {
                "type": "string",
                "description": "Optional subpath within project root to list. Defaults to root.",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory traversal depth (default 3).",
            },
        },
    }

    def execute(self, subpath: str = "", max_depth: int = 3, **kwargs: Any) -> ToolResult:
        try:
            base_dir = self.permissions.project_root or Path.cwd()
            if subpath:
                target = (base_dir / subpath).resolve()
            else:
                target = base_dir.resolve()

            validated_dir = self.permissions.validate_path_containment(target)
            self.permissions.request_approval(ActionType.LIST_DIR, f"List directory: {validated_dir}")

            if not validated_dir.exists():
                return ToolResult(success=False, output="", error=f"Directory not found: {subpath}")
            if not validated_dir.is_dir():
                return ToolResult(success=False, output="", error=f"Path is not a directory: {subpath}")

            collected_files: list[str] = []
            base_depth = len(validated_dir.parts)

            for root_str, dirs, files in os.walk(validated_dir):
                root_path = Path(root_str)
                current_depth = len(root_path.parts) - base_depth
                if current_depth >= max_depth:
                    dirs.clear()
                    continue

                # Filter out ignored directories in-place
                dirs[:] = [
                    d for d in dirs
                    if d not in IGNORED_DIRS and not d.startswith(".")
                ]

                for file_name in sorted(files):
                    file_path = root_path / file_name
                    if not self.permissions.is_path_safe_from_secrets(file_path):
                        continue
                    try:
                        rel = file_path.relative_to(base_dir)
                        size_kb = file_path.stat().st_size / 1024
                        collected_files.append(f"{rel} ({size_kb:.1f} KB)")
                    except Exception:
                        continue

            output = "\n".join(collected_files) if collected_files else "No relevant project files found."
            return ToolResult(
                success=True,
                output=output,
                data={"total_files": len(collected_files)},
            )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error listing files: {e}")
