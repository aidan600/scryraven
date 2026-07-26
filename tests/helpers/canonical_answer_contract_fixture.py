from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.contract_amendment_record import (
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    UserConfirmationPosture,
    WeakeningPosture,
)
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.followup_search_authorization_loop import (
    FollowupSearchReentryResult,
    authorize_followup_search_work,
    build_fixture_fetch_read_content_packet,
    build_fixture_search_result_candidate_packet,
    build_followup_reentry_analysis_packet,
    reduce_component_coverage_from_admitted_followup_support,
    unresolved_component_posture_from_analysis_packet,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.semantic_observation_admission_bridge import (
    admit_semantic_observations_from_analysis_support_findings,
)


def apply_nonmaterial_current_contract_fixture(
    kernel: RunKernel,
    *,
    fixture_id: str,
) -> ContractAmendmentRecord:
    """Create current contract authority without retired Scout/revision lineage."""

    accepted = kernel.state.current_answer_contract or kernel.state.initial_answer_contract
    if not accepted:
        raise ValueError("current-contract fixture requires an accepted answer contract")
    qmr_digest = str(accepted["parent_question_meaning_record_digest"])
    record = ContractAmendmentRecord(
        amendment_record_id=f"amendment:{fixture_id}:normalization",
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        request_digest=qmr_digest,
        parent_contract_version=str(accepted["accepted_contract_version"]),
        parent_contract_digest=str(accepted["accepted_contract_digest"]),
        parent_question_meaning_record_id=str(accepted["parent_question_meaning_record_id"]),
        parent_question_meaning_record_digest=qmr_digest,
        accepted_contract_ref=(f"contract:{accepted['accepted_contract_version']}:accepted"),
        trigger_refs=AmendmentTriggerRefs(
            gap_refs=(f"fixture-gap:{fixture_id}:current-contract-required",),
        ),
        operations=(
            AmendmentOperation(
                operation_id=f"operation:{fixture_id}:add-normalization",
                operation_kind=AmendmentOperationKind.ADD_NORMALIZATION,
                operation_payload={"normalization": ("Preserve the accepted fixture meaning and component authority.")},
            ),
        ),
        materiality=MaterialityPosture.NON_MATERIAL,
        user_confirmation_posture=UserConfirmationPosture.NOT_REQUIRED,
        monotonicity=MonotonicityPosture.PRESERVES,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        metadata={
            "fixture_only": True,
            "purpose": "canonical_current_contract_without_retired_revision_lineage",
        },
    ).require_valid()

    admission_action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )
    kernel.reduce(
        Observation.from_action(
            admission_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={"contract_amendment_record": record.to_dict()},
        )
    )
    admission = kernel.state.contract_amendment_admission_projection
    application_action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(admission["admission_digest"]),
    )
    kernel.reduce(
        Observation.from_action(
            application_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    return record


def run_split_followup_reentry_fixture(
    *,
    authorization_run_kernel: RunKernel,
    semantic_run_kernel: RunKernel,
    followup_search_intent_packet: Mapping[str, Any],
    fixture_candidates: Sequence[Mapping[str, Any]],
    fixture_fetch_read_materials: Sequence[Mapping[str, Any]],
    mode: str,
    analyst_repass_outcome: str,
) -> FollowupSearchReentryResult:
    """Keep current-contract authorization separate from initial semantic custody."""

    authorization = authorize_followup_search_work(
        run_kernel=authorization_run_kernel,
        followup_search_intent_packet=followup_search_intent_packet,
        mode=mode,
    )
    candidate_packet = build_fixture_search_result_candidate_packet(
        authorization_result=authorization,
        fixture_candidates=fixture_candidates,
    )
    fetch_read_packet = build_fixture_fetch_read_content_packet(
        candidate_packet=candidate_packet,
        fixture_fetch_read_materials=fixture_fetch_read_materials,
    )
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=semantic_run_kernel,
        fetch_read_content_packet=fetch_read_packet,
    )
    analysis_packet = build_followup_reentry_analysis_packet(
        ledger_projection=ledger_projection,
        analyst_repass_outcome=analyst_repass_outcome,
        followup_handoff_digest=authorization.authorized_work_identity.get("handoff_digest"),
    )
    semantic_results = ()
    coverage_projection: Mapping[str, Any] = {}
    unresolved_posture: Mapping[str, Any] = {}
    if any(
        finding.get("proposal_kind") == "possible_support_proposal"
        for finding in analysis_packet["analyst_report"].get("findings", ())
    ):
        semantic_results = admit_semantic_observations_from_analysis_support_findings(
            run_kernel=semantic_run_kernel,
            evidence_relative_analysis_packet=analysis_packet,
            fetch_read_content_packet=fetch_read_packet,
        )
        coverage_projection = reduce_component_coverage_from_admitted_followup_support(
            run_kernel=semantic_run_kernel,
            admission_result=semantic_results[0],
        )
    else:
        unresolved_posture = unresolved_component_posture_from_analysis_packet(analysis_packet)
    return FollowupSearchReentryResult(
        authorization_result=authorization,
        candidate_packet=candidate_packet,
        fetch_read_packet=fetch_read_packet,
        ledger_projection=ledger_projection,
        analysis_packet=analysis_packet,
        semantic_admission_results=semantic_results,
        coverage_projection=coverage_projection,
        unresolved_component_posture=unresolved_posture,
    )
