"""Offline proof for additive per-component SearchOS transition visibility.

Test path/node id: tests/test_searchos_per_component_product_transition_projection_01.py
Proof class: PRODUCT-supporting structural proof.
Validation bucket: phase_focus.
Surface guarded: bounded SearchOS causal projection and packet privacy.
High-custody or closed-this-phase surface: SearchOS runtime authority is closed.
Runtime/product path guarded: deterministic projection fixture only; no live path.
Expected cost: five sub-second deterministic tests.
Promotion posture: remain phase_focus; not a permanent lane sentinel.
Demotion/retirement condition: retire when the bounded projection is replaced
or these component-transition facts move to a canonical durable test owner.
Why not fast_pr: phase-detail correlation and privacy proof are too narrow for
ordinary PR sentinel scope.

This file exercises only the existing bounded causal projection from
deterministic canonical-shaped readiness records; it makes no provider or model
calls and cannot participate in runtime decisions.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping

from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_OWNER,
    SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
    SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION,
)
from core.searchos_slice_a_product_runtime import (
    build_bounded_searchos_n1_causal_projection,
)

RUN_ID = "offline-transition-run"
REQUEST_ID = "offline-transition-request"
PRIVATE_CANARY = "SEARCHOS_TRANSITION_PRIVATE_CANARY_MUST_NOT_SERIALIZE"
PRIVATE_URL = "https://private.example.invalid/should-not-serialize"


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _component_digest(component: str) -> str:
    return _digest({"component": component, "contract_revision": 1})


def _slot_ref(component: str) -> dict[str, Any]:
    component_id = f"component-{component.lower()}"
    component_digest = _component_digest(component)
    obligation_id = f"obligation-{component.lower()}"
    obligation_digest = _digest(
        {"obligation": obligation_id, "component_digest": component_digest}
    )
    return {
        "slot_id": f"slot-{component.lower()}",
        "slot_digest": _digest({"slot": component}),
        "component_id": component_id,
        "source_obligation_id": obligation_id,
        "component_ref": {
            "component_id": component_id,
            "component_revision": "revision-1",
            "component_digest": component_digest,
        },
        "source_obligation_ref": {
            "source_obligation_id": obligation_id,
            "source_obligation_digest": obligation_digest,
        },
    }


def _safe_handoff(component: str) -> dict[str, str]:
    digest = _digest({"handoff": component})
    return {
        "semantic_handoff_id": f"searchos-semantic-handoff:{digest[:24]}",
        "semantic_handoff_digest": digest,
    }


def _safe_custody(component: str) -> dict[str, Any]:
    return {
        "read_custody_material_id": f"searchos-read-custody:{_digest(component)[:24]}",
        "read_custody_material_digest": _digest(
            {"custody": component, "version": 1}
        ),
        "bounded_text_digest": _digest(
            {"bounded_material": component, "version": 1}
        ),
        "normalized_url": PRIVATE_URL,
        "read_content": PRIVATE_CANARY,
    }


def _slot_record(
    component: str,
    *,
    admitted: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    slot_ref = _slot_ref(component)
    component_digest = str(slot_ref["component_ref"]["component_digest"])
    query_plan_digest = _digest(
        {"query_plan": component}
    )
    candidate_state_digest = _digest(
        {"candidate_state": component}
    )
    candidate_window_digest = _digest(
        {"candidate_window": component}
    )
    full_option_digest = _digest(
        {"candidate_options": component}
    )
    handoff = _safe_handoff(component)
    history: list[dict[str, Any]] = [
        {
            "event": "candidate_window_exposed",
            "candidate_use_window_ref": {
                "candidate_use_window_digest": candidate_window_digest,
                "full_eligible_option_digest": full_option_digest,
                "window_ordinal": 1,
            },
            "normalized_url": PRIVATE_URL,
        },
        {
            "event": "judgment_decided",
            "action": "REQUEST_READ_PAGE",
            "reason": PRIVATE_CANARY,
            "title": PRIVATE_CANARY,
        },
    ]
    if admitted:
        history.append(
            {
                "event": "judgment_decided",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "reason": PRIVATE_CANARY,
            }
        )
        posture = "semantically_handed_off"
        reason = "read_custody_selected_for_semantic_evaluation"
        custody_refs = [_safe_custody(component)]
        recorded_handoff = {
            **handoff,
            "slot_ref": deepcopy(slot_ref),
            "schema_version": SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
        }
        case_ref = {
            "role": "component_analyst",
            "component_digest": component_digest,
        }
        outcome = {
            "semantic_handoff_ref": dict(handoff),
            "component_analyst_case_ref": dict(case_ref),
            "semantic_admission_outcome_ref": {
                "component_analyst_case_ref": dict(case_ref),
                "component_coverage_ref": {"coverage_state": "satisfied"},
            },
            "semantic_admission_status": "admitted",
            "searchos_handoff_material_consumed": True,
        }
    else:
        history.append(
            {
                "event": "stale_or_invalid",
                "reason": f"candidate_packet_stale:{PRIVATE_CANARY}",
            }
        )
        posture = "stale_or_invalid"
        reason = f"candidate_packet_stale:{PRIVATE_CANARY}"
        custody_refs = []
        recorded_handoff = None
        outcome = {}

    record: dict[str, Any] = {
        "slot_ref": slot_ref,
        "requirement_posture": "required",
        "support_kind": "official_current",
        "latest_judgment_posture": posture,
        "latest_judgment_reason": reason,
        "judgment_call_count": 2,
        "action_history": history,
        "candidate_state_ref": {
            "candidate_state_id": f"searchos-state:{candidate_state_digest[:24]}",
            "candidate_state_digest": candidate_state_digest,
            "zero_result_discover_wave_ref": {"zero_useful_result": False},
            "authorized_query": PRIVATE_CANARY,
        },
        "current_query_plan_item_refs": [
            {
                "query_plan_item_id": f"query-plan-item:{component.lower()}",
                "query_plan_item_digest": query_plan_digest,
                "authorized_query": PRIVATE_CANARY,
            }
        ],
        "custody_refs": custody_refs,
        "semantic_handoff_ref": dict(handoff) if admitted else {},
        "recorded_searchos_semantic_handoff_ref": recorded_handoff or {},
        "slice_a_ready": admitted,
    }
    if admitted:
        record["component_analyst_case_ref"] = dict(case_ref)
    return record, outcome


def _projection(
    *,
    admitted_components: frozenset[str],
    processing_order: tuple[str, str] = ("A", "B"),
) -> dict[str, Any]:
    records_by_component: dict[str, dict[str, Any]] = {}
    outcomes_by_component: dict[str, dict[str, Any]] = {}
    for component in processing_order:
        record, outcome = _slot_record(
            component,
            admitted=component in admitted_components,
        )
        records_by_component[component] = record
        outcomes_by_component[component] = outcome

    # Readiness order is the canonical accepted component order. The loop above
    # intentionally models a reversed physical processing order without using
    # that order to assign logical component identity.
    slot_records = [records_by_component[component] for component in ("A", "B")]
    readiness_core = {
        "schema_version": SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "required_slot_count": 2,
        "optional_slot_count": 0,
        "all_required_slots_slice_a_ready": len(admitted_components) == 2,
        "slot_records": slot_records,
    }
    readiness_digest = _digest(readiness_core)
    readiness = {
        **readiness_core,
        "readiness_projection_id": f"searchos-readiness:{readiness_digest[:24]}",
        "readiness_projection_digest": readiness_digest,
        "replay_identity": f"searchos-readiness:{readiness_digest}",
    }
    return {
        "schema_version": "searchos_slice_a_product_runtime_v1",
        "owner": SEARCHOS_OWNER,
        "slot_postures": {
            str(record["slot_ref"]["slot_id"]): record["latest_judgment_posture"]
            for record in slot_records
        },
        "semantic_outcomes_by_slot": {
            str(record["slot_ref"]["slot_id"]): outcomes_by_component[component]
            for component, record in zip(("A", "B"), slot_records)
        },
        "readiness_projection_ref": {
            "readiness_projection_id": readiness["readiness_projection_id"],
            "readiness_projection_digest": readiness["readiness_projection_digest"],
        },
        "readiness_projection": readiness,
    }


def _projected_by_component(projection: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(slot["component_digest"]): dict(slot)
        for slot in projection["slots"]
    }


def test_divergence_fixture_exposes_component_local_transition_boundary() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_projection(admitted_components=frozenset({"A"})),
        expected_run_id=RUN_ID,
        expected_request_id=REQUEST_ID,
    )
    assert projection is not None
    by_component = _projected_by_component(projection)
    component_a = by_component[_component_digest("A")]
    component_b = by_component[_component_digest("B")]

    assert component_a["component_ordinal"] == 1
    assert component_b["component_ordinal"] == 2
    assert component_a["query_plan_item_count"] == 1
    assert component_b["query_plan_item_count"] == 1
    assert component_a["candidate_state_digest"] == _digest(
        {"candidate_state": "A"}
    )
    assert component_b["candidate_zero_useful_result"] is False
    assert component_a["candidate_window_count"] == 1
    assert component_b["candidate_window_count"] == 1
    assert component_a["candidate_window_digests"] == [
        _digest({"candidate_window": "A"})
    ]
    assert component_b["full_eligible_option_digests"] == [
        _digest({"candidate_options": "B"})
    ]
    assert component_a["read_nomination_count"] == 1
    assert component_b["read_nomination_count"] == 1
    assert component_a["custody_count"] == 1
    assert component_b["custody_count"] == 0
    assert component_a["semantic_handoff_count"] == 1
    assert component_b["semantic_handoff_count"] == 0
    assert component_a["final_posture"] == "semantically_handed_off"
    assert component_b["final_posture"] == "stale_or_invalid"
    assert component_b["safe_failure_class"] == "stale_or_invalid"


def test_success_fixture_keeps_two_logical_components_independently_correlatable() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_projection(
            admitted_components=frozenset({"A", "B"}),
            processing_order=("B", "A"),
        ),
        expected_run_id=RUN_ID,
        expected_request_id=REQUEST_ID,
    )
    assert projection is not None
    assert projection["required_slot_count"] == 2
    by_component = _projected_by_component(projection)
    component_a = by_component[_component_digest("A")]
    component_b = by_component[_component_digest("B")]

    assert {component_a["component_ordinal"], component_b["component_ordinal"]} == {
        1,
        2,
    }
    assert component_a["component_ordinal"] == 1
    assert component_b["component_ordinal"] == 2
    assert component_a["component_digest"] != component_b["component_digest"]
    assert component_a["source_obligation_digest"] != component_b[
        "source_obligation_digest"
    ]
    assert component_a["query_plan_item_digests"] != component_b[
        "query_plan_item_digests"
    ]
    assert component_a["custody_material_digests"] != component_b[
        "custody_material_digests"
    ]
    assert component_a["semantic_handoff_digests"] != component_b[
        "semantic_handoff_digests"
    ]
    assert all(
        slot["final_posture"] == "semantically_handed_off"
        for slot in (component_a, component_b)
    )


def test_reverse_processing_order_does_not_swap_component_records() -> None:
    forward = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_projection(
            admitted_components=frozenset({"A", "B"}),
            processing_order=("A", "B"),
        ),
        expected_run_id=RUN_ID,
        expected_request_id=REQUEST_ID,
    )
    reverse = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_projection(
            admitted_components=frozenset({"A", "B"}),
            processing_order=("B", "A"),
        ),
        expected_run_id=RUN_ID,
        expected_request_id=REQUEST_ID,
    )
    assert forward is not None
    assert reverse is not None
    assert _projected_by_component(forward) == _projected_by_component(reverse)


def test_projection_is_zero_authority_and_new_fields_are_privacy_bounded() -> None:
    fixture = _projection(admitted_components=frozenset({"A"}))
    before = deepcopy(fixture)
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=fixture,
        expected_run_id=RUN_ID,
        expected_request_id=REQUEST_ID,
    )
    assert projection is not None
    assert fixture == before

    serialized = json.dumps(projection, sort_keys=True)
    assert PRIVATE_CANARY not in serialized
    assert PRIVATE_URL not in serialized
    assert "authorized_query" not in serialized
    assert "normalized_url" not in serialized
    assert "read_content" not in serialized
    assert "title" not in serialized
    assert "snippet" not in serialized
    assert "action_history" not in serialized
    assert "custody_refs" not in serialized
    assert "semantic_handoff_authorization_attempted_slot_ids" not in serialized


def test_projection_disabled_and_existing_surface_remains_compatible() -> None:
    fixture = _projection(admitted_components=frozenset({"A", "B"}))
    assert (
        build_bounded_searchos_n1_causal_projection(
            searchos_slice_a_projection=fixture,
            enabled=False,
        )
        is None
    )
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=fixture,
        expected_run_id=RUN_ID,
        expected_request_id=REQUEST_ID,
    )
    assert projection is not None
    assert projection["schema_version"] == "bounded_searchos_n1_causal_projection_v1"
    assert projection["component_receiver_failure_class"] == "none"
    assert projection["logical_call_correlation"] == "not_directly_available"
    for slot in projection["slots"]:
        assert {
            "slot_identity_digest",
            "component_identity_digest",
            "source_obligation_identity_digest",
            "required",
            "support_kind",
            "final_posture",
            "canonical_slot_posture",
            "last_searchjudgment_action",
            "judgment_event_count",
            "judgment_failure_count",
            "read_custody_observed",
            "semantic_handoff_present",
            "handoff_material_consumed",
            "component_analyst_case_present",
            "semantic_admission_status",
            "component_coverage_satisfied",
        }.issubset(slot)
