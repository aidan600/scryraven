"""Offline live-shaped follow-up provider-job execution seam for AG-96I3A.

This module consumes a RunKernel-authorized official/current follow-up action
and returns sanitized candidate observations from injected adapter payloads.
It performs no external calls and owns no answer authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.followup_deliberation import (
    ProviderJobKind,
    clean_text,
    clean_token,
    safe_json,
)
from core.followup_fixture_boundaries import (
    FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    followup_common_redaction_posture,
    followup_live_surface_flags,
)

FOLLOWUP_PROVIDER_JOB_EXECUTION_SCHEMA_VERSION = (
    "followup_provider_job_execution_ag96i3a_v1"
)
FOLLOWUP_PROVIDER_JOB_EXECUTION_TRACE_KEY = (
    "followup_provider_job_execution_runtime"
)
FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE = "bounded_provider_job_offline"
FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON = (
    "ag96i3a_offline_live_shaped_provider_job_execution"
)
FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND = (
    ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
)


class FollowupProviderJobExecutionStatus(str, Enum):
    CANDIDATE_ACQUIRED = "candidate_acquired"
    NO_RESULT = "no_result"
    WRONG_SOURCE_CLASS = "wrong_source_class"
    BRIDGE_ONLY = "bridge_only"
    ADAPTER_ERROR = "adapter_error"
    BUDGET_DENIED = "budget_denied"
    CLOSED_SURFACE_DENIED = "closed_surface_denied"


@dataclass(frozen=True, slots=True)
class FollowupProviderJobExecutionRequest:
    request_id: str
    run_id: str
    checkpoint_id: str
    followup_authorization_consumption_id: str
    sealed_candidate_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    expected_evidence_ledger_custody_update: Mapping[str, Any]
    budget_debit: Mapping[str, Any]
    authorized_query_ref: str | None
    authorized_query: str | None
    execution_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_PROVIDER_JOB_EXECUTION_SCHEMA_VERSION,
            "record_type": "followup_provider_job_execution_request",
            "request_id": clean_text(self.request_id, limit=220),
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
            "expected_source_classes": [
                clean_token(item)
                for item in self.expected_source_classes
                if clean_token(item)
            ],
            "expected_evidence_ledger_custody_update": safe_json(
                self.expected_evidence_ledger_custody_update
            ),
            "budget_debit": safe_json(self.budget_debit),
            "authorized_query_ref": clean_token(self.authorized_query_ref, limit=180),
            "authorized_query": clean_text(self.authorized_query, limit=300),
            "execution_mode": clean_token(self.execution_mode),
            "execution_gate": _execution_gate(),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupProviderJobExecutionResult:
    result_id: str
    status: FollowupProviderJobExecutionStatus
    sanitized_candidate_summary: Mapping[str, Any]
    bridge_only: bool
    adapter_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_PROVIDER_JOB_EXECUTION_SCHEMA_VERSION,
            "record_type": "followup_provider_job_execution_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": self.status.value,
            "sanitized_candidate_summary": safe_json(
                self.sanitized_candidate_summary
            ),
            "bridge_only": bool(self.bridge_only),
            "adapter_error_code": clean_token(self.adapter_error_code, limit=120),
            "source_obligation_satisfied": False,
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "sufficiency_ready": False,
            "final_answer_packet_ready": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupProviderJobExecutionObservation:
    observation_id: str
    request: FollowupProviderJobExecutionRequest
    result: FollowupProviderJobExecutionResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        summary = _candidate_summary(
            result.get("sanitized_candidate_summary"),
            request=request,
            result_status=str(result.get("status") or ""),
        )
        return {
            "schema_version": FOLLOWUP_PROVIDER_JOB_EXECUTION_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_PROVIDER_JOB_EXECUTION_TRACE_KEY,
            "record_type": "followup_provider_job_execution_observation",
            "owner": "FollowupProviderJobExecutionRuntime",
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
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "expected_evidence_ledger_custody_update": request.get(
                "expected_evidence_ledger_custody_update",
                {},
            ),
            "authorized_query_ref": request.get("authorized_query_ref"),
            "authorized_query": request.get("authorized_query"),
            "execution_mode": request.get("execution_mode"),
            "request": request,
            "result": result,
            "result_status": result.get("status"),
            "sanitized_candidate_summary": summary,
            "budget_debit": request.get("budget_debit", {}),
            "budget_semantics": _budget_semantics(request.get("budget_debit", {})),
            "bridge_only": result.get("bridge_only"),
            "bridge_only_status": (
                "bridge_only" if result.get("bridge_only") else "not_bridge_only"
            ),
            "adapter_error_code": result.get("adapter_error_code"),
            "offline_live_shaped_execution": True,
            "adapter_result_injected": True,
            "provider_execution_licensed": False,
            "live_provider_call_executed": False,
            "search_executed": False,
            "retrieval_executed": False,
            "fetch_executed": False,
            "model_called": False,
            "live_validation_not_run": True,
            "source_obligation_satisfied": False,
            "final_evidence_satisfied": False,
            "citation_eligible": False,
            "sufficiency_ready": False,
            "final_answer_packet_ready": False,
            "author_activation_allowed": False,
            "author_executor_invoked": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "evidence_ledger_intake_deferred": True,
            "evidence_ledger_evidence_admitted": False,
            "execution_gate": _execution_gate(),
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupProviderJobExecutionConsumptionRecord:
    execution_id: str
    observation: FollowupProviderJobExecutionObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_provider_job_execution_consumption_record",
            "owner": "RunKernel.FollowupProviderJobExecution",
            "canonical_state": True,
            "execution_id": clean_text(self.execution_id, limit=220),
        }


@dataclass(frozen=True, slots=True)
class FollowupProviderJobExecutionActionResult:
    record: FollowupProviderJobExecutionConsumptionRecord
    observation: Any


def execute_followup_provider_job_action(
    action: Any,
    *,
    adapter_result_payload: Mapping[str, Any] | None = None,
) -> FollowupProviderJobExecutionActionResult:
    from core.run_kernel import (  # Local import avoids a module import cycle.
        FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE,
        stage=FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED
        ),
    )
    record = build_followup_provider_job_execution_record(
        authorized.inputs,
        adapter_result_payload=adapter_result_payload,
    )
    return FollowupProviderJobExecutionActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=(
                ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED
            ),
            status=RunStageStatus.COMPLETED,
            payload={"followup_execution_state": record.to_dict()},
        ),
    )


def build_followup_provider_job_execution_record(
    action_inputs: Mapping[str, Any],
    *,
    adapter_result_payload: Mapping[str, Any] | None,
) -> FollowupProviderJobExecutionConsumptionRecord:
    inputs = _mapping(safe_json(action_inputs))
    if inputs.get("execution_mode") != FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        raise PermissionError("follow-up provider-job action requires offline mode")
    if inputs.get("provider_job_kind") != FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND:
        raise PermissionError("follow-up provider-job action kind is not allowlisted")
    if not (
        clean_token(inputs.get("authorized_query_ref"), limit=180)
        or clean_text(inputs.get("authorized_query"), limit=300)
    ):
        raise PermissionError("follow-up provider-job action requires authorized query/ref")
    if adapter_result_payload is None:
        raise ValueError("offline provider-job execution requires injected adapter result")

    sanitized = _mapping(safe_json(adapter_result_payload))
    request = FollowupProviderJobExecutionRequest(
        request_id=(
            "followup-provider-job-request:"
            f"{inputs.get('checkpoint_id')}:{inputs.get('sealed_candidate_id')}"
        ),
        run_id=str(inputs.get("run_id") or ""),
        checkpoint_id=str(inputs.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(
            inputs.get("followup_authorization_consumption_id") or ""
        ),
        sealed_candidate_id=str(inputs.get("sealed_candidate_id") or ""),
        provider_job_kind=str(inputs.get("provider_job_kind") or ""),
        component_id=str(inputs.get("component_id") or ""),
        source_obligation_id=str(inputs.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(inputs.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(inputs.get("expected_source_classes"))),
        expected_evidence_ledger_custody_update=_mapping(
            inputs.get("expected_evidence_ledger_custody_update")
        ),
        budget_debit=_mapping(inputs.get("budget_debit")),
        authorized_query_ref=clean_token(inputs.get("authorized_query_ref"), limit=180),
        authorized_query=clean_text(inputs.get("authorized_query"), limit=300),
        execution_mode=FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
    )
    status = _result_status(sanitized, request.expected_source_classes)
    bridge_only = bool(sanitized.get("bridge_only")) or (
        status is FollowupProviderJobExecutionStatus.BRIDGE_ONLY
    )
    if bridge_only:
        status = FollowupProviderJobExecutionStatus.BRIDGE_ONLY
    summary = _candidate_summary(
        sanitized,
        request=request.to_dict(),
        result_status=status.value,
    )
    result = FollowupProviderJobExecutionResult(
        result_id=(
            "followup-provider-job-result:"
            f"{request.checkpoint_id}:{request.sealed_candidate_id}"
        ),
        status=status,
        sanitized_candidate_summary=summary,
        bridge_only=bridge_only,
        adapter_error_code=clean_token(
            sanitized.get("adapter_error_code") or sanitized.get("error_code"),
            limit=120,
        ),
    )
    observation = FollowupProviderJobExecutionObservation(
        observation_id=(
            "followup-provider-job-observation:"
            f"{request.checkpoint_id}:{request.sealed_candidate_id}"
        ),
        request=request,
        result=result,
    )
    return FollowupProviderJobExecutionConsumptionRecord(
        execution_id=(
            "followup-provider-job-execution:"
            f"{request.checkpoint_id}:{request.sealed_candidate_id}"
        ),
        observation=observation,
    )


def _result_status(
    payload: Mapping[str, Any],
    expected_source_classes: tuple[str, ...],
) -> FollowupProviderJobExecutionStatus:
    if bool(payload.get("closed_surface_denied")):
        return FollowupProviderJobExecutionStatus.CLOSED_SURFACE_DENIED
    if bool(payload.get("budget_denied")):
        return FollowupProviderJobExecutionStatus.BUDGET_DENIED
    if bool(payload.get("adapter_error")) or bool(payload.get("error")):
        return FollowupProviderJobExecutionStatus.ADAPTER_ERROR
    if bool(payload.get("bridge_only")):
        return FollowupProviderJobExecutionStatus.BRIDGE_ONLY
    if bool(payload.get("no_result")):
        return FollowupProviderJobExecutionStatus.NO_RESULT
    raw = clean_token(payload.get("result_status"))
    if raw:
        for status in FollowupProviderJobExecutionStatus:
            if raw == status.value:
                return status
    source_class = clean_token(payload.get("source_class"))
    if bool(payload.get("wrong_source_class")) or (
        source_class and source_class not in expected_source_classes
    ):
        return FollowupProviderJobExecutionStatus.WRONG_SOURCE_CLASS
    return FollowupProviderJobExecutionStatus.CANDIDATE_ACQUIRED


def _candidate_summary(
    value: Any,
    *,
    request: Mapping[str, Any],
    result_status: str,
) -> dict[str, Any]:
    source = _mapping(value)
    adapter_result_id = (
        clean_token(source.get("adapter_result_id"), limit=180)
        or clean_token(source.get("retrieval_pass_id"), limit=180)
        or "injected_adapter_result"
    )
    return {
        "adapter_result_id": adapter_result_id,
        "url": clean_text(source.get("url"), limit=500),
        "title": clean_text(source.get("title") or source.get("summary"), limit=300),
        "domain": clean_text(source.get("domain"), limit=160),
        "source_tier": clean_token(source.get("source_tier")),
        "source_class": clean_token(source.get("source_class")) or "unknown",
        "currentness_signal": clean_token(
            source.get("currentness_signal") or source.get("currentness") or "current"
        ),
        "readable_status": clean_token(source.get("readable_status") or "readable"),
        "fetchable_status": clean_token(source.get("fetchable_status") or "fetchable"),
        "provider_name": clean_token(source.get("provider_name") or "offline_adapter"),
        "retrieval_pass_id": clean_token(
            source.get("retrieval_pass_id") or adapter_result_id,
            limit=180,
        ),
        "result_status": clean_token(result_status),
        "bridge_only": bool(source.get("bridge_only")) or result_status == "bridge_only",
        "component_id": request.get("component_id"),
        "source_obligation_id": request.get("source_obligation_id"),
        "requirement_ids": list(request.get("requirement_ids", []) or []),
        "expected_source_classes": list(request.get("expected_source_classes", []) or []),
        "sealed_candidate_id": request.get("sealed_candidate_id"),
        "provider_job_kind": request.get("provider_job_kind"),
        "authorized_query_ref": request.get("authorized_query_ref"),
        "authorized_query": request.get("authorized_query"),
        "eligible_for_stronger_obligation": bool(
            source.get("eligible_for_stronger_obligation")
        ),
        "aggregate_only": bool(source.get("aggregate_only")),
    }


def _execution_gate() -> dict[str, Any]:
    return {
        "allowed_execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
        "provider_job_kind_allowlist": [FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND],
        "provider_execution_licensed": False,
        "provider_execution_available_in_this_phase": False,
        "offline_live_shaped_execution": True,
        "adapter_result_injected_required": True,
        "reason": FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON,
    }


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        "evidence_ledger_mutated": False,
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_updated": False,
        **{name: False for name in FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS},
    }


def _budget_semantics(planned_debit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "planned_debit_authorized": safe_json(planned_debit),
        "offline_provider_job_execution_did_not_incur_live_cost": True,
        "actual_provider_search_fetch_read_cost_incurred": False,
        "actual_provider_account_debited": False,
        "provider_cost_accounting_deferred": True,
    }


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
    ) | {
        "sanitized_candidate_facts_only": True,
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
    "FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND",
    "FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON",
    "FOLLOWUP_PROVIDER_JOB_EXECUTION_SCHEMA_VERSION",
    "FOLLOWUP_PROVIDER_JOB_EXECUTION_TRACE_KEY",
    "FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE",
    "FollowupProviderJobExecutionActionResult",
    "FollowupProviderJobExecutionConsumptionRecord",
    "FollowupProviderJobExecutionObservation",
    "FollowupProviderJobExecutionRequest",
    "FollowupProviderJobExecutionResult",
    "FollowupProviderJobExecutionStatus",
    "build_followup_provider_job_execution_record",
    "execute_followup_provider_job_action",
]
