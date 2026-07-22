"""Focused offline proof for the inactive navigation execution/custody bridge."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any

import pytest

from core.acquisition_adapters import AcquisitionTransports
from core.acquisition_control import (
    ACQUISITION_TERMINAL_RECEIPT_SCHEMA_VERSION,
    AcquisitionControlError,
    AcquisitionNeedProposalV1,
)
from core.authorized_acquisition_runtime import (
    execute_acquisition_work_order_to_terminal,
)
from core.run_kernel import RunKernel
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
    SearchOSJudgmentAction,
    SearchOSSlotPosture,
    begin_searchos_judgment_round,
    build_candidate_use_window_v1,
    build_searchos_initial_state,
    build_searchos_navigation_judgment_request_v1,
    build_searchos_policy_snapshot,
    build_searchos_read_custody_material_ref,
    charge_searchos_judgment_call,
    record_searchos_candidate_window,
    reduce_searchos_judgment_decision,
    validate_searchos_judgment_model_output,
)
from core.searchos_navigation_runtime import (
    NAVIGATION_PENDING_EXECUTION,
    EphemeralNavigationLocatorStore,
    NavigationOption,
    NavigationRuntimeError,
    admit_navigation_options_from_markdown,
    build_searchos_navigation_acquisition_need_proposal,
    execute_navigation_selection,
    project_navigation_window,
)

RUN_ID = "navigation-bridge-run"
REQUEST_ID = "navigation-bridge-request"
CHILD_URL = "https://official.example.test/root/child"


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _ref(name: str, suffix: str) -> dict[str, str]:
    return {
        f"{name}_id": f"{name}:{suffix}",
        f"{name}_digest": _digest(suffix),
    }


def _refresh_state(state: dict[str, Any]) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    slots = dict(core["slots_by_id"])
    for slot_id, raw_slot in slots.items():
        slot = dict(raw_slot)
        slot.pop("slot_state_digest", None)
        slot["slot_state_digest"] = _digest(slot)
        slots[slot_id] = slot
    core["slots_by_id"] = slots
    digest = _digest(core)
    return {
        **core,
        "state_id": f"searchos-state:{digest[:24]}",
        "state_digest": digest,
        "replay_identity": f"searchos-state:{digest}",
    }


def _kernel() -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    kernel.state.current_answer_contract = {
        "accepted_contract_version": "contract-v1",
        "accepted_contract_digest": "a" * 64,
        "accepted_answer_component_refs": [
            {
                "component_id": "component-1",
                "component_revision": "component-r1",
                "component_digest": "b" * 64,
                "source_obligation_candidate_ids": ["obligation-1"],
            }
        ],
    }
    kernel.state.search_executor_handoff_state = {
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "contract_parent_kind": "current_answer_contract",
        "parent_current_contract_ref": {
            "source": "current_answer_contract",
            "contract_version": "contract-v1",
            "contract_digest": "a" * 64,
        },
        "source_obligation_candidate_refs": [
            {
                "candidate_id": "obligation-1",
                "component_candidate_ids": ["component-1"],
                "required_source_class": "official_primary",
                "reason": "one current official source is required",
            }
        ],
    }
    return kernel


def _selected_navigation() -> tuple[
    RunKernel,
    EphemeralNavigationLocatorStore,
    NavigationOption,
    dict[str, Any],
]:
    kernel = _kernel()
    snapshot = kernel.acquisition_authority_snapshot()
    component = snapshot["components_by_id"]["component-1"]
    obligation = snapshot["source_obligations_by_id"]["obligation-1"]
    policy = build_searchos_policy_snapshot(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        profile_name="Balanced",
        navigation_runtime_open=True,
    )
    state = build_searchos_initial_state(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        answer_contract_ref={
            "answer_contract_id": "answer-contract:current",
            "answer_contract_digest": snapshot["answer_contract_ref"][
                "contract_digest"
            ],
            "contract_version": snapshot["answer_contract_ref"][
                "contract_version"
            ],
            "contract_digest": snapshot["answer_contract_ref"][
                "contract_digest"
            ],
        },
        policy_snapshot=policy,
        active_slots=[
            {
                "slot_id": "slot-1",
                "component_ref": component,
                "source_obligation_ref": obligation,
                "requirement_posture": "required",
            }
        ],
        initial_candidate_state_ref=_ref("candidate_state", "revision-1"),
    )
    slot = dict(state["slots_by_id"]["slot-1"])
    parent_option = {
        **_ref("candidate_use_option", "parent"),
        "slot_id": "slot-1",
        "normalized_url": "https://official.example.test/root",
    }
    parent = build_searchos_read_custody_material_ref(
        slot_ref=slot["slot_ref"],
        candidate_use_option_ref=parent_option,
        custody_record={
            "normalized_url": "https://official.example.test/root",
            "fetch_read_content_packet_ref": _ref(
                "fetch_read_content_packet", "parent"
            ),
            "evidence_ledger_custody_ref": _ref(
                "evidence_ledger_custody", "parent"
            ),
            "evidence_ledger_candidate_id": "ledger-candidate:parent",
            "terminal_receipt_ref": _ref("terminal_receipt", "parent"),
            "custody_authorization_ref": _ref(
                "custody_authorization", "parent"
            ),
            "bounded_content_present": True,
        },
        same_normalized_url_reused=False,
    )
    slot["custody_refs"] = [parent]
    state["slots_by_id"]["slot-1"] = slot
    state = _refresh_state(state)
    store = EphemeralNavigationLocatorStore(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    state, _ = admit_navigation_options_from_markdown(
        state,
        slot_id="slot-1",
        parent_read_custody_ref=parent,
        parent_url="https://official.example.test/root",
        parent_depth=0,
        ancestor_physical_identity_digests=(),
        markdown_text="[child](/root/child)",
        locator_store=store,
    )
    slot = state["slots_by_id"]["slot-1"]
    candidate_window = build_candidate_use_window_v1(
        slot_ref=slot["slot_ref"],
        ordered_options=(),
        window_ordinal=1,
        policy_snapshot=state["policy_snapshot"],
    )
    state = record_searchos_candidate_window(state, window=candidate_window)
    state, reservation = begin_searchos_judgment_round(
        state,
        slot_ids=["slot-1"],
    )
    state, charge = charge_searchos_judgment_call(
        state,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    navigation_window = project_navigation_window(state, slot_id="slot-1")
    request = build_searchos_navigation_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_window=navigation_window,
        read_custody_refs=[parent],
    )
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
            "judgment_request_id": request["judgment_request_id"],
            "judgment_request_digest": request["judgment_request_digest"],
            "slot_id": "slot-1",
            "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
            "navigation_candidate_ref": navigation_window[0][
                "navigation_candidate_ref"
            ],
            "reason": "The selected breadcrumb is the one bounded next read.",
            "read_custody_assessments": [
                {
                    "reviewed_custody_ref": parent,
                    "material_disposition": "read_insufficient",
                    "reason_code": "needed_detail_absent",
                }
            ],
        },
    )
    kernel.state.searchos_state = reduce_searchos_judgment_decision(
        state,
        decision=decision,
    )
    action = kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=decision,
        navigation_candidate=navigation_window[0]["navigation_candidate_ref"],
    )
    observation = execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(kernel.state.searchos_state),
        locator_store=store,
    )
    kernel.reduce(observation)
    option = NavigationOption.from_dict(
        next(
            iter(
                kernel.state.searchos_state["navigation"][
                    "options_by_id"
                ].values()
            )
        )
    )
    assert option.disposition == NAVIGATION_PENDING_EXECUTION
    return kernel, store, option, parent


def _proposal(
    kernel: RunKernel,
    option: NavigationOption,
    parent: dict[str, Any],
) -> AcquisitionNeedProposalV1:
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    return build_searchos_navigation_acquisition_need_proposal(
        run_kernel=kernel,
        slot_ref=slot["slot_ref"],
        navigation_option_ref=option.ref(),
        navigation_selection_ref=option.active_selection_ref,
        destination_binding_ref=option.destination_binding_ref,
        parent_read_custody_ref=parent,
    )


def test_navigation_uses_url_free_v1_chain_and_consume_once_dispatch() -> None:
    kernel, store, option, parent = _selected_navigation()
    proposal = _proposal(kernel, option, parent)
    payloads: list[dict[str, Any]] = []

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        payloads.append(payload)
        assert store.committed_count == 0
        return {"markdown": "Offline child material with one bounded fact."}

    result = execute_acquisition_work_order_to_terminal(
        run_kernel=kernel,
        proposal=proposal,
        available_providers={"linkup": True, "tavily": False},
        transports=AcquisitionTransports(linkup_fetch=transport),
        transient_destination_resolver=lambda: store.consume_once_for_execution(
            option.destination_binding_ref
        ),
    )

    work_order = result["work_order"]
    assert proposal.schema_version == "acquisition_need_proposal_v1"
    assert proposal.origin == "searchos_navigation"
    assert proposal.candidate_ref == {} and proposal.available_urls == ()
    assert work_order.origin == "searchos_navigation"
    assert work_order.candidate_ref == {} and work_order.selected_urls == ()
    assert result["route_observation"].selected_provider == "linkup"
    assert payloads == [
        {
            "url": CHILD_URL,
            "extractImages": False,
            "includeRawHtml": False,
            "renderJs": False,
        }
    ]
    assert result["provider_calls_attempted"] == 1
    assert result["provider_calls_completed"] == 1
    assert result["terminal_receipt"].schema_version == (
        ACQUISITION_TERMINAL_RECEIPT_SCHEMA_VERSION
    )
    assert result["terminal_receipt"].terminal_status == "completed"
    canonical = json.dumps(
        {
            "proposal": proposal.to_dict(),
            "work_order": work_order.to_dict(),
            "execution": result["execution_observation"].to_dict(),
            "receipt": result["terminal_receipt"].to_dict(),
            "control": kernel.state.acquisition_control_state,
        },
        sort_keys=True,
    )
    assert CHILD_URL not in canonical
    assert "candidate_id" not in proposal.to_dict()
    assert "query_plan" not in canonical.casefold()
    trace = result["execution_observation"].to_dict()
    assert trace["provider_failure_fallback_attempted"] is False
    assert trace["capability_switch_attempted"] is False
    with pytest.raises(NavigationRuntimeError, match="binding_unavailable"):
        store.consume_once_for_execution(option.destination_binding_ref)


def test_mixed_origin_and_locator_scope_mismatch_fail_before_transport() -> None:
    kernel, _store, option, parent = _selected_navigation()
    proposal = _proposal(kernel, option, parent)
    with pytest.raises(AcquisitionControlError, match="branches_mixed"):
        AcquisitionNeedProposalV1.create(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            producer_surface="tests.invalid_mixed_origin",
            answer_contract_ref=proposal.answer_contract_ref,
            source_obligation_ref=proposal.source_obligation_ref,
            component_ref=proposal.component_ref,
            requested_material_shape="explicit_known_url",
            origin="searchos_navigation",
            destination_binding_ref=option.destination_binding_ref,
            available_urls=(CHILD_URL,),
        )
    wrong_scope = EphemeralNavigationLocatorStore(
        run_id="other-run",
        request_id="other-request",
    )
    calls = 0

    def forbidden(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"markdown": "must not execute"}

    with pytest.raises(NavigationRuntimeError, match="binding_unavailable"):
        execute_acquisition_work_order_to_terminal(
            run_kernel=kernel,
            proposal=proposal,
            available_providers={"linkup": True, "tavily": False},
            transports=AcquisitionTransports(linkup_fetch=forbidden),
            transient_destination_resolver=(
                lambda: wrong_scope.consume_once_for_execution(
                    option.destination_binding_ref
                )
            ),
        )
    assert calls == 0


def test_ordinary_candidate_v1_serialization_has_no_navigation_fields() -> None:
    kernel = _kernel()
    snapshot = kernel.acquisition_authority_snapshot()
    proposal = AcquisitionNeedProposalV1.create(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        producer_surface="tests.ordinary_candidate",
        answer_contract_ref=snapshot["answer_contract_ref"],
        source_obligation_ref=snapshot["source_obligations_by_id"][
            "obligation-1"
        ],
        component_ref=snapshot["components_by_id"]["component-1"],
        requested_material_shape="ordinary_single_page",
        candidate_ref={
            "candidate_id": "candidate-1",
            "candidate_digest": "c" * 64,
            "url": CHILD_URL,
        },
        available_urls=(CHILD_URL,),
        advisory_proposed_capability="READ",
    )
    before = proposal.to_dict()
    round_trip = AcquisitionNeedProposalV1.from_dict(before).to_dict()
    assert round_trip == before
    assert "origin" not in before
    assert "destination_binding_ref" not in before
    assert kernel.state.searchos_state == {}
    assert SearchOSSlotPosture.AWAITING_NAVIGATION_EXECUTION.value not in (
        kernel.state.projections
    )
