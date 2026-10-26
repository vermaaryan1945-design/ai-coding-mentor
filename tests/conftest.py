"""Shared pytest fixtures for the AI Coding Mentor test suite."""

import sys
from pathlib import Path
import pytest

# Ensure src is on Python path
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from coding_mentor.permissions import PermissionManager
from coding_mentor.providers.mock_provider import MockProvider


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure with source files, configs, and a shielded secret file."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    # Sample python source
    calc_py = src_dir / "calculator.py"
    calc_py.write_text(
        '"""Calculator module."""\n\n'
        'class Calculator:\n'
        '    """Basic math."""\n'
        '    def add(self, a: int, b: int) -> int:\n'
        '        return a + b\n\n'
        'def multiply(x: int, y: int) -> int:\n'
        '    return x * y\n',
        encoding="utf-8",
    )

    # Sample test file
    test_calc = tests_dir / "test_calculator.py"
    test_calc.write_text(
        'from src.calculator import Calculator, multiply\n\n'
        'def test_add():\n'
        '    assert Calculator().add(2, 3) == 5\n\n'
        'def test_multiply():\n'
        '    assert multiply(3, 4) == 12\n',
        encoding="utf-8",
    )

    # .gitignore
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".env\n__pycache__/\nbuild/\n", encoding="utf-8")

    # Sensitive .env file that MUST NOT be exposed
    secret_env = tmp_path / ".env"
    secret_env.write_text("SUPER_SECRET_KEY=sk-test-super-secret-token-1234567890\n", encoding="utf-8")

    # README
    readme = tmp_path / "README.md"
    readme.write_text("# Sample Project\nA simple calculator project.\n", encoding="utf-8")

    return tmp_path


@pytest.fixture
def mock_provider() -> MockProvider:
    """Provide a fresh MockProvider."""
    return MockProvider(model="test-model")


@pytest.fixture
def permission_manager(temp_project: Path) -> PermissionManager:
    """Provide a permission manager bound to the temp_project root."""
    return PermissionManager(
        project_root=temp_project,
        auto_approve_reads=True,
        allow_code_execution=False,
    )
