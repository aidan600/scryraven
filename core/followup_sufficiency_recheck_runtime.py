"""Offline follow-up SufficiencyJudgment recheck seam for AG-96I2D/AG-96I3A.

This module derives a conservative SufficiencyJudgment recheck from canonical
follow-up EvidenceLedger intake state and the current EvidenceLedger projection.
It never calls providers, search, retrieval, fetch/read, prompts, models,
citation formatters, provider-job executors, shell processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Mapping, Sequence

from core.followup_deliberation import clean_text, clean_token, safe_json, stable_hash
from core.followup_fixture_boundaries import (
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    followup_common_redaction_posture,
    followup_fixture_provenance,
    followup_live_surface_flags,
)
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
)
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgmentInput,
    SufficiencyJudgmentMode,
    SufficiencyPosture,
)
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)

FOLLOWUP_SUFFICIENCY_RECHECK_SCHEMA_VERSION = (
    "followup_sufficiency_recheck_ag96i2d_v1"
)
FOLLOWUP_SUFFICIENCY_RECHECK_TRACE_KEY = "followup_sufficiency_recheck_runtime"
FOLLOWUP_SUFFICIENCY_RECHECK_STAGE = "followup_sufficiency_recheck"
FOLLOWUP_SUFFICIENCY_RECHECK_MODE = "fixture_only_followup_sufficiency_recheck"
FOLLOWUP_SUFFICIENCY_RECHECK_GATE_REASON = (
    "ag96i2d_fixture_only_sufficiency_recheck"
)
AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE = (
    "ag96i3m2_admission_review_followup_intake"
)


class FollowupSufficiencyRequirementStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"


class FollowupSufficiencyPosture(str, Enum):
    READY_FOR_NEXT_FIXTURE_PHASE = "ready_for_next_fixture_phase"
    ANSWER_WITH_CAVEATS = "answer_with_caveats"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFUSE_OR_BLOCK = "refuse_or_block"
    NEEDS_DEEP = "needs_deep"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    SOURCE_BOUND_UNKNOWN = "source_bound_unknown"


@dataclass(frozen=True, slots=True)
class FollowupSufficiencyRecheckRequest:
    request_id: str
    run_id: str
    checkpoint_id: str
    followup_authorization_consumption_id: str
    sealed_candidate_id: str
    followup_execution_id: str
    execution_id: str
    followup_execution_observation_id: str
    followup_evidence_intake_id: str
    intake_id: str
    followup_evidence_intake_observation_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    result_status: str
    bridge_only: bool
    fixture_execution_mode: str
    execution_mode: str
    evidence_ledger_intake_mode: str
    evidence_ledger_projection_digest: str
    evidence_ledger_custody_summary: Mapping[str, Any]
    evidence_ledger_observation_id: str
    evidence_ledger_counts: Mapping[str, Any]
    source_requirement_statuses: tuple[Mapping[str, Any], ...]
    custody_gaps: tuple[Mapping[str, Any], ...]
    official_current_custody_status: Mapping[str, Any]
    ag96i3m2_admission_review_candidate: Mapping[str, Any]
    ag96i3m2_evidence_ledger_intake_binding: Mapping[str, Any]
    provider_execution_licensed: bool
    sufficiency_recheck_mode: str
    final_answer_packet_deferred: bool
    author_activation_allowed: bool
    citation_behavior_changed: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_SUFFICIENCY_RECHECK_SCHEMA_VERSION,
            "record_type": "followup_sufficiency_recheck_request",
            "request_id": clean_text(self.request_id, limit=220),
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
            "followup_evidence_intake_id": clean_text(
                self.followup_evidence_intake_id,
                limit=220,
            ),
            "intake_id": clean_text(self.intake_id, limit=220),
            "followup_evidence_intake_observation_id": clean_text(
                self.followup_evidence_intake_observation_id,
                limit=220,
            ),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [clean_token(item) for item in self.requirement_ids],
            "expected_source_classes": [
                clean_token(item) for item in self.expected_source_classes
            ],
            "result_status": clean_token(self.result_status),
            "bridge_only": bool(self.bridge_only),
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "execution_mode": clean_token(self.execution_mode),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "evidence_ledger_projection_digest": clean_text(
                self.evidence_ledger_projection_digest,
                limit=120,
            ),
            "evidence_ledger_custody_summary": safe_json(
                self.evidence_ledger_custody_summary
            ),
            "evidence_ledger_observation_id": clean_text(
                self.evidence_ledger_observation_id,
                limit=220,
            ),
            "evidence_ledger_counts": safe_json(self.evidence_ledger_counts),
            "source_requirement_statuses": [
                safe_json(item) for item in self.source_requirement_statuses
            ],
            "custody_gaps": [safe_json(item) for item in self.custody_gaps],
            "official_current_custody_status": safe_json(
                self.official_current_custody_status
            ),
            "ag96i3m2_admission_review_candidate": safe_json(
                self.ag96i3m2_admission_review_candidate
            ),
            "ag96i3m2_evidence_ledger_intake_binding": safe_json(
                self.ag96i3m2_evidence_ledger_intake_binding
            ),
            "fixture_only_provenance": _fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "sufficiency_recheck_mode": clean_token(self.sufficiency_recheck_mode),
            "final_answer_packet_deferred": bool(
                self.final_answer_packet_deferred
            ),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "citation_behavior_changed": bool(self.citation_behavior_changed),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupSufficiencyRecheckResult:
    result_id: str
    status: str
    fixture_sufficiency_posture: str
    source_requirement_status_summary: Mapping[str, Any]
    sufficiency_judgment_projection: Mapping[str, Any]
    sufficiency_judgment_ref: Mapping[str, Any]
    final_answer_packet_deferred: bool
    author_activation_allowed: bool
    citation_behavior_changed: bool
    citation_eligible: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_SUFFICIENCY_RECHECK_SCHEMA_VERSION,
            "record_type": "followup_sufficiency_recheck_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "fixture_sufficiency_posture": clean_token(
                self.fixture_sufficiency_posture
            ),
            "source_requirement_status_summary": safe_json(
                self.source_requirement_status_summary
            ),
            "sufficiency_judgment_projection": safe_json(
                self.sufficiency_judgment_projection
            ),
            "sufficiency_judgment_ref": safe_json(self.sufficiency_judgment_ref),
            "final_answer_packet_deferred": bool(
                self.final_answer_packet_deferred
            ),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "citation_behavior_changed": bool(self.citation_behavior_changed),
            "citation_eligible": bool(self.citation_eligible),
            "live_validation_not_run": bool(self.live_validation_not_run),
        }


@dataclass(frozen=True, slots=True)
class FollowupSufficiencyRecheckObservation:
    observation_id: str
    request: FollowupSufficiencyRecheckRequest
    result: FollowupSufficiencyRecheckResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        return {
            "schema_version": FOLLOWUP_SUFFICIENCY_RECHECK_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_SUFFICIENCY_RECHECK_TRACE_KEY,
            "record_type": "followup_sufficiency_recheck_observation",
            "owner": "FollowupSufficiencyRecheckRuntime",
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
            "followup_evidence_intake_id": request.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": request.get("intake_id"),
            "followup_evidence_intake_observation_id": request.get(
                "followup_evidence_intake_observation_id"
            ),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "result_status": request.get("result_status"),
            "bridge_only": request.get("bridge_only"),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "execution_mode": request.get("execution_mode"),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "evidence_ledger_projection_digest": request.get(
                "evidence_ledger_projection_digest"
            ),
            "evidence_ledger_custody_summary": request.get(
                "evidence_ledger_custody_summary",
                {},
            ),
            "evidence_ledger_observation_id": request.get(
                "evidence_ledger_observation_id"
            ),
            "evidence_ledger_counts": request.get("evidence_ledger_counts", {}),
            "source_requirement_statuses": request.get(
                "source_requirement_statuses",
                [],
            ),
            "custody_gaps": request.get("custody_gaps", []),
            "official_current_custody_status": request.get(
                "official_current_custody_status",
                {},
            ),
            "ag96i3m2_admission_review_candidate": request.get(
                "ag96i3m2_admission_review_candidate",
                {},
            ),
            "ag96i3m2_evidence_ledger_intake_binding": request.get(
                "ag96i3m2_evidence_ledger_intake_binding",
                {},
            ),
            "fixture_only_provenance": request.get("fixture_only_provenance", {}),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "sufficiency_recheck_mode": request.get("sufficiency_recheck_mode"),
            "request": request,
            "result": result,
            "recheck_status": result.get("status"),
            "fixture_sufficiency_posture": result.get(
                "fixture_sufficiency_posture"
            ),
            "source_requirement_status_summary": result.get(
                "source_requirement_status_summary",
                {},
            ),
            "sufficiency_judgment_projection": result.get(
                "sufficiency_judgment_projection",
                {},
            ),
            "sufficiency_judgment_ref": result.get("sufficiency_judgment_ref", {}),
            "final_answer_packet_deferred": result.get(
                "final_answer_packet_deferred"
            ),
            "author_activation_allowed": result.get("author_activation_allowed"),
            "citation_behavior_changed": result.get("citation_behavior_changed"),
            "citation_eligible": result.get("citation_eligible"),
            "live_validation_not_run": result.get("live_validation_not_run"),
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupSufficiencyRecheckConsumptionRecord:
    recheck_id: str
    observation: FollowupSufficiencyRecheckObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_sufficiency_recheck_consumption_record",
            "owner": "FollowupSufficiencyRecheckRuntime",
            "canonical_state": False,
            "recheck_id": clean_text(self.recheck_id, limit=220),
        }


@dataclass(frozen=True, slots=True)
class FollowupSufficiencyRecheckActionResult:
    record: FollowupSufficiencyRecheckConsumptionRecord
    observation: Any


def execute_followup_sufficiency_recheck_action(
    action: Any,
    *,
    followup_evidence_intake_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    prior_sufficiency_judgment_projection: Mapping[str, Any] | None = None,
    sufficiency_handoff: Mapping[str, Any] | None = None,
) -> FollowupSufficiencyRecheckActionResult:
    """Execute the fixture-only recheck adapter for one authorized action."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_SUFFICIENCY_RECHECK,
        stage=FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_SUFFICIENCY_RECHECK_OBSERVED
        ),
    )
    record = build_followup_sufficiency_recheck_record(
        action_inputs=authorized.inputs,
        followup_evidence_intake_state=followup_evidence_intake_state,
        evidence_ledger_projection=evidence_ledger_projection,
        prior_sufficiency_judgment_projection=prior_sufficiency_judgment_projection,
        sufficiency_handoff=sufficiency_handoff,
    )
    return FollowupSufficiencyRecheckActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_SUFFICIENCY_RECHECK_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_sufficiency_recheck_state": record.to_dict()},
        ),
    )


def build_followup_sufficiency_recheck_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    prior_sufficiency_judgment_projection: Mapping[str, Any] | None = None,
    sufficiency_handoff: Mapping[str, Any] | None = None,
) -> FollowupSufficiencyRecheckConsumptionRecord:
    action = _mapping(action_inputs)
    intake = _mapping(safe_json(followup_evidence_intake_state))
    ledger = _mapping(safe_json(evidence_ledger_projection))
    prior = _mapping(safe_json(prior_sufficiency_judgment_projection))
    handoff = _mapping(safe_json(sufficiency_handoff))
    _validate_intake_state(intake)
    _validate_ledger_projection(ledger)
    _validate_action_inputs(action, intake, ledger)

    statuses = _source_requirement_statuses(
        ledger,
        requirement_ids=_strings(action.get("requirement_ids")),
        source_obligation_id=action.get("source_obligation_id"),
    )
    if _ag96i3m2_source_obligation_unsatisfied(intake):
        statuses = _unsatisfied_source_requirement_statuses(
            action_inputs=action,
            statuses=statuses,
        )
    custody_gaps = tuple(
        _mapping(item)
        for item in _list(ledger.get("custody_gaps"))
        if isinstance(item, Mapping)
    )
    custody_summary = evidence_ledger_custody_summary(ledger)
    digest = evidence_ledger_projection_digest(ledger)
    m2_summary = _ag96i3m2_recheck_summary(
        intake_state=intake,
        evidence_ledger_projection=ledger,
        source_requirement_statuses=statuses,
    )
    judgment_input = _build_sufficiency_input(
        action_inputs=action,
        ledger_projection=ledger,
        source_requirement_statuses=statuses,
        prior_sufficiency_judgment_projection=prior,
        sufficiency_handoff=handoff,
    )
    judgment = build_deterministic_sufficiency_judgment(judgment_input)
    mandatory = tuple(
        dict.fromkeys(
            tuple(judgment.mandatory_caveats)
            + tuple(_strings(prior.get("mandatory_caveats")))
            + tuple(_strings(handoff.get("mandatory_caveats")))
            + ("fixture_only_sufficiency_recheck_final_answer_deferred",)
        )
    )
    prohibited = tuple(
        dict.fromkeys(
            tuple(judgment.prohibited_upgrades)
            + tuple(_strings(prior.get("prohibited_upgrades")))
            + tuple(_strings(handoff.get("prohibited_upgrades")))
            + (
                "do_not_convert_fixture_only_sufficiency_to_product_answer_readiness",
                "do_not_treat_bridge_only_followup_intake_as_sufficient",
            )
        )
    )
    final_packet_inputs = dict(judgment.final_packet_inputs)
    final_packet_inputs["readiness_status"] = (
        "fixture_sufficiency_rechecked_final_answer_deferred"
    )
    final_packet_inputs["final_answer_packet_deferred"] = True
    final_packet_inputs["author_activation_allowed"] = False
    final_packet_inputs["citation_behavior_changed"] = False
    final_packet_inputs["live_validation_not_run"] = True
    flags = _mapping(final_packet_inputs.get("behavior_boundary_flags"))
    final_packet_inputs["behavior_boundary_flags"] = {
        **flags,
        **_behavior_boundary_flags(),
    }
    judgment = replace(
        judgment,
        mode=SufficiencyJudgmentMode.DETERMINISTIC,
        final_answer_allowed=False,
        mandatory_caveats=mandatory,
        prohibited_upgrades=prohibited,
        final_packet_inputs=final_packet_inputs,
    )
    judgment_projection = judgment.to_projection()
    if _source_bound_recheck_without_resolution(action):
        unknowns = list(judgment_projection.get("source_bound_numeric_unknowns") or [])
        if not unknowns:
            unknowns.append(
                {
                    "requirement_id": _ledger_requirement_id(action),
                    "source_class": "sourced_numeric_values",
                    "reason": "fixture_only_source_bound_numeric_resolution_deferred",
                }
            )
        judgment_projection["source_bound_numeric_unknowns"] = unknowns
        judgment_projection["decision"] = (
            RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN.value
        )
        judgment_projection["final_answer_posture"] = (
            SufficiencyPosture.PARTIAL_ANSWER.value
        )
        judgment_projection["contract_fulfilled"] = False
        judgment_projection["required_obligations_satisfied"] = False
        judgment_projection["mandatory_caveats"] = list(
            dict.fromkeys(
                list(judgment_projection.get("mandatory_caveats") or [])
                + ["missing_source_bound_numeric_value_remains_unknown"]
            )
        )
        judgment_projection["prohibited_upgrades"] = list(
            dict.fromkeys(
                list(judgment_projection.get("prohibited_upgrades") or [])
                + ["do_not_present_source_bound_numeric_unknown_as_known"]
            )
        )
        judgment_projection["readiness_reasons"] = list(
            dict.fromkeys(
                list(judgment_projection.get("readiness_reasons") or [])
                + ["source_bound_numeric_unknown"]
            )
        )
        packet_inputs = _mapping(judgment_projection.get("final_packet_inputs"))
        packet_inputs["decision"] = (
            RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN.value
        )
        packet_inputs["final_answer_posture"] = SufficiencyPosture.PARTIAL_ANSWER.value
        packet_inputs["required_obligations_satisfied"] = False
        packet_inputs["source_bound_numeric_unknowns"] = unknowns
        packet_inputs["readiness_reasons"] = list(
            dict.fromkeys(
                list(packet_inputs.get("readiness_reasons") or [])
                + ["source_bound_numeric_unknown"]
            )
        )
        packet_inputs["claim_postures"] = list(
            dict.fromkeys(
                list(packet_inputs.get("claim_postures") or [])
                + ["insufficient_evidence"]
            )
        )
        judgment_projection["final_packet_inputs"] = packet_inputs
    judgment_projection["validation"] = {
        "status": "valid",
        "model_attempted": False,
        "deterministic_decision": judgment_projection.get("decision"),
        "recheck_mode": FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    }
    judgment_projection["final_answer_packet_deferred"] = True
    judgment_projection["author_activation_allowed"] = False
    judgment_projection["citation_behavior_changed"] = False
    judgment_projection["live_validation_not_run"] = True

    request = FollowupSufficiencyRecheckRequest(
        request_id=f"followup-sufficiency-recheck-request:{action.get('intake_id')}",
        run_id=str(action.get("run_id") or intake.get("run_id") or ""),
        checkpoint_id=str(action.get("checkpoint_id") or intake.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(
            action.get("followup_authorization_consumption_id") or ""
        ),
        sealed_candidate_id=str(action.get("sealed_candidate_id") or ""),
        followup_execution_id=str(action.get("followup_execution_id") or ""),
        execution_id=str(action.get("execution_id") or ""),
        followup_execution_observation_id=str(
            action.get("followup_execution_observation_id") or ""
        ),
        followup_evidence_intake_id=str(
            action.get("followup_evidence_intake_id") or ""
        ),
        intake_id=str(action.get("intake_id") or ""),
        followup_evidence_intake_observation_id=str(
            action.get("followup_evidence_intake_observation_id") or ""
        ),
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        result_status=str(action.get("result_status") or ""),
        bridge_only=bool(action.get("bridge_only")),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        execution_mode=str(
            action.get("execution_mode")
            or action.get("fixture_execution_mode")
            or ""
        ),
        evidence_ledger_intake_mode=str(
            action.get("evidence_ledger_intake_mode") or ""
        ),
        evidence_ledger_projection_digest=digest,
        evidence_ledger_custody_summary=custody_summary,
        evidence_ledger_observation_id=str(
            m2_summary.get("evidence_ledger_observation_id") or ""
        ),
        evidence_ledger_counts=_mapping(m2_summary.get("evidence_ledger_counts")),
        source_requirement_statuses=statuses,
        custody_gaps=custody_gaps,
        official_current_custody_status=_mapping(
            m2_summary.get("official_current_custody_status")
        ),
        ag96i3m2_admission_review_candidate=_mapping(
            m2_summary.get("ag96i3m2_admission_review_candidate")
        ),
        ag96i3m2_evidence_ledger_intake_binding=_mapping(
            m2_summary.get("ag96i3m2_evidence_ledger_intake_binding")
        ),
        provider_execution_licensed=False,
        sufficiency_recheck_mode=FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
        final_answer_packet_deferred=True,
        author_activation_allowed=False,
        citation_behavior_changed=False,
        live_validation_not_run=True,
    )
    posture = _fixture_sufficiency_posture(
        action_inputs=action,
        judgment_projection=judgment_projection,
        source_requirement_statuses=statuses,
        prior_sufficiency_judgment_projection=prior,
    )
    result = FollowupSufficiencyRecheckResult(
        result_id=f"followup-sufficiency-recheck-result:{action.get('intake_id')}",
        status="fixture_recheck_completed",
        fixture_sufficiency_posture=posture,
        source_requirement_status_summary=_status_summary(statuses),
        sufficiency_judgment_projection=judgment_projection,
        sufficiency_judgment_ref=_sufficiency_ref(judgment_projection),
        final_answer_packet_deferred=True,
        author_activation_allowed=False,
        citation_behavior_changed=False,
        citation_eligible=False,
        live_validation_not_run=True,
    )
    observation = FollowupSufficiencyRecheckObservation(
        observation_id=f"followup-sufficiency-recheck-observation:{action.get('intake_id')}",
        request=request,
        result=result,
    )
    return FollowupSufficiencyRecheckConsumptionRecord(
        recheck_id=f"followup-sufficiency-recheck:{action.get('intake_id')}",
        observation=observation,
    )


def evidence_ledger_projection_digest(
    evidence_ledger_projection: Mapping[str, Any],
) -> str:
    return stable_hash(safe_json(evidence_ledger_projection))


def evidence_ledger_custody_summary(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    ledger = _mapping(evidence_ledger_projection)
    statuses = _source_requirement_statuses(ledger)
    return {
        "owner": ledger.get("owner"),
        "canonical_state": ledger.get("canonical_state"),
        "candidate_count": ledger.get("candidate_count", 0),
        "requirement_count": ledger.get("requirement_count", 0),
        "custody_record_count": ledger.get("custody_record_count", 0),
        "source_requirement_statuses": [safe_json(item) for item in statuses],
        "custody_gap_count": len(_list(ledger.get("custody_gaps"))),
        "custody_gap_types": list(
            dict.fromkeys(
                clean_token(_mapping(item).get("gap_type"))
                for item in _list(ledger.get("custody_gaps"))
                if isinstance(item, Mapping)
            )
        ),
        "observation_ref_count": len(_list(ledger.get("observation_refs"))),
    }


def _build_sufficiency_input(
    *,
    action_inputs: Mapping[str, Any],
    ledger_projection: Mapping[str, Any],
    source_requirement_statuses: Sequence[Mapping[str, Any]],
    prior_sufficiency_judgment_projection: Mapping[str, Any],
    sufficiency_handoff: Mapping[str, Any],
) -> RunSufficiencyJudgmentInput:
    required_source_class = _required_source_class(
        _strings(action_inputs.get("expected_source_classes")),
        provider_job_kind=action_inputs.get("provider_job_kind"),
    )
    contract_requirement = {
        "requirement_id": _ledger_requirement_id(action_inputs),
        "requirement_kind": _requirement_kind(required_source_class),
        "required_source_class": required_source_class,
        "required_source_tier": _required_source_tier(required_source_class),
        "required_currentness": "current",
        "strictness": "required",
        "component_id": action_inputs.get("component_id"),
        "source_obligation_id": action_inputs.get("source_obligation_id"),
        "origin_ref": f"followup_evidence_intake:{action_inputs.get('intake_id')}",
    }
    mandatory = tuple(
        dict.fromkeys(
            tuple(_strings(prior_sufficiency_judgment_projection.get("mandatory_caveats")))
            + tuple(_strings(sufficiency_handoff.get("mandatory_caveats")))
            + tuple(_strings(sufficiency_handoff.get("required_caveats")))
        )
    )
    prohibited = tuple(
        dict.fromkeys(
            tuple(_strings(prior_sufficiency_judgment_projection.get("prohibited_upgrades")))
            + tuple(_strings(sufficiency_handoff.get("prohibited_upgrades")))
            + tuple(_strings(sufficiency_handoff.get("prohibited_upgrades_preserved")))
        )
    )
    contract_projection = {
        "schema_version": FOLLOWUP_SUFFICIENCY_RECHECK_SCHEMA_VERSION,
        "owner": "RunKernel.FollowupSufficiencyRecheck",
        "canonical_state": True,
        "contract_id": f"followup-sufficiency-contract:{action_inputs.get('intake_id')}",
        "selected_template_ids": ["ag96i2d_followup_fixture_sufficiency_recheck"],
        "source_requirements": [contract_requirement],
        "final_posture_policy": {
            "partial_allowed_if": ["fixture_only_final_answer_deferred"],
            "mandatory_caveats": list(mandatory),
            "prohibited_upgrades": list(prohibited),
        },
    }
    answer_contract_projection = {}
    if any(
        _mapping(item).get("status")
        in {
            FollowupSufficiencyRequirementStatus.UNKNOWN.value,
            FollowupSufficiencyRequirementStatus.UNSATISFIED.value,
        }
        and _mapping(item).get("required_source_class") == "sourced_numeric_values"
        for item in source_requirement_statuses
    ):
        answer_contract_projection = {
            "source_bound_numeric_unknowns": ["sourced_numeric_values"]
        }
    conflict_facts = {}
    unresolved_conflicts = _strings(
        prior_sufficiency_judgment_projection.get("unresolved_conflicts")
    )
    if unresolved_conflicts:
        conflict_facts = {
            "conflicts_present": True,
            "conflict_posture": "unresolved",
            "unresolved_central_conflict": True,
        }
    return RunSufficiencyJudgmentInput(
        contract_projection=contract_projection,
        evidence_ledger_projection=ledger_projection,
        search_judgment_projection={"decision": "defer_to_legacy_compatibility"},
        search_judgment_history=(),
        answer_contract_projection=answer_contract_projection,
        source_obligation_projection=ledger_projection,
        final_evidence_facts={
            "final_evidence_count": 0,
            "author_evidence_count": 0,
            "citation_eligible_candidate_count": 0,
        },
        conflict_facts=conflict_facts,
        indirect_inference_facts={},
        weak_failure_facts={
            "corpus_weak": True,
            "weak_corpus_reason": "fixture_only_followup_recheck_final_answer_deferred",
        },
        budget={"iteration": 0, "max_iterations": 1, "budget_exhausted": False},
    )


def _validate_intake_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError("follow-up sufficiency recheck requires canonical intake state")
    if state.get("owner") != "RunKernel.FollowupEvidenceIntake":
        raise PermissionError("follow-up sufficiency recheck requires RunKernel intake state")
    execution_mode = (
        clean_token(state.get("execution_mode"))
        or clean_token(state.get("fixture_execution_mode"))
    )
    if execution_mode not in {"fixture_only", FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE}:
        raise PermissionError("follow-up sufficiency recheck requires known execution")
    intake_mode = clean_token(state.get("evidence_ledger_intake_mode"))
    if intake_mode == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE:
        _validate_ag96i3m2_intake_state(state)
    elif execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        if intake_mode != "bounded_provider_job_offline_followup_intake":
            raise PermissionError(
                "follow-up sufficiency recheck requires offline provider-job intake"
            )
    elif intake_mode != "fixture_only_followup_intake":
        raise PermissionError("follow-up sufficiency recheck requires fixture-only intake")
    if state.get("provider_execution_licensed") is not False:
        raise PermissionError("provider execution is not licensed for sufficiency recheck")
    if state.get("final_evidence_satisfied") is not False:
        raise PermissionError("follow-up sufficiency recheck cannot consume final evidence satisfaction")
    if state.get("citation_eligible") is not False:
        raise PermissionError("follow-up sufficiency recheck cannot consume citation eligibility")
    if state.get("author_activation_allowed", False) is not False:
        raise PermissionError("follow-up sufficiency recheck cannot activate Author")
    if state.get("final_answer_packet_updated", False) is not False:
        raise PermissionError("follow-up sufficiency recheck cannot consume FinalAnswerPacket updates")
    if state.get("sufficiency_judgment_recheck_deferred", True) is not True:
        raise PermissionError("follow-up sufficiency recheck requires deferred SufficiencyJudgment")
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
        "search_judgment_rerun",
        "final_answer_packet_updated",
        "final_answer_behavior_changed",
        "author_prose_behavior_changed",
        "citation_behavior_changed",
        "pipeline_orchestrator_domain_logic_changed",
    ):
        if flags.get(flag) is not False:
            raise PermissionError(f"follow-up sufficiency recheck requires {flag}=False")


def _validate_ledger_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("owner") != "RunKernel.EvidenceLedger":
        raise PermissionError("follow-up sufficiency recheck requires EvidenceLedger owner")
    if projection.get("canonical_state") is not True:
        raise PermissionError("follow-up sufficiency recheck requires canonical EvidenceLedger")
    if projection.get("trace_only") is not False:
        raise PermissionError("EvidenceLedger projection must not be trace-only")
    if int(projection.get("requirement_count") or 0) <= 0:
        raise PermissionError("follow-up sufficiency recheck requires source requirements")


def _validate_action_inputs(
    action_inputs: Mapping[str, Any],
    intake_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
) -> None:
    for field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
        "execution_mode",
        "evidence_ledger_intake_mode",
    ):
        if action_inputs.get(field) != intake_state.get(field):
            raise PermissionError(f"authorized sufficiency recheck {field} mismatch")
    if (
        action_inputs.get("execution_mode") == "fixture_only"
        and action_inputs.get("fixture_execution_mode")
        != intake_state.get("fixture_execution_mode")
    ):
        raise PermissionError("authorized sufficiency recheck fixture_execution_mode mismatch")
    for action_field, state_field in (
        ("followup_evidence_intake_id", "intake_id"),
        ("intake_id", "intake_id"),
        ("followup_evidence_intake_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != intake_state.get(state_field):
            raise PermissionError(
                f"authorized sufficiency recheck {action_field} mismatch"
            )
    if _strings(action_inputs.get("requirement_ids")) != _strings(
        intake_state.get("requirement_ids")
    ):
        raise PermissionError("authorized sufficiency recheck requirement_ids mismatch")
    if _strings(action_inputs.get("expected_source_classes")) != _strings(
        intake_state.get("expected_source_classes")
    ):
        raise PermissionError(
            "authorized sufficiency recheck expected_source_classes mismatch"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("sufficiency recheck must keep provider unlicensed")
    if action_inputs.get("sufficiency_recheck_mode") != (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    ):
        raise PermissionError("sufficiency recheck action must be fixture-only")
    if action_inputs.get("final_answer_packet_deferred") is not True:
        raise PermissionError("sufficiency recheck must defer FinalAnswerPacket")
    if action_inputs.get("author_activation_allowed") is not False:
        raise PermissionError("sufficiency recheck must keep Author closed")
    if action_inputs.get("citation_behavior_changed") is not False:
        raise PermissionError("sufficiency recheck must not change citations")
    if action_inputs.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(evidence_ledger_projection)
    ):
        raise PermissionError("authorized sufficiency recheck EvidenceLedger digest mismatch")


def _validate_ag96i3m2_intake_state(state: Mapping[str, Any]) -> None:
    if state.get("runtime_evidence_intake_occurred") is not True:
        raise PermissionError(
            "AG-96I3M2 sufficiency recheck requires runtime EvidenceLedger intake"
        )
    if state.get("source_obligation_satisfied") not in {True, False}:
        raise PermissionError(
            "AG-96I3M2 sufficiency recheck requires explicit source obligation posture"
        )
    if not _mapping(state.get("ag96i3m2_admission_review_candidate")):
        raise PermissionError(
            "AG-96I3M2 sufficiency recheck requires admission-review summary"
        )
    if not _mapping(state.get("ag96i3m2_evidence_ledger_intake_binding")):
        raise PermissionError(
            "AG-96I3M2 sufficiency recheck requires EvidenceLedger binding summary"
        )
    adapter_projection = _mapping(state.get("ag96i3m1_adapter_projection"))
    if adapter_projection.get("accepted") is not True:
        raise PermissionError(
            "AG-96I3M2 sufficiency recheck requires accepted intake adapter state"
        )
    if state.get("sufficiency_judgment_rechecked") is not False:
        raise PermissionError(
            "AG-96I3M2 sufficiency recheck requires unrechecked intake state"
        )


def _ag96i3m2_source_obligation_unsatisfied(
    intake_state: Mapping[str, Any],
) -> bool:
    return (
        clean_token(intake_state.get("evidence_ledger_intake_mode"))
        == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        and intake_state.get("source_obligation_satisfied") is False
    )


def _unsatisfied_source_requirement_statuses(
    *,
    action_inputs: Mapping[str, Any],
    statuses: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    if statuses:
        return tuple(
            {
                **_mapping(item),
                "status": FollowupSufficiencyRequirementStatus.UNSATISFIED.value,
                "reason": "ag96i3m2_source_obligation_not_satisfied",
            }
            for item in statuses
        )
    required_source_class = _required_source_class(
        _strings(action_inputs.get("expected_source_classes")),
        provider_job_kind=action_inputs.get("provider_job_kind"),
    )
    return (
        {
            "requirement_id": clean_token(_ledger_requirement_id(action_inputs)),
            "status": FollowupSufficiencyRequirementStatus.UNSATISFIED.value,
            "required_source_class": required_source_class,
            "required_source_tier": _required_source_tier(required_source_class),
            "required_currentness": "current",
            "linked_candidate_ids": [],
            "reason": "ag96i3m2_source_obligation_not_satisfied",
        },
    )


def _ag96i3m2_recheck_summary(
    *,
    intake_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    source_requirement_statuses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    summary = {
        "evidence_ledger_observation_id": _evidence_ledger_observation_id(
            intake_state
        ),
        "evidence_ledger_counts": _evidence_ledger_counts(
            evidence_ledger_projection
        ),
        "official_current_custody_status": _official_current_custody_status(
            intake_state=intake_state,
            source_requirement_statuses=source_requirement_statuses,
        ),
    }
    if clean_token(intake_state.get("evidence_ledger_intake_mode")) == (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        summary.update(
            {
                "ag96i3m2_admission_review_candidate": _mapping(
                    intake_state.get("ag96i3m2_admission_review_candidate")
                ),
                "ag96i3m2_evidence_ledger_intake_binding": _mapping(
                    intake_state.get("ag96i3m2_evidence_ledger_intake_binding")
                ),
            }
        )
    return summary


def _evidence_ledger_observation_id(intake_state: Mapping[str, Any]) -> str:
    ledger_observation = _mapping(intake_state.get("ledger_observation"))
    return clean_text(ledger_observation.get("observation_id"), limit=220)


def _evidence_ledger_counts(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_count": int(evidence_ledger_projection.get("candidate_count") or 0),
        "requirement_count": int(
            evidence_ledger_projection.get("requirement_count") or 0
        ),
        "custody_record_count": int(
            evidence_ledger_projection.get("custody_record_count") or 0
        ),
        "custody_gap_count": len(_list(evidence_ledger_projection.get("custody_gaps"))),
        "observation_ref_count": len(
            _list(evidence_ledger_projection.get("observation_refs"))
        ),
    }


def _official_current_custody_status(
    *,
    intake_state: Mapping[str, Any],
    source_requirement_statuses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    statuses = [_mapping(item) for item in source_requirement_statuses]
    official_current_statuses = [
        item
        for item in statuses
        if item.get("required_source_class")
        in {"official_current_rules", "current_primary_or_official"}
        or item.get("required_source_tier") == "official"
        or item.get("required_currentness") == "current"
    ]
    return {
        "source_obligation_satisfied": intake_state.get(
            "source_obligation_satisfied"
        ),
        "runtime_evidence_intake_occurred": intake_state.get(
            "runtime_evidence_intake_occurred"
        ),
        "official_current_requirement_count": len(official_current_statuses),
        "official_current_satisfied": bool(official_current_statuses)
        and all(
            item.get("status")
            == FollowupSufficiencyRequirementStatus.SATISFIED.value
            for item in official_current_statuses
        ),
        "source_requirement_statuses": [
            safe_json(item) for item in official_current_statuses
        ],
    }


def _source_requirement_statuses(
    projection: Mapping[str, Any],
    *,
    requirement_ids: Sequence[str] | None = None,
    source_obligation_id: Any = None,
) -> tuple[Mapping[str, Any], ...]:
    wanted = {
        _requirement_token(item)
        for item in tuple(requirement_ids or ())
        if _requirement_token(item)
    }
    source_obligation = clean_token(source_obligation_id)
    statuses: list[dict[str, Any]] = []
    for requirement in _list(projection.get("source_requirements")):
        if not isinstance(requirement, Mapping):
            continue
        requirement_id = str(requirement.get("requirement_id") or "")
        token = _requirement_token(requirement_id)
        origin = clean_text(requirement.get("origin_ref"), limit=220) or ""
        if wanted and token not in wanted:
            if not source_obligation or source_obligation not in origin:
                continue
        status = _coerce_requirement_status(requirement.get("status"))
        statuses.append(
            {
                "requirement_id": clean_token(requirement_id),
                "status": status,
                "required_source_class": clean_token(
                    requirement.get("required_source_class")
                ),
                "required_source_tier": clean_token(
                    requirement.get("required_source_tier")
                ),
                "required_currentness": clean_token(
                    requirement.get("required_currentness")
                ),
                "linked_candidate_ids": _strings(
                    requirement.get("linked_candidate_ids")
                ),
                "reason": clean_text(requirement.get("reason"), limit=260),
            }
        )
    if statuses:
        return tuple(statuses)
    return tuple(
        {
            "requirement_id": clean_token(_ledger_requirement_id({"requirement_ids": [item]})),
            "status": FollowupSufficiencyRequirementStatus.UNKNOWN.value,
            "reason": "requirement_not_present_in_evidence_ledger_projection",
        }
        for item in tuple(requirement_ids or ())
    )


def _coerce_requirement_status(value: Any) -> str:
    token = clean_token(value)
    if token == "satisfied":
        return FollowupSufficiencyRequirementStatus.SATISFIED.value
    if token == "partially_satisfied":
        return FollowupSufficiencyRequirementStatus.PARTIALLY_SATISFIED.value
    if token == "unsatisfied":
        return FollowupSufficiencyRequirementStatus.UNSATISFIED.value
    return FollowupSufficiencyRequirementStatus.UNKNOWN.value


def _status_summary(statuses: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {
        "satisfied": 0,
        "partially_satisfied": 0,
        "unsatisfied": 0,
        "unknown": 0,
    }
    for item in statuses:
        status = _mapping(item).get("status") or "unknown"
        counts[status if status in counts else "unknown"] += 1
    return {
        **counts,
        "all_satisfied": bool(statuses) and counts["satisfied"] == len(statuses),
        "any_satisfied": counts["satisfied"] > 0,
        "any_non_sufficient": (
            counts["partially_satisfied"] + counts["unsatisfied"] + counts["unknown"]
        )
        > 0,
    }


def _fixture_sufficiency_posture(
    *,
    action_inputs: Mapping[str, Any],
    judgment_projection: Mapping[str, Any],
    source_requirement_statuses: Sequence[Mapping[str, Any]],
    prior_sufficiency_judgment_projection: Mapping[str, Any],
) -> str:
    if _strings(prior_sufficiency_judgment_projection.get("unresolved_conflicts")):
        return FollowupSufficiencyPosture.UNRESOLVED_CONFLICT.value
    if judgment_projection.get("source_bound_numeric_unknowns"):
        return FollowupSufficiencyPosture.SOURCE_BOUND_UNKNOWN.value
    decision = clean_token(judgment_projection.get("decision"))
    if decision in {"block_finalization", "conflict_blocked"}:
        return FollowupSufficiencyPosture.REFUSE_OR_BLOCK.value
    if action_inputs.get("bridge_only") is True:
        return FollowupSufficiencyPosture.ANSWER_WITH_CAVEATS.value
    if action_inputs.get("result_status") != "fixture_success":
        return FollowupSufficiencyPosture.INSUFFICIENT_EVIDENCE.value
    summary = _status_summary(source_requirement_statuses)
    if summary.get("all_satisfied"):
        return FollowupSufficiencyPosture.READY_FOR_NEXT_FIXTURE_PHASE.value
    if summary.get("any_satisfied") or summary.get("partially_satisfied"):
        return FollowupSufficiencyPosture.ANSWER_WITH_CAVEATS.value
    return FollowupSufficiencyPosture.INSUFFICIENT_EVIDENCE.value


def _source_bound_recheck_without_resolution(action_inputs: Mapping[str, Any]) -> bool:
    provider_job_kind = clean_token(action_inputs.get("provider_job_kind"))
    if provider_job_kind == "source_bound_numeric_extraction_calculation_support":
        return True
    return "sourced_numeric_values" in _strings(
        action_inputs.get("expected_source_classes")
    )


def _sufficiency_ref(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner": projection.get("owner"),
        "canonical_state": projection.get("canonical_state"),
        "trace_only": projection.get("trace_only"),
        "judgment_id": projection.get("judgment_id"),
        "decision": projection.get("decision"),
        "final_answer_posture": projection.get("final_answer_posture"),
        "final_answer_allowed": projection.get("final_answer_allowed"),
    }


def _ledger_requirement_id(action_inputs: Mapping[str, Any]) -> str:
    requirement_id = next(iter(_strings(action_inputs.get("requirement_ids"))), "")
    requirement_id = requirement_id or str(action_inputs.get("source_obligation_id") or "")
    token = clean_token(requirement_id) or "followup_requirement"
    if ":" in token:
        return token
    return f"source_requirement:{token}"


def _requirement_token(value: Any) -> str:
    token = clean_token(value) or ""
    if token.startswith("source_requirement:"):
        token = token.split(":", 1)[1]
    return token


def _required_source_class(
    expected_source_classes: Sequence[str],
    *,
    provider_job_kind: Any,
) -> str:
    expected = tuple(item for item in expected_source_classes if item)
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
    if expected:
        return expected[0]
    job_kind = clean_token(provider_job_kind)
    by_job = {
        "official_current_candidate_acquisition": "official_current_rules",
        "legal_current_primary_acquisition": "legal_or_regulatory_text",
        "canonical_doc_acquisition": "primary_source_documents",
        "source_bound_numeric_extraction_calculation_support": "sourced_numeric_values",
        "conflict_currentness_check": "current_primary_or_official",
    }
    return by_job.get(job_kind, "answer_bearing_candidate")


def _requirement_kind(source_class: str) -> str:
    if source_class in {"official_current_rules", "current_primary_or_official"}:
        return "official_current"
    if source_class == "legal_or_regulatory_text":
        return "legal_primary"
    if source_class == "primary_source_documents":
        return "canonical_docs"
    if source_class == "sourced_numeric_values":
        return "source_bound_numeric"
    return "general"


def _required_source_tier(source_class: str) -> str | None:
    if source_class in {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
    }:
        return "official"
    return None


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": True,
        "final_answer_packet_updated": False,
        "final_answer_behavior_changed": False,
        "author_prose_behavior_changed": False,
        "author_activation_allowed": False,
        "citation_behavior_changed": False,
        "citation_eligible": False,
    }


def _fixture_only_provenance() -> dict[str, Any]:
    return followup_fixture_provenance(
        intake_bridge="ag96i2c_followup_evidence_ledger_intake",
        recheck_bridge="ag96i2d_followup_sufficiency_recheck",
    )


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return []


def _strings(value: Any) -> tuple[str, ...]:
    if value is None or isinstance(value, str):
        values = (value,) if value else ()
    elif isinstance(value, Sequence):
        values = tuple(value)
    else:
        values = (value,)
    out: list[str] = []
    for item in values:
        token = clean_token(item)
        if token and token not in out:
            out.append(token)
    return tuple(out)


__all__ = [
    "FOLLOWUP_SUFFICIENCY_RECHECK_GATE_REASON",
    "FOLLOWUP_SUFFICIENCY_RECHECK_MODE",
    "FOLLOWUP_SUFFICIENCY_RECHECK_SCHEMA_VERSION",
    "FOLLOWUP_SUFFICIENCY_RECHECK_STAGE",
    "FOLLOWUP_SUFFICIENCY_RECHECK_TRACE_KEY",
    "FollowupSufficiencyPosture",
    "FollowupSufficiencyRecheckActionResult",
    "FollowupSufficiencyRecheckConsumptionRecord",
    "FollowupSufficiencyRecheckObservation",
    "FollowupSufficiencyRecheckRequest",
    "FollowupSufficiencyRecheckResult",
    "FollowupSufficiencyRequirementStatus",
    "build_followup_sufficiency_recheck_record",
    "evidence_ledger_custody_summary",
    "evidence_ledger_projection_digest",
    "execute_followup_sufficiency_recheck_action",
]
