"""Code and symbol search tools using AST parsing and bounded regex search."""

from __future__ import annotations

import ast
import os
import re
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


class SymbolSearchTool(Tool):
    """Tool that uses Python AST to locate function and class declarations."""

    name = "search_symbols"
    description = (
        "Search for class and function declarations across Python project files "
        "using Abstract Syntax Tree (AST) analysis."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Symbol name or substring to search for (e.g. 'process_data' or 'Mentor').",
            },
            "exact": {
                "type": "boolean",
                "description": "If True, only exact symbol name matches are returned (default False).",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, exact: bool = False, **kwargs: Any) -> ToolResult:
        try:
            base_dir = self.permissions.project_root or Path.cwd()
            self.permissions.request_approval(ActionType.SEARCH_CODE, f"Search symbols for: {query}")

            matches: list[str] = []
            q_lower = query.lower()

            for root_str, dirs, files in os.walk(base_dir):
                # Prune ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

                for f in files:
                    if not f.endswith(".py"):
                        continue
                    file_path = Path(root_str) / f
                    if not self.permissions.is_path_safe_from_secrets(file_path):
                        continue

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        tree = ast.parse(content, filename=str(file_path))
                    except Exception:
                        continue

                    rel_path = file_path.relative_to(base_dir)

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            name = node.name
                            matched = (name == query) if exact else (q_lower in name.lower())
                            if matched:
                                kind = "class" if isinstance(node, ast.ClassDef) else "def"
                                doc = ast.get_docstring(node)
                                first_doc = f" - {doc.splitlines()[0]}" if doc else ""
                                matches.append(f"{rel_path}:{node.lineno} [{kind}] {name}{first_doc}")

            output = "\n".join(matches) if matches else f"No symbols matching '{query}' found."
            return ToolResult(success=True, output=output, data={"matches_count": len(matches)})
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Symbol search failed: {e}")


class CodeSearchTool(Tool):
    """Tool that performs targeted text or regex search across project files."""

    name = "search_code"
    description = "Search for a text pattern or regular expression across project source files."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text or regex pattern to search for.",
            },
            "is_regex": {
                "type": "boolean",
                "description": "Whether to treat query as a regular expression (default False).",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matching lines to return (default 30).",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, is_regex: bool = False, max_results: int = 30, **kwargs: Any) -> ToolResult:
        try:
            base_dir = self.permissions.project_root or Path.cwd()
            self.permissions.request_approval(ActionType.SEARCH_CODE, f"Search code for: {query}")

            try:
                flags = re.IGNORECASE
                pattern = re.compile(query if is_regex else re.escape(query), flags)
            except re.error as e:
                return ToolResult(success=False, output="", error=f"Invalid regular expression: {e}")

            results: list[str] = []

            for root_str, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

                for f in files:
                    file_path = Path(root_str) / f
                    if not self.permissions.is_path_safe_from_secrets(file_path):
                        continue

                    # Only inspect text-like source files
                    if not f.endswith((".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt", ".rst")):
                        continue

                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as fp:
                            for idx, line in enumerate(fp, start=1):
                                if pattern.search(line):
                                    rel = file_path.relative_to(base_dir)
                                    results.append(f"{rel}:{idx}: {line.strip()[:120]}")
                                    if len(results) >= max_results:
                                        break
                    except Exception:
                        continue

                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break

            if not results:
                return ToolResult(success=True, output=f"No matches found for '{query}'.")

            summary = "\n".join(results)
            if len(results) >= max_results:
                summary += f"\n... [Capped at {max_results} results]"
            return ToolResult(success=True, output=summary, data={"count": len(results)})
        except (PathSecurityError, PermissionDeniedError) as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Code search error: {e}")
