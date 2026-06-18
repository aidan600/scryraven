"""Offline follow-up FinalAnswerPacket preparation seam for AG-96I2E/AG-96I3A.

This module derives a packet-level authority record from canonical follow-up
sufficiency recheck state, the current EvidenceLedger projection, and the
current SufficiencyJudgment projection. It never calls Author, providers, search,
retrieval, fetch/read, prompts, models, citation formatters, provider-job
executors, shell processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from core.final_answer_packet import FinalAnswerPacket, SourceObligationStatus
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.followup_deliberation import clean_text, clean_token, safe_json, stable_hash
from core.followup_fixture_boundaries import (
    FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS,
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    followup_closed_flags,
    followup_common_redaction_posture,
    followup_fixture_provenance,
    followup_live_surface_flags,
)
from core.followup_sufficiency_recheck_runtime import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
)

FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION = (
    "followup_final_answer_packet_ag96i2e_v1"
)
FOLLOWUP_FINAL_ANSWER_PACKET_TRACE_KEY = "followup_final_answer_packet_runtime"
FOLLOWUP_FINAL_ANSWER_PACKET_STAGE = "followup_final_answer_packet"
FOLLOWUP_FINAL_ANSWER_PACKET_MODE = (
    "fixture_only_followup_final_answer_packet_prepare"
)
FOLLOWUP_FINAL_ANSWER_PACKET_GATE_REASON = (
    "ag96i2e_fixture_only_final_answer_packet_prepare"
)
FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_SCHEMA_VERSION = (
    "followup_final_answer_packet_readiness_ag96i3o1_v1"
)
FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_TRACE_KEY = (
    "followup_final_answer_packet_readiness_runtime"
)
FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE = (
    "followup_final_answer_packet_readiness"
)
AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE = (
    "ag96i3o1_final_answer_packet_preparation_readiness"
)
FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_GATE_REASON = (
    "ag96i3o1_final_answer_packet_preparation_readiness"
)
FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_SCHEMA_VERSION = (
    "followup_blocked_final_answer_packet_shell_ag96i3o2_v1"
)
FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_TRACE_KEY = (
    "followup_blocked_final_answer_packet_shell_runtime"
)
FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE = (
    "followup_blocked_final_answer_packet_shell"
)
AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE = (
    "ag96i3o2_blocked_final_answer_packet_shell"
)
FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_GATE_REASON = (
    "ag96i3o2_blocked_final_answer_packet_shell"
)

_FORBIDDEN_AUTHORITY_REF_FIELDS = frozenset(
    {
        "citation_eligible_source_ids",
        "citation_eligibility_refs",
        "final_evidence_refs",
        "author_payload_ref",
    }
)
_PRIVATE_VALUE_MARKERS = (
    "api_key",
    "authorization:",
    "bearer ",
    "private-sentinel",
    "provider_payload",
    "raw prompt",
    "raw_prompt",
    "raw_provider",
    "raw_text",
    "secret",
    "sk-",
)


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketRequest:
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
    followup_sufficiency_recheck_id: str
    recheck_id: str
    followup_sufficiency_recheck_observation_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    fixture_execution_mode: str
    execution_mode: str
    evidence_ledger_intake_mode: str
    sufficiency_recheck_mode: str
    evidence_ledger_projection_digest: str
    sufficiency_judgment_digest: str
    followup_sufficiency_recheck_digest: str
    provider_execution_licensed: bool
    final_answer_packet_mode: str
    author_activation_allowed: bool
    citation_rendering_changed: bool
    product_answer_behavior_changed: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION,
            "record_type": "followup_final_answer_packet_request",
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
            "followup_sufficiency_recheck_id": clean_text(
                self.followup_sufficiency_recheck_id,
                limit=220,
            ),
            "recheck_id": clean_text(self.recheck_id, limit=220),
            "followup_sufficiency_recheck_observation_id": clean_text(
                self.followup_sufficiency_recheck_observation_id,
                limit=220,
            ),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [clean_token(item) for item in self.requirement_ids],
            "expected_source_classes": [
                clean_token(item) for item in self.expected_source_classes
            ],
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "execution_mode": clean_token(self.execution_mode),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "sufficiency_recheck_mode": clean_token(self.sufficiency_recheck_mode),
            "evidence_ledger_projection_digest": clean_text(
                self.evidence_ledger_projection_digest,
                limit=120,
            ),
            "sufficiency_judgment_digest": clean_text(
                self.sufficiency_judgment_digest,
                limit=120,
            ),
            "followup_sufficiency_recheck_digest": clean_text(
                self.followup_sufficiency_recheck_digest,
                limit=120,
            ),
            "fixture_only_provenance": _fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "final_answer_packet_mode": clean_token(self.final_answer_packet_mode),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "citation_rendering_changed": bool(self.citation_rendering_changed),
            "product_answer_behavior_changed": bool(
                self.product_answer_behavior_changed
            ),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketResult:
    result_id: str
    status: str
    packet_projection: Mapping[str, Any]
    final_evidence_refs: tuple[Mapping[str, Any], ...]
    citation_eligibility_refs: tuple[Mapping[str, Any], ...]
    packet_authority_payload: Mapping[str, Any]
    answer_readiness_posture: Mapping[str, Any]
    mandatory_caveats: tuple[str, ...]
    prohibited_upgrades: tuple[str, ...]
    missing_required_obligations: tuple[Mapping[str, Any], ...]
    partial_obligations: tuple[Mapping[str, Any], ...]
    satisfied_obligations: tuple[Mapping[str, Any], ...]
    source_bound_unknowns: tuple[Mapping[str, Any], ...]
    unresolved_conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION,
            "record_type": "followup_final_answer_packet_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "packet_projection": safe_json(self.packet_projection),
            "final_evidence_refs": [safe_json(item) for item in self.final_evidence_refs],
            "citation_eligibility_refs": [
                safe_json(item) for item in self.citation_eligibility_refs
            ],
            "packet_authority_payload": safe_json(self.packet_authority_payload),
            "answer_readiness_posture": safe_json(self.answer_readiness_posture),
            "mandatory_caveats": [clean_text(item, limit=300) for item in self.mandatory_caveats],
            "prohibited_upgrades": [
                clean_text(item, limit=300) for item in self.prohibited_upgrades
            ],
            "missing_required_obligations": [
                safe_json(item) for item in self.missing_required_obligations
            ],
            "partial_obligations": [safe_json(item) for item in self.partial_obligations],
            "satisfied_obligations": [
                safe_json(item) for item in self.satisfied_obligations
            ],
            "source_bound_unknowns": [safe_json(item) for item in self.source_bound_unknowns],
            "unresolved_conflicts": [clean_text(item, limit=220) for item in self.unresolved_conflicts],
            "final_answer_packet_prepared": True,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "provider_execution_licensed": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketObservation:
    observation_id: str
    request: FollowupFinalAnswerPacketRequest
    result: FollowupFinalAnswerPacketResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        packet = _mapping(result.get("packet_projection"))
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_FINAL_ANSWER_PACKET_TRACE_KEY,
            "record_type": "followup_final_answer_packet_observation",
            "owner": "FollowupFinalAnswerPacketRuntime",
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
            "followup_sufficiency_recheck_id": request.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": request.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": request.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "execution_mode": request.get("execution_mode"),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": request.get("sufficiency_recheck_mode"),
            "evidence_ledger_projection_digest": request.get(
                "evidence_ledger_projection_digest"
            ),
            "sufficiency_judgment_digest": request.get(
                "sufficiency_judgment_digest"
            ),
            "followup_sufficiency_recheck_digest": request.get(
                "followup_sufficiency_recheck_digest"
            ),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "final_answer_packet_mode": request.get("final_answer_packet_mode"),
            "request": request,
            "result": result,
            "packet_projection": packet,
            "packet_id": packet.get("packet_id"),
            "readiness_status": packet.get("readiness_status"),
            "readiness_reasons": packet.get("readiness_reasons", []),
            "final_evidence_refs": result.get("final_evidence_refs", []),
            "citation_eligibility_refs": result.get("citation_eligibility_refs", []),
            "packet_authority_payload": result.get("packet_authority_payload", {}),
            "answer_readiness_posture": result.get("answer_readiness_posture", {}),
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
            "final_answer_packet_prepared": True,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketConsumptionRecord:
    packet_preparation_id: str
    observation: FollowupFinalAnswerPacketObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_final_answer_packet_consumption_record",
            "owner": "FollowupFinalAnswerPacketRuntime",
            "canonical_state": False,
            "packet_preparation_id": clean_text(
                self.packet_preparation_id,
                limit=220,
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketActionResult:
    record: FollowupFinalAnswerPacketConsumptionRecord
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketReadinessRequest:
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
    followup_sufficiency_recheck_id: str
    recheck_id: str
    followup_sufficiency_recheck_observation_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    fixture_execution_mode: str
    execution_mode: str
    evidence_ledger_intake_mode: str
    sufficiency_recheck_mode: str
    evidence_ledger_projection_digest: str
    sufficiency_judgment_digest: str
    followup_sufficiency_recheck_digest: str
    provider_execution_licensed: bool
    packet_preparation_readiness_mode: str
    canonical_final_answer_packet_mutated: bool
    final_evidence_selected: bool
    citation_eligible: bool
    citations_rendered: bool
    citation_rendering_changed: bool
    citation_behavior_changed: bool
    citation_formatter_invoked: bool
    author_activation_allowed: bool
    author_payload_created: bool
    author_execution_deferred: bool
    analyst_activation_allowed: bool
    analyst_handoff_created: bool
    economist_activation_allowed: bool
    economist_handoff_created: bool
    economist_code_execution_allowed: bool
    answer_ready: bool
    prompt_behavior_changed: bool
    product_answer_behavior_changed: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_SCHEMA_VERSION,
            "record_type": "followup_final_answer_packet_readiness_request",
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
            "followup_sufficiency_recheck_id": clean_text(
                self.followup_sufficiency_recheck_id,
                limit=220,
            ),
            "recheck_id": clean_text(self.recheck_id, limit=220),
            "followup_sufficiency_recheck_observation_id": clean_text(
                self.followup_sufficiency_recheck_observation_id,
                limit=220,
            ),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [clean_token(item) for item in self.requirement_ids],
            "expected_source_classes": [
                clean_token(item) for item in self.expected_source_classes
            ],
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "execution_mode": clean_token(self.execution_mode),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "sufficiency_recheck_mode": clean_token(self.sufficiency_recheck_mode),
            "evidence_ledger_projection_digest": clean_text(
                self.evidence_ledger_projection_digest,
                limit=120,
            ),
            "sufficiency_judgment_digest": clean_text(
                self.sufficiency_judgment_digest,
                limit=120,
            ),
            "followup_sufficiency_recheck_digest": clean_text(
                self.followup_sufficiency_recheck_digest,
                limit=120,
            ),
            "fixture_only_provenance": _readiness_fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "packet_preparation_readiness_mode": clean_token(
                self.packet_preparation_readiness_mode
            ),
            "canonical_final_answer_packet_mutated": bool(
                self.canonical_final_answer_packet_mutated
            ),
            "final_evidence_selected": bool(self.final_evidence_selected),
            "citation_eligible": bool(self.citation_eligible),
            "citations_rendered": bool(self.citations_rendered),
            "citation_rendering_changed": bool(self.citation_rendering_changed),
            "citation_behavior_changed": bool(self.citation_behavior_changed),
            "citation_formatter_invoked": bool(self.citation_formatter_invoked),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "author_payload_created": bool(self.author_payload_created),
            "author_execution_deferred": bool(self.author_execution_deferred),
            "analyst_activation_allowed": bool(self.analyst_activation_allowed),
            "analyst_handoff_created": bool(self.analyst_handoff_created),
            "economist_activation_allowed": bool(self.economist_activation_allowed),
            "economist_handoff_created": bool(self.economist_handoff_created),
            "economist_code_execution_allowed": bool(
                self.economist_code_execution_allowed
            ),
            "answer_ready": bool(self.answer_ready),
            "prompt_behavior_changed": bool(self.prompt_behavior_changed),
            "product_answer_behavior_changed": bool(
                self.product_answer_behavior_changed
            ),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _readiness_behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketReadinessResult:
    result_id: str
    status: str
    preparation_readiness_status: str
    final_answer_activation_blocked: bool
    block_reasons: tuple[str, ...]
    prerequisite_summary: Mapping[str, Any]
    evidence_ledger_counts: Mapping[str, Any]
    source_requirement_status_summary: Mapping[str, Any]
    official_current_custody_status: Mapping[str, Any]
    sufficiency_decision: str | None
    sufficiency_posture: str | None
    final_packet_inputs_summary: Mapping[str, Any]
    mandatory_caveats: tuple[str, ...]
    prohibited_upgrades: tuple[str, ...]
    missing_obligations: tuple[Mapping[str, Any], ...]
    partial_obligations: tuple[Mapping[str, Any], ...]
    satisfied_obligations: tuple[Mapping[str, Any], ...]
    source_bound_unknowns: tuple[Mapping[str, Any], ...]
    unresolved_conflicts: tuple[str, ...]
    ag96i3m2_candidate_summary: Mapping[str, Any]
    ag96i3m2_binding_summary: Mapping[str, Any]
    ag96i3n_recheck_summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_SCHEMA_VERSION,
            "record_type": "followup_final_answer_packet_readiness_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "preparation_readiness_status": clean_token(
                self.preparation_readiness_status
            ),
            "final_answer_activation_blocked": bool(
                self.final_answer_activation_blocked
            ),
            "block_reasons": [
                clean_token(item, limit=220) for item in self.block_reasons
            ],
            "prerequisite_summary": safe_json(self.prerequisite_summary),
            "evidence_ledger_counts": safe_json(self.evidence_ledger_counts),
            "source_requirement_status_summary": safe_json(
                self.source_requirement_status_summary
            ),
            "official_current_custody_status": safe_json(
                self.official_current_custody_status
            ),
            "sufficiency_decision": clean_token(self.sufficiency_decision),
            "sufficiency_posture": clean_token(self.sufficiency_posture),
            "final_packet_inputs_summary": safe_json(
                self.final_packet_inputs_summary
            ),
            "final_answer_allowed": False,
            "mandatory_caveats": [
                clean_token(item, limit=220) for item in self.mandatory_caveats
            ],
            "prohibited_upgrades": [
                clean_token(item, limit=220) for item in self.prohibited_upgrades
            ],
            "missing_obligations": [
                safe_json(item) for item in self.missing_obligations
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
                clean_token(item, limit=220) for item in self.unresolved_conflicts
            ],
            "ag96i3m2_candidate_summary": safe_json(
                self.ag96i3m2_candidate_summary
            ),
            "ag96i3m2_binding_summary": safe_json(self.ag96i3m2_binding_summary),
            "ag96i3n_recheck_summary": safe_json(self.ag96i3n_recheck_summary),
            "canonical_final_answer_packet_mutated": False,
            "final_evidence_selected": False,
            "citation_eligible": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "answer_ready": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "provider_execution_licensed": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketReadinessObservation:
    observation_id: str
    request: FollowupFinalAnswerPacketReadinessRequest
    result: FollowupFinalAnswerPacketReadinessResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_TRACE_KEY,
            "record_type": "followup_final_answer_packet_readiness_observation",
            "owner": "FollowupFinalAnswerPacketReadinessRuntime",
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
            "followup_sufficiency_recheck_id": request.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": request.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": request.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "execution_mode": request.get("execution_mode"),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": request.get("sufficiency_recheck_mode"),
            "evidence_ledger_projection_digest": request.get(
                "evidence_ledger_projection_digest"
            ),
            "sufficiency_judgment_digest": request.get(
                "sufficiency_judgment_digest"
            ),
            "followup_sufficiency_recheck_digest": request.get(
                "followup_sufficiency_recheck_digest"
            ),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "packet_preparation_readiness_mode": request.get(
                "packet_preparation_readiness_mode"
            ),
            "request": request,
            "result": result,
            "preparation_readiness_status": result.get(
                "preparation_readiness_status"
            ),
            "final_answer_activation_blocked": result.get(
                "final_answer_activation_blocked"
            ),
            "block_reasons": result.get("block_reasons", []),
            "prerequisite_summary": result.get("prerequisite_summary", {}),
            "evidence_ledger_counts": result.get("evidence_ledger_counts", {}),
            "source_requirement_status_summary": result.get(
                "source_requirement_status_summary",
                {},
            ),
            "official_current_custody_status": result.get(
                "official_current_custody_status",
                {},
            ),
            "sufficiency_decision": result.get("sufficiency_decision"),
            "sufficiency_posture": result.get("sufficiency_posture"),
            "final_answer_allowed": False,
            "final_packet_inputs_summary": result.get(
                "final_packet_inputs_summary",
                {},
            ),
            "mandatory_caveats": result.get("mandatory_caveats", []),
            "prohibited_upgrades": result.get("prohibited_upgrades", []),
            "missing_obligations": result.get("missing_obligations", []),
            "partial_obligations": result.get("partial_obligations", []),
            "satisfied_obligations": result.get("satisfied_obligations", []),
            "source_bound_unknowns": result.get("source_bound_unknowns", []),
            "unresolved_conflicts": result.get("unresolved_conflicts", []),
            "ag96i3m2_candidate_summary": result.get(
                "ag96i3m2_candidate_summary",
                {},
            ),
            "ag96i3m2_binding_summary": result.get(
                "ag96i3m2_binding_summary",
                {},
            ),
            "ag96i3n_recheck_summary": result.get("ag96i3n_recheck_summary", {}),
            "canonical_final_answer_packet_mutated": False,
            "final_evidence_selected": False,
            "citation_eligible": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "answer_ready": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "behavior_boundary_flags": _readiness_behavior_boundary_flags(),
            "redaction_posture": _readiness_redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketReadinessConsumptionRecord:
    packet_preparation_readiness_id: str
    observation: FollowupFinalAnswerPacketReadinessObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": (
                "followup_final_answer_packet_readiness_consumption_record"
            ),
            "owner": "FollowupFinalAnswerPacketReadinessRuntime",
            "canonical_state": False,
            "packet_preparation_readiness_id": clean_text(
                self.packet_preparation_readiness_id,
                limit=220,
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketReadinessActionResult:
    record: FollowupFinalAnswerPacketReadinessConsumptionRecord
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupBlockedFinalAnswerPacketShellRequest:
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
    followup_sufficiency_recheck_id: str
    recheck_id: str
    followup_sufficiency_recheck_observation_id: str
    packet_preparation_readiness_id: str
    readiness_observation_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    fixture_execution_mode: str
    execution_mode: str
    evidence_ledger_intake_mode: str
    sufficiency_recheck_mode: str
    packet_preparation_readiness_mode: str
    blocked_final_answer_packet_mode: str
    evidence_ledger_projection_digest: str
    sufficiency_judgment_digest: str
    followup_sufficiency_recheck_digest: str
    followup_final_answer_packet_readiness_digest: str
    provider_execution_licensed: bool
    final_evidence_selected: bool
    citation_eligible: bool
    citations_rendered: bool
    citation_rendering_changed: bool
    citation_behavior_changed: bool
    citation_formatter_invoked: bool
    author_activation_allowed: bool
    author_payload_created: bool
    author_execution_deferred: bool
    analyst_activation_allowed: bool
    analyst_handoff_created: bool
    economist_activation_allowed: bool
    economist_handoff_created: bool
    economist_code_execution_allowed: bool
    answer_ready: bool
    prompt_behavior_changed: bool
    product_answer_behavior_changed: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_SCHEMA_VERSION,
            "record_type": "followup_blocked_final_answer_packet_shell_request",
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
            "followup_sufficiency_recheck_id": clean_text(
                self.followup_sufficiency_recheck_id,
                limit=220,
            ),
            "recheck_id": clean_text(self.recheck_id, limit=220),
            "followup_sufficiency_recheck_observation_id": clean_text(
                self.followup_sufficiency_recheck_observation_id,
                limit=220,
            ),
            "packet_preparation_readiness_id": clean_text(
                self.packet_preparation_readiness_id,
                limit=220,
            ),
            "readiness_observation_id": clean_text(
                self.readiness_observation_id,
                limit=220,
            ),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [clean_token(item) for item in self.requirement_ids],
            "expected_source_classes": [
                clean_token(item) for item in self.expected_source_classes
            ],
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "execution_mode": clean_token(self.execution_mode),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "sufficiency_recheck_mode": clean_token(self.sufficiency_recheck_mode),
            "packet_preparation_readiness_mode": clean_token(
                self.packet_preparation_readiness_mode
            ),
            "blocked_final_answer_packet_mode": clean_token(
                self.blocked_final_answer_packet_mode
            ),
            "evidence_ledger_projection_digest": clean_text(
                self.evidence_ledger_projection_digest,
                limit=120,
            ),
            "sufficiency_judgment_digest": clean_text(
                self.sufficiency_judgment_digest,
                limit=120,
            ),
            "followup_sufficiency_recheck_digest": clean_text(
                self.followup_sufficiency_recheck_digest,
                limit=120,
            ),
            "followup_final_answer_packet_readiness_digest": clean_text(
                self.followup_final_answer_packet_readiness_digest,
                limit=120,
            ),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "final_evidence_selected": bool(self.final_evidence_selected),
            "citation_eligible_flag": bool(self.citation_eligible),
            "citations_rendered": bool(self.citations_rendered),
            "citation_rendering_changed": bool(self.citation_rendering_changed),
            "citation_behavior_changed": bool(self.citation_behavior_changed),
            "citation_formatter_invoked": bool(self.citation_formatter_invoked),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "author_payload_created": bool(self.author_payload_created),
            "author_execution_deferred": bool(self.author_execution_deferred),
            "analyst_activation_allowed": bool(self.analyst_activation_allowed),
            "analyst_handoff_created": bool(self.analyst_handoff_created),
            "economist_activation_allowed": bool(self.economist_activation_allowed),
            "economist_handoff_created": bool(self.economist_handoff_created),
            "economist_code_execution_allowed": bool(
                self.economist_code_execution_allowed
            ),
            "answer_ready": bool(self.answer_ready),
            "prompt_behavior_changed": bool(self.prompt_behavior_changed),
            "product_answer_behavior_changed": bool(
                self.product_answer_behavior_changed
            ),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _blocked_shell_behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupBlockedFinalAnswerPacketShellResult:
    result_id: str
    status: str
    blocked_final_answer_packet_shell_id: str
    packet_projection: Mapping[str, Any]
    readiness_block_reasons: tuple[str, ...]
    mandatory_caveats: tuple[str, ...]
    prohibited_upgrades: tuple[str, ...]
    missing_obligations: tuple[Mapping[str, Any], ...]
    partial_obligations: tuple[Mapping[str, Any], ...]
    satisfied_obligations: tuple[Mapping[str, Any], ...]
    source_bound_unknowns: tuple[Mapping[str, Any], ...]
    unresolved_conflicts: tuple[str, ...]
    final_packet_inputs_summary: Mapping[str, Any]
    official_current_custody_status: Mapping[str, Any]
    ag96i3m2_candidate_summary: Mapping[str, Any]
    ag96i3m2_binding_summary: Mapping[str, Any]
    ag96i3n_recheck_summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        packet = _mapping(self.packet_projection)
        return {
            "schema_version": FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_SCHEMA_VERSION,
            "record_type": "followup_blocked_final_answer_packet_shell_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "blocked_final_answer_packet_shell_id": clean_text(
                self.blocked_final_answer_packet_shell_id,
                limit=220,
            ),
            "packet_projection": safe_json(packet),
            "packet_id": packet.get("packet_id"),
            "readiness_status": packet.get("readiness_status"),
            "readiness_reasons": packet.get("readiness_reasons", []),
            "readiness_block_reasons": [
                clean_token(item, limit=220) for item in self.readiness_block_reasons
            ],
            "final_answer_allowed": False,
            "answer_ready": False,
            "evidence_allowed": [],
            "evidence_excluded": [],
            "author_evidence": [],
            "citation_eligible": [],
            "citation_ineligible": [],
            "author_input_refs": {},
            "mandatory_caveats": [
                clean_token(item, limit=220) for item in self.mandatory_caveats
            ],
            "prohibited_upgrades": [
                clean_token(item, limit=220) for item in self.prohibited_upgrades
            ],
            "missing_obligations": [
                safe_json(item) for item in self.missing_obligations
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
                clean_token(item, limit=220) for item in self.unresolved_conflicts
            ],
            "final_packet_inputs_summary": safe_json(
                self.final_packet_inputs_summary
            ),
            "official_current_custody_status": safe_json(
                self.official_current_custody_status
            ),
            "ag96i3m2_candidate_summary": safe_json(
                self.ag96i3m2_candidate_summary
            ),
            "ag96i3m2_binding_summary": safe_json(self.ag96i3m2_binding_summary),
            "ag96i3n_recheck_summary": safe_json(self.ag96i3n_recheck_summary),
            "canonical_final_answer_packet_mutated": True,
            "final_answer_packet_updated": True,
            "final_answer_packet_rebuilt": True,
            "blocked_final_answer_packet_shell_activated": True,
            "final_evidence_selected": False,
            "citation_eligible_flag": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "not_role_consumption_payload": True,
            "final_evidence_selection_deferred": True,
            "citation_eligibility_deferred": True,
        }


@dataclass(frozen=True, slots=True)
class FollowupBlockedFinalAnswerPacketShellObservation:
    observation_id: str
    request: FollowupBlockedFinalAnswerPacketShellRequest
    result: FollowupBlockedFinalAnswerPacketShellResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        packet = _mapping(result.get("packet_projection"))
        return {
            "schema_version": FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_TRACE_KEY,
            "record_type": "followup_blocked_final_answer_packet_shell_observation",
            "owner": "FollowupBlockedFinalAnswerPacketShellRuntime",
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
            "followup_sufficiency_recheck_id": request.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": request.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": request.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": request.get(
                "packet_preparation_readiness_id"
            ),
            "readiness_observation_id": request.get("readiness_observation_id"),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "execution_mode": request.get("execution_mode"),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": request.get("sufficiency_recheck_mode"),
            "packet_preparation_readiness_mode": request.get(
                "packet_preparation_readiness_mode"
            ),
            "blocked_final_answer_packet_mode": request.get(
                "blocked_final_answer_packet_mode"
            ),
            "evidence_ledger_projection_digest": request.get(
                "evidence_ledger_projection_digest"
            ),
            "sufficiency_judgment_digest": request.get(
                "sufficiency_judgment_digest"
            ),
            "followup_sufficiency_recheck_digest": request.get(
                "followup_sufficiency_recheck_digest"
            ),
            "followup_final_answer_packet_readiness_digest": request.get(
                "followup_final_answer_packet_readiness_digest"
            ),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "request": request,
            "result": result,
            "blocked_final_answer_packet_shell_id": result.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "packet_projection": packet,
            "packet_id": packet.get("packet_id"),
            "readiness_status": packet.get("readiness_status"),
            "readiness_reasons": packet.get("readiness_reasons", []),
            "readiness_block_reasons": result.get("readiness_block_reasons", []),
            "final_answer_allowed": False,
            "answer_ready": False,
            "evidence_allowed": [],
            "evidence_excluded": [],
            "author_evidence": [],
            "citation_eligible": [],
            "citation_ineligible": [],
            "author_input_refs": {},
            "mandatory_caveats": result.get("mandatory_caveats", []),
            "prohibited_upgrades": result.get("prohibited_upgrades", []),
            "missing_obligations": result.get("missing_obligations", []),
            "partial_obligations": result.get("partial_obligations", []),
            "satisfied_obligations": result.get("satisfied_obligations", []),
            "source_bound_unknowns": result.get("source_bound_unknowns", []),
            "unresolved_conflicts": result.get("unresolved_conflicts", []),
            "final_packet_inputs_summary": result.get(
                "final_packet_inputs_summary",
                {},
            ),
            "official_current_custody_status": result.get(
                "official_current_custody_status",
                {},
            ),
            "ag96i3m2_candidate_summary": result.get(
                "ag96i3m2_candidate_summary",
                {},
            ),
            "ag96i3m2_binding_summary": result.get(
                "ag96i3m2_binding_summary",
                {},
            ),
            "ag96i3n_recheck_summary": result.get("ag96i3n_recheck_summary", {}),
            "canonical_final_answer_packet_mutated": True,
            "final_answer_packet_updated": True,
            "final_answer_packet_rebuilt": True,
            "blocked_final_answer_packet_shell_activated": True,
            "final_evidence_selected": False,
            "citation_eligible_flag": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "not_role_consumption_payload": True,
            "final_evidence_selection_deferred": True,
            "citation_eligibility_deferred": True,
            "behavior_boundary_flags": _blocked_shell_behavior_boundary_flags(),
            "redaction_posture": _blocked_shell_redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupBlockedFinalAnswerPacketShellConsumptionRecord:
    blocked_final_answer_packet_shell_id: str
    observation: FollowupBlockedFinalAnswerPacketShellObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": (
                "followup_blocked_final_answer_packet_shell_consumption_record"
            ),
            "owner": "FollowupBlockedFinalAnswerPacketShellRuntime",
            "canonical_state": False,
            "blocked_final_answer_packet_shell_id": clean_text(
                self.blocked_final_answer_packet_shell_id,
                limit=220,
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupBlockedFinalAnswerPacketShellActionResult:
    record: FollowupBlockedFinalAnswerPacketShellConsumptionRecord
    observation: Any


def execute_followup_final_answer_packet_prepare_action(
    action: Any,
    *,
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupFinalAnswerPacketActionResult:
    """Execute the fixture-only packet adapter for one authorized action."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
        stage=FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED
        ),
    )
    record = build_followup_final_answer_packet_record(
        action_inputs=authorized.inputs,
        followup_sufficiency_recheck_state=followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        followup_evidence_intake_state=followup_evidence_intake_state,
    )
    return FollowupFinalAnswerPacketActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_final_answer_packet_state": record.to_dict()},
        ),
    )


def execute_followup_final_answer_packet_readiness_action(
    action: Any,
    *,
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupFinalAnswerPacketReadinessActionResult:
    """Execute the AG-96I3O1 preparation-readiness adapter."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_READINESS,
        stage=FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_PREPARED
        ),
    )
    record = build_followup_final_answer_packet_readiness_record(
        action_inputs=authorized.inputs,
        followup_sufficiency_recheck_state=followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        followup_evidence_intake_state=followup_evidence_intake_state,
    )
    _ensure_no_private_payload(record.to_dict())
    return FollowupFinalAnswerPacketReadinessActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=(
                ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_PREPARED
            ),
            status=RunStageStatus.COMPLETED,
            payload={
                "followup_final_answer_packet_readiness_state": record.to_dict()
            },
        ),
    )


def execute_followup_blocked_final_answer_packet_shell_action(
    action: Any,
    *,
    followup_final_answer_packet_readiness_state: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupBlockedFinalAnswerPacketShellActionResult:
    """Execute the AG-96I3O2 blocked canonical packet shell adapter."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
        stage=FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_PREPARED
        ),
    )
    record = build_followup_blocked_final_answer_packet_shell_record(
        action_inputs=authorized.inputs,
        followup_final_answer_packet_readiness_state=(
            followup_final_answer_packet_readiness_state
        ),
        followup_sufficiency_recheck_state=followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        followup_evidence_intake_state=followup_evidence_intake_state,
    )
    _ensure_no_private_payload(record.to_dict())
    return FollowupBlockedFinalAnswerPacketShellActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=(
                ObservationType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_PREPARED
            ),
            status=RunStageStatus.COMPLETED,
            payload={
                "followup_blocked_final_answer_packet_shell_state": record.to_dict()
            },
        ),
    )


def build_followup_final_answer_packet_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupFinalAnswerPacketConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    recheck = _mapping(safe_json(followup_sufficiency_recheck_state))
    sufficiency = _mapping(safe_json(sufficiency_judgment_projection))
    ledger = _mapping(safe_json(evidence_ledger_projection))
    intake = _mapping(safe_json(followup_evidence_intake_state))
    _validate_recheck_state(recheck)
    _validate_sufficiency_projection(sufficiency)
    _validate_ledger_projection(ledger)
    _validate_intake_state(intake, action)
    _validate_action_inputs(action, recheck, sufficiency, ledger, intake)

    final_evidence = _eligible_final_evidence_refs(
        ledger,
        action_inputs=action,
        recheck_state=recheck,
    )
    packet_sufficiency = _packet_sufficiency_projection(sufficiency, recheck)
    packet = build_final_answer_packet(
        run_id=str(action.get("run_id") or recheck.get("run_id") or ""),
        final_evidence=final_evidence,
        author_evidence=final_evidence,
        ordered_sources=(),
        unique_source_urls=_unique_source_urls(final_evidence),
        final_answer_source_telemetry={},
        source_obligation_projection=ledger,
        answer_contract_projection=None,
        run_contract_projection=None,
        sufficiency_judgment_projection=packet_sufficiency,
        query_lineage_refs={
            "followup_final_answer_packet": {
                "authority": "RunKernel.FollowupFinalAnswerPacket",
                "recheck_id": action.get("recheck_id"),
                "evidence_ledger_projection_digest": action.get(
                    "evidence_ledger_projection_digest"
                ),
            }
        },
        evidence_sufficient=False,
        corpus_weak=True,
        failure_card_payload={"show": False, "reason": None},
        conflicts_present=bool(sufficiency.get("unresolved_conflicts")),
        synth_was_insufficient=True,
        author_notes=None,
    )
    packet = _with_fixture_packet_boundaries(packet)
    packet_projection = packet.to_dict()
    authority_payload = _packet_authority_payload(packet)
    request = FollowupFinalAnswerPacketRequest(
        request_id=f"followup-final-answer-packet-request:{action.get('recheck_id')}",
        run_id=str(action.get("run_id") or ""),
        checkpoint_id=str(action.get("checkpoint_id") or ""),
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
        followup_sufficiency_recheck_id=str(
            action.get("followup_sufficiency_recheck_id") or ""
        ),
        recheck_id=str(action.get("recheck_id") or ""),
        followup_sufficiency_recheck_observation_id=str(
            action.get("followup_sufficiency_recheck_observation_id") or ""
        ),
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        execution_mode=str(
            action.get("execution_mode")
            or action.get("fixture_execution_mode")
            or ""
        ),
        evidence_ledger_intake_mode=str(action.get("evidence_ledger_intake_mode") or ""),
        sufficiency_recheck_mode=str(action.get("sufficiency_recheck_mode") or ""),
        evidence_ledger_projection_digest=str(
            action.get("evidence_ledger_projection_digest") or ""
        ),
        sufficiency_judgment_digest=str(action.get("sufficiency_judgment_digest") or ""),
        followup_sufficiency_recheck_digest=str(
            action.get("followup_sufficiency_recheck_digest") or ""
        ),
        provider_execution_licensed=False,
        final_answer_packet_mode=FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
        author_activation_allowed=False,
        citation_rendering_changed=False,
        product_answer_behavior_changed=False,
        live_validation_not_run=True,
    )
    result = FollowupFinalAnswerPacketResult(
        result_id=f"followup-final-answer-packet-result:{action.get('recheck_id')}",
        status="fixture_final_answer_packet_prepared",
        packet_projection=packet_projection,
        final_evidence_refs=tuple(packet_projection.get("evidence_allowed") or ()),
        citation_eligibility_refs=tuple(
            tuple(packet_projection.get("citation_eligible") or ())
            + tuple(packet_projection.get("citation_ineligible") or ())
        ),
        packet_authority_payload=authority_payload,
        answer_readiness_posture={
            "readiness_status": packet_projection.get("readiness_status"),
            "readiness_reasons": packet_projection.get("readiness_reasons", []),
            "final_answer_allowed": packet_projection.get("final_answer_allowed"),
            "final_answer_posture": packet_projection.get("final_answer_posture"),
            "sufficiency_decision": packet_projection.get("sufficiency_decision"),
        },
        mandatory_caveats=tuple(
            _strings(packet_projection.get("mandatory_caveats"))
        ),
        prohibited_upgrades=tuple(
            _strings(packet_projection.get("prohibited_upgrades"))
        ),
        missing_required_obligations=tuple(
            _mappings(packet_projection.get("missing_required_obligations"))
            or _missing_source_obligations(packet)
        ),
        partial_obligations=tuple(_mappings(packet_projection.get("partial_obligations"))),
        satisfied_obligations=tuple(
            _mappings(packet_projection.get("satisfied_obligations"))
        ),
        source_bound_unknowns=tuple(
            _mappings(packet_projection.get("source_bound_numeric_unknowns"))
        ),
        unresolved_conflicts=tuple(_strings(sufficiency.get("unresolved_conflicts"))),
    )
    observation = FollowupFinalAnswerPacketObservation(
        observation_id=f"followup-final-answer-packet-observation:{action.get('recheck_id')}",
        request=request,
        result=result,
    )
    return FollowupFinalAnswerPacketConsumptionRecord(
        packet_preparation_id=(
            f"followup-final-answer-packet:{action.get('recheck_id')}"
        ),
        observation=observation,
    )


def build_followup_final_answer_packet_readiness_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupFinalAnswerPacketReadinessConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    recheck = _mapping(safe_json(followup_sufficiency_recheck_state))
    sufficiency = _mapping(safe_json(sufficiency_judgment_projection))
    ledger = _mapping(safe_json(evidence_ledger_projection))
    intake = _mapping(safe_json(followup_evidence_intake_state))
    _validate_readiness_recheck_state(recheck)
    _validate_sufficiency_projection(sufficiency)
    _validate_ledger_projection(ledger)
    _validate_readiness_intake_state(intake, action)
    _validate_readiness_action_inputs(action, recheck, sufficiency, ledger, intake)

    statuses = _readiness_source_requirement_statuses(recheck, ledger)
    status_summary = _readiness_status_summary(statuses)
    packet_inputs = _mapping(sufficiency.get("final_packet_inputs"))
    missing, partial, satisfied = _readiness_obligation_lists(
        statuses,
        packet_inputs=packet_inputs,
        sufficiency=sufficiency,
    )
    source_bound_unknowns = _readiness_source_bound_unknowns(packet_inputs, sufficiency)
    unresolved_conflicts = tuple(
        dict.fromkeys(
            _strings(sufficiency.get("unresolved_conflicts"))
            + _strings(recheck.get("unresolved_conflicts"))
        )
    )
    mandatory = tuple(
        dict.fromkeys(
            _strings(packet_inputs.get("mandatory_caveats"))
            + _strings(sufficiency.get("mandatory_caveats"))
            + _strings(recheck.get("mandatory_caveats"))
        )
    )
    prohibited = tuple(
        dict.fromkeys(
            _strings(packet_inputs.get("prohibited_upgrades"))
            + _strings(sufficiency.get("prohibited_upgrades"))
            + _strings(recheck.get("prohibited_upgrades"))
            + (
                "do_not_treat_preparation_readiness_as_final_answer_packet",
                "do_not_create_citation_eligibility_from_readiness",
                "do_not_select_final_evidence_from_readiness",
                "do_not_activate_author_from_preparation_readiness",
            )
        )
    )
    evidence_counts = _readiness_evidence_ledger_counts(ledger)
    official_current = _mapping(recheck.get("official_current_custody_status"))
    custody_present = bool(evidence_counts.get("custody_record_count")) and (
        status_summary.get("satisfied", 0) > 0
    )
    sufficiency_rechecked = (
        _mapping(recheck.get("behavior_boundary_flags")).get(
            "sufficiency_judgment_rechecked"
        )
        is True
    )
    block_reasons = _readiness_block_reasons(
        custody_present=custody_present,
        status_summary=status_summary,
        missing=missing,
        partial=partial,
        source_bound_unknowns=source_bound_unknowns,
        unresolved_conflicts=unresolved_conflicts,
    )
    preparation_status = (
        "prerequisites_present_activation_blocked"
        if custody_present
        and status_summary.get("all_satisfied") is True
        and not source_bound_unknowns
        and not unresolved_conflicts
        else "blocked_missing_or_partial_prerequisites"
    )
    prerequisite_summary = {
        "custody_present": custody_present,
        "sufficiency_rechecked": sufficiency_rechecked,
        "obligations_satisfied": status_summary.get("all_satisfied") is True,
        "obligations_partial": bool(partial),
        "obligations_missing": bool(missing),
        "caveats_present": bool(mandatory),
        "prohibited_upgrades_present": bool(prohibited),
        "unresolved_conflicts_present": bool(unresolved_conflicts),
        "source_bound_unknowns_present": bool(source_bound_unknowns),
        "final_answer_activation_blocked": True,
        "block_reasons": list(block_reasons),
    }
    request = FollowupFinalAnswerPacketReadinessRequest(
        request_id=f"followup-final-answer-packet-readiness-request:{action.get('recheck_id')}",
        run_id=str(action.get("run_id") or ""),
        checkpoint_id=str(action.get("checkpoint_id") or ""),
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
        followup_sufficiency_recheck_id=str(
            action.get("followup_sufficiency_recheck_id") or ""
        ),
        recheck_id=str(action.get("recheck_id") or ""),
        followup_sufficiency_recheck_observation_id=str(
            action.get("followup_sufficiency_recheck_observation_id") or ""
        ),
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        execution_mode=str(
            action.get("execution_mode")
            or action.get("fixture_execution_mode")
            or ""
        ),
        evidence_ledger_intake_mode=str(action.get("evidence_ledger_intake_mode") or ""),
        sufficiency_recheck_mode=str(action.get("sufficiency_recheck_mode") or ""),
        evidence_ledger_projection_digest=str(
            action.get("evidence_ledger_projection_digest") or ""
        ),
        sufficiency_judgment_digest=str(action.get("sufficiency_judgment_digest") or ""),
        followup_sufficiency_recheck_digest=str(
            action.get("followup_sufficiency_recheck_digest") or ""
        ),
        provider_execution_licensed=False,
        packet_preparation_readiness_mode=(
            AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
        ),
        canonical_final_answer_packet_mutated=False,
        final_evidence_selected=False,
        citation_eligible=False,
        citations_rendered=False,
        citation_rendering_changed=False,
        citation_behavior_changed=False,
        citation_formatter_invoked=False,
        author_activation_allowed=False,
        author_payload_created=False,
        author_execution_deferred=True,
        analyst_activation_allowed=False,
        analyst_handoff_created=False,
        economist_activation_allowed=False,
        economist_handoff_created=False,
        economist_code_execution_allowed=False,
        answer_ready=False,
        prompt_behavior_changed=False,
        product_answer_behavior_changed=False,
        live_validation_not_run=True,
    )
    result = FollowupFinalAnswerPacketReadinessResult(
        result_id=f"followup-final-answer-packet-readiness-result:{action.get('recheck_id')}",
        status="preparation_readiness_recorded",
        preparation_readiness_status=preparation_status,
        final_answer_activation_blocked=True,
        block_reasons=block_reasons,
        prerequisite_summary=prerequisite_summary,
        evidence_ledger_counts=evidence_counts,
        source_requirement_status_summary=status_summary,
        official_current_custody_status=official_current,
        sufficiency_decision=(
            clean_token(sufficiency.get("decision"))
            or clean_token(packet_inputs.get("decision"))
        ),
        sufficiency_posture=(
            clean_token(sufficiency.get("final_answer_posture"))
            or clean_token(recheck.get("fixture_sufficiency_posture"))
        ),
        final_packet_inputs_summary=_final_packet_inputs_summary(packet_inputs),
        mandatory_caveats=mandatory,
        prohibited_upgrades=prohibited,
        missing_obligations=missing,
        partial_obligations=partial,
        satisfied_obligations=satisfied,
        source_bound_unknowns=source_bound_unknowns,
        unresolved_conflicts=unresolved_conflicts,
        ag96i3m2_candidate_summary=_mapping(
            recheck.get("ag96i3m2_admission_review_candidate")
        ),
        ag96i3m2_binding_summary=_mapping(
            recheck.get("ag96i3m2_evidence_ledger_intake_binding")
        ),
        ag96i3n_recheck_summary=_ag96i3n_recheck_summary(
            recheck,
            status_summary=status_summary,
        ),
    )
    observation = FollowupFinalAnswerPacketReadinessObservation(
        observation_id=f"followup-final-answer-packet-readiness-observation:{action.get('recheck_id')}",
        request=request,
        result=result,
    )
    record = FollowupFinalAnswerPacketReadinessConsumptionRecord(
        packet_preparation_readiness_id=(
            f"followup-final-answer-packet-readiness:{action.get('recheck_id')}"
        ),
        observation=observation,
    )
    _ensure_no_private_payload(record.to_dict())
    return record


def build_followup_blocked_final_answer_packet_shell_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_final_answer_packet_readiness_state: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupBlockedFinalAnswerPacketShellConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    readiness = _mapping(safe_json(followup_final_answer_packet_readiness_state))
    recheck = _mapping(safe_json(followup_sufficiency_recheck_state))
    sufficiency = _mapping(safe_json(sufficiency_judgment_projection))
    ledger = _mapping(safe_json(evidence_ledger_projection))
    intake = _mapping(safe_json(followup_evidence_intake_state))
    _validate_readiness_recheck_state(recheck)
    _validate_sufficiency_projection(sufficiency)
    _validate_ledger_projection(ledger)
    _validate_readiness_intake_state(intake, action)
    _validate_blocked_shell_readiness_state(readiness, action)
    _validate_blocked_shell_action_inputs(
        action,
        readiness,
        recheck,
        sufficiency,
        ledger,
        intake,
    )

    shell_id = str(action.get("blocked_final_answer_packet_shell_id") or "")
    readiness_id = str(action.get("packet_preparation_readiness_id") or "")
    readiness_observation_id = str(action.get("readiness_observation_id") or "")
    readiness_block_reasons = tuple(
        dict.fromkeys(_strings(readiness.get("block_reasons")))
    )
    mandatory = tuple(dict.fromkeys(_strings(readiness.get("mandatory_caveats"))))
    prohibited = tuple(
        dict.fromkeys(
            _strings(readiness.get("prohibited_upgrades"))
            + (
                "do_not_treat_blocked_shell_as_author_input",
                "do_not_select_final_evidence_from_blocked_shell",
                "do_not_create_citation_eligibility_from_blocked_shell",
                "do_not_activate_roles_from_blocked_shell",
            )
        )
    )
    missing = _dedupe_mappings(_mappings(readiness.get("missing_obligations")))
    partial = _dedupe_mappings(_mappings(readiness.get("partial_obligations")))
    satisfied = _dedupe_mappings(_mappings(readiness.get("satisfied_obligations")))
    source_bound_unknowns = _dedupe_mappings(
        _mappings(readiness.get("source_bound_unknowns"))
    )
    unresolved_conflicts = tuple(
        dict.fromkeys(_strings(readiness.get("unresolved_conflicts")))
    )
    final_packet_inputs_summary = _strip_forbidden_authority_refs(
        _mapping(readiness.get("final_packet_inputs_summary"))
    )
    official_current = _mapping(readiness.get("official_current_custody_status"))
    packet_projection = _blocked_shell_packet_projection(
        action=action,
        readiness=readiness,
        shell_id=shell_id,
        readiness_id=readiness_id,
        readiness_observation_id=readiness_observation_id,
        readiness_block_reasons=readiness_block_reasons,
        mandatory_caveats=mandatory,
        prohibited_upgrades=prohibited,
        missing_obligations=missing,
        partial_obligations=partial,
        satisfied_obligations=satisfied,
        source_bound_unknowns=source_bound_unknowns,
        unresolved_conflicts=unresolved_conflicts,
        final_packet_inputs_summary=final_packet_inputs_summary,
        official_current_custody_status=official_current,
    )
    request = FollowupBlockedFinalAnswerPacketShellRequest(
        request_id=f"followup-blocked-final-answer-packet-shell-request:{readiness_id}",
        run_id=str(action.get("run_id") or ""),
        checkpoint_id=str(action.get("checkpoint_id") or ""),
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
        followup_sufficiency_recheck_id=str(
            action.get("followup_sufficiency_recheck_id") or ""
        ),
        recheck_id=str(action.get("recheck_id") or ""),
        followup_sufficiency_recheck_observation_id=str(
            action.get("followup_sufficiency_recheck_observation_id") or ""
        ),
        packet_preparation_readiness_id=readiness_id,
        readiness_observation_id=readiness_observation_id,
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        execution_mode=str(
            action.get("execution_mode")
            or action.get("fixture_execution_mode")
            or ""
        ),
        evidence_ledger_intake_mode=str(action.get("evidence_ledger_intake_mode") or ""),
        sufficiency_recheck_mode=str(action.get("sufficiency_recheck_mode") or ""),
        packet_preparation_readiness_mode=(
            AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
        ),
        blocked_final_answer_packet_mode=(
            AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
        ),
        evidence_ledger_projection_digest=str(
            action.get("evidence_ledger_projection_digest") or ""
        ),
        sufficiency_judgment_digest=str(action.get("sufficiency_judgment_digest") or ""),
        followup_sufficiency_recheck_digest=str(
            action.get("followup_sufficiency_recheck_digest") or ""
        ),
        followup_final_answer_packet_readiness_digest=str(
            action.get("followup_final_answer_packet_readiness_digest") or ""
        ),
        provider_execution_licensed=False,
        final_evidence_selected=False,
        citation_eligible=False,
        citations_rendered=False,
        citation_rendering_changed=False,
        citation_behavior_changed=False,
        citation_formatter_invoked=False,
        author_activation_allowed=False,
        author_payload_created=False,
        author_execution_deferred=True,
        analyst_activation_allowed=False,
        analyst_handoff_created=False,
        economist_activation_allowed=False,
        economist_handoff_created=False,
        economist_code_execution_allowed=False,
        answer_ready=False,
        prompt_behavior_changed=False,
        product_answer_behavior_changed=False,
        live_validation_not_run=True,
    )
    result = FollowupBlockedFinalAnswerPacketShellResult(
        result_id=f"followup-blocked-final-answer-packet-shell-result:{readiness_id}",
        status="blocked_final_answer_packet_shell_activated",
        blocked_final_answer_packet_shell_id=shell_id,
        packet_projection=packet_projection,
        readiness_block_reasons=readiness_block_reasons,
        mandatory_caveats=mandatory,
        prohibited_upgrades=prohibited,
        missing_obligations=missing,
        partial_obligations=partial,
        satisfied_obligations=satisfied,
        source_bound_unknowns=source_bound_unknowns,
        unresolved_conflicts=unresolved_conflicts,
        final_packet_inputs_summary=final_packet_inputs_summary,
        official_current_custody_status=official_current,
        ag96i3m2_candidate_summary=_mapping(
            readiness.get("ag96i3m2_candidate_summary")
        ),
        ag96i3m2_binding_summary=_mapping(
            readiness.get("ag96i3m2_binding_summary")
        ),
        ag96i3n_recheck_summary=_mapping(readiness.get("ag96i3n_recheck_summary")),
    )
    observation = FollowupBlockedFinalAnswerPacketShellObservation(
        observation_id=f"followup-blocked-final-answer-packet-shell-observation:{readiness_id}",
        request=request,
        result=result,
    )
    record = FollowupBlockedFinalAnswerPacketShellConsumptionRecord(
        blocked_final_answer_packet_shell_id=shell_id,
        observation=observation,
    )
    _ensure_no_private_payload(record.to_dict())
    return record


def followup_projection_digest(projection: Mapping[str, Any]) -> str:
    return stable_hash(safe_json(projection))


def _blocked_shell_packet_projection(
    *,
    action: Mapping[str, Any],
    readiness: Mapping[str, Any],
    shell_id: str,
    readiness_id: str,
    readiness_observation_id: str,
    readiness_block_reasons: Sequence[str],
    mandatory_caveats: Sequence[str],
    prohibited_upgrades: Sequence[str],
    missing_obligations: Sequence[Mapping[str, Any]],
    partial_obligations: Sequence[Mapping[str, Any]],
    satisfied_obligations: Sequence[Mapping[str, Any]],
    source_bound_unknowns: Sequence[Mapping[str, Any]],
    unresolved_conflicts: Sequence[str],
    final_packet_inputs_summary: Mapping[str, Any],
    official_current_custody_status: Mapping[str, Any],
) -> dict[str, Any]:
    packet_id = f"blocked-final-answer-packet-shell:{readiness_id}"
    reasons = tuple(
        dict.fromkeys(
            (
                "ag96i3o2_blocked_packet_shell",
                "final_evidence_selection_deferred",
                "citation_eligibility_deferred",
                "role_handoffs_closed",
            )
            + tuple(readiness_block_reasons)
        )
    )
    packet = FinalAnswerPacket(
        packet_id=packet_id,
        evidence_records=(),
        citation_records=(),
        source_obligations=(),
        official_current_custody_summary=official_current_custody_status,
        sufficiency_decision=readiness.get("sufficiency_decision"),
        final_answer_posture=readiness.get("sufficiency_posture"),
        final_answer_allowed=False,
        required_obligations_satisfied=(
            _mapping(readiness.get("prerequisite_summary")).get(
                "obligations_satisfied"
            )
            is True
        ),
        missing_required_obligations=tuple(missing_obligations),
        partial_obligations=tuple(partial_obligations),
        satisfied_obligations=tuple(satisfied_obligations),
        source_bound_numeric_unknowns=tuple(source_bound_unknowns),
        source_bound_numeric_resolutions=(),
        behavior_boundary_flags=_blocked_shell_behavior_boundary_flags(),
        claim_postures=(),
        mandatory_caveats=tuple(mandatory_caveats),
        prohibited_upgrades=tuple(prohibited_upgrades),
        author_input_refs={},
        query_lineage_refs={},
        readiness_status="blocked",
        readiness_reasons=reasons,
    )
    projection = packet.to_dict()
    projection.update(
        {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "blocked_final_answer_packet_shell_id": shell_id,
            "packet_preparation_readiness_id": readiness_id,
            "packet_preparation_readiness_observation_id": (
                readiness_observation_id
            ),
            "readiness_observation_id": readiness_observation_id,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "evidence_ledger_intake_mode": action.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": action.get("sufficiency_recheck_mode"),
            "evidence_ledger_projection_digest": action.get(
                "evidence_ledger_projection_digest"
            ),
            "sufficiency_judgment_digest": action.get(
                "sufficiency_judgment_digest"
            ),
            "followup_sufficiency_recheck_digest": action.get(
                "followup_sufficiency_recheck_digest"
            ),
            "followup_final_answer_packet_readiness_digest": action.get(
                "followup_final_answer_packet_readiness_digest"
            ),
            "readiness_block_reasons": list(readiness_block_reasons),
            "missing_obligations": list(missing_obligations),
            "source_bound_unknowns": list(source_bound_unknowns),
            "final_packet_inputs_summary": safe_json(final_packet_inputs_summary),
            "official_current_custody_status": safe_json(
                official_current_custody_status
            ),
            "bounded_ag96i3m2_summary": safe_json(
                readiness.get("ag96i3m2_candidate_summary")
            ),
            "bounded_ag96i3n_summary": safe_json(
                readiness.get("ag96i3n_recheck_summary")
            ),
            "answer_ready": False,
            "author_evidence": [],
            "final_evidence_selected": False,
            "citation_eligible_flag": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_payload_created": False,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "not_role_consumption_payload": True,
            "final_evidence_selection_deferred": True,
            "citation_eligibility_deferred": True,
            "trace_mode": "final_answer_packet_blocked_shell_authority_state",
        }
    )
    return _strip_forbidden_authority_refs(projection)


def _packet_sufficiency_projection(
    sufficiency: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
) -> dict[str, Any]:
    projection = dict(sufficiency)
    packet_inputs = _mapping(projection.get("final_packet_inputs"))
    mandatory = tuple(
        dict.fromkeys(
            _strings(packet_inputs.get("mandatory_caveats"))
            + _strings(projection.get("mandatory_caveats"))
            + _strings(recheck_state.get("mandatory_caveats"))
            + ("fixture_only_final_answer_packet_author_deferred",)
        )
    )
    prohibited = tuple(
        dict.fromkeys(
            _strings(packet_inputs.get("prohibited_upgrades"))
            + _strings(projection.get("prohibited_upgrades"))
            + _strings(recheck_state.get("prohibited_upgrades"))
            + (
                "do_not_activate_author_from_fixture_only_final_answer_packet",
                "do_not_convert_fixture_packet_to_product_answer_readiness",
            )
        )
    )
    packet_inputs.update(
        {
            "final_answer_allowed": False,
            "readiness_status": "blocked",
            "readiness_reasons": list(
                dict.fromkeys(
                    _strings(packet_inputs.get("readiness_reasons"))
                    + _strings(projection.get("readiness_reasons"))
                    + (
                        "fixture_only_final_answer_packet_author_deferred",
                        "product_answer_behavior_closed",
                    )
                )
            ),
            "mandatory_caveats": list(mandatory),
            "prohibited_upgrades": list(prohibited),
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "behavior_boundary_flags": {
                **_mapping(packet_inputs.get("behavior_boundary_flags")),
                **_behavior_boundary_flags(),
            },
        }
    )
    projection["final_answer_allowed"] = False
    projection["final_packet_inputs"] = packet_inputs
    projection["mandatory_caveats"] = list(mandatory)
    projection["prohibited_upgrades"] = list(prohibited)
    projection["author_activation_allowed"] = False
    projection["citation_behavior_changed"] = False
    projection["live_validation_not_run"] = True
    return projection


def _eligible_final_evidence_refs(
    ledger: Mapping[str, Any],
    *,
    action_inputs: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    expected_classes = set(_expected_source_classes(action_inputs))
    allowed_candidate_ids = _satisfied_candidate_ids(recheck_state, action_inputs)
    custody = {
        _mapping(record).get("candidate_id"): _mapping(record)
        for record in _list(ledger.get("custody_records"))
        if isinstance(record, Mapping)
    }
    refs: list[dict[str, Any]] = []
    for candidate in _mappings(ledger.get("candidate_records")):
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id or candidate_id not in allowed_candidate_ids:
            continue
        custody_record = custody.get(candidate_id, {})
        if custody_record.get("disposition") != "accepted":
            continue
        if candidate.get("fact_disposition") != "accepted":
            continue
        if expected_classes and candidate.get("source_class") not in expected_classes:
            continue
        if candidate.get("contextual_only") is True:
            continue
        if candidate.get("readable_status") in {"not_readable", "unreadable"}:
            continue
        refs.append(
            {
                "candidate_id": candidate_id,
                "source_id": candidate_id,
                "url": candidate.get("url"),
                "title": candidate.get("title") or candidate.get("source_label"),
                "domain": candidate.get("domain"),
                "source_tier": candidate.get("source_tier"),
                "source_class": candidate.get("source_class"),
                "text": "",
                "query_refs": [
                    item
                    for item in (
                        candidate.get("query_ref"),
                        candidate.get("retrieval_pass_id"),
                    )
                    if item
                ],
                "custody_ref": {
                    "authority": "RunKernel.EvidenceLedger",
                    "candidate_id": candidate_id,
                    "custody_observation_id": custody_record.get("observation_id"),
                    "requirement_id": custody_record.get("requirement_id"),
                    "disposition": custody_record.get("disposition"),
                    "reason": custody_record.get("reason"),
                },
            }
        )
    return tuple(refs)


def _satisfied_candidate_ids(
    recheck_state: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> set[str]:
    wanted_requirements = {
        _requirement_token(item)
        for item in _strings(action_inputs.get("requirement_ids"))
    }
    out: set[str] = set()
    for status in _mappings(recheck_state.get("source_requirement_statuses")):
        if status.get("status") != "satisfied":
            continue
        requirement_id = status.get("requirement_id")
        if wanted_requirements and _requirement_token(requirement_id) not in (
            wanted_requirements
        ):
            continue
        out.update(_strings(status.get("linked_candidate_ids")))
    return out


def _packet_authority_payload(packet: FinalAnswerPacket) -> dict[str, Any]:
    citation_source_ids = [
        item.get("source_id")
        for item in packet.to_dict().get("citation_eligible", [])
        if item.get("source_id") is not None
    ]
    citation_ineligible = packet.to_dict().get("citation_ineligible", [])
    missing = tuple(packet.missing_required_obligations) or _missing_source_obligations(
        packet
    )
    payload = packet.to_authority_payload(
        citation_source_ids=citation_source_ids,
        citation_ineligible_refs=citation_ineligible,
        missing_source_obligations=missing,
        partial_source_obligations=tuple(packet.partial_obligations),
        satisfied_source_obligations=tuple(packet.satisfied_obligations)
        or _satisfied_source_obligations(packet),
    )
    return {
        **payload,
        "fixture_only": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "not_for_product_answer_activation": True,
    }


def _with_fixture_packet_boundaries(packet: FinalAnswerPacket) -> FinalAnswerPacket:
    flags = {
        **_mapping(packet.behavior_boundary_flags),
        **_behavior_boundary_flags(),
    }
    refs = {
        **_mapping(packet.author_input_refs),
        "status": "author_execution_deferred",
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "fixture_only": True,
        "not_for_product_answer_activation": True,
        "citation_formatter_invoked": False,
    }
    return replace(packet, behavior_boundary_flags=flags, author_input_refs=refs)


def _missing_source_obligations(packet: FinalAnswerPacket) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        obligation.to_dict()
        for obligation in packet.source_obligations
        if obligation.status is not SourceObligationStatus.SATISFIED
    )


def _satisfied_source_obligations(
    packet: FinalAnswerPacket,
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        obligation.to_dict()
        for obligation in packet.source_obligations
        if obligation.status is SourceObligationStatus.SATISFIED
    )


def _unique_source_urls(
    final_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        str(item.get("url")): item.get("source_id")
        for item in final_evidence
        if item.get("url") and item.get("source_id")
    }


def _expected_source_classes(action_inputs: Mapping[str, Any]) -> tuple[str, ...]:
    expected = tuple(
        item
        for item in _strings(action_inputs.get("expected_source_classes"))
        if item and item != "[redacted]"
    )
    if expected:
        return expected
    job_kind = clean_token(action_inputs.get("provider_job_kind"))
    by_job = {
        "official_current_candidate_acquisition": (
            "official_government",
            "official_current_rules",
        ),
        "legal_current_primary_acquisition": (
            "primary_legal",
            "legal_or_regulatory_text",
        ),
        "canonical_doc_acquisition": ("canonical", "primary_source_documents"),
        "source_bound_numeric_extraction_calculation_support": (
            "sourced_numeric_values",
        ),
        "conflict_currentness_check": ("current_primary_or_official",),
        "reconciliation_support": ("source_family_map",),
        "fetch_read_extract": ("answer_bearing_extract",),
    }
    return by_job.get(job_kind, ("answer_bearing_candidate",))


def _validate_recheck_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical recheck state")
    if state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
        raise PermissionError("follow-up packet requires RunKernel recheck state")
    if state.get("sufficiency_recheck_mode") != FOLLOWUP_SUFFICIENCY_RECHECK_MODE:
        raise PermissionError("follow-up packet requires fixture-only recheck mode")
    if state.get("provider_execution_licensed") is not False:
        raise PermissionError("provider execution is not licensed for packet prep")
    if state.get("final_answer_packet_deferred") is not True:
        raise PermissionError("follow-up packet requires previously deferred packet")
    if state.get("author_activation_allowed") is not False:
        raise PermissionError("follow-up packet requires Author activation closed")
    if state.get("citation_behavior_changed") is not False:
        raise PermissionError("follow-up packet requires unchanged citation behavior")
    flags = _mapping(state.get("behavior_boundary_flags"))
    for flag in _closed_surface_false_flags():
        if flags.get(flag) is not False:
            raise PermissionError(f"follow-up packet requires {flag}=False")
    if flags.get("sufficiency_judgment_rechecked") is not True:
        raise PermissionError("follow-up packet requires completed sufficiency recheck")


def _validate_sufficiency_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
        raise PermissionError("follow-up packet requires canonical sufficiency owner")
    if projection.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical sufficiency")
    if projection.get("trace_only") is not False:
        raise PermissionError("SufficiencyJudgment projection must not be trace-only")
    packet_inputs = _mapping(projection.get("final_packet_inputs"))
    if (
        projection.get("author_activation_allowed") is True
        or packet_inputs.get("author_activation_allowed") is True
    ):
        raise PermissionError("SufficiencyJudgment must keep Author closed")
    if (
        projection.get("citation_behavior_changed") is True
        or packet_inputs.get("citation_behavior_changed") is True
    ):
        raise PermissionError("SufficiencyJudgment must keep citation behavior closed")
    if (
        projection.get("live_validation_not_run") is False
        or packet_inputs.get("live_validation_not_run") is False
    ):
        raise PermissionError("SufficiencyJudgment must record no live validation")


def _validate_ledger_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("owner") != "RunKernel.EvidenceLedger":
        raise PermissionError("follow-up packet requires EvidenceLedger owner")
    if projection.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical EvidenceLedger")
    if projection.get("trace_only") is not False:
        raise PermissionError("EvidenceLedger projection must not be trace-only")


def _validate_intake_state(
    intake_state: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    if intake_state.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical intake state")
    if intake_state.get("owner") != "RunKernel.FollowupEvidenceIntake":
        raise PermissionError("follow-up packet requires RunKernel intake state")
    if intake_state.get("intake_id") != action_inputs.get("intake_id"):
        raise PermissionError("follow-up packet intake_id mismatch")
    if intake_state.get("provider_execution_licensed") is not False:
        raise PermissionError("follow-up packet intake must keep provider unlicensed")


def _validate_action_inputs(
    action_inputs: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
    sufficiency_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
    ):
        if action_inputs.get(field) != recheck_state.get(field):
            raise PermissionError(f"authorized follow-up packet {field} mismatch")
    if action_inputs.get("execution_mode") == "fixture_only" and (
        action_inputs.get("fixture_execution_mode")
        != recheck_state.get("fixture_execution_mode")
    ):
        raise PermissionError("authorized follow-up packet fixture_execution_mode mismatch")
    for field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "intake_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
    ):
        if action_inputs.get(field) != intake_state.get(field):
            raise PermissionError(
                f"authorized follow-up packet intake {field} mismatch"
            )
    if action_inputs.get("execution_mode") == "fixture_only" and (
        action_inputs.get("fixture_execution_mode")
        != intake_state.get("fixture_execution_mode")
    ):
        raise PermissionError(
            "authorized follow-up packet intake fixture_execution_mode mismatch"
        )
    for action_field, state_field in (
        ("followup_evidence_intake_id", "intake_id"),
        ("followup_evidence_intake_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != intake_state.get(state_field):
            raise PermissionError(
                f"authorized follow-up packet intake {action_field} mismatch"
            )
    for action_field, state_field in (
        ("followup_sufficiency_recheck_id", "recheck_id"),
        ("recheck_id", "recheck_id"),
        ("followup_sufficiency_recheck_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != recheck_state.get(state_field):
            raise PermissionError(
                f"authorized follow-up packet {action_field} mismatch"
            )
    if _strings(action_inputs.get("requirement_ids")) != _strings(
        recheck_state.get("requirement_ids")
    ):
        raise PermissionError("authorized follow-up packet requirement_ids mismatch")
    if _strings(action_inputs.get("expected_source_classes")) != (
        _expected_source_classes(recheck_state)
    ):
        raise PermissionError(
            "authorized follow-up packet expected_source_classes mismatch"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("follow-up packet must keep provider unlicensed")
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise PermissionError("follow-up packet action must be fixture-only")
    if action_inputs.get("author_activation_allowed") is not False:
        raise PermissionError("follow-up packet action must keep Author closed")
    if action_inputs.get("citation_rendering_changed") is not False:
        raise PermissionError("follow-up packet action must not render citations")
    if action_inputs.get("product_answer_behavior_changed") is not False:
        raise PermissionError("follow-up packet action must not change product answers")
    if action_inputs.get("live_validation_not_run") is not True:
        raise PermissionError("follow-up packet action must not run live validation")
    if action_inputs.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(evidence_ledger_projection)
    ):
        raise PermissionError("follow-up packet EvidenceLedger digest mismatch")
    if action_inputs.get("sufficiency_judgment_digest") != (
        followup_projection_digest(sufficiency_projection)
    ):
        raise PermissionError("follow-up packet SufficiencyJudgment digest mismatch")
    if action_inputs.get("followup_sufficiency_recheck_digest") != (
        followup_projection_digest(recheck_state)
    ):
        raise PermissionError("follow-up packet recheck digest mismatch")


def _validate_readiness_recheck_state(state: Mapping[str, Any]) -> None:
    _validate_recheck_state(state)
    if state.get("evidence_ledger_intake_mode") != AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE:
        raise PermissionError(
            "AG-96I3O1 readiness requires AG-96I3M2 intake mode"
        )
    if state.get("citation_eligible") is not False:
        raise PermissionError("readiness recheck state must keep citation_eligible=false")
    if not _mapping(state.get("ag96i3m2_admission_review_candidate")):
        raise PermissionError("readiness requires AG-96I3M2 candidate summary")
    if not _mapping(state.get("ag96i3m2_evidence_ledger_intake_binding")):
        raise PermissionError("readiness requires AG-96I3M2 binding summary")


def _validate_readiness_intake_state(
    intake_state: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    _validate_intake_state(intake_state, action_inputs)
    if intake_state.get("evidence_ledger_intake_mode") != (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        raise PermissionError(
            "AG-96I3O1 readiness requires AG-96I3M2 intake state"
        )
    if intake_state.get("runtime_evidence_intake_occurred") is not True:
        raise PermissionError("readiness requires runtime EvidenceLedger intake")


def _validate_readiness_action_inputs(
    action_inputs: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
    sufficiency_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
    ):
        if action_inputs.get(field) != recheck_state.get(field):
            raise PermissionError(
                f"authorized follow-up readiness {field} mismatch"
            )
    if action_inputs.get("execution_mode") == "fixture_only" and (
        action_inputs.get("fixture_execution_mode")
        != recheck_state.get("fixture_execution_mode")
    ):
        raise PermissionError(
            "authorized follow-up readiness fixture_execution_mode mismatch"
        )
    for field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "intake_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
    ):
        if action_inputs.get(field) != intake_state.get(field):
            raise PermissionError(
                f"authorized follow-up readiness intake {field} mismatch"
            )
    for action_field, state_field in (
        ("followup_evidence_intake_id", "intake_id"),
        ("followup_evidence_intake_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != intake_state.get(state_field):
            raise PermissionError(
                f"authorized follow-up readiness intake {action_field} mismatch"
            )
    for action_field, state_field in (
        ("followup_sufficiency_recheck_id", "recheck_id"),
        ("recheck_id", "recheck_id"),
        ("followup_sufficiency_recheck_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != recheck_state.get(state_field):
            raise PermissionError(
                f"authorized follow-up readiness {action_field} mismatch"
            )
    if _strings(action_inputs.get("requirement_ids")) != _strings(
        recheck_state.get("requirement_ids")
    ):
        raise PermissionError("authorized follow-up readiness requirement_ids mismatch")
    if _strings(action_inputs.get("expected_source_classes")) != (
        _expected_source_classes(recheck_state)
    ):
        raise PermissionError(
            "authorized follow-up readiness expected_source_classes mismatch"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("follow-up readiness must keep provider unlicensed")
    if action_inputs.get("evidence_ledger_intake_mode") != (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        raise PermissionError("follow-up readiness requires AG-96I3M2 intake mode")
    if action_inputs.get("packet_preparation_readiness_mode") != (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    ):
        raise PermissionError("follow-up readiness action must use AG-96I3O1 mode")
    _reject_truthy_downstream_flags(action_inputs, context="follow-up readiness action")
    if action_inputs.get("author_execution_deferred") is not True:
        raise PermissionError("follow-up readiness action must defer Author execution")
    if action_inputs.get("live_validation_not_run") is not True:
        raise PermissionError("follow-up readiness action must not run live validation")
    if action_inputs.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(evidence_ledger_projection)
    ):
        raise PermissionError("follow-up readiness EvidenceLedger digest mismatch")
    if action_inputs.get("sufficiency_judgment_digest") != (
        followup_projection_digest(sufficiency_projection)
    ):
        raise PermissionError("follow-up readiness SufficiencyJudgment digest mismatch")
    if action_inputs.get("followup_sufficiency_recheck_digest") != (
        followup_projection_digest(recheck_state)
    ):
        raise PermissionError("follow-up readiness recheck digest mismatch")
    _reject_forbidden_authority_refs(action_inputs)


def _validate_blocked_shell_readiness_state(
    readiness_state: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    if readiness_state.get("owner") != "RunKernel.FollowupFinalAnswerPacketReadiness":
        raise PermissionError("blocked shell requires RunKernel readiness owner")
    if readiness_state.get("canonical_state") is not True:
        raise PermissionError("blocked shell requires canonical readiness state")
    if readiness_state.get("diagnostic_only") is not True:
        raise PermissionError("blocked shell requires diagnostic readiness")
    if readiness_state.get("not_final_answer_packet_authority") is not True:
        raise PermissionError("blocked shell requires non-packet-authority readiness")
    if readiness_state.get("not_role_consumption_payload") is not True:
        raise PermissionError("blocked shell requires non-role readiness payload")
    if readiness_state.get("packet_preparation_readiness_id") != action_inputs.get(
        "packet_preparation_readiness_id"
    ):
        raise PermissionError("blocked shell readiness ID mismatch")
    if readiness_state.get("observation_id") != action_inputs.get(
        "readiness_observation_id"
    ):
        raise PermissionError("blocked shell readiness observation ID mismatch")
    if readiness_state.get("packet_preparation_readiness_mode") != (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    ):
        raise PermissionError("blocked shell requires AG-96I3O1 readiness mode")
    if readiness_state.get("final_answer_activation_blocked") is not True:
        raise PermissionError("blocked shell requires blocked readiness activation")
    if readiness_state.get("final_answer_allowed") is not False:
        raise PermissionError("blocked shell requires final_answer_allowed=false")
    _reject_truthy_downstream_flags(
        readiness_state,
        context="blocked shell readiness",
    )
    if readiness_state.get("author_execution_deferred") is not True:
        raise PermissionError("blocked shell readiness must defer Author execution")
    if readiness_state.get("live_validation_not_run") is not True:
        raise PermissionError("blocked shell readiness must not run live validation")
    _reject_forbidden_authority_refs(readiness_state)
    _ensure_no_private_payload(readiness_state)


def _validate_blocked_shell_action_inputs(
    action_inputs: Mapping[str, Any],
    readiness_state: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
    sufficiency_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_sufficiency_recheck_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "packet_preparation_readiness_mode",
    ):
        if action_inputs.get(field) != readiness_state.get(field):
            raise PermissionError(f"blocked shell readiness {field} mismatch")
    if action_inputs.get("execution_mode") == "fixture_only" and (
        action_inputs.get("fixture_execution_mode")
        != readiness_state.get("fixture_execution_mode")
    ):
        raise PermissionError("blocked shell readiness fixture_execution_mode mismatch")
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
    ):
        if action_inputs.get(field) != recheck_state.get(field):
            raise PermissionError(f"blocked shell recheck {field} mismatch")
    if action_inputs.get("execution_mode") == "fixture_only" and (
        action_inputs.get("fixture_execution_mode")
        != recheck_state.get("fixture_execution_mode")
    ):
        raise PermissionError("blocked shell recheck fixture_execution_mode mismatch")
    for field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "intake_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
    ):
        if action_inputs.get(field) != intake_state.get(field):
            raise PermissionError(f"blocked shell intake {field} mismatch")
    for action_field, state_field in (
        ("followup_evidence_intake_id", "intake_id"),
        ("followup_evidence_intake_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != intake_state.get(state_field):
            raise PermissionError(f"blocked shell intake {action_field} mismatch")
    for action_field, state_field in (
        ("followup_sufficiency_recheck_id", "recheck_id"),
        ("recheck_id", "recheck_id"),
        ("followup_sufficiency_recheck_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != recheck_state.get(state_field):
            raise PermissionError(f"blocked shell {action_field} mismatch")
    if _strings(action_inputs.get("requirement_ids")) != _strings(
        readiness_state.get("requirement_ids")
    ):
        raise PermissionError("blocked shell requirement_ids mismatch")
    if _strings(action_inputs.get("requirement_ids")) != _strings(
        recheck_state.get("requirement_ids")
    ):
        raise PermissionError("blocked shell recheck requirement_ids mismatch")
    if _strings(action_inputs.get("expected_source_classes")) != _strings(
        readiness_state.get("expected_source_classes")
    ):
        raise PermissionError("blocked shell expected_source_classes mismatch")
    if _strings(action_inputs.get("expected_source_classes")) != (
        _expected_source_classes(recheck_state)
    ):
        raise PermissionError("blocked shell recheck expected_source_classes mismatch")
    if not action_inputs.get("blocked_final_answer_packet_shell_id"):
        raise PermissionError("blocked shell requires shell ID")
    if action_inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("blocked shell must keep provider unlicensed")
    if action_inputs.get("evidence_ledger_intake_mode") != (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        raise PermissionError("blocked shell requires AG-96I3M2 intake mode")
    if action_inputs.get("packet_preparation_readiness_mode") != (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    ):
        raise PermissionError("blocked shell action must consume AG-96I3O1 readiness")
    if action_inputs.get("blocked_final_answer_packet_mode") != (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    ):
        raise PermissionError("blocked shell action must use AG-96I3O2 mode")
    _reject_truthy_blocked_shell_downstream_flags(
        action_inputs,
        context="blocked shell action",
    )
    if action_inputs.get("author_execution_deferred") is not True:
        raise PermissionError("blocked shell action must defer Author execution")
    if action_inputs.get("live_validation_not_run") is not True:
        raise PermissionError("blocked shell action must not run live validation")
    if action_inputs.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(evidence_ledger_projection)
    ):
        raise PermissionError("blocked shell EvidenceLedger digest mismatch")
    if action_inputs.get("sufficiency_judgment_digest") != (
        followup_projection_digest(sufficiency_projection)
    ):
        raise PermissionError("blocked shell SufficiencyJudgment digest mismatch")
    if action_inputs.get("followup_sufficiency_recheck_digest") != (
        followup_projection_digest(recheck_state)
    ):
        raise PermissionError("blocked shell recheck digest mismatch")
    if action_inputs.get("followup_final_answer_packet_readiness_digest") != (
        followup_projection_digest(readiness_state)
    ):
        raise PermissionError("blocked shell readiness digest mismatch")
    _reject_forbidden_authority_refs(action_inputs)
    _ensure_no_private_payload(action_inputs)


def _reject_truthy_blocked_shell_downstream_flags(
    payload: Mapping[str, Any],
    *,
    context: str,
) -> None:
    for field in (
        "final_evidence_selected",
        "citation_eligible",
        "citations_rendered",
        "citation_rendering_changed",
        "citation_behavior_changed",
        "citation_formatter_invoked",
        "author_activation_allowed",
        "author_payload_created",
        "analyst_activation_allowed",
        "analyst_handoff_created",
        "economist_activation_allowed",
        "economist_handoff_created",
        "economist_code_execution_allowed",
        "answer_ready",
        "prompt_behavior_changed",
        "product_answer_behavior_changed",
    ):
        if payload.get(field) is not False:
            raise PermissionError(f"{context} requires {field}=False")


def _reject_truthy_downstream_flags(
    payload: Mapping[str, Any],
    *,
    context: str,
) -> None:
    for field in (
        "canonical_final_answer_packet_mutated",
        "final_evidence_selected",
        "citation_eligible",
        "citations_rendered",
        "citation_rendering_changed",
        "citation_behavior_changed",
        "citation_formatter_invoked",
        "author_activation_allowed",
        "author_payload_created",
        "analyst_activation_allowed",
        "analyst_handoff_created",
        "economist_activation_allowed",
        "economist_handoff_created",
        "economist_code_execution_allowed",
        "answer_ready",
        "prompt_behavior_changed",
        "product_answer_behavior_changed",
    ):
        if payload.get(field) is not False:
            raise PermissionError(f"{context} requires {field}=False")


def _reject_forbidden_authority_refs(payload: Mapping[str, Any]) -> None:
    for field in _FORBIDDEN_AUTHORITY_REF_FIELDS:
        if payload.get(field) not in (None, False, [], (), {}):
            raise PermissionError(f"readiness cannot carry {field}")


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": True,
        "final_answer_packet_prepared": True,
        "final_answer_packet_updated": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        **followup_closed_flags(
            *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS
        ),
        "live_validation_not_run": True,
    }


def _readiness_behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_recorded": True,
        "canonical_final_answer_packet_mutated": False,
        "final_answer_packet_updated": False,
        "final_answer_packet_rebuilt": False,
        "final_evidence_selected": False,
        "citation_eligible": False,
        "citations_rendered": False,
        "author_payload_created": False,
        "analyst_activation_allowed": False,
        "analyst_handoff_created": False,
        "economist_activation_allowed": False,
        "economist_handoff_created": False,
        "economist_code_execution_allowed": False,
        "answer_ready": False,
        "prompt_behavior_changed": False,
        **followup_closed_flags(
            *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS
        ),
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "product_answer_behavior_changed": False,
        "live_validation_not_run": True,
    }


def _blocked_shell_behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_consumed": True,
        "canonical_final_answer_packet_mutated": True,
        "final_answer_packet_updated": True,
        "final_answer_packet_rebuilt": True,
        "blocked_final_answer_packet_shell_activated": True,
        "final_evidence_selected": False,
        "citation_eligible": False,
        "citations_rendered": False,
        "author_payload_created": False,
        "analyst_activation_allowed": False,
        "analyst_handoff_created": False,
        "economist_activation_allowed": False,
        "economist_handoff_created": False,
        "economist_code_execution_allowed": False,
        "answer_ready": False,
        "prompt_behavior_changed": False,
        **followup_closed_flags(
            *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS
        ),
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "product_answer_behavior_changed": False,
        "live_validation_not_run": True,
        "not_role_consumption_payload": True,
        "final_evidence_selection_deferred": True,
        "citation_eligibility_deferred": True,
    }


def _closed_surface_false_flags() -> tuple[str, ...]:
    return (
        *FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:],
        *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
        "final_answer_packet_updated",
        "final_answer_behavior_changed",
        "author_prose_behavior_changed",
        "citation_behavior_changed",
    )


def _readiness_fixture_only_provenance() -> dict[str, Any]:
    return followup_fixture_provenance(
        intake_bridge="ag96i3m2_admission_review_followup_intake",
        recheck_bridge="ag96i3n_followup_sufficiency_recheck_after_m2_intake",
        packet_bridge="ag96i3o1_final_answer_packet_preparation_readiness",
        author_executor_connected=False,
    )


def _fixture_only_provenance() -> dict[str, Any]:
    return followup_fixture_provenance(
        intake_bridge="ag96i2c_followup_evidence_ledger_intake",
        recheck_bridge="ag96i2d_followup_sufficiency_recheck",
        packet_bridge="ag96i2e_followup_final_answer_packet_prepare",
        author_executor_connected=False,
    )


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture()


def _readiness_redaction_posture() -> dict[str, bool]:
    return {
        **followup_common_redaction_posture(),
        "raw_text_retained": False,
        "provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "private_payload_retained": False,
        "citation_eligibility_retained": False,
        "author_payload_retained": False,
    }


def _blocked_shell_redaction_posture() -> dict[str, bool]:
    return {
        **followup_common_redaction_posture(),
        "raw_text_retained": False,
        "provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "private_payload_retained": False,
        "final_evidence_refs_retained": False,
        "citation_eligibility_retained": False,
        "author_payload_retained": False,
    }


def _readiness_evidence_ledger_counts(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, int]:
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


def _readiness_source_requirement_statuses(
    recheck_state: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    statuses = _mappings(recheck_state.get("source_requirement_statuses"))
    if statuses:
        return statuses
    out: list[Mapping[str, Any]] = []
    for requirement in _mappings(evidence_ledger_projection.get("source_requirements")):
        out.append(
            {
                "requirement_id": requirement.get("requirement_id"),
                "status": requirement.get("status") or "unknown",
                "required_source_class": requirement.get("required_source_class"),
                "required_source_tier": requirement.get("required_source_tier"),
                "required_currentness": requirement.get("required_currentness"),
                "linked_candidate_ids": requirement.get("linked_candidate_ids", []),
                "reason": requirement.get("reason"),
            }
        )
    return tuple(out)


def _readiness_status_summary(
    statuses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    counts = {
        "satisfied": 0,
        "partially_satisfied": 0,
        "unsatisfied": 0,
        "unknown": 0,
    }
    for status in statuses:
        value = clean_token(_mapping(status).get("status")) or "unknown"
        counts[value if value in counts else "unknown"] += 1
    return {
        **counts,
        "all_satisfied": bool(statuses) and counts["satisfied"] == len(statuses),
        "any_satisfied": counts["satisfied"] > 0,
        "any_partial": counts["partially_satisfied"] > 0,
        "any_missing": (counts["unsatisfied"] + counts["unknown"]) > 0,
        "requirement_count": len(statuses),
    }


def _readiness_obligation_lists(
    statuses: Sequence[Mapping[str, Any]],
    *,
    packet_inputs: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
) -> tuple[
    tuple[Mapping[str, Any], ...],
    tuple[Mapping[str, Any], ...],
    tuple[Mapping[str, Any], ...],
]:
    missing: list[Mapping[str, Any]] = []
    partial: list[Mapping[str, Any]] = []
    satisfied: list[Mapping[str, Any]] = []
    for item in statuses:
        payload = _readiness_obligation_ref(item)
        status = clean_token(payload.get("status")) or "unknown"
        if status == "satisfied":
            satisfied.append(payload)
        elif status == "partially_satisfied":
            partial.append(payload)
        else:
            missing.append(payload)
    for item in _mappings(
        packet_inputs.get("missing_required_obligations")
        or sufficiency.get("missing_required_obligations")
    ):
        missing.append(_readiness_obligation_ref(item))
    for item in _mappings(
        packet_inputs.get("partial_obligations") or sufficiency.get("partial_obligations")
    ):
        partial.append(_readiness_obligation_ref(item))
    for item in _mappings(
        packet_inputs.get("satisfied_obligations")
        or sufficiency.get("satisfied_obligations")
    ):
        satisfied.append(_readiness_obligation_ref(item))
    return (
        _dedupe_mappings(missing),
        _dedupe_mappings(partial),
        _dedupe_mappings(satisfied),
    )


def _readiness_obligation_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    mapping = _mapping(item)
    return {
        key: value
        for key, value in {
            "requirement_id": clean_token(mapping.get("requirement_id")),
            "source_obligation_id": clean_token(mapping.get("source_obligation_id")),
            "required_source_class": clean_token(
                mapping.get("required_source_class") or mapping.get("source_class")
            ),
            "required_source_tier": clean_token(mapping.get("required_source_tier")),
            "required_currentness": clean_token(mapping.get("required_currentness")),
            "status": clean_token(mapping.get("status")) or "unknown",
            "reason": clean_token(mapping.get("reason"), limit=220),
            "linked_candidate_ids": list(_strings(mapping.get("linked_candidate_ids"))),
        }.items()
        if value not in (None, "", [], {})
    }


def _readiness_source_bound_unknowns(
    packet_inputs: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    return _dedupe_mappings(
        tuple(
            _readiness_obligation_ref(item)
            for item in (
                _mappings(packet_inputs.get("source_bound_numeric_unknowns"))
                or _mappings(sufficiency.get("source_bound_numeric_unknowns"))
            )
        )
    )


def _readiness_block_reasons(
    *,
    custody_present: bool,
    status_summary: Mapping[str, Any],
    missing: Sequence[Mapping[str, Any]],
    partial: Sequence[Mapping[str, Any]],
    source_bound_unknowns: Sequence[Mapping[str, Any]],
    unresolved_conflicts: Sequence[str],
) -> tuple[str, ...]:
    reasons = [
        "ag96i3o1_preparation_readiness_only",
        "final_answer_activation_explicitly_blocked",
        "canonical_final_answer_packet_mutation_prohibited",
    ]
    if not custody_present:
        reasons.append("missing_custody")
    if missing or status_summary.get("any_missing"):
        reasons.append("missing_or_unsatisfied_obligation")
    if partial or status_summary.get("any_partial"):
        reasons.append("partial_obligation")
    if source_bound_unknowns:
        reasons.append("source_bound_unknowns_present")
    if unresolved_conflicts:
        reasons.append("unresolved_conflicts_present")
    return tuple(dict.fromkeys(reasons))


def _final_packet_inputs_summary(packet_inputs: Mapping[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "readiness_status",
        "readiness_reasons",
        "decision",
        "final_answer_posture",
        "final_answer_allowed",
        "required_obligations_satisfied",
        "missing_required_obligations",
        "partial_obligations",
        "satisfied_obligations",
        "source_bound_numeric_unknowns",
        "mandatory_caveats",
        "prohibited_upgrades",
        "author_activation_allowed",
        "citation_behavior_changed",
        "live_validation_not_run",
    )
    summary = {
        key: packet_inputs.get(key)
        for key in allowed_keys
        if packet_inputs.get(key) not in (None, "", [], {})
    }
    summary["final_answer_allowed"] = False
    summary["author_activation_allowed"] = False
    summary["citation_behavior_changed"] = False
    return _strip_forbidden_authority_refs(_mapping(safe_json(summary)))


def _ag96i3n_recheck_summary(
    recheck_state: Mapping[str, Any],
    *,
    status_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "recheck_id": recheck_state.get("recheck_id"),
        "observation_id": recheck_state.get("observation_id"),
        "recheck_status": recheck_state.get("recheck_status"),
        "fixture_sufficiency_posture": recheck_state.get(
            "fixture_sufficiency_posture"
        ),
        "source_requirement_status_summary": safe_json(status_summary),
        "evidence_ledger_counts": safe_json(
            _mapping(recheck_state.get("evidence_ledger_counts"))
        ),
        "official_current_custody_status": safe_json(
            _mapping(recheck_state.get("official_current_custody_status"))
        ),
        "final_answer_packet_deferred": recheck_state.get(
            "final_answer_packet_deferred"
        ),
        "author_activation_allowed": recheck_state.get("author_activation_allowed"),
        "citation_eligible": recheck_state.get("citation_eligible"),
    }


def _strip_forbidden_authority_refs(payload: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _FORBIDDEN_AUTHORITY_REF_FIELDS:
            continue
        if isinstance(value, Mapping):
            out[key] = _strip_forbidden_authority_refs(value)
        elif isinstance(value, list):
            out[key] = [
                _strip_forbidden_authority_refs(item)
                if isinstance(item, Mapping)
                else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def _dedupe_mappings(
    values: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    out: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        safe = _strip_forbidden_authority_refs(_mapping(safe_json(value)))
        if not safe:
            continue
        key = repr(safe)
        if key not in seen:
            out.append(safe)
            seen.add(key)
    return tuple(out)


def _ensure_no_private_payload(value: Any) -> None:
    def walk(item: Any, path: str) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                key_text = str(key or "").casefold()
                if key_text in _FORBIDDEN_AUTHORITY_REF_FIELDS:
                    if child not in (None, False, [], (), {}):
                        raise PermissionError(
                            f"readiness retained forbidden {key_text}"
                        )
                    continue
                if key_text.startswith("raw_") or key_text in {
                    "provider_payload",
                    "raw_prompt",
                    "raw_text",
                    "secret",
                    "secrets",
                    "token",
                }:
                    if child not in (None, False, [], (), {}):
                        raise PermissionError(
                            f"readiness retained private key {path}.{key}"
                        )
                    continue
                walk(child, f"{path}.{key}")
        elif isinstance(item, Sequence) and not isinstance(item, str | bytes):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")
        elif isinstance(item, str):
            lowered = item.casefold()
            if any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS):
                raise PermissionError("readiness retained private payload material")

    walk(value, "readiness")


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


def _requirement_token(value: Any) -> str:
    token = clean_token(value) or ""
    if token.startswith("source_requirement:"):
        token = token.split(":", 1)[1]
    if token.startswith("source_requirement_"):
        token = token.removeprefix("source_requirement_")
    return token


__all__ = [
    "AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE",
    "AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE",
    "FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_GATE_REASON",
    "FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_SCHEMA_VERSION",
    "FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE",
    "FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_TRACE_KEY",
    "FOLLOWUP_FINAL_ANSWER_PACKET_GATE_REASON",
    "FOLLOWUP_FINAL_ANSWER_PACKET_MODE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_GATE_REASON",
    "FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_SCHEMA_VERSION",
    "FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_TRACE_KEY",
    "FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION",
    "FOLLOWUP_FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_TRACE_KEY",
    "FollowupFinalAnswerPacketActionResult",
    "FollowupBlockedFinalAnswerPacketShellActionResult",
    "FollowupBlockedFinalAnswerPacketShellConsumptionRecord",
    "FollowupBlockedFinalAnswerPacketShellObservation",
    "FollowupBlockedFinalAnswerPacketShellRequest",
    "FollowupBlockedFinalAnswerPacketShellResult",
    "FollowupFinalAnswerPacketConsumptionRecord",
    "FollowupFinalAnswerPacketObservation",
    "FollowupFinalAnswerPacketRequest",
    "FollowupFinalAnswerPacketResult",
    "FollowupFinalAnswerPacketReadinessActionResult",
    "FollowupFinalAnswerPacketReadinessConsumptionRecord",
    "FollowupFinalAnswerPacketReadinessObservation",
    "FollowupFinalAnswerPacketReadinessRequest",
    "FollowupFinalAnswerPacketReadinessResult",
    "build_followup_blocked_final_answer_packet_shell_record",
    "build_followup_final_answer_packet_record",
    "build_followup_final_answer_packet_readiness_record",
    "execute_followup_blocked_final_answer_packet_shell_action",
    "execute_followup_final_answer_packet_prepare_action",
    "execute_followup_final_answer_packet_readiness_action",
    "followup_projection_digest",
]
