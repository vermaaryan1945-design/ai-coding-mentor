"""Project context engine for safe directory analysis and token-budgeted summaries.

Inspects workspace hierarchy, extracts symbols, detects dependencies, and builds
context for LLM prompts while shielding secrets and excluding build artifacts.
"""

from __future__ import annotations

import ast
import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from coding_mentor.permissions import IGNORED_DIRS, PROTECTED_PATTERNS


@dataclass
class ProjectFileSummary:
    """Metadata summary of an inspected project file."""

    relative_path: str
    size_bytes: int
    symbols: list[str] = field(default_factory=list)


class ProjectContextManager:
    """Scans and analyzes an active project directory to build grounded AI context."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root: Optional[Path] = project_root.resolve() if project_root else None
        self._gitignore_patterns: list[str] = []
        self._explicit_files: list[Path] = []
        if self.project_root:
            self._load_gitignore()

    def set_project_root(self, root: Path) -> None:
        """Update the active project root and reload ignore rules."""
        self.project_root = root.resolve()
        self._load_gitignore()

    def add_explicit_file(self, file_path: Path) -> None:
        """Add a specific file to targeted context."""
        resolved = file_path.resolve()
        if resolved.is_file() and resolved not in self._explicit_files:
            self._explicit_files.append(resolved)

    def clear_explicit_files(self) -> None:
        self._explicit_files.clear()

    def _load_gitignore(self) -> None:
        """Parse local .gitignore patterns if available."""
        self._gitignore_patterns = []
        if not self.project_root:
            return
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.is_file():
            try:
                for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._gitignore_patterns.append(line.rstrip("/"))
            except Exception:
                pass

    def _is_ignored(self, path: Path) -> bool:
        """Check if a path matches gitignore or built-in ignore rules."""
        name = path.name.lower()

        # Check protected secrets first
        for pat in PROTECTED_PATTERNS:
            if fnmatch.fnmatch(name, pat.lower()):
                return True

        # Check ignored directories
        for part in path.parts:
            if part in IGNORED_DIRS or (part.startswith(".") and part != "."):
                return True

        if not self.project_root:
            return False

        try:
            rel = str(path.relative_to(self.project_root)).replace("\\", "/")
            for pat in self._gitignore_patterns:
                if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat):
                    return True
        except ValueError:
            return True

        return False

    def scan_files(self, max_files: int = 50) -> list[ProjectFileSummary]:
        """Collect file summaries and symbols within the project root."""
        if not self.project_root or not self.project_root.exists():
            return []

        summaries: list[ProjectFileSummary] = []

        for root_str, dirs, files in os.walk(self.project_root):
            # Exclude ignored dirs in-place
            dirs[:] = [
                d for d in dirs
                if d not in IGNORED_DIRS and not d.startswith(".")
            ]

            for file_name in sorted(files):
                full_path = Path(root_str) / file_name
                if self._is_ignored(full_path):
                    continue

                try:
                    rel_path = str(full_path.relative_to(self.project_root)).replace("\\", "/")
                    stat = full_path.stat()
                    symbols: list[str] = []

                    if file_name.endswith(".py"):
                        symbols = self._extract_symbols(full_path)

                    summaries.append(
                        ProjectFileSummary(
                            relative_path=rel_path,
                            size_bytes=stat.st_size,
                            symbols=symbols,
                        )
                    )
                    if len(summaries) >= max_files:
                        return summaries
                except Exception:
                    continue

        return summaries

    def _extract_symbols(self, py_path: Path) -> list[str]:
        """Extract top-level class and function names from a Python file via AST."""
        try:
            code = py_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(code, filename=str(py_path))
            symbols = []
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"class {node.name}")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"def {node.name}")
            return symbols[:8]  # Limit symbols per file to conserve prompt budget
        except Exception:
            return []

    def get_context_summary(self, max_tokens_estimate: int = 800) -> str:
        """Produce a bounded textual summary of the project structure and dependencies."""
        if not self.project_root:
            return "No project directory selected. Use `context <path>` to attach a project."

        lines: list[str] = [f"Project Root: {self.project_root}"]

        # 1. Dependency information if present
        pyproject = self.project_root / "pyproject.toml"
        requirements = self.project_root / "requirements.txt"
        if pyproject.is_file():
            lines.append("Detected Config: pyproject.toml present")
        elif requirements.is_file():
            try:
                reqs = [
                    line.strip()
                    for line in requirements.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                lines.append(f"Dependencies: {', '.join(reqs[:6])}")
            except Exception:
                pass

        # 2. File list and symbols
        files = self.scan_files(max_files=35)
        if files:
            lines.append("Project Files & Symbols:")
            for f in files:
                sym_str = f" [{', '.join(f.symbols)}]" if f.symbols else ""
                lines.append(f"  - {f.relative_path} ({f.size_bytes} bytes){sym_str}")
        else:
            lines.append("Project Files: No active source files found.")

        # 3. Explicitly pinned files
        if self._explicit_files:
            lines.append("Pinned Active Files:")
            for ef in self._explicit_files:
                lines.append(f"  * {ef.name}")

        return "\n".join(lines)
