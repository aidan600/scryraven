"""Passive planned-vs-observed controller diagnostics.

This module compares a passive RunPlan with facts that already exist in an
execution_trace. It does not route, retrieve, dispatch, retry, gate, persist, or
change orchestration behavior.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.run_plan import PlanDisposition, RunPlan, build_run_plan
from core.task_ledger import TaskLedger, TaskStatus

_CONTROLLER_DIAGNOSTICS_SCHEMA_VERSION = "controller_diagnostics_v1"
_MAX_CONTROLLER_DIAGNOSTIC_STRING_CHARS = 200
_MAX_CONTROLLER_DIAGNOSTIC_SCALAR_ITEMS = 10


class PlannedObservedStatus(str, Enum):
    OBSERVED_STARTED = "observed_started"
    OBSERVED_COMPLETED = "observed_completed"
    OBSERVED_SKIPPED = "observed_skipped"
    OBSERVED_BLOCKED = "observed_blocked"
    OBSERVED_FAILED = "observed_failed"
    MISSING_REQUIRED = "missing_required"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    OPTIONAL_NOT_OBSERVED = "optional_not_observed"
    MAY_RUN_NOT_OBSERVED = "may_run_not_observed"
    SHADOW_NOT_OBSERVED = "shadow_not_observed"
    BLOCKED_BY_MODE = "blocked_by_mode"
    NOT_APPLICABLE = "not_applicable"


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple((str(key), _freeze_value(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return deepcopy(value)


def _thaw_value(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            for item in value
        ):
            return {key: _thaw_value(item) for key, item in value}
        return [_thaw_value(item) for item in value]
    return deepcopy(value)


def _freeze_metadata(
    metadata: Mapping[str, Any] | None,
) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (str(key), _freeze_value(value))
        for key, value in (metadata or {}).items()
    )


def _thaw_metadata(metadata: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
    return {key: _thaw_value(value) for key, value in metadata}


@dataclass(frozen=True)
class ObservedStageFact:
    """One observed stage fact derived from an existing execution_trace."""

    stage_id: str
    module_id: str
    status: TaskStatus
    reason: str | None = None
    metadata: tuple[tuple[str, Any], ...] = ()

    @classmethod
    def build(
        cls,
        *,
        stage_id: str,
        module_id: str,
        status: TaskStatus,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ObservedStageFact:
        return cls(
            stage_id=str(stage_id),
            module_id=str(module_id),
            status=status,
            reason=None if reason is None else str(reason),
            metadata=_freeze_metadata(metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "module_id": self.module_id,
            "status": self.status.value,
            "reason": self.reason,
            "metadata": _thaw_metadata(self.metadata),
        }


@dataclass(frozen=True)
class PlannedObservedStage:
    """Comparison result for one RunPlan stage."""

    stage_id: str
    module_id: str
    disposition: PlanDisposition
    status: PlannedObservedStatus
    observed_status: TaskStatus | None = None
    reason: str | None = None
    failure: bool = False
    metadata: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "module_id": self.module_id,
            "disposition": self.disposition.value,
            "status": self.status.value,
            "observed_status": (
                self.observed_status.value if self.observed_status is not None else None
            ),
            "reason": self.reason,
            "failure": self.failure,
            "metadata": _thaw_metadata(self.metadata),
        }


@dataclass(frozen=True)
class PlannedObservedDiagnostics:
    """Passive comparison summary for a RunPlan and execution_trace."""

    stages: tuple[PlannedObservedStage, ...]
    observed_facts: tuple[ObservedStageFact, ...]

    def status_counts(self) -> dict[str, int]:
        counts = {status.value: 0 for status in PlannedObservedStatus}
        for stage in self.stages:
            counts[stage.status.value] += 1
        return counts

    def failures(self) -> tuple[PlannedObservedStage, ...]:
        return tuple(stage for stage in self.stages if stage.failure)

    def to_dict(self) -> dict[str, Any]:
        failures = self.failures()
        return {
            "stages": [stage.to_dict() for stage in self.stages],
            "observed_facts": [fact.to_dict() for fact in self.observed_facts],
            "status_counts": self.status_counts(),
            "failure_count": len(failures),
            "failures": [stage.to_dict() for stage in failures],
        }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return deepcopy(list(value))
    return []


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_string(
    value: Any,
    *,
    max_chars: int = _MAX_CONTROLLER_DIAGNOSTIC_STRING_CHARS,
) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[: max_chars - 3]}..."


def _compact_scalar_list(
    value: Any,
    *,
    max_items: int = _MAX_CONTROLLER_DIAGNOSTIC_SCALAR_ITEMS,
) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, set)):
        return []
    items = sorted(value, key=str) if isinstance(value, set) else list(value)
    compact: list[Any] = []
    for item in items[:max_items]:
        if isinstance(item, str):
            compact.append(_compact_string(item))
        elif isinstance(item, (int, float, bool)) or item is None:
            compact.append(item)
        else:
            compact.append(_compact_string(item))
    return compact


def _compact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in mapping.items():
        clean_key = _compact_string(key)
        if clean_key is None:
            continue
        if isinstance(value, str):
            compact[clean_key] = _compact_string(value)
        elif isinstance(value, (int, float, bool)) or value is None:
            compact[clean_key] = value
        elif isinstance(value, (list, tuple, set)):
            compact[clean_key] = _compact_scalar_list(value)
        else:
            compact[clean_key] = _compact_string(value)
    return compact


def _selected_metadata(
    trace: Mapping[str, Any],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    return {key: deepcopy(trace[key]) for key in keys if key in trace}


def _context_stage_names(trace: Mapping[str, Any]) -> set[str]:
    context_measurement = _as_mapping(trace.get("context_measurement"))
    stages = _as_mapping(context_measurement.get("stages"))
    return {str(stage_name) for stage_name in stages}


def _provider_role_seen(trace: Mapping[str, Any], role: str) -> bool:
    attempts_by_role = _as_mapping(trace.get("provider_attempts_by_role"))
    if _as_int(attempts_by_role.get(role)) and int(attempts_by_role.get(role) or 0) > 0:
        return True
    for attempt in _as_list(trace.get("provider_diagnostics")):
        if isinstance(attempt, Mapping) and str(attempt.get("provider_role")) == role:
            return True
    return False


def _blocked_reason(reason: Any, blockers: Any = None) -> bool:
    text = str(reason or "")
    if text.startswith("blocked_") or text.startswith("max_iterations"):
        return True
    return bool(_as_list(blockers))


def _route_intent_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    keys = (
        "mode",
        "complexity",
        "intent",
        "report_type",
        "query_type",
        "primary_entity",
        "entities",
        "routing_override_applied",
        "routing_override_reason",
        "router_entity_retry_used",
    )
    if not any(key in trace for key in keys):
        return None
    return ObservedStageFact.build(
        stage_id="route_intent",
        module_id="router",
        status=TaskStatus.COMPLETED,
        reason="routing_metadata_present",
        metadata=_selected_metadata(trace, keys),
    )


def _researcher_queries_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    queries_by_iteration = _as_mapping(trace.get("queries_per_iteration"))
    if not queries_by_iteration:
        return None
    iteration_1 = _as_list(queries_by_iteration.get("1"))
    query_count = sum(len(_as_list(value)) for value in queries_by_iteration.values())
    if query_count <= 0:
        return None
    return ObservedStageFact.build(
        stage_id="researcher_queries",
        module_id="researcher",
        status=TaskStatus.COMPLETED,
        reason="queries_per_iteration_present",
        metadata={
            "iteration_keys": [str(key) for key in queries_by_iteration],
            "iteration_1_query_count": len(iteration_1),
            "query_count": query_count,
        },
    )


def _main_retrieval_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    iterations_run = _as_int(trace.get("iterations_run")) or 0
    pass_providers = _as_list(trace.get("pass_providers"))
    if iterations_run <= 0 and not pass_providers and not _provider_role_seen(
        trace,
        "main_retrieval",
    ):
        return None
    return ObservedStageFact.build(
        stage_id="main_retrieval",
        module_id="retrieval",
        status=TaskStatus.COMPLETED,
        reason="main_retrieval_trace_present",
        metadata={
            "iterations_run": iterations_run,
            "pass_count": len(pass_providers),
            "provider_attempts_by_role": deepcopy(
                _as_mapping(trace.get("provider_attempts_by_role"))
            ),
            "discover_candidate_urls_admitted": deepcopy(
                trace.get("discover_candidate_urls_admitted")
            ),
            "urls_fetched": deepcopy(trace.get("urls_fetched")),
            "total_chunks": deepcopy(trace.get("total_chunks")),
        },
    )


def _weak_corpus_recovery_fact(
    trace: Mapping[str, Any],
) -> ObservedStageFact | None:
    keys = (
        "weak_corpus_recovery_considered",
        "weak_corpus_recovery_used",
        "weak_corpus_recovery_skip_reason",
        "weak_corpus_recovery_queries",
        "weak_corpus_recovery_decision",
        "weak_corpus_recovery_reason",
        "weak_corpus_recovery_blockers",
    )
    if not any(key in trace for key in keys):
        return None
    considered = bool(trace.get("weak_corpus_recovery_considered"))
    used = bool(trace.get("weak_corpus_recovery_used"))
    skip_reason = trace.get("weak_corpus_recovery_skip_reason")
    if not considered and not used:
        return None
    if used:
        status = TaskStatus.COMPLETED
        reason = "weak_corpus_recovery_used"
    elif _blocked_reason(skip_reason):
        status = TaskStatus.BLOCKED
        reason = skip_reason
    else:
        status = TaskStatus.SKIPPED
        reason = skip_reason or "weak_corpus_recovery_not_used"
    return ObservedStageFact.build(
        stage_id="weak_corpus_recovery",
        module_id="weak_corpus_recovery",
        status=status,
        reason=reason,
        metadata=_selected_metadata(trace, keys),
    )


def _source_class_recovery_fact(
    trace: Mapping[str, Any],
) -> ObservedStageFact | None:
    active_keys = (
        "active_source_class_recovery_considered",
        "active_source_class_recovery_eligible",
        "active_source_class_recovery_used",
        "active_source_class_recovery_skip_reason",
        "active_source_class_recovery_blockers",
        "active_source_class_recovery_missing_classes",
        "active_source_class_recovery_queries",
        "active_source_class_recovery_result_count",
        "active_source_class_recovery_new_url_count",
        "active_source_class_recovery_provider_role",
        "active_source_class_recovery_search_depth",
        "active_source_class_recovery_attempt_count",
        "source_class_recovery_recommended",
        "source_class_recovery_shadow_mode",
        "missing_expected_source_classes",
        "source_class_recovery_queries",
        "source_class_recovery_query_count",
    )
    if not any(key in trace for key in active_keys):
        return None
    considered = bool(trace.get("active_source_class_recovery_considered"))
    used = bool(trace.get("active_source_class_recovery_used"))
    eligible = bool(trace.get("active_source_class_recovery_eligible"))
    skip_reason = trace.get("active_source_class_recovery_skip_reason")
    blockers = trace.get("active_source_class_recovery_blockers")
    if used:
        status = TaskStatus.COMPLETED
        reason = "source_class_recovery_used"
    elif considered and eligible:
        status = TaskStatus.STARTED
        reason = "source_class_recovery_eligible_not_used"
    elif considered:
        status = TaskStatus.BLOCKED if _blocked_reason(skip_reason, blockers) else TaskStatus.SKIPPED
        reason = skip_reason or "source_class_recovery_not_used"
    else:
        return None
    return ObservedStageFact.build(
        stage_id="source_class_recovery",
        module_id="source_class_recovery",
        status=status,
        reason=reason,
        metadata=_selected_metadata(trace, active_keys),
    )


def _analyst_review_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    context_stages = _context_stage_names(trace)
    analyst_context_stages = {
        stage
        for stage in context_stages
        if stage.startswith("analyst")
    }
    if bool(trace.get("analyst_model_called")) or analyst_context_stages:
        return ObservedStageFact.build(
            stage_id="analyst_review",
            module_id="analyst",
            status=TaskStatus.COMPLETED,
            reason="analyst_model_observed",
            metadata={
                "analyst_model_called": bool(trace.get("analyst_model_called")),
                "context_stages": sorted(analyst_context_stages),
            },
        )
    if bool(trace.get("analyst_skipped")):
        return ObservedStageFact.build(
            stage_id="analyst_review",
            module_id="analyst",
            status=TaskStatus.SKIPPED,
            reason=trace.get("analyst_skip_reason") or "analyst_skipped",
            metadata=_selected_metadata(
                trace,
                (
                    "analyst_skipped",
                    "analyst_skip_reason",
                    "post_retrieval_fast_path_used",
                    "pre_analyst_gate_signals",
                ),
            ),
        )
    if bool(trace.get("analyst_skipped_after_economist")):
        return ObservedStageFact.build(
            stage_id="analyst_review",
            module_id="analyst",
            status=TaskStatus.SKIPPED,
            reason=(
                trace.get("analyst_after_economist_skip_reason")
                or "analyst_skipped_after_economist"
            ),
            metadata=_selected_metadata(
                trace,
                (
                    "analyst_skipped_after_economist",
                    "analyst_after_economist_skip_reason",
                    "economist_output_used_as_analysis",
                ),
            ),
        )
    return None


def _economist_preflight_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    keys = (
        "economist_ran",
        "economist_preflight_allowed",
        "economist_preflight_block_reason",
        "economist_preflight_missing_entities",
        "economist_safety_status",
        "economist_schema_version",
        "economist_schema_valid",
        "economist_pre_analyst_skip_candidate_shadow",
        "economist_pre_analyst_skip_candidate_gate_reason",
        "economist_output_used_as_analysis",
        "analyst_skipped_after_economist",
    )
    if bool(trace.get("economist_ran")):
        status = TaskStatus.COMPLETED
        reason = "economist_ran"
    elif trace.get("economist_preflight_allowed") is False:
        status = TaskStatus.BLOCKED
        reason = trace.get("economist_preflight_block_reason") or "preflight_blocked"
    elif any(key in trace for key in keys):
        return None
    else:
        return None
    return ObservedStageFact.build(
        stage_id="economist_preflight",
        module_id="economist",
        status=status,
        reason=reason,
        metadata=_selected_metadata(trace, keys),
    )


def _supplemental_retrieval_fact(
    trace: Mapping[str, Any],
) -> ObservedStageFact | None:
    if bool(trace.get("supplemental_ran")) or _provider_role_seen(
        trace,
        "supplemental_search",
    ):
        return ObservedStageFact.build(
            stage_id="supplemental_retrieval",
            module_id="retrieval",
            status=TaskStatus.COMPLETED,
            reason="supplemental_retrieval_observed",
            metadata=_selected_metadata(
                trace,
                (
                    "supplemental_ran",
                    "synth_was_insufficient",
                    "synth_sufficient_first_pass",
                    "synth_sufficient_first_pass_raw",
                    "provider_attempts_by_role",
                ),
            ),
        )
    return None


def _scrutineer_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    if bool(trace.get("scrutineer_ran")) or "scrutineer" in _context_stage_names(trace):
        return ObservedStageFact.build(
            stage_id="scrutineer",
            module_id="scrutineer",
            status=TaskStatus.COMPLETED,
            reason="scrutineer_observed",
            metadata=_selected_metadata(
                trace,
                ("scrutineer_ran", "scrutineer_flag_count"),
            ),
        )
    return None


def _author_fact(trace: Mapping[str, Any]) -> ObservedStageFact | None:
    context_stages = _context_stage_names(trace)
    keys = (
        "author_system_prompt_key",
        "author_quant_content_source",
        "author_received_raw_quant_packet",
        "author_received_economist_framework",
        "author_received_analyst_packet_marker",
        "author_quant_handoff_gate_reason",
        "output_word_count",
        "final_output_preview",
    )
    if not any(key in trace for key in keys) and "author" not in context_stages:
        return None
    return ObservedStageFact.build(
        stage_id="author",
        module_id="author",
        status=TaskStatus.COMPLETED,
        reason="author_output_observed",
        metadata={
            **_selected_metadata(trace, keys),
            "context_stage_present": "author" in context_stages,
        },
    )


def _observed_stage_facts(
    execution_trace: Mapping[str, Any],
) -> tuple[ObservedStageFact, ...]:
    trace = _as_mapping(execution_trace)
    builders = (
        _route_intent_fact,
        _researcher_queries_fact,
        _main_retrieval_fact,
        _weak_corpus_recovery_fact,
        _source_class_recovery_fact,
        _analyst_review_fact,
        _economist_preflight_fact,
        _supplemental_retrieval_fact,
        _scrutineer_fact,
        _author_fact,
    )
    facts: list[ObservedStageFact] = []
    for builder in builders:
        fact = builder(trace)
        if fact is not None:
            facts.append(fact)
    return tuple(facts)


def build_task_ledger_from_trace(
    execution_trace: Mapping[str, Any],
    *,
    run_plan: RunPlan | None = None,
) -> TaskLedger:
    """Build a passive TaskLedger from an already-built execution_trace."""
    ledger = TaskLedger.empty()
    if run_plan is not None:
        for item in run_plan.items:
            ledger = ledger.record_planned(
                task_id=item.stage_id,
                module_id=item.module_id,
                reason=item.reason,
                metadata={
                    "disposition": item.disposition.value,
                    "dependencies": list(item.dependencies),
                },
            )
    for fact in _observed_stage_facts(execution_trace):
        ledger = ledger.record(
            task_id=fact.stage_id,
            module_id=fact.module_id,
            status=fact.status,
            reason=fact.reason,
            metadata=_thaw_metadata(fact.metadata),
        )
    return ledger


def _observed_status_to_planned_status(
    status: TaskStatus,
) -> PlannedObservedStatus:
    if status is TaskStatus.STARTED:
        return PlannedObservedStatus.OBSERVED_STARTED
    if status is TaskStatus.COMPLETED:
        return PlannedObservedStatus.OBSERVED_COMPLETED
    if status is TaskStatus.SKIPPED:
        return PlannedObservedStatus.OBSERVED_SKIPPED
    if status is TaskStatus.BLOCKED:
        return PlannedObservedStatus.OBSERVED_BLOCKED
    if status is TaskStatus.FAILED:
        return PlannedObservedStatus.OBSERVED_FAILED
    return PlannedObservedStatus.OBSERVED_STARTED


def _analyst_completed(stage_results: Mapping[str, PlannedObservedStage]) -> bool:
    analyst = stage_results.get("analyst_review")
    return (
        analyst is not None
        and analyst.status is PlannedObservedStatus.OBSERVED_COMPLETED
    )


def _dependencies_satisfied(
    dependencies: tuple[str, ...],
    stage_results: Mapping[str, PlannedObservedStage],
) -> tuple[bool, list[str]]:
    blocked: list[str] = []
    for dependency in dependencies:
        result = stage_results.get(dependency)
        if result is None or result.status is not PlannedObservedStatus.OBSERVED_COMPLETED:
            blocked.append(dependency)
    return not blocked, blocked


def _absent_status_for_disposition(
    disposition: PlanDisposition,
) -> PlannedObservedStatus:
    if disposition is PlanDisposition.OPTIONAL:
        return PlannedObservedStatus.OPTIONAL_NOT_OBSERVED
    if disposition is PlanDisposition.MAY_RUN:
        return PlannedObservedStatus.MAY_RUN_NOT_OBSERVED
    if disposition is PlanDisposition.SHADOW:
        return PlannedObservedStatus.SHADOW_NOT_OBSERVED
    if disposition is PlanDisposition.BLOCKED_BY_MODE:
        return PlannedObservedStatus.BLOCKED_BY_MODE
    if disposition is PlanDisposition.NOT_APPLICABLE:
        return PlannedObservedStatus.NOT_APPLICABLE
    return PlannedObservedStatus.MISSING_REQUIRED


def compare_run_plan_to_observed_trace(
    run_plan: RunPlan,
    execution_trace: Mapping[str, Any],
) -> PlannedObservedDiagnostics:
    """Compare a passive RunPlan against facts already present in a trace."""
    observed_facts = _observed_stage_facts(execution_trace)
    observed_by_stage = {fact.stage_id: fact for fact in observed_facts}
    stage_results: dict[str, PlannedObservedStage] = {}

    for item in run_plan.items:
        fact = observed_by_stage.get(item.stage_id)
        if fact is not None:
            status = _observed_status_to_planned_status(fact.status)
            stage = PlannedObservedStage(
                stage_id=item.stage_id,
                module_id=item.module_id,
                disposition=item.disposition,
                status=status,
                observed_status=fact.status,
                reason=fact.reason,
                failure=status is PlannedObservedStatus.OBSERVED_FAILED,
                metadata=fact.metadata,
            )
            stage_results[item.stage_id] = stage
            continue

        if item.disposition is PlanDisposition.REQUIRED:
            dependencies_satisfied, blocked_dependencies = _dependencies_satisfied(
                item.dependencies,
                stage_results,
            )
            if item.stage_id == "scrutineer" and not _analyst_completed(stage_results):
                dependencies_satisfied = False
                if "analyst_review" not in blocked_dependencies:
                    blocked_dependencies.append("analyst_review")
            if dependencies_satisfied:
                status = PlannedObservedStatus.MISSING_REQUIRED
                reason = "required_stage_not_observed"
                failure = True
            else:
                status = PlannedObservedStatus.DEPENDENCY_BLOCKED
                reason = "dependency_not_observed"
                failure = False
            metadata = _freeze_metadata(
                {
                    "dependencies": list(item.dependencies),
                    "blocked_dependencies": blocked_dependencies,
                }
            )
        else:
            status = _absent_status_for_disposition(item.disposition)
            reason = status.value
            failure = False
            metadata = _freeze_metadata({"dependencies": list(item.dependencies)})

        stage_results[item.stage_id] = PlannedObservedStage(
            stage_id=item.stage_id,
            module_id=item.module_id,
            disposition=item.disposition,
            status=status,
            observed_status=None,
            reason=reason,
            failure=failure,
            metadata=metadata,
        )

    return PlannedObservedDiagnostics(
        stages=tuple(stage_results[item.stage_id] for item in run_plan.items),
        observed_facts=observed_facts,
    )


def _derive_run_plan_from_trace(execution_trace: Mapping[str, Any]) -> RunPlan:
    return build_run_plan(
        mode=execution_trace.get("mode"),
        routing_metadata={
            "intent": execution_trace.get("intent"),
            "report_type": execution_trace.get("report_type"),
            "query_type": execution_trace.get("query_type"),
        },
    )


def _plan_item_payload(item: Any) -> dict[str, Any]:
    return {
        "stage_id": _compact_string(item.stage_id),
        "module_id": _compact_string(item.module_id),
        "disposition": item.disposition.value,
        "dependencies": _compact_scalar_list(item.dependencies),
    }


def _planned_observed_stage_payload(
    stage: PlannedObservedStage,
) -> dict[str, Any]:
    return {
        "stage_id": _compact_string(stage.stage_id),
        "module_id": _compact_string(stage.module_id),
        "disposition": stage.disposition.value,
        "status": stage.status.value,
        "observed_status": (
            stage.observed_status.value if stage.observed_status is not None else None
        ),
        "reason": _compact_string(stage.reason),
        "failure": stage.failure,
    }


def _source_class_recovery_not_activated(trace: Mapping[str, Any]) -> bool:
    active_queries = _as_list(trace.get("active_source_class_recovery_queries"))
    query_only_insufficient_posture = bool(
        active_queries
        and trace.get("authority_lifecycle_insufficient_partial_posture_explicit")
        is True
        and trace.get("authority_lifecycle_weak_corpus_may_own_path") is True
    )
    return (
        trace.get("active_source_class_recovery_used") is False
        and (_as_int(trace.get("active_source_class_recovery_attempt_count")) or 0) == 0
        and trace.get("active_source_class_recovery_provider_role") in (None, "")
        and (not active_queries or query_only_insufficient_posture)
        and (_as_int(trace.get("active_source_class_recovery_result_count")) or 0) == 0
        and (_as_int(trace.get("active_source_class_recovery_new_url_count")) or 0)
        == 0
    )


def _controller_stage_payload(
    stage: PlannedObservedStage,
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _planned_observed_stage_payload(stage)
    if (
        stage.stage_id == "source_class_recovery"
        and stage.disposition is PlanDisposition.MAY_RUN
        and _source_class_recovery_not_activated(trace)
    ):
        payload["status"] = PlannedObservedStatus.MAY_RUN_NOT_OBSERVED.value
        payload["observed_status"] = None
        payload["reason"] = PlannedObservedStatus.MAY_RUN_NOT_OBSERVED.value
        payload["failure"] = False
    return payload


def _stage_payload_status_counts(stages: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status.value: 0 for status in PlannedObservedStatus}
    for stage in stages:
        status = stage.get("status")
        if status in counts:
            counts[str(status)] += 1
    return counts


def _observed_summary_from_stage_payloads(
    stages: list[dict[str, Any]],
) -> dict[str, Any]:
    observed = [stage for stage in stages if stage.get("observed_status") is not None]
    status_counts = {status.value: 0 for status in TaskStatus}
    for stage in observed:
        status = str(stage.get("observed_status"))
        if status in status_counts:
            status_counts[status] += 1
    return {
        "observed_stage_count": len(observed),
        "observed_stage_ids": _compact_scalar_list(
            [stage.get("stage_id") for stage in observed]
        ),
        "observed_status_counts": status_counts,
    }


def build_controller_diagnostics_payload(
    execution_trace: Mapping[str, Any],
    *,
    run_plan: RunPlan | None = None,
    task_ledger: TaskLedger | None = None,
    include_stage_items: bool = True,
) -> dict[str, Any]:
    """Build a compact passive controller diagnostics payload.

    The returned payload is post-hoc diagnostic data only. Runtime wiring may
    nest the compact payload under ``execution_trace["controller_diagnostics"]``,
    but it has no authority and must not be used for prompts or control flow.
    """
    trace = _as_mapping(execution_trace)
    plan = run_plan or _derive_run_plan_from_trace(trace)
    ledger = task_ledger or build_task_ledger_from_trace(trace, run_plan=plan)
    diagnostics = compare_run_plan_to_observed_trace(plan, trace)
    stage_payloads = [
        _controller_stage_payload(stage, trace)
        for stage in diagnostics.stages
    ]
    failures = [stage for stage in stage_payloads if stage["failure"]]

    return {
        "schema_version": _CONTROLLER_DIAGNOSTICS_SCHEMA_VERSION,
        "passive_only": True,
        "diagnostic_only": True,
        "authority": "none",
        "source": "posthoc_execution_trace",
        "mode_policy": _compact_mapping(plan.mode_policy.to_dict()),
        "run_plan": {
            "routing_metadata": _compact_mapping(dict(plan.routing_metadata)),
            "stage_count": len(plan.items),
            "disposition_counts": dict(
                Counter(item.disposition.value for item in plan.items)
            ),
            "items": (
                [_plan_item_payload(item) for item in plan.items]
                if include_stage_items
                else []
            ),
        },
        "task_ledger": {
            "record_count": len(ledger.records),
            "status_counts": ledger.status_counts(),
        },
        "planned_vs_observed": {
            "status_counts": _stage_payload_status_counts(stage_payloads),
            "failure_count": len(failures),
            "stages": (
                stage_payloads if include_stage_items else []
            ),
            "failures": failures[:_MAX_CONTROLLER_DIAGNOSTIC_SCALAR_ITEMS],
        },
        "observed_summary": _observed_summary_from_stage_payloads(stage_payloads),
    }


__all__ = [
    "ObservedStageFact",
    "PlannedObservedDiagnostics",
    "PlannedObservedStage",
    "PlannedObservedStatus",
    "build_controller_diagnostics_payload",
    "build_task_ledger_from_trace",
    "compare_run_plan_to_observed_trace",
]
