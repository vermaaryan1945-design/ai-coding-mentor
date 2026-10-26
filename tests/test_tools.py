"""Tests for controlled tools: file reading, AST symbol search, syntax checking, runner, and patching."""

from pathlib import Path
from coding_mentor.permissions import ActionType, PermissionManager
from coding_mentor.tools.code_search import CodeSearchTool, SymbolSearchTool
from coding_mentor.tools.file_reader import ListFilesTool, ReadFileTool
from coding_mentor.tools.patch_tool import ProposePatchTool
from coding_mentor.tools.python_runner import PythonRunnerTool
from coding_mentor.tools.syntax_checker import SyntaxCheckerTool


def test_read_file_tool(temp_project: Path, permission_manager: PermissionManager) -> None:
    """Reading a valid file returns formatted line-numbered text."""
    tool = ReadFileTool(permission_manager)
    res = tool.execute(path="src/calculator.py")
    assert res.success is True
    assert "class Calculator" in res.output
    assert "1 |" in res.output


def test_read_file_line_slices(temp_project: Path, permission_manager: PermissionManager) -> None:
    """Reading with start_line and end_line bounds output accurately."""
    tool = ReadFileTool(permission_manager)
    res = tool.execute(path="src/calculator.py", start_line=3, end_line=6)
    assert res.success is True
    assert res.data["start_line"] == 3
    assert res.data["end_line"] == 6


def test_read_file_blocks_secret(temp_project: Path, permission_manager: PermissionManager) -> None:
    """ReadFileTool blocks access to .env."""
    tool = ReadFileTool(permission_manager)
    res = tool.execute(path=".env")
    assert res.success is False
    assert "Security violation" in res.error


def test_list_files_tool(temp_project: Path, permission_manager: PermissionManager) -> None:
    """ListFilesTool lists project files and excludes .env."""
    tool = ListFilesTool(permission_manager)
    res = tool.execute()
    assert res.success is True
    assert "calculator.py" in res.output
    assert ".env" not in res.output


def test_symbol_search_tool(temp_project: Path, permission_manager: PermissionManager) -> None:
    """SymbolSearchTool locates functions and classes."""
    tool = SymbolSearchTool(permission_manager)
    res = tool.execute(query="Calculator")
    assert res.success is True
    assert "[class] Calculator" in res.output

    res2 = tool.execute(query="multiply")
    assert res2.success is True
    assert "[def] multiply" in res2.output


def test_code_search_tool(temp_project: Path, permission_manager: PermissionManager) -> None:
    """CodeSearchTool finds text occurrences with line numbers."""
    tool = CodeSearchTool(permission_manager)
    res = tool.execute(query="multiply")
    assert res.success is True
    assert "calculator.py" in res.output


def test_syntax_checker_valid(permission_manager: PermissionManager) -> None:
    """SyntaxCheckerTool confirms valid Python code."""
    tool = SyntaxCheckerTool(permission_manager)
    res = tool.execute(code="def hello():\n    return 'world'\n")
    assert res.success is True
    assert "Syntax valid" in res.output


def test_syntax_checker_invalid(permission_manager: PermissionManager) -> None:
    """SyntaxCheckerTool pinpoints syntax error with caret pointer."""
    tool = SyntaxCheckerTool(permission_manager)
    res = tool.execute(code="def broken_func(:\n    pass\n")
    assert res.success is False
    assert "SyntaxError" in res.output
    assert "^" in res.output
    assert res.data["line"] == 1


def test_propose_patch_tool(temp_project: Path, permission_manager: PermissionManager) -> None:
    """ProposePatchTool generates a clean unified diff."""
    tool = ProposePatchTool(permission_manager)
    new_code = (
        '"""Calculator module."""\n\n'
        'class Calculator:\n'
        '    def add(self, a: int, b: int) -> int:\n'
        '        return a + b\n\n'
        'def subtract(x: int, y: int) -> int:\n'
        '    return x - y\n'
    )
    res = tool.execute(path="src/calculator.py", new_content=new_code, explanation="Add subtract function")
    assert res.success is True
    assert "```diff" in res.output
    assert "+def subtract" in res.output


def test_python_runner_blocked_without_permission(temp_project: Path) -> None:
    """PythonRunnerTool fails when permission is disabled."""
    pm = PermissionManager(project_root=temp_project, allow_code_execution=False)
    tool = PythonRunnerTool(pm)
    res = tool.execute(path="src/calculator.py")
    assert res.success is False
    assert "disabled by configuration" in res.error


def test_python_runner_success_with_approval(temp_project: Path) -> None:
    """PythonRunnerTool executes Python script when user approves."""
    pm = PermissionManager(
        project_root=temp_project,
        allow_code_execution=True,
        approval_callback=lambda act, desc: True,
    )
    tool = PythonRunnerTool(pm)

    test_script = temp_project / "hello.py"
    test_script.write_text("print('HELLO_FROM_TEST')", encoding="utf-8")

    res = tool.execute(path="hello.py")
    assert res.success is True
    assert "HELLO_FROM_TEST" in res.output
    assert res.data["returncode"] == 0
