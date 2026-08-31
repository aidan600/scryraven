"""PRODUCT-PATH-REGRESSION: closed SearchOS post-READ cause projection.

Proof class: PRODUCT-supporting structural proof. Validation bucket:
phase_focus. Surface guarded: the existing REQUEST_READ_PAGE failure reducer,
Slice A readiness, and bounded PRODUCT causal projection. Runtime/product path
guarded: the bounded projection derives one closed cause from the existing
canonical reason without changing selection, READ, custody, or recovery
behavior. Expected cost: milliseconds per node.
Promotion posture: remain phase_focus unless this closed diagnostic becomes a
durable product contract. Why not fast_pr: this is phase-detail observability,
while existing compact-selection and SearchOS lane sentinels own behavior.
"""

from __future__ import annotations

import inspect
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import core.pipeline as pipeline
import core.searchos_slice_a_product_runtime as product_runtime
from core.acquisition_adapters import AcquisitionTransports
from core.run_kernel import RunKernel
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_OWNER,
    begin_searchos_judgment_round,
    build_candidate_use_options_v1,
    build_candidate_use_window_v1,
    build_searchos_judgment_request_v1,
    build_searchos_slice_a_readiness_v1,
    candidate_use_option_ref,
    charge_searchos_judgment_call,
    mark_searchos_slot_stale_or_invalid,
    record_searchos_candidate_window,
    reduce_searchos_judgment_decision,
    validate_searchos_judgment_model_output,
)
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_POST_READ_FAILURE_CAUSES,
    _read_failure_reason,
    build_bounded_searchos_n1_causal_projection,
)
from scripts import ag_live_bound_01_support as bounded_product_support
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)
from tests.test_searchos_iterative_judgment_cutover_01 import (
    _candidate,
    _compact_candidate_use_option_id,
    _post_read_judgment_request,
    _state,
)
from tests.test_searchos_read_source_and_custody_01 import (
    _install_response_only_discovery,
)

_PRIVATE_REASON_CANARY = "PRIVATE_POST_READ_DETAIL_MUST_NOT_SERIALIZE"


def _awaiting_read_state() -> dict[str, Any]:
    state = _state()
    slot_ref = state["slots_by_id"]["slot-1"]["slot_ref"]
    options = build_candidate_use_options_v1(
        [_candidate(slot_ref=slot_ref, ordinal=1)]
    )
    window = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=options,
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
    )
    state = record_searchos_candidate_window(state, window=window)
    state, round_ref = begin_searchos_judgment_round(
        state,
        slot_ids=["slot-1"],
    )
    state, charge = charge_searchos_judgment_call(
        state,
        reservation_ref=round_ref,
        slot_id="slot-1",
    )
    request = build_searchos_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=window,
        read_custody_refs=[],
    )
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "REQUEST_READ_PAGE",
            "candidate_use_option_id": _compact_candidate_use_option_id(
                candidate_use_option_ref(options[0])
            ),
            "reason": "read the exact current offline candidate",
        },
    )
    state = reduce_searchos_judgment_decision(state, decision=decision)
    assert state["slots_by_id"]["slot-1"]["posture"] == "awaiting_read"
    return state


def _bounded_projection_for_state(state: dict[str, Any]) -> dict[str, Any]:
    outcomes = {slot_id: {} for slot_id in state["active_slot_ids"]}
    readiness = build_searchos_slice_a_readiness_v1(
        state=state,
        semantic_outcomes_by_slot=outcomes,
    )
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection={
            "schema_version": "searchos_slice_a_product_runtime_v1",
            "owner": SEARCHOS_OWNER,
            "readiness_projection": readiness,
            "readiness_projection_ref": {
                "readiness_projection_id": readiness["readiness_projection_id"],
                "readiness_projection_digest": readiness[
                    "readiness_projection_digest"
                ],
            },
            "semantic_outcomes_by_slot": outcomes,
            "slot_postures": {
                slot_id: state["slots_by_id"][slot_id]["posture"]
                for slot_id in state["active_slot_ids"]
            },
        },
        expected_run_id=state["run_id"],
        expected_request_id=state["request_id"],
    )
    assert projection is not None
    return projection


@pytest.mark.parametrize(
    ("cause", "reason"),
    (
        (
            "read_nomination_already_disposed",
            "read_nomination_already_disposed",
        ),
        ("candidate_packet_stale", "candidate_packet_stale"),
        (
            "read_transport_failure",
            f"read_transport_failure:{_PRIVATE_REASON_CANARY}",
        ),
        (
            "read_unusable_or_invalid_material",
            f"read_unusable_or_invalid_material:{_PRIVATE_REASON_CANARY}",
        ),
        (
            "read_authority_or_route_blocked",
            f"read_authority_or_route_blocked:{_PRIVATE_REASON_CANARY}",
        ),
    ),
)
def test_all_closed_post_read_causes_flow_from_slot_to_bounded_projection(
    cause: str,
    reason: str,
) -> None:
    stale = mark_searchos_slot_stale_or_invalid(
        _awaiting_read_state(),
        slot_id="slot-1",
        reason=reason,
    )
    slot = stale["slots_by_id"]["slot-1"]
    assert slot["latest_reason"] == reason
    assert "searchos_post_read_failure_cause" not in slot
    canonical_state_before_projection = deepcopy(stale)

    readiness = build_searchos_slice_a_readiness_v1(
        state=stale,
        semantic_outcomes_by_slot={"slot-1": {}},
    )
    readiness_slot = readiness["slot_records"][0]
    assert readiness_slot["latest_judgment_reason"] == reason
    assert "searchos_post_read_failure_cause" not in readiness_slot

    projection = _bounded_projection_for_state(stale)
    projected_slot = projection["slots"][0]
    assert stale == canonical_state_before_projection
    assert projected_slot["searchos_post_read_failure_cause"] == cause
    assert _PRIVATE_REASON_CANARY not in json.dumps(projection, sort_keys=True)


def test_closed_cause_is_not_part_of_canonical_state_contract() -> None:
    assert "searchos_post_read_failure_cause" not in inspect.signature(
        mark_searchos_slot_stale_or_invalid
    ).parameters
    assert "searchos_post_read_failure_cause" not in inspect.signature(
        RunKernel.mark_searchos_slot_stale_or_invalid
    ).parameters


def test_successful_read_custody_has_no_post_read_failure_cause() -> None:
    state, _request, _custody, _remaining = _post_read_judgment_request()
    assert state["slots_by_id"]["slot-1"]["custody_refs"]

    projection = _bounded_projection_for_state(state)

    assert "searchos_post_read_failure_cause" not in projection["slots"][0]


def test_non_read_stale_transition_is_not_falsely_labeled() -> None:
    stale = mark_searchos_slot_stale_or_invalid(
        _state(),
        slot_id="slot-1",
        reason="candidate_window_preparation_failed:OfflineFailure",
    )

    projection = _bounded_projection_for_state(stale)

    assert projection["slots"][0]["final_posture"] == "stale_or_invalid"
    assert "searchos_post_read_failure_cause" not in projection["slots"][0]


def test_unknown_post_read_reason_is_not_projected() -> None:
    reason = f"open_post_read_failure:{_PRIVATE_REASON_CANARY}"
    stale = mark_searchos_slot_stale_or_invalid(
        _awaiting_read_state(),
        slot_id="slot-1",
        reason=reason,
    )

    assert stale["slots_by_id"]["slot-1"]["latest_reason"] == reason
    projection = _bounded_projection_for_state(stale)

    assert "searchos_post_read_failure_cause" not in projection["slots"][0]
    assert _PRIVATE_REASON_CANARY not in json.dumps(projection, sort_keys=True)


@pytest.mark.parametrize(
    ("code", "expected"),
    (
        ("selected_provider_transport_failed", "read_transport_failure"),
        ("empty_content", "read_unusable_or_invalid_material"),
        ("provider_route_blocked", "read_authority_or_route_blocked"),
    ),
)
def test_existing_read_exception_classification_projects_closed_cause(
    code: str,
    expected: str,
) -> None:
    class CodedReadFailure(RuntimeError):
        def __init__(self) -> None:
            super().__init__(_PRIVATE_REASON_CANARY)
            self.code = code

    reason = _read_failure_reason(CodedReadFailure())
    stale = mark_searchos_slot_stale_or_invalid(
        _awaiting_read_state(),
        slot_id="slot-1",
        reason=reason,
    )
    projection = _bounded_projection_for_state(stale)

    assert reason.startswith(expected + ":")
    assert expected in SEARCHOS_POST_READ_FAILURE_CAUSES
    assert _PRIVATE_REASON_CANARY not in reason
    assert projection["slots"][0]["searchos_post_read_failure_cause"] == expected
    assert _PRIVATE_REASON_CANARY not in json.dumps(projection, sort_keys=True)


def test_candidate_packet_stale_product_branch_projects_closed_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    original = product_runtime._bindings_from_state

    def stale_packet_bindings(value: dict[str, Any]) -> list[Any]:
        return [
            replace(
                binding,
                candidate_packet_ref={
                    **dict(binding.candidate_packet_ref),
                    "packet_id": "search-result-candidate-packet:stale-offline",
                },
            )
            for binding in original(value)
        ]

    monkeypatch.setattr(
        product_runtime,
        "_bindings_from_state",
        stale_packet_bindings,
    )
    outcome, _harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="REQUEST_FIRST_THEN_NO_READ",
        deps_overrides={"process_search_queries": pipeline.process_search_queries},
        environment_overrides={
            "TAVILY_API_KEY": "offline-placeholder"  # pragma: allowlist secret
        },
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(
            outcome.execution_trace["searchos_slice_a"]
        ),
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
    )

    assert projection is not None
    assert projection["slots"][0]["searchos_post_read_failure_cause"] == (
        "candidate_packet_stale"
    )


def test_read_transport_product_branch_preserves_judgment_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)

    def fail_linkup(_payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(_PRIVATE_REASON_CANARY)

    outcome, _harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="REQUEST_FIRST_THEN_NO_READ",
        deps_overrides={
            "provider_availability": {
                "linkup": True,
                "tavily": False,
                "exa": False,
                "serper": False,
                "brave": False,
            },
            "process_search_queries": pipeline.process_search_queries,
            "searchos_read_acquisition_transports": AcquisitionTransports(
                linkup_fetch=fail_linkup
            ),
        },
        environment_overrides={
            "LINKUP_API_KEY": "offline-placeholder"  # pragma: allowlist secret
        },
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(
            outcome.execution_trace["searchos_slice_a"]
        ),
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
    )

    assert projection is not None
    assert projection["slots"][0]["final_posture"] == "unresolved_handoff"
    assert "searchos_post_read_failure_cause" not in projection["slots"][0]
    assert _PRIVATE_REASON_CANARY not in json.dumps(projection, sort_keys=True)


def test_bounded_product_packet_support_reuses_the_closed_projection_owner() -> None:
    stale = mark_searchos_slot_stale_or_invalid(
        _awaiting_read_state(),
        slot_id="slot-1",
        reason="candidate_packet_stale",
    )

    projection = _bounded_projection_for_state(stale)

    assert bounded_product_support.build_bounded_searchos_n1_causal_projection is (
        build_bounded_searchos_n1_causal_projection
    )
    assert projection["slots"][0]["searchos_post_read_failure_cause"] == (
        "candidate_packet_stale"
    )
