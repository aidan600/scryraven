"""Offline product-path proof for exact-URL network-target safety.

Test path/node id: tests/test_exact_url_network_target_safety_owner_01.py
Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: canonical target policy, route eligibility, RunKernel Gates 1-3,
terminal slot release/exhaustion, and custody denial after safety failure.
Closed surface: live DNS, provider transport, READ activation, Focused Extract,
semantic admission, and final-answer custody.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from inspect import signature
from pathlib import Path
from typing import Any

import pytest

import core.acquisition_contracts as acquisition_contracts
from core.acquisition_adapters import LINKUP_FETCH_URL, TAVILY_API_ROOT
from core.acquisition_contracts import AcquisitionRequest
from core.acquisition_control import (
    AcquisitionControlError,
    AcquisitionExecutionObservationV1,
    stable_json_digest,
)
from core.authorized_acquisition_runtime import (
    OfflineAcquisitionTransportFixtureV1,
    execute_acquisition_capability_decision_action,
    execute_acquisition_route_action,
    execute_acquisition_route_action_for_offline_target_safety_validation,
    execute_acquisition_terminal_reduction_action,
    execute_authorized_acquisition_work_order,
    execute_authorized_acquisition_work_order_for_offline_target_safety_validation,
)
from core.cap_enforcement import RunCapExceeded
from core.network_target_safety import (
    MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS,
    NetworkTargetFactKind,
    NetworkTargetResolutionSnapshotV1,
    NetworkTargetSafetyStage,
    NetworkTargetSafetyStatus,
    NetworkTargetTransportMode,
    canonical_resolution_snapshot_bundle,
    evaluate_network_target_safety,
)
from core.routing import (
    UNTRUSTED_EXACT_URL_TARGET_CLASS,
    AcquisitionCapability,
    DiscoverQualifier,
    OfflineProviderTargetSafetyValidationAuthorityV1,
    ProviderCapabilityRequest,
    RouteFidelity,
    provider_operation_identity,
    route_provider_capability,
    route_provider_capability_for_offline_target_safety_validation,
)
from core.run_kernel import RunKernel, RunKernelTransitionError
from tests.test_runkernel_acquisition_control_foundation_01 import (
    READ_URL,
    _admit_read,
    _kernel,
    _offline_validation_authority,
    _proposal,
    _proposal_snapshots,
    _route_read,
)


def _decision(url: str, *, snapshot=None):
    return evaluate_network_target_safety(
        url,
        stage=NetworkTargetSafetyStage.ADMISSION_PRE_ROUTE,
        transport_mode=NetworkTargetTransportMode.PROVIDER_MEDIATED,
        fact_kind=NetworkTargetFactKind.EXPLICIT_USER,
        resolver_snapshot=snapshot,
        lineage_ref={"run_id": "offline-safety-red-team"},
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "https:///missing-host",
        "http://127.0.0.1/private",
        "http://0.0.0.0/private",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/private",
        "http://172.16.0.1/private",
        "http://192.168.1.1/private",
        "http://[::1]/private",
        "http://[fe80::1]/private",
        "http://[fc00::1]/private",
        "http://[::]/private",
        "http://224.0.0.1/private",
        "http://[ff02::1]/private",
        "http://240.0.0.1/private",
        "http://192.0.2.1/private",
        "http://[2001:db8::1]/private",
        "http://[::ffff:127.0.0.1]/private",
        "http://localhost/private",
        "http://api.localhost/private",
        "http://2130706433/private",
        "http://0x7f000001/private",
        "http://0177.0.0.1/private",
        "http://127.1/private",
        "http://0x7f.0.0.1/private",
        "http://127%2e0%2e0%2e1/private",
        "http://user@public.example.test/private",
        "http://user:password@public.example.test/private",
        "https://public.example.test:notaport/private",
        "http://::1/private",
        "http://[fe80::1%25eth0]/private",
        "https://tést.example/private",
        "https://public.example.test/\x00private",
        "file:///etc/passwd",
        "https://public.example.test\\@127.0.0.1/private",
    ],
)
def test_static_prohibited_target_matrix_blocks(url: str) -> None:
    decision = _decision(url)

    assert decision.status == NetworkTargetSafetyStatus.BLOCKED.value
    assert decision.blocker_code
    assert decision.raw_dns_retained is False
    assert decision.credentials_retained is False


@pytest.mark.parametrize(
    ("url", "snapshot"),
    (
        (
            "https://public.example.test/rule",
            NetworkTargetResolutionSnapshotV1.create(
                canonical_host="public.example.test",
                addresses=("1.1.1.1",),
            ),
        ),
        (
            "https://ipv6.example.test/rule",
            NetworkTargetResolutionSnapshotV1.create(
                canonical_host="ipv6.example.test",
                addresses=("2606:4700:4700::1111",),
            ),
        ),
        ("https://1.1.1.1/rule", None),
        ("https://[2606:4700:4700::1111]/rule", None),
    ),
)
def test_representative_public_targets_are_allowed_without_network(
    url: str,
    snapshot: NetworkTargetResolutionSnapshotV1 | None,
) -> None:
    decision = _decision(url, snapshot=snapshot)

    assert decision.status == NetworkTargetSafetyStatus.ALLOWED.value
    assert decision.blocker_code is None


def test_policy_owner_is_pure_and_has_no_resolver_or_transport_import() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "core" / "network_target_safety.py").read_text(
        encoding="utf-8"
    )
    imported_modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert imported_modules.isdisjoint(
        {"socket", "requests", "httpx", "urllib.request"}
    )


def test_dynamic_target_policy_callers_exclude_fixed_and_local_endpoints() -> None:
    root = Path(__file__).resolve().parents[1]
    callers: set[str] = set()
    for path in (root / "core").glob("*.py"):
        if path.name == "network_target_safety.py":
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        if any(
            isinstance(node, ast.Call)
            and (
                isinstance(node.func, ast.Name)
                and node.func.id == "evaluate_network_target_safety"
            )
            for node in ast.walk(tree)
        ):
            callers.add(path.name)

    assert callers == {
        "acquisition_control.py",
        "authorized_acquisition_runtime.py",
        "run_kernel.py",
    }
    for relative_path in (
        "core/acquisition_adapters.py",
        "core/llm.py",
        "core/run_config.py",
        "proplex/mvp_live_dogfood_run.py",
        "scripts/request_live_validation_broker.py",
        "scripts/request_provider_proxy_broker.py",
    ):
        source = (root / relative_path).read_text(encoding="utf-8")
        assert "evaluate_network_target_safety(" not in source


def test_request_validation_evaluates_content_url_not_fixed_provider_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_targets: list[str] = []
    monkeypatch.setattr(
        acquisition_contracts,
        "static_network_target_block_code",
        lambda url: observed_targets.append(url) or None,
    )
    route = route_provider_capability_for_offline_target_safety_validation(
        ProviderCapabilityRequest(capability=AcquisitionCapability.READ),
        {"linkup": True, "tavily": True},
        validation_authority=_offline_validation_authority(),
    )
    request = AcquisitionRequest(
        acquisition_job_id="fixed-endpoint-exclusion-proof",
        route_decision=route,
        selected_urls=(READ_URL,),
        candidate_reference="candidate-fixed-endpoint-exclusion",
    )

    acquisition_contracts.validate_acquisition_request(request)

    assert observed_targets == [READ_URL]
    assert LINKUP_FETCH_URL not in observed_targets
    assert TAVILY_API_ROOT not in observed_targets


def test_resolver_snapshot_blocks_mixed_public_private_and_hides_private_ip() -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1", "10.0.0.8"),
    )
    decision = _decision(
        "https://public.example.test/rule",
        snapshot=snapshot,
    )
    persisted = snapshot.to_dict()

    assert decision.status == "blocked"
    assert decision.blocker_code == (
        "target_resolution_contains_prohibited_address:private_network"
    )
    assert "10.0.0.8" not in repr(persisted)
    assert persisted["raw_dns_retained"] is False
    assert persisted["raw_private_network_data_retained"] is False


def test_typed_snapshot_is_revalidated_and_resolved_counts_are_exact() -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1",),
    )
    forged_typed_snapshot = replace(snapshot, address_count=2)

    with pytest.raises(
        ValueError,
        match="network_target_resolution_snapshot_count_invalid",
    ):
        canonical_resolution_snapshot_bundle((forged_typed_snapshot,))

    resolved_empty = replace(
        NetworkTargetResolutionSnapshotV1.create(
            canonical_host="public.example.test",
            resolution_status="empty",
        ),
        resolution_status="resolved",
    )
    with pytest.raises(
        ValueError,
        match="network_target_resolution_snapshot_resolved_empty",
    ):
        canonical_resolution_snapshot_bundle((resolved_empty,))


def test_network_target_safety_decision_trace_round_trips_canonically() -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1",),
    )
    admission = _decision(
        "https://public.example.test/rule",
        snapshot=snapshot,
    )
    pretransport = evaluate_network_target_safety(
        "https://public.example.test/rule",
        stage=NetworkTargetSafetyStage.FINAL_PRETRANSPORT,
        transport_mode=NetworkTargetTransportMode.PROVIDER_MEDIATED,
        fact_kind=NetworkTargetFactKind.REQUESTED,
        resolver_snapshot=snapshot,
        previous_decision_ref=admission.ref(),
        lineage_ref={"work_order_id": "work-order-1"},
    )
    prohibited_literal = _decision("http://127.0.0.1/private")

    for decision in (admission, pretransport, prohibited_literal):
        trace = decision.to_trace()
        restored = type(decision).from_trace(trace)

        assert restored.to_trace() == trace
        assert restored.decision_id == decision.decision_id
        assert restored.decision_digest == decision.decision_digest
        assert restored.normalized_target_url is None

    prohibited_trace = prohibited_literal.to_trace()
    assert prohibited_trace["canonical_host"] is None
    assert "127.0.0.1" not in repr(prohibited_trace)


def test_network_target_safety_decision_trace_rejects_tampering() -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1",),
    )
    admission = _decision(
        "https://public.example.test/rule",
        snapshot=snapshot,
    )
    decision = evaluate_network_target_safety(
        "https://public.example.test/rule",
        stage=NetworkTargetSafetyStage.FINAL_PRETRANSPORT,
        transport_mode=NetworkTargetTransportMode.PROVIDER_MEDIATED,
        fact_kind=NetworkTargetFactKind.REQUESTED,
        resolver_snapshot=snapshot,
        previous_decision_ref=admission.ref(),
        lineage_ref={"work_order_id": "work-order-1"},
    )
    canonical = decision.to_trace()
    tampered: list[dict[str, Any]] = []

    extra_field = deepcopy(canonical)
    extra_field["unexpected"] = False
    tampered.append(extra_field)
    missing_field = deepcopy(canonical)
    missing_field.pop("scheme")
    tampered.append(missing_field)
    stale_policy = deepcopy(canonical)
    stale_policy["policy_version"] = "stale-policy"
    tampered.append(stale_policy)
    forged_digest = deepcopy(canonical)
    forged_digest["decision_digest"] = "0" * 64
    tampered.append(forged_digest)
    forged_id = deepcopy(canonical)
    forged_id["decision_id"] = "network-target-safety:forged"
    tampered.append(forged_id)
    invalid_stage = deepcopy(canonical)
    invalid_stage["stage"] = "after_custody"
    tampered.append(invalid_stage)
    blocker_mismatch = deepcopy(canonical)
    blocker_mismatch["status"] = "blocked"
    tampered.append(blocker_mismatch)
    authority_grant = deepcopy(canonical)
    authority_grant["custody_authority_granted"] = True
    tampered.append(authority_grant)
    unbounded_lineage = deepcopy(canonical)
    unbounded_lineage["lineage_ref"]["work_order_id"] = "x" * 301
    tampered.append(unbounded_lineage)
    invalid_counts = deepcopy(canonical)
    invalid_counts["address_classification_counts"] = {"public": 17}
    tampered.append(invalid_counts)
    forged_resolver = deepcopy(canonical)
    forged_resolver["resolver_snapshot_ref"]["raw_dns_retained"] = True
    tampered.append(forged_resolver)
    unbounded_previous = deepcopy(canonical)
    unbounded_previous["previous_decision_ref"]["unexpected"] = "value"
    tampered.append(unbounded_previous)

    for trace in tampered:
        with pytest.raises(ValueError):
            type(decision).from_trace(trace)


def test_overflow_snapshot_retains_only_the_bounded_address_prefix() -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=tuple(f"8.8.8.{ordinal}" for ordinal in range(1, 18)),
    )

    persisted = canonical_resolution_snapshot_bundle((snapshot,))[0]

    assert persisted["resolution_status"] == "overflow"
    assert persisted["address_count"] == 17
    assert len(persisted["address_entries"]) == 16


def test_gate1_snapshot_bundle_rejects_unrelated_and_unbounded_hosts() -> None:
    expected = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1",),
    )
    unrelated = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="unrelated.example.test",
        addresses=("1.0.0.1",),
    )

    with pytest.raises(
        ValueError,
        match="unrelated_network_target_resolution_snapshot",
    ):
        canonical_resolution_snapshot_bundle(
            (expected, unrelated),
            expected_target_urls=("https://public.example.test/rule",),
        )

    over_bound = tuple(
        NetworkTargetResolutionSnapshotV1.create(
            canonical_host=f"host-{ordinal}.example.test",
            addresses=("1.1.1.1",),
        )
        for ordinal in range(MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS + 1)
    )
    with pytest.raises(
        ValueError,
        match="network_target_resolution_snapshot_bundle_overflow",
    ):
        canonical_resolution_snapshot_bundle(over_bound)


@pytest.mark.parametrize(
    "url",
    (
        "http://127.0.0.1/private",
        "http://[::1]/private",
        "http://169.254.169.254/latest/meta-data/",
    ),
)
def test_prohibited_literal_is_absent_from_decision_refs_and_traces(
    url: str,
) -> None:
    decision = _decision(url)

    for persisted in (decision.ref(), decision.to_trace()):
        assert persisted["canonical_host"] is None
        assert "normalized_target_url" not in persisted
        assert decision.canonical_host not in repr(persisted)


@pytest.mark.parametrize(
    ("status", "blocker"),
    [
        ("empty", "target_resolution_empty"),
        ("malformed", "target_resolution_malformed"),
        ("resolver_exception", "target_resolution_exception"),
        ("indeterminate", "target_resolution_indeterminate"),
        ("overflow", "target_resolution_overflow"),
    ],
)
def test_indeterminate_resolver_postures_fail_closed(
    status: str,
    blocker: str,
) -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        resolution_status=status,
    )

    assert _decision(
        "https://public.example.test/rule",
        snapshot=snapshot,
    ).blocker_code == blocker


def test_snapshot_identity_is_order_independent_and_ipv4_mapped_is_effective() -> None:
    first = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1", "2606:4700:4700::1111"),
    )
    second = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("2606:4700:4700::1111", "1.1.1.1"),
    )
    duplicated = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1", "2606:4700:4700::1111", "1.1.1.1"),
    )
    mapped = _decision("http://[::ffff:127.0.0.1]/private")

    assert first.snapshot_digest == second.snapshot_digest
    assert duplicated.snapshot_digest == first.snapshot_digest
    assert duplicated.address_count == 2
    assert mapped.blocker_code == "target_address_loopback_blocked"


def test_fragment_is_stripped_without_collapsing_stage_identity() -> None:
    snapshot = NetworkTargetResolutionSnapshotV1.create(
        canonical_host="public.example.test",
        addresses=("1.1.1.1",),
    )
    admission = evaluate_network_target_safety(
        "https://public.example.test/rule#section",
        stage=NetworkTargetSafetyStage.ADMISSION_PRE_ROUTE,
        transport_mode=NetworkTargetTransportMode.PROVIDER_MEDIATED,
        fact_kind=NetworkTargetFactKind.EXPLICIT_USER,
        resolver_snapshot=snapshot,
    )
    posttransport = evaluate_network_target_safety(
        "https://public.example.test/rule#other",
        stage=NetworkTargetSafetyStage.POSTTRANSPORT_OBSERVED_TARGET,
        transport_mode=NetworkTargetTransportMode.PROVIDER_MEDIATED,
        fact_kind=NetworkTargetFactKind.FINAL,
        resolver_snapshot=snapshot,
    )

    assert admission.status == posttransport.status == "allowed"
    assert admission.normalized_target_digest == (
        posttransport.normalized_target_digest
    )
    assert admission.stage != posttransport.stage
    assert admission.decision_id != posttransport.decision_id


def test_gate1_blocks_without_operation_admission_or_terminalization() -> None:
    kernel = _kernel()
    proposal = _proposal(kernel, url="http://127.0.0.1/private")
    action = kernel.authorize_acquisition_capability_decision(proposal=proposal)
    result = execute_acquisition_capability_decision_action(
        action,
        proposal=proposal,
        authority_snapshot=kernel.acquisition_authority_snapshot(),
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(result.observation)
    control = kernel.state.acquisition_control_state

    assert result.decision.decision_status == "blocked"
    assert result.decision.block_code.startswith(
        "admission_target_safety_blocked:"
    )
    assert control["work_orders_by_id"] == {}
    assert control["proposals_by_id"] == {}
    assert control["routes_by_id"] == {}
    assert control["active_by_source_obligation"] == {}
    assert control["terminal_receipts_by_operation_key"] == {}
    assert control["exhausted_operation_keys"] == {}
    with pytest.raises(
        RunKernelTransitionError,
        match="decision blocker is not a durable terminal capability blocker",
    ):
        kernel.authorize_acquisition_terminal_reduction(
            capability_decision_ref=result.decision.ref()
        )


@pytest.mark.parametrize(
    "unsafe_url",
    (
        "http://127.0.0.1/private",
        "http://user:password@public.example.test/private",
    ),
)
def test_gate1_unsafe_target_is_not_retained_in_action_or_kernel_state(
    unsafe_url: str,
) -> None:
    kernel = _kernel()
    proposal = _proposal(kernel, url=unsafe_url)
    action = kernel.authorize_acquisition_capability_decision(
        proposal=proposal
    )
    result = execute_acquisition_capability_decision_action(
        action,
        proposal=proposal,
        authority_snapshot=kernel.acquisition_authority_snapshot(),
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(result.observation)

    retained_state = repr(
        {
            "action": action.inputs,
            "control": kernel.state.acquisition_control_state,
            "projections": kernel.state.projections,
        }
    )
    assert unsafe_url not in retained_state
    assert "user:password" not in retained_state
    assert "127.0.0.1" not in retained_state


def test_gate1_precedes_capability_recognition_for_unsafe_target() -> None:
    kernel = _kernel()
    unsafe_url = "http://127.0.0.1/private"
    proposal = _proposal(
        kernel,
        material_shape="site_topology",
        advisory=None,
        url=unsafe_url,
    )

    action = kernel.authorize_acquisition_capability_decision(
        proposal=proposal
    )
    result = execute_acquisition_capability_decision_action(
        action,
        proposal=proposal,
        authority_snapshot=kernel.acquisition_authority_snapshot(),
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(result.observation)

    assert result.decision.derived_capability is None
    assert result.decision.block_code == (
        "admission_target_safety_blocked:target_address_loopback_blocked"
    )
    assert kernel.state.acquisition_control_state["proposals_by_id"] == {}
    retained_state = repr(
        {
            "action": action.inputs,
            "control": kernel.state.acquisition_control_state,
            "projections": kernel.state.projections,
        }
    )
    assert unsafe_url not in retained_state
    assert "127.0.0.1" not in retained_state


def test_production_route_blocks_when_no_operation_is_truthfully_eligible() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    work_order = admitted.work_order_result.work_order
    action = kernel.authorize_acquisition_route(
        work_order_ref=work_order.ref(),
        provider_availability={"linkup": True, "tavily": True},
    )
    result = execute_acquisition_route_action(
        action,
        work_order=work_order,
        available_providers={"linkup": True, "tavily": True},
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(result.observation)

    assert result.route_observation.terminal_status == "blocked"
    assert result.route_observation.block_code == (
        "no_safety_eligible_provider_for_untrusted_exact_url"
    )
    assert all(
        candidate.target_safety_eligible is False
        for candidate in result.route_decision.fallback_candidates
    )


def test_ordinary_route_api_has_no_injected_eligibility_authority() -> None:
    assert (
        "provider_target_safety_eligibility"
        not in signature(route_provider_capability).parameters
    )
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.READ,
            target_class=UNTRUSTED_EXACT_URL_TARGET_CLASS,
        ),
        {"linkup": True, "tavily": True},
    )

    assert decision.fidelity is RouteFidelity.BLOCKED
    assert decision.block_reason == (
        "no_safety_eligible_provider_for_untrusted_exact_url"
    )
    assert decision.target_safety_eligibility_ref["source_posture"] == (
        "code_owned_repository_evidence"
    )
    assert decision.target_safety_eligibility_ref["authority_posture"] == "PRODUCT"
    assert decision.target_safety_eligibility_ref["product_reachable"] is True


@pytest.mark.parametrize(
    "requester_target_class",
    ["target_safety_not_applicable", "requester_claimed_safe_target"],
)
def test_dynamic_content_target_class_is_code_owned_and_cannot_be_bypassed(
    requester_target_class: str,
) -> None:
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.READ,
            target_class=requester_target_class,
        ),
        {"linkup": True, "tavily": True},
    )

    assert decision.request.target_class == UNTRUSTED_EXACT_URL_TARGET_CLASS
    assert decision.fidelity is RouteFidelity.BLOCKED
    assert decision.block_reason == (
        "no_safety_eligible_provider_for_untrusted_exact_url"
    )


def test_ordinary_runkernel_and_runtime_route_apis_have_no_fixture_parameter() -> None:
    for ordinary_api in (
        RunKernel.authorize_acquisition_route,
        execute_acquisition_route_action,
    ):
        parameters = signature(ordinary_api).parameters
        assert "provider_target_safety_eligibility_fixture" not in parameters
        assert "validation_authority" not in parameters
        assert all(
            parameter.kind.name != "VAR_KEYWORD"
            for parameter in parameters.values()
        )


def test_offline_selected_route_cannot_enter_ordinary_execution_path() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order

    assert route.route_observation.target_safety_eligibility_ref[
        "product_reachable"
    ] is False
    with pytest.raises(
        RunKernelTransitionError,
        match="offline_validation_route_cannot_enter_product_execution",
    ):
        kernel.authorize_acquisition_execution(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
        )

    offline_action = (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="offline_validation_execution_cannot_enter_product_runtime",
    ):
        execute_authorized_acquisition_work_order(
            offline_action,
            run_kernel=kernel,
            work_order=work_order,
            route_observation=route.route_observation,
            route_decision=route.route_decision,
            target_resolution_snapshots=_proposal_snapshots(
                admitted.proposal
            ),
        )


def test_offline_route_authority_is_code_identity_bounded_and_tamper_evident() -> None:
    with pytest.raises(ValueError, match="unknown operation identities"):
        OfflineProviderTargetSafetyValidationAuthorityV1.create(
            {"invented:READ:fetch:known_url": True}
        )
    with pytest.raises(ValueError, match="must be boolean"):
        OfflineProviderTargetSafetyValidationAuthorityV1.create(
            {
                provider_operation_identity(
                    provider="linkup",
                    capability=AcquisitionCapability.READ,
                    operation="fetch",
                    variant="known_url",
                ): 1
            }
        )

    authority = OfflineProviderTargetSafetyValidationAuthorityV1.create({})
    forged = replace(authority, fixture_digest="0" * 64)
    with pytest.raises(ValueError, match="stale or forged"):
        forged.validated_mapping()


def test_offline_route_entrypoint_selects_eligible_route_time_alternative() -> None:
    tavily_read = provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.READ,
        operation="extract",
        variant="basic",
    )
    authority = OfflineProviderTargetSafetyValidationAuthorityV1.create(
        {tavily_read: True}
    )
    decision = route_provider_capability_for_offline_target_safety_validation(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.READ,
            target_class=UNTRUSTED_EXACT_URL_TARGET_CLASS,
        ),
        {"linkup": True, "tavily": True},
        validation_authority=authority,
    )

    assert decision.fidelity is RouteFidelity.EXACT
    assert decision.selected_provider == "tavily"
    assert decision.selected_provider_target_safety_eligible is True
    assert decision.target_safety_eligibility_ref["authority_posture"] == (
        "PRODUCT-unreachable"
    )
    assert decision.target_safety_eligibility_ref["product_reachable"] is False
    assert decision.target_safety_eligibility_ref[
        "offline_validation_authority_ref"
    ] == authority.ref()
    linkup = next(
        candidate
        for candidate in decision.fallback_candidates
        if candidate.provider == "linkup"
    )
    assert linkup.currently_available is True
    assert linkup.target_safety_eligible is False


def test_offline_target_safety_authority_cannot_enter_discover_routing() -> None:
    authority = OfflineProviderTargetSafetyValidationAuthorityV1.create({})
    with pytest.raises(ValueError, match="does not apply to DISCOVER"):
        route_provider_capability_for_offline_target_safety_validation(
            ProviderCapabilityRequest(
                capability=AcquisitionCapability.DISCOVER,
                qualifier=DiscoverQualifier.GENERAL,
            ),
            {"linkup": True},
            validation_authority=authority,
        )

    ordinary = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.GENERAL,
        ),
        {"linkup": True},
    )
    assert ordinary.selected_provider == "linkup"
    assert ordinary.target_safety_eligibility_ref == {}
    assert ordinary.selected_provider_target_safety_eligible is None
    assert all(
        candidate.target_safety_eligible is None
        for candidate in ordinary.fallback_candidates
    )


def test_route_can_choose_existing_eligible_alternative_before_dispatch() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    work_order = admitted.work_order_result.work_order
    tavily_read = provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.READ,
        operation="extract",
        variant="basic",
    )
    validation_authority = (
        OfflineProviderTargetSafetyValidationAuthorityV1.create(
            {tavily_read: True}
        )
    )
    action = (
        kernel.authorize_acquisition_route_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            provider_availability={"linkup": True, "tavily": True},
            validation_authority=validation_authority,
        )
    )
    result = (
        execute_acquisition_route_action_for_offline_target_safety_validation(
            action,
            work_order=work_order,
            available_providers={"linkup": True, "tavily": True},
            validation_authority=validation_authority,
            acquisition_control_state=(
                kernel.state.acquisition_control_state
            ),
        )
    )
    kernel.reduce(result.observation)

    assert result.route_observation.selected_provider == "tavily"
    linkup = next(
        candidate
        for candidate in result.route_decision.fallback_candidates
        if candidate.provider == "linkup"
    )
    assert linkup.currently_available is True
    assert linkup.target_safety_eligible is False


def _terminalize_execution(kernel, admitted, route, execution):
    kernel.reduce(execution.observation)
    action = kernel.authorize_acquisition_terminal_reduction(
        execution_observation_ref=execution.execution_observation.ref()
    )
    terminal = execute_acquisition_terminal_reduction_action(
        action,
        work_order=admitted.work_order_result.work_order,
        route_observation=route.route_observation,
        execution_observation=execution.execution_observation,
        acquisition_control_state=kernel.state.acquisition_control_state,
    )
    kernel.reduce(terminal.observation)
    return terminal


def test_gate2_is_the_only_unclaimed_execution_block_and_exhausts_operation() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )
    cap_charges = 0

    def cap_charge() -> None:
        nonlocal cap_charges
        cap_charges += 1

    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not run"}
    )

    execution = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(
            admitted.proposal,
            address="1.1.1.1",
        ),
        before_transport=cap_charge,
    )

    assert execution.execution_observation.terminal_status == "blocked"
    assert execution.execution_result.execution_claim_consumed is False
    assert execution.execution_result.adapter_invoked is False
    assert execution.execution_result.provider_calls_attempted == 0
    assert cap_charges == fixture.calls == 0
    with pytest.raises(
        RunKernelTransitionError,
        match="pretransport_target_safety_block_unclaimable",
    ):
        kernel.claim_acquisition_execution(
            action=action,
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
        )
    terminal = _terminalize_execution(kernel, admitted, route, execution)
    control = kernel.state.acquisition_control_state
    assert control["active_by_source_obligation"] == {}
    assert control["exhausted_operation_keys"][
        work_order.operation_identity_key
    ]["terminal_receipt_ref"] == terminal.terminal_receipt.ref()
    assert control["target_safety_telemetry"][
        "unsafe_target_operations_exhausted"
    ] == 1


def test_gate2_invalid_typed_snapshot_reduces_without_stranding_active_slot() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )
    canonical = _proposal_snapshots(admitted.proposal)[0]
    forged = replace(canonical, address_count=canonical.address_count + 1)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not run"}
    )

    execution = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=(forged,),
    )

    assert execution.execution_observation.terminal_status == "blocked"
    assert execution.execution_result.execution_claim_consumed is False
    assert fixture.calls == 0
    _terminalize_execution(kernel, admitted, route, execution)
    assert kernel.state.acquisition_control_state[
        "active_by_source_obligation"
    ] == {}


def test_claim_failure_occurs_before_cap_charge_or_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )
    cap_charges = 0

    def deny_claim(**_kwargs: Any) -> None:
        raise RunKernelTransitionError("synthetic_claim_failure")

    def cap_charge() -> None:
        nonlocal cap_charges
        cap_charges += 1

    monkeypatch.setattr(kernel, "claim_acquisition_execution", deny_claim)
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not run"}
    )

    with pytest.raises(AcquisitionControlError, match="synthetic_claim_failure"):
        execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
            action,
            run_kernel=kernel,
            work_order=work_order,
            route_observation=route.route_observation,
            route_decision=route.route_decision,
            validation_authority=_offline_validation_authority(),
            transport_fixture=fixture,
            target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
            before_transport=cap_charge,
        )

    assert cap_charges == fixture.calls == 0


def test_run_cap_block_is_claimed_once_and_never_reaches_transport() -> None:
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )
    fixture = OfflineAcquisitionTransportFixtureV1.create(
        response={"markdown": "must not run"}
    )

    def cap_block() -> None:
        raise RunCapExceeded("synthetic cap block")

    execution = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=_proposal_snapshots(admitted.proposal),
        before_transport=cap_block,
    )

    assert execution.execution_observation.terminal_status == "blocked"
    assert execution.execution_result.execution_claim_consumed is True
    assert execution.execution_result.provider_calls_attempted == 0
    assert fixture.calls == 0
    _terminalize_execution(kernel, admitted, route, execution)
    with pytest.raises(RunCapExceeded, match="synthetic cap block"):
        execution.raise_deferred_error()


def _execute_linkup_fixture(
    *,
    response: dict[str, Any],
    snapshots: tuple[NetworkTargetResolutionSnapshotV1, ...] | None = None,
):
    kernel = _kernel()
    admitted = _admit_read(kernel)
    route = _route_read(kernel, admitted)
    work_order = admitted.work_order_result.work_order
    action = (
        kernel.authorize_acquisition_execution_for_offline_target_safety_validation(
            work_order_ref=work_order.ref(),
            route_observation_ref=route.route_observation.ref(),
            validation_authority=_offline_validation_authority(),
        )
    )
    cap_charges = 0

    def cap_charge() -> None:
        nonlocal cap_charges
        cap_charges += 1

    fixture = OfflineAcquisitionTransportFixtureV1.create(response=response)

    execution = execute_authorized_acquisition_work_order_for_offline_target_safety_validation(
        action,
        run_kernel=kernel,
        work_order=work_order,
        route_observation=route.route_observation,
        route_decision=route.route_decision,
        validation_authority=_offline_validation_authority(),
        transport_fixture=fixture,
        target_resolution_snapshots=(
            snapshots or _proposal_snapshots(admitted.proposal)
        ),
        before_transport=cap_charge,
    )
    return kernel, admitted, route, execution, cap_charges, fixture.calls


def test_gate3_unsafe_observed_target_preserves_one_transport_but_no_artifact() -> None:
    kernel, admitted, route, execution, cap_charges, calls = (
        _execute_linkup_fixture(
            response={
                "markdown": "offline readable fixture",
                "final_url": "http://127.0.0.1/private",
            }
        )
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code.startswith(
        "posttransport_target_safety_failure:"
    )
    assert execution.execution_result.artifacts == ()
    assert execution.execution_result.provider_calls_attempted == 1
    assert execution.execution_result.provider_calls_completed == 1
    assert execution.execution_result.execution_claim_consumed is True
    assert execution.execution_result.target_safety_summary[
        "urls_fetched_delta"
    ] == 1
    assert cap_charges == calls == 1
    terminal = _terminalize_execution(kernel, admitted, route, execution)
    with pytest.raises(
        RunKernelTransitionError,
        match="noncompleted_receipt_cannot_authorize_custody",
    ):
        kernel.authorize_acquisition_custody_consumption(
            terminal_receipt_ref=terminal.terminal_receipt.ref()
        )


def test_gate3_unsafe_target_is_not_masked_by_material_normalization_failure() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "",
            "final_url": "http://127.0.0.1/private",
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code.startswith(
        "posttransport_target_safety_failure:"
    )
    assert execution.execution_result.artifacts == ()
    assert execution.execution_result.provider_calls_attempted == 1
    assert execution.execution_result.provider_calls_completed == 1
    assert execution.execution_result.target_safety_summary[
        "gate3_decisions_observed"
    ] >= 3
    assert execution.execution_result.target_safety_summary[
        "posttransport_target_safety_failure"
    ] is True
    assert cap_charges == calls == 1


def test_gate3_observation_overflow_blocks_when_unsafe_target_is_record_101() -> None:
    safe_records = [
        {
            "url": f"https://official.example.test/observed-{ordinal}",
            "raw_content": "bounded offline material",
        }
        for ordinal in range(100)
    ]
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "results": [
                *safe_records,
                {
                    "url": "http://127.0.0.1/private-record-101",
                    "raw_content": "must never be admitted",
                },
            ]
        }
    )

    result = execution.execution_result
    assert result.status.value == "failed"
    assert result.failure_code == (
        "posttransport_target_safety_failure:"
        "posttransport_target_observation_overflow"
    )
    assert result.artifacts == ()
    assert result.provider_calls_attempted == 1
    assert result.provider_calls_completed == 1
    assert result.target_safety_summary[
        "posttransport_target_safety_failure"
    ] is True
    assert any(
        decision.get("blocker_code")
        == "posttransport_target_observation_overflow"
        for decision in result.target_safety_decision_refs
    )
    assert cap_charges == calls == 1


def test_gate3_raw_source_overflow_without_target_mappings_is_safety_failure() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={"results": [READ_URL] * 201}
    )

    result = execution.execution_result
    assert result.status.value == "failed"
    assert result.failure_code == (
        "posttransport_target_safety_failure:"
        "posttransport_target_observation_overflow"
    )
    assert result.artifacts == ()
    assert result.provider_calls_attempted == 1
    assert result.provider_calls_completed == 1
    assert cap_charges == calls == 1


def test_gate3_safe_target_does_not_upgrade_failed_material_normalization() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "",
            "final_url": "https://official.example.test/canonical-rule",
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code == (
        "read_material_empty_or_unreadable"
    )
    assert len(execution.execution_result.artifacts) == 1
    assert execution.execution_result.artifacts[0].status == "failed"
    assert execution.execution_result.target_safety_summary[
        "posttransport_target_safety_failure"
    ] is False
    assert execution.execution_result.target_safety_summary[
        "gate3_decisions_observed"
    ] >= 3
    assert cap_charges == calls == 1


def test_gate3_scalar_prohibited_sibling_survives_nonscalar_target_error() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "offline readable fixture",
            "final_url": {"href": "https://official.example.test/final"},
            "redirect_url": "http://127.0.0.1/private",
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code.startswith(
        "posttransport_target_safety_failure:"
    )
    assert execution.execution_result.artifacts == ()
    assert cap_charges == calls == 1


def test_reducer_rejects_self_consistent_artifact_target_substitution() -> None:
    kernel, _, _, execution, _, _ = _execute_linkup_fixture(
        response={
            "markdown": "offline readable fixture",
            "final_url": "https://official.example.test/original-final",
        }
    )
    original = execution.execution_observation
    artifact_ref = dict(original.artifact_refs[0])
    artifact_ref["final_url"] = (
        "https://official.example.test/substituted-final"
    )
    digest_core = {
        key: value
        for key, value in artifact_ref.items()
        if key
        not in {
            "artifact_id",
            "artifact_digest",
            "retained_text_included",
            "raw_provider_payload_included",
        }
    }
    artifact_ref["artifact_digest"] = stable_json_digest(digest_core)
    artifact_ref["artifact_id"] = (
        f"acquisition-artifact:{artifact_ref['acquisition_job_id']}:"
        f"{artifact_ref['artifact_digest'][:20]}"
    )
    forged_execution = AcquisitionExecutionObservationV1.create(
        work_order_ref=original.work_order_ref,
        completed_route_ref=original.completed_route_ref,
        execution_result_trace=execution.execution_result.to_trace(),
        artifact_refs=(artifact_ref,),
        provider_calls_attempted=original.provider_calls_attempted,
        provider_calls_completed=original.provider_calls_completed,
        terminal_status=original.terminal_status,
        failure_or_block_code=original.failure_or_block_code,
        target_safety_decision_refs=original.target_safety_decision_refs,
        target_safety_summary=original.target_safety_summary,
        execution_claim_consumed=original.execution_claim_consumed,
        adapter_invoked=original.adapter_invoked,
        transport_posture=original.transport_posture,
        execution_authority_posture=original.execution_authority_posture,
    )
    forged_observation = replace(
        execution.observation,
        payload={"execution_observation": forged_execution.to_dict()},
    )

    with pytest.raises(
        RunKernelTransitionError,
        match="execution_artifact_target_safety_binding_mismatch",
    ):
        kernel.reduce(forged_observation)


@pytest.mark.parametrize(
    "stage",
    (
        NetworkTargetSafetyStage.FINAL_PRETRANSPORT.value,
        NetworkTargetSafetyStage.POSTTRANSPORT_OBSERVED_TARGET.value,
    ),
)
def test_execution_reducer_rejects_tampered_canonical_safety_store(
    stage: str,
) -> None:
    kernel, _, _, execution, _, _ = _execute_linkup_fixture(
        response={"markdown": "offline readable fixture"}
    )
    authorization = kernel.state.acquisition_control_state[
        "execution_authorizations_by_id"
    ][execution.observation.action_id]
    trace = authorization["target_safety_decision_traces_by_stage"][stage][0]
    trace["decision_digest"] = "0" * 64

    expected = (
        "pretransport_target_safety_decision_store_invalid"
        if stage == NetworkTargetSafetyStage.FINAL_PRETRANSPORT.value
        else "posttransport_target_safety_decision_store_invalid"
    )
    with pytest.raises(RunKernelTransitionError, match=expected):
        kernel.reduce(execution.observation)


@pytest.mark.parametrize(
    "observed_final_url",
    (
        "file:///etc/passwd",
        "http://user:password@public.example.test/private",
        "http://[::1",
    ),
)
def test_gate3_does_not_normalize_away_malformed_or_prohibited_observed_url(
    observed_final_url: str,
) -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "offline readable fixture",
            "final_url": observed_final_url,
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code.startswith(
        "posttransport_target_safety_failure:"
    )
    assert execution.execution_result.artifacts == ()
    assert execution.execution_result.provider_calls_attempted == 1
    assert execution.execution_result.provider_calls_completed == 1
    assert cap_charges == calls == 1


def test_present_nonscalar_observed_target_is_typed_provider_failure() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "offline readable fixture",
            "final_url": {"href": "http://127.0.0.1/private"},
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code == (
        "observed_target_scalar_required"
    )
    assert execution.execution_result.succeeded is False
    assert execution.execution_result.provider_calls_attempted == 1
    assert execution.execution_result.provider_calls_completed == 1
    assert cap_charges == calls == 1


def test_gate3_accepts_safe_same_source_final_url_and_preserves_a_and_b() -> None:
    final_url = "https://official.example.test/canonical-rule"
    kernel, admitted, route, execution, cap_charges, calls = (
        _execute_linkup_fixture(
            response={
                "markdown": "offline readable fixture",
                "redirect_url": final_url,
                "final_url": final_url,
                "canonical_url": final_url,
            }
        )
    )

    assert execution.execution_result.succeeded is True
    artifact = execution.execution_result.artifacts[0]
    assert artifact.requested_url == READ_URL
    assert artifact.redirect_url == final_url
    assert artifact.final_url == final_url
    assert artifact.canonical_url == final_url
    assert execution.execution_observation.artifact_refs[0][
        "requested_url"
    ] == READ_URL
    assert execution.execution_observation.artifact_refs[0][
        "redirect_url"
    ] == final_url
    assert execution.execution_observation.artifact_refs[0]["final_url"] == final_url
    assert execution.execution_result.target_safety_summary[
        "safe_redirect_targets_accepted"
    ] == 1
    assert execution.execution_result.target_safety_summary[
        "safe_final_targets_accepted"
    ] == 1
    assert cap_charges == calls == 1
    terminal = _terminalize_execution(kernel, admitted, route, execution)
    with pytest.raises(
        RunKernelTransitionError,
        match="custody_requires_product_execution_authority",
    ):
        kernel.authorize_acquisition_custody_consumption(
            terminal_receipt_ref=terminal.terminal_receipt.ref()
        )


def test_safe_but_inapplicable_target_is_lineage_failure_not_safety_failure() -> None:
    other_url = "https://other-public.example.test/rule"
    snapshots = (
        NetworkTargetResolutionSnapshotV1.create(
            canonical_host="official.example.test",
            addresses=("93.184.216.34",),
        ),
        NetworkTargetResolutionSnapshotV1.create(
            canonical_host="other-public.example.test",
            addresses=("1.1.1.1",),
        ),
    )
    kernel, admitted, route, execution, cap_charges, calls = (
        _execute_linkup_fixture(
            response={
                "markdown": "offline readable fixture",
                "final_url": other_url,
            },
            snapshots=snapshots,
        )
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code == (
        "posttransport_target_applicability_failure:final_url"
    )
    assert not execution.execution_result.failure_code.startswith(
        "posttransport_target_safety_failure:"
    )
    assert execution.execution_result.artifacts == ()
    assert execution.execution_result.target_safety_summary[
        "safe_target_applicability_failure"
    ] is True
    assert cap_charges == calls == 1
    terminal = _terminalize_execution(kernel, admitted, route, execution)
    assert terminal.terminal_receipt.terminal_status == "failed"


def test_provider_reported_result_identity_remains_exact_applicability_rule() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "offline readable fixture",
            "url": "https://official.example.test/different-result",
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code == (
        "posttransport_target_applicability_failure:provider_reported_url"
    )
    assert execution.execution_result.target_safety_summary[
        "posttransport_target_safety_failure"
    ] is False
    assert execution.execution_result.artifacts == ()
    assert cap_charges == calls == 1


def test_prohibited_provider_reported_identity_is_safety_failure_first() -> None:
    _, _, _, execution, cap_charges, calls = _execute_linkup_fixture(
        response={
            "markdown": "offline readable fixture",
            "url": "http://127.0.0.1/private",
        }
    )

    assert execution.execution_result.status.value == "failed"
    assert execution.execution_result.failure_code.startswith(
        "posttransport_target_safety_failure:"
    )
    assert execution.execution_result.artifacts == ()
    assert cap_charges == calls == 1
