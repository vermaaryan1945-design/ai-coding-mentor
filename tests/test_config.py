"""Tests for MentorConfig, environment parsing, and credential validation."""

import os
from pathlib import Path
import pytest

from coding_mentor.config import ConfigurationError, MentorConfig, load_dotenv


def test_default_config() -> None:
    """Verify default settings."""
    cfg = MentorConfig()
    assert cfg.default_mode == "hint"
    assert cfg.llm_provider == "openai"
    assert cfg.max_history == 20
    assert cfg.auto_approve_reads is True
    assert cfg.allow_code_execution is False
    assert cfg.runner_timeout == 15


def test_validation_missing_key() -> None:
    """OpenAI provider without API key must raise ConfigurationError."""
    cfg = MentorConfig(llm_provider="openai", api_key=None, base_url=None)
    with pytest.raises(ConfigurationError) as exc_info:
        cfg.validate()
    assert "Missing API key" in str(exc_info.value)
    assert not cfg.is_llm_ready()


def test_validation_with_key() -> None:
    """OpenAI provider with valid API key passes validation."""
    cfg = MentorConfig(llm_provider="openai", api_key="sk-test-fake-key-1234567890")
    cfg.validate()
    assert cfg.is_llm_ready()


def test_validation_mock_provider() -> None:
    """Mock provider does not require an API key."""
    cfg = MentorConfig(llm_provider="mock", api_key=None)
    cfg.validate()
    assert cfg.is_llm_ready()


def test_validation_local_endpoint() -> None:
    """Local base_url (e.g. Ollama) does not require API key."""
    cfg = MentorConfig(llm_provider="openai", api_key=None, base_url="http://localhost:11434/v1")
    cfg.validate()
    assert cfg.is_llm_ready()


def test_validation_invalid_mode() -> None:
    """Unknown mode raises ConfigurationError."""
    cfg = MentorConfig(default_mode="invalid_mode")
    with pytest.raises(ConfigurationError) as exc_info:
        cfg.validate()
    assert "Invalid default mode" in str(exc_info.value)


def test_masked_summary_redacts_key() -> None:
    """Masked summary must hide sensitive portions of API key."""
    cfg = MentorConfig(api_key="sk-abcdef1234567890xyz")
    summary = cfg.masked_summary()
    api_key_masked = str(summary["api_key"])
    assert "sk-" in api_key_masked
    assert "123456" not in api_key_masked
    assert "..." in api_key_masked


def test_load_dotenv_custom_path(tmp_path: Path) -> None:
    """Test safe parsing of a .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("MENTOR_TEST_VAR=hello_mentor\n# A comment\nANOTHER=value123\n", encoding="utf-8")
    loaded = load_dotenv(env_file)
    assert loaded.get("MENTOR_TEST_VAR") == "hello_mentor"
    assert loaded.get("ANOTHER") == "value123"
    assert os.environ.get("MENTOR_TEST_VAR") == "hello_mentor"
