"""Fixture-only follow-up Author output observation seam for AG-96I2H.

This module observes an explicit, sanitized fixture Author output payload after
the AG-96I2F Author gate. It never calls Author, providers, search, retrieval,
fetch/read, prompts, models, citation formatters, provider-job executors, shell
processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.followup_author_gate_runtime import FOLLOWUP_AUTHOR_GATE_MODE
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

FOLLOWUP_AUTHOR_OBSERVATION_SCHEMA_VERSION = (
    "followup_author_observation_ag96i2h_v1"
)
FOLLOWUP_AUTHOR_OBSERVATION_TRACE_KEY = "followup_author_observation_runtime"
FOLLOWUP_AUTHOR_OBSERVATION_STAGE = "followup_author_observation"
FOLLOWUP_AUTHOR_OBSERVATION_MODE = "fixture_only_followup_author_observation"
FOLLOWUP_AUTHOR_OBSERVATION_REASON = (
    "ag96i2h_fixture_only_author_output_observation"
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorObservationRequest:
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
    followup_author_gate_id: str
    author_gate_id: str
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
    author_gate_mode: str
    fixture_author_observation_mode: str
    final_answer_packet_digest: str
    final_answer_authority_projection_digest: str
    followup_author_gate_digest: str
    provider_execution_licensed: bool
    author_activation_allowed: bool
    author_execution_deferred: bool
    author_executor_invoked: bool
    model_called: bool
    author_prompt_changed: bool
    author_prose_behavior_changed: bool
    citation_rendering_changed: bool
    citation_formatter_invoked: bool
    product_answer_behavior_changed: bool
    final_text_included: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_AUTHOR_OBSERVATION_SCHEMA_VERSION,
            "record_type": "followup_author_observation_request",
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
            "followup_author_gate_id": clean_text(
                self.followup_author_gate_id,
                limit=220,
            ),
            "author_gate_id": clean_text(self.author_gate_id, limit=220),
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
            "author_gate_mode": clean_token(self.author_gate_mode),
            "fixture_author_observation_mode": clean_token(
                self.fixture_author_observation_mode
            ),
            "final_answer_packet_digest": clean_text(
                self.final_answer_packet_digest,
                limit=120,
            ),
            "final_answer_authority_projection_digest": clean_text(
                self.final_answer_authority_projection_digest,
                limit=120,
            ),
            "followup_author_gate_digest": clean_text(
                self.followup_author_gate_digest,
                limit=120,
            ),
            "fixture_only_provenance": _fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "author_execution_deferred": bool(self.author_execution_deferred),
            "author_executor_invoked": bool(self.author_executor_invoked),
            "model_called": bool(self.model_called),
            "author_prompt_changed": bool(self.author_prompt_changed),
            "author_prose_behavior_changed": bool(
                self.author_prose_behavior_changed
            ),
            "citation_rendering_changed": bool(self.citation_rendering_changed),
            "citation_formatter_invoked": bool(self.citation_formatter_invoked),
            "product_answer_behavior_changed": bool(
                self.product_answer_behavior_changed
            ),
            "final_text_included": bool(self.final_text_included),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorObservationResult:
    result_id: str
    status: str
    observed_output_facts: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        facts = _mapping(safe_json(self.observed_output_facts))
        return {
            "schema_version": FOLLOWUP_AUTHOR_OBSERVATION_SCHEMA_VERSION,
            "record_type": "followup_author_observation_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "observed_output_facts": facts,
            "output_fact_summary": _output_fact_summary(facts),
            "report_hash": facts.get("report_hash"),
            "report_length": facts.get("report_length"),
            "final_text_hash": facts.get("report_hash"),
            "final_text_length": facts.get("report_length"),
            "cited_source_ids": facts.get("cited_source_ids", []),
            "mandatory_caveats_acknowledged": facts.get(
                "mandatory_caveats_acknowledged",
                [],
            ),
            "prohibited_upgrade_violations": facts.get(
                "prohibited_upgrade_violations",
                [],
            ),
            "source_bound_unknowns_acknowledged": facts.get(
                "source_bound_unknowns_acknowledged",
                [],
            ),
            "missing_obligations_acknowledged": facts.get(
                "missing_obligations_acknowledged",
                [],
            ),
            "claim_posture_labels": facts.get("claim_posture_labels", []),
            "refusal_or_caveat_posture": facts.get("refusal_or_caveat_posture"),
            "fixture_author_notes": facts.get("fixture_author_notes", []),
            "author_output_observed": True,
            "packet_authority_consumed": True,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "model_called": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_text_included": False,
            "live_validation_not_run": True,
            "provider_execution_licensed": False,
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorObservationObservation:
    observation_id: str
    request: FollowupAuthorObservationRequest
    result: FollowupAuthorObservationResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        facts = _mapping(result.get("observed_output_facts"))
        return {
            "schema_version": FOLLOWUP_AUTHOR_OBSERVATION_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_AUTHOR_OBSERVATION_TRACE_KEY,
            "record_type": "followup_author_observation_observation",
            "owner": "FollowupAuthorObservationRuntime",
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
            "followup_author_gate_id": request.get("followup_author_gate_id"),
            "author_gate_id": request.get("author_gate_id"),
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
            "author_gate_mode": request.get("author_gate_mode"),
            "fixture_author_observation_mode": request.get(
                "fixture_author_observation_mode"
            ),
            "final_answer_packet_digest": request.get("final_answer_packet_digest"),
            "final_answer_authority_projection_digest": request.get(
                "final_answer_authority_projection_digest"
            ),
            "followup_author_gate_digest": request.get(
                "followup_author_gate_digest"
            ),
            "provider_execution_licensed": False,
            "request": request,
            "result": result,
            "observed_output_facts": facts,
            "output_fact_summary": result.get("output_fact_summary", {}),
            "report_hash": result.get("report_hash"),
            "report_length": result.get("report_length"),
            "final_text_hash": result.get("final_text_hash"),
            "final_text_length": result.get("final_text_length"),
            "cited_source_ids": result.get("cited_source_ids", []),
            "mandatory_caveats_acknowledged": result.get(
                "mandatory_caveats_acknowledged",
                [],
            ),
            "prohibited_upgrade_violations": result.get(
                "prohibited_upgrade_violations",
                [],
            ),
            "source_bound_unknowns_acknowledged": result.get(
                "source_bound_unknowns_acknowledged",
                [],
            ),
            "missing_obligations_acknowledged": result.get(
                "missing_obligations_acknowledged",
                [],
            ),
            "claim_posture_labels": result.get("claim_posture_labels", []),
            "refusal_or_caveat_posture": result.get("refusal_or_caveat_posture"),
            "fixture_author_notes": result.get("fixture_author_notes", []),
            "author_output_observed": True,
            "packet_authority_consumed": True,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "model_called": False,
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
class FollowupAuthorObservationConsumptionRecord:
    author_observation_id: str
    observation: FollowupAuthorObservationObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_author_observation_consumption_record",
            "owner": "FollowupAuthorObservationRuntime",
            "canonical_state": False,
            "author_observation_id": clean_text(
                self.author_observation_id,
                limit=220,
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupAuthorObservationActionResult:
    record: FollowupAuthorObservationConsumptionRecord
    observation: Any


def execute_followup_author_observation_action(
    action: Any,
    *,
    followup_author_gate_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    fixture_author_output_payload: Mapping[str, Any],
) -> FollowupAuthorObservationActionResult:
    """Observe an explicit fixture-only Author output payload."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
        stage=FOLLOWUP_AUTHOR_OBSERVATION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_OBSERVATION_OBSERVED
        ),
    )
    record = build_followup_author_observation_record(
        action_inputs=authorized.inputs,
        followup_author_gate_state=followup_author_gate_state,
        final_answer_packet=final_answer_packet,
        final_answer_authority_projection=final_answer_authority_projection,
        fixture_author_output_payload=fixture_author_output_payload,
    )
    return FollowupAuthorObservationActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_AUTHOR_OBSERVATION_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_author_observation_state": record.to_dict()},
        ),
    )


def build_followup_author_observation_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    fixture_author_output_payload: Mapping[str, Any] | None = None,
    observed_output_facts: Mapping[str, Any] | None = None,
) -> FollowupAuthorObservationConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    gate = _mapping(safe_json(followup_author_gate_state))
    packet = _mapping(safe_json(final_answer_packet))
    authority = _mapping(safe_json(final_answer_authority_projection))
    _validate_gate_state(gate)
    _validate_final_answer_packet(packet, gate)
    _validate_authority_projection(authority, gate, packet)
    _validate_action_inputs(action, gate, packet, authority)
    if observed_output_facts is None:
        facts = _sanitize_fixture_author_output_payload(
            fixture_author_output_payload or {}
        )
    else:
        facts = _sanitize_observed_output_facts(observed_output_facts)

    gate_id = str(action.get("author_gate_id") or gate.get("author_gate_id") or "")
    request = FollowupAuthorObservationRequest(
        request_id=f"followup-author-observation-request:{gate_id}",
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
        followup_author_gate_id=str(action.get("followup_author_gate_id") or ""),
        author_gate_id=gate_id,
        packet_id=str(action.get("packet_id") or packet.get("packet_id") or ""),
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        evidence_ledger_intake_mode=str(action.get("evidence_ledger_intake_mode") or ""),
        sufficiency_recheck_mode=str(action.get("sufficiency_recheck_mode") or ""),
        final_answer_packet_mode=FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
        author_gate_mode=FOLLOWUP_AUTHOR_GATE_MODE,
        fixture_author_observation_mode=FOLLOWUP_AUTHOR_OBSERVATION_MODE,
        final_answer_packet_digest=str(action.get("final_answer_packet_digest") or ""),
        final_answer_authority_projection_digest=str(
            action.get("final_answer_authority_projection_digest") or ""
        ),
        followup_author_gate_digest=str(action.get("followup_author_gate_digest") or ""),
        provider_execution_licensed=False,
        author_activation_allowed=False,
        author_execution_deferred=True,
        author_executor_invoked=False,
        model_called=False,
        author_prompt_changed=False,
        author_prose_behavior_changed=False,
        citation_rendering_changed=False,
        citation_formatter_invoked=False,
        product_answer_behavior_changed=False,
        final_text_included=False,
        live_validation_not_run=True,
    )
    result = FollowupAuthorObservationResult(
        result_id=f"followup-author-observation-result:{gate_id}",
        status="fixture_author_output_observed",
        observed_output_facts=facts,
    )
    observation = FollowupAuthorObservationObservation(
        observation_id=f"followup-author-observation-observation:{gate_id}",
        request=request,
        result=result,
    )
    return FollowupAuthorObservationConsumptionRecord(
        author_observation_id=f"followup-author-observation:{gate_id}",
        observation=observation,
    )


def derive_followup_author_observation_compliance(
    *,
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    observed_output_facts: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive packet-authority compliance from canonical authority and facts."""

    packet = _mapping(safe_json(final_answer_packet))
    authority = _mapping(safe_json(final_answer_authority_projection))
    gate = _mapping(safe_json(followup_author_gate_state))
    facts = _sanitize_observed_output_facts(observed_output_facts)

    citation_allowed_ids = _citation_eligible_source_ids(
        packet=packet,
        authority=authority,
        gate=gate,
    )
    cited_source_ids = _texts(facts.get("cited_source_ids"))
    unauthorized_citation_source_ids = tuple(
        item for item in cited_source_ids if item not in citation_allowed_ids
    )
    citation_status = (
        "noncompliant" if unauthorized_citation_source_ids else "compliant"
    )

    mandatory_caveats = _texts(
        packet.get("mandatory_caveats") or gate.get("mandatory_caveats")
    )
    caveats_acknowledged = _texts(facts.get("mandatory_caveats_acknowledged"))
    caveat_keys = {_text_key(item) for item in caveats_acknowledged}
    missing_mandatory_caveats = tuple(
        item for item in mandatory_caveats if _text_key(item) not in caveat_keys
    )
    caveat_status = "noncompliant" if missing_mandatory_caveats else "compliant"

    prohibited_upgrade_violations = _texts(
        facts.get("prohibited_upgrade_violations")
    )
    prohibited_upgrade_status = (
        "noncompliant" if prohibited_upgrade_violations else "compliant"
    )

    source_bound_unknowns = _mappings(
        packet.get("source_bound_numeric_unknowns")
        or gate.get("source_bound_unknowns")
    )
    unknown_acknowledged = _texts(facts.get("source_bound_unknowns_acknowledged"))
    unacknowledged_source_bound_unknowns = _unacknowledged_refs(
        source_bound_unknowns,
        unknown_acknowledged,
    )
    source_bound_unknown_status = (
        "noncompliant" if unacknowledged_source_bound_unknowns else "compliant"
    )

    missing_or_partial = tuple(
        _mappings(packet.get("missing_required_obligations"))
        + _mappings(packet.get("partial_obligations"))
    )
    missing_acknowledged = _texts(facts.get("missing_obligations_acknowledged"))
    unacknowledged_missing_obligations = _unacknowledged_refs(
        missing_or_partial,
        missing_acknowledged,
    )
    missing_obligation_status = (
        "noncompliant" if unacknowledged_missing_obligations else "compliant"
    )

    substatuses = (
        citation_status,
        caveat_status,
        prohibited_upgrade_status,
        source_bound_unknown_status,
        missing_obligation_status,
    )
    packet_authority_status = (
        "noncompliant" if "noncompliant" in substatuses else "compliant"
    )
    return {
        "author_output_observed": True,
        "fixture_author_observation_mode": FOLLOWUP_AUTHOR_OBSERVATION_MODE,
        "packet_authority_consumed": True,
        "packet_authority_compliance_status": packet_authority_status,
        "citation_compliance_status": citation_status,
        "caveat_compliance_status": caveat_status,
        "prohibited_upgrade_compliance_status": prohibited_upgrade_status,
        "source_bound_unknown_compliance_status": source_bound_unknown_status,
        "missing_obligation_compliance_status": missing_obligation_status,
        "citation_eligible_source_ids": list(citation_allowed_ids),
        "cited_source_ids": list(cited_source_ids),
        "unauthorized_citation_source_ids": list(
            unauthorized_citation_source_ids
        ),
        "mandatory_caveats": list(mandatory_caveats),
        "mandatory_caveats_acknowledged": list(caveats_acknowledged),
        "missing_mandatory_caveats": list(missing_mandatory_caveats),
        "prohibited_upgrade_violations": list(prohibited_upgrade_violations),
        "source_bound_unknowns_acknowledged": list(unknown_acknowledged),
        "unacknowledged_source_bound_unknowns": [
            safe_json(item) for item in unacknowledged_source_bound_unknowns
        ],
        "missing_obligations_acknowledged": list(missing_acknowledged),
        "unacknowledged_missing_obligations": [
            safe_json(item) for item in unacknowledged_missing_obligations
        ],
        "final_text_included": False,
        "final_text_hash": facts.get("report_hash"),
        "final_text_length": facts.get("report_length"),
        "report_hash": facts.get("report_hash"),
        "report_length": facts.get("report_length"),
        "product_answer_behavior_changed": False,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "author_executor_invoked": False,
        "model_called": False,
        "live_validation_not_run": True,
    }


def _sanitize_fixture_author_output_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    source = _mapping(payload)
    _reject_boundary_claims(source, context="fixture Author output payload")
    report_text = source.get("report_text")
    if report_text is None:
        report_text = source.get("final_text")
    report = "" if report_text is None else str(report_text)
    facts = {
        "report_hash": _hash_text(report),
        "report_length": len(report),
        "cited_source_ids": list(_texts(source.get("citation_source_ids_used"))),
        "mandatory_caveats_acknowledged": list(
            _texts(source.get("mandatory_caveats_acknowledged"))
        ),
        "prohibited_upgrade_violations": list(
            _texts(source.get("prohibited_upgrade_violations"))
        ),
        "source_bound_unknowns_acknowledged": list(
            _texts(source.get("source_bound_unknowns_acknowledged"))
        ),
        "missing_obligations_acknowledged": list(
            _texts(source.get("missing_obligations_acknowledged"))
        ),
        "claim_posture_labels": list(_strings(source.get("claim_posture_labels"))),
        "refusal_or_caveat_posture": clean_text(
            source.get("refusal_or_caveat_posture"),
            limit=220,
        ),
        "fixture_author_notes": list(_texts(source.get("fixture_author_notes"))),
        "final_text_included": False,
        "raw_text_retained": False,
        "report_text_retained": False,
    }
    return _sanitize_observed_output_facts(facts)


def _sanitize_observed_output_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
    source = _mapping(facts)
    _reject_raw_text_keys(source, context="fixture Author observed output facts")
    _reject_boundary_claims(source, context="fixture Author observed output facts")
    report_hash = clean_text(source.get("report_hash"), limit=120)
    if not report_hash:
        report_hash = _hash_text("")
    return {
        "report_hash": report_hash,
        "report_length": _nonnegative_int(source.get("report_length")),
        "cited_source_ids": list(_texts(source.get("cited_source_ids"))),
        "mandatory_caveats_acknowledged": list(
            _texts(source.get("mandatory_caveats_acknowledged"))
        ),
        "prohibited_upgrade_violations": list(
            _texts(source.get("prohibited_upgrade_violations"))
        ),
        "source_bound_unknowns_acknowledged": list(
            _texts(source.get("source_bound_unknowns_acknowledged"))
        ),
        "missing_obligations_acknowledged": list(
            _texts(source.get("missing_obligations_acknowledged"))
        ),
        "claim_posture_labels": list(_strings(source.get("claim_posture_labels"))),
        "refusal_or_caveat_posture": clean_text(
            source.get("refusal_or_caveat_posture"),
            limit=220,
        ),
        "fixture_author_notes": list(_texts(source.get("fixture_author_notes"))),
        "final_text_included": False,
        "raw_text_retained": False,
        "report_text_retained": False,
    }


def reject_followup_author_observation_boundary_spoof(
    observed_state: Mapping[str, Any],
) -> None:
    """Reject observed state that claims closed-surface or raw-text activation."""

    state = _mapping(observed_state)
    _reject_raw_text_keys(state, context="follow-up Author observation")
    _reject_boundary_claims(state, context="follow-up Author observation")
    facts = _mapping(state.get("observed_output_facts"))
    if facts:
        _reject_raw_text_keys(
            facts,
            context="follow-up Author observation facts",
        )
        _reject_boundary_claims(
            facts,
            context="follow-up Author observation facts",
        )
    flags = _mapping(state.get("behavior_boundary_flags"))
    if flags:
        _reject_boundary_claims(
            flags,
            context="follow-up Author observation boundary flags",
        )


def _validate_gate_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError(
            "follow-up Author observation requires canonical Author gate state"
        )
    if state.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError(
            "follow-up Author observation requires RunKernel Author gate state"
        )
    if state.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
        raise PermissionError(
            "follow-up Author observation requires fixture-only Author gate"
        )
    if state.get("packet_authority_consumed") is not True:
        raise PermissionError(
            "follow-up Author observation requires consumed packet authority"
        )
    if state.get("author_activation_allowed") is not False:
        raise PermissionError(
            "follow-up Author observation requires Author activation closed"
        )
    if state.get("author_execution_deferred") is not True:
        raise PermissionError(
            "follow-up Author observation requires deferred Author execution"
        )
    if state.get("final_text_included") is not False:
        raise PermissionError(
            "follow-up Author observation requires final_text_included=False"
        )
    flags = _mapping(state.get("behavior_boundary_flags"))
    for flag in _gate_state_closed_false_flags():
        if flags.get(flag) is not False:
            raise PermissionError(
                f"follow-up Author observation requires {flag}=False"
            )
    if flags.get("packet_authority_consumed") is not True:
        raise PermissionError(
            "follow-up Author observation requires packet authority consumption"
        )
    if flags.get("author_execution_deferred") is not True:
        raise PermissionError(
            "follow-up Author observation requires Author execution deferral"
        )
    if flags.get("live_validation_not_run") is not True:
        raise PermissionError(
            "follow-up Author observation requires no live validation"
        )


def _validate_final_answer_packet(
    packet: Mapping[str, Any],
    gate_state: Mapping[str, Any],
) -> None:
    packet_id = packet.get("packet_id")
    if not packet_id:
        raise PermissionError("follow-up Author observation requires packet")
    if packet_id != gate_state.get("packet_id"):
        raise PermissionError("follow-up Author observation packet_id mismatch")
    if packet.get("trace_mode") != "final_answer_packet_authority_projection":
        raise PermissionError(
            "follow-up Author observation requires packet authority projection"
        )
    if packet.get("author_input_refs", {}).get("status") not in {
        "author_execution_deferred",
        None,
    }:
        raise PermissionError(
            "follow-up Author observation requires deferred author refs"
        )
    flags = _mapping(packet.get("behavior_boundary_flags"))
    for flag in (
        "author_activation_allowed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
    ):
        if flags.get(flag) is True:
            raise PermissionError(
                f"follow-up Author observation requires packet {flag}=False"
            )


def _validate_authority_projection(
    authority: Mapping[str, Any],
    gate_state: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> None:
    if authority.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError(
            "follow-up Author observation requires packet authority owner"
        )
    if authority.get("canonical_state") is not True:
        raise PermissionError(
            "follow-up Author observation requires canonical packet authority"
        )
    if authority.get("trace_only") is not False:
        raise PermissionError("packet authority projection must not be trace-only")
    if authority.get("packet_id") != packet.get("packet_id"):
        raise PermissionError("packet authority projection packet_id mismatch")
    if authority.get("packet_id") != gate_state.get("packet_id"):
        raise PermissionError(
            "packet authority projection Author gate packet_id mismatch"
        )
    payload_ref = _mapping(authority.get("author_payload_ref"))
    if payload_ref.get("status") != "author_execution_deferred":
        raise PermissionError(
            "follow-up Author observation requires deferred author payload"
        )
    if payload_ref.get("author_activation_allowed") is not False:
        raise PermissionError(
            "follow-up Author observation requires payload activation closed"
        )
    if payload_ref.get("author_execution_deferred") is not True:
        raise PermissionError(
            "follow-up Author observation requires payload deferral"
        )
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
    gate: Mapping[str, Any],
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
        "followup_final_answer_packet_id",
        "packet_preparation_id",
        "packet_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "author_gate_mode",
    ):
        if action.get(field) != gate.get(field):
            raise PermissionError(
                f"authorized follow-up Author observation {field} mismatch"
            )
    if action.get("followup_author_gate_id") != gate.get("author_gate_id"):
        raise PermissionError(
            "authorized follow-up Author observation gate id mismatch"
        )
    if action.get("author_gate_id") != gate.get("author_gate_id"):
        raise PermissionError(
            "authorized follow-up Author observation author_gate_id mismatch"
        )
    if action.get("packet_id") != packet.get("packet_id"):
        raise PermissionError(
            "authorized follow-up Author observation packet_id mismatch"
        )
    if _strings(action.get("requirement_ids")) != _strings(
        gate.get("requirement_ids")
    ):
        raise PermissionError(
            "authorized follow-up Author observation requirement_ids mismatch"
        )
    if _strings(action.get("expected_source_classes")) != _strings(
        gate.get("expected_source_classes")
    ):
        raise PermissionError(
            "authorized follow-up Author observation expected_source_classes mismatch"
        )
    if action.get("final_answer_packet_digest") != followup_projection_digest(packet):
        raise PermissionError(
            "follow-up Author observation FinalAnswerPacket digest mismatch"
        )
    if action.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError(
            "follow-up Author observation authority projection digest mismatch"
        )
    if action.get("followup_author_gate_digest") != followup_projection_digest(gate):
        raise PermissionError(
            "follow-up Author observation Author gate digest mismatch"
        )
    if action.get("provider_execution_licensed") is not False:
        raise PermissionError(
            "follow-up Author observation must keep provider unlicensed"
        )
    if action.get("fixture_author_observation_mode") != (
        FOLLOWUP_AUTHOR_OBSERVATION_MODE
    ):
        raise PermissionError(
            "follow-up Author observation action must be fixture-only"
        )
    for field in (
        "author_activation_allowed",
        "author_executor_invoked",
        "model_called",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
        "final_text_included",
    ):
        if action.get(field) is not False:
            raise PermissionError(
                f"follow-up Author observation must keep {field}=False"
            )
    if action.get("author_execution_deferred") is not True:
        raise PermissionError(
            "follow-up Author observation must defer Author execution"
        )
    if action.get("live_validation_not_run") is not True:
        raise PermissionError(
            "follow-up Author observation must not run live validation"
        )


def _citation_eligible_source_ids(
    *,
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    gate: Mapping[str, Any],
) -> tuple[str, ...]:
    ids = list(_texts(authority.get("citation_eligible_source_ids")))
    ids.extend(_texts(gate.get("citation_eligible_source_ids")))
    for item in _mappings(packet.get("citation_eligible")):
        if item.get("source_id") is not None:
            ids.extend(_texts(item.get("source_id")))
    out: list[str] = []
    for item in ids:
        if item not in out:
            out.append(item)
    return tuple(out)


def _unacknowledged_refs(
    refs: Sequence[Mapping[str, Any]],
    acknowledged: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    acknowledged_keys = {_text_key(item) for item in acknowledged}
    out: list[dict[str, Any]] = []
    for ref in refs:
        tokens = _ref_ack_tokens(ref)
        if tokens and tokens.intersection(acknowledged_keys):
            continue
        out.append(dict(ref))
    return tuple(out)


def _ref_ack_tokens(ref: Mapping[str, Any]) -> set[str]:
    values: list[Any] = []
    for key in (
        "requirement_id",
        "source_obligation_id",
        "obligation_id",
        "required_source_class",
        "source_class",
        "status",
        "reason",
    ):
        if ref.get(key) is not None:
            values.append(ref.get(key))
    values.extend(item for item in _texts(ref.get("requirement_ids")))
    return {_text_key(item) for item in values if _text_key(item)}


def _reject_boundary_claims(payload: Mapping[str, Any], *, context: str) -> None:
    for field in _boundary_false_fields():
        if payload.get(field) is True:
            raise PermissionError(f"{context} must keep {field}=False")
    if payload.get("live_validation_not_run") is False:
        raise PermissionError(f"{context} must not run live validation")
    if payload.get("author_execution_deferred") is False:
        raise PermissionError(f"{context} must defer Author execution")


def _reject_raw_text_keys(payload: Mapping[str, Any], *, context: str) -> None:
    for key in (
        "report_text",
        "final_text",
        "raw_text",
        "raw_output",
        "raw_response",
        "model_response",
        "text",
    ):
        if payload.get(key) not in (None, "", [], {}):
            raise PermissionError(f"{context} must not retain raw final text")


def _boundary_false_fields() -> tuple[str, ...]:
    return (
        "provider_execution_licensed",
        "live_provider_call_executed",
        "provider_job_scheduled",
        "provider_job_dispatched",
        "search_executed",
        "retrieval_executed",
        "fetch_executed",
        "model_called",
        "query_generation_changed",
        "retrieval_ranking_filtering_changed",
        "pipeline_orchestrator_domain_logic_changed",
        "search_judgment_rerun",
        "sufficiency_judgment_rechecked",
        "final_answer_packet_rebuilt",
        "final_answer_packet_updated",
        "author_activation_allowed",
        "author_executor_invoked",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "citation_behavior_changed",
        "product_answer_behavior_changed",
        "final_answer_behavior_changed",
        "final_text_included",
    )


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_rebuilt": False,
        "final_answer_packet_updated": False,
        "packet_authority_consumed": True,
        "author_output_observed": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        **followup_closed_flags(
            *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS
        ),
        "final_text_included": False,
        "live_validation_not_run": True,
    }


def _gate_state_closed_false_flags() -> tuple[str, ...]:
    return (
        *FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:],
        *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
        "sufficiency_judgment_rechecked",
        "final_answer_packet_rebuilt",
        "final_answer_packet_updated",
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
    posture = followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
        packet_authority_refs_only=True,
        final_text_retained=False,
    )
    posture["report_hash_only"] = True
    return posture


def _output_fact_summary(facts: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "report_hash": facts.get("report_hash"),
        "report_length": facts.get("report_length"),
        "cited_source_count": len(_texts(facts.get("cited_source_ids"))),
        "mandatory_caveat_acknowledgement_count": len(
            _texts(facts.get("mandatory_caveats_acknowledged"))
        ),
        "prohibited_upgrade_violation_count": len(
            _texts(facts.get("prohibited_upgrade_violations"))
        ),
        "source_bound_unknown_acknowledgement_count": len(
            _texts(facts.get("source_bound_unknowns_acknowledged"))
        ),
        "missing_obligation_acknowledgement_count": len(
            _texts(facts.get("missing_obligations_acknowledged"))
        ),
        "claim_posture_label_count": len(_strings(facts.get("claim_posture_labels"))),
        "fixture_author_note_count": len(_texts(facts.get("fixture_author_notes"))),
        "final_text_included": False,
    }


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
        text = clean_text(item, limit=300)
        if text and text not in out:
            out.append(text)
    return tuple(out)


def _text_key(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _hash_text(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "FOLLOWUP_AUTHOR_OBSERVATION_MODE",
    "FOLLOWUP_AUTHOR_OBSERVATION_REASON",
    "FOLLOWUP_AUTHOR_OBSERVATION_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_OBSERVATION_STAGE",
    "FOLLOWUP_AUTHOR_OBSERVATION_TRACE_KEY",
    "FollowupAuthorObservationActionResult",
    "FollowupAuthorObservationConsumptionRecord",
    "FollowupAuthorObservationObservation",
    "FollowupAuthorObservationRequest",
    "FollowupAuthorObservationResult",
    "build_followup_author_observation_record",
    "derive_followup_author_observation_compliance",
    "execute_followup_author_observation_action",
    "reject_followup_author_observation_boundary_spoof",
]
