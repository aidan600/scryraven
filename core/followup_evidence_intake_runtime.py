"""Offline follow-up EvidenceLedger intake seam for AG-96I2C/AG-96I3A.

This module bridges canonical fixture or offline provider-job execution state
into a sanitized EvidenceLedger observation. It never calls providers, search,
retrieval, fetch/read, prompts, models, citation formatters, provider-job
executors, shell processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.evidence_ledger import EvidenceLedgerObservation
from core.evidence_ledger_intake_adapter import (
    build_evidence_ledger_intake_observation_from_admission_review,
)
from core.followup_deliberation import (
    ProviderJobKind,
    clean_text,
    clean_token,
    safe_json,
)
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    FollowupExecutionStatus,
)
from core.followup_fixture_boundaries import (
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    followup_common_redaction_posture,
    followup_fixture_provenance,
    followup_live_surface_flags,
)
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND,
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
    FollowupProviderJobExecutionStatus,
)
from core.followup_runkernel_reducers import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    FollowupRunKernelReducerError,
    ag96i3m2_admission_review_authorization_projection,
    ag96i3m2_intake_binding_authorization_projection,
    ag96i3m2_validate_authorized_intake_materials,
)
from core.run_kernel import (
    FOLLOWUP_EVIDENCE_INTAKE_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)

FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION = "followup_evidence_intake_ag96i2c_v1"
FOLLOWUP_EVIDENCE_INTAKE_TRACE_KEY = "followup_evidence_intake_runtime"
FOLLOWUP_EVIDENCE_INTAKE_MODE = "fixture_only_followup_intake"
FOLLOWUP_PROVIDER_JOB_EVIDENCE_INTAKE_MODE = (
    "bounded_provider_job_offline_followup_intake"
)
FOLLOWUP_EVIDENCE_INTAKE_GATE_REASON = "ag96i2c_fixture_only_evidence_ledger_intake"


class FollowupEvidenceIntakeStatus(str, Enum):
    FIXTURE_INTAKE_ADMITTED = "fixture_intake_admitted"
    FIXTURE_BRIDGE_ONLY_RECORDED = "fixture_bridge_only_recorded"
    FIXTURE_NO_ADMISSION_RECORDED = "fixture_no_admission_recorded"
    PROVIDER_JOB_INTAKE_ADMITTED = "provider_job_intake_admitted"
    PROVIDER_JOB_BRIDGE_ONLY_RECORDED = "provider_job_bridge_only_recorded"
    PROVIDER_JOB_NO_ADMISSION_RECORDED = "provider_job_no_admission_recorded"
    ADMISSION_REVIEW_INTAKE_ADMITTED = "admission_review_intake_admitted"


@dataclass(frozen=True, slots=True)
class FollowupEvidenceIntakeRequest:
    request_id: str
    run_id: str
    checkpoint_id: str
    followup_authorization_consumption_id: str
    sealed_candidate_id: str
    followup_execution_id: str
    execution_id: str
    followup_execution_observation_id: str
    observation_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    result_status: str
    bridge_only: bool
    expected_source_classes: tuple[str, ...]
    expected_evidence_ledger_custody_update: Mapping[str, Any]
    sanitized_fixture_result_summary: Mapping[str, Any]
    sanitized_candidate_summary: Mapping[str, Any]
    execution_mode: str
    authorized_query_ref: str | None
    authorized_query: str | None
    provider_execution_licensed: bool
    evidence_ledger_intake_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION,
            "record_type": "followup_evidence_intake_request",
            "request_id": clean_token(self.request_id),
            "run_id": clean_token(self.run_id),
            "checkpoint_id": clean_token(self.checkpoint_id),
            "followup_authorization_consumption_id": clean_text(
                self.followup_authorization_consumption_id,
                limit=220,
            ),
            "sealed_candidate_id": clean_token(self.sealed_candidate_id),
            "followup_execution_id": clean_text(
                self.followup_execution_id,
                limit=220,
            ),
            "execution_id": clean_text(self.execution_id, limit=220),
            "followup_execution_observation_id": clean_text(
                self.followup_execution_observation_id,
                limit=220,
            ),
            "observation_id": clean_text(self.observation_id, limit=220),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [
                clean_token(item) for item in self.requirement_ids if clean_token(item)
            ],
            "result_status": clean_token(self.result_status),
            "bridge_only": bool(self.bridge_only),
            "expected_source_classes": [
                clean_token(item)
                for item in self.expected_source_classes
                if clean_token(item)
            ],
            "expected_evidence_ledger_custody_update": safe_json(
                self.expected_evidence_ledger_custody_update
            ),
            "sanitized_fixture_result_summary": safe_json(
                self.sanitized_fixture_result_summary
            ),
            "sanitized_candidate_summary": safe_json(self.sanitized_candidate_summary),
            "execution_mode": clean_token(self.execution_mode),
            "authorized_query_ref": clean_token(self.authorized_query_ref, limit=180),
            "authorized_query": clean_text(self.authorized_query, limit=300),
            "fixture_only_provenance": _fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupEvidenceIntakeResult:
    result_id: str
    status: FollowupEvidenceIntakeStatus
    ledger_observation: Mapping[str, Any]
    evidence_ledger_candidate_admitted: bool
    source_obligation_satisfied: bool
    bridge_only: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION,
            "record_type": "followup_evidence_intake_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": self.status.value,
            "ledger_observation": safe_json(self.ledger_observation),
            "evidence_ledger_candidate_admitted": bool(
                self.evidence_ledger_candidate_admitted
            ),
            "source_obligation_satisfied": bool(self.source_obligation_satisfied),
            "bridge_only": bool(self.bridge_only),
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "sufficiency_judgment_recheck_deferred": True,
        }


@dataclass(frozen=True, slots=True)
class FollowupEvidenceIntakeObservation:
    observation_id: str
    request: FollowupEvidenceIntakeRequest
    result: FollowupEvidenceIntakeResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        ledger_observation = _ledger_observation_from_request(
            self.request,
            ledger_projection={},
        ).to_dict()
        return {
            "schema_version": FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_EVIDENCE_INTAKE_TRACE_KEY,
            "record_type": "followup_evidence_intake_observation",
            "owner": "FollowupEvidenceIntakeRuntime",
            "canonical_state": False,
            "trace_only": False,
            "storage_only": False,
            "observation_id": clean_text(self.observation_id, limit=220),
            "run_id": request.get("run_id"),
            "checkpoint_id": request.get("checkpoint_id"),
            "followup_authorization_consumption_id": request.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": request.get("sealed_candidate_id"),
            "followup_execution_id": request.get("followup_execution_id"),
            "execution_id": request.get("execution_id"),
            "followup_execution_observation_id": request.get(
                "followup_execution_observation_id"
            ),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "result_status": request.get("result_status"),
            "fixture_execution_mode": (
                FIXTURE_EXECUTION_MODE
                if request.get("execution_mode") == FIXTURE_EXECUTION_MODE
                else None
            ),
            "execution_mode": request.get("execution_mode"),
            "authorized_query_ref": request.get("authorized_query_ref"),
            "authorized_query": request.get("authorized_query"),
            "bridge_only": request.get("bridge_only"),
            "expected_source_classes": request.get("expected_source_classes", []),
            "expected_evidence_ledger_custody_update": request.get(
                "expected_evidence_ledger_custody_update",
                {},
            ),
            "sanitized_fixture_result_summary": request.get(
                "sanitized_fixture_result_summary",
                {},
            ),
            "sanitized_candidate_summary": request.get(
                "sanitized_candidate_summary",
                {},
            ),
            "fixture_only_provenance": request.get("fixture_only_provenance", {}),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "request": request,
            "result": result,
            "intake_status": result.get("status"),
            "ledger_observation": ledger_observation,
            "ledger_requirements": ledger_observation.get("requirements", []),
            "ledger_candidates": ledger_observation.get("candidates", []),
            "ledger_requirement_links": ledger_observation.get(
                "requirement_links",
                [],
            ),
            "ledger_followup_fixture_intake": ledger_observation.get(
                "followup_fixture_intake",
                {},
            ),
            "evidence_ledger_candidate_admitted": result.get(
                "evidence_ledger_candidate_admitted"
            ),
            "source_obligation_satisfied": result.get(
                "source_obligation_satisfied"
            ),
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "sufficiency_judgment_recheck_deferred": True,
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class AG96I3M2FollowupEvidenceIntakeObservation:
    observation_id: str
    request: FollowupEvidenceIntakeRequest
    admission_review_candidate: Mapping[str, Any]
    evidence_ledger_intake_binding: Mapping[str, Any]
    adapter_projection: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        candidate_payload = _ag96i3m2_candidate_payload(
            self.admission_review_candidate
        )
        binding_payload = _mapping(safe_json(self.evidence_ledger_intake_binding))
        candidate_projection = ag96i3m2_admission_review_authorization_projection(
            candidate_payload
        )
        binding_projection = ag96i3m2_intake_binding_authorization_projection(
            binding_payload
        )
        adapter_projection = _mapping(safe_json(self.adapter_projection))
        return {
            "schema_version": FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_EVIDENCE_INTAKE_TRACE_KEY,
            "record_type": "followup_evidence_intake_observation",
            "owner": "FollowupEvidenceIntakeRuntime",
            "canonical_state": False,
            "trace_only": False,
            "storage_only": False,
            "observation_id": clean_text(self.observation_id, limit=220),
            "run_id": request.get("run_id"),
            "checkpoint_id": request.get("checkpoint_id"),
            "followup_authorization_consumption_id": request.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": request.get("sealed_candidate_id"),
            "followup_execution_id": request.get("followup_execution_id"),
            "execution_id": request.get("execution_id"),
            "followup_execution_observation_id": request.get(
                "followup_execution_observation_id"
            ),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "result_status": request.get("result_status"),
            "fixture_execution_mode": (
                FIXTURE_EXECUTION_MODE
                if request.get("execution_mode") == FIXTURE_EXECUTION_MODE
                else None
            ),
            "execution_mode": request.get("execution_mode"),
            "authorized_query_ref": request.get("authorized_query_ref"),
            "authorized_query": request.get("authorized_query"),
            "bridge_only": request.get("bridge_only"),
            "expected_source_classes": request.get("expected_source_classes", []),
            "expected_evidence_ledger_custody_update": request.get(
                "expected_evidence_ledger_custody_update",
                {},
            ),
            "provider_execution_licensed": False,
            "evidence_ledger_intake_mode": AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
            "request": request,
            "intake_status": (
                FollowupEvidenceIntakeStatus.ADMISSION_REVIEW_INTAKE_ADMITTED.value
            ),
            "evidence_ledger_candidate_admitted": True,
            "source_obligation_satisfied": True,
            "runtime_evidence_intake_occurred": True,
            "ag96i3m2_admission_review_candidate": candidate_projection,
            "ag96i3m2_admission_review_candidate_payload": candidate_payload,
            "ag96i3m2_evidence_ledger_intake_binding": binding_projection,
            "ag96i3m2_evidence_ledger_intake_binding_payload": binding_payload,
            "ag96i3m1_adapter_projection": {
                **adapter_projection,
                "accepted": True,
            },
            "adapter_call_path": (
                "core.followup_evidence_intake_runtime."
                "build_followup_evidence_intake_record -> "
                "core.evidence_ledger_intake_adapter."
                "build_evidence_ledger_intake_observation_from_admission_review"
            ),
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "author_activation_allowed": False,
            "sufficiency_judgment_recheck_deferred": True,
            "sufficiency_judgment_rechecked": False,
            "final_answer_packet_updated": False,
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _ag96i3m2_redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupEvidenceIntakeConsumptionRecord:
    intake_id: str
    observation: FollowupEvidenceIntakeObservation | AG96I3M2FollowupEvidenceIntakeObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_evidence_intake_consumption_record",
            "owner": "RunKernel.FollowupEvidenceIntake",
            "canonical_state": True,
            "intake_id": clean_text(self.intake_id, limit=220),
        }


@dataclass(frozen=True, slots=True)
class FollowupEvidenceIntakeActionResult:
    record: FollowupEvidenceIntakeConsumptionRecord
    observation: Observation


def execute_followup_evidence_intake_action(
    action: AuthorizedAction,
    *,
    followup_execution_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    admission_review_candidate: Mapping[str, Any] | None = None,
    evidence_ledger_intake_binding: Mapping[str, Any] | None = None,
) -> FollowupEvidenceIntakeActionResult:
    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_EVIDENCE_INTAKE,
        stage=FOLLOWUP_EVIDENCE_INTAKE_STAGE,
        expected_observation_type=ObservationType.FOLLOWUP_EVIDENCE_INTAKE_OBSERVED,
    )
    record = build_followup_evidence_intake_record(
        authorized,
        followup_execution_state=followup_execution_state,
        evidence_ledger_projection=evidence_ledger_projection,
        admission_review_candidate=admission_review_candidate,
        evidence_ledger_intake_binding=evidence_ledger_intake_binding,
    )
    return FollowupEvidenceIntakeActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_EVIDENCE_INTAKE_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_evidence_intake_state": record.to_dict()},
        ),
    )


def build_followup_evidence_intake_record(
    action: AuthorizedAction,
    *,
    followup_execution_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    admission_review_candidate: Mapping[str, Any] | None = None,
    evidence_ledger_intake_binding: Mapping[str, Any] | None = None,
) -> FollowupEvidenceIntakeConsumptionRecord:
    state = _mapping(safe_json(followup_execution_state))
    ledger_projection = _mapping(safe_json(evidence_ledger_projection))
    _validate_execution_state(state)
    _validate_action_inputs(action.inputs, state)
    if action.inputs.get("evidence_ledger_intake_mode") == (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        return _build_ag96i3m2_evidence_intake_record(
            action,
            followup_execution_state=state,
            admission_review_candidate=admission_review_candidate,
            evidence_ledger_intake_binding=evidence_ledger_intake_binding,
        )
    if admission_review_candidate is not None or evidence_ledger_intake_binding is not None:
        raise PermissionError(
            "AG-96I3L admission-review intake material requires AG-96I3M2 mode"
        )

    request = FollowupEvidenceIntakeRequest(
        request_id=f"followup-evidence-intake-request:{state.get('execution_id')}",
        run_id=str(state.get("run_id") or ""),
        checkpoint_id=str(state.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(
            state.get("followup_authorization_consumption_id") or ""
        ),
        sealed_candidate_id=str(state.get("sealed_candidate_id") or ""),
        followup_execution_id=str(state.get("execution_id") or ""),
        execution_id=str(state.get("execution_id") or ""),
        followup_execution_observation_id=str(state.get("observation_id") or ""),
        observation_id=str(state.get("observation_id") or ""),
        provider_job_kind=str(state.get("provider_job_kind") or ""),
        component_id=str(state.get("component_id") or ""),
        source_obligation_id=str(state.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(state.get("requirement_ids"))),
        result_status=str(state.get("result_status") or ""),
        bridge_only=bool(state.get("bridge_only")),
        expected_source_classes=tuple(_strings(state.get("expected_source_classes"))),
        expected_evidence_ledger_custody_update=_mapping(
            state.get("expected_evidence_ledger_custody_update")
        ),
        sanitized_fixture_result_summary=_mapping(
            state.get("sanitized_fixture_result_summary")
        ),
        sanitized_candidate_summary=_mapping(
            state.get("sanitized_candidate_summary")
        ),
        execution_mode=str(
            state.get("execution_mode")
            or state.get("fixture_execution_mode")
            or FIXTURE_EXECUTION_MODE
        ),
        authorized_query_ref=clean_token(
            state.get("authorized_query_ref"),
            limit=180,
        ),
        authorized_query=clean_text(state.get("authorized_query"), limit=300),
        provider_execution_licensed=False,
        evidence_ledger_intake_mode=_intake_mode_for_execution_state(state),
    )
    ledger_observation = _ledger_observation_from_request(
        request,
        ledger_projection=ledger_projection,
    )
    result = FollowupEvidenceIntakeResult(
        result_id=f"followup-evidence-intake-result:{request.execution_id}",
        status=_intake_status(request),
        ledger_observation=ledger_observation.to_dict(),
        evidence_ledger_candidate_admitted=_candidate_admitted(request),
        source_obligation_satisfied=_source_obligation_satisfied(request),
        bridge_only=request.bridge_only,
    )
    observation = FollowupEvidenceIntakeObservation(
        observation_id=(
            "followup-evidence-intake-observation:"
            f"{request.execution_id}"
        ),
        request=request,
        result=result,
    )
    return FollowupEvidenceIntakeConsumptionRecord(
        intake_id=f"followup-evidence-intake:{request.execution_id}",
        observation=observation,
    )


def _build_ag96i3m2_evidence_intake_record(
    action: AuthorizedAction,
    *,
    followup_execution_state: Mapping[str, Any],
    admission_review_candidate: Mapping[str, Any] | None,
    evidence_ledger_intake_binding: Mapping[str, Any] | None,
) -> FollowupEvidenceIntakeConsumptionRecord:
    if admission_review_candidate is None:
        raise PermissionError("AG-96I3M2 intake requires admission-review candidate")
    if evidence_ledger_intake_binding is None:
        raise PermissionError("AG-96I3M2 intake requires EvidenceLedgerIntakeBinding")
    try:
        ag96i3m2_validate_authorized_intake_materials(
            action_inputs=action.inputs,
            admission_review_candidate=admission_review_candidate,
            binding=evidence_ledger_intake_binding,
        )
    except FollowupRunKernelReducerError as exc:
        raise PermissionError(str(exc)) from exc

    adapter_result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=admission_review_candidate,
        binding=evidence_ledger_intake_binding,
    )
    if not adapter_result.accepted or adapter_result.observation is None:
        blockers = [blocker.value for blocker in adapter_result.blocker_codes]
        raise PermissionError(
            "AG-96I3M2 EvidenceLedger intake adapter rejected candidate: "
            + ", ".join(blockers)
        )

    state = followup_execution_state
    request = FollowupEvidenceIntakeRequest(
        request_id=f"followup-evidence-intake-request:{state.get('execution_id')}",
        run_id=str(state.get("run_id") or ""),
        checkpoint_id=str(state.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(
            state.get("followup_authorization_consumption_id") or ""
        ),
        sealed_candidate_id=str(state.get("sealed_candidate_id") or ""),
        followup_execution_id=str(state.get("execution_id") or ""),
        execution_id=str(state.get("execution_id") or ""),
        followup_execution_observation_id=str(state.get("observation_id") or ""),
        observation_id=str(state.get("observation_id") or ""),
        provider_job_kind=str(state.get("provider_job_kind") or ""),
        component_id=str(state.get("component_id") or ""),
        source_obligation_id=str(state.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(state.get("requirement_ids"))),
        result_status=str(state.get("result_status") or ""),
        bridge_only=bool(state.get("bridge_only")),
        expected_source_classes=tuple(_strings(state.get("expected_source_classes"))),
        expected_evidence_ledger_custody_update=_mapping(
            state.get("expected_evidence_ledger_custody_update")
        ),
        sanitized_fixture_result_summary=_mapping(
            state.get("sanitized_fixture_result_summary")
        ),
        sanitized_candidate_summary=_mapping(state.get("sanitized_candidate_summary")),
        execution_mode=str(
            state.get("execution_mode")
            or state.get("fixture_execution_mode")
            or FIXTURE_EXECUTION_MODE
        ),
        authorized_query_ref=clean_token(
            state.get("authorized_query_ref"),
            limit=180,
        ),
        authorized_query=clean_text(state.get("authorized_query"), limit=300),
        provider_execution_licensed=False,
        evidence_ledger_intake_mode=AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    )
    observation = AG96I3M2FollowupEvidenceIntakeObservation(
        observation_id=(
            "followup-evidence-intake-observation:"
            f"{request.execution_id}:ag96i3m2"
        ),
        request=request,
        admission_review_candidate=admission_review_candidate,
        evidence_ledger_intake_binding=evidence_ledger_intake_binding,
        adapter_projection=adapter_result.projection,
    )
    return FollowupEvidenceIntakeConsumptionRecord(
        intake_id=f"followup-evidence-intake:{request.execution_id}:ag96i3m2",
        observation=observation,
    )


def _validate_execution_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError("follow-up evidence intake requires canonical execution state")
    execution_mode = _execution_mode(state)
    if state.get("owner") not in {
        "RunKernel.FollowupFixtureExecution",
        "RunKernel.FollowupProviderJobExecution",
    }:
        raise PermissionError("follow-up evidence intake requires RunKernel execution state")
    if execution_mode not in {
        FIXTURE_EXECUTION_MODE,
        FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
    }:
        raise PermissionError("follow-up evidence intake requires known execution mode")
    if execution_mode == FIXTURE_EXECUTION_MODE and (
        state.get("fixture_execution_mode") != FIXTURE_EXECUTION_MODE
    ):
        raise PermissionError("follow-up evidence intake requires fixture_only execution")
    if execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        if state.get("provider_job_kind") != FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND:
            raise PermissionError("offline provider-job intake requires official/current kind")
        if not (
            clean_token(state.get("authorized_query_ref"), limit=180)
            or clean_text(state.get("authorized_query"), limit=300)
        ):
            raise PermissionError("offline provider-job intake requires authorized query/ref")
    gate = _mapping(state.get("execution_gate"))
    if gate.get("allowed_execution_mode") != execution_mode:
        raise PermissionError("follow-up evidence intake requires matching execution gate")
    if gate.get("provider_execution_licensed") is not False:
        raise PermissionError("provider execution is not licensed for intake")
    if state.get("evidence_ledger_intake_deferred") is not True:
        raise PermissionError("follow-up execution state must defer EvidenceLedger intake")
    if state.get("evidence_ledger_evidence_admitted") is not False:
        raise PermissionError("follow-up execution state must not have admitted evidence")
    try:
        ProviderJobKind(state.get("provider_job_kind"))
    except ValueError:
        raise PermissionError("unknown follow-up provider job kind")
    allowed_statuses = {item.value for item in FollowupExecutionStatus}
    if execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        allowed_statuses = {item.value for item in FollowupProviderJobExecutionStatus}
    if state.get("result_status") not in allowed_statuses:
        raise PermissionError("unknown follow-up fixture result status")
    flags = _mapping(state.get("behavior_boundary_flags"))
    for flag in (
        "live_provider_call_executed",
        "provider_job_scheduled",
        "provider_job_dispatched",
        "search_executed",
        "retrieval_executed",
        "fetch_executed",
        "model_called",
        "query_generation_changed",
        "retrieval_ranking_filtering_changed",
        "evidence_ledger_mutated",
        "sufficiency_judgment_rechecked",
        "final_answer_behavior_changed",
        "author_prose_behavior_changed",
        "pipeline_orchestrator_domain_logic_changed",
    ):
        if flags.get(flag) is not False:
            raise PermissionError(f"follow-up execution state requires {flag}=False")
    if execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        if state.get("offline_live_shaped_execution") is not True:
            raise PermissionError("offline provider-job execution state requires offline flag")
        if state.get("adapter_result_injected") is not True:
            raise PermissionError("offline provider-job execution state requires injected result")
        if state.get("live_validation_not_run") is not True:
            raise PermissionError("offline provider-job execution must not run live validation")


def _validate_action_inputs(
    action_inputs: Mapping[str, Any],
    state: Mapping[str, Any],
) -> None:
    execution_mode = _execution_mode(state)
    binding_fields = [
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
    ]
    if execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        binding_fields.extend(
            [
                "execution_mode",
                "authorized_query_ref",
                "authorized_query",
            ]
        )
    else:
        binding_fields.append("fixture_execution_mode")
    for binding_field in binding_fields:
        if action_inputs.get(binding_field) != state.get(binding_field):
            raise PermissionError(f"authorized intake action {binding_field} mismatch")
    for action_field, state_field in (
        ("followup_execution_id", "execution_id"),
        ("execution_id", "execution_id"),
        ("followup_execution_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != state.get(state_field):
            raise PermissionError(f"authorized intake action {action_field} mismatch")
    if action_inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("authorized intake action must keep provider unlicensed")
    intake_mode = action_inputs.get("evidence_ledger_intake_mode")
    if intake_mode == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE:
        if not action_inputs.get("ag96i3m2_admission_review_candidate"):
            raise PermissionError("AG-96I3M2 intake requires authorized candidate")
        if not action_inputs.get("ag96i3m2_evidence_ledger_intake_binding"):
            raise PermissionError("AG-96I3M2 intake requires authorized binding")
    elif intake_mode != _intake_mode_for_execution_state(state):
        raise PermissionError("authorized intake action mode mismatch")


def _ledger_observation_from_request(
    request: FollowupEvidenceIntakeRequest,
    *,
    ledger_projection: Mapping[str, Any],
) -> EvidenceLedgerObservation:
    provider_job_offline = (
        request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    )
    summary = _mapping(
        request.sanitized_candidate_summary
        if provider_job_offline
        else request.sanitized_fixture_result_summary
    )
    requirement = _source_requirement(request, summary)
    candidate = _candidate_record(request, summary)
    observation_source = (
        "followup_provider_job_offline_evidence_intake"
        if provider_job_offline
        else "followup_fixture_evidence_intake"
    )
    metadata_key = (
        "followup_provider_job_intake"
        if provider_job_offline
        else "followup_fixture_intake"
    )
    metadata = {
        "schema_version": FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION,
        "run_id": request.run_id,
        "checkpoint_id": request.checkpoint_id,
        "followup_authorization_consumption_id": (
            request.followup_authorization_consumption_id
        ),
        "sealed_candidate_id": request.sealed_candidate_id,
        "followup_execution_id": request.followup_execution_id,
        "followup_execution_observation_id": (
            request.followup_execution_observation_id
        ),
        "provider_job_kind": request.provider_job_kind,
        "component_id": request.component_id,
        "source_obligation_id": request.source_obligation_id,
        "requirement_ids": list(request.requirement_ids),
        "expected_source_classes": _expected_source_classes(request),
        "result_status": request.result_status,
        "bridge_only": request.bridge_only,
        "execution_mode": request.execution_mode,
        "ledger_candidate_count_before": ledger_projection.get(
            "candidate_count",
            0,
        ),
        "ledger_requirement_count_before": ledger_projection.get(
            "requirement_count",
            0,
        ),
    }
    if provider_job_offline:
        metadata.update(
            {
                "offline_live_shaped_execution": True,
                "adapter_result_injected": True,
                "live_provider_call_executed": False,
                "authorized_query_ref": request.authorized_query_ref,
                "authorized_query": request.authorized_query,
            }
        )
    else:
        metadata["fixture_only_provenance"] = _fixture_only_provenance()
    payload: dict[str, Any] = {
        "observation_id": f"ledger:{request.execution_id}",
        "observation_source": observation_source,
        "requirements": [requirement],
        "candidates": [candidate],
        "requirement_links": [
            {
                "requirement_id": _requirement_id(request),
                "candidate_id": candidate["candidate_id"],
                "link_reason": (
                    "followup_provider_job_execution_binding"
                    if provider_job_offline
                    else "followup_fixture_execution_binding"
                ),
                "link_status": candidate["disposition"],
            }
        ],
        metadata_key: metadata,
    }
    return EvidenceLedgerObservation(
        observation_id=f"ledger:{request.execution_id}",
        source=observation_source,
        payload={
            key: value
            for key, value in payload.items()
            if key not in {"observation_id", "observation_source"}
        },
    )


def _source_requirement(
    request: FollowupEvidenceIntakeRequest,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    required_source_class = _required_source_class(request)
    required_source_tier = clean_token(summary.get("required_source_tier"))
    if not required_source_tier and required_source_class in {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
    }:
        required_source_tier = "official"
    return {
        "requirement_id": _requirement_id(request),
        "requirement_kind": _requirement_kind(required_source_class),
        "origin_ref": f"followup_fixture_execution:{request.execution_id}",
        "required_source_class": required_source_class,
        "required_source_tier": required_source_tier,
        "required_currentness": clean_token(
            summary.get("required_currentness")
            or summary.get("currentness_signal")
            or "current"
        ),
    }


def _candidate_record(
    request: FollowupEvidenceIntakeRequest,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    status = clean_token(request.result_status)
    provider_job_offline = (
        request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    )
    source_class = clean_token(summary.get("source_class")) or "unknown"
    source_tier = clean_token(summary.get("source_tier"))
    if not source_tier and source_class in {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
    }:
        source_tier = "official"
    disposition = _candidate_disposition(request)
    success_statuses = {
        FollowupExecutionStatus.FIXTURE_SUCCESS.value,
        FollowupProviderJobExecutionStatus.CANDIDATE_ACQUIRED.value,
    }
    readable = "readable" if status in success_statuses else "not_readable"
    fetchable = "fetchable" if status in success_statuses else "not_fetchable"
    return {
        "candidate_id": _ledger_candidate_id(request),
        "url": clean_text(summary.get("url"), limit=500),
        "title": clean_text(summary.get("title") or summary.get("summary")),
        "domain": clean_text(summary.get("domain"), limit=160),
        "source_label": (
            "fixture follow-up intake "
            f"{request.component_id} {request.source_obligation_id} "
            f"{request.sealed_candidate_id}"
        ),
        "provider_name": (
            summary.get("provider_name") if provider_job_offline else "followup_fixture"
        ),
        "provider_role": request.provider_job_kind,
        "retrieval_pass_id": request.followup_execution_observation_id,
        "query_ref": (
            request.authorized_query_ref
            if provider_job_offline
            else "fixture_only_followup_intake"
        ),
        "action_ref": request.execution_id,
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": clean_token(
            summary.get("currentness_signal") or "fixture_current"
        ),
        "readable_status": clean_token(summary.get("readable_status") or readable),
        "fetchable_status": clean_token(summary.get("fetchable_status") or fetchable),
        "disposition": disposition,
        "record_kind": "fact",
        "requirement_id": _requirement_id(request),
        "eligible_for_stronger_obligation": _source_class_matches_expected(request)
        and bool(
            summary.get("eligible_for_stronger_obligation")
            or source_tier in {"official", "primary", "canonical"}
        ),
        "final_evidence_eligible": False,
        "reason": _candidate_reason(request),
        "followup_execution_id": request.execution_id,
        "followup_execution_observation_id": request.followup_execution_observation_id,
        "sealed_candidate_id": request.sealed_candidate_id,
        "component_id": request.component_id,
        "source_obligation_id": request.source_obligation_id,
        "authorized_query_ref": request.authorized_query_ref,
        "authorized_query": request.authorized_query,
        (
            "sanitized_candidate_summary"
            if provider_job_offline
            else "sanitized_fixture_result_summary"
        ): summary,
    }


def _candidate_disposition(request: FollowupEvidenceIntakeRequest) -> str:
    if request.bridge_only:
        return "contextual"
    summary = _mapping(
        request.sanitized_candidate_summary
        if request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
        else request.sanitized_fixture_result_summary
    )
    if bool(summary.get("aggregate_only")):
        return "rejected"
    if clean_token(summary.get("currentness_signal")) in {
        "stale",
        "outdated",
        "historical_only",
        "off_topic",
        "not_current",
    }:
        return "rejected"
    if clean_token(summary.get("readable_status")) in {
        "unreadable",
        "fetch_failed",
        "not_readable",
        "blocked",
        "unfetchable",
        "no_readable_text",
    }:
        return "rejected"
    if clean_token(summary.get("fetchable_status")) in {
        "unfetchable",
        "fetch_failed",
        "not_fetchable",
        "blocked",
    }:
        return "rejected"
    if (
        request.result_status
        in {
            FollowupExecutionStatus.FIXTURE_SUCCESS.value,
            FollowupProviderJobExecutionStatus.CANDIDATE_ACQUIRED.value,
        }
        and _source_class_matches_expected(request)
    ):
        return "accepted"
    return "rejected"


def _candidate_reason(request: FollowupEvidenceIntakeRequest) -> str:
    provider_job_offline = (
        request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    )
    if request.bridge_only:
        return (
            "bridge_only_provider_job_result_not_satisfying"
            if provider_job_offline
            else "bridge_only_fixture_result_not_satisfying"
        )
    if (
        request.result_status
        in {
            FollowupExecutionStatus.FIXTURE_SUCCESS.value,
            FollowupProviderJobExecutionStatus.CANDIDATE_ACQUIRED.value,
        }
        and not _source_class_matches_expected(request)
    ):
        return (
            "provider_job_candidate_outside_sealed_contract"
            if provider_job_offline
            else "fixture_success_source_class_outside_sealed_contract"
        )
    if request.result_status in {
        FollowupExecutionStatus.FIXTURE_SUCCESS.value,
        FollowupProviderJobExecutionStatus.CANDIDATE_ACQUIRED.value,
    }:
        return (
            "provider_job_offline_followup_evidence_intake"
            if provider_job_offline
            else "fixture_success_followup_evidence_intake"
        )
    return f"{request.result_status}_not_admitted_as_satisfying_evidence"


def _candidate_admitted(request: FollowupEvidenceIntakeRequest) -> bool:
    return (
        request.result_status
        in {
            FollowupExecutionStatus.FIXTURE_SUCCESS.value,
            FollowupProviderJobExecutionStatus.CANDIDATE_ACQUIRED.value,
        }
        and not request.bridge_only
        and _source_class_matches_expected(request)
        and _candidate_disposition(request) == "accepted"
    )


def _source_obligation_satisfied(request: FollowupEvidenceIntakeRequest) -> bool:
    return _candidate_admitted(request)


def _intake_status(
    request: FollowupEvidenceIntakeRequest,
) -> FollowupEvidenceIntakeStatus:
    provider_job_offline = (
        request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    )
    if request.bridge_only:
        return (
            FollowupEvidenceIntakeStatus.PROVIDER_JOB_BRIDGE_ONLY_RECORDED
            if provider_job_offline
            else FollowupEvidenceIntakeStatus.FIXTURE_BRIDGE_ONLY_RECORDED
        )
    if _candidate_admitted(request):
        return (
            FollowupEvidenceIntakeStatus.PROVIDER_JOB_INTAKE_ADMITTED
            if provider_job_offline
            else FollowupEvidenceIntakeStatus.FIXTURE_INTAKE_ADMITTED
        )
    return (
        FollowupEvidenceIntakeStatus.PROVIDER_JOB_NO_ADMISSION_RECORDED
        if provider_job_offline
        else FollowupEvidenceIntakeStatus.FIXTURE_NO_ADMISSION_RECORDED
    )


def _ledger_candidate_id(request: FollowupEvidenceIntakeRequest) -> str:
    prefix = (
        "followup_provider_job"
        if request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
        else "followup_fixture"
    )
    return clean_token(
        f"{prefix}:{request.sealed_candidate_id}:{request.execution_id}"
    )


def _requirement_id(request: FollowupEvidenceIntakeRequest) -> str:
    requirement_id = next(iter(request.requirement_ids), None) or request.source_obligation_id
    if ":" not in requirement_id:
        return f"source_requirement:{requirement_id}"
    return requirement_id


def _expected_source_classes(request: FollowupEvidenceIntakeRequest) -> tuple[str, ...]:
    if request.expected_source_classes and "[redacted]" not in request.expected_source_classes:
        return request.expected_source_classes
    expected = _mapping(request.expected_evidence_ledger_custody_update)
    classes = _strings(expected.get("source_classes"))
    if classes and "[redacted]" not in classes:
        return tuple(classes)
    return _expected_source_classes_for_provider_job(request.provider_job_kind)


def _expected_source_classes_for_provider_job(provider_job_kind: str) -> tuple[str, ...]:
    job_kind = clean_token(provider_job_kind)
    if job_kind == ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value:
        return ("official_government", "official_current_rules")
    if job_kind == ProviderJobKind.LEGAL_CURRENT_PRIMARY_ACQUISITION.value:
        return ("primary_legal", "legal_or_regulatory_text")
    if job_kind == ProviderJobKind.CANONICAL_DOC_ACQUISITION.value:
        return ("canonical", "primary_source_documents")
    if (
        job_kind
        == ProviderJobKind.SOURCE_BOUND_NUMERIC_EXTRACTION_CALCULATION_SUPPORT.value
    ):
        return ("sourced_numeric_values",)
    if job_kind == ProviderJobKind.CONFLICT_CURRENTNESS_CHECK.value:
        return ("current_primary_or_official",)
    if job_kind == ProviderJobKind.RECONCILIATION_SUPPORT.value:
        return ("source_family_map",)
    if job_kind == ProviderJobKind.FETCH_READ_EXTRACT.value:
        return ("answer_bearing_extract",)
    return ("answer_bearing_candidate",)


def _required_source_class(request: FollowupEvidenceIntakeRequest) -> str:
    expected = _expected_source_classes(request)
    preferred = (
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "current_primary_or_official",
        "sourced_numeric_values",
    )
    for item in preferred:
        if item in expected:
            return item
    return next(iter(expected), "unknown")


def _source_class_matches_expected(request: FollowupEvidenceIntakeRequest) -> bool:
    summary = _mapping(
        request.sanitized_candidate_summary
        if request.execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
        else request.sanitized_fixture_result_summary
    )
    source_class = clean_token(summary.get("source_class"))
    if not source_class:
        return False
    return source_class in _expected_source_classes(request)


def _execution_mode(state: Mapping[str, Any]) -> str:
    return (
        clean_token(state.get("execution_mode"))
        or clean_token(state.get("fixture_execution_mode"))
        or FIXTURE_EXECUTION_MODE
    )


def _intake_mode_for_execution_state(state: Mapping[str, Any]) -> str:
    if _execution_mode(state) == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        return FOLLOWUP_PROVIDER_JOB_EVIDENCE_INTAKE_MODE
    return FOLLOWUP_EVIDENCE_INTAKE_MODE


def _requirement_kind(source_class: str) -> str:
    if source_class in {"official_current_rules", "current_primary_or_official"}:
        return "official_current"
    if source_class == "legal_or_regulatory_text":
        return "legal"
    if source_class in {"primary_source_documents", "archival_primary_text"}:
        return "canonical"
    return "general"


def _fixture_only_provenance() -> dict[str, Any]:
    return followup_fixture_provenance(
        intake_bridge="ag96i2c_followup_evidence_ledger_intake"
    )


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        "evidence_ledger_mutated": True,
        "evidence_ledger_intake_only_opened_surface": True,
        "sufficiency_judgment_rechecked": False,
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "final_answer_packet_updated": False,
        "final_answer_behavior_changed": False,
        "author_prose_behavior_changed": False,
        "citation_behavior_changed": False,
    }


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture()


def _ag96i3m2_redaction_posture() -> dict[str, bool]:
    return {
        **followup_common_redaction_posture(
            sanitized_fixture_summary_only=False,
        ),
        "sanitized_admission_review_projection_only": True,
        "explicit_intake_binding_only": True,
        "raw_text_retained": False,
        "verifier_text_retained": False,
        "supported_excerpts_retained": False,
        "provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "secrets_retained": False,
        "db_rows_retained": False,
        "private_logs_retained": False,
    }


def _ag96i3m2_candidate_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(value)
    identity = _mapping(candidate.get("candidate_identity_summary"))
    verification = _mapping(candidate.get("verification_summary"))
    read_summary = _mapping(candidate.get("read_observation_summary"))
    custody_summary = _mapping(candidate.get("custody_metadata_summary"))
    boundary_flags = _mapping(candidate.get("non_authoritative_boundary_flags"))
    evidence_boundary = _mapping(candidate.get("evidence_boundary"))
    return _compact(
        {
            "schema_version": clean_token(candidate.get("schema_version")),
            "record_type": clean_token(candidate.get("record_type")),
            "candidate_id": clean_token(candidate.get("candidate_id")),
            "observation_id": clean_token(candidate.get("observation_id")),
            "observation_ref": clean_text(candidate.get("observation_ref"), limit=220),
            "owner": clean_text(candidate.get("owner"), limit=160),
            "canonical_state": candidate.get("canonical_state") is True,
            "trace_only": candidate.get("trace_only") is True,
            "storage_only": candidate.get("storage_only") is True,
            "diagnostic_only": candidate.get("diagnostic_only") is True,
            "admission_review_status": clean_token(
                candidate.get("admission_review_status")
            ),
            "admission_review_candidate_ready": (
                candidate.get("admission_review_candidate_ready") is True
            ),
            "blocker_codes": _strings(candidate.get("blocker_codes")),
            "reason_codes": _strings(candidate.get("reason_codes")),
            "recommended_next_step": clean_token(
                candidate.get("recommended_next_step")
            ),
            "candidate_identity_summary": _compact(
                {
                    "candidate_url": clean_text(identity.get("candidate_url"), limit=500),
                    "candidate_domain": clean_text(
                        identity.get("candidate_domain"),
                        limit=160,
                    ),
                    "attempted_url": clean_text(identity.get("attempted_url"), limit=500),
                    "resolved_url": clean_text(identity.get("resolved_url"), limit=500),
                    "attempted_domain": clean_text(
                        identity.get("attempted_domain"),
                        limit=160,
                    ),
                    "resolved_domain": clean_text(
                        identity.get("resolved_domain"),
                        limit=160,
                    ),
                    "observation_domain": clean_text(
                        identity.get("observation_domain"),
                        limit=160,
                    ),
                    "source_identity_status": clean_token(
                        identity.get("source_identity_status")
                    ),
                    "url_domain_comparison_posture": clean_token(
                        identity.get("url_domain_comparison_posture")
                    ),
                }
            ),
            "verification_summary": _compact(
                {
                    "verification_status": clean_token(
                        verification.get("verification_status")
                    ),
                    "candidate_accounting_status": clean_token(
                        verification.get("candidate_accounting_status")
                    ),
                    "source_identity_status": clean_token(
                        verification.get("source_identity_status")
                    ),
                    "official_source_status": clean_token(
                        verification.get("official_source_status")
                    ),
                    "source_obligation": clean_token(
                        verification.get("source_obligation")
                    ),
                    "source_class_required": clean_token(
                        verification.get("source_class_required")
                    ),
                    "source_class_posture": clean_token(
                        verification.get("source_class_posture")
                    ),
                    "currentness_posture": clean_token(
                        verification.get("currentness_posture")
                    ),
                    "relevance_posture": clean_token(
                        verification.get("relevance_posture")
                    ),
                    "candidate_fit_posture": clean_token(
                        verification.get("candidate_fit_posture")
                    ),
                    "recommended_next_step_from_verification": clean_token(
                        verification.get("recommended_next_step_from_verification")
                    ),
                }
            ),
            "read_observation_summary": _compact(
                {
                    "schema_version": clean_token(read_summary.get("schema_version")),
                    "record_type": clean_token(read_summary.get("record_type")),
                    "read_posture": clean_token(read_summary.get("read_posture")),
                    "fetch_status": clean_token(read_summary.get("fetch_status")),
                    "read_status": clean_token(read_summary.get("read_status")),
                    "http_status": read_summary.get("http_status"),
                    "content_type": clean_text(
                        read_summary.get("content_type"),
                        limit=160,
                    ),
                    "media_type": clean_token(read_summary.get("media_type")),
                    "title": clean_text(read_summary.get("title"), limit=300),
                    "detected_updated_date": clean_text(
                        read_summary.get("detected_updated_date"),
                        limit=80,
                    ),
                    "extracted_text_present": (
                        read_summary.get("extracted_text_present") is True
                    ),
                    "extracted_text_char_count": read_summary.get(
                        "extracted_text_char_count"
                    ),
                    "sanitized_text_char_count": read_summary.get(
                        "sanitized_text_char_count"
                    ),
                    "extracted_text_truncated": (
                        read_summary.get("extracted_text_truncated") is True
                    ),
                    "raw_page_text_retained": (
                        read_summary.get("raw_page_text_retained") is True
                    ),
                }
            ),
            "custody_metadata_summary": _bool_mapping(custody_summary),
            "custody_metadata_complete": (
                candidate.get("custody_metadata_complete") is True
            ),
            "non_authoritative_boundary_flags": _bool_mapping(boundary_flags),
            "evidence_boundary": _bool_mapping(evidence_boundary),
            "final_evidence": candidate.get("final_evidence") is True,
            "citation_eligible": candidate.get("citation_eligible") is True,
            "evidence_ledger_admitted": candidate.get("evidence_ledger_admitted")
            is True,
            "author_activation_allowed": candidate.get("author_activation_allowed")
            is True,
        }
    )


def _bool_mapping(value: Mapping[str, Any]) -> dict[str, bool]:
    return {str(key): item is True for key, item in value.items()}


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    out: list[str] = []
    for item in value:
        token = clean_token(item)
        if token:
            out.append(token)
    return out


__all__ = [
    "AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE",
    "FOLLOWUP_EVIDENCE_INTAKE_GATE_REASON",
    "FOLLOWUP_EVIDENCE_INTAKE_MODE",
    "FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION",
    "FOLLOWUP_EVIDENCE_INTAKE_TRACE_KEY",
    "FOLLOWUP_PROVIDER_JOB_EVIDENCE_INTAKE_MODE",
    "FollowupEvidenceIntakeActionResult",
    "FollowupEvidenceIntakeConsumptionRecord",
    "FollowupEvidenceIntakeObservation",
    "FollowupEvidenceIntakeRequest",
    "FollowupEvidenceIntakeResult",
    "FollowupEvidenceIntakeStatus",
    "build_followup_evidence_intake_record",
    "execute_followup_evidence_intake_action",
]
