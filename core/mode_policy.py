"""Passive mirror of existing UI mode settings.

This module records the mode-derived settings that the orchestrator already
computes. It does not choose routing, search providers, prompts, retrieval, or
execution paths.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class RunMode(str, Enum):
    FAST = "Fast"
    BALANCED = "Balanced"
    DEEP = "Deep"


@dataclass(frozen=True)
class ModePolicy:
    """Passive snapshot of settings currently assigned from a UI mode."""

    mode: RunMode
    complexity: str
    search_depth: str
    max_queries: int
    results_per_query: int
    top_chunks: int
    max_iterations: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        return payload


MODE_POLICIES: dict[RunMode, ModePolicy] = {
    RunMode.FAST: ModePolicy(
        mode=RunMode.FAST,
        complexity="low",
        search_depth="basic",
        max_queries=2,
        results_per_query=5,
        top_chunks=8,
        max_iterations=1,
    ),
    RunMode.BALANCED: ModePolicy(
        mode=RunMode.BALANCED,
        complexity="medium",
        search_depth="basic",
        max_queries=2,
        results_per_query=6,
        top_chunks=20,
        max_iterations=2,
    ),
    RunMode.DEEP: ModePolicy(
        mode=RunMode.DEEP,
        complexity="high",
        search_depth="advanced",
        max_queries=3,
        results_per_query=8,
        top_chunks=40,
        max_iterations=3,
    ),
}


def normalize_mode(mode: str | RunMode | None) -> RunMode:
    """Return the canonical mode enum for known UI modes."""
    if isinstance(mode, RunMode):
        return mode
    clean = str(mode or "").strip().casefold()
    for candidate in RunMode:
        if clean == candidate.value.casefold():
            return candidate
    raise ValueError(f"unknown run mode: {mode!r}")


def mode_policy_for(mode: str | RunMode | None) -> ModePolicy:
    """Return a passive policy snapshot for an already-selected UI mode."""
    return MODE_POLICIES[normalize_mode(mode)]


__all__ = [
    "MODE_POLICIES",
    "ModePolicy",
    "RunMode",
    "mode_policy_for",
    "normalize_mode",
]
