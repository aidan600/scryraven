"""Passive run-plan checklist contracts.

RunPlan is descriptive scaffolding only. It mirrors what a run may contain
based on already-known mode and routing metadata, and it is not a runtime
policy, retry policy, or source of truth for orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.mode_policy import ModePolicy, RunMode, mode_policy_for


class PlanDisposition(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    SHADOW = "shadow"
    MAY_RUN = "may_run"
    BLOCKED_BY_MODE = "blocked_by_mode"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class PlanItem:
    """One passive checklist item for a possible stage."""

    stage_id: str
    module_id: str
    disposition: PlanDisposition
    reason: str
    dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "module_id": self.module_id,
            "disposition": self.disposition.value,
            "reason": self.reason,
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class RunPlan:
    """A passive checklist snapshot for diagnostics and future migration work."""

    mode_policy: ModePolicy
    items: tuple[PlanItem, ...]
    routing_metadata: tuple[tuple[str, str], ...] = ()

    def item(self, stage_id: str) -> PlanItem:
        for plan_item in self.items:
            if plan_item.stage_id == stage_id:
                return plan_item
        raise KeyError(stage_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_policy": self.mode_policy.to_dict(),
            "routing_metadata": dict(self.routing_metadata),
            "items": [item.to_dict() for item in self.items],
        }


def _routing_metadata_items(
    routing_metadata: Mapping[str, Any] | None,
) -> tuple[tuple[str, str], ...]:
    raw = routing_metadata or {}
    keys = ("intent", "report_type", "query_type")
    return tuple(
        (key, str(raw[key]))
        for key in keys
        if raw.get(key) not in (None, "")
    )


def _is_quantitative_route(routing_metadata: Mapping[str, Any] | None) -> bool:
    raw = routing_metadata or {}
    query_type = str(raw.get("query_type") or "").strip().lower()
    report_type = str(raw.get("report_type") or "").strip().lower()
    return query_type in {"comparison", "quantitative_comparison"} or report_type in {
        "quantitative_comparison",
        "comparative_analysis",
        "benchmark",
        "cost_analysis",
        "unit_economics",
    }


def build_run_plan(
    *,
    mode: str | RunMode | None,
    routing_metadata: Mapping[str, Any] | None = None,
    mode_policy: ModePolicy | None = None,
) -> RunPlan:
    """Build a passive checklist from existing mode and routing metadata."""
    policy = mode_policy or mode_policy_for(mode)
    is_fast = policy.mode is RunMode.FAST
    is_deep = policy.mode is RunMode.DEEP
    is_quantitative = _is_quantitative_route(routing_metadata)

    analyst_disposition = (
        PlanDisposition.BLOCKED_BY_MODE if is_fast else PlanDisposition.REQUIRED
    )
    source_recovery_disposition = PlanDisposition.MAY_RUN
    weak_recovery_disposition = (
        PlanDisposition.BLOCKED_BY_MODE if is_fast else PlanDisposition.MAY_RUN
    )
    supplemental_disposition = (
        PlanDisposition.BLOCKED_BY_MODE if is_fast else PlanDisposition.OPTIONAL
    )
    scrutineer_disposition = (
        PlanDisposition.REQUIRED if is_deep else PlanDisposition.BLOCKED_BY_MODE
    )
    economist_disposition = (
        PlanDisposition.SHADOW
        if is_quantitative
        else PlanDisposition.NOT_APPLICABLE
    )

    items = (
        PlanItem(
            stage_id="route_intent",
            module_id="router",
            disposition=PlanDisposition.REQUIRED,
            reason="router metadata is produced before mode-derived execution settings",
        ),
        PlanItem(
            stage_id="researcher_queries",
            module_id="researcher",
            disposition=PlanDisposition.REQUIRED,
            reason="research queries are part of the existing first retrieval pass",
            dependencies=("route_intent",),
        ),
        PlanItem(
            stage_id="main_retrieval",
            module_id="retrieval",
            disposition=PlanDisposition.REQUIRED,
            reason="first-pass retrieval is already required for all modes",
            dependencies=("researcher_queries",),
        ),
        PlanItem(
            stage_id="weak_corpus_recovery",
            module_id="weak_corpus_recovery",
            disposition=weak_recovery_disposition,
            reason=(
                "Fast has no extra iteration budget"
                if is_fast
                else "Balanced and Deep may use existing weak-corpus recovery"
            ),
            dependencies=("main_retrieval",),
        ),
        PlanItem(
            stage_id="source_class_recovery",
            module_id="source_class_recovery",
            disposition=source_recovery_disposition,
            reason=(
                "Fast source-class recovery remains conditional on existing lifecycle eligibility and budget compatibility"
                if is_fast
                else "source-class recovery may run when existing lifecycle facts allow it"
            ),
            dependencies=("main_retrieval",),
        ),
        PlanItem(
            stage_id="analyst_review",
            module_id="analyst",
            disposition=analyst_disposition,
            reason=(
                "Fast skips deep analysis by existing mode behavior"
                if is_fast
                else "Balanced and Deep retain Analyst review unless existing gates skip it"
            ),
            dependencies=("main_retrieval",),
        ),
        PlanItem(
            stage_id="economist_preflight",
            module_id="economist",
            disposition=economist_disposition,
            reason=(
                "quantitative routes can produce shadow Economist telemetry"
                if economist_disposition is PlanDisposition.SHADOW
                else "not a quantitative route in this passive checklist"
            ),
            dependencies=("main_retrieval",),
        ),
        PlanItem(
            stage_id="supplemental_retrieval",
            module_id="retrieval",
            disposition=supplemental_disposition,
            reason=(
                "Fast has no supplemental retrieval pass"
                if is_fast
                else "supplemental retrieval remains optional and synthesis-gated"
            ),
            dependencies=("analyst_review",),
        ),
        PlanItem(
            stage_id="scrutineer",
            module_id="scrutineer",
            disposition=scrutineer_disposition,
            reason=(
                "Deep keeps the existing Scrutineer path"
                if is_deep
                else "Scrutineer is Deep-only"
            ),
            dependencies=("analyst_review",),
        ),
        PlanItem(
            stage_id="author",
            module_id="author",
            disposition=PlanDisposition.REQUIRED,
            reason="Author remains the final response stage",
            dependencies=("main_retrieval",),
        ),
    )

    return RunPlan(
        mode_policy=policy,
        items=items,
        routing_metadata=_routing_metadata_items(routing_metadata),
    )


__all__ = [
    "PlanDisposition",
    "PlanItem",
    "RunPlan",
    "build_run_plan",
]
