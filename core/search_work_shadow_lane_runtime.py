"""Consolidated SearchWork shadow lane after RunAuthority contract synthesis.

The lane is a bounded projection runner. It constructs RunKernel-owned
SearchWorkPlan shadow state through the existing AG-96C7/C8 seam, then derives
the AG-96C9 QueryPlan-work shadow projection from that state. It does not
generate query text, admit queries, schedule providers, call retrieval, assemble
prompts, or alter final-answer/citation behavior.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Sequence

from core.run_kernel import RunKernel
from core.search_work_official_current_handoff import (
    OFFICIAL_CURRENT_HANDOFF_TRACE_KEY,
    build_search_work_official_current_handoff,
)
from core.search_work_plan_query_plan_shadow import (
    QUERY_PLAN_WORK_SHADOW_TRACE_KEY,
    build_query_plan_work_shadow_projection,
)
from core.search_work_plan_shadow_runtime import (
    RuntimeShadowSearchWorkPlanInput,
    observe_runtime_shadow_search_work_plan_construction,
)

SEARCH_WORK_SHADOW_LANE_SCHEMA_VERSION = "search_work_shadow_lane_ag96c10_v1"
SEARCH_WORK_SHADOW_LANE_TRACE_KEY = "search_work_shadow_lane_projection"

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


def run_search_work_shadow_lane(
    *,
    run_kernel: RunKernel,
    run_contract_projection: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None = None,
    requested_mode: str | None = None,
    selected_depth: str | None = None,
    current_date_ref: str | Mapping[str, Any] | None = None,
    safe_user_domain_hints: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run SearchWork shadow construction and QueryPlan-work projection.

    The caller supplies safe post-contract runtime facts. This helper owns the
    shadow construction/projection semantics so the orchestrator remains a
    pass-through coordinator.
    """

    lane_metadata = _safe_mapping(metadata)
    action = run_kernel.authorize_search_work_plan_construction(
        inputs={
            "run_contract_id": _clean_token(
                run_contract_projection.get("contract_id")
            ),
            "shadow_lane": SEARCH_WORK_SHADOW_LANE_TRACE_KEY,
            "shadow_only": True,
            "query_plan_behavior_changed": False,
            "provider_search_behavior_changed": False,
            **lane_metadata,
        }
    )
    observation = observe_runtime_shadow_search_work_plan_construction(
        action,
        RuntimeShadowSearchWorkPlanInput(
            run_contract_projection=run_contract_projection,
            route_projection=route_projection,
            requested_mode=requested_mode,
            selected_depth=selected_depth,
            current_date_ref=current_date_ref,
            safe_user_domain_hints=safe_user_domain_hints,
            metadata={
                "lane": SEARCH_WORK_SHADOW_LANE_TRACE_KEY,
                "phase": "AG-96C10",
                **lane_metadata,
            },
        ),
    )
    state = run_kernel.reduce(observation)
    search_work_plan_projection = dict(state.search_work_plan_projection)
    query_plan_work_shadow_projection = build_query_plan_work_shadow_projection(
        {
            "search_work_plan": state.search_work_plan,
            "search_work_plan_projection": search_work_plan_projection,
        }
    )
    search_work_official_current_handoff = (
        build_search_work_official_current_handoff(query_plan_work_shadow_projection)
    )
    lane_projection = _lane_projection(
        search_work_plan_projection=search_work_plan_projection,
        query_plan_work_shadow_projection=query_plan_work_shadow_projection,
        search_work_official_current_handoff=search_work_official_current_handoff,
        action_ref={
            "action_id": action.action_id,
            "stage": action.stage,
            "action_type": action.action_type.value,
        },
        metadata={
            "phase": "AG-96C10",
            "safe_structured_inputs_only": True,
            **lane_metadata,
        },
    )
    run_kernel.state.projections[SEARCH_WORK_SHADOW_LANE_TRACE_KEY] = lane_projection
    return lane_projection


def _lane_projection(
    *,
    search_work_plan_projection: Mapping[str, Any],
    query_plan_work_shadow_projection: Mapping[str, Any],
    search_work_official_current_handoff: Mapping[str, Any],
    action_ref: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    projection = {
        "schema_version": SEARCH_WORK_SHADOW_LANE_SCHEMA_VERSION,
        "trace_key": SEARCH_WORK_SHADOW_LANE_TRACE_KEY,
        "owner": "RunKernel.SearchWorkShadowLane",
        "derived_from": "RunAuthorityContract",
        "shadow_lane_ran": True,
        "shadow_only": True,
        "search_work_plan_projection_present": bool(search_work_plan_projection),
        "query_plan_work_shadow_projection_present": bool(
            query_plan_work_shadow_projection
        ),
        "search_work_official_current_handoff_present": bool(
            search_work_official_current_handoff
        ),
        "query_plan_work_shadow_trace_key": QUERY_PLAN_WORK_SHADOW_TRACE_KEY,
        "search_work_official_current_handoff_trace_key": (
            OFFICIAL_CURRENT_HANDOFF_TRACE_KEY
        ),
        "official_current_handoff_source_obligation_driven": bool(
            search_work_official_current_handoff.get("source_obligation_driven")
        ),
        "official_current_handoff_mode_specific_official_executor": bool(
            search_work_official_current_handoff.get(
                "mode_specific_official_executor"
            )
        ),
        "official_current_handoff_provider_selected": bool(
            search_work_official_current_handoff.get("provider_selected")
        ),
        "official_current_handoff_query_text_generated": bool(
            search_work_official_current_handoff.get("query_text_generated")
        ),
        "official_current_handoff_search_executed": bool(
            search_work_official_current_handoff.get("search_executed")
        ),
        "official_current_handoff_retrieval_executed": bool(
            search_work_official_current_handoff.get("retrieval_executed")
        ),
        "official_current_handoff_final_answer_behavior_changed": bool(
            search_work_official_current_handoff.get(
                "final_answer_behavior_changed"
            )
        ),
        "official_current_handoff_need_counts": {
            "official_current": len(
                _sequence_of_mappings(
                    search_work_official_current_handoff.get(
                        "official_current_needs"
                    )
                )
            ),
            "legal_current_primary": len(
                _sequence_of_mappings(
                    search_work_official_current_handoff.get(
                        "legal_current_primary_needs"
                    )
                )
            ),
            "canonical_documentation": len(
                _sequence_of_mappings(
                    search_work_official_current_handoff.get(
                        "canonical_documentation_needs"
                    )
                )
            ),
            "source_bound_numeric": len(
                _sequence_of_mappings(
                    search_work_official_current_handoff.get(
                        "source_bound_numeric_needs"
                    )
                )
            ),
        },
        "search_work_plan_runtime_consumed": False,
        "runtime_consumed_by_query_plan": False,
        "query_plan_behavior_changed": False,
        "query_text_generated": False,
        "query_admission_changed": False,
        "query_order_changed": False,
        "provider_search_behavior_changed": False,
        "search_depth_changed": False,
        "retrieval_behavior_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "final_answer_behavior_changed": False,
        "search_work_plan_projection": search_work_plan_projection,
        "query_plan_work_shadow_projection": query_plan_work_shadow_projection,
        "search_work_official_current_handoff": (
            search_work_official_current_handoff
        ),
        "action_ref": action_ref,
        "metadata": metadata,
    }
    return _safe_mapping(projection)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _json_safe(dict(value or {}))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 7:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=100)
            if not key_text:
                continue
            normalized = key_text.casefold()
            if normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS:
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


__all__ = [
    "SEARCH_WORK_SHADOW_LANE_SCHEMA_VERSION",
    "SEARCH_WORK_SHADOW_LANE_TRACE_KEY",
    "run_search_work_shadow_lane",
]
