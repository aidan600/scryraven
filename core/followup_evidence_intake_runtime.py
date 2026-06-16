"""Fixture-only follow-up EvidenceLedger intake seam for AG-96I2C.

This module bridges canonical AG-96I2B fixture execution state into a sanitized
EvidenceLedger observation. It never calls providers, search, retrieval,
fetch/read, prompts, models, citation formatters, provider-job executors, shell
processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.evidence_ledger import EvidenceLedgerObservation
from core.followup_deliberation import clean_text, clean_token, safe_json
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    FollowupExecutionStatus,
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
FOLLOWUP_EVIDENCE_INTAKE_GATE_REASON = "ag96i2c_fixture_only_evidence_ledger_intake"


class FollowupEvidenceIntakeStatus(str, Enum):
    FIXTURE_INTAKE_ADMITTED = "fixture_intake_admitted"
    FIXTURE_BRIDGE_ONLY_RECORDED = "fixture_bridge_only_recorded"
    FIXTURE_NO_ADMISSION_RECORDED = "fixture_no_admission_recorded"


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
    result_status: str
    bridge_only: bool
    expected_evidence_ledger_custody_update: Mapping[str, Any]
    sanitized_fixture_result_summary: Mapping[str, Any]
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
            "result_status": clean_token(self.result_status),
            "bridge_only": bool(self.bridge_only),
            "expected_evidence_ledger_custody_update": safe_json(
                self.expected_evidence_ledger_custody_update
            ),
            "sanitized_fixture_result_summary": safe_json(
                self.sanitized_fixture_result_summary
            ),
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
            "result_status": request.get("result_status"),
            "fixture_execution_mode": FIXTURE_EXECUTION_MODE,
            "bridge_only": request.get("bridge_only"),
            "expected_evidence_ledger_custody_update": request.get(
                "expected_evidence_ledger_custody_update",
                {},
            ),
            "sanitized_fixture_result_summary": request.get(
                "sanitized_fixture_result_summary",
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
            "ledger_observation": result.get("ledger_observation", {}),
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
class FollowupEvidenceIntakeConsumptionRecord:
    intake_id: str
    observation: FollowupEvidenceIntakeObservation

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
) -> FollowupEvidenceIntakeConsumptionRecord:
    state = _mapping(safe_json(followup_execution_state))
    ledger_projection = _mapping(safe_json(evidence_ledger_projection))
    _validate_execution_state(state)
    _validate_action_inputs(action.inputs, state)

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
        result_status=str(state.get("result_status") or ""),
        bridge_only=bool(state.get("bridge_only")),
        expected_evidence_ledger_custody_update=_mapping(
            state.get("expected_evidence_ledger_custody_update")
        ),
        sanitized_fixture_result_summary=_mapping(
            state.get("sanitized_fixture_result_summary")
        ),
        provider_execution_licensed=False,
        evidence_ledger_intake_mode=FOLLOWUP_EVIDENCE_INTAKE_MODE,
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


def _validate_execution_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError("follow-up evidence intake requires canonical execution state")
    if state.get("owner") != "RunKernel.FollowupFixtureExecution":
        raise PermissionError("follow-up evidence intake requires RunKernel execution state")
    if state.get("fixture_execution_mode") != FIXTURE_EXECUTION_MODE:
        raise PermissionError("follow-up evidence intake requires fixture_only execution")
    gate = _mapping(state.get("execution_gate"))
    if gate.get("allowed_execution_mode") != FIXTURE_EXECUTION_MODE:
        raise PermissionError("follow-up evidence intake requires fixture-only gate")
    if gate.get("provider_execution_licensed") is not False:
        raise PermissionError("provider execution is not licensed for intake")
    if state.get("evidence_ledger_intake_deferred") is not True:
        raise PermissionError("follow-up execution state must defer EvidenceLedger intake")
    if state.get("evidence_ledger_evidence_admitted") is not False:
        raise PermissionError("follow-up execution state must not have admitted evidence")
    if state.get("provider_job_kind") not in {
        "official_current_candidate_acquisition",
        "direct_candidate_search",
        "semantic_recall",
        "reconciliation_support",
    }:
        raise PermissionError("unknown follow-up provider job kind")
    if state.get("result_status") not in {item.value for item in FollowupExecutionStatus}:
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


def _validate_action_inputs(
    action_inputs: Mapping[str, Any],
    state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "fixture_execution_mode",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
    ):
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
    if action_inputs.get("evidence_ledger_intake_mode") != (
        FOLLOWUP_EVIDENCE_INTAKE_MODE
    ):
        raise PermissionError("authorized intake action must be fixture-only")


def _ledger_observation_from_request(
    request: FollowupEvidenceIntakeRequest,
    *,
    ledger_projection: Mapping[str, Any],
) -> EvidenceLedgerObservation:
    summary = _mapping(request.sanitized_fixture_result_summary)
    requirement = _source_requirement(request, summary)
    candidate = _candidate_record(request, summary)
    payload: dict[str, Any] = {
        "observation_id": f"ledger:{request.execution_id}",
        "observation_source": "followup_fixture_evidence_intake",
        "requirements": [requirement],
        "candidates": [candidate],
        "requirement_links": [
            {
                "requirement_id": request.source_obligation_id,
                "candidate_id": candidate["candidate_id"],
                "link_reason": "followup_fixture_execution_binding",
                "link_status": candidate["disposition"],
            }
        ],
        "followup_fixture_intake": {
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
            "result_status": request.result_status,
            "bridge_only": request.bridge_only,
            "fixture_only_provenance": _fixture_only_provenance(),
            "ledger_candidate_count_before": ledger_projection.get(
                "candidate_count",
                0,
            ),
            "ledger_requirement_count_before": ledger_projection.get(
                "requirement_count",
                0,
            ),
        },
    }
    return EvidenceLedgerObservation(
        observation_id=f"ledger:{request.execution_id}",
        source="followup_fixture_evidence_intake",
        payload=payload,
    )


def _source_requirement(
    request: FollowupEvidenceIntakeRequest,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    required_source_class = (
        clean_token(summary.get("required_source_class"))
        or clean_token(summary.get("source_class"))
        or "unknown"
    )
    required_source_tier = clean_token(summary.get("required_source_tier"))
    if not required_source_tier and required_source_class in {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
    }:
        required_source_tier = "official"
    return {
        "requirement_id": request.source_obligation_id,
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
    readable = "readable" if status == FollowupExecutionStatus.FIXTURE_SUCCESS.value else "not_readable"
    fetchable = "fetchable" if status == FollowupExecutionStatus.FIXTURE_SUCCESS.value else "not_fetchable"
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
        "provider_name": "followup_fixture",
        "provider_role": request.provider_job_kind,
        "retrieval_pass_id": request.followup_execution_observation_id,
        "query_ref": "fixture_only_followup_intake",
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
        "requirement_id": request.source_obligation_id,
        "eligible_for_stronger_obligation": bool(
            summary.get("eligible_for_stronger_obligation")
            or source_tier in {"official", "primary", "canonical"}
        ),
        "final_evidence_eligible": False,
        "reason": _candidate_reason(request),
        "followup_execution_id": request.execution_id,
        "followup_execution_observation_id": request.followup_execution_observation_id,
        "sealed_candidate_id": request.sealed_candidate_id,
        "component_id": request.component_id,
        "sanitized_fixture_result_summary": summary,
    }


def _candidate_disposition(request: FollowupEvidenceIntakeRequest) -> str:
    if request.bridge_only:
        return "contextual"
    if request.result_status == FollowupExecutionStatus.FIXTURE_SUCCESS.value:
        return "accepted"
    return "rejected"


def _candidate_reason(request: FollowupEvidenceIntakeRequest) -> str:
    if request.bridge_only:
        return "bridge_only_fixture_result_not_satisfying"
    if request.result_status == FollowupExecutionStatus.FIXTURE_SUCCESS.value:
        return "fixture_success_followup_evidence_intake"
    return f"{request.result_status}_not_admitted_as_satisfying_evidence"


def _candidate_admitted(request: FollowupEvidenceIntakeRequest) -> bool:
    return (
        request.result_status == FollowupExecutionStatus.FIXTURE_SUCCESS.value
        and not request.bridge_only
    )


def _source_obligation_satisfied(request: FollowupEvidenceIntakeRequest) -> bool:
    return _candidate_admitted(request)


def _intake_status(
    request: FollowupEvidenceIntakeRequest,
) -> FollowupEvidenceIntakeStatus:
    if request.bridge_only:
        return FollowupEvidenceIntakeStatus.FIXTURE_BRIDGE_ONLY_RECORDED
    if _candidate_admitted(request):
        return FollowupEvidenceIntakeStatus.FIXTURE_INTAKE_ADMITTED
    return FollowupEvidenceIntakeStatus.FIXTURE_NO_ADMISSION_RECORDED


def _ledger_candidate_id(request: FollowupEvidenceIntakeRequest) -> str:
    return clean_token(
        f"followup_fixture:{request.sealed_candidate_id}:{request.execution_id}"
    )


def _requirement_kind(source_class: str) -> str:
    if source_class in {"official_current_rules", "current_primary_or_official"}:
        return "official_current"
    if source_class == "legal_or_regulatory_text":
        return "legal"
    if source_class in {"primary_source_documents", "archival_primary_text"}:
        return "canonical"
    return "general"


def _fixture_only_provenance() -> dict[str, Any]:
    return {
        "origin": "ag96i2b_followup_fixture_execution",
        "intake_bridge": "ag96i2c_followup_evidence_ledger_intake",
        "fixture_only": True,
        "live_provider_result": False,
        "provider_job_executor_connected": False,
    }


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        "provider_execution_licensed": False,
        "live_provider_call_executed": False,
        "provider_job_scheduled": False,
        "provider_job_dispatched": False,
        "search_executed": False,
        "retrieval_executed": False,
        "fetch_executed": False,
        "model_called": False,
        "query_generation_changed": False,
        "retrieval_ranking_filtering_changed": False,
        "evidence_ledger_mutated": True,
        "evidence_ledger_intake_only_opened_surface": True,
        "sufficiency_judgment_rechecked": False,
        "search_judgment_rerun": False,
        "final_answer_packet_updated": False,
        "final_answer_behavior_changed": False,
        "author_prose_behavior_changed": False,
        "citation_behavior_changed": False,
        "pipeline_orchestrator_domain_logic_changed": False,
    }


def _redaction_posture() -> dict[str, bool]:
    return {
        "json_safe": True,
        "sanitized_fixture_summary_only": True,
        "provider_payloads_retained": False,
        "prompts_retained": False,
        "model_responses_retained": False,
        "unsanitized_text_retained": False,
        "private_records_or_complete_traces_retained": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "FOLLOWUP_EVIDENCE_INTAKE_GATE_REASON",
    "FOLLOWUP_EVIDENCE_INTAKE_MODE",
    "FOLLOWUP_EVIDENCE_INTAKE_SCHEMA_VERSION",
    "FOLLOWUP_EVIDENCE_INTAKE_TRACE_KEY",
    "FollowupEvidenceIntakeActionResult",
    "FollowupEvidenceIntakeConsumptionRecord",
    "FollowupEvidenceIntakeObservation",
    "FollowupEvidenceIntakeRequest",
    "FollowupEvidenceIntakeResult",
    "FollowupEvidenceIntakeStatus",
    "build_followup_evidence_intake_record",
    "execute_followup_evidence_intake_action",
]
