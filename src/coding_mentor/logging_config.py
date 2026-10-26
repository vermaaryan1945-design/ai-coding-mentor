"""Structured logging configuration with automatic secret redaction.

Ensures that sensitive information such as API keys, tokens, and authorization
headers are never exposed in log output or debug dumps.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Pattern

# Patterns representing common API keys and secret formats
SECRET_PATTERNS: list[Pattern[str]] = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[=:]\s*['\"]?)[a-zA-Z0-9_\-]{16,}(['\"]?)", re.IGNORECASE),
    re.compile(r"(password\s*[=:]\s*['\"]?)[^\s'\"]{6,}(['\"]?)", re.IGNORECASE),
    re.compile(r"(secret\s*[=:]\s*['\"]?)[^\s'\"]{8,}(['\"]?)", re.IGNORECASE),
]


class SecretRedactingFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize_value(v) for v in record.args)
        return True

    @classmethod
    def redact(cls, text: str) -> str:
        """Replace occurrences of recognized secrets with a safe masked string."""
        if not isinstance(text, str):
            return text
        sanitized = text
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(r"[REDACTED_SECRET]", sanitized)
        return sanitized

    @classmethod
    def _sanitize_value(cls, value: object) -> object:
        if isinstance(value, str):
            return cls.redact(value)
        return value


def setup_logging(level_name: str = "INFO") -> logging.Logger:
    """Initialize structured, redacted logging for the coding mentor package.

    Args:
        level_name: Desired logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR').

    Returns:
        Configured root logger for coding_mentor.
    """
    numeric_level = getattr(logging, level_name.upper(), logging.INFO)
    logger = logging.getLogger("coding_mentor")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is invoked multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactingFilter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
