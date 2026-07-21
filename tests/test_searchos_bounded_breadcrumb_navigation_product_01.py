"""Offline ordinary-path proof for SearchOS bounded breadcrumb navigation."""

from __future__ import annotations

import json
from hashlib import sha256

import pytest

from core.acquisition_control import (
    AcquisitionExecutionObservationV2,
    AcquisitionNeedProposalV1,
    AcquisitionNeedProposalV2,
    AcquisitionWorkOrderV2,
    build_acquisition_work_order,
    derive_acquisition_capability_decision,
    initial_acquisition_control_state,
)
from core.evidence_ledger import EvidenceLedger
from core.evidence_ledger_candidate_custody import (
    EvidenceLedgerCandidateCustodyError,
    admit_navigation_packet_commit_to_evidence_ledger,
    build_evidence_ledger_observation_from_fetch_read_content_packet,
)
from core.fetch_read_content_reference import (
    build_navigation_fetch_read_content_packet_v2,
    validate_fetch_read_content_packet,
)
from core.routing import acquisition_routing_policy_ref
from core.searchos_navigation_runtime import (
    SearchOSNavigationDestinationRegistry,
    SearchOSNavigationError,
    SearchOSNavigationExecutionOverlayV1,
    SearchOSNavigationPacketCommitRegistry,
)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _ref(kind: str, seed: str) -> dict[str, str]:
    return {
        f"{kind}_id": f"{kind}:{seed}",
        f"{kind}_digest": _digest(seed),
    }


def _authority():
    contract = {
        "source": "current_answer_contract",
        "contract_version": "contract-v1",
        "contract_digest": _digest("contract"),
    }
    component = {
        "component_id": "component-1",
        "component_revision": "revision-1",
        "component_digest": _digest("component"),
    }
    obligation = {
        "source_obligation_id": "obligation-1",
        "source_obligation_digest": _digest("obligation"),
        "binding_kind": "pre_acquisition_source_obligation_lineage",
        "answer_contract_digest": contract["contract_digest"],
        "component_ids": [component["component_id"]],
        "active": True,
    }
    snapshot_core = {
        "run_id": "run-1",
        "request_id": "request-1",
        "answer_contract_ref": contract,
        "components_by_id": {component["component_id"]: component},
        "source_obligations_by_id": {
            obligation["source_obligation_id"]: obligation
        },
        "lineage_posture": "pre_acquisition_only_no_satisfaction_authority",
    }
    snapshot = {
        **snapshot_core,
        "snapshot_digest": _stable_json_digest(snapshot_core),
    }
    return contract, component, obligation, snapshot


def _stable_json_digest(value) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _navigation_contracts(exact_url: str = "https://example.com/a/"):
    contract, component, obligation, snapshot = _authority()
    registry = SearchOSNavigationDestinationRegistry(
        run_id="run-1", request_id="request-1"
    )
    binding = registry.register(exact_url)
    edge_ref = _ref("navigation_edge", "edge")
    selection_ref = _ref("navigation_selection", "selection")
    lineage_ref = _ref("navigation_lineage", "lineage")
    contributor_ref = _ref("navigation_contributor", "contributor")
    parent_ref = _ref("searchos_parent_use_custody", "parent")
    proposal = AcquisitionNeedProposalV2.create(
        run_id="run-1",
        request_id="request-1",
        producer_surface="SearchOS.SearchJudgment",
        answer_contract_ref=contract,
        source_obligation_ref=obligation,
        component_ref=component,
        navigation_destination_binding_ref=binding,
        navigation_edge_ref=edge_ref,
        navigation_selection_ref=selection_ref,
        navigation_lineage_snapshot_ref=lineage_ref,
        representative_contributor_ref=contributor_ref,
        parent_custody_ref=parent_ref,
        physical_identity_digest=binding["physical_identity_digest"],
        full_destination_digest=binding["full_destination_digest"],
        operation_identity_key=(
            f"read-navigation:{binding['physical_identity_digest']}"
        ),
    )
    state = initial_acquisition_control_state(
        run_id="run-1", request_id="request-1"
    )
    decision = derive_acquisition_capability_decision(
        proposal=proposal,
        authority_snapshot=snapshot,
        acquisition_control_state=state,
    )
    work_order = build_acquisition_work_order(
        proposal=proposal,
        decision=decision,
        runkernel_authorization_ref=_ref("action", "work-order-admission"),
    )
    assert isinstance(work_order, AcquisitionWorkOrderV2)
    route_ref = _ref("route_observation", "route")
    overlay = SearchOSNavigationExecutionOverlayV1.create(
        run_id="run-1",
        request_id="request-1",
        destination_binding_ref=binding,
        navigation_edge_ref=edge_ref,
        navigation_selection_ref=selection_ref,
        work_order_ref=work_order.ref(),
        route_observation_ref=route_ref,
        destination_registry=registry,
    )
    return {
        "contract": contract,
        "component": component,
        "obligation": obligation,
        "snapshot": snapshot,
        "registry": registry,
        "binding": binding,
        "edge_ref": edge_ref,
        "selection_ref": selection_ref,
        "lineage_ref": lineage_ref,
        "contributor_ref": contributor_ref,
        "parent_ref": parent_ref,
        "proposal": proposal,
        "decision": decision,
        "work_order": work_order,
        "route_ref": route_ref,
        "overlay": overlay,
        "exact_url": exact_url,
    }


def test_navigation_v2_proposal_and_work_order_are_url_free() -> None:
    values = _navigation_contracts(
        "https://example.com/phase-unique-pre-custody-path-3f2d/"
    )
    assert values["decision"].decision_status == "accepted"
    assert values["decision"].derived_capability == "READ"
    proposal = values["proposal"].to_dict()
    work_order = values["work_order"].to_dict()
    serialized = json.dumps(
        {"proposal": proposal, "work_order": work_order}, sort_keys=True
    )
    assert proposal["schema_version"] == "acquisition_need_proposal_v2"
    assert work_order["schema_version"] == "acquisition_work_order_v2"
    assert "phase-unique-pre-custody-path-3f2d" not in serialized
    assert "selected_urls" not in serialized
    assert "available_urls" not in serialized
    assert "root_url" not in serialized
    assert "https://" not in serialized


def test_navigation_overlay_is_exact_one_shot_and_nonserializable() -> None:
    values = _navigation_contracts()
    overlay = values["overlay"]
    overlay.validate_lineage(
        work_order_ref=values["work_order"].ref(),
        route_observation_ref=values["route_ref"],
        navigation_edge_ref=values["edge_ref"],
        navigation_selection_ref=values["selection_ref"],
        destination_binding_ref=values["binding"],
    )
    overlay_ref = overlay.ref()
    assert "url" not in json.dumps(overlay_ref).casefold()
    overlay.consume(execution_action_ref=_ref("action", "execute"))
    assert overlay.consumed_action_ref == _ref("action", "execute")
    with pytest.raises(SearchOSNavigationError, match="overlay_unavailable"):
        overlay.consume(execution_action_ref=_ref("action", "replay"))
    overlay.expire()
    assert overlay.exact_execution_url == ""
    with pytest.raises(TypeError, match="nonserializable"):
        overlay.__reduce__()


def test_navigation_execution_observation_is_url_free_v2() -> None:
    values = _navigation_contracts()
    work_order = values["work_order"]
    artifact_digest = _digest("safe-navigation-artifact")
    artifact_ref = {
        "artifact_id": (
            "acquisition-artifact-navigation:"
            f"{work_order.work_order_id}:{artifact_digest[:20]}"
        ),
        "artifact_digest": artifact_digest,
        "kind": "selected_url_read",
        "acquisition_job_id": work_order.work_order_id,
        "provider": "linkup",
        "operation": "fetch",
        "provider_variant": "standard",
        "output_type": "searchResults",
        "status": "readable",
        "physical_acquisition_origin": "navigation_candidate",
        "navigation_destination_binding_ref": values["binding"],
        "navigation_edge_ref": values["edge_ref"],
        "navigation_selection_ref": values["selection_ref"],
        "physical_identity_digest": values["binding"][
            "physical_identity_digest"
        ],
        "full_destination_digest": values["binding"][
            "full_destination_digest"
        ],
        "retained_digest": _digest("content"),
        "retained_character_count": 7,
        "authority_posture": "acquisition_material_only",
        "retained_text_included": False,
        "raw_provider_payload_included": False,
        "exact_locator_included": False,
    }
    observation = AcquisitionExecutionObservationV2.create(
        work_order=work_order,
        completed_route_ref=values["route_ref"],
        execution_action_ref=_ref("action", "execute"),
        navigation_execution_overlay_ref=values["overlay"].ref(),
        execution_result_trace={
            "status": "succeeded",
            "artifact_refs": [artifact_ref],
            "provider_calls_attempted": 1,
            "provider_calls_completed": 1,
            "provider_failure_fallback_attempted": False,
        },
        artifact_refs=[artifact_ref],
        provider_calls_attempted=1,
        provider_calls_completed=1,
        terminal_status="completed",
        failure_or_block_code=None,
    )
    serialized = json.dumps(observation.to_dict(), sort_keys=True)
    assert observation.schema_version == "acquisition_execution_observation_v2"
    assert "https://" not in serialized
    assert "selected_urls" not in serialized
    assert observation.exact_locator_included is False


def _local_packet(values, *, text: str = "Bounded destination content"):
    return build_navigation_fetch_read_content_packet_v2(
        run_id="run-1",
        request_id="request-1",
        answer_contract_ref=values["contract"],
        source_obligation_ref=values["obligation"],
        component_ref=values["component"],
        acquisition_work_order_ref=values["work_order"].ref(),
        route_observation_ref=values["route_ref"],
        execution_action_ref=_ref("action", "execute"),
        acquisition_artifact_ref=_ref("artifact", "artifact"),
        physical_acquisition_ref=_ref("physical_acquisition", "physical"),
        navigation_destination_binding_ref=values["binding"],
        navigation_edge_ref=values["edge_ref"],
        navigation_selection_ref=values["selection_ref"],
        navigation_lineage_snapshot_ref=values["lineage_ref"],
        representative_contributor_ref=values["contributor_ref"],
        parent_custody_ref=values["parent_ref"],
        operation_identity_key=values["work_order"].operation_identity_key,
        attempted_url=values["exact_url"],
        durable_source_url=values["exact_url"],
        provider="linkup",
        operation="fetch",
        bounded_text=text,
        retained_digest=_digest(text),
        retained_character_count=len(text),
        content_type="text/markdown",
        http_status=200,
        content_title="Destination",
        secondary_source_provenance={
            "canonical_url": "https://other.example.net/ignored",
            "final_url": values["exact_url"],
        },
    )


def test_atomic_ledger_commit_is_first_canonical_exact_url() -> None:
    unique_path = "phase-unique-durable-source-commit-770b"
    values = _navigation_contracts(f"https://example.com/{unique_path}/")
    packet = _local_packet(values)
    assert validate_fetch_read_content_packet(packet) == packet
    packet_registry = SearchOSNavigationPacketCommitRegistry(
        run_id="run-1", request_id="request-1"
    )
    commit_ref = packet_registry.register(packet)
    assert unique_path not in json.dumps(commit_ref, sort_keys=True)
    with pytest.raises(
        EvidenceLedgerCandidateCustodyError,
        match="transient packet commit ref",
    ):
        build_evidence_ledger_observation_from_fetch_read_content_packet(packet)

    original = EvidenceLedger()
    result = admit_navigation_packet_commit_to_evidence_ledger(
        evidence_ledger=original,
        packet_registry=packet_registry,
        packet_commit_ref=commit_ref,
    )
    assert original.candidates == {}
    canonical = result.evidence_ledger.to_projection().to_dict()
    serialized = json.dumps(canonical, sort_keys=True)
    assert unique_path in serialized
    custody = next(iter(result.evidence_ledger.fetch_read_candidate_custody.values()))
    assert custody["durable_source_url"] == values["exact_url"]
    assert custody["attempted_url"] == values["exact_url"]
    assert custody["physical_acquisition_origin"] == "navigation_candidate"
    reference = packet["reference_records"][0]
    assert reference["durable_source_url"] == values["exact_url"]
    assert result.committed_fetch_read_packet == packet
    with pytest.raises(SearchOSNavigationError, match="commit_unavailable"):
        packet_registry.resolve(commit_ref)


def test_failed_ledger_admission_discards_local_packet_without_durable_url(
    monkeypatch,
) -> None:
    unique_path = "phase-unique-ledger-failure-no-commit-a913"
    values = _navigation_contracts(f"https://example.com/{unique_path}")
    packet_registry = SearchOSNavigationPacketCommitRegistry(
        run_id="run-1", request_id="request-1"
    )
    commit_ref = packet_registry.register(_local_packet(values))

    def _fail(_self, _observation):
        raise RuntimeError("injected ledger admission failure")

    monkeypatch.setattr(EvidenceLedger, "reduce_observation", _fail)
    with pytest.raises(RuntimeError, match="injected ledger"):
        admit_navigation_packet_commit_to_evidence_ledger(
            evidence_ledger=EvidenceLedger(),
            packet_registry=packet_registry,
            packet_commit_ref=commit_ref,
        )
    with pytest.raises(SearchOSNavigationError, match="commit_unavailable"):
        packet_registry.resolve(commit_ref)
    assert unique_path not in json.dumps(commit_ref, sort_keys=True)


def test_discovery_v1_schema_replay_remains_exact() -> None:
    # The exact v1 parser still rejects navigation-v2 fields rather than
    # silently reinterpreting the discovery-origin record.
    with pytest.raises(Exception, match="unknown fields"):
        AcquisitionNeedProposalV1.from_dict(
            {
                "schema_version": "acquisition_need_proposal_v1",
                "navigation_destination_binding_ref": _ref("binding", "x"),
            }
        )
    assert acquisition_routing_policy_ref()["owner"] == "core.routing"
