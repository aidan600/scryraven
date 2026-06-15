"""Runtime consumption seam for AG-96I2A follow-up authorization records.

This module validates passive AG-96I1 checkpoints and converts them into
canonical, non-executable follow-up authorization state. It never calls
providers, search, retrieval, fetch/read, prompts, models, citation formatters,
or provider-job executors.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.followup_deliberation import (
    FollowupDecision,
    FollowupDeliberationCheckpoint,
    FollowupMode,
    ProviderJobKind,
    ReasoningHopType,
    clean_text,
    clean_token,
    safe_json,
    stable_hash,
)
from core.followup_deliberation_validation import (
    validate_followup_deliberation_checkpoint,
)
from core.run_kernel import (
    FOLLOWUP_AUTHORIZATION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)

FOLLOWUP_AUTHORIZATION_SCHEMA_VERSION = "followup_authorization_ag96i2a_v1"
FOLLOWUP_AUTHORIZATION_TRACE_KEY = "followup_authorization_runtime"
FOLLOWUP_EXECUTION_GATE_REASON = "provider_execution_not_licensed_in_ag96i2a"


class FollowupAuthorizationStatus(str, Enum):
    SEALED_NON_EXECUTABLE = "sealed_non_executable"
    DENIED = "denied"
    DENIED_INVALID_CHECKPOINT = "denied_invalid_checkpoint"


@dataclass(frozen=True, slots=True)
class FollowupAuthorizationSeal:
    seal_id: str
    candidate_id: str
    checkpoint_id: str
    run_id: str
    mode: str
    input_checkpoint_hash: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_evidence_ledger_custody_update: Mapping[str, Any]
    budget_debit: Mapping[str, Any]
    fallback_stop_posture: str | None
    fallback_caveat_refuse_posture: str | None
    bridge_only_provider_output: bool = False
    status: FollowupAuthorizationStatus = (
        FollowupAuthorizationStatus.SEALED_NON_EXECUTABLE
    )

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "record_type": "followup_authorization_seal",
                "seal_id": clean_token(self.seal_id),
                "candidate_id": clean_token(self.candidate_id),
                "checkpoint_id": clean_token(self.checkpoint_id),
                "run_id": clean_token(self.run_id),
                "mode": clean_token(self.mode),
                "status": self.status.value,
                "input_checkpoint_hash": self.input_checkpoint_hash,
                "provider_job_kind": clean_token(self.provider_job_kind),
                "component_id": clean_token(self.component_id),
                "source_obligation_id": clean_token(self.source_obligation_id),
                "requirement_ids": [clean_token(item) for item in self.requirement_ids],
                "expected_evidence_ledger_custody_update": safe_json(
                    self.expected_evidence_ledger_custody_update
                ),
                "budget_debit": safe_json(self.budget_debit),
                "budget_semantics": {
                    "planned_debit_preserved": bool(self.budget_debit),
                    "debit_would_apply_in_future_execution_phase": bool(
                        self.budget_debit
                    ),
                    "actual_provider_search_fetch_read_cost_incurred": False,
                    "provider_cost_accounting_added": False,
                },
                "fallback_stop_posture": clean_token(self.fallback_stop_posture),
                "fallback_caveat_refuse_posture": clean_token(
                    self.fallback_caveat_refuse_posture
                ),
                "bridge_only_provider_output": bool(self.bridge_only_provider_output),
                "bridge_only_provider_output_satisfies_final_evidence": False,
                "final_evidence_satisfaction_allowed": False,
                "execution_gate": _execution_gate(),
            }
        )


@dataclass(frozen=True, slots=True)
class FollowupRuntimeConsumptionRecord:
    consumption_id: str
    checkpoint_id: str
    run_id: str
    mode: str
    input_checkpoint_hash: str
    validation_status: str
    validation_errors: tuple[str, ...]
    sealed_candidates: tuple[FollowupAuthorizationSeal, ...]
    denied_candidate_ids: tuple[str, ...]
    consumed_stop_decisions: tuple[Mapping[str, Any], ...]
    consumed_caveat_refuse_decisions: tuple[Mapping[str, Any], ...]
    consumed_budget_decisions: tuple[Mapping[str, Any], ...]
    denied_budget_debits: tuple[Mapping[str, Any], ...]
    reasoning_hops: tuple[Mapping[str, Any], ...]
    micro_hop_validation: tuple[Mapping[str, Any], ...]
    sufficiency_handoff: Mapping[str, Any]
    deep_assumption_audit: Mapping[str, Any] | None
    selected_mode_insufficient: bool
    needs_balanced_or_deep: bool
    needs_deep: bool
    status: FollowupAuthorizationStatus

    def to_dict(self) -> dict[str, Any]:
        sealed = tuple(item.to_dict() for item in self.sealed_candidates)
        return {
            "schema_version": FOLLOWUP_AUTHORIZATION_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_AUTHORIZATION_TRACE_KEY,
            "record_type": "followup_runtime_consumption_record",
            "owner": "RunKernel.FollowupAuthorization",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "consumption_id": clean_token(self.consumption_id),
            "checkpoint_id": clean_token(self.checkpoint_id),
            "run_id": clean_token(self.run_id),
            "mode": clean_token(self.mode),
            "input_checkpoint_hash": self.input_checkpoint_hash,
            "validation": {
                "status": self.validation_status,
                "ok": self.validation_status == "valid",
                "errors": list(self.validation_errors),
            },
            "status": self.status.value,
            "selected_authorization_candidate_ids": [
                item["candidate_id"] for item in sealed
            ],
            "denied_candidate_ids": list(self.denied_candidate_ids),
            "sealed_candidates": list(sealed),
            "sealed_candidate_count": len(sealed),
            "consumed_stop_decisions": [
                safe_json(item) for item in self.consumed_stop_decisions
            ],
            "consumed_caveat_refuse_decisions": [
                safe_json(item) for item in self.consumed_caveat_refuse_decisions
            ],
            "consumed_budget_decisions": [
                _budget_decision_projection(item)
                for item in self.consumed_budget_decisions
            ],
            "denied_budget_debits": [
                safe_json(item) for item in self.denied_budget_debits
            ],
            "budget_semantics": {
                "planned_debits_preserved": [
                    item["budget_debit"] for item in sealed if item.get("budget_debit")
                ],
                "denied_debits_preserved": [
                    safe_json(item) for item in self.denied_budget_debits
                ],
                "actual_provider_search_fetch_read_cost_incurred": False,
                "debits_would_apply_in_future_execution_phase": bool(sealed),
                "provider_cost_accounting_added": False,
            },
            "reasoning_hops": [safe_json(item) for item in self.reasoning_hops],
            "micro_hop_validation": [
                safe_json(item) for item in self.micro_hop_validation
            ],
            "sufficiency_handoff": safe_json(self.sufficiency_handoff),
            "deep_assumption_audit": safe_json(self.deep_assumption_audit),
            "selected_mode_insufficient": bool(self.selected_mode_insufficient),
            "needs_balanced_or_deep": bool(self.needs_balanced_or_deep),
            "needs_deep": bool(self.needs_deep),
            "execution_gate": _execution_gate(),
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": {
                "json_safe": True,
                "provider_payloads_retained": False,
                "prompts_retained": False,
                "model_responses_retained": False,
                "private_records_or_complete_traces_retained": False,
            },
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {FOLLOWUP_AUTHORIZATION_TRACE_KEY: self.to_dict()}


@dataclass(frozen=True, slots=True)
class FollowupAuthorizationConsumptionResult:
    record: FollowupRuntimeConsumptionRecord
    observation: Observation


def consume_followup_deliberation_checkpoint(
    checkpoint: FollowupDeliberationCheckpoint | Mapping[str, Any],
) -> FollowupRuntimeConsumptionRecord:
    payload = _checkpoint_payload(checkpoint)
    checkpoint_id = clean_token(payload.get("checkpoint_id")) or "checkpoint"
    run_id = clean_token(payload.get("run_id")) or "run"
    mode = clean_token(payload.get("mode")) or FollowupMode.BALANCED.value
    checkpoint_hash = stable_hash(payload)
    validation = validate_followup_deliberation_checkpoint(payload)
    records = _mapping(payload.get("records"))

    if not validation.ok:
        candidate_ids = tuple(
            clean_token(item.get("authorization_id")) or "authorization_candidate"
            for item in _mappings(records.get("followup_authorization_candidates"))
        )
        return FollowupRuntimeConsumptionRecord(
            consumption_id=f"followup-auth:{checkpoint_id}:{checkpoint_hash[:12]}",
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            mode=mode,
            input_checkpoint_hash=checkpoint_hash,
            validation_status="invalid",
            validation_errors=validation.errors,
            sealed_candidates=(),
            denied_candidate_ids=tuple(dict.fromkeys(candidate_ids)),
            consumed_stop_decisions=tuple(
                _mappings(records.get("stop_decisions"))
            ),
            consumed_caveat_refuse_decisions=tuple(
                _mappings(records.get("caveat_refuse_decisions"))
            ),
            consumed_budget_decisions=tuple(
                _mappings(records.get("budget_decisions"))
            ),
            denied_budget_debits=_denied_budget_debits(records),
            reasoning_hops=tuple(_mappings(records.get("reasoning_hops"))),
            micro_hop_validation=_micro_hops(records),
            sufficiency_handoff=_mapping(records.get("sufficiency_handoff")),
            deep_assumption_audit=_optional_mapping(
                records.get("deep_assumption_audit")
            ),
            selected_mode_insufficient=_has_decision(
                records, FollowupDecision.SELECTED_MODE_INSUFFICIENT.value
            ),
            needs_balanced_or_deep=_needs_balanced_or_deep(records),
            needs_deep=_has_decision(records, FollowupDecision.NEEDS_DEEP.value),
            status=FollowupAuthorizationStatus.DENIED_INVALID_CHECKPOINT,
        )

    sealed = tuple(
        _seal_candidate(
            candidate,
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            mode=mode,
            checkpoint_hash=checkpoint_hash,
        )
        for candidate in _sealable_candidates(records, mode)
    )
    all_candidate_ids = tuple(
        clean_token(item.get("authorization_id")) or "authorization_candidate"
        for item in _mappings(records.get("followup_authorization_candidates"))
    )
    sealed_ids = {item.candidate_id for item in sealed}
    denied_candidate_ids = tuple(
        candidate_id for candidate_id in all_candidate_ids if candidate_id not in sealed_ids
    )
    return FollowupRuntimeConsumptionRecord(
        consumption_id=f"followup-auth:{checkpoint_id}:{checkpoint_hash[:12]}",
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        mode=mode,
        input_checkpoint_hash=checkpoint_hash,
        validation_status="valid",
        validation_errors=(),
        sealed_candidates=sealed,
        denied_candidate_ids=denied_candidate_ids,
        consumed_stop_decisions=tuple(_mappings(records.get("stop_decisions"))),
        consumed_caveat_refuse_decisions=tuple(
            _mappings(records.get("caveat_refuse_decisions"))
        ),
        consumed_budget_decisions=tuple(_mappings(records.get("budget_decisions"))),
        denied_budget_debits=_denied_budget_debits(records),
        reasoning_hops=tuple(_mappings(records.get("reasoning_hops"))),
        micro_hop_validation=_micro_hops(records),
        sufficiency_handoff=_mapping(records.get("sufficiency_handoff")),
        deep_assumption_audit=_optional_mapping(records.get("deep_assumption_audit")),
        selected_mode_insufficient=_has_decision(
            records, FollowupDecision.SELECTED_MODE_INSUFFICIENT.value
        ),
        needs_balanced_or_deep=_needs_balanced_or_deep(records),
        needs_deep=_has_decision(records, FollowupDecision.NEEDS_DEEP.value),
        status=(
            FollowupAuthorizationStatus.SEALED_NON_EXECUTABLE
            if sealed
            else FollowupAuthorizationStatus.DENIED
        ),
    )


def execute_followup_authorization_consumption_action(
    action: AuthorizedAction,
    *,
    checkpoint: FollowupDeliberationCheckpoint | Mapping[str, Any],
) -> FollowupAuthorizationConsumptionResult:
    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_AUTHORIZATION_CONSUME,
        stage=FOLLOWUP_AUTHORIZATION_STAGE,
        expected_observation_type=ObservationType.FOLLOWUP_AUTHORIZATION_CONSUMED,
    )
    record = consume_followup_deliberation_checkpoint(checkpoint)
    return FollowupAuthorizationConsumptionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_AUTHORIZATION_CONSUMED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_authorization_state": record.to_dict()},
        ),
    )


def request_followup_provider_execution(
    record: FollowupRuntimeConsumptionRecord | Mapping[str, Any],
    *,
    candidate_id: str,
) -> None:
    _ = record
    candidate = clean_token(candidate_id) or "candidate"
    raise PermissionError(
        f"{candidate}: {FOLLOWUP_EXECUTION_GATE_REASON}"
    )


def _checkpoint_payload(
    checkpoint: FollowupDeliberationCheckpoint | Mapping[str, Any],
) -> dict[str, Any]:
    payload = checkpoint.to_dict() if hasattr(checkpoint, "to_dict") else checkpoint
    safe = safe_json(payload)
    return dict(safe) if isinstance(safe, Mapping) else {}


def _sealable_candidates(
    records: Mapping[str, Any],
    mode: str,
) -> tuple[Mapping[str, Any], ...]:
    if mode == FollowupMode.FAST.value:
        return ()
    candidates = []
    for candidate in _mappings(records.get("followup_authorization_candidates")):
        hop_type = clean_token(candidate.get("hop_type"))
        job_kind = clean_token(candidate.get("provider_job_kind"))
        decision = clean_token(candidate.get("decision"))
        if decision != FollowupDecision.AUTHORIZE_CANDIDATE.value:
            continue
        if mode == FollowupMode.BALANCED.value:
            if hop_type != ReasoningHopType.MESO_TARGETED_REPAIR.value:
                continue
            if job_kind == ProviderJobKind.RECONCILIATION_SUPPORT.value:
                continue
        if mode == FollowupMode.DEEP.value:
            if hop_type not in {
                ReasoningHopType.MESO_TARGETED_REPAIR.value,
                ReasoningHopType.MACRO_RUN_DIAGNOSIS.value,
            }:
                continue
        candidates.append(candidate)
    return tuple(candidates)


def _seal_candidate(
    candidate: Mapping[str, Any],
    *,
    checkpoint_id: str,
    run_id: str,
    mode: str,
    checkpoint_hash: str,
) -> FollowupAuthorizationSeal:
    candidate_id = clean_token(candidate.get("authorization_id")) or "candidate"
    return FollowupAuthorizationSeal(
        seal_id=f"seal:{checkpoint_id}:{candidate_id}",
        candidate_id=candidate_id,
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        mode=mode,
        input_checkpoint_hash=checkpoint_hash,
        provider_job_kind=clean_token(candidate.get("provider_job_kind"))
        or "provider_job",
        component_id=clean_token(candidate.get("component_id")) or "component",
        source_obligation_id=clean_token(candidate.get("source_obligation_id"))
        or "source_obligation",
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
    )


def _budget_decision_projection(decision: Mapping[str, Any]) -> dict[str, Any]:
    decision_value = clean_token(decision.get("decision"))
    return {
        "budget_decision_id": clean_token(decision.get("budget_decision_id")),
        "decision": decision_value,
        "planned_or_denied_debit": safe_json(decision.get("debit") or {}),
        "budget_before": safe_json(decision.get("budget_before") or {}),
        "budget_after": safe_json(decision.get("budget_after") or {}),
        "debit_authorized_for_future_phase": (
            decision_value == FollowupDecision.AUTHORIZE_CANDIDATE.value
        ),
        "actual_provider_search_fetch_read_cost_incurred": False,
        "reason": clean_text(decision.get("reason"), limit=300),
    }


def _denied_budget_debits(records: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    denied = []
    for decision in _mappings(records.get("budget_decisions")):
        if clean_token(decision.get("decision")) != FollowupDecision.AUTHORIZE_CANDIDATE.value:
            denied.append(
                {
                    "budget_decision_id": clean_token(
                        decision.get("budget_decision_id")
                    ),
                    "decision": clean_token(decision.get("decision")),
                    "denied_debit": safe_json(decision.get("debit") or {}),
                    "reason": clean_text(decision.get("reason"), limit=300),
                    "actual_provider_search_fetch_read_cost_incurred": False,
                }
            )
    return tuple(denied)


def _micro_hops(records: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        item
        for item in _mappings(records.get("reasoning_hops"))
        if clean_token(item.get("hop_type")) == ReasoningHopType.MICRO_VERIFICATION.value
    )


def _has_decision(records: Mapping[str, Any], decision: str) -> bool:
    for key in (
        "budget_decisions",
        "stop_decisions",
        "caveat_refuse_decisions",
        "followup_recommendations",
    ):
        if any(clean_token(item.get("decision")) == decision for item in _mappings(records.get(key))):
            return True
    return False


def _needs_balanced_or_deep(records: Mapping[str, Any]) -> bool:
    if _has_decision(records, FollowupDecision.SELECTED_MODE_INSUFFICIENT.value):
        return True
    return any(
        clean_token(item.get("final_answer_posture")) == "needs_balanced_or_deep"
        for item in _mappings(records.get("stop_decisions"))
    )


def _execution_gate() -> dict[str, Any]:
    return {
        "execution_permission": False,
        "executable_in_current_phase": False,
        "provider_execution_licensed": False,
        "reason": FOLLOWUP_EXECUTION_GATE_REASON,
    }


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        "provider_search_behavior_changed": False,
        "provider_selected": False,
        "search_executed": False,
        "retrieval_executed": False,
        "fetch_executed": False,
        "model_called": False,
        "provider_job_scheduled": False,
        "provider_job_dispatched": False,
        "query_generation_changed": False,
        "retrieval_ranking_filtering_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "author_prose_behavior_changed": False,
        "final_answer_behavior_changed": False,
        "pipeline_orchestrator_domain_logic_changed": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _optional_mapping(value: Any) -> Mapping[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None or isinstance(value, str | bytes):
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _strings(value: Any) -> tuple[str, ...]:
    if value is None or isinstance(value, str):
        values = (value,) if value else ()
    elif isinstance(value, Sequence):
        values = tuple(value)
    else:
        values = (value,)
    out = []
    for item in values:
        token = clean_token(item)
        if token and token not in out:
            out.append(token)
    return tuple(out)


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, [], {})}


__all__ = [
    "FOLLOWUP_AUTHORIZATION_SCHEMA_VERSION",
    "FOLLOWUP_AUTHORIZATION_TRACE_KEY",
    "FOLLOWUP_EXECUTION_GATE_REASON",
    "FollowupAuthorizationConsumptionResult",
    "FollowupAuthorizationSeal",
    "FollowupAuthorizationStatus",
    "FollowupRuntimeConsumptionRecord",
    "consume_followup_deliberation_checkpoint",
    "execute_followup_authorization_consumption_action",
    "request_followup_provider_execution",
]
