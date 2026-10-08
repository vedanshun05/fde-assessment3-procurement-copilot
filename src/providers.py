"""Server-side provider selection; public configuration never contains a key."""
from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class LiveConfiguration:
    provider: str
    model: str
    key_variable: str

    @property
    def configured(self) -> bool:
        return bool(os.getenv(self.key_variable, "").strip())


def live_configuration() -> LiveConfiguration:
    # Preserve existing OpenAI setups; a Gemini-only key selects Gemini automatically.
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider:
        provider = "gemini" if os.getenv("GEMINI_API_KEY", "").strip() else "openai"
    if provider == "gemini":
        return LiveConfiguration(provider, os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"), "GEMINI_API_KEY")
    if provider == "openai":
        return LiveConfiguration(provider, os.getenv("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14"), "OPENAI_API_KEY")
    raise ValueError("LLM_PROVIDER must be gemini or openai")


class ModelRateLimitError(RuntimeError):
    """Quota failure without provider response text or credentials."""
