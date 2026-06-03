"""Shared JSON-safe serialization helpers for Controller handoff contracts.

The helpers in this module are intentionally representational. They normalize
already-computed handoff facts into bounded, JSON-safe controller state without
calling prompts, providers, search, retrieval, orchestration, persistence, or
cache layers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence


def enum_value(value: Any) -> Any:
    """Return the stable value for enums while leaving other values untouched."""

    if isinstance(value, Enum):
        return value.value
    return value


def json_safe(value: Any) -> Any:
    """Normalize handoff values into JSON-safe primitives."""

    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return json_safe(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [json_safe(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def compact_text(value: Any, *, limit: int = 500) -> str | None:
    """Collapse whitespace and bound review-visible handoff text."""

    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def deduped_text_tuple(
    value: Sequence[Any] | None, *, limit: int = 240
) -> tuple[str, ...]:
    """Return a stable, case-insensitively deduplicated tuple of bounded text."""

    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = compact_text(item, limit=limit)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def json_safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe dict for optional handoff reference mappings."""

    return json_safe(dict(value or {}))
