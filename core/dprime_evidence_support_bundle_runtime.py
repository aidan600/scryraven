"""D-prime evidence support-bundle runtime.

This runtime consumes admitted D-prime SemanticObservation and existing D-prime
authority lineage. It binds ComponentCoverage, then consumes source-obligation
authority and citation-source handoff authority through RunKernel-owned product
surfaces in the same phase.

It does not create SufficiencyReadiness, FinalAnswerPacket, Author output,
answer text, product correctness, live calls, provider/model calls, search,
fetch/read, or retrieval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_coverage_record import (
    ComponentCoverageRecord,
    ConflictPosture,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageLineage,
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
from core.component_coverage_reduction_runtime import (
    evidence_ledger_projection_digest,
)
from core.dprime_semantic_observation_materialization_runtime import (
    DPrimeSemanticObservationMaterializationResult,
)
from core.dprime_source_obligation_citation_authority_runtime import (
    BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED,
    DPrimeSourceObligationCitationAuthorityError,
    consume_dprime_source_obligation_and_citation_authority,
)
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION
from core.run_kernel import Observation, ObservationType, RunKernel, RunKernelTransitionError, RunStageStatus

DPRIME_EVIDENCE_SUPPORT_BUNDLE_SCHEMA_VERSION = (
    "dprime_evidence_support_bundle_runtime_v1"
)
DPRIME_EVIDENCE_SUPPORT_BUNDLE_SURFACE = (
    "core.dprime_evidence_support_bundle_runtime"
)
DPRIME_EVIDENCE_SUPPORT_BUNDLE_OWNER = "RunKernel.DPrimeEvidenceSupportBundle"

BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING = (
    "BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING"
)
BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING = (
    "BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING"
)
BLOCKED_DPRIME_CITATION_ELIGIBILITY_AUTHORITY_MISSING = (
    "BLOCKED_DPRIME_CITATION_ELIGIBILITY_AUTHORITY_MISSING"
)
BLOCKED_DPRIME_CITATION_SOURCE_HANDOFF_MISSING = (
    "BLOCKED_DPRIME_CITATION_SOURCE_HANDOFF_MISSING"
)


class DPrimeEvidenceSupportBundleError(ValueError):
    """Raised when the support bundle cannot consume existing authority."""

    def __init__(self, blocker: str, detail: str) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DPrimeEvidenceSupportBundleResult:
    """Outcome A support-bundle completion before SufficiencyReadiness."""

    component_coverage_state: Mapping[str, Any]
    component_coverage_projection: Mapping[str, Any]
    source_obligation_authority_ref: Mapping[str, Any]
    citation_eligibility_authority_ref: Mapping[str, Any]
    decision: str
    blocker_detail: str

    @property
    def component_coverage_ref(self) -> dict[str, Any]:
        projection = self.component_coverage_projection
        return {
            "status": "bound",
            "coverage_ref": _id_digest_ref(
                projection.get("coverage_record_id"),
                projection.get("coverage_record_digest"),
            ),
            "coverage_record_id": projection.get("coverage_record_id"),
            "coverage_record_digest": projection.get("coverage_record_digest"),
            "coverage_reduction_digest": projection.get("coverage_reduction_digest"),
            "coverage_state": projection.get("coverage_state"),
            "semantic_support_status": projection.get("semantic_support_status"),
            "source_obligation_status": projection.get("source_obligation_status"),
            "owner": "RunKernel.ComponentCoverageReduction",
            "runtime_surface": DPRIME_EVIDENCE_SUPPORT_BUNDLE_SURFACE,
            "reasons": [
                "bound through existing RunKernel ComponentCoverage authority",
                "coverage is supported_with_caveats, not SufficiencyReadiness",
                "coverage alone is not source-obligation or citation authority",
            ],
        }

    def to_status_overlay(self) -> dict[str, Any]:
        return {
            "component_coverage_status": "bound",
            "component_coverage_ref": self.component_coverage_ref,
            "source_obligation_authority_ref": dict(
                self.source_obligation_authority_ref
            ),
            "citation_eligibility_authority_ref": dict(
                self.citation_eligibility_authority_ref
            ),
            "source_obligation_authority_status": (
                self.source_obligation_authority_ref.get("status")
            ),
            "citation_eligibility_authority_status": (
                self.citation_eligibility_authority_ref.get("status")
            ),
            "source_obligation_authority_consumed": (
                self.source_obligation_authority_ref.get("authority_consumed")
                is True
            ),
            "citation_eligibility_or_source_handoff_authority_consumed": (
                self.citation_eligibility_authority_ref.get("authority_consumed")
                is True
            ),
            "support_bundle_completed": True,
            "component_coverage_only_treated_as_pass": False,
            "detached_posture_status_packet_treated_as_authority": False,
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_answer_created": False,
            "product_correctness_claimed": False,
            "decision": self.decision,
            "blocker_detail": self.blocker_detail,
        }


def build_dprime_evidence_support_bundle(
    *,
    semantic_materialization: DPrimeSemanticObservationMaterializationResult,
    run_kernel: RunKernel,
    source_obligation_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
) -> DPrimeEvidenceSupportBundleResult:
    """Bind D-prime ComponentCoverage, then consume source/citation authority."""

    observation = semantic_materialization.semantic_observation
    accepted_contract = _safe_mapping(run_kernel.state.initial_answer_contract)
    component = _accepted_component(accepted_contract, observation.answer_component_id)
    _require_admitted_observation(run_kernel, observation)
    coverage_record = _component_coverage_record(
        run_kernel=run_kernel,
        accepted_contract=accepted_contract,
        component=component,
        semantic_materialization=semantic_materialization,
        source_obligation_ref=source_obligation_ref,
        citation_source_obligation_readiness_ref=citation_source_obligation_readiness_ref,
    )
    try:
        action = run_kernel.authorize_component_coverage_reduction(
            coverage_record_id=coverage_record.record_id,
            coverage_record_digest=coverage_record.record_digest,
            answer_component_id=str(component["component_id"]),
            component_revision=str(component["component_revision"]),
            component_digest=str(component["component_digest"]),
            inputs={
                "dprime_evidence_support_bundle": (
                    DPRIME_EVIDENCE_SUPPORT_BUNDLE_SURFACE
                ),
                "source_obligation_authority_consumed": False,
                "citation_eligibility_authority_consumed": False,
                "component_coverage_only_treated_as_pass": False,
            },
        )
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
                status=RunStageStatus.COMPLETED,
                payload={
                    "component_coverage_record": _reseal_coverage_record(
                        coverage_record
                    )
                },
            )
        )
    except RunKernelTransitionError as exc:
        raise DPrimeEvidenceSupportBundleError(
            BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING,
            str(exc),
        ) from exc

    try:
        source_citation_authority = (
            consume_dprime_source_obligation_and_citation_authority(
                semantic_materialization=semantic_materialization,
                run_kernel=run_kernel,
                component_coverage_projection=(
                    run_kernel.state.component_coverage_projection
                ),
                source_obligation_ref=source_obligation_ref,
                citation_source_obligation_readiness_ref=(
                    citation_source_obligation_readiness_ref
                ),
            )
        )
    except DPrimeSourceObligationCitationAuthorityError as exc:
        raise DPrimeEvidenceSupportBundleError(exc.blocker, exc.detail) from exc
    return DPrimeEvidenceSupportBundleResult(
        component_coverage_state=dict(run_kernel.state.component_coverage_state),
        component_coverage_projection=dict(
            run_kernel.state.component_coverage_projection
        ),
        source_obligation_authority_ref=(
            source_citation_authority.source_obligation_authority_ref
        ),
        citation_eligibility_authority_ref=(
            source_citation_authority.citation_eligibility_authority_ref
        ),
        decision=source_citation_authority.decision,
        blocker_detail=source_citation_authority.blocker_detail,
    )


def _component_coverage_record(
    *,
    run_kernel: RunKernel,
    accepted_contract: Mapping[str, Any],
    component: Mapping[str, Any],
    semantic_materialization: DPrimeSemanticObservationMaterializationResult,
    source_obligation_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
) -> ComponentCoverageRecord:
    observation = semantic_materialization.semantic_observation
    content_ref = semantic_materialization.sanitized_content_reference
    observation_ref = SemanticObservationCoverageRef.from_observation(
        observation.to_dict()
    )
    content_binding = ContentReferenceCoverageBinding.from_content_reference(
        content_ref.to_dict()
    )
    observation_digest = observation.observation_digest
    record_id = f"component-coverage:dprime:{observation_digest[:16]}"
    return ComponentCoverageRecord(
        record_id=record_id,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        request_digest=_digest_json(
            {
                "run_id": run_kernel.state.run_id,
                "request_id": run_kernel.state.request_id,
                "surface": DPRIME_EVIDENCE_SUPPORT_BUNDLE_SURFACE,
            }
        ),
        accepted_contract_version=str(accepted_contract["accepted_contract_version"]),
        accepted_contract_digest=str(accepted_contract["accepted_contract_digest"]),
        answer_component_id=str(component["component_id"]),
        component_revision=str(component["component_revision"]),
        component_digest=str(component["component_digest"]),
        evidence_ledger_binding=_ledger_binding(
            run_kernel,
            source_requirement_ids=(),
        ),
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=SourceObligationStatus.UNKNOWN,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(observation_ref,),
        content_reference_bindings=(content_binding,),
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        conflict_posture=ConflictPosture.NONE,
        currentness_posture=CurrentnessPosture.CURRENT,
        remaining_unknowns=(
            "source_obligation_authority_missing",
            "citation_eligibility_authority_missing",
        ),
        required_caveats=(
            "ComponentCoverage is bound from admitted D-prime SemanticObservation only.",
            "ComponentCoverage alone is not source-obligation authority.",
            "ComponentCoverage alone is not citation-source handoff authority.",
        ),
        prohibited_upgrades=(
            "Do not treat ComponentCoverage as SufficiencyReadiness.",
            "Do not treat source-obligation lineage as satisfaction authority.",
            "Do not treat readiness posture as citation eligibility authority.",
        ),
        followup_need=FollowupNeed.BLOCKED,
        mode_budget_posture=ModeBudgetPosture.BLOCKED,
        stale=False,
        lineage=CoverageLineage(
            created_by=DPRIME_EVIDENCE_SUPPORT_BUNDLE_OWNER,
            created_from=(
                "admitted_dprime_semantic_observation",
                "run_kernel_component_coverage_reduction",
                "lineage_only_source_obligation_ref",
            ),
        ),
        metadata={
            "runtime_surface": DPRIME_EVIDENCE_SUPPORT_BUNDLE_SURFACE,
            "citation_source_obligation_readiness_posture": (
                citation_source_obligation_readiness_ref.get("posture")
            ),
            "source_obligation_authority_consumed": False,
            "citation_eligibility_authority_consumed": False,
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_answer_created": False,
            "product_correctness_claimed": False,
        },
    ).require_valid(
        observations=(observation.to_dict(),),
        content_references=(content_ref.to_dict(),),
    )


def _ledger_binding(
    run_kernel: RunKernel,
    *,
    source_requirement_ids: Sequence[str],
) -> EvidenceLedgerSnapshotBinding:
    projection = run_kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        str(ref["observation_id"])
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, Mapping) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{run_kernel.state.run_id}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        source_requirement_ids=tuple(source_requirement_ids),
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _require_admitted_observation(
    run_kernel: RunKernel,
    observation: Any,
) -> None:
    for item in run_kernel.state.semantic_observation_admission_history:
        admission = _safe_mapping(item)
        if (
            admission.get("observation_id") == observation.observation_id
            and admission.get("observation_digest") == observation.observation_digest
        ):
            return
    raise DPrimeEvidenceSupportBundleError(
        BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING,
        "D-prime ComponentCoverage requires an admitted SemanticObservation",
    )


def _accepted_component(
    accepted_contract: Mapping[str, Any],
    component_id: str,
) -> Mapping[str, Any]:
    for item in accepted_contract.get("accepted_answer_component_refs") or ():
        component = _safe_mapping(item)
        if component.get("component_id") == component_id:
            return component
    raise DPrimeEvidenceSupportBundleError(
        BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING,
        "accepted contract lacks D-prime component binding",
    )


def _missing_source_obligation_authority_ref(
    source_obligation_ref: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "missing",
        "blocker": BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING,
        "source_obligation_candidate_ids": list(
            _text_tuple(source_obligation_ref.get("source_obligation_candidate_ids"))
        ),
        "retained_ids_are_lineage_only": True,
        "satisfaction_claimed": False,
        "authority_consumed": False,
        "reasons": [
            "retained source-obligation ids are lineage only",
            "no pre-Sufficiency/FAP RunKernel source-obligation authority was found",
        ],
    }


def _missing_citation_eligibility_authority_ref() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "blocker": BLOCKED_DPRIME_CITATION_ELIGIBILITY_AUTHORITY_MISSING,
        "authority_consumed": False,
        "citation_rendering_created": False,
        "author_answer_created": False,
        "reasons": [
            "citation eligibility authority is downstream of closed Sufficiency/FAP surfaces",
            "D-prime support bundle cannot create citation eligibility authority",
        ],
    }


def _reseal_coverage_record(record: ComponentCoverageRecord) -> dict[str, Any]:
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    return payload


def _id_digest_ref(identifier: Any, digest: Any) -> str:
    clean_id = _clean_text(identifier, limit=320)
    clean_digest = _clean_text(digest, limit=128)
    if clean_id and clean_digest:
        return f"{clean_id} / {clean_digest}"
    return clean_id or clean_digest or "unavailable"


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _digest_json(value: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "BLOCKED_DPRIME_CITATION_ELIGIBILITY_AUTHORITY_MISSING",
    "BLOCKED_DPRIME_CITATION_SOURCE_HANDOFF_MISSING",
    "BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING",
    "BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING",
    "BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED",
    "DPRIME_EVIDENCE_SUPPORT_BUNDLE_OWNER",
    "DPRIME_EVIDENCE_SUPPORT_BUNDLE_SCHEMA_VERSION",
    "DPRIME_EVIDENCE_SUPPORT_BUNDLE_SURFACE",
    "DPrimeEvidenceSupportBundleError",
    "DPrimeEvidenceSupportBundleResult",
    "build_dprime_evidence_support_bundle",
]
