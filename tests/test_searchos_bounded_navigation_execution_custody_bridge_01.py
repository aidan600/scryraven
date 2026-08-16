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
from core.cap_enforcement import RunCapExceeded
from core.evidence_ledger import EvidenceLedger
from core.evidence_ledger_candidate_custody import (
    build_evidence_ledger_observation_from_fetch_read_content_packet,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_navigation,
    validate_fetch_read_content_packet,
)
from core.run_kernel import RunKernel, RunKernelTransitionError
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
    NAVIGATION_CUSTODIED,
    NAVIGATION_DESTINATION_FAILED,
    NAVIGATION_PENDING_EXECUTION,
    EphemeralNavigationLocatorStore,
    NavigationOption,
    NavigationRuntimeError,
    admit_navigation_options_from_markdown,
    build_searchos_navigation_acquisition_need_proposal,
    execute_navigation_selection,
    execute_searchos_navigation_read_to_custody,
    project_navigation_window,
)

RUN_ID = "navigation-bridge-run"
REQUEST_ID = "navigation-bridge-request"
CHILD_URL = "https://official.example.test/root/child"
OTHER_URL = "https://official.example.test/root/other"


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
            "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
            "navigation_candidate_id": navigation_window[0][
                "navigation_candidate_ref"
            ]["navigation_candidate_id"],
            "reason": "The selected breadcrumb is the one bounded next read.",
            "read_custody_assessments": [
                {
                    "read_custody_material_id": parent["read_custody_material_id"],
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


def _ordinary_proposal(kernel: RunKernel) -> AcquisitionNeedProposalV1:
    snapshot = kernel.acquisition_authority_snapshot()
    return AcquisitionNeedProposalV1.create(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        producer_surface="tests.ordinary_candidate",
        answer_contract_ref=snapshot["answer_contract_ref"],
        source_obligation_ref=snapshot["source_obligations_by_id"]["obligation-1"],
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


def _lineage(
    kernel: RunKernel,
    option: NavigationOption,
    parent: dict[str, Any],
) -> dict[str, Any]:
    return {
        "slot_ref": kernel.state.searchos_state["slots_by_id"]["slot-1"][
            "slot_ref"
        ],
        "navigation_option_ref": option.ref(),
        "navigation_selection_ref": option.active_selection_ref,
        "destination_binding_ref": option.destination_binding_ref,
        "parent_read_custody_ref": parent,
    }


def _navigation_packet(*, attempted_url: str = CHILD_URL) -> dict[str, Any]:
    kernel, _store, option, parent = _selected_navigation()
    proposal = _proposal(kernel, option, parent)
    return build_fetch_read_content_packet_from_navigation(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        answer_contract_ref=proposal.answer_contract_ref,
        component_ref=proposal.component_ref,
        source_obligation_ref=proposal.source_obligation_ref,
        navigation_lineage=_lineage(kernel, option, parent),
        terminal_receipt_ref=_ref("terminal_receipt", "child"),
        custody_authorization_ref=_ref("custody_authorization", "child"),
        sanitized_material={
            "fetch_read_status": "readable",
            "attempted_url": attempted_url,
            "content_title": "Official child",
            "bounded_text": "Offline child material.",
            "bounded_text_sanitized": True,
            "bounded_text_bounded": True,
        },
    )


def test_navigation_custody_observation_atomically_owns_canonical_candidate() -> None:
    packet = _navigation_packet()
    reference = packet["reference_records"][0]
    observation = build_evidence_ledger_observation_from_fetch_read_content_packet(
        packet
    ).to_dict()
    expected_id = "searchos_custody_candidate:" + _digest(
        {
            "identity_kind": "searchos_navigation_custody_candidate_v1",
            "navigation_content_reference": {
                "reference_id": reference["reference_id"],
                "reference_digest": reference["reference_digest"],
            },
            "fetch_read_content_packet": {
                "packet_id": packet["packet_id"],
                "packet_digest": packet["packet_digest"],
            },
        }
    )

    assert len(observation["candidates"]) == 1
    assert len(observation["fetch_read_candidate_custody"]) == 1
    candidate = observation["candidates"][0]
    custody = observation["fetch_read_candidate_custody"][0]
    assert candidate["candidate_id"] == custody["candidate_id"] == expected_id
    assert candidate["url"] == reference["attempted_url"]
    assert candidate["title"] == reference["content_title"]
    assert candidate["disposition"] == "observed"
    assert candidate["evidence_material_type"] == "searchos_read_custody"
    assert candidate["eligible_for_stronger_obligation"] is False
    assert candidate["final_evidence_eligible"] is False
    assert custody["reference_id"] == reference["reference_id"]
    assert custody["reference_digest"] == reference["reference_digest"]
    assert custody["fetch_read_content_packet_id"] == packet["packet_id"]
    assert custody["fetch_read_content_packet_digest"] == packet["packet_digest"]
    assert custody["lineage_only"] is True

    ledger = EvidenceLedger().reduce_observation(observation)
    projection = ledger.to_projection().to_dict()
    record = projection["candidate_records"][0]
    physical = ledger.to_fetch_read_candidate_custody_projection()[
        "fetch_read_candidate_custody_records"
    ][0]
    assert record["candidate_id"] == physical["candidate_id"] == expected_id
    before_replay = (
        deepcopy(projection),
        deepcopy(ledger.to_fetch_read_candidate_custody_projection()),
    )
    ledger.reduce_observation(observation)
    assert (
        ledger.to_projection().to_dict(),
        ledger.to_fetch_read_candidate_custody_projection(),
    ) == before_replay


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


def test_reused_execution_authorization_is_zero_additional_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.authorized_acquisition_runtime as acquisition_runtime

    kernel, store, option, parent = _selected_navigation()
    proposal = _proposal(kernel, option, parent)
    original = acquisition_runtime.execute_authorized_acquisition_work_order
    captured: dict[str, Any] = {}
    calls = 0

    def transport(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"markdown": "Offline child material."}

    def capture(action: Any, **kwargs: Any) -> Any:
        captured.update(action=action, kwargs=kwargs)
        return original(action, **kwargs)

    monkeypatch.setattr(
        acquisition_runtime,
        "execute_authorized_acquisition_work_order",
        capture,
    )
    execute_acquisition_work_order_to_terminal(
        run_kernel=kernel,
        proposal=proposal,
        available_providers={"linkup": True, "tavily": False},
        transports=AcquisitionTransports(linkup_fetch=transport),
        transient_destination_resolver=lambda: store.consume_once_for_execution(
            option.destination_binding_ref
        ),
    )
    assert calls == 1
    with pytest.raises(AcquisitionControlError, match="already_reduced"):
        original(captured["action"], **captured["kwargs"])
    assert calls == 1


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

    result = execute_acquisition_work_order_to_terminal(
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
    assert result["status"] == "failed"
    assert result["terminal_receipt"].terminal_status == "failed"
    assert calls == 0


def test_ordinary_candidate_v1_serialization_has_no_navigation_fields() -> None:
    kernel = _kernel()
    proposal = _ordinary_proposal(kernel)
    before = proposal.to_dict()
    round_trip = AcquisitionNeedProposalV1.from_dict(before).to_dict()
    assert round_trip == before
    assert "origin" not in before
    assert "destination_binding_ref" not in before
    assert kernel.state.searchos_state == {}
    assert SearchOSSlotPosture.AWAITING_NAVIGATION_EXECUTION.value not in (
        kernel.state.projections
    )


def test_navigation_fetchread_rejects_redigested_url_binding_mismatch() -> None:
    import core.fetch_read_content_reference as fetch_read

    packet = _navigation_packet()
    reference = packet["reference_records"][0]
    reference["attempted_url"] = OTHER_URL
    reference_digest = fetch_read._digest_json(
        fetch_read._reference_digest_payload(reference)
    )
    reference["reference_digest"] = reference_digest
    reference["reference_id"] = (
        f"sanitized-content-reference:{REQUEST_ID}:{reference_digest[:16]}"
    )
    packet_digest = fetch_read._digest_json(fetch_read._packet_digest_payload(packet))
    packet["packet_digest"] = packet_digest
    packet["packet_id"] = f"fetch-read-content-packet:{REQUEST_ID}:{packet_digest[:16]}"
    reference["packet_id"] = packet["packet_id"]
    reference["packet_digest"] = packet_digest
    with pytest.raises(ValueError, match="binding"):
        validate_fetch_read_content_packet(packet)
    with pytest.raises(ValueError, match="binding"):
        _navigation_packet(attempted_url=OTHER_URL)


@pytest.mark.parametrize("failure", ["missing_locator", "run_cap"])
def test_pretransport_navigation_failure_is_terminal_and_nonreplayable(
    failure: str,
) -> None:
    kernel, store, option, parent = _selected_navigation()
    before = deepcopy(kernel.state.searchos_state)
    calls = 0

    def transport(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"markdown": "must not execute"}

    def cap_failure() -> None:
        raise RunCapExceeded("fetch_read_operations cap exceeded")

    if failure == "missing_locator":
        store.consume_once_for_execution(option.destination_binding_ref)
    result = execute_searchos_navigation_read_to_custody(
        run_kernel=kernel,
        locator_store=store,
        navigation_lineage=_lineage(kernel, option, parent),
        available_providers={"linkup": True, "tavily": False},
        acquisition_transports=AcquisitionTransports(linkup_fetch=transport),
        before_transport=cap_failure if failure == "run_cap" else None,
    )
    control = kernel.state.acquisition_control_state
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    current_option = NavigationOption.from_dict(
        next(iter(kernel.state.searchos_state["navigation"]["options_by_id"].values()))
    )
    assert result["provider_calls_attempted"] == calls == 0
    assert len(control["execution_observations_by_id"]) == 1
    assert len(control["terminal_receipts_by_operation_key"]) == 1
    assert control["active_by_source_obligation"] == {}
    assert len(control["exhausted_operation_keys"]) == 1
    assert current_option.disposition == NAVIGATION_DESTINATION_FAILED
    assert slot["posture"] == (
        SearchOSSlotPosture.BUDGET_EXHAUSTED.value
        if failure == "run_cap"
        else SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    )
    assert slot["custody_refs"] == before["slots_by_id"]["slot-1"]["custody_refs"]
    assert kernel.state.searchos_state["navigation"]["edges"] == before["navigation"]["edges"]
    assert kernel.state.searchos_state["budget"] == before["budget"]
    assert store.committed_count == 0
    assert kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
        "custody_record_count"
    ] == 0


def test_ordinary_candidate_run_cap_still_propagates_after_terminal_receipt() -> None:
    kernel = _kernel()
    calls = 0

    def transport(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"markdown": "must not execute"}

    with pytest.raises(RunCapExceeded, match="fetch_read_operations"):
        execute_acquisition_work_order_to_terminal(
            run_kernel=kernel,
            proposal=_ordinary_proposal(kernel),
            available_providers={"linkup": True, "tavily": False},
            transports=AcquisitionTransports(linkup_fetch=transport),
            before_transport=lambda: (_ for _ in ()).throw(
                RunCapExceeded("fetch_read_operations cap exceeded")
            ),
        )
    control = kernel.state.acquisition_control_state
    assert calls == 0 and control["active_by_source_obligation"] == {}
    assert len(control["terminal_receipts_by_operation_key"]) == 1


@pytest.mark.parametrize("failure", ["authorization", "reduction"])
def test_post_ledger_searchos_failure_preserves_truthful_custody(
    failure: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, store, option, parent = _selected_navigation()
    calls = 0
    original_reduce = kernel.reduce

    def fail_after_ledger_commit(observation: Any) -> Any:
        action = kernel.state.issued_actions.get(observation.action_id)
        if action and failure == "reduction" and action.stage == (
            "searchos_read_custody_admission"
        ):
            raise RunKernelTransitionError("synthetic SearchOS custody rejection")
        return original_reduce(observation)

    monkeypatch.setattr(kernel, "reduce", fail_after_ledger_commit)
    if failure == "authorization":
        monkeypatch.setattr(
            kernel,
            "authorize_searchos_read_custody_admission",
            lambda **_kwargs: (_ for _ in ()).throw(
                RunKernelTransitionError("synthetic SearchOS custody rejection")
            ),
        )

    def transport(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"markdown": "Offline child material with one bounded fact."}

    with pytest.raises(
        NavigationRuntimeError,
        match="navigation_custody_committed_searchos_admission_failed",
    ):
        execute_searchos_navigation_read_to_custody(
            run_kernel=kernel,
            locator_store=store,
            navigation_lineage=_lineage(kernel, option, parent),
            available_providers={"linkup": True, "tavily": False},
            acquisition_transports=AcquisitionTransports(linkup_fetch=transport),
        )
    ledger = kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()
    slot = kernel.state.searchos_state["slots_by_id"]["slot-1"]
    current_option = NavigationOption.from_dict(
        next(iter(kernel.state.searchos_state["navigation"]["options_by_id"].values()))
    )
    assert ledger["custody_record_count"] == 1
    physical = ledger["fetch_read_candidate_custody_records"][0]
    assert physical["attempted_url"] == CHILD_URL
    assert physical["candidate_id"] in {
        item["candidate_id"]
        for item in kernel.state.evidence_ledger.to_projection().to_dict()[
            "candidate_records"
        ]
    }
    assert current_option.disposition != NAVIGATION_DESTINATION_FAILED
    assert slot["posture"] != SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    assert calls == 1 and store.committed_count == 0


def test_success_reuses_fetchread_evidenceledger_and_searchos_custody() -> None:
    kernel, store, option, parent = _selected_navigation()
    before = deepcopy(kernel.state.searchos_state)
    result = execute_searchos_navigation_read_to_custody(
        run_kernel=kernel,
        locator_store=store,
        navigation_lineage=_lineage(kernel, option, parent),
        available_providers={"linkup": True, "tavily": False},
        acquisition_transports=AcquisitionTransports(
            linkup_fetch=lambda _payload: {
                "markdown": "Offline child material with one bounded fact."
            }
        ),
    )

    after = kernel.state.searchos_state
    before_slot = before["slots_by_id"]["slot-1"]
    after_slot = after["slots_by_id"]["slot-1"]
    after_option = NavigationOption.from_dict(
        next(iter(after["navigation"]["options_by_id"].values()))
    )
    assert result["status"] == NAVIGATION_CUSTODIED
    assert result["provider_calls_attempted"] == 1
    assert result["provider_calls_completed"] == 1
    assert after_slot["posture"] == SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    assert after_option.disposition == NAVIGATION_CUSTODIED
    assert len(after_slot["custody_refs"]) == 2
    assert parent in after_slot["custody_refs"]
    assert after_slot["read_nomination_count"] == before_slot["read_nomination_count"]
    assert after_slot["navigation_selection_count"] == before_slot[
        "navigation_selection_count"
    ]
    assert after["navigation"]["edges"] == before["navigation"]["edges"]
    assert after["budget"] == before["budget"]
    assert CHILD_URL not in json.dumps(after_slot["custody_refs"][-1], sort_keys=True)
    ledger = kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()
    assert ledger["custody_record_count"] == 1
    record = ledger["fetch_read_candidate_custody_records"][0]
    assert record["origin"] == "searchos_navigation"
    canonical_candidate_id = record["candidate_id"]
    assert canonical_candidate_id.startswith("searchos_custody_candidate:")
    assert len(canonical_candidate_id.split(":", 1)[1]) == 64
    assert after_slot["custody_refs"][-1]["evidence_ledger_candidate_id"] == (
        canonical_candidate_id
    )
    candidate = next(
        item
        for item in kernel.state.evidence_ledger.to_projection().to_dict()[
            "candidate_records"
        ]
        if item["candidate_id"] == canonical_candidate_id
    )
    assert candidate["fact_disposition"] == "observed"
    assert candidate["evidence_material_type"] == "searchos_read_custody"
    assert record["attempted_url"] == CHILD_URL
    assert record["semantic_support_created"] is False
    assert record["citation_eligible"] is False
    assert store.committed_count == 0


@pytest.mark.parametrize(
    "case",
    [
        "route_block",
        "transport_failure",
        "unreadable",
        "packet_rejection",
        "custody_rejection",
        "ledger_authorization_rejection",
        "ledger_reduction_rejection",
    ],
)
def test_destination_failures_reopen_slot_without_retry(
    case: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, store, option, parent = _selected_navigation()
    before = deepcopy(kernel.state.searchos_state)
    calls = 0

    def transport(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if case == "transport_failure":
            raise RuntimeError("offline selected transport failure")
        return {
            "markdown": "" if case == "unreadable" else "bounded child fact"
        }

    if case == "packet_rejection":
        import core.fetch_read_content_reference as fetch_read

        monkeypatch.setattr(
            fetch_read,
            "build_fetch_read_content_packet_from_navigation",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("packet rejected")),
        )
    if case == "custody_rejection":
        monkeypatch.setattr(
            kernel,
            "authorize_acquisition_custody_consumption",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("custody rejected")
            ),
        )
    if case == "ledger_authorization_rejection":
        monkeypatch.setattr(
            kernel,
            "authorize_evidence_ledger_reduction",
            lambda **_kwargs: (_ for _ in ()).throw(
                RuntimeError("ledger rejected")
            ),
        )
    if case == "ledger_reduction_rejection":
        monkeypatch.setattr(
            type(kernel.state.evidence_ledger),
            "reduce_observation",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("ledger rejected")),
        )
    result = execute_searchos_navigation_read_to_custody(
        run_kernel=kernel,
        locator_store=store,
        navigation_lineage=_lineage(kernel, option, parent),
        available_providers={
            "linkup": case != "route_block",
            "tavily": False,
        },
        acquisition_transports=AcquisitionTransports(linkup_fetch=transport),
    )

    after = kernel.state.searchos_state
    after_slot = after["slots_by_id"]["slot-1"]
    after_option = NavigationOption.from_dict(
        next(iter(after["navigation"]["options_by_id"].values()))
    )
    assert result["status"] == "failed"
    assert after_slot["posture"] == SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    assert after_option.disposition == NAVIGATION_DESTINATION_FAILED
    assert after_slot["custody_refs"] == before["slots_by_id"]["slot-1"][
        "custody_refs"
    ]
    assert after["navigation"]["edges"] == before["navigation"]["edges"]
    assert after["budget"] == before["budget"]
    assert calls <= 1
    assert store.committed_count == 0
    assert kernel.state.evidence_ledger.to_fetch_read_candidate_custody_projection()[
        "custody_record_count"
    ] == 0
    assert kernel.state.evidence_ledger.to_projection().to_dict()[
        "candidate_count"
    ] == 0


@pytest.mark.parametrize(
    "tamper",
    [
        "wrong_slot",
        "stale_revision",
        "selection",
        "binding",
        "parent",
        "component",
        "obligation",
        "contract",
        "locator_scope",
    ],
)
def test_authority_tampering_is_zero_transport(tamper: str) -> None:
    kernel, store, option, parent = _selected_navigation()
    lineage = _lineage(kernel, option, parent)
    if tamper == "wrong_slot":
        lineage["slot_ref"] = {**lineage["slot_ref"], "slot_id": "wrong-slot"}
    elif tamper == "stale_revision":
        lineage["navigation_option_ref"] = {
            **lineage["navigation_option_ref"],
            "revision": 1,
        }
    elif tamper == "selection":
        lineage["navigation_selection_ref"] = _ref("navigation_selection", "wrong")
    elif tamper == "binding":
        lineage["destination_binding_ref"] = {
            **option.destination_binding_ref,
            "destination_binding_digest": "f" * 64,
        }
    elif tamper == "parent":
        lineage["parent_read_custody_ref"] = _ref("read_custody_material", "wrong")
    elif tamper == "component":
        kernel.state.current_answer_contract["accepted_answer_component_refs"][0][
            "component_digest"
        ] = "d" * 64
    elif tamper == "obligation":
        kernel.state.search_executor_handoff_state[
            "source_obligation_candidate_refs"
        ][0]["reason"] = "changed obligation"
    elif tamper == "contract":
        kernel.state.current_answer_contract["accepted_contract_digest"] = "e" * 64
    else:
        store = EphemeralNavigationLocatorStore(
            run_id="wrong-run",
            request_id="wrong-request",
        )
    calls = 0

    def forbidden(_payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"markdown": "must not execute"}

    result = execute_searchos_navigation_read_to_custody(
        run_kernel=kernel,
        locator_store=store,
        navigation_lineage=lineage,
        available_providers={"linkup": True, "tavily": False},
        acquisition_transports=AcquisitionTransports(linkup_fetch=forbidden),
    )
    assert result["status"] == "failed"
    assert result["provider_calls_attempted"] == 0
    assert calls == 0
