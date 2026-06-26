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


@dataclass(frozen=True)
class InitialSubjectBudgetPolicy:
    """Passive future-policy scaffold for initial subject/component budgets."""

    mode_name: str
    max_initial_selected_subjects: int | None
    internal_followups_exempt: bool
    policy_status: str
    mode_exists: bool
    subject_budget_scope: str = "initial_independent_subjects_only"
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_name": self.mode_name,
            "max_initial_selected_subjects": self.max_initial_selected_subjects,
            "internal_followups_exempt": self.internal_followups_exempt,
            "policy_status": self.policy_status,
            "mode_exists": self.mode_exists,
            "subject_budget_scope": self.subject_budget_scope,
            "notes": self.notes,
        }


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

INITIAL_SUBJECT_BUDGET_POLICIES: dict[str, InitialSubjectBudgetPolicy] = {
    "Fast": InitialSubjectBudgetPolicy(
        mode_name="Fast",
        max_initial_selected_subjects=5,
        internal_followups_exempt=True,
        policy_status="planned",
        mode_exists=True,
        notes=(
            "Passive scaffold only; existing Fast query/search/fetch/model caps "
            "are unchanged."
        ),
    ),
    "Balanced": InitialSubjectBudgetPolicy(
        mode_name="Balanced",
        max_initial_selected_subjects=5,
        internal_followups_exempt=True,
        policy_status="planned",
        mode_exists=True,
        notes=(
            "Passive scaffold only; existing Balanced query/search/fetch/model "
            "caps are unchanged."
        ),
    ),
    "Deep": InitialSubjectBudgetPolicy(
        mode_name="Deep",
        max_initial_selected_subjects=None,
        internal_followups_exempt=True,
        policy_status="undecided",
        mode_exists=True,
        notes="No enforced Deep initial-subject cap is decided in this phase.",
    ),
    "Instant": InitialSubjectBudgetPolicy(
        mode_name="Instant",
        max_initial_selected_subjects=None,
        internal_followups_exempt=True,
        policy_status="not_existing_mode_future_note",
        mode_exists=False,
        notes=(
            "Instant is not an existing repo mode; no runtime policy or cap is "
            "added."
        ),
    ),
    "Pro": InitialSubjectBudgetPolicy(
        mode_name="Pro",
        max_initial_selected_subjects=None,
        internal_followups_exempt=True,
        policy_status="not_existing_mode_future_note",
        mode_exists=False,
        notes=(
            "Pro is not an existing repo mode; no runtime policy or cap is added."
        ),
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


def initial_subject_budget_policy_for(
    mode: str | RunMode | None,
) -> InitialSubjectBudgetPolicy:
    """Return passive subject-budget metadata for known modes or future notes."""

    if isinstance(mode, RunMode):
        return INITIAL_SUBJECT_BUDGET_POLICIES[mode.value]
    clean = str(mode or "").strip()
    for candidate in RunMode:
        if clean.casefold() == candidate.value.casefold():
            return INITIAL_SUBJECT_BUDGET_POLICIES[candidate.value]
    for name, policy in INITIAL_SUBJECT_BUDGET_POLICIES.items():
        if clean.casefold() == name.casefold():
            return policy
    raise ValueError(f"unknown run mode or subject-budget note: {mode!r}")


def initial_subject_budget_policy_registry() -> dict[str, dict[str, Any]]:
    """Expose passive subject-budget policy notes without affecting modes."""

    return {
        name: policy.to_dict()
        for name, policy in INITIAL_SUBJECT_BUDGET_POLICIES.items()
    }


__all__ = [
    "INITIAL_SUBJECT_BUDGET_POLICIES",
    "InitialSubjectBudgetPolicy",
    "MODE_POLICIES",
    "ModePolicy",
    "RunMode",
    "initial_subject_budget_policy_for",
    "initial_subject_budget_policy_registry",
    "mode_policy_for",
    "normalize_mode",
]
