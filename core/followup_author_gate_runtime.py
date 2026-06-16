"""Fixture-only follow-up Author gate seam for AG-96I2F.

This module consumes the already-reduced fixture-only FinalAnswerPacket
authority and records the Author-facing gate posture. It never calls Author,
providers, search, retrieval, fetch/read, prompts, models, citation formatters,
provider-job executors, shell processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_deliberation import clean_text, clean_token, safe_json
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
    followup_projection_digest,
)
from core.followup_fixture_boundaries import (
    FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS,
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    followup_closed_flags,
    followup_common_redaction_posture,
    followup_fixture_provenance,
    followup_live_surface_flags,
)

FOLLOWUP_AUTHOR_GATE_SCHEMA_VERSION = "followup_author_gate_ag96i2f_v1"
FOLLOWUP_AUTHOR_GATE_TRACE_KEY = "followup_author_gate_runtime"
FOLLOWUP_AUTHOR_GATE_STAGE = "followup_author_gate"
FOLLOWUP_AUTHOR_GATE_MODE = "fixture_only_followup_author_gate"
FOLLOWUP_AUTHOR_GATE_REASON = "ag96i2f_fixture_only_author_gate_deferred"


@dataclass(frozen=True, slots=True)
class FollowupAuthorGateRequest:
    request_id: str
    run_id: str
    checkpoint_id: str
    followup_authorization_consumption_id: str
    sealed_candidate_id: str
    followup_execution_id: str
    execution_id: str
    followup_evidence_intake_id: str
    intake_id: str
    followup_sufficiency_recheck_id: str
    recheck_id: str
    followup_final_answer_packet_id: str
    packet_preparation_id: str
    packet_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    fixture_execution_mode: str
    evidence_ledger_intake_mode: str
    sufficiency_recheck_mode: str
    final_answer_packet_mode: str
    final_answer_packet_digest: str
    final_answer_authority_projection_digest: str
    provider_execution_licensed: bool
    author_gate_mode: str
    author_activation_allowed: bool
    author_execution_deferred: bool
    author_executor_invoked: bool
    author_prompt_changed: bool
    author_prose_behavior_changed: bool
    citation_rendering_changed: bool
    citation_formatter_invoked: bool
    product_answer_behavior_changed: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_AUTHOR_GATE_SCHEMA_VERSION,
            "record_type": "followup_author_gate_request",
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
            "followup_evidence_intake_id": clean_text(
                self.followup_evidence_intake_id,
                limit=220,
            ),
            "intake_id": clean_text(self.intake_id, limit=220),
            "followup_sufficiency_recheck_id": clean_text(
                self.followup_sufficiency_recheck_id,
                limit=220,
            ),
            "recheck_id": clean_text(self.recheck_id, limit=220),
            "followup_final_answer_packet_id": clean_text(
                self.followup_final_answer_packet_id,
                limit=220,
            ),
            "packet_preparation_id": clean_text(
                self.packet_preparation_id,
                limit=220,
            ),
            "packet_id": clean_text(self.packet_id, limit=220),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [clean_token(item) for item in self.requirement_ids],
            "expected_source_classes": [
                clean_token(item) for item in self.expected_source_classes
            ],
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "sufficiency_recheck_mode": clean_token(self.sufficiency_recheck_mode),
            "final_answer_packet_mode": clean_token(self.final_answer_packet_mode),
            "final_answer_packet_digest": clean_text(
                self.final_answer_packet_digest,
                limit=120,
            ),
            "final_answer_authority_projection_digest": clean_text(
                self.final_answer_authority_projection_digest,
                limit=120,
            ),
            "fixture_only_provenance": _fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "author_gate_mode": clean_token(self.author_gate_mode),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "author_execution_deferred": bool(self.author_execution_deferred),
            "author_executor_invoked": bool(self.author_executor_invoked),
            "author_prompt_changed": bool(self.author_prompt_changed),
            "author_prose_behavior_changed": bool(
                self.author_prose_behavior_changed
            ),
            "citation_rendering_changed": bool(self.citation_rendering_changed),
            "citation_formatter_invoked": bool(self.citation_formatter_invoked),
            "product_answer_behavior_changed": bool(
                self.product_answer_behavior_changed
            ),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorGateResult:
    result_id: str
    status: str
    author_gate_decision: str
    author_gate_reason: str
    packet_authority_consumed: bool
    answer_readiness_posture: Mapping[str, Any]
    author_payload_ref: Mapping[str, Any]
    final_answer_authority_payload_ref: Mapping[str, Any]
    mandatory_caveats: tuple[str, ...]
    prohibited_upgrades: tuple[str, ...]
    missing_required_obligations: tuple[Mapping[str, Any], ...]
    partial_obligations: tuple[Mapping[str, Any], ...]
    satisfied_obligations: tuple[Mapping[str, Any], ...]
    source_bound_unknowns: tuple[Mapping[str, Any], ...]
    unresolved_conflicts: tuple[str, ...]
    citation_eligibility_refs: tuple[Mapping[str, Any], ...]
    citation_eligible_source_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_AUTHOR_GATE_SCHEMA_VERSION,
            "record_type": "followup_author_gate_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "author_gate_decision": clean_token(self.author_gate_decision),
            "author_gate_reason": clean_token(self.author_gate_reason),
            "packet_authority_consumed": bool(self.packet_authority_consumed),
            "answer_readiness_posture": safe_json(self.answer_readiness_posture),
            "author_payload_ref": safe_json(self.author_payload_ref),
            "final_answer_authority_payload_ref": safe_json(
                self.final_answer_authority_payload_ref
            ),
            "mandatory_caveats": [
                clean_text(item, limit=300) for item in self.mandatory_caveats
            ],
            "prohibited_upgrades": [
                clean_text(item, limit=300) for item in self.prohibited_upgrades
            ],
            "missing_required_obligations": [
                safe_json(item) for item in self.missing_required_obligations
            ],
            "partial_obligations": [
                safe_json(item) for item in self.partial_obligations
            ],
            "satisfied_obligations": [
                safe_json(item) for item in self.satisfied_obligations
            ],
            "source_bound_unknowns": [
                safe_json(item) for item in self.source_bound_unknowns
            ],
            "unresolved_conflicts": [
                clean_text(item, limit=220) for item in self.unresolved_conflicts
            ],
            "citation_eligibility_refs": [
                safe_json(item) for item in self.citation_eligibility_refs
            ],
            "citation_eligible_source_ids": [
                clean_text(item, limit=220)
                for item in self.citation_eligible_source_ids
            ],
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_text_included": False,
            "live_validation_not_run": True,
            "provider_execution_licensed": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorGateObservation:
    observation_id: str
    request: FollowupAuthorGateRequest
    result: FollowupAuthorGateResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        return {
            "schema_version": FOLLOWUP_AUTHOR_GATE_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_AUTHOR_GATE_TRACE_KEY,
            "record_type": "followup_author_gate_observation",
            "owner": "FollowupAuthorGateRuntime",
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
            "followup_evidence_intake_id": request.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": request.get("intake_id"),
            "followup_sufficiency_recheck_id": request.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": request.get("recheck_id"),
            "followup_final_answer_packet_id": request.get(
                "followup_final_answer_packet_id"
            ),
            "packet_preparation_id": request.get("packet_preparation_id"),
            "packet_id": request.get("packet_id"),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": request.get("sufficiency_recheck_mode"),
            "final_answer_packet_mode": request.get("final_answer_packet_mode"),
            "final_answer_packet_digest": request.get("final_answer_packet_digest"),
            "final_answer_authority_projection_digest": request.get(
                "final_answer_authority_projection_digest"
            ),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "author_gate_mode": request.get("author_gate_mode"),
            "request": request,
            "result": result,
            "author_gate_decision": result.get("author_gate_decision"),
            "author_gate_reason": result.get("author_gate_reason"),
            "packet_authority_consumed": result.get("packet_authority_consumed"),
            "answer_readiness_posture": result.get("answer_readiness_posture", {}),
            "author_payload_ref": result.get("author_payload_ref", {}),
            "final_answer_authority_payload_ref": result.get(
                "final_answer_authority_payload_ref",
                {},
            ),
            "mandatory_caveats": result.get("mandatory_caveats", []),
            "prohibited_upgrades": result.get("prohibited_upgrades", []),
            "missing_required_obligations": result.get(
                "missing_required_obligations",
                [],
            ),
            "partial_obligations": result.get("partial_obligations", []),
            "satisfied_obligations": result.get("satisfied_obligations", []),
            "source_bound_unknowns": result.get("source_bound_unknowns", []),
            "unresolved_conflicts": result.get("unresolved_conflicts", []),
            "citation_eligibility_refs": result.get("citation_eligibility_refs", []),
            "citation_eligible_source_ids": result.get(
                "citation_eligible_source_ids",
                [],
            ),
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_text_included": False,
            "live_validation_not_run": True,
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorGateConsumptionRecord:
    author_gate_id: str
    observation: FollowupAuthorGateObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_author_gate_consumption_record",
            "owner": "FollowupAuthorGateRuntime",
            "canonical_state": False,
            "author_gate_id": clean_text(self.author_gate_id, limit=220),
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorGateActionResult:
    record: FollowupAuthorGateConsumptionRecord
    observation: Any


def execute_followup_author_gate_action(
    action: Any,
    *,
    followup_final_answer_packet_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorGateActionResult:
    """Execute the fixture-only Author gate adapter for one authorized action."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_AUTHOR_GATE,
        stage=FOLLOWUP_AUTHOR_GATE_STAGE,
        expected_observation_type=ObservationType.FOLLOWUP_AUTHOR_GATE_OBSERVED,
    )
    record = build_followup_author_gate_record(
        action_inputs=authorized.inputs,
        followup_final_answer_packet_state=followup_final_answer_packet_state,
        final_answer_packet=final_answer_packet,
        final_answer_authority_projection=final_answer_authority_projection,
    )
    return FollowupAuthorGateActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_AUTHOR_GATE_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_author_gate_state": record.to_dict()},
        ),
    )


def build_followup_author_gate_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_final_answer_packet_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorGateConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    packet_state = _mapping(safe_json(followup_final_answer_packet_state))
    packet = _mapping(safe_json(final_answer_packet))
    authority = _mapping(safe_json(final_answer_authority_projection))
    _validate_packet_state(packet_state)
    _validate_final_answer_packet(packet, packet_state)
    _validate_authority_projection(authority, packet_state, packet)
    _validate_action_inputs(action, packet_state, packet, authority)

    author_payload_ref = _mapping(authority.get("author_payload_ref"))
    authority_payload_ref = _mapping(authority.get("author_authority_payload_ref"))
    final_answer_allowed = packet.get("final_answer_allowed") is True
    decision = "deferred" if final_answer_allowed else "blocked"
    reason = (
        "fixture_only_packet_author_deferred"
        if final_answer_allowed
        else "packet_final_answer_not_allowed"
    )
    packet_id = str(action.get("packet_id") or packet.get("packet_id") or "")
    request = FollowupAuthorGateRequest(
        request_id=f"followup-author-gate-request:{action.get('packet_preparation_id')}",
        run_id=str(action.get("run_id") or ""),
        checkpoint_id=str(action.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(
            action.get("followup_authorization_consumption_id") or ""
        ),
        sealed_candidate_id=str(action.get("sealed_candidate_id") or ""),
        followup_execution_id=str(action.get("followup_execution_id") or ""),
        execution_id=str(action.get("execution_id") or ""),
        followup_evidence_intake_id=str(
            action.get("followup_evidence_intake_id") or ""
        ),
        intake_id=str(action.get("intake_id") or ""),
        followup_sufficiency_recheck_id=str(
            action.get("followup_sufficiency_recheck_id") or ""
        ),
        recheck_id=str(action.get("recheck_id") or ""),
        followup_final_answer_packet_id=str(
            action.get("followup_final_answer_packet_id") or ""
        ),
        packet_preparation_id=str(action.get("packet_preparation_id") or ""),
        packet_id=packet_id,
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        evidence_ledger_intake_mode=str(action.get("evidence_ledger_intake_mode") or ""),
        sufficiency_recheck_mode=str(action.get("sufficiency_recheck_mode") or ""),
        final_answer_packet_mode=FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
        final_answer_packet_digest=str(action.get("final_answer_packet_digest") or ""),
        final_answer_authority_projection_digest=str(
            action.get("final_answer_authority_projection_digest") or ""
        ),
        provider_execution_licensed=False,
        author_gate_mode=FOLLOWUP_AUTHOR_GATE_MODE,
        author_activation_allowed=False,
        author_execution_deferred=True,
        author_executor_invoked=False,
        author_prompt_changed=False,
        author_prose_behavior_changed=False,
        citation_rendering_changed=False,
        citation_formatter_invoked=False,
        product_answer_behavior_changed=False,
        live_validation_not_run=True,
    )
    result = FollowupAuthorGateResult(
        result_id=f"followup-author-gate-result:{action.get('packet_preparation_id')}",
        status="fixture_author_gate_consumed",
        author_gate_decision=decision,
        author_gate_reason=reason,
        packet_authority_consumed=True,
        answer_readiness_posture={
            "packet_id": packet_id,
            "readiness_status": packet.get("readiness_status"),
            "readiness_reasons": packet.get("readiness_reasons", []),
            "final_answer_allowed": packet.get("final_answer_allowed"),
            "final_answer_posture": packet.get("final_answer_posture"),
            "sufficiency_decision": packet.get("sufficiency_decision"),
        },
        author_payload_ref=author_payload_ref,
        final_answer_authority_payload_ref=authority_payload_ref,
        mandatory_caveats=tuple(_strings(packet.get("mandatory_caveats"))),
        prohibited_upgrades=tuple(_strings(packet.get("prohibited_upgrades"))),
        missing_required_obligations=tuple(
            _mappings(packet.get("missing_required_obligations"))
        ),
        partial_obligations=tuple(_mappings(packet.get("partial_obligations"))),
        satisfied_obligations=tuple(_mappings(packet.get("satisfied_obligations"))),
        source_bound_unknowns=tuple(
            _mappings(packet.get("source_bound_numeric_unknowns"))
        ),
        unresolved_conflicts=tuple(
            _strings(packet_state.get("unresolved_conflicts"))
        ),
        citation_eligibility_refs=tuple(
            _mappings(
                authority.get("citation_eligibility_refs")
                or packet_state.get("citation_eligibility_refs")
            )
        ),
        citation_eligible_source_ids=tuple(
            _texts(authority.get("citation_eligible_source_ids"))
        ),
    )
    observation = FollowupAuthorGateObservation(
        observation_id=f"followup-author-gate-observation:{action.get('packet_preparation_id')}",
        request=request,
        result=result,
    )
    return FollowupAuthorGateConsumptionRecord(
        author_gate_id=f"followup-author-gate:{action.get('packet_preparation_id')}",
        observation=observation,
    )


def _validate_packet_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError("follow-up Author gate requires canonical packet state")
    if state.get("owner") != "RunKernel.FollowupFinalAnswerPacket":
        raise PermissionError("follow-up Author gate requires RunKernel packet state")
    if state.get("final_answer_packet_mode") != FOLLOWUP_FINAL_ANSWER_PACKET_MODE:
        raise PermissionError("follow-up Author gate requires fixture-only packet mode")
    if state.get("final_answer_packet_prepared") is not True:
        raise PermissionError("follow-up Author gate requires prepared packet")
    if state.get("author_activation_allowed") is not False:
        raise PermissionError("follow-up Author gate requires Author activation closed")
    if state.get("author_execution_deferred") is not True:
        raise PermissionError("follow-up Author gate requires deferred Author execution")
    flags = _mapping(state.get("behavior_boundary_flags"))
    for flag in _packet_state_closed_false_flags():
        if flags.get(flag) is not False:
            raise PermissionError(f"follow-up Author gate requires {flag}=False")
    if flags.get("author_execution_deferred") is not True:
        raise PermissionError("follow-up Author gate requires packet Author deferral")
    if flags.get("live_validation_not_run") is not True:
        raise PermissionError("follow-up Author gate requires no live validation")


def _validate_final_answer_packet(
    packet: Mapping[str, Any],
    packet_state: Mapping[str, Any],
) -> None:
    packet_id = packet.get("packet_id")
    if not packet_id:
        raise PermissionError("follow-up Author gate requires FinalAnswerPacket")
    if packet_id != packet_state.get("packet_id"):
        raise PermissionError("follow-up Author gate packet_id mismatch")
    if packet.get("trace_mode") != "final_answer_packet_authority_projection":
        raise PermissionError("follow-up Author gate requires packet projection")
    if packet.get("author_input_refs", {}).get("status") not in {
        "author_execution_deferred",
        None,
    }:
        raise PermissionError("follow-up Author gate requires deferred author refs")
    if packet.get("behavior_boundary_flags", {}).get(
        "author_activation_allowed"
    ) is True:
        raise PermissionError("follow-up Author gate requires closed Author flag")


def _validate_authority_projection(
    authority: Mapping[str, Any],
    packet_state: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> None:
    if authority.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("follow-up Author gate requires packet authority owner")
    if authority.get("canonical_state") is not True:
        raise PermissionError("follow-up Author gate requires canonical authority")
    if authority.get("trace_only") is not False:
        raise PermissionError("packet authority projection must not be trace-only")
    if authority.get("packet_id") != packet.get("packet_id"):
        raise PermissionError("packet authority projection packet_id mismatch")
    if authority.get("packet_id") != packet_state.get("packet_id"):
        raise PermissionError("packet authority projection state packet_id mismatch")
    payload_ref = _mapping(authority.get("author_payload_ref"))
    if payload_ref.get("status") != "author_execution_deferred":
        raise PermissionError("follow-up Author gate requires deferred author payload")
    if payload_ref.get("author_activation_allowed") is not False:
        raise PermissionError("follow-up Author gate requires payload activation closed")
    if payload_ref.get("author_execution_deferred") is not True:
        raise PermissionError("follow-up Author gate requires payload deferral")
    for field in (
        "author_activation_allowed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
    ):
        if authority.get(field) is not False:
            raise PermissionError(f"packet authority must keep {field}=False")
    if authority.get("author_execution_deferred") is not True:
        raise PermissionError("packet authority must defer Author execution")
    if authority.get("live_validation_not_run") is not True:
        raise PermissionError("packet authority must record no live validation")


def _validate_action_inputs(
    action: Mapping[str, Any],
    packet_state: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "packet_preparation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
    ):
        if action.get(field) != packet_state.get(field):
            raise PermissionError(f"authorized follow-up Author gate {field} mismatch")
    if action.get("followup_final_answer_packet_id") != packet_state.get(
        "packet_preparation_id"
    ):
        raise PermissionError(
            "authorized follow-up Author gate final packet id mismatch"
        )
    if action.get("packet_id") != packet.get("packet_id"):
        raise PermissionError("authorized follow-up Author gate packet_id mismatch")
    if _strings(action.get("requirement_ids")) != _strings(
        packet_state.get("requirement_ids")
    ):
        raise PermissionError(
            "authorized follow-up Author gate requirement_ids mismatch"
        )
    if _strings(action.get("expected_source_classes")) != _strings(
        packet_state.get("expected_source_classes")
    ):
        raise PermissionError(
            "authorized follow-up Author gate expected_source_classes mismatch"
        )
    if action.get("final_answer_packet_digest") != followup_projection_digest(packet):
        raise PermissionError("follow-up Author gate FinalAnswerPacket digest mismatch")
    if action.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError(
            "follow-up Author gate authority projection digest mismatch"
        )
    if action.get("provider_execution_licensed") is not False:
        raise PermissionError("follow-up Author gate must keep provider unlicensed")
    if action.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
        raise PermissionError("follow-up Author gate action must be fixture-only")
    for field in (
        "author_activation_allowed",
        "author_executor_invoked",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
    ):
        if action.get(field) is not False:
            raise PermissionError(f"follow-up Author gate must keep {field}=False")
    if action.get("author_execution_deferred") is not True:
        raise PermissionError("follow-up Author gate must defer Author execution")
    if action.get("live_validation_not_run") is not True:
        raise PermissionError("follow-up Author gate must not run live validation")


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_rebuilt": False,
        "final_answer_packet_updated": False,
        "packet_authority_consumed": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        **followup_closed_flags(
            *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS
        ),
        "live_validation_not_run": True,
    }


def _packet_state_closed_false_flags() -> tuple[str, ...]:
    return (
        *FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:],
        *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
        "author_executor_invoked",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "citation_behavior_changed",
        "product_answer_behavior_changed",
        "final_answer_behavior_changed",
    )


def _fixture_only_provenance() -> dict[str, Any]:
    return followup_fixture_provenance(
        intake_bridge="ag96i2c_followup_evidence_ledger_intake",
        recheck_bridge="ag96i2d_followup_sufficiency_recheck",
        packet_bridge="ag96i2e_followup_final_answer_packet_prepare",
        author_gate_bridge="ag96i2f_followup_author_gate",
        author_executor_connected=False,
    )


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
        packet_authority_refs_only=True,
        final_text_retained=False,
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> tuple[dict[str, Any], ...]:
    return tuple(dict(item) for item in _list(value) if isinstance(item, Mapping))


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


def _texts(value: Any) -> tuple[str, ...]:
    if value is None or isinstance(value, str):
        values = (value,) if value else ()
    elif isinstance(value, Sequence):
        values = tuple(value)
    else:
        values = (value,)
    out: list[str] = []
    for item in values:
        text = clean_text(item, limit=220)
        if text and text not in out:
            out.append(text)
    return tuple(out)


__all__ = [
    "FOLLOWUP_AUTHOR_GATE_MODE",
    "FOLLOWUP_AUTHOR_GATE_REASON",
    "FOLLOWUP_AUTHOR_GATE_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_GATE_STAGE",
    "FOLLOWUP_AUTHOR_GATE_TRACE_KEY",
    "FollowupAuthorGateActionResult",
    "FollowupAuthorGateConsumptionRecord",
    "FollowupAuthorGateObservation",
    "FollowupAuthorGateRequest",
    "FollowupAuthorGateResult",
    "build_followup_author_gate_record",
    "execute_followup_author_gate_action",
]
