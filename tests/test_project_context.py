"""Tests for ProjectContextManager file scanning, symbol extraction, and secret filtering."""

from pathlib import Path
from coding_mentor.project_context import ProjectContextManager


def test_scan_files_and_extract_symbols(temp_project: Path) -> None:
    """Verify scanning captures Python files and AST symbols while skipping .env."""
    pcm = ProjectContextManager(project_root=temp_project)
    summaries = pcm.scan_files()

    rel_paths = [s.relative_path for s in summaries]

    # Python files should be present
    assert any("calculator.py" in p for p in rel_paths)
    assert any("test_calculator.py" in p for p in rel_paths)

    # Secret files must NEVER appear in scanned summaries
    assert not any(".env" in p for p in rel_paths)

    # Check extracted symbols for calculator.py
    calc_summary = next(s for s in summaries if "calculator.py" in s.relative_path)
    assert "class Calculator" in calc_summary.symbols
    assert "def multiply" in calc_summary.symbols


def test_context_summary_generation(temp_project: Path) -> None:
    """Context summary should contain project root and symbols without leaking secrets."""
    pcm = ProjectContextManager(project_root=temp_project)
    summary = pcm.get_context_summary()

    assert str(temp_project) in summary
    assert "calculator.py" in summary
    assert "SUPER_SECRET_KEY" not in summary
    assert "sk-test" not in summary


def test_context_without_project() -> None:
    """Empty context returns helpful placeholder message."""
    pcm = ProjectContextManager(project_root=None)
    summary = pcm.get_context_summary()
    assert "No project directory selected" in summary
