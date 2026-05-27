"""Typed pipeline settings persisted on sessions (JSON-serialized as a dict)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

UI_MODES = frozenset({"Fast", "Balanced", "Deep"})


@dataclass(frozen=True)
class PipelineConfig:
    intent: str = "general"
    complexity: str = "medium"
    search_depth: str | None = None
    mode: str = "Balanced"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> PipelineConfig:
        if not raw:
            return cls()
        sd_raw = raw.get("search_depth")
        search_depth = None if sd_raw is None or sd_raw == "" else str(sd_raw)
        return cls(
            intent=str(raw.get("intent") or "general"),
            complexity=str(raw.get("complexity") or "medium"),
            search_depth=search_depth,
            mode=str(raw.get("mode") or "Balanced"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "complexity": self.complexity,
            "search_depth": self.search_depth,
            "mode": self.mode,
        }
