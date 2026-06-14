"""QueryPlan-facing shadow work projection derived from SearchWorkPlan.

This adapter exposes work hints adjacent to QueryPlan without creating query
text, admitting query candidates, choosing providers, changing retrieval, or
mutating RunKernel directly.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence

QUERY_PLAN_WORK_SHADOW_SCHEMA_VERSION = "query_plan_work_shadow_ag96c9_v1"
QUERY_PLAN_WORK_SHADOW_TRACE_KEY = "query_plan_work_shadow_projection"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)
_ACQUISITION_NEED_KINDS = (
    "official_current",
    "legal_current_primary",
    "canonical_documentation",
    "source_bound_numeric",
)


def build_query_plan_work_shadow_projection(
    search_work_plan_source: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a QueryPlan-adjacent shadow projection from SearchWorkPlan state."""

    plan, source_projection = _extract_search_work_plan(search_work_plan_source)
    components = _sequence_of_mappings(plan.get("components"))
    provider_jobs = _sequence_of_mappings(plan.get("provider_jobs"))
    quant_work_units = _sequence_of_mappings(plan.get("quant_work_units"))
    synthesis_jobs = _sequence_of_mappings(plan.get("synthesis_jobs"))
    audit_jobs = _sequence_of_mappings(plan.get("audit_jobs"))
    stop_conditions = _sequence_of_mappings(plan.get("stop_conditions"))
    follow_up = _mapping(plan.get("follow_up_authority"))

    obligations_by_component = _source_obligations_by_component(components)
    provider_jobs_by_component = _jobs_by_component(
        provider_jobs,
        id_key="provider_job_id",
        kind_key="job_kind",
        extra_keys=("source_obligation_ids",),
        executes_key="executes_search",
    )
    quant_by_component = _jobs_by_component(
        quant_work_units,
        id_key="quant_unit_id",
        kind_key="target_metric",
        extra_keys=("source_bound_values_needed",),
        executes_key="executes_calculations",
    )
    synthesis_by_component = _jobs_by_component(
        synthesis_jobs,
        id_key="synthesis_job_id",
        kind_key="synthesis_scope",
        extra_keys=(),
        executes_key="owns_source_gap_search_remediation_authority",
    )
    audit_by_component = _jobs_by_component(
        audit_jobs,
        id_key="audit_job_id",
        kind_key="audit_scope",
        extra_keys=("remediation_permission",),
        executes_key="open_ended_loop",
    )
    acquisition_needs = _acquisition_needs(obligations_by_component)
    component_summaries = _component_summaries(
        components,
        obligations_by_component,
        provider_jobs_by_component,
        quant_by_component,
        synthesis_by_component,
        audit_by_component,
    )

    projection = {
        "schema_version": QUERY_PLAN_WORK_SHADOW_SCHEMA_VERSION,
        "trace_key": QUERY_PLAN_WORK_SHADOW_TRACE_KEY,
        "owner": "SearchWorkPlan.QueryPlanWorkShadowAdapter",
        "derived_from": "RunKernel.SearchWorkPlan",
        "source_owner": source_projection.get("owner") or "RunKernel.SearchWorkPlan",
        "source_schema_version": plan.get("schema_version")
        or source_projection.get("schema_version"),
        "source_construction_id": _source_construction_id(plan, source_projection),
        "shadow_only": True,
        "runtime_consumed_by_query_plan": False,
        "query_plan_behavior_changed": False,
        "query_text_generated": False,
        "query_admission_changed": False,
        "provider_search_behavior_changed": False,
        "query_order_changed": False,
        "search_depth_changed": False,
        "retrieval_behavior_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "final_answer_behavior_changed": False,
        "components": component_summaries,
        "source_obligations_by_component": obligations_by_component,
        "provider_jobs_by_component": provider_jobs_by_component,
        "acquisition_needs": acquisition_needs,
        "work_counts": {
            "component_count": len(components),
            "source_obligation_count": sum(
                len(items) for items in obligations_by_component.values()
            ),
            "provider_job_count": len(provider_jobs),
            "quant_work_unit_count": len(quant_work_units),
            "synthesis_job_count": len(synthesis_jobs),
            "audit_job_count": len(audit_jobs),
            "official_current_need_count": len(acquisition_needs["official_current"]),
            "legal_current_primary_need_count": len(
                acquisition_needs["legal_current_primary"]
            ),
            "canonical_documentation_need_count": len(
                acquisition_needs["canonical_documentation"]
            ),
            "source_bound_numeric_need_count": len(
                acquisition_needs["source_bound_numeric"]
            ),
        },
        "stop_and_follow_up_posture": {
            "follow_up_permission": _clean_token(follow_up.get("permission")),
            "executor_authority_allowed": bool(
                follow_up.get("executor_authority_allowed", False)
            ),
            "stop_condition_count": len(stop_conditions),
            "stop_conditions": [
                _without_empty(
                    {
                        "condition": _clean_token(item.get("condition")),
                        "outcome": _clean_token(item.get("outcome")),
                        "component_id": _clean_token(item.get("component_id")),
                    }
                )
                for item in stop_conditions
            ],
        },
        "candidate_work_groups": _candidate_work_groups(
            component_summaries,
            obligations_by_component,
            provider_jobs_by_component,
            quant_by_component,
            synthesis_by_component,
            audit_by_component,
        ),
        "validation": {
            "ok": bool(plan),
            "source_projection_present": bool(source_projection),
            "contains_executable_query_text": False,
            "admits_query_candidates": False,
            "executes_provider_calls": False,
        },
        "metadata": {
            "phase": "AG-96C9",
            "safe_structured_inputs_only": True,
        },
    }
    return _json_safe(projection)


def _extract_search_work_plan(
    source: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_map = _mapping(source)
    plan = _mapping(source_map.get("search_work_plan"))
    projection = _mapping(source_map.get("search_work_plan_projection"))
    if not plan and "components" in source_map:
        plan = source_map
    if not projection and source_map.get("owner") == "RunKernel.SearchWorkPlan":
        projection = source_map
    if not projection:
        projection = {
            "owner": "RunKernel.SearchWorkPlan",
            "schema_version": plan.get("schema_version"),
        }
    return plan, projection


def _source_obligations_by_component(
    components: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for component in components:
        component_id = _clean_token(component.get("component_id")) or "component:unknown"
        obligations: list[dict[str, Any]] = []
        for item in _sequence_of_mappings(component.get("source_obligations")):
            obligations.append(
                _without_empty(
                    {
                        "obligation_id": _clean_token(item.get("obligation_id")),
                        "kind": _clean_token(item.get("kind")),
                        "strictness": _clean_token(item.get("strictness")),
                        "currentness_required": bool(
                            item.get("currentness_requirement")
                        ),
                        "source_constraint_present": bool(item.get("search_constraint")),
                        "satisfaction_rule_present": bool(
                            item.get("satisfaction_rule")
                        ),
                        "official_current_is_source_obligation": bool(
                            item.get("official_current_is_source_obligation")
                        ),
                    }
                )
            )
        out[component_id] = obligations
    return out


def _jobs_by_component(
    jobs: Sequence[Mapping[str, Any]],
    *,
    id_key: str,
    kind_key: str,
    extra_keys: Sequence[str],
    executes_key: str,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        summary = _without_empty(
            {
                "work_id": _clean_token(job.get(id_key)),
                "work_kind": _clean_token(job.get(kind_key)),
                "executes_runtime_work": bool(job.get(executes_key, False)),
            }
        )
        for key in extra_keys:
            value = job.get(key)
            if isinstance(value, Sequence) and not isinstance(value, str):
                summary[key] = [_clean_token(item) for item in value if _clean_token(item)]
            else:
                text = _clean_token(value)
                if text:
                    summary[key] = text
        for component_id in _text_sequence(job.get("component_ids")):
            out.setdefault(component_id, []).append(summary)
    return out


def _acquisition_needs(
    obligations_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {kind: [] for kind in _ACQUISITION_NEED_KINDS}
    for component_id, obligations in obligations_by_component.items():
        for obligation in obligations:
            kind = _clean_token(obligation.get("kind"))
            if kind not in out:
                continue
            out[kind].append(
                _without_empty(
                    {
                        "component_id": _clean_token(component_id),
                        "obligation_id": _clean_token(obligation.get("obligation_id")),
                        "strictness": _clean_token(obligation.get("strictness")),
                        "shadow_hint_only": True,
                    }
                )
            )
    return out


def _component_summaries(
    components: Sequence[Mapping[str, Any]],
    obligations_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    provider_jobs_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    quant_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    synthesis_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    audit_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for component in components:
        component_id = _clean_token(component.get("component_id")) or "component:unknown"
        obligations = obligations_by_component.get(component_id, ())
        summaries.append(
            {
                "component_id": component_id,
                "mode_depth_allowance": _clean_token(
                    component.get("mode_depth_allowance")
                ),
                "source_obligation_count": len(obligations),
                "required_source_obligation_count": sum(
                    1
                    for item in obligations
                    if item.get("strictness") == "required"
                ),
                "provider_job_count": len(provider_jobs_by_component.get(component_id, ())),
                "quant_work_count": len(quant_by_component.get(component_id, ())),
                "synthesis_work_count": len(synthesis_by_component.get(component_id, ())),
                "audit_work_count": len(audit_by_component.get(component_id, ())),
                "stop_condition_count": len(
                    _sequence_of_mappings(component.get("stop_conditions"))
                ),
            }
        )
    return summaries


def _candidate_work_groups(
    component_summaries: Sequence[Mapping[str, Any]],
    obligations_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    provider_jobs_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    quant_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    synthesis_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
    audit_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for component in component_summaries:
        component_id = _clean_token(component.get("component_id")) or "component:unknown"
        groups.append(
            {
                "group_id": f"component:{component_id}",
                "component_id": component_id,
                "source_obligation_ids": [
                    item["obligation_id"]
                    for item in obligations_by_component.get(component_id, ())
                    if item.get("obligation_id")
                ],
                "provider_work_ids": [
                    item["work_id"]
                    for item in provider_jobs_by_component.get(component_id, ())
                    if item.get("work_id")
                ],
                "quant_work_ids": [
                    item["work_id"]
                    for item in quant_by_component.get(component_id, ())
                    if item.get("work_id")
                ],
                "synthesis_work_ids": [
                    item["work_id"]
                    for item in synthesis_by_component.get(component_id, ())
                    if item.get("work_id")
                ],
                "audit_work_ids": [
                    item["work_id"]
                    for item in audit_by_component.get(component_id, ())
                    if item.get("work_id")
                ],
                "contains_executable_query_text": False,
                "admits_query_candidates": False,
            }
        )
    return groups


def _source_construction_id(
    plan: Mapping[str, Any],
    source_projection: Mapping[str, Any],
) -> str | None:
    metadata = _mapping(plan.get("metadata"))
    return _clean_token(
        source_projection.get("construction_id") or metadata.get("construction_id")
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(text for item in value if (text := _clean_token(item)))


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=100)
            if not key_text or _is_sensitive_key(key_text):
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "QUERY_PLAN_WORK_SHADOW_SCHEMA_VERSION",
    "QUERY_PLAN_WORK_SHADOW_TRACE_KEY",
    "build_query_plan_work_shadow_projection",
]
