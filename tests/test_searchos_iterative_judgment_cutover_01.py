"""SearchOS Slice A contract and reducer boundary proof.

Proof class: PRODUCT-supporting structural proof. Validation bucket:
phase_focus, with exact QueryPlan follow-up admission promoted to
semantic_search_lane. Surface: policy, reservations, candidate windows,
append-only lineage, material authority, readiness, and RunKernel ownership;
navigation/recovery are closed. Runtime path: deterministic contracts and
reducers only. Expected cost: milliseconds per node. Promotion posture: one
durable domain sentinel, never fast_pr. Replace when the exact QueryPlan
continuation contract is retired.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

import core.searchos_iterative_judgment_runtime as searchos_runtime
from core.query_plan import QueryPlan, QueryPlanRole, QueryPlanStatus
from core.run_kernel import (
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED,
    SearchOSRuntimeError,
    begin_searchos_judgment_round,
    build_candidate_use_options_v1,
    build_candidate_use_window_v1,
    build_searchos_initial_state,
    build_searchos_iteration_candidate_set_v1,
    build_searchos_judgment_request_v1,
    build_searchos_policy_snapshot,
    build_searchos_read_custody_material_ref,
    build_searchos_required_needs_block,
    build_searchos_semantic_evaluation_handoff_v1,
    build_searchos_slice_a_readiness_v1,
    candidate_use_option_ref,
    charge_searchos_judgment_call,
    mark_searchos_slot_budget_exhausted,
    mark_searchos_slot_stale_or_invalid,
    mark_searchos_slot_unresolved,
    record_searchos_candidate_window,
    record_searchos_judgment_failure,
    record_searchos_read_custody_material,
    record_searchos_readiness_projection,
    record_searchos_semantic_handoff,
    reduce_searchos_judgment_decision,
    return_searchos_pre_call_reservation,
    searchos_iteration_candidate_set_ref,
    validate_searchos_append_only_lineage,
    validate_searchos_judgment_model_output,
    validate_searchos_required_needs_block,
)


def _digest(seed: str) -> str:
    return (seed.encode("utf-8").hex() + "0" * 64)[:64]


def _ref(kind: str, seed: str) -> dict[str, str]:
    return {f"{kind}_id": f"{kind}:{seed}", f"{kind}_digest": _digest(seed)}


def _slot(slot_id: str, *, required: bool = True) -> dict[str, object]:
    return {
        "slot_id": slot_id,
        "component_ref": _ref("component", slot_id),
        "source_obligation_ref": _ref("source_obligation", slot_id),
        "requirement_posture": "required" if required else "optional",
    }


def _state(*, profile: str = "Fast", slots: int = 1) -> dict[str, object]:
    policy = build_searchos_policy_snapshot(
        run_id="run-1", request_id="request-1", profile_name=profile
    )
    return build_searchos_initial_state(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=_ref("answer_contract", "contract"),
        policy_snapshot=policy,
        active_slots=[_slot(f"slot-{index}") for index in range(1, slots + 1)],
        initial_candidate_state_ref=_ref("candidate_state", "revision-1"),
    )


def _lawful_ineligible_facts(
    readiness: dict[str, object],
) -> list[dict[str, str]]:
    return [
        {
            "blocker_class": "recovery_ineligible",
            "interpretation": "lawful_recovery_ineligible",
            "reason_code": (
                "no_lawful_materially_novel_recovery_purpose"
            ),
            "slot_id": str(
                dict(dict(item)["slot_ref"])["slot_id"]
            ),
        }
        for item in readiness["unresolved_required_slots"]
    ]


def _reenvelope_required_needs_block(
    block: dict[str, object],
    **updates: object,
) -> dict[str, object]:
    core = {
        key: deepcopy(value)
        for key, value in block.items()
        if key not in {
            "block_id",
            "block_digest",
            "replay_identity",
        }
    }
    core.update(deepcopy(updates))
    digest = searchos_runtime._digest(core)
    return {
        **core,
        "block_id": (
            f"searchos-required-needs-block:{digest[:24]}"
        ),
        "block_digest": digest,
        "replay_identity": (
            f"searchos-required-needs-block:{digest}"
        ),
    }


def _candidate(
    *, slot_ref: dict[str, object], ordinal: int, url: str | None = None
) -> dict[str, object]:
    seed = f"candidate-{ordinal}"
    return {
        "slot_ref": slot_ref,
        "normalized_url": url or f"https://example.com/{ordinal}",
        "candidate_state_ref": _ref("candidate_state", "revision-1"),
        "candidate_ref": _ref("candidate", seed),
        "query_plan_item_ref": _ref("query_plan_item", seed),
        "provider_result_occurrence_ref": _ref("source_result", seed),
        "source_material_ref": _ref("material", seed),
        "title": f"Candidate {ordinal}",
        "snippet": f"Directional context {ordinal}",
    }


def _post_read_judgment_request() -> tuple[
    dict[str, object], dict[str, object], dict[str, object]
]:
    state = _state()
    slot_ref = state["slots_by_id"]["slot-1"]["slot_ref"]
    options = build_candidate_use_options_v1(
        [
            _candidate(slot_ref=slot_ref, ordinal=1),
            _candidate(slot_ref=slot_ref, ordinal=2),
        ]
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
    initial_request = build_searchos_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=window,
        read_custody_refs=[],
    )
    read_decision = validate_searchos_judgment_model_output(
        request=initial_request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "judgment_request_id": initial_request["judgment_request_id"],
            "judgment_request_digest": initial_request["judgment_request_digest"],
            "slot_id": "slot-1",
            "action": "REQUEST_READ_PAGE",
            "candidate_use_option_ref": candidate_use_option_ref(options[0]),
            "reason": "read the first exact admitted candidate",
        },
    )
    state = reduce_searchos_judgment_decision(state, decision=read_decision)
    custody = build_searchos_read_custody_material_ref(
        slot_ref=slot_ref,
        candidate_use_option_ref=candidate_use_option_ref(options[0]),
        custody_record={
            "normalized_url": options[0]["normalized_url"],
            "fetch_read_content_packet_ref": _ref(
                "fetch_read_content_packet", "post-read"
            ),
            "evidence_ledger_custody_ref": _ref(
                "evidence_ledger_custody", "post-read"
            ),
            "evidence_ledger_candidate_id": "candidate:post-read",
            "terminal_receipt_ref": _ref("terminal_receipt", "post-read"),
            "custody_authorization_ref": _ref(
                "custody_authorization", "post-read"
            ),
            "bounded_content_present": True,
        },
        same_normalized_url_reused=False,
    )
    state = record_searchos_read_custody_material(
        state,
        custody_material_ref=custody,
    )
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
        read_custody_refs=[custody],
    )
    return request, custody, candidate_use_option_ref(options[1])


def test_policy_profiles_and_complete_round_reservation_prevent_starvation() -> None:
    fast = build_searchos_policy_snapshot(
        run_id="run-1", request_id="request-1", profile_name="Fast"
    )
    balanced = build_searchos_policy_snapshot(
        run_id="run-1", request_id="request-1", profile_name="Balanced"
    )
    deep = build_searchos_policy_snapshot(
        run_id="run-1", request_id="request-1", profile_name="Deep"
    )
    assert fast["minimum_reserved_judgment_calls_per_required_slot"] == 2
    assert balanced["minimum_reserved_judgment_calls_per_required_slot"] == 3
    assert deep["minimum_reserved_judgment_calls_per_required_slot"] == 4
    assert {fast["candidate_use_window_size"], balanced["candidate_use_window_size"], deep["candidate_use_window_size"]} == {12}
    assert fast["navigation_runtime_open"] is False
    assert fast["post_analyst_reentry_runtime_open"] is False

    state = _state(slots=2)
    state, first_round = begin_searchos_judgment_round(
        state, slot_ids=["slot-1", "slot-2"]
    )
    state, _ = charge_searchos_judgment_call(
        state, reservation_ref=first_round, slot_id="slot-1"
    )
    state, _ = charge_searchos_judgment_call(
        state, reservation_ref=first_round, slot_id="slot-2"
    )
    state, second_round = begin_searchos_judgment_round(
        state, slot_ids=["slot-1", "slot-2"]
    )
    state, _ = charge_searchos_judgment_call(
        state, reservation_ref=second_round, slot_id="slot-1"
    )
    state, _ = charge_searchos_judgment_call(
        state, reservation_ref=second_round, slot_id="slot-2"
    )
    assert state["budget"]["reserved_calls_remaining_by_required_slot"] == {
        "slot-1": 0,
        "slot-2": 0,
    }
    assert state["budget"]["shared_calls_remaining"] == 2
    state, third_round = begin_searchos_judgment_round(
        state,
        slot_ids=["slot-1", "slot-2"],
    )
    assert {
        item["capacity_source"]
        for item in third_round["required_slot_reservations"]
    } == {"shared_pool"}
    assert state["budget"]["shared_calls_remaining"] == 0
    state, _ = charge_searchos_judgment_call(
        state,
        reservation_ref=third_round,
        slot_id="slot-1",
    )
    state, _ = charge_searchos_judgment_call(
        state,
        reservation_ref=third_round,
        slot_id="slot-2",
    )
    assert state["budget"]["charged_logical_judgment_calls"] == 6
    with pytest.raises(SearchOSRuntimeError, match="complete-round reservation"):
        begin_searchos_judgment_round(state, slot_ids=["slot-1", "slot-2"])


def test_candidate_option_identity_is_stable_while_lineage_snapshot_grows() -> None:
    state = _state()
    slot_ref = state["slots_by_id"]["slot-1"]["slot_ref"]
    revision_1 = _candidate(
        slot_ref=slot_ref,
        ordinal=1,
        url="https://example.com/stable",
    )
    wave_1 = {
        **_candidate(
            slot_ref=slot_ref,
            ordinal=2,
            url="https://example.com/stable",
        ),
        "candidate_state_ref": _ref("iteration_candidate_set", "wave-1"),
        "iteration_set_ref": _ref("iteration_candidate_set", "wave-1"),
    }
    wave_2 = {
        **_candidate(
            slot_ref=slot_ref,
            ordinal=3,
            url="https://example.com/stable",
        ),
        "candidate_state_ref": _ref("iteration_candidate_set", "wave-2"),
        "iteration_set_ref": _ref("iteration_candidate_set", "wave-2"),
    }

    [initial] = build_candidate_use_options_v1([revision_1])
    [grown] = build_candidate_use_options_v1([revision_1, wave_1, wave_2])

    assert grown["candidate_use_option_id"] == initial["candidate_use_option_id"]
    assert grown["candidate_use_option_digest"] == initial["candidate_use_option_digest"]
    assert grown["lineage_snapshot_ref"] != initial["lineage_snapshot_ref"]
    assert grown["candidate_state_origin_refs"] == [
        revision_1["candidate_state_ref"],
        wave_1["candidate_state_ref"],
        wave_2["candidate_state_ref"],
    ]
    initial_window = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=[initial],
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
        option_dispositions={initial["candidate_use_option_id"]: "custodied"},
    )
    grown_window = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=[grown],
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
        option_dispositions={grown["candidate_use_option_id"]: "custodied"},
    )
    assert initial_window["model_visible_candidate_use_options"] == []
    assert grown_window["model_visible_candidate_use_options"] == []
    assert (
        grown_window["ordered_candidate_use_option_refs"][0][
            "lineage_snapshot_ref"
        ]
        != initial_window["ordered_candidate_use_option_refs"][0][
            "lineage_snapshot_ref"
        ]
    )
    recorded = record_searchos_candidate_window(state, window=initial_window)
    advanced = record_searchos_candidate_window(recorded, window=grown_window)
    advanced_slot = advanced["slots_by_id"]["slot-1"]
    assert advanced_slot["candidate_window_count"] == 1
    assert (
        advanced_slot["candidate_use_option_refs"]
        == grown_window["ordered_candidate_use_option_refs"]
    )
    advancement = advanced_slot["action_history"][-1]
    assert advancement["event"] == "candidate_window_snapshot_advanced"
    assert advancement["candidate_use_window_ref"]["candidate_use_window_id"] == (
        grown_window["candidate_use_window_id"]
    )
    assert advancement["new_query_created"] is False
    assert advancement["provider_dispatched"] is False
    assert advancement["acquisition_proposal_created"] is False
    assert advancement["read_budget_consumed"] is False

    initial_available = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=[initial],
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
    )
    grown_available = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=[grown],
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
    )
    current = record_searchos_candidate_window(state, window=initial_available)
    current = record_searchos_candidate_window(current, window=grown_available)
    current, round_ref = begin_searchos_judgment_round(
        current,
        slot_ids=["slot-1"],
    )
    current, charge = charge_searchos_judgment_call(
        current,
        reservation_ref=round_ref,
        slot_id="slot-1",
    )
    current_request = build_searchos_judgment_request_v1(
        state=current,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=grown_available,
        read_custody_refs=[],
    )
    with pytest.raises(SearchOSRuntimeError, match="stale or altered"):
        validate_searchos_judgment_model_output(
            request=current_request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "judgment_request_id": current_request["judgment_request_id"],
                "judgment_request_digest": current_request[
                    "judgment_request_digest"
                ],
                "slot_id": "slot-1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_ref": candidate_use_option_ref(initial),
                "reason": "obsolete lineage snapshot",
            },
        )


def test_custodied_is_a_completed_candidate_window_disposition() -> None:
    from core.searchos_slice_a_product_runtime import (
        TERMINAL_CANDIDATE_OPTION_DISPOSITIONS,
    )

    assert "custodied" in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS


def test_model_failure_is_distinct_and_never_gets_a_fallback() -> None:
    state = _state()
    state, round_ref = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state, reservation_ref=round_ref, slot_id="slot-1"
    )
    failed = record_searchos_judgment_failure(
        state, charge_ref=charge, reason="model_unavailable"
    )
    slot = failed["slots_by_id"]["slot-1"]
    assert slot["posture"] == "judgment_failed"
    assert slot["satisfaction_claimed"] is False
    assert slot["action_history"][-1]["deterministic_semantic_fallback_invoked"] is False
    assert failed["budget"]["failed_logical_judgment_calls"] == 1


def test_pre_call_rejection_returns_required_slot_reservation() -> None:
    state = _state(slots=2)
    state, reservation = begin_searchos_judgment_round(
        state,
        slot_ids=["slot-1", "slot-2"],
    )
    state = return_searchos_pre_call_reservation(
        state,
        reservation_ref=reservation,
        slot_id="slot-2",
        reason="candidate_window_preparation_rejected",
    )
    state, _ = charge_searchos_judgment_call(
        state,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    assert state["budget"]["returned_pre_call_reservations"] == 1
    returned = state["budget"]["round_history"][0][
        "required_slot_reservations"
    ][1]
    assert returned["returned"] is True
    assert returned["charged"] is False
    state, next_round = begin_searchos_judgment_round(
        state,
        slot_ids=["slot-2"],
    )
    assert next_round["participating_slot_ids"] == ["slot-2"]

    shared_state = _state()
    for _ in range(2):
        shared_state, own_round = begin_searchos_judgment_round(
            shared_state,
            slot_ids=["slot-1"],
        )
        shared_state, _ = charge_searchos_judgment_call(
            shared_state,
            reservation_ref=own_round,
            slot_id="slot-1",
        )
    shared_state, shared_round = begin_searchos_judgment_round(
        shared_state,
        slot_ids=["slot-1"],
    )
    assert shared_state["budget"]["shared_calls_remaining"] == 0
    shared_state = return_searchos_pre_call_reservation(
        shared_state,
        reservation_ref=shared_round,
        slot_id="slot-1",
        reason="candidate_window_preparation_rejected",
    )
    assert shared_state["budget"]["shared_calls_remaining"] == 1


def test_candidate_options_aggregate_slot_plus_url_and_windows_are_progressive() -> None:
    state = _state()
    slot_ref = state["slots_by_id"]["slot-1"]["slot_ref"]
    first = _candidate(slot_ref=slot_ref, ordinal=1, url="https://EXAMPLE.com/a#fragment")
    duplicate = _candidate(slot_ref=slot_ref, ordinal=2, url="https://example.com/a")
    options = build_candidate_use_options_v1([first, duplicate])
    assert len(options) == 1
    assert options[0]["normalized_url"] == "https://example.com/a"
    assert len(options[0]["provider_result_occurrence_refs"]) == 2
    assert options[0]["material_authority"] == "directional_candidate_context"
    assert options[0]["support_proposal_eligible"] is False

    many = build_candidate_use_options_v1(
        [_candidate(slot_ref=slot_ref, ordinal=index) for index in range(1, 26)]
    )
    policy = state["policy_snapshot"]
    first_window = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=many,
        window_ordinal=1,
        policy_snapshot=policy,
    )
    second_window = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=many,
        window_ordinal=2,
        policy_snapshot=policy,
    )
    assert first_window["retained_option_count"] == 12
    assert first_window["remaining_option_count"] == 13
    assert first_window["next_window_available"] is True
    assert second_window["retained_option_count"] == 12
    assert second_window["remaining_option_count"] == 1
    assert second_window["next_window_available"] is False
    assert second_window["next_window_requires_provider_dispatch"] is False
    assert second_window["next_window_consumes_read_budget"] is False
    completed_first = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=many,
        window_ordinal=1,
        policy_snapshot=policy,
        option_dispositions={
            item["candidate_use_option_id"]: "custodied"
            for item in many[:12]
        },
    )
    progressed = record_searchos_candidate_window(
        state,
        window=completed_first,
    )
    progressed = record_searchos_candidate_window(
        progressed,
        window=second_window,
    )
    progression = progressed["slots_by_id"]["slot-1"]["action_history"][-1]
    assert progression["event"] == "candidate_window_exposed"
    assert progression["new_query_created"] is False
    assert progression["provider_dispatched"] is False
    assert progression["acquisition_proposal_created"] is False
    assert progression["read_budget_consumed"] is False
    with pytest.raises(SearchOSRuntimeError, match="policy budget exhausted"):
        build_candidate_use_window_v1(
            slot_ref=slot_ref,
            ordered_options=many,
            window_ordinal=3,
            policy_snapshot=policy,
        )


@pytest.mark.parametrize(
    ("candidate_count", "retained", "remaining", "next_available"),
    [
        (11, 11, 0, False),
        (12, 12, 0, False),
        (13, 12, 1, True),
    ],
)
def test_candidate_window_limit_minus_at_and_plus_one(
    candidate_count: int,
    retained: int,
    remaining: int,
    next_available: bool,
) -> None:
    state = _state()
    slot_ref = state["slots_by_id"]["slot-1"]["slot_ref"]
    options = build_candidate_use_options_v1(
        [
            _candidate(slot_ref=slot_ref, ordinal=index)
            for index in range(1, candidate_count + 1)
        ]
    )
    window = build_candidate_use_window_v1(
        slot_ref=slot_ref,
        ordered_options=options,
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
    )
    assert window["retained_option_count"] == retained
    assert window["remaining_option_count"] == remaining
    assert window["next_window_available"] is next_available


def test_append_only_lineage_rejects_plan_rewrite_and_omitted_delta() -> None:
    initial_plan = [_ref("query_plan_item", "initial")]
    current_plan = initial_plan + [_ref("query_plan_item", "followup")]
    initial_identity = [_ref("source_result", "initial")]
    delta_identity = [_ref("source_result", "followup")]
    delta_ref = {
        **_ref("identity_set_delta", "delta"),
        "identity_count": 1,
        "identity_refs_digest": __import__(
            "hashlib"
        ).sha256(
            __import__("json").dumps(
                delta_identity,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest(),
    }
    revision_ref = _ref("candidate_state", "revision-1")
    revision = {
        **revision_ref,
        "initial_query_plan_ref": _ref("query_plan", "initial"),
        "initial_identity_set_ref": _ref("identity_set", "initial"),
        "candidate_state_ref": revision_ref,
    }
    iteration = build_searchos_iteration_candidate_set_v1(
        run_id="run-1",
        request_id="request-1",
        iteration=2,
        parent_candidate_state_ref=revision_ref,
        slot_ref=_ref("slot", "one"),
        query_plan_item_ref=current_plan[-1],
        provider_plan_ref=_ref("provider_plan", "one"),
        route_refs=[_ref("route", "one")],
        retrieval_action_refs=[_ref("retrieval_action", "one")],
        ordered_provider_result_occurrence_refs=delta_identity,
        identity_set_delta_ref=delta_ref,
        selected_candidate_refs=[_ref("candidate", "one")],
        bounded_candidate_material_refs=[_ref("material", "one")],
        selection_facts={"selected": 1},
        overflow_facts={"overflow": 0},
        zero_useful_result=False,
    )
    proof = validate_searchos_append_only_lineage(
        revision_1=revision,
        initial_query_plan_items=initial_plan,
        current_query_plan_items=current_plan,
        initial_identity_refs=initial_identity,
        iteration_candidate_sets=[iteration],
        identity_deltas_by_digest={delta_ref["identity_set_delta_digest"]: delta_identity},
        current_identity_refs=initial_identity + delta_identity,
    )
    assert proof["initial_plan_is_exact_prefix"] is True
    assert proof["identity_delta_equality_proven"] is True
    assert searchos_iteration_candidate_set_ref(iteration)["iteration"] == 2

    rewritten = [deepcopy(initial_plan[0]), current_plan[-1]]
    rewritten[0]["query_plan_item_id"] = "query_plan_item:rewritten"
    with pytest.raises(SearchOSRuntimeError, match="exact current-plan prefix"):
        validate_searchos_append_only_lineage(
            revision_1=revision,
            initial_query_plan_items=initial_plan,
            current_query_plan_items=rewritten,
            initial_identity_refs=initial_identity,
            iteration_candidate_sets=[iteration],
            identity_deltas_by_digest={delta_ref["identity_set_delta_digest"]: delta_identity},
            current_identity_refs=initial_identity + delta_identity,
        )
    with pytest.raises(SearchOSRuntimeError, match="delta is omitted"):
        validate_searchos_append_only_lineage(
            revision_1=revision,
            initial_query_plan_items=initial_plan,
            current_query_plan_items=current_plan,
            initial_identity_refs=initial_identity,
            iteration_candidate_sets=[iteration],
            identity_deltas_by_digest={},
            current_identity_refs=initial_identity + delta_identity,
        )
    with pytest.raises(SearchOSRuntimeError, match="do not equal"):
        validate_searchos_append_only_lineage(
            revision_1=revision,
            initial_query_plan_items=initial_plan,
            current_query_plan_items=current_plan,
            initial_identity_refs=initial_identity,
            iteration_candidate_sets=[iteration],
            identity_deltas_by_digest={
                delta_ref["identity_set_delta_digest"]: delta_identity
            },
            current_identity_refs=initial_identity + delta_identity + delta_identity,
        )
    with pytest.raises(SearchOSRuntimeError, match="do not equal"):
        validate_searchos_append_only_lineage(
            revision_1=revision,
            initial_query_plan_items=initial_plan,
            current_query_plan_items=current_plan,
            initial_identity_refs=initial_identity,
            iteration_candidate_sets=[iteration],
            identity_deltas_by_digest={
                delta_ref["identity_set_delta_digest"]: delta_identity
            },
            current_identity_refs=delta_identity + initial_identity,
        )

    zero_useful = build_searchos_iteration_candidate_set_v1(
        run_id="run-1",
        request_id="request-1",
        iteration=2,
        parent_candidate_state_ref=revision_ref,
        slot_ref=_ref("slot", "one"),
        query_plan_item_ref=current_plan[-1],
        provider_plan_ref=_ref("provider_plan", "one"),
        route_refs=[_ref("route", "one")],
        retrieval_action_refs=[_ref("retrieval_action", "one")],
        ordered_provider_result_occurrence_refs=[],
        identity_set_delta_ref={
            **_ref("identity_set_delta", "zero"),
            "identity_count": 0,
        },
        selected_candidate_refs=[],
        bounded_candidate_material_refs=[],
        selection_facts={"selected": 0},
        overflow_facts={"overflow": 0},
        zero_useful_result=True,
    )
    assert zero_useful["zero_useful_result"] is True
    assert zero_useful["selected_candidate_refs"] == []


@pytest.mark.parametrize(
    "action",
    [
        "REQUEST_READ_PAGE",
        "PROPOSE_FOLLOWUP_QUERY",
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
        "HANDOFF_UNRESOLVED",
    ],
)
def test_strict_validator_accepts_each_exact_post_read_action(action: str) -> None:
    request, custody, remaining_option = _post_read_judgment_request()
    output = {
        "schema_version": "searchos_judgment_decision_v1",
        "judgment_request_id": request["judgment_request_id"],
        "judgment_request_digest": request["judgment_request_digest"],
        "slot_id": "slot-1",
        "action": action,
        "reason": "exact post-read action",
    }
    if action == "REQUEST_READ_PAGE":
        output["candidate_use_option_ref"] = remaining_option
    elif action == "PROPOSE_FOLLOWUP_QUERY":
        output["followup_query"] = "Alpha exact post-READ follow-up query"
    elif action == "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION":
        output["read_custody_refs"] = [custody]
    if action != "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION":
        output["read_custody_assessments"] = [
            {
                "reviewed_custody_ref": custody,
                "material_disposition": "read_insufficient",
                "reason_code": "active_need_not_met",
            }
        ]

    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output=output,
    )

    assert decision["action"] == action
    if action == "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION":
        assert decision["read_custody_refs"] == [custody]
        assert decision["read_custody_assessments"] == []
    else:
        assert decision["read_custody_assessments"][0][
            "reviewed_custody_ref"
        ] == custody


@pytest.mark.parametrize(
    ("invalid_assessment", "message"),
    [
        ("missing", "requires exact read_insufficient assessments"),
        ("duplicate", "repeats material"),
        ("stale", "stale or altered"),
        ("altered", "stale or altered"),
        ("wrong_disposition", "disposition is invalid"),
        ("unsupported_field", "shape is invalid"),
    ],
)
def test_strict_validator_rejects_invalid_post_read_assessments(
    invalid_assessment: str,
    message: str,
) -> None:
    request, custody, _ = _post_read_judgment_request()
    assessment = {
        "reviewed_custody_ref": custody,
        "material_disposition": "read_insufficient",
        "reason_code": "active_need_not_met",
    }
    assessments = [assessment]
    if invalid_assessment == "missing":
        assessments = []
    elif invalid_assessment == "duplicate":
        assessments = [assessment, deepcopy(assessment)]
    elif invalid_assessment == "stale":
        assessment["reviewed_custody_ref"] = _ref(
            "searchos_read_custody_material", "stale"
        )
    elif invalid_assessment == "altered":
        assessment["reviewed_custody_ref"] = {
            **custody,
            "searchos_read_custody_material_digest": _digest("altered"),
        }
    elif invalid_assessment == "wrong_disposition":
        assessment["material_disposition"] = "read_sufficient"
    else:
        assessment["unsupported_field"] = "must fail closed"
    output = {
        "schema_version": "searchos_judgment_decision_v1",
        "judgment_request_id": request["judgment_request_id"],
        "judgment_request_digest": request["judgment_request_digest"],
        "slot_id": "slot-1",
        "action": "HANDOFF_UNRESOLVED",
        "reason": "current READ material does not meet the active need",
    }
    if assessments:
        output["read_custody_assessments"] = assessments

    with pytest.raises(SearchOSRuntimeError, match=message):
        validate_searchos_judgment_model_output(
            request=request,
            model_output=output,
        )


def test_strict_validator_rejects_assessment_on_exact_semantic_handoff() -> None:
    request, custody, _ = _post_read_judgment_request()
    with pytest.raises(
        SearchOSRuntimeError,
        match="semantic handoff requires exact READ custody refs",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "judgment_request_id": request["judgment_request_id"],
                "judgment_request_digest": request["judgment_request_digest"],
                "slot_id": "slot-1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_refs": [custody],
                "reason": "exact custody is ready for semantic evaluation",
                "read_custody_assessments": [
                    {
                        "reviewed_custody_ref": custody,
                        "material_disposition": "read_insufficient",
                        "reason_code": "incompatible_with_handoff",
                    }
                ],
            },
        )


def test_read_custody_is_the_only_semantic_entry_and_required_block_is_safe() -> None:
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
    state, round_ref = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state, reservation_ref=round_ref, slot_id="slot-1"
    )
    read_request = build_searchos_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=window,
        read_custody_refs=[],
    )
    altered_option_ref = candidate_use_option_ref(options[0])
    altered_option_ref["normalized_url"] = "https://example.com/altered"
    with pytest.raises(SearchOSRuntimeError, match="stale or altered"):
        validate_searchos_judgment_model_output(
            request=read_request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "judgment_request_id": read_request["judgment_request_id"],
                "judgment_request_digest": read_request["judgment_request_digest"],
                "slot_id": "slot-1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_ref": altered_option_ref,
                "reason": "attempt to alter an admitted option ref",
            },
        )
    read_decision = validate_searchos_judgment_model_output(
        request=read_request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "judgment_request_id": read_request["judgment_request_id"],
            "judgment_request_digest": read_request["judgment_request_digest"],
            "slot_id": "slot-1",
            "action": "REQUEST_READ_PAGE",
            "candidate_use_option_ref": candidate_use_option_ref(options[0]),
            "reason": "read the exact admitted candidate",
        },
    )
    state = reduce_searchos_judgment_decision(state, decision=read_decision)
    custody = build_searchos_read_custody_material_ref(
        slot_ref=slot_ref,
        candidate_use_option_ref=candidate_use_option_ref(options[0]),
        custody_record={
            "normalized_url": options[0]["normalized_url"],
            "fetch_read_content_packet_ref": _ref("fetch_read_content_packet", "one"),
            "evidence_ledger_custody_ref": _ref("evidence_ledger_custody", "one"),
            "evidence_ledger_candidate_id": "candidate:one",
            "terminal_receipt_ref": _ref("terminal_receipt", "one"),
            "custody_authorization_ref": _ref("custody_authorization", "one"),
            "bounded_content_present": True,
        },
        same_normalized_url_reused=False,
    )
    state = record_searchos_read_custody_material(
        state,
        custody_material_ref=custody,
    )
    state, round_ref = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state, reservation_ref=round_ref, slot_id="slot-1"
    )
    request = build_searchos_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=window,
        read_custody_refs=[custody],
    )
    assert request["candidate_use_options"] == []
    assert "REQUEST_READ_PAGE" not in request["legal_actions"]
    read_nominations_before = state["slots_by_id"]["slot-1"][
        "read_nomination_count"
    ]
    with pytest.raises(SearchOSRuntimeError, match="not currently authorized"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "judgment_request_id": request["judgment_request_id"],
                "judgment_request_digest": request["judgment_request_digest"],
                "slot_id": "slot-1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_ref": candidate_use_option_ref(options[0]),
                "reason": "repeat an already-custodied option",
            },
        )
    assert state["slots_by_id"]["slot-1"]["read_nomination_count"] == (
        read_nominations_before
    )
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "judgment_request_id": request["judgment_request_id"],
            "judgment_request_digest": request["judgment_request_digest"],
            "slot_id": "slot-1",
            "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "read_custody_refs": [custody],
            "reason": "current read custody is suitable for governed analysis",
        },
    )
    state = reduce_searchos_judgment_decision(state, decision=decision)
    with pytest.raises(SearchOSRuntimeError, match="exact current admitted material"):
        build_searchos_semantic_evaluation_handoff_v1(
            state=state,
            slot_id="slot-1",
            judgment_decision_ref=decision,
            read_custody_material_refs=[
                {
                    **custody,
                    "material_authority": "directional_candidate_context",
                }
            ],
        )
    handoff = build_searchos_semantic_evaluation_handoff_v1(
        state=state,
        slot_id="slot-1",
        judgment_decision_ref=decision,
        read_custody_material_refs=[custody],
    )
    state = record_searchos_semantic_handoff(state, handoff=handoff)
    readiness = build_searchos_slice_a_readiness_v1(
        state=state,
        semantic_outcomes_by_slot={
            "slot-1": {
                "semantic_handoff_ref": handoff,
                "component_analyst_proposal_ref": _ref("analyst_proposal", "one"),
                "component_analyst_proposal_status": "proposed",
                "component_dprime_validation_ref": _ref("dprime_validation", "one"),
                "component_dprime_validation_status": "accepted",
                "semantic_admission_outcome_ref": _ref("semantic_admission", "one"),
                "semantic_admission_status": "admitted",
                "material_authority": "read_custody_material",
            }
        },
    )
    assert readiness["all_required_slots_slice_a_ready"] is True
    assert readiness["semantic_receiver_ready"] is True
    assert readiness["sufficiency_adjudication_required"] is True
    assert "final_answer_packet_allowed" not in readiness
    assert "author_execution_allowed" not in readiness

    exact_outcome = {
        "semantic_handoff_ref": handoff,
        "component_analyst_proposal_ref": _ref("analyst_proposal", "one"),
        "component_analyst_proposal_status": "proposed",
        "component_dprime_validation_ref": _ref("dprime_validation", "one"),
        "component_dprime_validation_status": "accepted",
        "semantic_admission_outcome_ref": _ref("semantic_admission", "one"),
        "semantic_admission_status": "admitted",
        "material_authority": "read_custody_material",
    }
    negative_outcomes = [
        (
            {**exact_outcome, "material_authority": "directional_candidate_context"},
            "candidate_only_or_directional_context_only",
        ),
        (
            {
                **exact_outcome,
                "component_dprime_validation_ref": {},
                "component_dprime_validation_status": "not_accepted",
            },
            "component_dprime_validation_missing_or_rejected",
        ),
        (
            {
                **exact_outcome,
                "semantic_admission_outcome_ref": {},
                "semantic_admission_status": "not_admitted",
            },
            "runkernel_semantic_admission_missing_or_rejected",
        ),
    ]
    for outcome, expected_reason in negative_outcomes:
        not_ready = build_searchos_slice_a_readiness_v1(
            state=state,
            semantic_outcomes_by_slot={"slot-1": outcome},
        )
        assert not_ready["all_required_slots_slice_a_ready"] is False
        assert not_ready["unresolved_required_slots"][0]["reason"] == (
            expected_reason
        )

    blocked = build_searchos_slice_a_readiness_v1(
        state=state,
        semantic_outcomes_by_slot={},
    )
    block = build_searchos_required_needs_block(
        blocked,
        blocker_facts=_lawful_ineligible_facts(blocked),
    )
    assert block["block_type"] == SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED
    assert block["semantic_receiver_ready"] is False
    assert block["sufficiency_adjudication_required"] is True
    assert block["subordinate_to_sufficiency"] is True
    assert "final_answer_packet_allowed" not in block
    assert "author_execution_allowed" not in block
    assert block["query_authorized"] is False
    assert block["read_authorized"] is False
    assert block["recovery_authorized"] is False
    assert block["stop_insufficient_emitted"] is False


def test_optional_slot_is_not_promoted_or_silently_satisfied() -> None:
    policy = build_searchos_policy_snapshot(
        run_id="run-1", request_id="request-1", profile_name="Fast"
    )
    state = build_searchos_initial_state(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=_ref("answer_contract", "contract"),
        policy_snapshot=policy,
        active_slots=[_slot("required"), _slot("optional", required=False)],
        initial_candidate_state_ref=_ref("candidate_state", "revision-1"),
    )
    readiness = build_searchos_slice_a_readiness_v1(
        state=state,
        semantic_outcomes_by_slot={},
    )
    optional = next(
        item
        for item in readiness["slot_records"]
        if item["slot_ref"]["slot_id"] == "optional"
    )
    assert optional["requirement_posture"] == "optional"
    assert optional["slice_a_ready"] is False
    assert len(readiness["unresolved_required_slots"]) == 1

    ambiguous = _slot("ambiguous")
    ambiguous.pop("requirement_posture")
    with pytest.raises(SearchOSRuntimeError, match="posture is ambiguous"):
        build_searchos_initial_state(
            run_id="run-1",
            request_id="request-1",
            answer_contract_ref=_ref("answer_contract", "contract"),
            policy_snapshot=policy,
            active_slots=[ambiguous],
            initial_candidate_state_ref=_ref("candidate_state", "revision-1"),
        )


def test_required_terminal_postures_share_block_family_with_distinct_reasons() -> None:
    cases: list[tuple[dict[str, object], str]] = []
    state = _state()
    cases.append(
        (
            mark_searchos_slot_unresolved(
                state,
                slot_id="slot-1",
                reason="offline_unresolved",
            ),
            "unresolved_handoff",
        )
    )
    cases.append(
        (
            mark_searchos_slot_budget_exhausted(
                state,
                slot_id="slot-1",
                reason="offline_budget_exhausted",
            ),
            "budget_exhausted",
        )
    )
    cases.append(
        (
            mark_searchos_slot_stale_or_invalid(
                state,
                slot_id="slot-1",
                reason="offline_stale",
            ),
            "stale_or_invalid",
        )
    )
    failed, reservation = begin_searchos_judgment_round(
        state,
        slot_ids=["slot-1"],
    )
    failed, charge = charge_searchos_judgment_call(
        failed,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    cases.append(
        (
            record_searchos_judgment_failure(
                failed,
                charge_ref=charge,
                reason="offline_model_failure",
            ),
            "judgment_failed",
        )
    )

    block_ids: set[str] = set()
    for terminal_state, expected_reason in cases:
        readiness = build_searchos_slice_a_readiness_v1(
            state=terminal_state,
            semantic_outcomes_by_slot={},
        )
        assert readiness["unresolved_required_slots"][0]["reason"] == (
            expected_reason
        )
        block = build_searchos_required_needs_block(
            readiness,
            blocker_facts=_lawful_ineligible_facts(readiness),
        )
        assert block["block_type"] == SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED
        assert block["sufficiency_adjudication_required"] is True
        assert block["subordinate_to_sufficiency"] is True
        assert "author_execution_allowed" not in block
        block_ids.add(block["block_id"])
    assert len(block_ids) == 4


@pytest.mark.parametrize(
    "blocker_facts",
    [
        [],
        [
            {
                "blocker_class": "recovery_ineligible",
                "reason_code": "missing_interpretation",
                "slot_id": "slot-1",
            }
        ],
        [
            {
                "blocker_class": "recovery_ineligible",
                "interpretation": "unknown_interpretation",
                "reason_code": "unknown_interpretation",
                "slot_id": "slot-1",
            }
        ],
        [
            {
                "blocker_class": "recovery_ineligible",
                "interpretation": (
                    "structural_or_validation_blocker"
                ),
                "reason_code": "inconsistent_interpretation",
                "slot_id": "slot-1",
            }
        ],
        [
            {
                "blocker_class": "recovery_ineligible",
                "interpretation": "lawful_recovery_ineligible",
                "reason_code": "foreign_slot",
                "slot_id": "slot-foreign",
            }
        ],
        [
            {
                "blocker_class": "recovery_ineligible",
                "interpretation": "lawful_recovery_ineligible",
                "reason_code": "duplicate_one",
                "slot_id": "slot-1",
            },
            {
                "blocker_class": "recovery_ineligible",
                "interpretation": "lawful_recovery_ineligible",
                "reason_code": "duplicate_two",
                "slot_id": "slot-1",
            },
        ],
    ],
)
def test_required_needs_block_rejects_noncanonical_typed_facts(
    blocker_facts: list[dict[str, str]],
) -> None:
    state = mark_searchos_slot_unresolved(
        _state(),
        slot_id="slot-1",
        reason="offline_unresolved",
    )
    readiness = build_searchos_slice_a_readiness_v1(
        state=state,
        semantic_outcomes_by_slot={},
    )

    with pytest.raises(SearchOSRuntimeError):
        build_searchos_required_needs_block(
            readiness,
            blocker_facts=blocker_facts,
        )


def test_required_needs_block_rejects_foreign_scope_stale_readiness_and_malformed_slot() -> None:
    state = mark_searchos_slot_unresolved(
        _state(),
        slot_id="slot-1",
        reason="offline_unresolved",
    )
    readiness = build_searchos_slice_a_readiness_v1(
        state=state,
        semantic_outcomes_by_slot={},
    )
    state_with_readiness = record_searchos_readiness_projection(
        state,
        readiness=readiness,
    )
    block = build_searchos_required_needs_block(
        readiness,
        blocker_facts=_lawful_ineligible_facts(readiness),
    )
    assert validate_searchos_required_needs_block(
        block,
        state=state_with_readiness,
    ) == block

    for foreign_scope in (
        {"run_id": "run-foreign"},
        {"request_id": "request-foreign"},
        {
            "readiness_projection_ref": {
                **block["readiness_projection_ref"],
                "readiness_projection_digest": "f" * 64,
            }
        },
    ):
        with pytest.raises(
            SearchOSRuntimeError,
            match="run, request, or readiness ref is stale",
        ):
            validate_searchos_required_needs_block(
                _reenvelope_required_needs_block(
                    block,
                    **foreign_scope,
                ),
                state=state_with_readiness,
            )

    malformed_unresolved = deepcopy(
        block["unresolved_required_slots"]
    )
    malformed_unresolved[0]["slot_ref"].pop(
        "source_obligation_id"
    )
    with pytest.raises(
        SearchOSRuntimeError,
        match="malformed unresolved slot identity",
    ):
        validate_searchos_required_needs_block(
            _reenvelope_required_needs_block(
                block,
                unresolved_required_slots=malformed_unresolved,
            )
        )


def test_query_plan_admits_exact_model_followup_without_evaluator_or_expander() -> None:
    plan = QueryPlan().append(
        origin="search_planner",
        role=QueryPlanRole.INITIAL,
        status=QueryPlanStatus.ORDERED,
        authorized_query="initial query",
        iteration=1,
        order=1,
    )
    decision = {
        **_ref("judgment_decision", "followup"),
        "action": "PROPOSE_FOLLOWUP_QUERY",
        "followup_query": "exact model-authored query",
        "slot_ref": _ref("slot", "one"),
    }
    current, admission = plan.admit_searchos_followup_query(
        judgment_decision=decision,
        iteration=2,
    )
    assert current.items[-1].authorized_query == "exact model-authored query"
    assert current.items[-1].original_query == "exact model-authored query"
    assert admission["exact_query_text_preserved"] is True
    assert current.items[-1].metadata["evaluator_authority_used"] is False
    assert current.items[-1].metadata["expander_authority_used"] is False
    assert current.to_dict()["items"][: len(plan.items)] == plan.to_dict()["items"]
    duplicate = {**decision, "followup_query": "INITIAL QUERY"}
    with pytest.raises(SearchOSRuntimeError, match="materially equivalent"):
        plan.admit_searchos_followup_query(
            judgment_decision=duplicate,
            iteration=2,
        )


@pytest.mark.parametrize(
    "prior, proposed",
    [
        ("Alpha current official rule", "ALPHA CURRENT OFFICIAL RULE"),
        ("Alpha current official rule", "Alpha,  current official rule!"),
        (
            "Alpha current official operating rule source",
            "Alpha official current operating rule source",
        ),
    ],
)
def test_searchos_followup_rejects_materially_equivalent_query_before_discover(
    prior: str,
    proposed: str,
) -> None:
    plan = QueryPlan(plan_id="query-plan:material-equivalence").append(
        origin="initial",
        role=QueryPlanRole.INITIAL,
        status=QueryPlanStatus.ORDERED,
        authorized_query=prior,
        phase="initial",
        iteration=1,
        order=1,
    )
    decision = {
        "action": "PROPOSE_FOLLOWUP_QUERY",
        "followup_query": proposed,
        "judgment_decision_id": "searchos-decision:equivalent",
        "judgment_decision_digest": "a" * 64,
        "slot_ref": {"slot_id": "slot-1", "slot_digest": "b" * 64},
    }

    with pytest.raises(SearchOSRuntimeError, match="materially equivalent"):
        plan.admit_searchos_followup_query(
            judgment_decision=decision,
            iteration=2,
        )


def test_searchos_followup_admits_genuinely_distinct_query_unchanged() -> None:
    plan = QueryPlan(plan_id="query-plan:distinct").append(
        origin="initial",
        role=QueryPlanRole.INITIAL,
        status=QueryPlanStatus.ORDERED,
        authorized_query="Alpha current official operating rule source",
        phase="initial",
        iteration=1,
        order=1,
    )
    proposed = "Alpha historical enforcement exceptions court decisions"
    current, admission = plan.admit_searchos_followup_query(
        judgment_decision={
            "action": "PROPOSE_FOLLOWUP_QUERY",
            "followup_query": proposed,
            "judgment_decision_id": "searchos-decision:distinct",
            "judgment_decision_digest": "c" * 64,
            "slot_ref": {"slot_id": "slot-1", "slot_digest": "d" * 64},
        },
        iteration=2,
    )

    assert current.items[-1].authorized_query == proposed
    assert admission["exact_query_text_preserved"] is True


def test_runkernel_owns_judgment_readiness_block_and_downstream_guard() -> None:
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    policy = build_searchos_policy_snapshot(
        run_id="run-1", request_id="request-1", profile_name="Fast"
    )
    initialize = kernel.authorize_searchos_initialization(
        answer_contract_ref=_ref("answer_contract", "contract"),
        policy_snapshot=policy,
        active_slots=[_slot("slot-1")],
        initial_candidate_state_ref=_ref("candidate_state", "revision-1"),
    )
    kernel.reduce(
        Observation.from_action(
            initialize,
            observation_type=ObservationType.SEARCHOS_INITIALIZED,
            status=RunStageStatus.COMPLETED,
            payload={"searchos_state": initialize.inputs["searchos_state"]},
        )
    )
    state = kernel.state.searchos_state
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
    kernel.expose_searchos_candidate_window(window=window)
    reservation = kernel.reserve_searchos_judgment_round(slot_ids=["slot-1"])
    judgment = kernel.authorize_searchos_judgment(
        reservation_ref=reservation,
        slot_id="slot-1",
        candidate_window=window,
    )
    request = judgment.inputs["judgment_request"]
    kernel.reduce(
        Observation.from_action(
            judgment,
            observation_type=ObservationType.SEARCHOS_JUDGMENT_DECIDED,
            status=RunStageStatus.COMPLETED,
            payload={
                "model_output": {
                    "schema_version": "searchos_judgment_decision_v1",
                    "judgment_request_id": request["judgment_request_id"],
                    "judgment_request_digest": request["judgment_request_digest"],
                    "slot_id": "slot-1",
                    "action": "HANDOFF_UNRESOLVED",
                    "reason": "current candidates cannot resolve the required need",
                }
            },
        )
    )
    assert kernel.state.searchos_state["slots_by_id"]["slot-1"]["posture"] == (
        "unresolved_handoff"
    )
    readiness_action = kernel.authorize_searchos_slice_a_readiness(
        semantic_outcomes_by_slot={}
    )
    kernel.reduce(
        Observation.from_action(
            readiness_action,
            observation_type=ObservationType.SEARCHOS_SLICE_A_READINESS_DERIVED,
            status=RunStageStatus.COMPLETED,
            payload={"readiness": readiness_action.inputs["readiness"]},
        )
    )
    block_action = kernel.authorize_searchos_required_needs_block(
        blocker_facts=[
            {
                "blocker_class": "recovery_ineligible",
                "interpretation": "lawful_recovery_ineligible",
                "reason_code": (
                    "no_lawful_materially_novel_recovery_purpose"
                ),
                "slot_id": "slot-1",
            }
        ]
    )
    kernel.reduce(
        Observation.from_action(
            block_action,
            observation_type=ObservationType.SEARCHOS_REQUIRED_NEEDS_BLOCKED,
            status=RunStageStatus.COMPLETED,
            payload={"block": block_action.inputs["block"]},
        )
    )
    assert kernel.state.searchos_state["required_needs_block_ref"]["block_type"] == (
        SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED
    )
    assert kernel.state.projections[
        "searchos_required_needs_block"
    ]["blocker_facts"] == [
        {
            "blocker_class": "recovery_ineligible",
            "interpretation": "lawful_recovery_ineligible",
            "reason_code": (
                "no_lawful_materially_novel_recovery_purpose"
            ),
            "slot_id": "slot-1",
        }
    ]
    sufficiency_action = kernel.authorize(
        stage="sufficiency_must_remain_reachable",
        action_type=ActionType.SUFFICIENCY_JUDGMENT_DECIDE,
        reason="subordinate SearchOS facts require Sufficiency",
        inputs={},
        expected_observation_type=(
            ObservationType.SUFFICIENCY_JUDGMENT_DECIDED
        ),
    )
    assert sufficiency_action.action_type is (
        ActionType.SUFFICIENCY_JUDGMENT_DECIDE
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="requires Sufficiency adjudication",
    ):
        kernel.authorize(
            stage="forbidden_author",
            action_type=ActionType.AUTHOR_EXECUTE,
            reason="must remain closed",
            inputs={},
            expected_observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
        )
