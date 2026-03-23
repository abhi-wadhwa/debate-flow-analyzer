"""LLM API interface with support for real and mock backends."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    """Wrapper around an LLM completion response."""

    text: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)

    def as_json(self) -> Any:
        """Parse the response text as JSON, stripping markdown fences if present."""
        cleaned = self.text.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` wrapper
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """Send a prompt and return the completion."""

    @abstractmethod
    def complete_json(self, prompt: str, system: str = "") -> Any:
        """Send a prompt and parse the response as JSON."""


class OpenAIClient(LLMClient):
    """Client that uses the OpenAI-compatible API (works with OpenAI, Azure, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        try:
            import openai  # noqa: F401
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import openai

            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        client = self._get_client()
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
        return LLMResponse(
            text=choice.message.content or "",
            model=response.model,
            usage=usage,
        )

    def complete_json(self, prompt: str, system: str = "") -> Any:
        resp = self.complete(prompt, system)
        return resp.as_json()


class MockLLMClient(LLMClient):
    """Mock LLM client for testing -- returns predefined responses."""

    def __init__(self, responses: Optional[List[str]] = None):
        self._responses: List[str] = responses or []
        self._call_index: int = 0
        self.prompts_received: List[str] = []

    def add_response(self, response: str) -> None:
        """Enqueue a response to be returned on the next call."""
        self._responses.append(response)

    def _next_response(self) -> str:
        if not self._responses:
            return "{}"
        idx = min(self._call_index, len(self._responses) - 1)
        self._call_index += 1
        return self._responses[idx]

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        self.prompts_received.append(prompt)
        return LLMResponse(text=self._next_response(), model="mock")

    def complete_json(self, prompt: str, system: str = "") -> Any:
        resp = self.complete(prompt, system)
        return resp.as_json()


def create_client(
    backend: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMClient:
    """Factory to create an LLM client.

    Parameters
    ----------
    backend : str
        ``"openai"`` for a real API client, ``"mock"`` for testing.
    api_key : str, optional
        API key (or set ``OPENAI_API_KEY`` env var).
    model : str, optional
        Model name.  Defaults to ``gpt-4o-mini``.
    base_url : str, optional
        Custom API base URL for compatible providers.
    """
    if backend == "mock":
        return MockLLMClient()
    if backend == "openai":
        return OpenAIClient(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            base_url=base_url,
        )
    raise ValueError(f"Unknown backend: {backend}")
