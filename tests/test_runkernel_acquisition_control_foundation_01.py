"""Focused offline owner for RunKernel post-discovery acquisition control.

The tests in this module intentionally separate three authority questions:

* proposals can describe a bounded material need but cannot carry provider or
  downstream authority;
* RunKernel admits every transition and owns canonical active/terminal state;
* ``core.routing`` is the first and only policy owner that selects a provider,
  while the low-level adapter remains independently usable and mechanical.

No test in this module performs a live provider call.

Test path/node id: tests/test_runkernel_acquisition_control_foundation_01.py
Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: RunKernel post-discovery capability, route, execution, terminal,
and READ custody authority.
High-custody or closed-this-phase surface, if any: live provider transports and
new Focused/Map/Crawl/premium execution remain closed; retained READ material is
kept outside RunKernel state.
Runtime/product path guarded: selected-candidate nontrigger behavior plus the
RunKernel-owned post-discovery acquisition transitions and mechanical adapter
seam for an independently established material need.
Expected cost: 55 synthetic offline cases in under one second locally.
Promotion posture: remain phase_focus until a later convergence phase selects a
smaller durable sentinel.
Demotion/retirement condition: replace when an equal-or-stronger ordinary-path
suite owns the converged exact-URL and final-custody boundary.
Why not fast_pr: this is a detailed phase authority matrix, not ordinary PR tax.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
from urllib.parse import urlsplit

import pytest

import core.authorized_acquisition_runtime as acquisition_runtime
import core.pipeline_orchestrator as orchestrator
from core.acquisition_adapters import (
    dispatch_acquisition_for_offline_target_safety_validation,
)
from core.acquisition_contracts import (
    AcquisitionExecutionResult,
    AcquisitionExecutionStatus,
    AcquisitionRequest,
)
from core.acquisition_control import (
    AcquisitionControlError,
    AcquisitionExecutionObservationV1,
    AcquisitionNeedProposalV1,
    derive_acquisition_capability_decision,
    initial_acquisition_control_state,
    stable_json_digest,
    validate_selected_candidate_material_need_proposal,
)
from core.authorized_acquisition_runtime import (
    AcquisitionCapabilityDecisionRuntimeResult,
    AcquisitionRouteRuntimeResult,
    AcquisitionWorkOrderAdmissionRuntimeResult,
    OfflineAcquisitionTransportFixtureV1,
    execute_acquisition_capability_decision_action,
    execute_acquisition_route_action_for_offline_target_safety_validation,
    execute_acquisition_terminal_reduction_action,
    execute_acquisition_work_order_admission_action,
    execute_authorized_acquisition_work_order_for_offline_target_safety_validation,
)
from core.cap_enforcement import RunCapPolicy
from core.network_target_safety import NetworkTargetResolutionSnapshotV1
from core.routing import (
    AcquisitionCapability,
    OfflineProviderTargetSafetyValidationAuthorityV1,
    ProviderCapabilityRequest,
    acquisition_routing_policy_ref,
    provider_operation_identity,
    route_provider_capability_for_offline_target_safety_validation,
)
from core.run_kernel import (
    ActionType,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
)
from tests.helpers.offline_ordinary_pipeline import scrub_offline_runtime
from tests.test_ag_ordinary_live_source_custody_integration_01 import (
    FakeSourceFetchRead,
    _candidate_results,
    _run_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

RUN_ID = "acquisition-control-run"
REQUEST_ID = "acquisition-control-request"
CONTRACT_VERSION = "contract-v1"
CONTRACT_DIGEST = "a" * 64
COMPONENT_ID = "answer-component-1"
COMPONENT_REVISION = "component-r1"
COMPONENT_DIGEST = "b" * 64
OBLIGATION_ID = "source-obligation-1"
READ_URL = "https://official.example.test/rule"

READ_PROVIDER_ELIGIBILITY = {
    provider_operation_identity(
        provider="linkup",
        capability=AcquisitionCapability.READ,
        operation="fetch",
        variant="known_url",
    ): True,
    provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.READ,
        operation="extract",
        variant="basic",
    ): True,
}


def _snapshots_for_urls(
    urls: tuple[str, ...],
    *,
    address: str = "93.184.216.34",
) -> tuple[NetworkTargetResolutionSnapshotV1, ...]:
    hosts = sorted(
        {
            str(urlsplit(url).hostname or "")
            for url in urls
            if urlsplit(url).hostname
        }
    )
    return tuple(
        NetworkTargetResolutionSnapshotV1.create(
            canonical_host=host,
            addresses=(address,),
        )
        for host in hosts
    )


def _proposal_snapshots(
    proposal: AcquisitionNeedProposalV1,
    *,
    address: str = "93.184.216.34",
) -> tuple[NetworkTargetResolutionSnapshotV1, ...]:
    urls = tuple(proposal.available_urls) + (
        ((proposal.root_url,) if proposal.root_url else ())
    )
    return _snapshots_for_urls(urls, address=address)


def _kernel() -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    kernel.state.current_answer_contract = {
        "accepted_contract_version": CONTRACT_VERSION,
        "accepted_contract_digest": CONTRACT_DIGEST,
        "accepted_answer_component_refs": [
            {
                "component_id": COMPONENT_ID,
                "component_revision": COMPONENT_REVISION,
                "component_digest": COMPONENT_DIGEST,
                "source_obligation_candidate_ids": [OBLIGATION_ID],
            }
        ],
    }
    kernel.state.search_executor_handoff_state = {
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "contract_parent_kind": "current_answer_contract",
        "parent_current_contract_ref": {
            "source": "current_answer_contract",
            "contract_version": CONTRACT_VERSION,
            "contract_digest": CONTRACT_DIGEST,
        },
        "source_obligation_candidate_refs": [
            {
                "candidate_id": OBLIGATION_ID,
                "component_candidate_ids": [COMPONENT_ID],
                "required_source_class": "official_primary",
                "reason": "current official rule requires a primary source",
            }
        ],
    }
    return kernel


def _proposal(
    kernel: RunKernel,
    *,
    material_shape: str = "ordinary_single_page",
    advisory: str | None = "READ",
    url: str = READ_URL,
    candidate_suffix: str = "1",
    bounded_focus: Mapping[str, Any] | None = None,
    root_url: str | None = None,
    include_domains: tuple[str, ...] = (),
    exclude_domains: tuple[str, ...] = (),
    include_path_prefix: str | None = None,
    exclude_path_prefixes: tuple[str, ...] = (),
    explicit_multi_page_need: bool = False,
    previous_read_posture: str | None = None,
    requested_bounds: Mapping[str, int] | None = None,
) -> AcquisitionNeedProposalV1:
    snapshot = kernel.acquisition_authority_snapshot()
    component = snapshot["components_by_id"][COMPONENT_ID]
    obligation = snapshot["source_obligations_by_id"][OBLIGATION_ID]
    available_urls = (url,) if url else ()
    candidate_ref: dict[str, Any] = {}
    if material_shape in {
        "ordinary_single_page",
        "full_page_or_unknown",
        "narrow_section",
        "exact_field",
        "exact_table",
        "exact_rule",
    }:
        candidate_ref = {
            "candidate_id": f"candidate-{candidate_suffix}",
            "candidate_digest": (candidate_suffix * 64)[:64],
            "url": url,
        }
    return AcquisitionNeedProposalV1.create(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        producer_surface="tests.offline_acquisition_proposer",
        answer_contract_ref=snapshot["answer_contract_ref"],
        source_obligation_ref=obligation,
        component_ref=component,
        requested_material_shape=material_shape,
        candidate_ref=candidate_ref,
        available_urls=available_urls,
        root_url=root_url,
        bounded_focus=bounded_focus,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        include_path_prefix=include_path_prefix,
        exclude_path_prefixes=exclude_path_prefixes,
        requested_bounds=requested_bounds,
        explicit_multi_page_need=explicit_multi_page_need,
        previous_read_posture=previous_read_posture,
        advisory_proposed_capability=advisory,
    )


def test_independent_material_need_can_bind_to_selected_url_provenance() -> None:
    kernel = _kernel()
    snapshot = kernel.acquisition_authority_snapshot()
    candidate = {
        "candidate_id": "candidate-1",
        "candidate_digest": "1" * 64,
        "record_digest": "2" * 64,
        "url": READ_URL,
        "component_id": COMPONENT_ID,
        "source_obligation_candidate_ids": [OBLIGATION_ID],
    }
    packet = {
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "packet_id": "candidate-packet-1",
        "packet_digest": "3" * 64,
        "current_answer_contract_digest": CONTRACT_DIGEST,
        "candidate_records": [candidate],
    }
    proposal = AcquisitionNeedProposalV1.create(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        producer_surface="tests.independent_current_material_need",
        answer_contract_ref=snapshot["answer_contract_ref"],
        source_obligation_ref=snapshot["source_obligations_by_id"][OBLIGATION_ID],
        component_ref=snapshot["components_by_id"][COMPONENT_ID],
        requested_material_shape="ordinary_single_page",
        candidate_ref={
            "packet_id": packet["packet_id"],
            "packet_digest": packet["packet_digest"],
            "candidate_id": candidate["candidate_id"],
            "candidate_digest": candidate["candidate_digest"],
            "record_digest": candidate["record_digest"],
            "url": READ_URL,
        },
        available_urls=(READ_URL,),
        advisory_proposed_capability="READ",
    )

    validated = validate_selected_candidate_material_need_proposal(
        proposal=proposal,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        candidate_packet=packet,
        selected_candidate=candidate,
        authority_snapshot=snapshot,
    )

    assert validated is proposal


@dataclass(frozen=True)
class _AdmittedRead:
    proposal: AcquisitionNeedProposalV1
    decision_result: AcquisitionCapabilityDecisionRuntimeResult
    work_order_result: AcquisitionWorkOrderAdmissionRuntimeResult


def _admit_read(
    kernel: RunKernel,
    *,
    proposal: AcquisitionNeedProposalV1 | None = None,
) -> _AdmittedRead:
    admitted_proposal = proposal or _proposal(kernel)
    decision_action = kernel.authorize_acquisition_capability_decision(
        proposal=admitted_proposal,
        target_resolution_snapshots=_proposal_snapshots(admitted_proposal),
    )
    decision_result = execute_acquisition_capability_decision_action(
        decision_action,
        proposal=admitted_proposal,
        authority_snapshot=kernel.acquisition_authority_snapshot(),
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(decision_result.observation)
    work_order_action = kernel.authorize_acquisition_work_order_admission(
        capability_decision_ref=decision_result.decision.ref()
    )
    work_order_result = execute_acquisition_work_order_admission_action(
        work_order_action,
        proposal=admitted_proposal,
        decision=decision_result.decision,
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(work_order_result.observation)
    return _AdmittedRead(
        proposal=admitted_proposal,
        decision_result=decision_result,
        work_order_result=work_order_result,
    )


def _route_read(
    kernel: RunKernel,
    admitted: _AdmittedRead,
    *,
    availability: Mapping[str, bool] | None = None,
) -> AcquisitionRouteRuntimeResult:
    providers = dict(availability or {"linkup": True, "tavily": True})
    work_order = admitted.work_order_result.work_order
    validation_authority = _offline_validation_authority()
    route_action = (
        kernel.authorize_acquisition_route_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            provider_availability=providers,
            validation_authority=validation_authority,
        )
    )
    result = (
        execute_acquisition_route_action_for_offline_target_safety_validation(
            route_action,
            work_order=work_order,
            available_providers=providers,
            validation_authority=validation_authority,
            acquisition_control_state=(
                kernel.state.acquisition_control_state
            ),
        )
    )
    kernel.reduce(result.observation)
    return result


def _offline_validation_authority(
) -> OfflineProviderTargetSafetyValidationAuthorityV1:
    return OfflineProviderTargetSafetyValidationAuthorityV1.create(
        READ_PROVIDER_ELIGIBILITY
    )


def _authorize_offline_execution(
    kernel: RunKernel,
    admitted: _AdmittedRead,
    route: AcquisitionRouteRuntimeResult,
):
    return (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=admitted.work_order_result.work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )


def _execute_offline_fixture(
    action,
    *,
    kernel: RunKernel,
    work_order,
    route_observation,
    route_decision,
    response: Mapping[str, Any] | None = None,
    raise_transport_error: bool = False,
    before_transport=None,
    target_resolution_snapshots=(),
):
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response=response,
        raise_transport_error=raise_transport_error,
    )
    result = (
        execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
            action,
            run_kernel=kernel,
            work_order=work_order,
            route_observation=route_observation,
            route_decision=route_decision,
            validation_authority=_offline_validation_authority(),
            transport_fixture=fixture,
            before_transport=before_transport,
            target_resolution_snapshots=target_resolution_snapshots,
        )
    )
    return result, fixture


def _derive(
    kernel: RunKernel,
    proposal: AcquisitionNeedProposalV1,
    *,
    state: Mapping[str, Any] | None = None,
):
    return derive_acquisition_capability_decision(
        proposal=proposal,
        authority_snapshot=kernel.acquisition_authority_snapshot(),
        acquisition_control_state=(
            state
            if state is not None
            else initial_acquisition_control_state(
                run_id=RUN_ID,
                request_id=REQUEST_ID,
            )
        ),
        target_resolution_snapshots=_proposal_snapshots(proposal),
    )


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "provider",
        "provider_preference",
        "provider_operation",
        "provider_variant",
        "provider_output_type",
        "provider_availability",
        "transport_identity",
    ],
)
def test_proposal_rejects_provider_and_transport_fields(
    forbidden_field: str,
) -> None:
    payload = _proposal(_kernel()).to_dict()
    payload[forbidden_field] = "forged"

    with pytest.raises(AcquisitionControlError) as exc_info:
        AcquisitionNeedProposalV1.from_dict(payload)
    assert exc_info.value.code in {
        "proposal_unknown_fields",
        "proposal_forbidden_authority_fields",
    }


def test_proposal_rejects_rehashed_noncanonical_tokens() -> None:
    raw = _proposal(_kernel()).to_dict()
    raw["proposal_reason_code"] = "selected   candidate   read"
    core = {
        key: value
        for key, value in raw.items()
        if key not in {"proposal_id", "proposal_digest"}
    }
    digest = stable_json_digest(core)
    raw["proposal_digest"] = digest
    raw["proposal_id"] = (
        f"acquisition-need:{REQUEST_ID}:{digest[:20]}"
    )

    with pytest.raises(
        AcquisitionControlError,
        match="proposal_not_canonical",
    ):
        AcquisitionNeedProposalV1.from_dict(raw)


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "evidence_admission",
        "source_authority",
        "citation_eligibility",
        "source_obligation_satisfied",
        "sufficiency",
        "fap_authority",
        "author_instruction",
        "answer_text",
        "tool_instructions",
    ],
)
def test_proposal_rejects_downstream_authority_fields(
    forbidden_field: str,
) -> None:
    payload = _proposal(_kernel()).to_dict()
    payload[forbidden_field] = True

    with pytest.raises(AcquisitionControlError) as exc_info:
        AcquisitionNeedProposalV1.from_dict(payload)
    assert exc_info.value.code in {
        "proposal_unknown_fields",
        "proposal_forbidden_authority_fields",
    }


def test_nested_provider_or_authority_fields_are_rejected() -> None:
    payload = _proposal(_kernel()).to_dict()
    payload["bounded_focus"] = {
        "focus_text": "exact rule",
        "source_obligation_digest": "x",
        "component_revision": COMPONENT_REVISION,
        "provider": "forged",
    }

    with pytest.raises(AcquisitionControlError) as exc_info:
        AcquisitionNeedProposalV1.from_dict(payload)
    assert exc_info.value.code == "proposal_forbidden_authority_fields"


def test_advisory_capability_is_not_authority_and_conflict_blocks() -> None:
    kernel = _kernel()
    proposal = _proposal(kernel, advisory="MAP_SITE")

    decision = _derive(kernel, proposal)

    assert decision.derived_capability == "READ"
    assert decision.advisory_proposal_match_status == "conflict"
    assert decision.decision_status == "blocked"
    assert decision.block_code == "advisory_capability_conflict"


def test_stale_answer_contract_is_rejected_before_work_order() -> None:
    kernel = _kernel()
    proposal = _proposal(kernel)
    kernel.state.current_answer_contract["accepted_contract_digest"] = "c" * 64
    kernel.state.search_executor_handoff_state["parent_current_contract_ref"]["contract_digest"] = "c" * 64

    decision = _derive(kernel, proposal)

    assert decision.decision_status == "blocked"
    assert decision.block_code == "stale_answer_contract"


def test_stale_component_revision_is_rejected_before_work_order() -> None:
    kernel = _kernel()
    proposal = _proposal(kernel)
    component = kernel.state.current_answer_contract["accepted_answer_component_refs"][0]
    component["component_revision"] = "component-r2"
    component["component_digest"] = "d" * 64

    decision = _derive(kernel, proposal)

    assert decision.decision_status == "blocked"
    assert decision.block_code == "stale_component_revision"


def test_mismatched_source_obligation_is_rejected_before_work_order() -> None:
    kernel = _kernel()
    proposal = _proposal(kernel)
    payload = proposal.to_dict()
    payload["source_obligation_ref"]["source_obligation_digest"] = "e" * 64
    core = {key: value for key, value in payload.items() if key not in {"proposal_id", "proposal_digest"}}
    payload["proposal_digest"] = stable_json_digest(core)
    payload["proposal_id"] = f"acquisition-need:{REQUEST_ID}:{payload['proposal_digest'][:20]}"
    mismatched = AcquisitionNeedProposalV1.from_dict(payload)

    decision = _derive(kernel, mismatched)

    assert decision.decision_status == "blocked"
    assert decision.block_code == "mismatched_source_obligation"


def test_duplicate_completed_and_terminal_operations_are_rejected() -> None:
    kernel = _kernel()
    proposal = _proposal(kernel)
    initial = _derive(kernel, proposal)
    assert initial.operation_identity_key
    state = initial_acquisition_control_state(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    state["terminal_receipts_by_operation_key"][initial.operation_identity_key] = {
        "receipt_id": "receipt-1",
        "receipt_digest": "f" * 64,
        "terminal_status": "completed",
    }

    completed = _derive(kernel, proposal, state=state)
    state["terminal_receipts_by_operation_key"][initial.operation_identity_key]["terminal_status"] = "failed"
    failed = _derive(kernel, proposal, state=state)

    assert completed.block_code == "duplicate_completed_operation"
    assert failed.block_code == "duplicate_terminal_operation_retry_unlicensed"


def test_one_active_operation_per_source_obligation_blocks_second_candidate() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    assert admitted.work_order_result.work_order.work_order_id
    competing = _proposal(
        kernel,
        url="https://official.example.test/alternate",
        candidate_suffix="2",
    )

    decision = _derive(
        kernel,
        competing,
        state=kernel.state.acquisition_control_state,
    )

    assert decision.decision_status == "blocked"
    assert decision.block_code == "active_conflicting_operation"
    active = kernel.state.acquisition_control_state["active_by_source_obligation"]
    assert list(active) == [OBLIGATION_ID]


def test_stale_work_order_invalidation_releases_slot_for_current_lineage() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    work_order = admitted.work_order_result.work_order
    replacement_digest = "f" * 64
    kernel.state.current_answer_contract["accepted_contract_digest"] = (
        replacement_digest
    )
    kernel.state.search_executor_handoff_state[
        "parent_current_contract_ref"
    ]["contract_digest"] = replacement_digest

    terminal_action = kernel.authorize_acquisition_terminal_reduction(
        invalidated_work_order_ref=work_order.ref()
    )
    terminal = execute_acquisition_terminal_reduction_action(
        terminal_action,
        work_order=work_order,
        invalidation_code=terminal_action.inputs[
            "work_order_invalidation_code"
        ],
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(terminal.observation)

    assert terminal.terminal_receipt.block_or_failure_code == (
        "stale_answer_contract"
    )
    assert kernel.state.acquisition_control_state[
        "active_by_source_obligation"
    ] == {}
    replacement = _admit_read(kernel, proposal=_proposal(kernel))
    assert replacement.work_order_result.work_order.answer_contract_ref[
        "contract_digest"
    ] == replacement_digest


def test_runkernel_authorizes_route_and_provider_first_appears_in_route() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    work_order = admitted.work_order_result.work_order
    route = _route_read(kernel, admitted)

    assert route.route_observation.terminal_status == "selected"
    assert route.route_observation.selected_provider == "linkup"
    assert route.route_observation.routing_policy_ref == acquisition_routing_policy_ref()
    assert "provider" not in admitted.proposal.to_dict()
    assert "selected_provider" not in admitted.proposal.to_dict()
    assert "selected_provider" not in work_order.to_dict()
    assert work_order.authority_posture == "acquisition_execution_only"
    route_actions = [
        action for action in kernel.state.issued_actions.values() if action.action_type is ActionType.ACQUISITION_ROUTE
    ]
    assert len(route_actions) == 1
    assert route_actions[0].expected_observation_type is ObservationType.ACQUISITION_ROUTE_COMPLETED


@pytest.mark.parametrize(
    "availability",
    [
        {"linkup": True, "tavily": True},
        {"linkup": False, "tavily": True},
        {"linkup": False, "tavily": False},
    ],
)
def test_provider_availability_cannot_determine_capability(
    availability: Mapping[str, bool],
) -> None:
    kernel = _kernel()
    proposal = _proposal(kernel)
    state = initial_acquisition_control_state(run_id=RUN_ID, request_id=REQUEST_ID)
    state["test_only_provider_availability"] = dict(availability)

    decision = _derive(kernel, proposal, state=state)

    assert decision.derived_capability == "READ"
    assert decision.decision_status == "accepted"
    assert decision.prerequisite_evaluation["provider_availability_consulted"] is False


@pytest.mark.parametrize(
    "availability",
    [
        {"linkup": "false"},
        {"linkup": True, "unknown_provider": False},
    ],
)
def test_route_availability_requires_exact_boolean_known_provider_facts(
    availability: Mapping[str, object],
) -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    with pytest.raises(RunKernelTransitionError):
        kernel.authorize_acquisition_route(
            work_order_ref=admitted.work_order_result.work_order.ref(),
            provider_availability=availability,
        )


@pytest.mark.parametrize("mode", ["Fast", "Balanced", "Deep"])
def test_mode_cannot_determine_capability(mode: str) -> None:
    kernel = _kernel()
    kernel.state.request["mode"] = mode

    decision = _derive(kernel, _proposal(kernel))

    assert decision.derived_capability == "READ"
    assert decision.decision_status == "accepted"
    assert decision.prerequisite_evaluation["mode_or_complexity_consulted"] is False


def test_explicit_known_url_without_candidate_identity_derives_read() -> None:
    kernel = _kernel()
    proposal = _proposal(
        kernel,
        material_shape="explicit_known_url",
        advisory="READ",
    )

    decision = _derive(kernel, proposal)

    assert proposal.candidate_ref == {}
    assert decision.derived_capability == "READ"
    assert decision.decision_status == "accepted"
    assert decision.material_shape_interpretation == "explicit_known_url_read"
    assert decision.operation_identity_key


def test_acquisition_action_preserves_schema_bounded_long_url_exactly() -> None:
    kernel = _kernel()
    long_url = "https://official.example.test/" + ("a" * 900)
    proposal = _proposal(
        kernel,
        material_shape="explicit_known_url",
        advisory="READ",
        url=long_url,
    )

    admitted = _admit_read(kernel, proposal=proposal)

    assert admitted.work_order_result.work_order.selected_urls == (long_url,)


@pytest.mark.parametrize(
    ("requested_bounds", "block_code"),
    [
        ({"max_depth": 999}, "operation_bound_exceeds_code_owned_maximum"),
        ({"unowned_limit": 1}, "operation_bound_not_allowed"),
    ],
)
def test_crawl_requires_valid_code_owned_hard_bounds(
    requested_bounds: Mapping[str, int], block_code: str
) -> None:
    kernel = _kernel()
    decision = _derive(
        kernel,
        _proposal(
            kernel,
            material_shape="bounded_multi_page",
            advisory="CRAWL_SITE",
            url="",
            root_url="https://official.example.test/",
            include_domains=("official.example.test",),
            include_path_prefix="/program/",
            explicit_multi_page_need=True,
            requested_bounds=requested_bounds,
        ),
    )

    assert decision.derived_capability == "CRAWL_SITE"
    assert decision.decision_status == "blocked"
    assert decision.block_code == block_code
    assert decision.prerequisite_evaluation[
        "hard_operation_bounds_valid"
    ] is False


def test_route_block_reduces_terminally_and_releases_active_slot() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(
        kernel,
        admitted,
        availability={"linkup": False, "tavily": False},
    )
    assert route.route_observation.terminal_status == "blocked"
    terminal_action = kernel.authorize_acquisition_terminal_reduction(
        route_observation_ref=route.route_observation.ref()
    )
    terminal = execute_acquisition_terminal_reduction_action(
        terminal_action,
        work_order=admitted.work_order_result.work_order,
        route_observation=route.route_observation,
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(terminal.observation)

    control = kernel.state.acquisition_control_state
    receipt = terminal.terminal_receipt
    assert receipt.terminal_status == "blocked"
    assert receipt.block_or_failure_code
    assert control["active_by_source_obligation"] == {}
    assert (
        control["terminal_receipts_by_operation_key"][receipt.operation_identity_key]["receipt_id"]
        == receipt.receipt_id
    )
    assert control["exhausted_operation_keys"][receipt.operation_identity_key]["retry_licensed"] is False


def test_work_order_or_route_without_exact_execution_authorization_cannot_dispatch() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not be reached"}
    )

    work_order_action = next(
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type is ActionType.ACQUISITION_WORK_ORDER_ADMIT
    )
    route_action = next(
        action for action in kernel.state.issued_actions.values() if action.action_type is ActionType.ACQUISITION_ROUTE
    )
    for unauthorized_action in (work_order_action, route_action):
        with pytest.raises((ValueError, RunKernelTransitionError)):
            execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
                unauthorized_action,
                run_kernel=kernel,
                work_order=admitted.work_order_result.work_order,
                route_observation=route.route_observation,
                route_decision=route.route_decision,
                validation_authority=_offline_validation_authority(),
                transport_fixture=fixture,
                target_resolution_snapshots=_proposal_snapshots(
                    admitted.proposal
                ),
            )
    assert fixture.calls == 0


def test_stale_work_order_route_pair_cannot_dispatch() -> None:
    first_kernel = _kernel()
    first = _admit_read(first_kernel)
    first_route = _route_read(first_kernel, first)

    second_kernel = _kernel()
    second = _admit_read(
        second_kernel,
        proposal=_proposal(
            second_kernel,
            url="https://official.example.test/other",
            candidate_suffix="2",
        ),
    )
    second_route = _route_read(second_kernel, second)
    execution_action = _authorize_offline_execution(
        first_kernel,
        first,
        first_route,
    )
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not be reached"}
    )

    with pytest.raises(AcquisitionControlError):
        execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
            execution_action,
            run_kernel=first_kernel,
            work_order=first.work_order_result.work_order,
            route_observation=second_route.route_observation,
            route_decision=second_route.route_decision,
            validation_authority=_offline_validation_authority(),
            transport_fixture=fixture,
            target_resolution_snapshots=_proposal_snapshots(first.proposal),
        )
    assert fixture.calls == 0


def test_execution_authorization_is_single_claim_and_single_transport_call() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = _authorize_offline_execution(kernel, admitted, route)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "offline readable fixture"}
    )

    first_result = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
    )

    with pytest.raises(
        AcquisitionControlError,
        match="execution_authorization_already_claimed",
    ):
        execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
            action,
            run_kernel=kernel,
            work_order=work_order,
            route_observation=route.route_observation,
            route_decision=route.route_decision,
            validation_authority=_offline_validation_authority(),
            transport_fixture=fixture,
            target_resolution_snapshots=_proposal_snapshots(
                admitted.proposal
            ),
        )
    kernel.reduce(first_result.observation)
    with pytest.raises(
        RunKernelTransitionError,
        match="execution_authorization_already_active",
    ):
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    assert fixture.calls == 1


def test_current_lineage_is_rechecked_inside_guard_before_transport() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = _authorize_offline_execution(kernel, admitted, route)
    replacement_digest = "f" * 64
    kernel.state.current_answer_contract["accepted_contract_digest"] = (
        replacement_digest
    )
    kernel.state.search_executor_handoff_state[
        "parent_current_contract_ref"
    ]["contract_digest"] = replacement_digest
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not be reached"}
    )

    with pytest.raises(
        AcquisitionControlError,
        match="authorized_action_authority_snapshot_digest_mismatch",
    ):
        execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
            action,
            run_kernel=kernel,
            work_order=work_order,
            route_observation=route.route_observation,
            route_decision=route.route_decision,
            validation_authority=_offline_validation_authority(),
            transport_fixture=fixture,
            target_resolution_snapshots=_proposal_snapshots(
                admitted.proposal
            ),
        )
    assert fixture.calls == 0


def test_lineage_change_in_pretransport_hook_blocks_provider_call() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = _authorize_offline_execution(kernel, admitted, route)

    def stale_lineage() -> None:
        replacement_digest = "f" * 64
        kernel.state.current_answer_contract[
            "accepted_contract_digest"
        ] = replacement_digest
        kernel.state.search_executor_handoff_state[
            "parent_current_contract_ref"
        ]["contract_digest"] = replacement_digest

    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not be reached"}
    )

    result = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
        before_transport=stale_lineage,
    )

    assert result.execution_observation.terminal_status == "failed"
    assert result.execution_result.failure_code == "guarded_execution_failed_closed"
    assert result.execution_result.execution_claim_consumed is True
    assert result.execution_result.provider_calls_attempted == 0
    assert fixture.calls == 0


def test_selected_provider_failure_has_no_failure_time_fallback() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    execution_action = _authorize_offline_execution(
        kernel,
        admitted,
        route,
    )
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        raise_transport_error=True
    )

    result = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        execution_action,
        run_kernel=kernel,
        work_order=admitted.work_order_result.work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
    )

    assert result.execution_observation.terminal_status == "failed"
    assert result.execution_observation.provider_calls_attempted == 1
    assert (
        result.execution_observation.target_safety_summary[
            "urls_fetched_delta"
        ]
        == 1
    )
    assert result.execution_result.transport_posture == "selected_adapter_failed_no_fallback"
    assert fixture.calls == 1
    assert route.route_decision.selected_provider == "linkup"


def test_preclaim_adapter_return_is_an_invariant_not_a_fabricated_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = _authorize_offline_execution(kernel, admitted, route)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not be reached"}
    )
    cap_charges = 0

    def preclaim_block(
        request: AcquisitionRequest,
        **_kwargs: Any,
    ) -> AcquisitionExecutionResult:
        return AcquisitionExecutionResult(
            request=request,
            status=AcquisitionExecutionStatus.BLOCKED,
            block_code="synthetic_preclaim_adapter_block",
            transport_posture="blocked_before_transport",
        )

    def cap_charge() -> None:
        nonlocal cap_charges
        cap_charges += 1

    monkeypatch.setattr(
        acquisition_runtime,
        "dispatch_acquisition_for_offline_target_safety_validation",
        preclaim_block,
    )
    with pytest.raises(
        AcquisitionControlError,
        match="execution_adapter_returned_before_claim",
    ):
        execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
            action,
            run_kernel=kernel,
            work_order=work_order,
            route_observation=route.route_observation,
            route_decision=route.route_decision,
            validation_authority=_offline_validation_authority(),
            transport_fixture=fixture,
            before_transport=cap_charge,
            target_resolution_snapshots=_proposal_snapshots(
                admitted.proposal
            ),
        )

    authorization = kernel.state.acquisition_control_state[
        "execution_authorizations_by_id"
    ][action.action_id]
    assert authorization["claim_status"] == "authorized"
    assert authorization["transport_claimed"] is False
    assert fixture.calls == cap_charges == 0


def test_target_safety_transport_count_is_not_artifact_cardinality() -> None:
    artifact = SimpleNamespace(
        pages=(),
        requested_url=None,
        redirect_url=None,
        final_url=None,
        canonical_url=None,
    )

    summary = acquisition_runtime._execution_target_safety_summary(
        gate2_decisions=(),
        gate3_decisions=(),
        artifacts=(artifact, artifact),
        urls_fetched_delta=1,
    )

    assert summary["successful_artifact_count"] == 2
    assert summary["urls_fetched_delta"] == 1


def test_post_claim_projection_failure_is_terminalized_without_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = _authorize_offline_execution(kernel, admitted, route)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "offline readable fixture"}
    )

    def projection_failure(_artifact: Any) -> dict[str, Any]:
        raise AcquisitionControlError("synthetic_projection_failure")

    monkeypatch.setattr(
        acquisition_runtime,
        "_artifact_ref",
        projection_failure,
    )
    result = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
    )
    kernel.reduce(result.observation)
    terminal_action = kernel.authorize_acquisition_terminal_reduction(
        execution_observation_ref=result.execution_observation.ref()
    )
    terminal = execute_acquisition_terminal_reduction_action(
        terminal_action,
        work_order=work_order,
        route_observation=route.route_observation,
        execution_observation=result.execution_observation,
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(terminal.observation)

    assert fixture.calls == 1
    assert result.execution_observation.terminal_status == "failed"
    assert result.execution_observation.failure_or_block_code == (
        "guarded_execution_failed_closed"
    )
    assert kernel.state.acquisition_control_state[
        "active_by_source_obligation"
    ] == {}


def test_completed_execution_rejects_fabricated_artifact_digests() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = _authorize_offline_execution(kernel, admitted, route)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "offline readable fixture"}
    )
    result = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
    )
    forged = result.execution_observation.to_dict()
    forged_artifact = forged["artifact_refs"][0]
    forged_artifact["artifact_digest"] = "0" * 64
    forged_artifact["artifact_id"] = (
        f"acquisition-artifact:{work_order.work_order_id}:"
        f"{'0' * 20}"
    )
    forged_artifact["retained_digest"] = "0" * 64
    forged_artifact["retained_character_count"] = 0

    with pytest.raises(
        AcquisitionControlError,
        match="artifact_ref_identity_invalid",
    ):
        AcquisitionExecutionObservationV1.from_dict(forged)

    empty_completion = result.execution_observation.to_dict()
    empty_completion["artifact_refs"] = []
    empty_completion["provider_calls_attempted"] = 0
    empty_completion["provider_calls_completed"] = 0
    with pytest.raises(
        AcquisitionControlError,
        match="completed_execution_material_invalid",
    ):
        AcquisitionExecutionObservationV1.from_dict(empty_completion)


def test_low_level_offline_fixture_dispatch_remains_mechanical_without_runkernel() -> None:
    route = route_provider_capability_for_offline_target_safety_validation(
        ProviderCapabilityRequest(capability=AcquisitionCapability.READ),
        {"linkup": True, "tavily": False},
        validation_authority=_offline_validation_authority(),
    )
    request = AcquisitionRequest(
        acquisition_job_id="typed-runtime-read",
        route_decision=route,
        selected_urls=(READ_URL,),
        max_retained_characters=20_000,
        candidate_reference="candidate-typed-runtime",
    )
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "offline readable fixture"}
    )

    result = dispatch_acquisition_for_offline_target_safety_validation(
        request,
        transport_fixture=fixture,
    )

    assert result.succeeded is True
    assert result.provider_calls_attempted == 1
    assert fixture.calls == 1


def test_actual_ordinary_selected_candidate_does_not_start_acquisition_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch, available_search_providers=("tavily",))
    fetcher = FakeSourceFetchRead()
    cap_policy = RunCapPolicy(
        max_search_dispatches=20,
        max_fetch_read_operations=1,
        max_author_model_calls=20,
        max_smart_search_judgment_model_calls=20,
        max_retries=0,
    )
    child_kernels: list[RunKernel] = []
    original_source_custody = orchestrator.execute_ordinary_live_source_custody

    def capture_child_kernel(**kwargs: Any):
        child_kernels.append(kwargs["run_kernel"])
        return original_source_custody(**kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_live_source_custody",
        capture_child_kernel,
    )

    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
        provider_availability={"linkup": True, "tavily": False},
        cap_policy=cap_policy,
    )

    projection = outcome.execution_trace["ordinary_live_source_custody"]
    assert projection["failed_closed"] is False, projection
    assert projection["status"] == "not_needed"
    assert projection["candidate_selection_creates_material_need"] is False
    assert projection["acquisition_need_proposal_created"] is False
    assert projection["acquisition_work_order_created"] is False
    assert projection["acquisition_route_created"] is False
    assert projection["exact_url_cap_charged"] is False
    assert projection["exact_url_transport_attempted"] is False
    assert fetcher.calls == []
    assert cap_policy.fetch_read_operations == 0
    assert harness.forbidden_live_calls == []
    assert len(child_kernels) == 1

    child = child_kernels[0]
    assert child.state.acquisition_control_state == {}
    acquisition_action_types = [
        action.action_type
        for action in child.state.issued_actions.values()
        if action.action_type
        in {
            ActionType.ACQUISITION_CAPABILITY_DECIDE,
            ActionType.ACQUISITION_WORK_ORDER_ADMIT,
            ActionType.ACQUISITION_ROUTE,
            ActionType.ACQUISITION_EXECUTE,
            ActionType.ACQUISITION_TERMINAL_REDUCE,
            ActionType.ACQUISITION_CUSTODY_CONSUME,
        }
    ]
    assert acquisition_action_types == []


def test_exact_narrow_need_derives_focused_extract_then_blocks_requester() -> None:
    kernel = _kernel()
    snapshot = kernel.acquisition_authority_snapshot()
    obligation = snapshot["source_obligations_by_id"][OBLIGATION_ID]
    focus_core = {
        "focus_text": "exact permit threshold",
        "source_obligation_digest": obligation["source_obligation_digest"],
        "component_revision": COMPONENT_REVISION,
    }
    focus = {
        **focus_core,
        "focus_digest": stable_json_digest({"focus_text": focus_core["focus_text"]}),
    }
    proposal = _proposal(
        kernel,
        material_shape="exact_rule",
        advisory="FOCUSED_EXTRACT",
        bounded_focus=focus,
    )

    decision = _derive(kernel, proposal)

    assert decision.derived_capability == "FOCUSED_EXTRACT"
    assert decision.material_shape_interpretation == "exact_bounded_focus"
    assert decision.decision_status == "blocked"
    assert decision.block_code == "focused_extract_requester_not_installed"


def test_site_topology_derives_map_then_blocks_candidate_reentry() -> None:
    kernel = _kernel()
    decision = _derive(
        kernel,
        _proposal(
            kernel,
            material_shape="site_topology",
            advisory="MAP_SITE",
            url="",
            root_url="https://official.example.test/",
        ),
    )

    assert decision.derived_capability == "MAP_SITE"
    assert decision.material_shape_interpretation == "unknown_relevant_page_site_root"
    assert decision.decision_status == "blocked"
    assert decision.block_code == "map_candidate_reentry_not_installed"


def test_bounded_multi_page_derives_crawl_then_blocks_page_custody() -> None:
    kernel = _kernel()
    decision = _derive(
        kernel,
        _proposal(
            kernel,
            material_shape="bounded_multi_page",
            advisory="CRAWL_SITE",
            url="",
            root_url="https://official.example.test/",
            include_domains=("official.example.test",),
            exclude_domains=("archive.official.example.test",),
            include_path_prefix="/program/",
            exclude_path_prefixes=("/program/archive/",),
            explicit_multi_page_need=True,
            requested_bounds={"max_depth": 1, "max_pages": 4},
        ),
    )

    assert decision.derived_capability == "CRAWL_SITE"
    assert decision.material_shape_interpretation == "explicit_bounded_multi_page"
    assert decision.decision_status == "blocked"
    assert decision.block_code == "crawl_page_custody_not_installed"


def test_general_deep_derives_separate_premium_capability_and_blocks() -> None:
    kernel = _kernel()
    decision = _derive(
        kernel,
        _proposal(
            kernel,
            material_shape="premium_sequential_acquisition",
            advisory=None,
            url="",
        ),
    )

    assert decision.derived_capability == "PREMIUM_SEQUENTIAL_ACQUISITION"
    assert decision.decision_status == "blocked"
    assert decision.block_code == "premium_sequential_acquisition_not_licensed"


def test_static_authority_boundaries_and_orchestrator_sequencing_only() -> None:
    adapter_source = (CORE / "acquisition_adapters.py").read_text(encoding="utf-8")
    control_source = (CORE / "acquisition_control.py").read_text(encoding="utf-8")
    orchestrator_source = (CORE / "pipeline_orchestrator.py").read_text(encoding="utf-8")
    custody_source = (CORE / "ordinary_live_source_custody_runtime.py").read_text(encoding="utf-8")
    runtime_source = (CORE / "authorized_acquisition_runtime.py").read_text(encoding="utf-8")

    assert "core.run_kernel" not in adapter_source
    assert "route_provider_capability(" not in control_source
    assert "dispatch_acquisition(" not in custody_source
    assert "dispatch_acquisition(" in runtime_source
    assert "derive_acquisition_capability_decision(" not in orchestrator_source
    assert "route_provider_capability(" not in orchestrator_source
    assert "AcquisitionCapability." not in orchestrator_source

    orchestrator_tree = ast.parse(orchestrator_source)
    forbidden_imports = {
        "core.acquisition_control",
        "core.acquisition_adapters",
    }
    imported_modules = {
        node.module for node in ast.walk(orchestrator_tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported_modules.isdisjoint(forbidden_imports)


def test_dormant_map_crawl_and_deep_block_before_any_transport() -> None:
    source = (CORE / "acquisition_control.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}

    assert "dispatch_acquisition" not in calls
    assert "route_provider_capability" not in calls
    assert "map_candidate_reentry_not_installed" in source
    assert "crawl_page_custody_not_installed" in source
    assert "premium_sequential_acquisition_not_licensed" in source
