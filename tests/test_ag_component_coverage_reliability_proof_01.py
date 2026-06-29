from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.analysis_gap_followup_search_packet import (
    build_followup_search_intent_packet,
    validate_followup_search_intent_packet,
)
from core.component_coverage_record import (
    ComponentCoverageRecord,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageState,
    CurrentnessPosture,
    DerivedSupportStatus,
    EvidenceBasis,
    EvidenceCustodyStatus,
    EvidenceLedgerSnapshotBinding,
    ExplicitnessPosture,
    FollowupNeed,
    ModeBudgetPosture,
    SemanticObservationCoverageRef,
    SemanticSupportStatus,
    SourceObligationStatus,
    SupportPosture,
    VersionValidity,
)
from core.component_coverage_reduction_runtime import evidence_ledger_projection_digest
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION
from core.evidence_ledger_lifecycle import reduce_fetch_read_content_packet_into_evidence_ledger
from core.evidence_relative_analysis_packet import (
    build_evidence_relative_analysis_packet,
    validate_evidence_relative_analysis_packet,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
    validate_fetch_read_content_packet,
)
from core.run_kernel import Observation, ObservationType, RunKernelTransitionError, RunStageStatus
from core.search_result_candidate_packet import validate_search_result_candidate_packet
from core.semantic_observation_foundation import (
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)
from tests.test_ag_analysis_gap_followup_search_01 import (
    _analysis_gap_proposal,
    _contract_ref_from_projection,
)
from tests.test_ag_analyst_evidence_relative_report_01 import (
    _records_by_status,
    _support_proposal,
)
from tests.test_ag_fetch_read_content_reference_01 import _failed_material, _readable_material
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

ROOT = Path(__file__).resolve().parents[1]
THIS_TEST = ROOT / "tests" / "test_ag_component_coverage_reliability_proof_01.py"
CORE_MODULES = (
    ROOT / "core" / "search_result_candidate_packet.py",
    ROOT / "core" / "fetch_read_content_reference.py",
    ROOT / "core" / "evidence_ledger_candidate_custody.py",
    ROOT / "core" / "evidence_relative_analysis_packet.py",
    ROOT / "core" / "analysis_gap_followup_search_packet.py",
    ROOT / "core" / "component_coverage_record.py",
    ROOT / "core" / "component_coverage_reduction_runtime.py",
)
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "architecture" / "AG_COMPONENT_COVERAGE_RELIABILITY_PROOF_01.md",
)

REPORT_NAME = "component_coverage_reliability_report"
RUN_ID_FRAGMENT = "ag-search-planner-revision-01"


def _chain_fixture() -> dict[str, Any]:
    kernel, candidate_packet = _packet_from_state(candidate_count=2)
    materials = [
        _readable_material(candidate_packet, index=0),
        _failed_material(candidate_packet, index=1),
    ]
    fetch_read_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        materials,
    )
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
    )
    readable = _records_by_status(ledger_projection, "readable")[0]
    failed = _records_by_status(ledger_projection, "failed")[0]
    contract_ref = _contract_ref_from_projection(ledger_projection)
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=ledger_projection,
        analyst_proposal_records=[
            _support_proposal(readable),
            _analysis_gap_proposal(failed, "missing_readable_source"),
        ],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    followup_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet,
    )
    return {
        "kernel": kernel,
        "candidate_packet": validate_search_result_candidate_packet(deepcopy(candidate_packet)),
        "fetch_read_packet": validate_fetch_read_content_packet(deepcopy(fetch_read_packet)),
        "ledger_projection": ledger_projection,
        "analysis_packet": validate_evidence_relative_analysis_packet(deepcopy(analysis_packet)),
        "followup_packet": validate_followup_search_intent_packet(deepcopy(followup_packet)),
        "readable_custody_record": readable,
        "failed_custody_record": failed,
    }


def _initial_component_ref(kernel: Any) -> Mapping[str, Any]:
    return kernel.state.initial_answer_contract["accepted_answer_component_refs"][0]


def _fetch_read_reference(fetch_read_packet: Mapping[str, Any], custody_record: Mapping[str, Any]) -> dict[str, Any]:
    for reference in fetch_read_packet["reference_records"]:
        if reference["reference_id"] == custody_record["reference_id"]:
            return dict(reference)
    raise AssertionError("fixture custody record is not represented in FetchReadContentPacket")


def _semantic_content_ref_from_fetch_read(
    *,
    kernel: Any,
    fetch_read_reference: Mapping[str, Any],
) -> SanitizedContentReference:
    accepted = kernel.state.initial_answer_contract
    component_ref = _initial_component_ref(kernel)
    return SanitizedContentReference(
        content_ref_id=fetch_read_reference["reference_id"],
        evidence_ref_id=fetch_read_reference["candidate_id"],
        admitted_evidence_ref=fetch_read_reference["candidate_id"],
        source_id=f"source:{fetch_read_reference['candidate_domain']}",
        source_digest=f"source-digest:{fetch_read_reference['reference_digest'][:32]}",
        source_url=fetch_read_reference["resolved_url"] or fetch_read_reference["candidate_url"],
        source_title=fetch_read_reference["content_title"] or fetch_read_reference["candidate_title"],
        source_domain=fetch_read_reference["resolved_domain"] or fetch_read_reference["candidate_domain"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text=fetch_read_reference["bounded_text"],
        extraction_method="fixture_only_component_coverage_reliability_proof",
        worker_kind="fixture_bridge_from_fetch_read_content_packet",
        currentness="fixture_current_for_2026",
        observed_at=fetch_read_reference.get("retrieved_or_observed_at") or "2026-06-28T00:00:00Z",
        metadata={
            "fixture_only": True,
            "search_result_candidate_packet_digest": fetch_read_reference[
                "search_result_candidate_packet_digest"
            ],
            "fetch_read_content_packet_digest": fetch_read_reference.get("fetch_read_content_packet_digest"),
        },
    ).require_valid()


def _semantic_observation_from_content_ref(
    *,
    kernel: Any,
    content_ref: SanitizedContentReference,
) -> SemanticObservation:
    accepted = kernel.state.initial_answer_contract
    component_ref = _initial_component_ref(kernel)
    return SemanticObservation(
        observation_id="observation:ag-component-coverage:supportable",
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        contract_version=accepted["accepted_contract_version"],
        contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        evidence_refs=(content_ref.evidence_ref_id,),
        content_refs=(content_ref.content_ref_id,),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value="fixture-only bounded support from readable sanitized content",
        normalization_fit="no computation; source wording only",
        scope_fit="requested 2026 component fixture",
        assumption_fit="fixture bridge only; not product parser output",
        inference_depth=0,
        candidate_caveats=(
            "EvidenceLedger fetch/read custody is observed and lineage-bound, not accepted final evidence.",
        ),
        candidate_followup_gaps=(
            "Product bridge from Analyst possible_support_proposal to SemanticObservation admission is missing.",
        ),
        candidate_contract_amendment_notes=(
            "No contract mutation is created by this fixture-only observation.",
        ),
        metadata={"fixture_only": True, REPORT_NAME: True},
    ).require_valid(content_references=(content_ref,))


def _admit_semantic_observation(
    *,
    kernel: Any,
    observation: SemanticObservation,
    content_ref: SanitizedContentReference,
) -> None:
    component_ref = _initial_component_ref(kernel)
    action = kernel.authorize_semantic_observation_admission(
        semantic_observation_id=observation.observation_id,
        semantic_observation_digest=observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "semantic_observation": observation.to_dict(),
                "sanitized_content_references": [content_ref.to_dict()],
            },
        )
    )


def _ledger_binding(kernel: Any) -> EvidenceLedgerSnapshotBinding:
    projection = kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        ref["observation_id"]
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, Mapping) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{kernel.state.run_id}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _coverage_record(
    *,
    kernel: Any,
    record_id: str,
    coverage_state: CoverageState,
    semantic_support_status: SemanticSupportStatus,
    source_obligation_status: SourceObligationStatus,
    content_availability_status: ContentAvailabilityStatus,
    evidence_custody_status: EvidenceCustodyStatus,
    evidence_basis: tuple[EvidenceBasis, ...],
    observation: SemanticObservation | None = None,
    content_ref: SanitizedContentReference | None = None,
    remaining_unknowns: tuple[str, ...] = (),
    followup_need: FollowupNeed = FollowupNeed.NONE,
    currentness_posture: CurrentnessPosture = CurrentnessPosture.UNKNOWN,
    metadata: Mapping[str, Any] | None = None,
) -> ComponentCoverageRecord:
    accepted = kernel.state.initial_answer_contract
    component_ref = _initial_component_ref(kernel)
    observation_refs: tuple[SemanticObservationCoverageRef, ...] = ()
    content_bindings: tuple[ContentReferenceCoverageBinding, ...] = ()
    if observation is not None:
        observation_refs = (SemanticObservationCoverageRef.from_observation(observation),)
    if content_ref is not None:
        content_bindings = (ContentReferenceCoverageBinding.from_content_reference(content_ref),)
    return ComponentCoverageRecord(
        record_id=record_id,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        request_digest=accepted["parent_question_meaning_record_digest"],
        accepted_contract_version=accepted["accepted_contract_version"],
        accepted_contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(kernel),
        coverage_state=coverage_state,
        semantic_support_status=semantic_support_status,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=source_obligation_status,
        content_availability_status=content_availability_status,
        evidence_custody_status=evidence_custody_status,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=observation_refs,
        content_reference_bindings=content_bindings,
        evidence_basis=evidence_basis,
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        currentness_posture=currentness_posture,
        remaining_unknowns=remaining_unknowns,
        required_caveats=("Do not upgrade observed custody to final evidence.",),
        prohibited_upgrades=("Do not treat Analyst possible_support_proposal as canonical coverage.",),
        followup_need=followup_need,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        metadata=dict(metadata or {}),
    )


def _reseal_coverage(record: ComponentCoverageRecord) -> dict[str, Any]:
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    return payload


def _reduce_coverage(kernel: Any, record: ComponentCoverageRecord) -> dict[str, Any]:
    component_ref = _initial_component_ref(kernel)
    action = kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": _reseal_coverage(record)},
        )
    )
    return dict(kernel.state.component_coverage_projection)


def _support_bridge(chain: Mapping[str, Any]) -> tuple[SanitizedContentReference, SemanticObservation]:
    fetch_read_ref = _fetch_read_reference(
        chain["fetch_read_packet"],
        chain["readable_custody_record"],
    )
    content_ref = _semantic_content_ref_from_fetch_read(
        kernel=chain["kernel"],
        fetch_read_reference=fetch_read_ref,
    )
    observation = _semantic_observation_from_content_ref(
        kernel=chain["kernel"],
        content_ref=content_ref,
    )
    return content_ref, observation


def _assert_downstream_closed(kernel: Any, projection: Mapping[str, Any] | None = None) -> None:
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.sufficiency_judgment_projection == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_authorization_state == {}
    if projection is None:
        return
    for field in (
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "followup_authorized",
        "query_plan_activated",
        "search_work_plan_activated",
        "citation_behavior_changed",
        "provider_search_behavior_changed",
        "runtime_behavior_changed",
    ):
        assert projection[field] is False


def component_coverage_reliability_report(
    *,
    chain: Mapping[str, Any],
    support_projection: Mapping[str, Any],
    missing_admission_error: str,
) -> dict[str, Any]:
    analysis_report = chain["analysis_packet"]["analyst_report"]
    gap = next(
        item
        for item in analysis_report["analysis_gap_proposals"]
        if item["gap_kind"] == "missing_readable_source"
    )
    followup = next(
        item
        for item in chain["followup_packet"]["analysis_gap_search_proposals"]
        if item["source_gap_id"] == gap["gap_id"]
    )
    kernel = chain["kernel"]
    current_contract = kernel.state.current_answer_contract
    initial_contract = kernel.state.initial_answer_contract
    current_digest = current_contract.get("accepted_contract_digest")
    initial_digest = initial_contract.get("accepted_contract_digest")
    return {
        "artifact": REPORT_NAME,
        "proof_class": "component_harness_proof",
        "validation_bucket": "phase_focus",
        "product_path_affected": "fixture/test harness only",
        "runtime_consumer": "core.component_coverage_reduction_runtime.build_component_coverage_reduction_state",
        "component_coverage_consumed_current_chain": "only_after_fixture_semantic_observation_admission_bridge",
        "semantic_observation_admission_required": True,
        "semantic_observation_admission_missing_from_current_packet_chain": True,
        "missing_admission_error": missing_admission_error,
        "current_contract_digest": current_digest,
        "initial_contract_digest": initial_digest,
        "current_to_initial_contract_bridge_required": current_digest != initial_digest,
        "components_evaluated": [
            {
                "attempt": "supportable_component_attempt",
                "component_id": support_projection["answer_component_id"],
                "coverage_result": support_projection["coverage_state"],
                "canonical_component_coverage_reduced": True,
                "source_obligation_status": support_projection["source_obligation_status"],
                "followup_need": support_projection["followup_need"],
                "upstream_artifacts_consumed": [
                    "SearchResultCandidatePacket.candidate_records[].candidate_id",
                    "FetchReadContentPacket.reference_records[].reference_id",
                    "EvidenceLedger.fetch_read_candidate_custody",
                    "fixture SemanticObservation admission",
                    "ComponentCoverageRecord proposal",
                ],
            },
            {
                "attempt": "blocked_followup_required_component",
                "component_id": gap["component_id"],
                "coverage_result": "blocked_passive_only",
                "canonical_component_coverage_reduced": False,
                "blocker_reason": (
                    "Analyst gap and FollowupSearchIntent proposal expose the blocker, "
                    "but no stable gap-to-ComponentCoverage reducer bridge exists."
                ),
                "analysis_gap_id": gap["gap_id"],
                "followup_proposal_id": followup["proposal_id"],
            },
        ],
        "fields_consumed": {
            "component_coverage_reducer": [
                "accepted_contract_version",
                "accepted_contract_digest",
                "answer_component_id",
                "component_revision",
                "component_digest",
                "coverage_record_id",
                "coverage_record_digest",
                "accepted_observation_refs[].observation_id",
                "accepted_observation_refs[].observation_digest",
                "content_reference_bindings[].content_ref_id",
                "content_reference_bindings[].content_digest",
                "content_reference_bindings[].evidence_ref_id",
                "evidence_ledger_binding.ledger_digest",
            ],
            "fixture_semantic_observation_admission_bridge": [
                "FetchReadContentPacket.reference_records[].bounded_text",
                "FetchReadContentPacket.reference_records[].reference_id",
                "FetchReadContentPacket.reference_records[].reference_digest",
                "EvidenceLedger.candidate_records[].candidate_id",
                "EvidenceLedger.custody_records[].candidate_id",
            ],
            "blocker_path_visible_not_reduced": [
                "analyst_report.analysis_gap_proposals[].gap_id",
                "FollowupSearchIntentPacket.analysis_gap_search_proposals[].proposal_id",
            ],
        },
        "fields_unused_by_component_coverage": [
            "SearchResultCandidatePacket.candidate_records[].snippet",
            "SearchResultCandidatePacket.candidate_records[].title",
            "FetchReadContentPacket.reference_records[].bounded_text outside fixture bridge",
            "EvidenceRelativeAnalysisPacket.analyst_report.findings[].proposal_summary",
            "EvidenceRelativeAnalysisPacket.analyst_report.findings[].reason",
            "FollowupSearchIntentPacket.analysis_gap_search_proposals[].proposed_query_hint",
            "FollowupSearchIntentPacket.analysis_gap_search_proposals[].required_source_class_hint",
        ],
        "missing_fields_or_bridges": [
            "EvidenceRelativeAnalysisPacket finding to SemanticObservation proposal/admission bridge",
            "analysis_gap/followup proposal refs as stable ComponentCoverage blocker lineage",
            "current_answer_contract to ComponentCoverage accepted-contract binding",
            "ledger accepted/final-evidence qualification before satisfied coverage",
        ],
        "surfaces_recommended_keep": [
            "SearchResultCandidatePacket as durable non-evidence candidate handoff",
            "FetchReadContentPacket / SanitizedContentReference as bounded read handoff",
            "EvidenceLedger candidate/content custody as custody lineage",
            "EvidenceRelativeAnalysisPacket as proposal-only analysis",
            "FollowupSearchIntentPacket as proposal-only review intent",
            "SemanticObservation admission as the next minimal bridge candidate",
        ],
        "surfaces_recommended_collapse_or_demote": [
            "search snippets as non-support lineage",
            "Analyst possible_support_proposal as non-canonical support",
            "FollowupSearchIntent proposal as non-authorization",
            "source_obligation_candidate_ids as lineage until real requirement links exist",
            "legacy AG-96 followup/SearchWorkPlan/offline SearchExecutor bridge paths",
        ],
        "semantic_observation_admission_bridge_recommended_next": True,
        "explicit_downstream_non_proofs": {
            "final_answer_packet_created": False,
            "author_input_created": False,
            "author_called": False,
            "product_correctness_claimed": False,
            "sufficiency_decided": False,
            "search_authorized_from_followup_intent": False,
        },
    }


def test_current_packet_chain_constructs_through_validators_without_live_execution() -> None:
    chain = _chain_fixture()

    assert chain["candidate_packet"]["candidate_count"] == 2
    assert chain["fetch_read_packet"]["reference_count"] == 2
    assert chain["analysis_packet"]["analyst_report"]["finding_count"] >= 1
    assert any(
        finding["proposal_kind"] == "possible_support_proposal"
        for finding in chain["analysis_packet"]["analyst_report"]["findings"]
    )
    assert chain["followup_packet"]["proposal_count"] >= 1
    assert chain["kernel"].state.run_id.endswith(RUN_ID_FRAGMENT)

    for packet in (
        chain["candidate_packet"],
        chain["fetch_read_packet"],
        chain["analysis_packet"],
        chain["followup_packet"],
    ):
        encoded = json.dumps(packet, sort_keys=True)
        assert '"raw_provider_payload":' not in encoded
        assert '"raw_search_response":' not in encoded
        assert '"raw_page_content":' not in encoded
        assert '"raw_prompt":' not in encoded

    assert chain["candidate_packet"]["fetch_read_executed"] is False
    assert chain["fetch_read_packet"]["raw_page_content_retained"] is False
    assert chain["fetch_read_packet"]["evidence_ledger_admitted"] is False
    assert chain["analysis_packet"]["semantic_observation_admitted"] is False
    assert chain["followup_packet"]["search_dispatched"] is False
    _assert_downstream_closed(chain["kernel"])


def test_supportable_component_reduces_only_after_fixture_semantic_observation_admission_bridge() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    content_ref, observation = _support_bridge(chain)
    record = _coverage_record(
        kernel=kernel,
        record_id="coverage:ag-component-coverage:supportable",
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        observation=observation,
        content_ref=content_ref,
        remaining_unknowns=("ledger candidate is observed, not accepted final evidence",),
        followup_need=FollowupNeed.OPTIONAL,
        currentness_posture=CurrentnessPosture.CURRENT,
    ).require_valid()

    with pytest.raises(RunKernelTransitionError, match="at least one admitted SemanticObservation") as excinfo:
        _reduce_coverage(kernel, record)
    missing_admission_error = str(excinfo.value)

    _admit_semantic_observation(kernel=kernel, observation=observation, content_ref=content_ref)
    projection = _reduce_coverage(kernel, record)

    assert projection["coverage_state"] == "supported_with_caveats"
    assert projection["semantic_support_status"] == "supported"
    assert projection["source_obligation_status"] == "partial"
    assert projection["followup_need"] == "optional"
    assert projection["accepted_observation_refs"][0]["observation_id"] == observation.observation_id
    assert projection["content_reference_bindings"][0]["content_ref_id"] == content_ref.content_ref_id
    assert projection["lineage"]["created_from"] == [
        "passive_component_coverage_record",
        "accepted_initial_answer_contract",
        "admitted_semantic_observation",
    ]
    assert missing_admission_error == (
        "component coverage reduction requires at least one admitted SemanticObservation"
    )
    _assert_downstream_closed(kernel, projection)


def test_satisfied_overclaim_from_current_chain_is_rejected_until_ledger_is_qualified() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    content_ref, observation = _support_bridge(chain)
    _admit_semantic_observation(kernel=kernel, observation=observation, content_ref=content_ref)
    satisfied = _coverage_record(
        kernel=kernel,
        record_id="coverage:ag-component-coverage:satisfied-overclaim",
        coverage_state=CoverageState.SATISFIED,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        source_obligation_status=SourceObligationStatus.NOT_APPLICABLE,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        observation=observation,
        content_ref=content_ref,
        currentness_posture=CurrentnessPosture.CURRENT,
    )

    with pytest.raises(
        RunKernelTransitionError,
        match=(
            "ledger_candidate_not_qualified|ledger_candidate_custody_fact_missing|"
            "source_requirement_link_missing|source_obligation_not_applicable_but_required"
        ),
    ):
        _reduce_coverage(kernel, satisfied)

    assert kernel.state.component_coverage_state == {}
    _assert_downstream_closed(kernel)


def test_blocked_followup_required_component_stays_non_supported_and_names_missing_blocker_bridge() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    gap = next(
        item
        for item in chain["analysis_packet"]["analyst_report"]["analysis_gap_proposals"]
        if item["gap_kind"] == "missing_readable_source"
    )
    proposal = next(
        item
        for item in chain["followup_packet"]["analysis_gap_search_proposals"]
        if item["source_gap_id"] == gap["gap_id"]
    )
    blocked = _coverage_record(
        kernel=kernel,
        record_id="coverage:ag-component-coverage:blocked-followup",
        coverage_state=CoverageState.BLOCKED,
        semantic_support_status=SemanticSupportStatus.UNKNOWN,
        source_obligation_status=SourceObligationStatus.UNSATISFIED,
        content_availability_status=ContentAvailabilityStatus.UNREADABLE,
        evidence_custody_status=EvidenceCustodyStatus.PARTIAL,
        evidence_basis=(EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,),
        remaining_unknowns=(
            f"analysis_gap_id={gap['gap_id']}",
            f"followup_proposal_id={proposal['proposal_id']}",
            "missing readable source prevents semantic support",
        ),
        followup_need=FollowupNeed.REQUIRED,
        metadata={
            "analysis_gap_id": gap["gap_id"],
            "followup_proposal_id": proposal["proposal_id"],
            "missing_bridge": "stable AnalysisGapSearchProposal to ComponentCoverage blocker lineage",
        },
    ).require_valid()

    assert blocked.coverage_state is CoverageState.BLOCKED
    assert blocked.semantic_support_status is SemanticSupportStatus.UNKNOWN
    assert blocked.followup_need is FollowupNeed.REQUIRED
    assert proposal["authorized"] is False
    assert proposal["search_dispatched"] is False
    assert proposal["evidence_ledger_admitted"] is False
    assert proposal["component_coverage_created"] is False

    with pytest.raises(RunKernelTransitionError, match="at least one admitted SemanticObservation"):
        _reduce_coverage(kernel, blocked)
    assert kernel.state.component_coverage_state == {}
    _assert_downstream_closed(kernel)


@pytest.mark.parametrize(
    ("record_id", "basis", "content_binding", "expected_error"),
    [
        (
            "coverage:ag-component-coverage:search-candidate-only",
            (EvidenceBasis.CANDIDATE_DISCOVERY,),
            False,
            "SemanticObservation refs",
        ),
        (
            "coverage:ag-component-coverage:fetch-read-only",
            (EvidenceBasis.ANSWER_BEARING_CONTENT,),
            True,
            "SemanticObservation refs",
        ),
        (
            "coverage:ag-component-coverage:ledger-custody-only",
            (EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,),
            False,
            "SemanticObservation refs",
        ),
        (
            "coverage:ag-component-coverage:analyst-proposal-only",
            (EvidenceBasis.IDS_OR_DIGESTS_ONLY,),
            False,
            "SemanticObservation refs",
        ),
    ],
)
def test_overclaim_sources_alone_cannot_create_canonical_satisfied_coverage(
    record_id: str,
    basis: tuple[EvidenceBasis, ...],
    content_binding: bool,
    expected_error: str,
) -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    content_ref, _observation = _support_bridge(chain)
    record = _coverage_record(
        kernel=kernel,
        record_id=record_id,
        coverage_state=CoverageState.SATISFIED,
        semantic_support_status=SemanticSupportStatus.UNKNOWN,
        source_obligation_status=SourceObligationStatus.UNSATISFIED,
        content_availability_status=(
            ContentAvailabilityStatus.AVAILABLE if content_binding else ContentAvailabilityStatus.UNKNOWN
        ),
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        evidence_basis=basis,
        content_ref=content_ref if content_binding else None,
        currentness_posture=CurrentnessPosture.UNKNOWN,
    )

    errors = record.validate().errors

    assert any(expected_error in error for error in errors)
    assert any("answer-bearing content" in error for error in errors) or content_binding
    assert any("semantic_observation evidence basis" in error for error in errors)
    with pytest.raises(RunKernelTransitionError, match="at least one admitted SemanticObservation"):
        _reduce_coverage(kernel, record)
    assert kernel.state.component_coverage_state == {}


def test_component_coverage_reliability_report_audits_consumed_unused_and_missing_fields() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    content_ref, observation = _support_bridge(chain)
    support_record = _coverage_record(
        kernel=kernel,
        record_id="coverage:ag-component-coverage:report-supportable",
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        observation=observation,
        content_ref=content_ref,
        remaining_unknowns=("ledger candidate is observed, not accepted final evidence",),
        followup_need=FollowupNeed.OPTIONAL,
        currentness_posture=CurrentnessPosture.CURRENT,
    ).require_valid()
    with pytest.raises(RunKernelTransitionError) as excinfo:
        _reduce_coverage(kernel, support_record)
    _admit_semantic_observation(kernel=kernel, observation=observation, content_ref=content_ref)
    support_projection = _reduce_coverage(kernel, support_record)

    report = component_coverage_reliability_report(
        chain=chain,
        support_projection=support_projection,
        missing_admission_error=str(excinfo.value),
    )

    assert report["artifact"] == REPORT_NAME
    assert report["proof_class"] == "component_harness_proof"
    assert report["component_coverage_consumed_current_chain"] == (
        "only_after_fixture_semantic_observation_admission_bridge"
    )
    assert report["semantic_observation_admission_required"] is True
    assert report["semantic_observation_admission_missing_from_current_packet_chain"] is True
    assert report["current_to_initial_contract_bridge_required"] is True
    assert report["components_evaluated"][0]["coverage_result"] == "supported_with_caveats"
    assert report["components_evaluated"][1]["coverage_result"] == "blocked_passive_only"
    assert "accepted_observation_refs[].observation_id" in report["fields_consumed"]["component_coverage_reducer"]
    assert "EvidenceRelativeAnalysisPacket.analyst_report.findings[].proposal_summary" in (
        report["fields_unused_by_component_coverage"]
    )
    assert "EvidenceRelativeAnalysisPacket finding to SemanticObservation proposal/admission bridge" in (
        report["missing_fields_or_bridges"]
    )
    assert "analysis_gap/followup proposal refs as stable ComponentCoverage blocker lineage" in (
        report["missing_fields_or_bridges"]
    )
    assert "SemanticObservation admission as the next minimal bridge candidate" in report["surfaces_recommended_keep"]
    assert "FollowupSearchIntent proposal as non-authorization" in (
        report["surfaces_recommended_collapse_or_demote"]
    )
    assert report["semantic_observation_admission_bridge_recommended_next"] is True
    assert report["explicit_downstream_non_proofs"] == {
        "final_answer_packet_created": False,
        "author_input_created": False,
        "author_called": False,
        "product_correctness_claimed": False,
        "sufficiency_decided": False,
        "search_authorized_from_followup_intent": False,
    }
    assert json.dumps(report, sort_keys=True)


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    return imported_names, called_names


def test_static_import_and_call_guards_keep_closed_surfaces_closed() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.authoring",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
    }
    forbidden_calls = {
        "run_pipeline",
        "call_broker",
        "invoke_broker",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "fetch_page",
        "read_url",
        "execute_author",
        "execute_author_action",
        "create_final_answer_packet",
        "derive_author_input_payload",
        "ask_model",
    }
    for path in CORE_MODULES:
        imported_names, called_names = _imports_and_calls(path)
        assert imported_names.isdisjoint(forbidden_imports)
        assert called_names.isdisjoint(forbidden_calls)

    imported_names, called_names = _imports_and_calls(THIS_TEST)
    assert "core.pipeline_orchestrator" not in imported_names
    assert called_names.isdisjoint(forbidden_calls)


def test_docs_record_component_coverage_reliability_proof_posture() -> None:
    required = (
        "Current next gate is ComponentCoverage reliability proof",
        "no new standalone proposal packet",
        "SemanticObservation/admission bridge",
        "packet budget rule",
        "A packet is suspect",
        "Broker is local/private validation plumbing",
        "Modes change budget and review depth, not authority",
        "logical depth, loop budget, RunKernel approval, and query fanout",
        "Fast has no Scrutineer in MVP",
        "Balanced uses Scrutineer on red flags",
        "Deep requires Scrutineer",
        "max 3 follow-up loops by default",
        "max 4 only with explicit RunKernel extra recovery authorization",
        "Specialist MVP is deferred",
        "source-bound calculation/economist-style reasoning",
        "AG-96 followup stack",
        "offline SearchExecutor bridge",
        "SearchWorkPlan shadow",
        "legacy/passive/closed",
        REPORT_NAME,
    )
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    for phrase in required:
        assert phrase in docs_text
