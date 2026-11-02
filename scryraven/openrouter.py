"""Narrow stateless Responses adaptation; no server tools or model fallback."""

from __future__ import annotations

from copy import deepcopy


def openrouter_payload(payload: dict) -> dict:
    """Retain strict schemas, native function calls and opaque continuation.

    OpenRouter's documented Responses endpoint accepts the native conversation.
    Its compatibility filter must require every requested parameter. API cache
    extensions and OpenAI service tiers are not OpenRouter controls.
    """
    body = deepcopy(payload)
    for name in ("prompt_cache_key", "prompt_cache_options", "service_tier"):
        body.pop(name, None)
    for item in body["input"]:
        content = item.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block.pop("prompt_cache_breakpoint", None)
    body["provider"] = {"require_parameters": True, "allow_fallbacks": False}
    # Explicit empties also prevent account-default transforms/plugins from
    # adding summarization, server search or JSON repair to this request.
    body["plugins"] = []
    body["transforms"] = []
    body["store"] = False
    return body
