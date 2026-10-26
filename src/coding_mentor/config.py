"""Configuration management for AI Coding Mentor.

Loads settings from environment variables and .env files with sensible
defaults and beginner-friendly error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class ConfigurationError(Exception):
    """Raised when application configuration is invalid or missing required credentials."""


def load_dotenv(env_path: Optional[Path] = None) -> dict[str, str]:
    """Parse key-value pairs from a .env file without external dependencies.

    Does not overwrite existing environment variables.
    """
    if env_path is None:
        # Search current working directory, then user home or package parent
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
        ]
        for candidate in candidates:
            if candidate.is_file():
                env_path = candidate
                break

    loaded: dict[str, str] = {}
    if not env_path or not env_path.is_file():
        return loaded

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
                        loaded[key] = val
    except Exception:
        # Ignore errors reading .env gracefully
        pass
    return loaded


@dataclass
class MentorConfig:
    """Runtime configuration for the AI Coding Mentor assistant."""

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    api_key: Optional[str] = field(default=None, repr=False)
    base_url: Optional[str] = None
    default_mode: str = "hint"
    max_history: int = 20
    auto_approve_reads: bool = True
    allow_code_execution: bool = False
    runner_timeout: int = 15
    log_level: str = "INFO"
    project_path: Optional[Path] = None

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None) -> MentorConfig:
        """Create a configuration instance by loading environment variables."""
        load_dotenv(env_path)

        def _get_bool(key: str, default: bool) -> bool:
            val = os.getenv(key)
            if val is None:
                return default
            return val.lower() in ("1", "true", "yes", "on")

        def _get_int(key: str, default: int) -> int:
            val = os.getenv(key)
            if val is None:
                return default
            try:
                return int(val)
            except ValueError:
                return default

        provider = os.getenv("MENTOR_LLM_PROVIDER", "openai").strip().lower()
        model = os.getenv("MENTOR_LLM_MODEL", "gpt-4o-mini").strip()
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("MENTOR_API_KEY")
        base_url = os.getenv("MENTOR_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        default_mode = os.getenv("MENTOR_DEFAULT_MODE", "hint").strip().lower()
        max_history = _get_int("MENTOR_MAX_HISTORY", 20)
        auto_approve_reads = _get_bool("MENTOR_AUTO_APPROVE_READS", True)
        allow_code_execution = _get_bool("MENTOR_ALLOW_CODE_EXECUTION", False)
        runner_timeout = _get_int("MENTOR_RUNNER_TIMEOUT", 15)
        log_level = os.getenv("MENTOR_LOG_LEVEL", "INFO").strip().upper()

        project_dir_env = os.getenv("MENTOR_PROJECT_PATH")
        project_path = Path(project_dir_env).resolve() if project_dir_env else None

        return cls(
            llm_provider=provider,
            llm_model=model,
            api_key=api_key,
            base_url=base_url,
            default_mode=default_mode,
            max_history=max_history,
            auto_approve_reads=auto_approve_reads,
            allow_code_execution=allow_code_execution,
            runner_timeout=runner_timeout,
            log_level=log_level,
            project_path=project_path,
        )

    def validate(self) -> None:
        """Validate settings and verify credentials when necessary.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        valid_modes = {"hint", "concept", "pseudocode", "review", "solution"}
        if self.default_mode not in valid_modes:
            raise ConfigurationError(
                f"Invalid default mode '{self.default_mode}'. Must be one of: {', '.join(sorted(valid_modes))}"
            )

        if self.llm_provider in ("openai", "openai-compatible"):
            # If using custom local endpoint like Ollama/LM Studio without key, it might be allowed
            is_local = self.base_url and ("localhost" in self.base_url or "127.0.0.1" in self.base_url)
            if not self.api_key and not is_local:
                raise ConfigurationError(
                    "Missing API key for OpenAI provider.\n"
                    "Please set the OPENAI_API_KEY environment variable or define it in a .env file.\n"
                    "For offline testing, set MENTOR_LLM_PROVIDER=mock or pass --offline."
                )

    def is_llm_ready(self) -> bool:
        """Check whether the configuration has sufficient credentials to invoke the LLM."""
        try:
            self.validate()
            return True
        except ConfigurationError:
            return False

    def masked_summary(self) -> dict[str, str | int | bool | None]:
        """Return a dictionary representation with sensitive values masked."""
        masked_key = (
            f"{self.api_key[:3]}...{self.api_key[-4:]}"
            if self.api_key and len(self.api_key) > 8
            else ("***" if self.api_key else None)
        )
        return {
            "provider": self.llm_provider,
            "model": self.llm_model,
            "api_key": masked_key,
            "base_url": self.base_url,
            "default_mode": self.default_mode,
            "max_history": self.max_history,
            "auto_approve_reads": self.auto_approve_reads,
            "allow_code_execution": self.allow_code_execution,
            "runner_timeout": self.runner_timeout,
            "log_level": self.log_level,
            "project_path": str(self.project_path) if self.project_path else None,
        }
