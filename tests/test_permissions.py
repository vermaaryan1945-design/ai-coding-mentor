"""Tests for PermissionManager security boundaries, path containment, and gates."""

from pathlib import Path
import pytest

from coding_mentor.permissions import (
    ActionType,
    PathSecurityError,
    PermissionDeniedError,
    PermissionManager,
)


def test_path_containment_valid(temp_project: Path) -> None:
    """Accessing valid files within project root is permitted."""
    pm = PermissionManager(project_root=temp_project)
    calc_path = temp_project / "src" / "calculator.py"
    validated = pm.validate_path_containment(calc_path)
    assert validated == calc_path.resolve()


def test_path_traversal_blocked(temp_project: Path) -> None:
    """Attempts to escape project root via ../ are blocked."""
    pm = PermissionManager(project_root=temp_project)
    outside_file = temp_project.parent / "outside.txt"
    outside_file.write_text("Secret outside data")

    with pytest.raises(PathSecurityError) as exc_info:
        pm.validate_path_containment(outside_file)
    assert "outside approved project root" in str(exc_info.value)


def test_secret_files_blocked(temp_project: Path) -> None:
    """Attempts to access .env or key files are blocked even if inside project root."""
    pm = PermissionManager(project_root=temp_project)
    env_file = temp_project / ".env"
    with pytest.raises(PathSecurityError) as exc_info:
        pm.validate_path_containment(env_file)
    assert "sensitive file" in str(exc_info.value).lower()

    fake_key = temp_project / "id_rsa"
    with pytest.raises(PathSecurityError):
        pm.validate_path_containment(fake_key)


def test_code_execution_disabled_by_default(temp_project: Path) -> None:
    """RUN_CODE is blocked when allow_code_execution is False."""
    pm = PermissionManager(project_root=temp_project, allow_code_execution=False)
    with pytest.raises(PermissionDeniedError) as exc_info:
        pm.request_approval(ActionType.RUN_CODE, "Run script")
    assert "disabled by configuration" in str(exc_info.value)


def test_approval_callback_accepted(temp_project: Path) -> None:
    """Action passes when approval callback returns True."""
    approved_actions: list[ActionType] = []

    def mock_cb(action: ActionType, desc: str) -> bool:
        approved_actions.append(action)
        return True

    pm = PermissionManager(
        project_root=temp_project,
        allow_code_execution=True,
        approval_callback=mock_cb,
    )
    pm.request_approval(ActionType.RUN_CODE, "Run calculation")
    assert ActionType.RUN_CODE in approved_actions


def test_approval_callback_denied(temp_project: Path) -> None:
    """Action raises PermissionDeniedError when approval callback returns False."""
    def mock_cb(action: ActionType, desc: str) -> bool:
        return False

    pm = PermissionManager(
        project_root=temp_project,
        allow_code_execution=True,
        approval_callback=mock_cb,
    )
    with pytest.raises(PermissionDeniedError) as exc_info:
        pm.request_approval(ActionType.RUN_CODE, "Run calculation")
    assert "rejected by user" in str(exc_info.value)
