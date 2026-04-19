from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# ─────────────────────────────────────────────────────────────────────────────
# Config loader
# ─────────────────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "llm_config.yaml"


def _load_yaml_config() -> dict[str, Any]:
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Message primitive
# ─────────────────────────────────────────────────────────────────────────────

class Message:
    """Simple chat message container (role + content)."""

    def __init__(self, role: str, content: str) -> None:
        if role not in ("system", "user", "assistant"):
            raise ValueError(f"Invalid role: {role!r}")
        self.role = role
        self.content = content

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


# ─────────────────────────────────────────────────────────────────────────────
# Generic LLM client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Generic LLM client — provider-agnostic interface.

    Provider and model settings are read from config/llm_config.yaml.
    Secrets are read from .env:

        LLM_API_KEY   – API key (required for all providers)
        LLM_ENDPOINT  – Azure endpoint URL (Azure only)
        LLM_PROVIDER  – optional env override for the provider

    Supported providers (set LLM_PROVIDER in yaml or .env):
        openai     – OpenAI Chat Completions API
        azure      – Azure OpenAI Chat Completions API
        anthropic  – Anthropic Messages API (Claude)
    """

    def __init__(self) -> None:
        cfg = _load_yaml_config()

        self.provider = (
            os.environ.get("LLM_PROVIDER") or cfg.get("LLM_PROVIDER", "openai")
        ).lower().strip()

        self.model        = cfg.get("LLM_MODEL", "gpt-4o")
        self.temperature  = float(cfg.get("LLM_TEMPERATURE", 0.2))
        self.max_tokens   = int(cfg.get("LLM_MAX_TOKENS", 4096))
        self._api_version = cfg.get("LLM_AZURE_API_VERSION", "2024-02-01")

        self._sdk_client = self._init_sdk()

    def _init_sdk(self) -> Any:
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("LLM_API_KEY is not set in .env.")

        if self.provider == "openai":
            try:
                from openai import OpenAI  # noqa: PLC0415
            except ImportError as exc:
                raise ImportError("pip install openai") from exc
            return OpenAI(api_key=api_key)

        if self.provider == "azure":
            endpoint = os.environ.get("LLM_ENDPOINT", "").strip()
            if not endpoint:
                raise EnvironmentError("LLM_ENDPOINT is not set in .env (required for Azure).")
            try:
                from openai import AzureOpenAI  # noqa: PLC0415
            except ImportError as exc:
                raise ImportError("pip install openai") from exc
            return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=self._api_version)

        if self.provider == "anthropic":
            try:
                import anthropic as sdk  # noqa: PLC0415
            except ImportError as exc:
                raise ImportError("pip install anthropic") from exc
            return sdk.Anthropic(api_key=api_key)

        raise ValueError(
            f"Unknown LLM provider: {self.provider!r}. "
            "Set LLM_PROVIDER to one of: openai, azure, anthropic"
        )

    def generate(self, messages: list[Message], **kwargs: Any) -> str:
        """Send *messages* to the LLM and return the generated text."""
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens  = kwargs.get("max_tokens", self.max_tokens)

        if self.provider == "anthropic":
            system_content = ""
            conversation: list[dict[str, str]] = []
            for msg in messages:
                if msg.role == "system":
                    system_content += msg.content + "\n"
                else:
                    conversation.append(msg.to_dict())
            response = self._sdk_client.messages.create(
                model=self.model,
                system=system_content.strip(),
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.content[0].text if response.content else ""

        # openai and azure share the same Chat Completions interface
        response = self._sdk_client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    # ── convenience constructors ──────────────────────────────────────────────

    @staticmethod
    def system(content: str) -> Message:
        return Message("system", content)

    @staticmethod
    def user(content: str) -> Message:
        return Message("user", content)

    @staticmethod
    def assistant(content: str) -> Message:
        return Message("assistant", content)


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def get_llm_client() -> LLMClient:
    """Create and return a configured LLMClient."""
    return LLMClient()
