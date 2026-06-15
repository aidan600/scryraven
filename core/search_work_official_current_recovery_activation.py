"""Gated SearchWork official/current recovery recommendation activation.

This helper merges AG-96D1/D2 SearchWork official/current bridge visibility into
the existing source-class recovery recommendation shape. It is execution-free:
it does not generate queries, select providers, run search/retrieval, assemble
prompts, or alter final-answer/citation behavior.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from core.search_work_official_current_recovery_bridge import (
    SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_TRACE_KEY,
    build_search_work_official_current_recovery_bridge,
)

SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY = (
    "search_work_official_current_recovery_activation"
)
SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_SCHEMA_VERSION = (
    "search_work_official_current_recovery_activation_ag96d3_v1"
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


def activate_search_work_official_current_recovery_recommendation(
    *,
    recommendation: Mapping[str, Any] | None,
    search_work_lane_projection: Mapping[str, Any] | None = None,
    search_work_official_current_handoff: Mapping[str, Any] | None = None,
    search_work_official_current_recovery_bridge: Mapping[str, Any] | None = None,
    existing_blockers: Iterable[Any] = (),
    recovery_lifecycle_allowed: bool = True,
) -> dict[str, Any]:
    """Merge eligible SearchWork official/current bridge visibility.

    Existing recommendation fields are preserved. Missing expected source
    classes and trigger fields are appended. Recovery query fields are copied
    from the existing recommendation and are never generated or mutated here.
    """

    base = _safe_mapping(recommendation)
    bridge = _bridge_from_inputs(
        search_work_lane_projection=search_work_lane_projection,
        search_work_official_current_handoff=search_work_official_current_handoff,
        search_work_official_current_recovery_bridge=(
            search_work_official_current_recovery_bridge
        ),
        existing_recovery_recommendation=base,
        existing_blockers=existing_blockers,
    )
    missing_from_bridge = _string_list(bridge.get("missing_expected_source_classes"))
    bridge_present = bool(bridge.get("bridge_considered"))
    if not bridge_present:
        return base
    blockers = _append_strings(
        _string_list(existing_blockers),
        _string_list(bridge.get("handoff_blockers")),
        _string_list(bridge.get("bridge_blockers")),
    )
    bridge_eligible = bool(bridge.get("bridge_eligible"))
    activation_eligible = bool(
        bridge_present
        and bridge_eligible
        and missing_from_bridge
        and not blockers
        and recovery_lifecycle_allowed
    )

    out = dict(base)
    out["missing_expected_source_classes"] = _append_strings(
        _string_list(base.get("missing_expected_source_classes")),
        missing_from_bridge,
    )
    out["source_class_recovery_trigger_fields"] = _append_strings(
        _string_list(base.get("source_class_recovery_trigger_fields")),
        _string_list(bridge.get("source_class_recovery_trigger_fields")),
        (
            "search_work_official_current_recovery_activation",
            "search_work_source_obligation_recovery",
        ),
    )
    if activation_eligible:
        out["source_class_recovery_recommended"] = True
        out.setdefault("source_class_recovery_shadow_mode", True)
        out["source_obligation_driven"] = True
        if not _clean_text(out.get("source_class_recovery_reason"), limit=300):
            out["source_class_recovery_reason"] = _clean_text(
                bridge.get("source_class_recovery_reason"),
                limit=300,
            ) or "search_work_official_current_recovery_activation"
    else:
        out["source_class_recovery_recommended"] = bool(
            base.get("source_class_recovery_recommended")
        )
        if bridge_present:
            out["source_obligation_driven"] = bool(base.get("source_obligation_driven"))
        if not out["source_class_recovery_recommended"] and not base.get(
            "source_class_recovery_reason"
        ):
            out["source_class_recovery_reason"] = None

    queries = _string_list(base.get("source_class_recovery_queries"))
    if "source_class_recovery_queries" in base:
        out["source_class_recovery_queries"] = queries
    if "source_class_recovery_query_count" in base:
        out["source_class_recovery_query_count"] = len(queries)

    trace = _activation_trace(
        bridge=bridge,
        activation_eligible=activation_eligible,
        recovery_lifecycle_allowed=recovery_lifecycle_allowed,
        blockers=blockers,
        query_count=len(queries),
    )
    out[SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY] = trace
    return _safe_mapping(out)


def _bridge_from_inputs(
    *,
    search_work_lane_projection: Mapping[str, Any] | None,
    search_work_official_current_handoff: Mapping[str, Any] | None,
    search_work_official_current_recovery_bridge: Mapping[str, Any] | None,
    existing_recovery_recommendation: Mapping[str, Any],
    existing_blockers: Iterable[Any],
) -> dict[str, Any]:
    explicit_bridge = _safe_mapping(search_work_official_current_recovery_bridge)
    if explicit_bridge:
        return explicit_bridge
    if not (
        isinstance(search_work_lane_projection, Mapping)
        or isinstance(search_work_official_current_handoff, Mapping)
    ):
        return {}
    return build_search_work_official_current_recovery_bridge(
        search_work_lane_projection,
        search_work_official_current_handoff=search_work_official_current_handoff,
        existing_recovery_recommendation=existing_recovery_recommendation,
        existing_blockers=tuple(existing_blockers or ()),
    )


def _activation_trace(
    *,
    bridge: Mapping[str, Any],
    activation_eligible: bool,
    recovery_lifecycle_allowed: bool,
    blockers: Sequence[str],
    query_count: int,
) -> dict[str, Any]:
    considered = bool(bridge.get("bridge_considered"))
    missing = _string_list(bridge.get("missing_expected_source_classes"))
    return _safe_mapping(
        {
            "schema_version": (
                SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_SCHEMA_VERSION
            ),
            "trace_key": SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY,
            "bridge_trace_key": SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_BRIDGE_TRACE_KEY,
            "activation_considered": considered,
            "activation_eligible": activation_eligible,
            "activation_used": activation_eligible,
            "activation_skip_reason": _activation_skip_reason(
                considered=considered,
                bridge_eligible=bool(bridge.get("bridge_eligible")),
                missing=missing,
                blockers=blockers,
                recovery_lifecycle_allowed=recovery_lifecycle_allowed,
            ),
            "missing_expected_source_classes": missing,
            "source_class_recovery_trigger_fields": _string_list(
                bridge.get("source_class_recovery_trigger_fields")
            ),
            "blockers": list(blockers),
            "source_obligation_driven": bool(activation_eligible),
            "source_class_recovery_queries_unchanged": True,
            "source_class_recovery_query_count": query_count,
            "provider_selected": False,
            "query_text_generated": False,
            "search_executed": False,
            "retrieval_executed": False,
            "prompt_behavior_changed": False,
            "citation_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "fast_official_lane_runtime_behavior_changed": False,
        }
    )


def _activation_skip_reason(
    *,
    considered: bool,
    bridge_eligible: bool,
    missing: Sequence[str],
    blockers: Sequence[str],
    recovery_lifecycle_allowed: bool,
) -> str | None:
    if not considered:
        return "search_work_bridge_missing"
    if blockers:
        return "existing_runtime_blocker"
    if not recovery_lifecycle_allowed:
        return "recovery_lifecycle_not_allowed"
    if not missing:
        return "no_missing_official_current_source_classes"
    if not bridge_eligible:
        return "bridge_not_eligible"
    return None


def _append_strings(*sources: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for item in _string_list(source):
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def _string_list(value: Any) -> list[str]:
    if value is None or isinstance(value, str):
        return []
    try:
        items = tuple(value)
    except TypeError:
        return []
    out: list[str] = []
    for item in items:
        text = _clean_text(item, limit=220)
        if text:
            out.append(text)
    return out


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = _clean_token(key, limit=120)
        if not key_text or _is_sensitive_key(key_text):
            continue
        out[key_text] = _safe_value(item)
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:120]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:120]]
    return _clean_text(value, limit=300)


def _clean_text(value: Any, *, limit: int) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_SCHEMA_VERSION",
    "SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY",
    "activate_search_work_official_current_recovery_recommendation",
]
