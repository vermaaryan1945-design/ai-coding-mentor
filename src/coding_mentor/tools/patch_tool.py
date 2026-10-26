"""Patch and code proposal tool generating reviewable diffs.

Ensures that code changes are never silently written to disk without explicit
user review and confirmation.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any, Optional

from coding_mentor.permissions import (
    ActionType,
    PathSecurityError,
    PermissionDeniedError,
    PermissionManager,
)
from coding_mentor.tools.base import Tool, ToolResult


class ProposePatchTool(Tool):
    """Tool to prepare a reviewable unified diff for proposed file changes."""

    name = "propose_patch"
    description = (
        "Generate a unified diff proposal for a target project file. "
        "Allows the user to inspect changes safely before any modification is applied."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Target file path (relative to project root or absolute).",
            },
            "new_content": {
                "type": "string",
                "description": "Complete new content proposed for the file.",
            },
            "explanation": {
                "type": "string",
                "description": "Brief explanation of what the proposed patch changes and why.",
            },
        },
        "required": ["path", "new_content"],
    }

    def execute(
        self,
        path: str,
        new_content: str,
        explanation: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        try:
            target = Path(path)
            if not target.is_absolute() and self.permissions.project_root:
                target = self.permissions.project_root / target

            validated_path = self.permissions.validate_path_containment(target)
            self.permissions.request_approval(
                ActionType.PROPOSE_PATCH,
                f"Propose patch for: {validated_path.name}",
            )

            # Read existing content if file exists
            if validated_path.exists():
                existing_content = validated_path.read_text(encoding="utf-8", errors="replace")
                orig_label = f"a/{validated_path.name} (original)"
            else:
                existing_content = ""
                orig_label = f"/dev/null (new file)"

            new_label = f"b/{validated_path.name} (proposed)"

            diff_lines = list(
                difflib.unified_diff(
                    existing_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=orig_label,
                    tofile=new_label,
                )
            )
            diff_text = "".join(diff_lines)

            if not diff_text:
                return ToolResult(
                    success=True,
                    output=f"No differences: Proposed content is identical to existing {validated_path.name}.",
                    data={"identical": True},
                )

            summary = f"Proposed Changes for: {validated_path.name}\n"
            if explanation:
                summary += f"Explanation: {explanation}\n"
            summary += f"\n```diff\n{diff_text}```\n"

            return ToolResult(
                success=True,
                output=summary,
                data={
                    "target_path": str(validated_path),
                    "new_content": new_content,
                    "diff": diff_text,
                    "is_new_file": not validated_path.exists(),
                },
            )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Patch proposal failed: {e}")

    def apply_patch(self, path: str, new_content: str) -> ToolResult:
        """Apply approved content to the specified file after confirmation."""
        try:
            target = Path(path)
            if not target.is_absolute() and self.permissions.project_root:
                target = self.permissions.project_root / target

            validated_path = self.permissions.validate_path_containment(target)
            self.permissions.request_approval(
                ActionType.APPLY_PATCH,
                f"Write {len(new_content)} characters to '{validated_path}'",
            )

            validated_path.parent.mkdir(parents=True, exist_ok=True)
            validated_path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Successfully applied changes to {validated_path.name}.",
                data={"path": str(validated_path)},
            )
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to apply patch: {e}")
