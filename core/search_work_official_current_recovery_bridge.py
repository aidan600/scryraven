"""Recovery-compatible bridge for SearchWork official/current handoff.

This module converts AG-96D0/D1 official-current handoff projections into the
source-class recovery vocabulary older compatibility surfaces understand. It is
execution-free: it does not generate query text, select providers, run search or
retrieval, or alter final-answer behavior.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence

SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_SCHEMA_VERSION = (
    "search_work_official_current_recovery_bridge_ag96d2_v1"
)
SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_TRACE_KEY = (
    "search_work_official_current_recovery_bridge"
)

_HANDOFF_TRACE_KEY = "search_work_official_current_handoff"
_NEED_FIELDS = (
    "official_current_needs",
    "legal_current_primary_needs",
    "canonical_documentation_needs",
    "source_bound_numeric_needs",
)
_LOWER_TIER_SOURCE_MARKERS = frozenset(
    {
        "community",
        "community_forum",
        "forum",
        "lower_tier",
        "secondary",
        "secondary_only",
        "social",
        "social_media",
        "tertiary",
        "weak",
    }
)
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
_EXECUTION_FLAGS = {
    "recovery_execution_authorized": False,
    "provider_selected": False,
    "query_text_generated": False,
    "search_executed": False,
    "retrieval_executed": False,
    "final_answer_behavior_changed": False,
}


def build_search_work_official_current_recovery_bridge(
    projection: Mapping[str, Any] | None = None,
    *,
    search_work_official_current_handoff: Mapping[str, Any] | None = None,
    existing_recovery_recommendation: Mapping[str, Any] | None = None,
    existing_blockers: Sequence[Any] = (),
    observed_material_diagnostics: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a bounded source-class recovery bridge from SearchWork handoff.

    ``projection`` may be either an AG-96D1 shadow-lane projection containing
    ``search_work_official_current_handoff`` or the AG-96D0 handoff projection
    itself. Existing blockers remain authoritative and prevent recovery
    recommendation while keeping missing source-class visibility.
    """

    handoff = _extract_handoff(
        projection,
        explicit_handoff=search_work_official_current_handoff,
    )
    existing_recommendation = _safe_mapping(existing_recovery_recommendation)
    blockers = _blockers(
        explicit_blockers=existing_blockers,
        existing_recommendation=existing_recommendation,
        handoff=handoff,
    )
    missing_source_classes = _missing_source_classes(
        handoff=handoff,
        existing_recommendation=existing_recommendation,
    )
    trigger_fields = _trigger_fields(
        handoff=handoff,
        existing_recommendation=existing_recommendation,
    )
    considered = bool(handoff)
    eligible = bool(considered and missing_source_classes and not blockers)
    used = eligible
    reason = _recovery_reason(
        existing_recommendation=existing_recommendation,
        missing_source_classes=missing_source_classes,
    )
    recommendation_summary = _existing_recommendation_summary(
        existing_recommendation,
        missing_source_classes=missing_source_classes,
        trigger_fields=trigger_fields,
    )

    result = {
        "schema_version": SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_SCHEMA_VERSION,
        "trace_key": SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_TRACE_KEY,
        "owner": "SearchWorkPlan.OfficialCurrentRecoveryBridge",
        "derived_from": handoff.get("trace_key") or _HANDOFF_TRACE_KEY,
        "bridge_considered": considered,
        "bridge_eligible": eligible,
        "bridge_used": used,
        "bridge_skip_reason": _skip_reason(
            considered=considered,
            missing_source_classes=missing_source_classes,
            blockers=blockers,
        ),
        "source_obligation_driven": True,
        "missing_expected_source_classes": missing_source_classes,
        "source_class_recovery_recommended": bool(eligible),
        "source_class_recovery_shadow_mode": True,
        "source_class_recovery_reason": reason,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": trigger_fields,
        "handoff_blockers": blockers,
        "existing_recovery_recommendation": recommendation_summary,
        "observed_material_diagnostics": _observed_material_summary(
            observed_material_diagnostics,
            required_source_classes=missing_source_classes,
        ),
        "lower_tier_material_satisfies_required_official_current": False,
        "subordinate_recovery_ownership": {
            "grant_search_judgment_authority": False,
            "bypass_search_judgment": False,
            "bypass_sufficiency_judgment": False,
            "lower_tier_bridge_material_can_satisfy": False,
            "existing_blockers_remain_authoritative": True,
        },
        "behavior_boundary": {
            "query_plan_behavior_changed": False,
            "provider_routing_changed": False,
            "search_depth_changed": False,
            "prompt_behavior_changed": False,
            "citation_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "fast_official_lane_runtime_behavior_changed": False,
        },
        "metadata": {
            "phase": "AG-96D2",
            "safe_structured_inputs_only": True,
            "fast_official_lane_compatibility_retained": True,
            "mode_specific_official_executor_introduced": False,
        },
        **_EXECUTION_FLAGS,
    }
    return _json_safe(result)


def _extract_handoff(
    projection: Mapping[str, Any] | None,
    *,
    explicit_handoff: Mapping[str, Any] | None,
) -> dict[str, Any]:
    explicit = _safe_mapping(explicit_handoff)
    if explicit:
        return explicit
    source = _safe_mapping(projection)
    if not source:
        return {}
    nested = _safe_mapping(source.get(_HANDOFF_TRACE_KEY))
    if nested:
        return nested
    projections = _safe_mapping(source.get("projections"))
    nested = _safe_mapping(projections.get(_HANDOFF_TRACE_KEY))
    if nested:
        return nested
    if source.get("trace_key") == _HANDOFF_TRACE_KEY or any(
        field in source for field in _NEED_FIELDS
    ):
        return source
    return {}


def _missing_source_classes(
    *,
    handoff: Mapping[str, Any],
    existing_recommendation: Mapping[str, Any],
) -> list[str]:
    out: list[str] = []
    for source in (
        existing_recommendation.get("missing_expected_source_classes"),
        handoff.get("required_source_classes"),
        handoff.get("unsatisfied_required_source_classes"),
        _safe_mapping(handoff.get("source_class_recovery_handoff")).get(
            "missing_expected_source_classes"
        ),
    ):
        for item in _text_sequence(source):
            _append_unique(out, item)
    for field in _NEED_FIELDS:
        for need in _sequence_of_mappings(handoff.get(field)):
            for item in _text_sequence(need.get("required_source_classes")):
                _append_unique(out, item)
    return out


def _trigger_fields(
    *,
    handoff: Mapping[str, Any],
    existing_recommendation: Mapping[str, Any],
) -> list[str]:
    out: list[str] = []
    embedded = _safe_mapping(handoff.get("source_class_recovery_handoff"))
    for source in (
        existing_recommendation.get("source_class_recovery_trigger_fields"),
        embedded.get("source_class_recovery_trigger_fields"),
    ):
        for item in _text_sequence(source):
            _append_unique(out, item)
    _append_unique(out, _HANDOFF_TRACE_KEY)
    _append_unique(out, SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_TRACE_KEY)
    _append_unique(out, "search_work_handoff:source_obligation_driven")
    for obligation_id in _text_sequence(handoff.get("source_obligation_ids")):
        _append_unique(out, f"source_obligation:{obligation_id}")
    return out


def _recovery_reason(
    *,
    existing_recommendation: Mapping[str, Any],
    missing_source_classes: Sequence[str],
) -> str | None:
    existing_reason = _clean_text(
        existing_recommendation.get("source_class_recovery_reason"),
        limit=300,
    )
    if existing_reason:
        return existing_reason
    if not missing_source_classes:
        return None
    return "search_work_official_current_recovery_bridge:" + ",".join(
        missing_source_classes
    )


def _blockers(
    *,
    explicit_blockers: Sequence[Any],
    existing_recommendation: Mapping[str, Any],
    handoff: Mapping[str, Any],
) -> list[str]:
    out: list[str] = []
    for source in (
        explicit_blockers,
        existing_recommendation.get("active_source_class_recovery_blockers"),
        existing_recommendation.get("source_class_recovery_candidate_v2_blockers"),
        existing_recommendation.get("handoff_blockers"),
        existing_recommendation.get("bridge_blockers"),
        handoff.get("recovery_handoff_blockers"),
        _safe_mapping(handoff.get("source_class_recovery_handoff")).get(
            "handoff_blockers"
        ),
    ):
        for item in _text_sequence(source):
            _append_unique(out, item)
    return out


def _existing_recommendation_summary(
    recommendation: Mapping[str, Any],
    *,
    missing_source_classes: Sequence[str],
    trigger_fields: Sequence[str],
) -> dict[str, Any]:
    if not recommendation:
        return {}
    return _without_empty(
        {
            "source_class_recovery_recommended": bool(
                recommendation.get("source_class_recovery_recommended")
            ),
            "source_class_recovery_shadow_mode": bool(
                recommendation.get("source_class_recovery_shadow_mode")
            ),
            "source_class_recovery_reason": _clean_text(
                recommendation.get("source_class_recovery_reason"),
                limit=300,
            ),
            "missing_expected_source_classes": list(missing_source_classes),
            "source_class_recovery_trigger_fields": list(trigger_fields),
            "source_class_recovery_query_count": 0,
            "source_class_recovery_queries_preserved": False,
            "query_text_omitted_by_bridge_boundary": True,
        }
    )


def _observed_material_summary(
    observed_material: Sequence[Mapping[str, Any]],
    *,
    required_source_classes: Sequence[str],
) -> dict[str, Any]:
    rejected: list[dict[str, Any]] = []
    for item in _sequence_of_mappings(observed_material):
        source_class = _clean_token(item.get("source_class"))
        source_tier = _clean_token(item.get("source_tier"))
        material_id = _clean_token(item.get("material_id") or item.get("id"))
        lower_tier = (
            source_class in _LOWER_TIER_SOURCE_MARKERS
            or source_tier in _LOWER_TIER_SOURCE_MARKERS
        )
        rejected.append(
            _without_empty(
                {
                    "material_id": material_id,
                    "source_class": source_class,
                    "source_tier": source_tier,
                    "required_source_classes": list(required_source_classes),
                    "satisfies_required_official_current": False,
                    "diagnostic_only": True,
                    "rejection_reason": (
                        "lower_tier_or_secondary_not_satisfying_official_current_obligation"
                        if lower_tier
                        else "bridge_does_not_accept_observed_material_as_satisfaction"
                    ),
                }
            )
        )
    return {
        "material_considered": len(rejected),
        "satisfied_required_source_classes": [],
        "rejected_material": rejected,
    }


def _skip_reason(
    *,
    considered: bool,
    missing_source_classes: Sequence[str],
    blockers: Sequence[str],
) -> str | None:
    if not considered:
        return "handoff_missing"
    if blockers:
        return "existing_runtime_blocker"
    if not missing_source_classes:
        return "no_missing_official_current_source_classes"
    return None


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = _clean_token(key)
        if not key_text or _is_sensitive_key(key_text):
            continue
        out[key_text] = _json_safe(item)
    return out


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text_sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return ()
    return tuple(text for item in value if (text := _clean_token(item)))


def _append_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 7:
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
    "SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_SCHEMA_VERSION",
    "SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_TRACE_KEY",
    "build_search_work_official_current_recovery_bridge",
]
