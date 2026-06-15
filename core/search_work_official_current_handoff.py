"""Official/current acquisition handoff from SearchWork shadow projections.

The builder here exposes source-obligation-driven acquisition intent to older
source-class recovery vocabulary. It does not generate query text, select
providers, change search depth, run retrieval, or affect final-answer behavior.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence

OFFICIAL_CURRENT_HANDOFF_SCHEMA_VERSION = (
    "search_work_official_current_handoff_ag96d0_v1"
)
OFFICIAL_CURRENT_HANDOFF_TRACE_KEY = "search_work_official_current_handoff"

_ACQUISITION_NEED_KINDS = (
    "official_current",
    "legal_current_primary",
    "canonical_documentation",
    "source_bound_numeric",
)
_SOURCE_CLASS_BY_KIND = {
    "official_current": ("official_current_rules",),
    "legal_current_primary": (
        "legal_or_regulatory_text",
        "current_primary_or_official",
    ),
    "canonical_documentation": ("primary_source_documents",),
    "source_bound_numeric": ("sourced_numeric_values",),
}
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
_LOWER_TIER_SOURCE_MARKERS = frozenset(
    {
        "community",
        "context",
        "forum",
        "lower_tier",
        "secondary",
        "secondary_only",
        "social",
        "tertiary",
        "weak",
    }
)


def build_search_work_official_current_handoff(
    search_work_shadow_projection: Mapping[str, Any],
    *,
    existing_blockers: Sequence[Any] = (),
    observed_material: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a JSON-safe official/current acquisition handoff.

    The input may be either an AG-96C10 shadow-lane projection or the nested
    AG-96C9 QueryPlan-work shadow projection. Observed material is diagnostic
    only; lower-tier material is recorded as rejected and cannot satisfy the
    required source-obligation needs emitted by this handoff.
    """

    query_plan_shadow = _extract_query_plan_work_shadow(search_work_shadow_projection)
    acquisition_needs = _acquisition_needs(query_plan_shadow)
    provider_jobs_by_component = _mapping(
        query_plan_shadow.get("provider_jobs_by_component")
    )
    stop_posture = _stop_posture(query_plan_shadow)
    blockers = _string_list(existing_blockers)

    needs_by_kind = {
        kind: [
            _handoff_need(
                need,
                kind=kind,
                provider_jobs_by_component=provider_jobs_by_component,
                stop_posture=stop_posture,
            )
            for need in acquisition_needs.get(kind, ())
        ]
        for kind in _ACQUISITION_NEED_KINDS
    }
    required_source_classes = _required_source_classes(needs_by_kind)
    observed_summary = _observed_material_summary(
        observed_material,
        required_source_classes=required_source_classes,
    )
    unsatisfied_required_classes = list(required_source_classes)
    escalation_blocked = bool(blockers)
    source_class_recommendation = _source_class_recovery_recommendation(
        needs_by_kind=needs_by_kind,
        required_source_classes=required_source_classes,
        blockers=blockers,
    )

    handoff = {
        "schema_version": OFFICIAL_CURRENT_HANDOFF_SCHEMA_VERSION,
        "trace_key": OFFICIAL_CURRENT_HANDOFF_TRACE_KEY,
        "owner": "SearchWorkPlan.OfficialCurrentAcquisitionHandoff",
        "derived_from": query_plan_shadow.get("trace_key")
        or "query_plan_work_shadow_projection",
        "source_owner": query_plan_shadow.get("owner"),
        "source_construction_id": query_plan_shadow.get("source_construction_id"),
        "source_obligation_driven": True,
        "mode_specific_official_executor": False,
        "provider_selected": False,
        "query_text_generated": False,
        "search_executed": False,
        "retrieval_executed": False,
        "final_answer_behavior_changed": False,
        "query_plan_behavior_changed": False,
        "query_admission_changed": False,
        "query_order_changed": False,
        "search_depth_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "official_current_needs": needs_by_kind["official_current"],
        "legal_current_primary_needs": needs_by_kind["legal_current_primary"],
        "canonical_documentation_needs": needs_by_kind[
            "canonical_documentation"
        ],
        "source_bound_numeric_needs": needs_by_kind["source_bound_numeric"],
        "required_source_classes": list(required_source_classes),
        "unsatisfied_required_source_classes": unsatisfied_required_classes,
        "component_ids": _component_ids(needs_by_kind),
        "source_obligation_ids": _source_obligation_ids(needs_by_kind),
        "strictness": _strictness_summary(needs_by_kind),
        "provider_job_kinds": _provider_job_kinds(needs_by_kind),
        "provider_job_kinds_are_hints_only": True,
        "source_class_recovery_handoff": source_class_recommendation,
        "recovery_handoff_escalation_allowed": bool(
            required_source_classes and not escalation_blocked
        ),
        "recovery_handoff_blocked": escalation_blocked,
        "recovery_handoff_blockers": blockers,
        "stop_fail_qualify_posture_if_unsatisfied": stop_posture,
        "observed_material_summary": observed_summary,
        "lower_tier_material_satisfies_required_official_current": False,
        "subordinate_recovery_ownership": {
            "preserve_existing_blockers": True,
            "bypass_search_judgment": False,
            "bypass_sufficiency_judgment": False,
            "lower_tier_bridge_material_can_satisfy": False,
        },
        "validation": {
            "query_plan_work_shadow_projection_present": bool(query_plan_shadow),
            "contains_executable_query_text": False,
            "executes_provider_calls": False,
            "executes_search": False,
            "executes_retrieval": False,
        },
        "metadata": {
            "phase": "AG-96D0",
            "safe_structured_inputs_only": True,
            "fast_official_lane_compatibility_retained": True,
        },
    }
    return _json_safe(handoff)


def source_class_recovery_recommendation_from_handoff(
    handoff: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the bounded source-class recommendation embedded in a handoff."""

    recommendation = _mapping(handoff.get("source_class_recovery_handoff"))
    return _json_safe(recommendation)


def _extract_query_plan_work_shadow(source: Mapping[str, Any]) -> dict[str, Any]:
    source_map = _mapping(source)
    nested = _mapping(source_map.get("query_plan_work_shadow_projection"))
    if nested:
        return nested
    if source_map.get("trace_key") == "query_plan_work_shadow_projection":
        return source_map
    projections = _mapping(source_map.get("projections"))
    nested = _mapping(projections.get("query_plan_work_shadow_projection"))
    if nested:
        return nested
    return source_map if "acquisition_needs" in source_map else {}


def _acquisition_needs(
    query_plan_shadow: Mapping[str, Any],
) -> dict[str, tuple[Mapping[str, Any], ...]]:
    needs = _mapping(query_plan_shadow.get("acquisition_needs"))
    return {
        kind: _sequence_of_mappings(needs.get(kind))
        for kind in _ACQUISITION_NEED_KINDS
    }


def _handoff_need(
    need: Mapping[str, Any],
    *,
    kind: str,
    provider_jobs_by_component: Mapping[str, Any],
    stop_posture: Mapping[str, Any],
) -> dict[str, Any]:
    component_id = _clean_token(need.get("component_id")) or "component:unknown"
    obligation_id = _clean_token(need.get("obligation_id"))
    strictness = _clean_token(need.get("strictness")) or "required"
    provider_job_hints = [
        _without_empty(
            {
                "work_id": _clean_token(job.get("work_id")),
                "work_kind": _clean_token(job.get("work_kind")),
                "source_obligation_ids": _text_sequence(
                    job.get("source_obligation_ids")
                ),
                "executes_runtime_work": False,
                "job_hint_only": True,
            }
        )
        for job in _sequence_of_mappings(provider_jobs_by_component.get(component_id))
        if not obligation_id
        or obligation_id in set(_text_sequence(job.get("source_obligation_ids")))
    ]
    return _without_empty(
        {
            "need_kind": kind,
            "component_id": component_id,
            "obligation_id": obligation_id,
            "strictness": strictness,
            "required_source_classes": list(_SOURCE_CLASS_BY_KIND[kind]),
            "provider_job_hints": provider_job_hints,
            "stop_fail_qualify_posture_if_unsatisfied": dict(stop_posture),
            "source_obligation_driven": True,
            "satisfied": False,
        }
    )


def _required_source_classes(
    needs_by_kind: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[str, ...]:
    out: list[str] = []
    for needs in needs_by_kind.values():
        for need in needs:
            if _clean_token(need.get("strictness")) != "required":
                continue
            for source_class in _text_sequence(need.get("required_source_classes")):
                _append_unique(out, source_class)
    return tuple(out)


def _source_class_recovery_recommendation(
    *,
    needs_by_kind: Mapping[str, Sequence[Mapping[str, Any]]],
    required_source_classes: Sequence[str],
    blockers: Sequence[str],
) -> dict[str, Any]:
    trigger_fields = [
        f"search_work_shadow:{kind}"
        for kind, needs in needs_by_kind.items()
        if needs
    ]
    recommended = bool(required_source_classes and not blockers)
    reason = None
    if required_source_classes:
        reason = "search_work_official_current_handoff:" + ",".join(
            required_source_classes
        )
    return {
        "source_class_recovery_recommended": recommended,
        "source_class_recovery_shadow_mode": True,
        "source_obligation_driven": True,
        "missing_expected_source_classes": list(required_source_classes),
        "source_class_recovery_reason": reason,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": trigger_fields,
        "provider_job_kinds_are_hints_only": True,
        "provider_selected": False,
        "query_text_generated": False,
        "search_executed": False,
        "retrieval_executed": False,
        "handoff_blocked_by_existing_recovery_ownership": bool(blockers),
        "handoff_blockers": list(blockers),
    }


def _stop_posture(query_plan_shadow: Mapping[str, Any]) -> dict[str, Any]:
    posture = _mapping(query_plan_shadow.get("stop_and_follow_up_posture"))
    outcomes: list[str] = []
    conditions: list[str] = []
    for item in _sequence_of_mappings(posture.get("stop_conditions")):
        condition = _clean_token(item.get("condition"))
        outcome = _clean_token(item.get("outcome"))
        if condition:
            _append_unique(conditions, condition)
        if outcome:
            _append_unique(outcomes, outcome)
    if not outcomes:
        outcomes.append("qualify")
    return {
        "obligations_unsatisfied": True,
        "conditions": conditions,
        "outcomes": outcomes,
        "posture": _dominant_stop_posture(outcomes),
    }


def _dominant_stop_posture(outcomes: Sequence[str]) -> str:
    for candidate in ("fail_closed", "refuse", "stop", "qualify"):
        if candidate in outcomes:
            return candidate
    return outcomes[0] if outcomes else "qualify"


def _observed_material_summary(
    observed_material: Sequence[Mapping[str, Any]],
    *,
    required_source_classes: Sequence[str],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for item in _sequence_of_mappings(observed_material):
        source_class = _clean_token(item.get("source_class"))
        source_tier = _clean_token(item.get("source_tier"))
        material_id = _clean_token(item.get("material_id") or item.get("id"))
        lower_tier = source_class in _LOWER_TIER_SOURCE_MARKERS or (
            source_tier in _LOWER_TIER_SOURCE_MARKERS
        )
        records.append(
            _without_empty(
                {
                    "material_id": material_id,
                    "source_class": source_class,
                    "source_tier": source_tier,
                    "required_source_classes": list(required_source_classes),
                    "satisfies_required_official_current": False,
                    "rejection_reason": (
                        "lower_tier_or_secondary_not_satisfying_official_current_obligation"
                        if lower_tier
                        else "handoff_does_not_accept_material_as_satisfaction"
                    ),
                }
            )
        )
    return {
        "material_considered": len(records),
        "satisfied_required_source_classes": [],
        "rejected_material": records,
    }


def _component_ids(
    needs_by_kind: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[str]:
    out: list[str] = []
    for needs in needs_by_kind.values():
        for need in needs:
            _append_unique(out, _clean_token(need.get("component_id")))
    return out


def _source_obligation_ids(
    needs_by_kind: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[str]:
    out: list[str] = []
    for needs in needs_by_kind.values():
        for need in needs:
            _append_unique(out, _clean_token(need.get("obligation_id")))
    return out


def _strictness_summary(
    needs_by_kind: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for kind, needs in needs_by_kind.items():
        values: list[str] = []
        for need in needs:
            _append_unique(values, _clean_token(need.get("strictness")))
        out[kind] = values
    return out


def _provider_job_kinds(
    needs_by_kind: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[str]:
    out: list[str] = []
    for needs in needs_by_kind.values():
        for need in needs:
            for job in _sequence_of_mappings(need.get("provider_job_hints")):
                _append_unique(out, _clean_token(job.get("work_kind")))
    return out


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


def _string_list(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str) or not isinstance(value, Sequence):
        return out
    for item in value:
        _append_unique(out, _clean_token(item))
    return out


def _append_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


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
    if depth > 6:
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
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:160]]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "OFFICIAL_CURRENT_HANDOFF_SCHEMA_VERSION",
    "OFFICIAL_CURRENT_HANDOFF_TRACE_KEY",
    "build_search_work_official_current_handoff",
    "source_class_recovery_recommendation_from_handoff",
]
