"""PRODUCT-PATH-REGRESSION: bounded SearchOS breadcrumb navigation.

Proof class: PRODUCT. Validation bucket: phase_focus, with the N=1 re-entry and
ledger-rollback nodes promoted to semantic_search_lane; the cheap URL-free v2
proposal/work-order boundary is promoted to fast_pr. Surface guarded: the
ordinary SearchJudgment -> governed READ -> custody -> semantic/citation loop,
including physical reuse and first durable URL publication. High-custody or
closed-this-phase surface: exact navigation execution authority and durable
source custody are high-custody; routing policy, Map, Crawl, Focused Extract,
fallback, retry, browser, and live calls remain closed. Runtime/product path
guarded: offline ordinary run_pipeline() with fake model/provider responses.
Expected cost: sub-second owner sentinels and roughly two seconds per ordinary
product node locally. Promotion posture: one cheap broad fast_pr sentinel and
two durable semantic-search sentinels; N=2 and detailed custody cases remain
phase_focus. Demotion/retirement condition: narrow or replace when a successor
SearchOS recovery/re-entry owner provides equal-or-stronger product proof. Why
not all fast_pr: the custody, reuse, and rollback matrices are detailed domain
proof rather than ordinary PR tax.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

import core.searchos_slice_a_product_runtime as product_runtime
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
from core.searchos_iterative_judgment_runtime import (
    SearchOSRuntimeError,
    validate_searchos_judgment_model_output,
)
from core.searchos_navigation_runtime import (
    SearchOSNavigationDestinationRegistry,
    SearchOSNavigationError,
    SearchOSNavigationExecutionOverlayV1,
    SearchOSNavigationPacketCommitRegistry,
)
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
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
    assert reference["secondary_source_provenance"] == {
        "final_url": values["exact_url"]
    }
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


def _kernel_trace(harness) -> dict[str, object]:
    return dict(harness.run_kernel.to_trace_fragment()["run_kernel"])


def _navigation_commit_observations(harness) -> list[dict[str, object]]:
    return [
        dict(item)
        for item in _kernel_trace(harness)["observations"]
        if item.get("stage") == "searchos_navigation_physical_custody"
        and item.get("status") == "completed"
    ]


def _navigation_decision_from_prompt(prompt: str) -> tuple[dict[str, object], dict[str, object]]:
    payload = json.loads(prompt)
    authorized = dict(payload["authorized_request"])
    contract = dict(payload["decision_contract"])
    custody_refs = list(authorized.get("read_custody_refs") or ())
    decision = {
        "schema_version": contract["decision_schema_version"],
        "judgment_request_id": authorized["judgment_request_id"],
        "judgment_request_digest": authorized["judgment_request_digest"],
        "slot_id": dict(authorized["slot_ref"])["slot_id"],
        "action": "REQUEST_NAVIGATE_BREADCRUMB",
        "navigation_candidate_ref": dict(authorized["navigation_candidate_refs"][0]),
        "reason": "exact current bounded navigation ref selected",
    }
    if custody_refs:
        decision["read_custody_assessments"] = [
            {
                "reviewed_custody_ref": dict(item),
                "material_disposition": "read_insufficient",
                "reason_code": "required_information_absent",
            }
            for item in custody_refs
        ]
    return authorized, decision


def test_n1_navigation_reuses_one_physical_destination_and_reenters_citation_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parents = [
        "https://alpha.example/parent-1",
        "https://alpha.example/parent-2",
    ]
    destination = "https://alpha.example/current"
    rejected_query_secret = "PHASE_NAV_QUERY_SECRET_91B7"
    parent_markdown = (
        "This page does not answer the question. "
        "[Current source](/current) "
        f"[rejected](/ignored?token={rejected_query_secret})"
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=[
            {
                "title": f"Alpha parent {index}",
                "url": url,
                "text": f"Directional parent {index}.",
            }
            for index, url in enumerate(parents, 1)
        ],
        read_content_by_url={
            **{url: parent_markdown for url in parents},
            destination: "Alpha's current official operating rule is Rule 17.",
        },
        read_assessment_decision="NAVIGATE_WHEN_AVAILABLE",
        raw_author_response=f"Alpha follows Rule 17. [[1]]({destination})",
    )

    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos["readiness_projection"]["all_required_slots_slice_a_ready"] is True
    assert searchos.get("component_receiver_failure") is None
    assert all(
        item["semantic_admission_status"] == "admitted"
        and item["searchos_handoff_material_consumed"] is True
        for item in searchos["semantic_outcomes_by_slot"].values()
    )
    assert harness.read_transport_calls == [*parents, destination]
    assert harness.read_transport_calls.count(destination) == 1
    assert len(harness.search_calls) == 1

    navigation_state = harness.run_kernel.state.searchos_navigation_state
    assert navigation_state["logical_edge_charges"] == 2
    assert navigation_state["logical_read_nomination_charges"] == 2
    use_refs = list(navigation_state["use_custody_refs_by_id"].values())
    assert len(use_refs) == 2
    assert len({dict(item["slot_ref"])["slot_id"] for item in use_refs}) == 2
    assert len({item["physical_identity_digest"] for item in use_refs}) == 1
    assert len(
        {
            json.dumps(item["fetch_read_content_packet_ref"], sort_keys=True)
            for item in use_refs
        }
    ) == 1
    assert all(item["physical_acquisition_origin"] == "navigation_candidate" for item in use_refs)

    semantic_material = list(harness.searchos_product_result.searchos_semantic_material)
    assert len(semantic_material) == 2
    assert all(item["url"] == destination for item in semantic_material)
    assert all(item["physical_acquisition_origin"] == "navigation_candidate" for item in semantic_material)

    kernel_trace = _kernel_trace(harness)
    serialized_actions = json.dumps(kernel_trace["actions"], sort_keys=True)
    assert destination not in serialized_actions
    destination_observations = [
        item
        for item in kernel_trace["observations"]
        if destination in json.dumps(item, sort_keys=True)
    ]
    assert destination_observations
    assert destination_observations[0]["stage"] == "searchos_navigation_physical_custody"
    assert destination_observations[0]["observation_type"] == (
        "acquisition_navigation_physical_custody_committed"
    )
    commit_payload = dict(destination_observations[0]["payload"])
    packet = dict(commit_payload["committed_fetch_read_content_packet"])
    reference = dict(packet["reference_records"][0])
    ledger_record = dict(
        commit_payload["evidence_ledger_observation"]["fetch_read_candidate_custody"][0]
    )
    physical_record = dict(commit_payload["navigation_physical_custody_record"])
    assert packet["attempted_url"] == packet["durable_source_url"] == destination
    assert reference["attempted_url"] == reference["durable_source_url"] == destination
    assert ledger_record["attempted_url"] == ledger_record["durable_source_url"] == destination
    assert physical_record["durable_source_url"] == destination
    assert all(item["url"] == destination for item in searchos["semantic_material_refs"])

    serialized_kernel = json.dumps(kernel_trace, sort_keys=True)
    serialized_outcome = json.dumps(outcome.execution_trace, sort_keys=True)
    assert rejected_query_secret not in serialized_kernel
    assert rejected_query_secret not in serialized_outcome
    assert parent_markdown not in serialized_kernel
    assert "SearchOSNavigationExtractionDraftV1" not in serialized_kernel
    assert "SearchOSNavigationDestinationRegistry" not in serialized_kernel
    assert "selected_urls" not in json.dumps(
        [
            item
            for item in kernel_trace["actions"] + kernel_trace["observations"]
            if "navigation" in str(item.get("stage") or "")
        ],
        sort_keys=True,
    )
    assert all(destination not in prompt for prompt in harness.searchos_judgment_prompts)
    assert all(rejected_query_secret not in prompt for prompt in harness.searchos_judgment_prompts)
    assert rejected_query_secret not in (tmp_path / "execution.jsonl").read_text(encoding="utf-8")

    query_plan = [item.to_dict() for item in harness.read_query_plan.items]
    assert destination not in json.dumps(query_plan, sort_keys=True)
    assert all("navigation" not in str(item.get("origin") or "") for item in query_plan)
    assert destination in json.dumps(outcome.execution_trace["final_answer_packet"], sort_keys=True)
    assert destination in json.dumps(
        outcome.execution_trace["citation_source_handoff_contract"],
        sort_keys=True,
    )

    navigation_prompts = [
        prompt
        for prompt in harness.searchos_judgment_prompts
        if json.loads(prompt)["authorized_request"].get("navigation_candidate_refs")
    ]
    assert navigation_prompts
    authorized, valid_output = _navigation_decision_from_prompt(navigation_prompts[0])
    validated = validate_searchos_judgment_model_output(
        request=authorized,
        model_output=valid_output,
    )
    assert validated["action"] == "REQUEST_NAVIGATE_BREADCRUMB"
    for forbidden_field in ("url", "provider", "route"):
        with pytest.raises(SearchOSRuntimeError):
            validate_searchos_judgment_model_output(
                request=authorized,
                model_output={**valid_output, forbidden_field: destination},
            )
    stale_output = json.loads(json.dumps(valid_output))
    stale_output["navigation_candidate_ref"]["navigation_candidate_ref_digest"] = "0" * 64
    with pytest.raises(SearchOSRuntimeError):
        validate_searchos_judgment_model_output(
            request=authorized,
            model_output=stale_output,
        )


def test_n2_navigation_uses_existing_multicomponent_receiver_with_physical_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parents = [f"https://shared.example/parent-{index}" for index in range(1, 9)]
    alpha_destination = "https://shared.example/alpha-current"
    beta_destination = "https://shared.example/beta-current"
    parent_content = {
        url: (
            "This page does not answer the question. "
            + (
                "[Current source](/alpha-current)"
                if index % 2
                else "[Current source](/beta-current)"
            )
        )
        for index, url in enumerate(parents, 1)
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="Compare Alpha and Beta current official operating rates.",
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        query_type="comparison",
        router_entities=("Alpha", "Beta"),
        researcher_queries=[
            "Alpha current official operating rate",
            "Beta current official operating rate",
        ],
        evidence_rows=[
            {
                "title": f"Shared parent {index}",
                "url": url,
                "text": f"Directional parent {index}.",
            }
            for index, url in enumerate(parents, 1)
        ],
        read_content_by_url={
            **parent_content,
            alpha_destination: "Alpha is 17 units per hour.",
            beta_destination: "Beta is 19 units per hour.",
        },
        read_assessment_decision="NAVIGATE_WHEN_AVAILABLE",
    )

    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    readiness = dict(searchos["readiness_projection"])
    assert readiness["all_required_slots_slice_a_ready"] is True
    assert readiness["required_ready_count"] == 4
    assert searchos.get("component_receiver_failure") is None
    assert all(
        item["component_analyst_proposal_status"] == "proposed"
        and item["component_dprime_validation_status"] == "accepted"
        and item["semantic_admission_status"] == "admitted"
        and item["searchos_handoff_material_consumed"] is True
        for item in searchos["semantic_outcomes_by_slot"].values()
    )
    component_projection = dict(
        harness.run_kernel.state.projections["multicomponent_component_admission"]
    )
    assert component_projection["component_count"] == 2
    assert component_projection["admitted_component_count"] == 2

    assert harness.read_transport_calls.count(alpha_destination) == 1
    assert harness.read_transport_calls.count(beta_destination) == 1
    assert len(harness.read_transport_calls) == 6
    assert len(harness.search_calls) == 1
    navigation_state = harness.run_kernel.state.searchos_navigation_state
    assert navigation_state["logical_edge_charges"] == 4
    assert navigation_state["logical_read_nomination_charges"] == 4
    use_refs = list(navigation_state["use_custody_refs_by_id"].values())
    assert len(use_refs) == 4
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in use_refs:
        grouped.setdefault(str(item["physical_identity_digest"]), []).append(item)
    assert sorted(len(items) for items in grouped.values()) == [1, 3]
    for items in grouped.values():
        assert len(
            {
                json.dumps(item["fetch_read_content_packet_ref"], sort_keys=True)
                for item in items
            }
        ) == 1
        assert len(
            {
                json.dumps(item["evidence_ledger_custody_ref"], sort_keys=True)
                for item in items
            }
        ) == 1
        assert all(item["physical_acquisition_origin"] == "navigation_candidate" for item in items)

    navigation_physical = [
        item
        for item in navigation_state["physical_custody_by_digest"].values()
        if item["physical_acquisition_origin"] == "navigation_candidate"
    ]
    assert len(navigation_physical) == 2
    semantic = list(harness.searchos_product_result.searchos_semantic_material)
    assert [item["url"] for item in semantic].count(alpha_destination) == 1
    assert [item["url"] for item in semantic].count(beta_destination) == 3
    assert all(item["physical_acquisition_origin"] == "navigation_candidate" for item in semantic)
    assert harness.forbidden_live_calls == []
    execution_observations = list(
        harness.run_kernel.state.acquisition_control_state["execution_observations_by_id"].values()
    )
    assert all(
        item.get("provider_failure_fallback_attempted") is not True
        for item in execution_observations
    )
    assert all(
        alpha_destination not in prompt and beta_destination not in prompt
        for prompt in harness.searchos_judgment_prompts
    )


def test_navigation_ledger_failure_rolls_back_without_durable_url_or_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = "https://alpha.example/parent"
    destination = "https://alpha.example/ledger-failure-destination"
    rejected_query_secret = "PHASE_LEDGER_ROLLBACK_SECRET_27D4"

    def fail_navigation_ledger_admission(**_kwargs):
        raise RuntimeError("injected_navigation_ledger_admission_failure")

    monkeypatch.setattr(
        product_runtime,
        "admit_navigation_packet_commit_to_evidence_ledger",
        fail_navigation_ledger_admission,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="What is Alpha's operating rate?",
        core_topic="Alpha operating rate",
        primary_entity="Alpha",
        researcher_queries=["Alpha operating rate"],
        evidence_rows=[
            {
                "title": "Alpha parent",
                "url": parent,
                "text": "Directional parent.",
            }
        ],
        read_content_by_url={
            parent: (
                "This page does not answer the question. "
                "[Current rate](/ledger-failure-destination) "
                f"[rejected](/ignored?token={rejected_query_secret})"
            ),
            destination: "Alpha is 17 units per hour.",
        },
        read_assessment_decision="NAVIGATE_WHEN_AVAILABLE",
    )

    assert harness.read_transport_calls == [parent, destination]
    assert harness.read_transport_calls.count(destination) == 1
    assert _navigation_commit_observations(harness) == []
    kernel_trace = _kernel_trace(harness)
    failed_custody_observations = [
        item
        for item in kernel_trace["observations"]
        if item.get("stage") == "searchos_navigation_physical_custody"
    ]
    assert len(failed_custody_observations) == 1
    assert failed_custody_observations[0]["status"] == "failed"
    assert failed_custody_observations[0]["payload"] == {
        "durable_source_commit_boundary": False,
        "failure_code": "read_authority_or_route_blocked:RuntimeError",
    }
    serialized_kernel = json.dumps(kernel_trace, sort_keys=True)
    assert destination not in serialized_kernel
    assert rejected_query_secret not in serialized_kernel
    assert destination not in json.dumps(outcome.execution_trace, sort_keys=True)
    assert harness.searchos_product_result.searchos_semantic_material == ()
    navigation_state = harness.run_kernel.state.searchos_navigation_state
    assert navigation_state["physical_custody_by_digest"]
    assert all(
        item["physical_acquisition_origin"] == "discovery_candidate"
        for item in navigation_state["physical_custody_by_digest"].values()
    )
    assert len(navigation_state["terminal_physical_operations_by_key"]) == 1
    operation_key = next(iter(navigation_state["terminal_physical_operations_by_key"]))
    assert operation_key.startswith("read-navigation:")
    assert navigation_state["logical_edge_charges"] == 1
    assert navigation_state["logical_read_nomination_charges"] == 1
    assert all(destination not in prompt for prompt in harness.searchos_judgment_prompts)
