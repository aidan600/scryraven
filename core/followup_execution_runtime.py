"""Fixture-only follow-up execution seam for AG-96I2B.

This module consumes sealed AG-96I2A follow-up authorization state and returns
sanitized fixture observations only. It never calls providers, search,
retrieval, fetch/read, prompts, models, citation formatters, provider-job
executors, shell processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.followup_authorization_runtime import FollowupRuntimeConsumptionRecord
from core.followup_deliberation import FollowupMode, clean_text, clean_token, safe_json
from core.followup_fixture_boundaries import (
    followup_common_redaction_posture,
    followup_live_surface_flags,
)
from core.run_kernel import (
    FOLLOWUP_EXECUTION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)

FOLLOWUP_EXECUTION_SCHEMA_VERSION = "followup_execution_ag96i2b_v1"
FOLLOWUP_EXECUTION_TRACE_KEY = "followup_fixture_execution_runtime"
FIXTURE_EXECUTION_MODE = "fixture_only"
DISABLED_EXECUTION_MODE = "disabled"
FOLLOWUP_FIXTURE_GATE_REASON = "ag96i2b_fixture_only_execution_required"


class FollowupExecutionStatus(str, Enum):
    FIXTURE_SUCCESS = "fixture_success"
    FIXTURE_NO_RESULT = "fixture_no_result"
    FIXTURE_WRONG_SOURCE_CLASS = "fixture_wrong_source_class"
    FIXTURE_BRIDGE_ONLY = "fixture_bridge_only"
    FIXTURE_ERROR = "fixture_error"


@dataclass(frozen=True, slots=True)
class FollowupExecutionRequest:
    request_id: str
    run_id: str
    checkpoint_id: str
    followup_authorization_consumption_id: str
    sealed_candidate_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_evidence_ledger_custody_update: Mapping[str, Any]
    budget_debit: Mapping[str, Any]
    fallback_stop_posture: str | None
    fallback_caveat_refuse_posture: str | None
    bridge_only_provider_output: bool
    fixture_execution_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_EXECUTION_SCHEMA_VERSION,
            "record_type": "followup_execution_request",
            "request_id": clean_token(self.request_id),
            "run_id": clean_token(self.run_id),
            "checkpoint_id": clean_token(self.checkpoint_id),
            "followup_authorization_consumption_id": clean_text(
                self.followup_authorization_consumption_id,
                limit=220,
            ),
            "sealed_candidate_id": clean_token(self.sealed_candidate_id),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [
                clean_token(item) for item in self.requirement_ids if clean_token(item)
            ],
            "expected_evidence_ledger_custody_update": safe_json(
                self.expected_evidence_ledger_custody_update
            ),
            "budget_debit": safe_json(self.budget_debit),
            "fallback_stop_posture": clean_token(self.fallback_stop_posture),
            "fallback_caveat_refuse_posture": clean_token(
                self.fallback_caveat_refuse_posture
            ),
            "bridge_only_provider_output": bool(self.bridge_only_provider_output),
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "execution_gate": _fixture_execution_gate(),
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "evidence_ledger_intake_deferred": True,
        }


@dataclass(frozen=True, slots=True)
class FollowupExecutionResult:
    result_id: str
    status: FollowupExecutionStatus
    sanitized_fixture_result_summary: Mapping[str, Any]
    bridge_only: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_EXECUTION_SCHEMA_VERSION,
            "record_type": "followup_execution_result",
            "result_id": clean_token(self.result_id),
            "status": self.status.value,
            "sanitized_fixture_result_summary": safe_json(
                self.sanitized_fixture_result_summary
            ),
            "bridge_only": bool(self.bridge_only),
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "evidence_ledger_intake_deferred": True,
            "evidence_ledger_evidence_admitted": False,
            "budget_semantics": _fixture_budget_semantics({}),
        }


@dataclass(frozen=True, slots=True)
class FollowupExecutionObservation:
    observation_id: str
    request: FollowupExecutionRequest
    result: FollowupExecutionResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        result["budget_semantics"] = _fixture_budget_semantics(
            request.get("budget_debit", {})
        )
        return {
            "schema_version": FOLLOWUP_EXECUTION_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_EXECUTION_TRACE_KEY,
            "record_type": "followup_execution_observation",
            "owner": "FollowupFixtureExecutionRuntime",
            "canonical_state": False,
            "trace_only": False,
            "storage_only": False,
            "observation_id": clean_token(self.observation_id),
            "run_id": request.get("run_id"),
            "checkpoint_id": request.get("checkpoint_id"),
            "followup_authorization_consumption_id": request.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": request.get("sealed_candidate_id"),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": _strings(
                _mapping(
                    request.get("expected_evidence_ledger_custody_update")
                ).get("source_classes")
            ),
            "expected_evidence_ledger_custody_update": request.get(
                "expected_evidence_ledger_custody_update",
                {},
            ),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "request": request,
            "result": result,
            "result_status": result.get("status"),
            "sanitized_fixture_result_summary": result.get(
                "sanitized_fixture_result_summary",
                {},
            ),
            "budget_debit": request.get("budget_debit", {}),
            "budget_semantics": result.get("budget_semantics", {}),
            "fallback_stop_posture": request.get("fallback_stop_posture"),
            "fallback_caveat_refuse_posture": request.get(
                "fallback_caveat_refuse_posture"
            ),
            "bridge_only": result.get("bridge_only"),
            "bridge_only_status": (
                "bridge_only" if result.get("bridge_only") else "not_bridge_only"
            ),
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "evidence_ledger_intake_deferred": True,
            "evidence_ledger_evidence_admitted": False,
            "execution_gate": _fixture_execution_gate(),
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupExecutionConsumptionRecord:
    execution_id: str
    observation: FollowupExecutionObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_execution_consumption_record",
            "owner": "RunKernel.FollowupFixtureExecution",
            "canonical_state": True,
            "execution_id": clean_token(self.execution_id),
        }


@dataclass(frozen=True, slots=True)
class FollowupFixtureExecutionResult:
    record: FollowupExecutionConsumptionRecord
    observation: Observation


def execute_followup_fixture(
    authorization_state: FollowupRuntimeConsumptionRecord | Mapping[str, Any],
    *,
    sealed_candidate_id: str,
    fixture_result_payload: Mapping[str, Any] | None = None,
    execution_mode: str = DISABLED_EXECUTION_MODE,
) -> FollowupExecutionConsumptionRecord:
    state = _authorization_state(authorization_state)
    mode = clean_token(execution_mode) or DISABLED_EXECUTION_MODE
    if mode != FIXTURE_EXECUTION_MODE:
        raise PermissionError(FOLLOWUP_FIXTURE_GATE_REASON)
    if fixture_result_payload is None:
        raise ValueError("fixture_only execution requires explicit fixture_result_payload")
    _validate_authorization_state(state)
    candidate = _sealed_candidate(state, sealed_candidate_id)
    _validate_candidate(state, candidate)

    sanitized = safe_json(fixture_result_payload)
    summary = dict(sanitized) if isinstance(sanitized, Mapping) else {}
    status = _fixture_status(summary, candidate)
    bridge_only = bool(
        summary.get("bridge_only")
        or candidate.get("bridge_only_provider_output")
        or status is FollowupExecutionStatus.FIXTURE_BRIDGE_ONLY
    )
    if bridge_only:
        status = FollowupExecutionStatus.FIXTURE_BRIDGE_ONLY

    request = FollowupExecutionRequest(
        request_id=(
            f"followup-execution-request:"
            f"{state.get('checkpoint_id')}:{candidate.get('candidate_id')}"
        ),
        run_id=str(state.get("run_id") or ""),
        checkpoint_id=str(state.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(state.get("consumption_id") or ""),
        sealed_candidate_id=str(candidate.get("candidate_id") or ""),
        provider_job_kind=str(candidate.get("provider_job_kind") or ""),
        component_id=str(candidate.get("component_id") or ""),
        source_obligation_id=str(candidate.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(candidate.get("requirement_ids"))),
        expected_evidence_ledger_custody_update=_mapping(
            candidate.get("expected_evidence_ledger_custody_update")
        ),
        budget_debit=_mapping(candidate.get("budget_debit")),
        fallback_stop_posture=clean_token(candidate.get("fallback_stop_posture")),
        fallback_caveat_refuse_posture=clean_token(
            candidate.get("fallback_caveat_refuse_posture")
        ),
        bridge_only_provider_output=bool(candidate.get("bridge_only_provider_output")),
        fixture_execution_mode=FIXTURE_EXECUTION_MODE,
    )
    result = FollowupExecutionResult(
        result_id=f"followup-execution-result:{request.checkpoint_id}:{request.sealed_candidate_id}",
        status=status,
        sanitized_fixture_result_summary=summary,
        bridge_only=bridge_only,
    )
    observation = FollowupExecutionObservation(
        observation_id=f"followup-execution-observation:{request.checkpoint_id}:{request.sealed_candidate_id}",
        request=request,
        result=result,
    )
    return FollowupExecutionConsumptionRecord(
        execution_id=f"followup-execution:{request.checkpoint_id}:{request.sealed_candidate_id}",
        observation=observation,
    )


def execute_followup_fixture_action(
    action: AuthorizedAction,
    *,
    authorization_state: FollowupRuntimeConsumptionRecord | Mapping[str, Any],
    sealed_candidate_id: str,
    fixture_result_payload: Mapping[str, Any] | None = None,
    execution_mode: str = DISABLED_EXECUTION_MODE,
) -> FollowupFixtureExecutionResult:
    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_FIXTURE_EXECUTE,
        stage=FOLLOWUP_EXECUTION_STAGE,
        expected_observation_type=ObservationType.FOLLOWUP_EXECUTION_OBSERVED,
    )
    record = execute_followup_fixture(
        authorization_state,
        sealed_candidate_id=sealed_candidate_id,
        fixture_result_payload=fixture_result_payload,
        execution_mode=execution_mode,
    )
    return FollowupFixtureExecutionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_EXECUTION_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_execution_state": record.to_dict()},
        ),
    )


def _authorization_state(
    state: FollowupRuntimeConsumptionRecord | Mapping[str, Any],
) -> dict[str, Any]:
    payload = state.to_dict() if hasattr(state, "to_dict") else state
    safe = safe_json(payload)
    return dict(safe) if isinstance(safe, Mapping) else {}


def _validate_authorization_state(state: Mapping[str, Any]) -> None:
    validation = _mapping(state.get("validation"))
    if validation.get("status") != "valid" or validation.get("ok") is not True:
        raise PermissionError("follow-up fixture execution requires valid authorization state")
    if state.get("status") != "sealed_non_executable":
        raise PermissionError("follow-up fixture execution requires sealed authorization state")
    if clean_token(state.get("mode")) == FollowupMode.FAST.value:
        raise PermissionError("Fast follow-up authorization candidates are not executable")
    if state.get("needs_deep") is True and clean_token(state.get("mode")) != FollowupMode.DEEP.value:
        raise PermissionError("Balanced needs_deep posture is not executable")
    if state.get("selected_mode_insufficient") is True:
        raise PermissionError("selected-mode-insufficient posture is not executable")
    gate = _mapping(state.get("execution_gate"))
    if (
        gate.get("execution_permission") is not False
        or gate.get("executable_in_current_phase") is not False
        or gate.get("provider_execution_licensed") is not False
    ):
        raise PermissionError("follow-up fixture execution requires closed provider gate")


def _sealed_candidate(
    state: Mapping[str, Any],
    sealed_candidate_id: str,
) -> Mapping[str, Any]:
    candidate_id = clean_token(sealed_candidate_id)
    for candidate in state.get("sealed_candidates", []) or []:
        if not isinstance(candidate, Mapping):
            continue
        if clean_token(candidate.get("candidate_id")) == candidate_id:
            return candidate
    raise KeyError(f"unknown sealed follow-up candidate: {sealed_candidate_id}")


def _validate_candidate(state: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    if candidate.get("status") != "sealed_non_executable":
        raise PermissionError("follow-up fixture execution requires sealed_non_executable candidate")
    if clean_token(candidate.get("mode") or state.get("mode")) == FollowupMode.FAST.value:
        raise PermissionError("Fast follow-up authorization candidates are not executable")
    gate = _mapping(candidate.get("execution_gate"))
    if (
        gate.get("execution_permission") is not False
        or gate.get("executable_in_current_phase") is not False
        or gate.get("provider_execution_licensed") is not False
    ):
        raise PermissionError("candidate claims real provider execution permission")


def _fixture_status(
    fixture_result_payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> FollowupExecutionStatus:
    if bool(fixture_result_payload.get("bridge_only")) or bool(
        candidate.get("bridge_only_provider_output")
    ):
        return FollowupExecutionStatus.FIXTURE_BRIDGE_ONLY
    if bool(fixture_result_payload.get("wrong_source_class")):
        return FollowupExecutionStatus.FIXTURE_WRONG_SOURCE_CLASS
    if bool(fixture_result_payload.get("error")):
        return FollowupExecutionStatus.FIXTURE_ERROR
    if bool(fixture_result_payload.get("no_result")):
        return FollowupExecutionStatus.FIXTURE_NO_RESULT
    raw = clean_token(fixture_result_payload.get("result_status"))
    if raw:
        for status in FollowupExecutionStatus:
            if raw == status.value:
                return status
    return FollowupExecutionStatus.FIXTURE_SUCCESS


def _fixture_execution_gate() -> dict[str, Any]:
    return {
        "default_execution_mode": DISABLED_EXECUTION_MODE,
        "allowed_execution_mode": FIXTURE_EXECUTION_MODE,
        "fixture_payload_required": True,
        "provider_execution_licensed": False,
        "execution_permission": True,
        "real_provider_execution_available": False,
        "provider_job_executor_connected": False,
        "reason": FOLLOWUP_FIXTURE_GATE_REASON,
    }


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        "evidence_ledger_mutated": False,
        "sufficiency_judgment_rechecked": False,
        "final_answer_behavior_changed": False,
        "author_prose_behavior_changed": False,
    }


def _fixture_budget_semantics(planned_debit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "planned_debit_preserved": safe_json(planned_debit),
        "fixture_execution_did_not_incur_provider_search_fetch_read_cost": True,
        "actual_provider_search_fetch_read_cost_incurred": False,
        "actual_provider_account_debited": False,
        "provider_cost_accounting_deferred": True,
    }


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture()


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
    "DISABLED_EXECUTION_MODE",
    "FIXTURE_EXECUTION_MODE",
    "FOLLOWUP_EXECUTION_SCHEMA_VERSION",
    "FOLLOWUP_EXECUTION_TRACE_KEY",
    "FOLLOWUP_FIXTURE_GATE_REASON",
    "FollowupExecutionConsumptionRecord",
    "FollowupExecutionObservation",
    "FollowupExecutionRequest",
    "FollowupExecutionResult",
    "FollowupExecutionStatus",
    "FollowupFixtureExecutionResult",
    "execute_followup_fixture",
    "execute_followup_fixture_action",
]
