"""OpenAI and OpenAI-compatible LLM Provider implementation.

Supports the official OpenAI client SDK and includes a lightweight standard-library
HTTP fallback for OpenAI-compatible endpoints (Ollama, LM Studio, vLLM, OpenRouter).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Optional

from coding_mentor.logging_config import SecretRedactingFilter
from coding_mentor.providers.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ProviderError,
    ToolCall,
)

logger = logging.getLogger("coding_mentor.providers.openai")


class OpenAIProvider(LLMProvider):
    """Provider connecting to OpenAI or any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self._openai_client = None
        self._init_client()

    def _init_client(self) -> None:
        """Attempt to instantiate official OpenAI SDK client if available."""
        try:
            import openai  # type: ignore

            kwargs: dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            else:
                # Use a dummy key if connecting to local Ollama / LM Studio without auth
                kwargs["api_key"] = "EMPTY"
            if self.base_url:
                kwargs["base_url"] = self.base_url

            self._openai_client = openai.OpenAI(**kwargs)
        except ImportError:
            self._openai_client = None
        except Exception as e:
            logger.warning("Could not initialize openai SDK client: %s", e)
            self._openai_client = None

    def is_available(self) -> bool:
        """Check if provider has credentials or a local server configured."""
        if self.api_key:
            return True
        if self.base_url and ("localhost" in self.base_url or "127.0.0.1" in self.base_url):
            return True
        return False

    def generate(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate response via official SDK or fallback HTTP client."""
        if not self.is_available():
            raise ProviderError(
                "OpenAI provider credentials missing.\n"
                "Please configure OPENAI_API_KEY in your environment or .env file,\n"
                "or run in mock mode via --offline or MENTOR_LLM_PROVIDER=mock."
            )

        # 1. Try official SDK if initialized
        if self._openai_client is not None:
            try:
                return self._generate_via_sdk(messages, tools, temperature)
            except Exception as e:
                # If SDK fails due to network/api errors, re-raise with clear explanation
                self._handle_sdk_error(e)

        # 2. Fallback to standard library urllib
        return self._generate_via_http(messages, tools, temperature)

    def _generate_via_sdk(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        payload_messages = [m.to_dict() for m in messages]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._openai_client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                call_id = getattr(tc, "id", "")
                func = getattr(tc, "function", None)
                fn_name = getattr(func, "name", "") if func else ""
                fn_args = getattr(func, "arguments", "{}") if func else "{}"
                tool_calls.append(ToolCall.from_raw(call_id, fn_name, fn_args))

        usage_dict = {}
        if getattr(response, "usage", None):
            usage_dict = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            model=getattr(response, "model", self.model),
            usage=usage_dict,
        )

    def _handle_sdk_error(self, err: Exception) -> None:
        err_msg = str(err)
        sanitized = SecretRedactingFilter.redact(err_msg)

        lower = sanitized.lower()
        if "authentication" in lower or "incorrect api key" in lower or "401" in lower:
            raise ProviderError(
                f"Authentication failed: The provided API key is invalid or expired. ({sanitized})"
            ) from err
        if "rate limit" in lower or "429" in lower:
            raise ProviderError(
                f"Rate limit exceeded: You have sent too many requests or exceeded quota. ({sanitized})"
            ) from err
        if "connection" in lower or "timeout" in lower:
            raise ProviderError(
                f"Network error: Unable to connect to LLM server. Check your internet connection. ({sanitized})"
            ) from err

        raise ProviderError(f"LLM Provider API request failed: {sanitized}") from err

    def _generate_via_http(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        endpoint = f"{self.base_url}/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AICodingMentor/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw_body = e.read().decode("utf-8", errors="replace")
            sanitized = SecretRedactingFilter.redact(raw_body)
            raise ProviderError(f"HTTP {e.code} error from LLM endpoint: {sanitized}") from e
        except Exception as e:
            sanitized = SecretRedactingFilter.redact(str(e))
            raise ProviderError(f"HTTP request to LLM endpoint failed: {sanitized}") from e

        choice = data["choices"][0]
        msg = choice.get("message", {})
        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append(ToolCall.from_raw(tc.get("id", ""), fn.get("name", ""), fn.get("arguments", "{}")))

        return LLMResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
        )
