"""Provider-aware API key validation helpers."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping

_SEARCH_PROVIDER_ENV = {
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "linkup": "LINKUP_API_KEY",
    "brave": "BRAVE_API_KEY",
}


def missing_required_api_keys(
    *,
    fast_provider: str,
    smart_provider: str,
    embed_provider: str,
    active_search_providers: Iterable[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Return required API key env var names that are currently missing."""
    env_map = env or os.environ
    missing: list[str] = []

    providers = (fast_provider, smart_provider, embed_provider)
    if any(str(provider).strip() == "OpenAI" for provider in providers):
        if not env_map.get("OPENAI_API_KEY"):
            missing.append("OPENAI_API_KEY")

    active = {
        str(provider).strip().lower()
        for provider in (active_search_providers or [])
        if str(provider).strip()
    }
    for provider in ("tavily", "exa", "linkup", "brave"):
        if provider not in active:
            continue
        env_key = _SEARCH_PROVIDER_ENV[provider]
        if not env_map.get(env_key):
            missing.append(env_key)

    return missing
