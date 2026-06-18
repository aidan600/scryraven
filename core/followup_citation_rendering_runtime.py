"""AG-96I3T1 R1-bound citation rendering state runtime.

This module turns canonical AG-96I3R1 source identity records into sanitized,
machine-readable source entries. It does not render final-answer citation
strings, build ordered product source output, prepare Author payloads, call
providers, retrieve, run prompts, or mutate the canonical FinalAnswerPacket.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_citation_source_handoff_runtime import (
    AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
)
from core.followup_deliberation import clean_text, clean_token, safe_json, stable_hash
from core.followup_final_answer_packet_runtime import (
    AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
    AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE,
    AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE,
    AG96I3Q1_CITATION_ELIGIBILITY_MODE,
    followup_projection_digest,
)
from core.followup_fixture_boundaries import (
    citation_rendering_boundary_flags,
    followup_common_redaction_posture,
)
from core.followup_sufficiency_recheck_runtime import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
)

FOLLOWUP_CITATION_RENDERING_SCHEMA_VERSION = (
    "followup_citation_rendering_ag96i3t1_v1"
)
FOLLOWUP_CITATION_RENDERING_TRACE_KEY = "followup_citation_rendering_runtime"
FOLLOWUP_CITATION_RENDERING_STAGE = "followup_citation_rendering"
AG96I3T1_CITATION_RENDERING_MODE = (
    "ag96i3t1_r1_bound_machine_readable_source_entries"
)
FOLLOWUP_CITATION_RENDERING_GATE_REASON = (
    "ag96i3t1_r1_bound_citation_rendering_state"
)
FOLLOWUP_CITATION_RENDERING_POLICY = "machine_readable_source_entry_only"

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
class FollowupCitationRenderingRequest:
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
    blocked_final_answer_packet_shell_id: str
    blocked_final_answer_packet_shell_observation_id: str
    final_evidence_selection_id: str
    final_evidence_selection_observation_id: str
    citation_eligibility_id: str
    citation_eligibility_observation_id: str
    citation_source_handoff_id: str
    citation_source_handoff_observation_id: str
    citation_rendering_id: str
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
    final_evidence_selection_mode: str
    citation_eligibility_mode: str
    citation_source_handoff_mode: str
    citation_rendering_mode: str
    evidence_ledger_projection_digest: str
    sufficiency_judgment_digest: str
    followup_sufficiency_recheck_digest: str
    followup_final_answer_packet_readiness_digest: str
    blocked_final_answer_packet_shell_digest: str
    blocked_final_answer_packet_digest: str
    followup_final_evidence_selection_digest: str
    followup_citation_eligibility_digest: str
    followup_citation_source_handoff_digest: str
    source_identity_digest: str
    current_final_answer_packet_digest: str
    provider_execution_licensed: bool
    final_answer_allowed: bool
    answer_ready: bool
    citation_rendering_deferred: bool
    author_execution_deferred: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_CITATION_RENDERING_SCHEMA_VERSION,
            "record_type": "followup_citation_rendering_request",
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
            "blocked_final_answer_packet_shell_id": clean_text(
                self.blocked_final_answer_packet_shell_id,
                limit=220,
            ),
            "blocked_final_answer_packet_shell_observation_id": clean_text(
                self.blocked_final_answer_packet_shell_observation_id,
                limit=220,
            ),
            "final_evidence_selection_id": clean_text(
                self.final_evidence_selection_id,
                limit=220,
            ),
            "final_evidence_selection_observation_id": clean_text(
                self.final_evidence_selection_observation_id,
                limit=220,
            ),
            "citation_eligibility_id": clean_text(
                self.citation_eligibility_id,
                limit=220,
            ),
            "citation_eligibility_observation_id": clean_text(
                self.citation_eligibility_observation_id,
                limit=220,
            ),
            "citation_source_handoff_id": clean_text(
                self.citation_source_handoff_id,
                limit=220,
            ),
            "citation_source_handoff_observation_id": clean_text(
                self.citation_source_handoff_observation_id,
                limit=220,
            ),
            "citation_rendering_id": clean_text(
                self.citation_rendering_id,
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
            "final_evidence_selection_mode": clean_token(
                self.final_evidence_selection_mode
            ),
            "citation_eligibility_mode": clean_token(
                self.citation_eligibility_mode
            ),
            "citation_source_handoff_mode": clean_token(
                self.citation_source_handoff_mode
            ),
            "citation_rendering_mode": clean_token(self.citation_rendering_mode),
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
            "blocked_final_answer_packet_shell_digest": clean_text(
                self.blocked_final_answer_packet_shell_digest,
                limit=120,
            ),
            "blocked_final_answer_packet_digest": clean_text(
                self.blocked_final_answer_packet_digest,
                limit=120,
            ),
            "followup_final_evidence_selection_digest": clean_text(
                self.followup_final_evidence_selection_digest,
                limit=120,
            ),
            "followup_citation_eligibility_digest": clean_text(
                self.followup_citation_eligibility_digest,
                limit=120,
            ),
            "followup_citation_source_handoff_digest": clean_text(
                self.followup_citation_source_handoff_digest,
                limit=120,
            ),
            "source_identity_digest": clean_text(
                self.source_identity_digest,
                limit=120,
            ),
            "current_final_answer_packet_digest": clean_text(
                self.current_final_answer_packet_digest,
                limit=120,
            ),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "final_answer_allowed": bool(self.final_answer_allowed),
            "answer_ready": bool(self.answer_ready),
            "citation_rendering_deferred": bool(self.citation_rendering_deferred),
            "author_execution_deferred": bool(self.author_execution_deferred),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _citation_rendering_behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupCitationRenderingResult:
    result_id: str
    status: str
    citation_rendering_id: str
    citation_source_handoff_id: str
    packet_id: str
    citation_eligible_source_ids: tuple[str, ...]
    citation_eligibility_refs: tuple[Mapping[str, Any], ...]
    source_identity_count: int
    source_identity_digest: str
    rendered_source_entries: tuple[Mapping[str, Any], ...]
    rendered_source_entry_count: int
    rendered_source_entry_digest: str
    citation_rendering_summary: Mapping[str, Any]
    citation_rendering_lineage: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_CITATION_RENDERING_SCHEMA_VERSION,
            "record_type": "followup_citation_rendering_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "citation_rendering_id": clean_text(
                self.citation_rendering_id,
                limit=220,
            ),
            "citation_source_handoff_id": clean_text(
                self.citation_source_handoff_id,
                limit=220,
            ),
            "packet_id": clean_text(self.packet_id, limit=220),
            "citation_eligible_source_ids": [
                clean_text(item, limit=220)
                for item in self.citation_eligible_source_ids
            ],
            "citation_eligibility_refs": [
                safe_json(item) for item in self.citation_eligibility_refs
            ],
            "source_identity_count": int(self.source_identity_count),
            "source_identity_digest": clean_text(
                self.source_identity_digest,
                limit=120,
            ),
            "rendered_source_entries": [
                safe_json(item) for item in self.rendered_source_entries
            ],
            "rendered_source_entry_count": int(self.rendered_source_entry_count),
            "rendered_source_entry_digest": clean_text(
                self.rendered_source_entry_digest,
                limit=120,
            ),
            "citation_rendering_summary": safe_json(
                self.citation_rendering_summary
            ),
            "citation_rendering_lineage": safe_json(
                self.citation_rendering_lineage
            ),
            "canonical_final_answer_packet_mutated": False,
            "final_answer_packet_updated": False,
            "final_answer_packet_rebuilt": False,
            "final_evidence_selected": True,
            "final_answer_allowed": False,
            "citation_eligibility_created": True,
            "citation_source_handoff_created": True,
            "citation_rendering_deferred": True,
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
            "not_role_consumption_payload": True,
            "ordered_product_source_output_created": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupCitationRenderingObservation:
    observation_id: str
    request: FollowupCitationRenderingRequest
    result: FollowupCitationRenderingResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        return {
            "schema_version": FOLLOWUP_CITATION_RENDERING_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_CITATION_RENDERING_TRACE_KEY,
            "record_type": "followup_citation_rendering_observation",
            "owner": "FollowupCitationRenderingRuntime",
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
            "blocked_final_answer_packet_shell_id": request.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "blocked_final_answer_packet_shell_observation_id": request.get(
                "blocked_final_answer_packet_shell_observation_id"
            ),
            "final_evidence_selection_id": request.get(
                "final_evidence_selection_id"
            ),
            "final_evidence_selection_observation_id": request.get(
                "final_evidence_selection_observation_id"
            ),
            "citation_eligibility_id": request.get("citation_eligibility_id"),
            "citation_eligibility_observation_id": request.get(
                "citation_eligibility_observation_id"
            ),
            "citation_source_handoff_id": request.get(
                "citation_source_handoff_id"
            ),
            "citation_source_handoff_observation_id": request.get(
                "citation_source_handoff_observation_id"
            ),
            "citation_rendering_id": request.get("citation_rendering_id"),
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
            "final_evidence_selection_mode": request.get(
                "final_evidence_selection_mode"
            ),
            "citation_eligibility_mode": request.get("citation_eligibility_mode"),
            "citation_source_handoff_mode": request.get(
                "citation_source_handoff_mode"
            ),
            "citation_rendering_mode": request.get("citation_rendering_mode"),
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
            "blocked_final_answer_packet_shell_digest": request.get(
                "blocked_final_answer_packet_shell_digest"
            ),
            "blocked_final_answer_packet_digest": request.get(
                "blocked_final_answer_packet_digest"
            ),
            "followup_final_evidence_selection_digest": request.get(
                "followup_final_evidence_selection_digest"
            ),
            "followup_citation_eligibility_digest": request.get(
                "followup_citation_eligibility_digest"
            ),
            "followup_citation_source_handoff_digest": request.get(
                "followup_citation_source_handoff_digest"
            ),
            "source_identity_digest": request.get("source_identity_digest"),
            "current_final_answer_packet_digest": request.get(
                "current_final_answer_packet_digest"
            ),
            "request": request,
            "result": result,
            "packet_id": result.get("packet_id"),
            "citation_eligible_source_ids": result.get(
                "citation_eligible_source_ids",
                [],
            ),
            "citation_eligibility_refs": result.get(
                "citation_eligibility_refs",
                [],
            ),
            "source_identity_count": result.get("source_identity_count"),
            "rendered_source_entries": result.get("rendered_source_entries", []),
            "rendered_source_entry_count": result.get(
                "rendered_source_entry_count"
            ),
            "rendered_source_entry_digest": result.get(
                "rendered_source_entry_digest"
            ),
            "citation_rendering_summary": result.get(
                "citation_rendering_summary",
                {},
            ),
            "citation_rendering_lineage": result.get(
                "citation_rendering_lineage",
                {},
            ),
            "canonical_final_answer_packet_mutated": False,
            "final_answer_packet_updated": False,
            "final_answer_packet_rebuilt": False,
            "final_evidence_selected": True,
            "final_answer_allowed": False,
            "citation_eligibility_created": True,
            "citation_source_handoff_created": True,
            "citation_rendering_deferred": True,
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
            "not_role_consumption_payload": True,
            "ordered_product_source_output_created": False,
            "rendering_policy": FOLLOWUP_CITATION_RENDERING_POLICY,
            "behavior_boundary_flags": _citation_rendering_behavior_boundary_flags(),
            "redaction_posture": _citation_rendering_redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupCitationRenderingConsumptionRecord:
    citation_rendering_id: str
    observation: FollowupCitationRenderingObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_citation_rendering_consumption_record",
            "owner": "FollowupCitationRenderingRuntime",
            "canonical_state": False,
            "citation_rendering_id": clean_text(
                self.citation_rendering_id,
                limit=220,
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupCitationRenderingActionResult:
    record: FollowupCitationRenderingConsumptionRecord
    observation: Any


def execute_followup_citation_rendering_action(
    action: Any,
    *,
    followup_citation_source_handoff_state: Mapping[str, Any],
    followup_citation_source_handoff_projection: Mapping[str, Any],
    followup_citation_source_handoff_history: Sequence[Mapping[str, Any]],
    followup_citation_eligibility_state: Mapping[str, Any],
    followup_citation_eligibility_projection: Mapping[str, Any],
    followup_citation_eligibility_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    followup_final_evidence_selection_state: Mapping[str, Any],
    followup_final_evidence_selection_projection: Mapping[str, Any],
    followup_final_evidence_selection_history: Sequence[Mapping[str, Any]],
    followup_blocked_final_answer_packet_shell_state: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_projection: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_history: Sequence[Mapping[str, Any]],
    followup_final_answer_packet_readiness_state: Mapping[str, Any],
    followup_final_answer_packet_readiness_projection: Mapping[str, Any],
    followup_final_answer_packet_readiness_history: Sequence[Mapping[str, Any]],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupCitationRenderingActionResult:
    """Execute bounded T1 source-entry rendering for one authorized action."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_CITATION_RENDERING,
        stage=FOLLOWUP_CITATION_RENDERING_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_CITATION_RENDERING_PREPARED
        ),
    )
    record = build_followup_citation_rendering_record(
        action_inputs=authorized.inputs,
        followup_citation_source_handoff_state=(
            followup_citation_source_handoff_state
        ),
        followup_citation_source_handoff_projection=(
            followup_citation_source_handoff_projection
        ),
        followup_citation_source_handoff_history=(
            followup_citation_source_handoff_history
        ),
        followup_citation_eligibility_state=followup_citation_eligibility_state,
        followup_citation_eligibility_projection=(
            followup_citation_eligibility_projection
        ),
        followup_citation_eligibility_history=(
            followup_citation_eligibility_history
        ),
        final_answer_packet=final_answer_packet,
        final_answer_authority_projection=final_answer_authority_projection,
        followup_final_evidence_selection_state=(
            followup_final_evidence_selection_state
        ),
        followup_final_evidence_selection_projection=(
            followup_final_evidence_selection_projection
        ),
        followup_final_evidence_selection_history=(
            followup_final_evidence_selection_history
        ),
        followup_blocked_final_answer_packet_shell_state=(
            followup_blocked_final_answer_packet_shell_state
        ),
        followup_blocked_final_answer_packet_shell_projection=(
            followup_blocked_final_answer_packet_shell_projection
        ),
        followup_blocked_final_answer_packet_shell_history=(
            followup_blocked_final_answer_packet_shell_history
        ),
        followup_final_answer_packet_readiness_state=(
            followup_final_answer_packet_readiness_state
        ),
        followup_final_answer_packet_readiness_projection=(
            followup_final_answer_packet_readiness_projection
        ),
        followup_final_answer_packet_readiness_history=(
            followup_final_answer_packet_readiness_history
        ),
        followup_sufficiency_recheck_state=followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        followup_evidence_intake_state=followup_evidence_intake_state,
    )
    return FollowupCitationRenderingActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=(
                ObservationType.FOLLOWUP_CITATION_RENDERING_PREPARED
            ),
            status=RunStageStatus.COMPLETED,
            payload={"followup_citation_rendering_state": record.to_dict()},
        ),
    )


def build_followup_citation_rendering_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_citation_source_handoff_state: Mapping[str, Any],
    followup_citation_source_handoff_projection: Mapping[str, Any],
    followup_citation_source_handoff_history: Sequence[Mapping[str, Any]],
    followup_citation_eligibility_state: Mapping[str, Any],
    followup_citation_eligibility_projection: Mapping[str, Any],
    followup_citation_eligibility_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    followup_final_evidence_selection_state: Mapping[str, Any],
    followup_final_evidence_selection_projection: Mapping[str, Any],
    followup_final_evidence_selection_history: Sequence[Mapping[str, Any]],
    followup_blocked_final_answer_packet_shell_state: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_projection: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_history: Sequence[Mapping[str, Any]],
    followup_final_answer_packet_readiness_state: Mapping[str, Any],
    followup_final_answer_packet_readiness_projection: Mapping[str, Any],
    followup_final_answer_packet_readiness_history: Sequence[Mapping[str, Any]],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupCitationRenderingConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    r1_state = _mapping(safe_json(followup_citation_source_handoff_state))
    r1_projection = _mapping(safe_json(followup_citation_source_handoff_projection))
    r1_history = tuple(_mappings(safe_json(followup_citation_source_handoff_history)))
    q1_state = _mapping(safe_json(followup_citation_eligibility_state))
    q1_projection = _mapping(safe_json(followup_citation_eligibility_projection))
    q1_history = tuple(_mappings(safe_json(followup_citation_eligibility_history)))
    packet = _mapping(safe_json(final_answer_packet))
    authority = _mapping(safe_json(final_answer_authority_projection))
    selection = _mapping(safe_json(followup_final_evidence_selection_state))
    selection_projection = _mapping(
        safe_json(followup_final_evidence_selection_projection)
    )
    selection_history = tuple(
        _mappings(safe_json(followup_final_evidence_selection_history))
    )
    shell = _mapping(safe_json(followup_blocked_final_answer_packet_shell_state))
    shell_projection = _mapping(
        safe_json(followup_blocked_final_answer_packet_shell_projection)
    )
    shell_history = tuple(
        _mappings(safe_json(followup_blocked_final_answer_packet_shell_history))
    )
    readiness = _mapping(safe_json(followup_final_answer_packet_readiness_state))
    readiness_projection = _mapping(
        safe_json(followup_final_answer_packet_readiness_projection)
    )
    readiness_history = tuple(
        _mappings(safe_json(followup_final_answer_packet_readiness_history))
    )
    recheck = _mapping(safe_json(followup_sufficiency_recheck_state))
    sufficiency = _mapping(safe_json(sufficiency_judgment_projection))
    ledger = _mapping(safe_json(evidence_ledger_projection))
    intake = _mapping(safe_json(followup_evidence_intake_state))

    _validate_t1_r1_state(r1_state, r1_projection, r1_history, action)
    _validate_t1_q1_state(q1_state, q1_projection, q1_history, action, r1_state)
    _validate_t1_p1_state(selection, selection_projection, selection_history, action)
    _validate_t1_o2_state(shell, shell_projection, shell_history, action)
    _validate_t1_o1_state(readiness, readiness_projection, readiness_history, action)
    _validate_t1_recheck_intake_sufficiency_ledger(
        recheck,
        intake,
        sufficiency,
        ledger,
        action,
    )
    _validate_t1_packet(packet, authority, action, r1_state)
    _validate_t1_action_inputs(
        action,
        r1_state=r1_state,
        q1_state=q1_state,
        q1_projection=q1_projection,
        packet=packet,
        selection=selection,
        shell=shell,
        readiness=readiness,
        recheck=recheck,
        intake=intake,
        sufficiency=sufficiency,
        ledger=ledger,
    )

    source_identity_records = _mappings(r1_state.get("source_identity_records"))
    rendering_id = str(action.get("citation_rendering_id") or "")
    rendering_mode = str(action.get("citation_rendering_mode") or "")
    rendered_entries = _rendered_source_entries(
        source_identity_records,
        rendering_id=rendering_id,
        rendering_mode=rendering_mode,
    )
    rendered_digest = stable_hash(safe_json(rendered_entries))
    lineage = _citation_rendering_lineage(
        action,
        r1_state=r1_state,
        q1_state=q1_state,
        selection=selection,
        shell=shell,
        readiness=readiness,
        recheck=recheck,
        intake=intake,
        rendered_source_entry_digest=rendered_digest,
    )
    summary = {
        "owner": "RunKernel.FollowupCitationRendering",
        "canonical_state": True,
        "rendering_policy": FOLLOWUP_CITATION_RENDERING_POLICY,
        "selection_source": "followup_citation_source_handoff_state.source_identity_records",
        "derived_from_r1": True,
        "packet_local_only": True,
        "source_identity_count": len(source_identity_records),
        "source_identity_digest": r1_state.get("source_identity_digest"),
        "rendered_source_entry_count": len(rendered_entries),
        "rendered_source_entry_digest": rendered_digest,
        "citations_rendered": False,
        "citation_formatter_invoked": False,
        "ordered_product_source_output_created": False,
        "author_payload_created": False,
        "role_handoffs_created": False,
    }
    _ensure_no_private_payload(summary)
    request = FollowupCitationRenderingRequest(
        request_id=f"followup-citation-rendering-request:{rendering_id}",
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
        packet_preparation_readiness_id=str(
            action.get("packet_preparation_readiness_id") or ""
        ),
        readiness_observation_id=str(action.get("readiness_observation_id") or ""),
        blocked_final_answer_packet_shell_id=str(
            action.get("blocked_final_answer_packet_shell_id") or ""
        ),
        blocked_final_answer_packet_shell_observation_id=str(
            action.get("blocked_final_answer_packet_shell_observation_id") or ""
        ),
        final_evidence_selection_id=str(
            action.get("final_evidence_selection_id") or ""
        ),
        final_evidence_selection_observation_id=str(
            action.get("final_evidence_selection_observation_id") or ""
        ),
        citation_eligibility_id=str(action.get("citation_eligibility_id") or ""),
        citation_eligibility_observation_id=str(
            action.get("citation_eligibility_observation_id") or ""
        ),
        citation_source_handoff_id=str(
            action.get("citation_source_handoff_id") or ""
        ),
        citation_source_handoff_observation_id=str(
            action.get("citation_source_handoff_observation_id") or ""
        ),
        citation_rendering_id=rendering_id,
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
        packet_preparation_readiness_mode=AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
        blocked_final_answer_packet_mode=AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE,
        final_evidence_selection_mode=AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE,
        citation_eligibility_mode=AG96I3Q1_CITATION_ELIGIBILITY_MODE,
        citation_source_handoff_mode=AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
        citation_rendering_mode=AG96I3T1_CITATION_RENDERING_MODE,
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
        blocked_final_answer_packet_shell_digest=str(
            action.get("blocked_final_answer_packet_shell_digest") or ""
        ),
        blocked_final_answer_packet_digest=str(
            action.get("blocked_final_answer_packet_digest") or ""
        ),
        followup_final_evidence_selection_digest=str(
            action.get("followup_final_evidence_selection_digest") or ""
        ),
        followup_citation_eligibility_digest=str(
            action.get("followup_citation_eligibility_digest") or ""
        ),
        followup_citation_source_handoff_digest=str(
            action.get("followup_citation_source_handoff_digest") or ""
        ),
        source_identity_digest=str(action.get("source_identity_digest") or ""),
        current_final_answer_packet_digest=str(
            action.get("current_final_answer_packet_digest") or ""
        ),
        provider_execution_licensed=False,
        final_answer_allowed=False,
        answer_ready=False,
        citation_rendering_deferred=True,
        author_execution_deferred=True,
        live_validation_not_run=True,
    )
    result = FollowupCitationRenderingResult(
        result_id=f"followup-citation-rendering-result:{rendering_id}",
        status="followup_r1_bound_rendered_source_entries_created",
        citation_rendering_id=rendering_id,
        citation_source_handoff_id=str(
            r1_state.get("citation_source_handoff_id") or ""
        ),
        packet_id=str(packet.get("packet_id") or ""),
        citation_eligible_source_ids=tuple(
            _strings(r1_state.get("citation_eligible_source_ids"))
        ),
        citation_eligibility_refs=tuple(
            _mappings(r1_state.get("citation_eligibility_refs"))
        ),
        source_identity_count=len(source_identity_records),
        source_identity_digest=str(r1_state.get("source_identity_digest") or ""),
        rendered_source_entries=tuple(rendered_entries),
        rendered_source_entry_count=len(rendered_entries),
        rendered_source_entry_digest=rendered_digest,
        citation_rendering_summary=summary,
        citation_rendering_lineage=lineage,
    )
    observation = FollowupCitationRenderingObservation(
        observation_id=f"followup-citation-rendering-observation:{rendering_id}",
        request=request,
        result=result,
    )
    record = FollowupCitationRenderingConsumptionRecord(
        citation_rendering_id=rendering_id,
        observation=observation,
    )
    _ensure_no_private_payload(record.to_dict())
    _reject_forbidden_t1_payload(record.to_dict())
    return record


def _validate_t1_r1_state(
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
) -> None:
    if state.get("owner") != "RunKernel.FollowupCitationSourceHandoff":
        raise PermissionError("citation rendering requires RunKernel R1 state")
    if state.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical R1 state")
    if state.get("citation_source_handoff_mode") != (
        AG96I3R1_CITATION_SOURCE_HANDOFF_MODE
    ):
        raise PermissionError("citation rendering requires AG-96I3R1 mode")
    if state.get("citation_source_handoff_id") != action.get(
        "citation_source_handoff_id"
    ):
        raise PermissionError("citation rendering R1 handoff ID mismatch")
    if state.get("observation_id") != action.get(
        "citation_source_handoff_observation_id"
    ):
        raise PermissionError("citation rendering R1 observation ID mismatch")
    if action.get("followup_citation_source_handoff_digest") != (
        followup_projection_digest(state)
    ):
        raise PermissionError("citation rendering R1 digest mismatch")
    if projection.get("owner") != "RunKernel.FollowupCitationSourceHandoff":
        raise PermissionError("citation rendering requires R1 projection")
    if projection.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical R1 projection")
    if projection.get("citation_source_handoff_id") != state.get(
        "citation_source_handoff_id"
    ):
        raise PermissionError("citation rendering R1 projection ID mismatch")
    if not history:
        raise PermissionError("citation rendering requires R1 history")
    if _mapping(history[-1]) != _mapping(projection):
        raise PermissionError("citation rendering R1 history mismatch")
    identities = _mappings(state.get("source_identity_records"))
    if not identities:
        raise PermissionError("citation rendering requires R1 source identities")
    if len(identities) != state.get("source_identity_count"):
        raise PermissionError("citation rendering R1 source identity count mismatch")
    if not _strings(state.get("citation_eligible_source_ids")):
        raise PermissionError("citation rendering requires R1 source IDs")
    if not _mappings(state.get("citation_eligibility_refs")):
        raise PermissionError("citation rendering requires R1 citation refs")
    if state.get("source_identity_digest") != action.get("source_identity_digest"):
        raise PermissionError("citation rendering source identity digest mismatch")
    _reject_t1_closed_output_fields(state, context="R1 state")
    _ensure_no_private_payload(state)


def _validate_t1_q1_state(
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
    r1_state: Mapping[str, Any],
) -> None:
    if state.get("owner") != "RunKernel.FollowupCitationEligibility":
        raise PermissionError("citation rendering requires RunKernel Q1 state")
    if state.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical Q1 state")
    if state.get("citation_eligibility_mode") != AG96I3Q1_CITATION_ELIGIBILITY_MODE:
        raise PermissionError("citation rendering requires AG-96I3Q1 mode")
    if state.get("citation_eligibility_id") != action.get("citation_eligibility_id"):
        raise PermissionError("citation rendering Q1 eligibility ID mismatch")
    if state.get("observation_id") != action.get("citation_eligibility_observation_id"):
        raise PermissionError("citation rendering Q1 observation ID mismatch")
    if state.get("citation_eligibility_id") != r1_state.get("citation_eligibility_id"):
        raise PermissionError("citation rendering R1/Q1 ID mismatch")
    if projection.get("owner") != "RunKernel.FollowupCitationEligibility":
        raise PermissionError("citation rendering requires Q1 projection")
    if projection.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical Q1 projection")
    if not history:
        raise PermissionError("citation rendering requires Q1 history")
    if _mapping(history[-1]) != _mapping(projection):
        raise PermissionError("citation rendering Q1 history mismatch")
    if action.get("followup_citation_eligibility_digest") != (
        followup_projection_digest(state)
    ):
        raise PermissionError("citation rendering Q1 digest mismatch")


def _validate_t1_p1_state(
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
) -> None:
    if state.get("owner") != "RunKernel.FollowupFinalEvidenceSelection":
        raise PermissionError("citation rendering requires RunKernel P1 state")
    if state.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical P1 state")
    if state.get("final_evidence_selection_mode") != (
        AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
    ):
        raise PermissionError("citation rendering requires AG-96I3P1 mode")
    if state.get("final_evidence_selection_id") != action.get(
        "final_evidence_selection_id"
    ):
        raise PermissionError("citation rendering P1 selection ID mismatch")
    if state.get("observation_id") != action.get("final_evidence_selection_observation_id"):
        raise PermissionError("citation rendering P1 observation ID mismatch")
    if projection.get("owner") != "RunKernel.FollowupFinalEvidenceSelection":
        raise PermissionError("citation rendering requires P1 projection")
    if projection.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical P1 projection")
    if not history:
        raise PermissionError("citation rendering requires P1 history")
    if _mapping(history[-1]) != _mapping(projection):
        raise PermissionError("citation rendering P1 history mismatch")
    if action.get("followup_final_evidence_selection_digest") != (
        followup_projection_digest(state)
    ):
        raise PermissionError("citation rendering P1 digest mismatch")


def _validate_t1_o2_state(
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
) -> None:
    if state.get("owner") != "RunKernel.FollowupBlockedFinalAnswerPacketShell":
        raise PermissionError("citation rendering requires RunKernel O2 shell")
    if state.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical O2 shell")
    if state.get("blocked_final_answer_packet_mode") != (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    ):
        raise PermissionError("citation rendering requires AG-96I3O2 shell")
    if state.get("blocked_final_answer_packet_shell_id") != action.get(
        "blocked_final_answer_packet_shell_id"
    ):
        raise PermissionError("citation rendering O2 shell ID mismatch")
    if state.get("observation_id") != action.get(
        "blocked_final_answer_packet_shell_observation_id"
    ):
        raise PermissionError("citation rendering O2 observation ID mismatch")
    if projection.get("owner") != "RunKernel.FollowupBlockedFinalAnswerPacketShell":
        raise PermissionError("citation rendering requires O2 projection")
    if projection.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical O2 projection")
    if not history:
        raise PermissionError("citation rendering requires O2 history")
    if _mapping(history[-1]) != _mapping(projection):
        raise PermissionError("citation rendering O2 history mismatch")
    if action.get("blocked_final_answer_packet_shell_digest") != (
        followup_projection_digest(state)
    ):
        raise PermissionError("citation rendering O2 shell digest mismatch")


def _validate_t1_o1_state(
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
) -> None:
    if state.get("owner") != "RunKernel.FollowupFinalAnswerPacketReadiness":
        raise PermissionError("citation rendering requires RunKernel O1 readiness")
    if state.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical O1 readiness")
    if state.get("packet_preparation_readiness_mode") != (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    ):
        raise PermissionError("citation rendering requires AG-96I3O1 readiness")
    if state.get("packet_preparation_readiness_id") != action.get(
        "packet_preparation_readiness_id"
    ):
        raise PermissionError("citation rendering O1 readiness ID mismatch")
    if state.get("observation_id") != action.get("readiness_observation_id"):
        raise PermissionError("citation rendering O1 observation ID mismatch")
    if projection.get("owner") != "RunKernel.FollowupFinalAnswerPacketReadiness":
        raise PermissionError("citation rendering requires O1 projection")
    if projection.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical O1 projection")
    if not history:
        raise PermissionError("citation rendering requires O1 history")
    if _mapping(history[-1]) != _mapping(projection):
        raise PermissionError("citation rendering O1 history mismatch")
    if action.get("followup_final_answer_packet_readiness_digest") != (
        followup_projection_digest(state)
    ):
        raise PermissionError("citation rendering O1 readiness digest mismatch")


def _validate_t1_recheck_intake_sufficiency_ledger(
    recheck: Mapping[str, Any],
    intake: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    ledger: Mapping[str, Any],
    action: Mapping[str, Any],
) -> None:
    if recheck.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
        raise PermissionError("citation rendering requires AG-96I3N recheck")
    if recheck.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical recheck")
    if recheck.get("sufficiency_recheck_mode") != FOLLOWUP_SUFFICIENCY_RECHECK_MODE:
        raise PermissionError("citation rendering requires recheck mode")
    if intake.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical M2 intake")
    if intake.get("evidence_ledger_intake_mode") != (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        raise PermissionError("citation rendering requires AG-96I3M2 intake")
    if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
        raise PermissionError("citation rendering requires SufficiencyJudgment")
    if sufficiency.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical SufficiencyJudgment")
    if ledger.get("owner") != "RunKernel.EvidenceLedger":
        raise PermissionError("citation rendering requires EvidenceLedger")
    if ledger.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical EvidenceLedger")
    for field in (
        "recheck_id",
        "intake_id",
        "execution_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
    ):
        intake_fields = {
            "intake_id",
            "execution_id",
            "followup_authorization_consumption_id",
            "sealed_candidate_id",
            "provider_job_kind",
            "component_id",
            "source_obligation_id",
        }
        expected = intake.get(field) if field in intake_fields else recheck.get(field)
        if action.get(field) != expected:
            raise PermissionError(f"citation rendering {field} mismatch")
    if action.get("followup_sufficiency_recheck_id") != recheck.get(
        "recheck_id"
    ):
        raise PermissionError("citation rendering recheck action ID mismatch")
    if action.get("followup_sufficiency_recheck_observation_id") != recheck.get(
        "observation_id"
    ):
        raise PermissionError("citation rendering recheck observation mismatch")
    if action.get("followup_evidence_intake_id") != intake.get("intake_id"):
        raise PermissionError("citation rendering intake action ID mismatch")
    if action.get("followup_evidence_intake_observation_id") != intake.get(
        "observation_id"
    ):
        raise PermissionError("citation rendering intake observation mismatch")
    if action.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(ledger)
    ):
        raise PermissionError("citation rendering EvidenceLedger digest mismatch")
    if action.get("sufficiency_judgment_digest") != (
        followup_projection_digest(sufficiency)
    ):
        raise PermissionError("citation rendering SufficiencyJudgment digest mismatch")
    if action.get("followup_sufficiency_recheck_digest") != (
        followup_projection_digest(recheck)
    ):
        raise PermissionError("citation rendering recheck digest mismatch")


def _validate_t1_packet(
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    action: Mapping[str, Any],
    r1_state: Mapping[str, Any],
) -> None:
    if authority != {}:
        raise PermissionError("citation rendering requires empty authority projection")
    if packet.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("citation rendering requires RunKernel packet owner")
    if packet.get("canonical_state") is not True:
        raise PermissionError("citation rendering requires canonical FinalAnswerPacket")
    if packet.get("packet_id") != r1_state.get("packet_id"):
        raise PermissionError("citation rendering packet ID mismatch")
    if packet.get("readiness_status") != "blocked":
        raise PermissionError("citation rendering requires blocked packet")
    if packet.get("final_answer_allowed") is not False:
        raise PermissionError("citation rendering requires final_answer_allowed=false")
    if packet.get("answer_ready") is not False:
        raise PermissionError("citation rendering requires answer_ready=false")
    if packet.get("author_input_refs") != {}:
        raise PermissionError("citation rendering requires empty author_input_refs")
    if packet.get("author_payload_ref") not in (None, False, [], (), {}):
        raise PermissionError("citation rendering requires no author_payload_ref")
    if packet.get("citations_rendered") is not False:
        raise PermissionError("citation rendering requires citations_rendered=false")
    if packet.get("citation_formatter_invoked") is not False:
        raise PermissionError("citation rendering requires formatter closed")
    if packet.get("citation_rendering_deferred") is not True:
        raise PermissionError("citation rendering requires rendering deferral")
    if packet.get("not_role_consumption_payload") is not True:
        raise PermissionError("citation rendering requires non-role packet")
    if action.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("citation rendering FinalAnswerPacket digest mismatch")
    if r1_state.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("citation rendering R1 packet digest mismatch")
    _reject_t1_packet_output_refs(packet)
    _reject_t1_closed_output_fields(packet, context="FinalAnswerPacket")
    _ensure_no_private_payload(packet)


def _validate_t1_action_inputs(
    action: Mapping[str, Any],
    *,
    r1_state: Mapping[str, Any],
    q1_state: Mapping[str, Any],
    q1_projection: Mapping[str, Any],
    packet: Mapping[str, Any],
    selection: Mapping[str, Any],
    shell: Mapping[str, Any],
    readiness: Mapping[str, Any],
    recheck: Mapping[str, Any],
    intake: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    ledger: Mapping[str, Any],
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
        "packet_preparation_readiness_id",
        "readiness_observation_id",
        "blocked_final_answer_packet_shell_id",
        "blocked_final_answer_packet_shell_observation_id",
        "final_evidence_selection_id",
        "final_evidence_selection_observation_id",
        "citation_eligibility_id",
        "citation_eligibility_observation_id",
        "citation_source_handoff_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "packet_preparation_readiness_mode",
        "blocked_final_answer_packet_mode",
        "final_evidence_selection_mode",
        "citation_eligibility_mode",
        "citation_source_handoff_mode",
        "evidence_ledger_projection_digest",
        "sufficiency_judgment_digest",
        "followup_sufficiency_recheck_digest",
        "followup_final_answer_packet_readiness_digest",
        "blocked_final_answer_packet_shell_digest",
        "blocked_final_answer_packet_digest",
        "followup_final_evidence_selection_digest",
        "followup_citation_eligibility_digest",
        "current_final_answer_packet_digest",
    ):
        if action.get(field) != r1_state.get(field):
            raise PermissionError(f"citation rendering R1 {field} mismatch")
    if action.get("citation_source_handoff_observation_id") != r1_state.get(
        "observation_id"
    ):
        raise PermissionError(
            "citation rendering R1 citation_source_handoff_observation_id mismatch"
        )
    if action.get("citation_rendering_mode") != AG96I3T1_CITATION_RENDERING_MODE:
        raise PermissionError("citation rendering action must use AG-96I3T1 mode")
    if not action.get("citation_rendering_id"):
        raise PermissionError("citation rendering requires rendering ID")
    if _strings(action.get("requirement_ids")) != _strings(
        r1_state.get("requirement_ids")
    ):
        raise PermissionError("citation rendering requirement_ids mismatch")
    if _strings(action.get("expected_source_classes")) != _strings(
        r1_state.get("expected_source_classes")
    ):
        raise PermissionError("citation rendering expected_source_classes mismatch")
    if action.get("provider_execution_licensed") is not False:
        raise PermissionError("citation rendering must keep provider unlicensed")
    if action.get("evidence_ledger_intake_mode") != (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        raise PermissionError("citation rendering requires AG-96I3M2 intake")
    if action.get("sufficiency_recheck_mode") != FOLLOWUP_SUFFICIENCY_RECHECK_MODE:
        raise PermissionError("citation rendering requires AG-96I3N recheck")
    if action.get("packet_preparation_readiness_mode") != (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    ):
        raise PermissionError("citation rendering must bind O1 readiness")
    if action.get("blocked_final_answer_packet_mode") != (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    ):
        raise PermissionError("citation rendering must bind O2 shell")
    if action.get("final_evidence_selection_mode") != (
        AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
    ):
        raise PermissionError("citation rendering must bind P1 selection")
    if action.get("citation_eligibility_mode") != AG96I3Q1_CITATION_ELIGIBILITY_MODE:
        raise PermissionError("citation rendering must bind Q1 eligibility")
    if action.get("citation_source_handoff_mode") != (
        AG96I3R1_CITATION_SOURCE_HANDOFF_MODE
    ):
        raise PermissionError("citation rendering must bind R1 handoff")
    if action.get("final_answer_allowed") is not False:
        raise PermissionError("citation rendering must keep answers disallowed")
    if action.get("answer_ready") is not False:
        raise PermissionError("citation rendering must keep answer_ready=false")
    if action.get("citation_rendering_deferred") is not True:
        raise PermissionError("citation rendering must keep final rendering deferred")
    if action.get("author_execution_deferred") is not True:
        raise PermissionError("citation rendering must defer Author execution")
    if action.get("live_validation_not_run") is not True:
        raise PermissionError("citation rendering must not run live validation")
    if action.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(ledger)
    ):
        raise PermissionError("citation rendering EvidenceLedger digest mismatch")
    if action.get("sufficiency_judgment_digest") != (
        followup_projection_digest(sufficiency)
    ):
        raise PermissionError("citation rendering SufficiencyJudgment digest mismatch")
    if action.get("followup_sufficiency_recheck_digest") != (
        followup_projection_digest(recheck)
    ):
        raise PermissionError("citation rendering recheck digest mismatch")
    if action.get("followup_final_answer_packet_readiness_digest") != (
        followup_projection_digest(readiness)
    ):
        raise PermissionError("citation rendering O1 readiness digest mismatch")
    if action.get("blocked_final_answer_packet_shell_digest") != (
        followup_projection_digest(shell)
    ):
        raise PermissionError("citation rendering O2 shell digest mismatch")
    if action.get("followup_final_evidence_selection_digest") != (
        followup_projection_digest(selection)
    ):
        raise PermissionError("citation rendering P1 digest mismatch")
    if action.get("followup_citation_eligibility_digest") != (
        followup_projection_digest(q1_state)
    ):
        raise PermissionError("citation rendering Q1 digest mismatch")
    if action.get("followup_citation_source_handoff_digest") != (
        followup_projection_digest(r1_state)
    ):
        raise PermissionError("citation rendering R1 digest mismatch")
    if action.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("citation rendering FinalAnswerPacket digest mismatch")
    if q1_projection.get("canonical_final_answer_packet_ref", {}).get(
        "packet_id"
    ) != packet.get("packet_id"):
        raise PermissionError("citation rendering Q1 packet ref mismatch")
    if selection.get("final_evidence_selection_id") != action.get(
        "final_evidence_selection_id"
    ):
        raise PermissionError("citation rendering P1 state mismatch")
    if shell.get("blocked_final_answer_packet_shell_id") != action.get(
        "blocked_final_answer_packet_shell_id"
    ):
        raise PermissionError("citation rendering O2 state mismatch")
    if readiness.get("packet_preparation_readiness_id") != action.get(
        "packet_preparation_readiness_id"
    ):
        raise PermissionError("citation rendering O1 state mismatch")
    if intake.get("intake_id") != action.get("intake_id"):
        raise PermissionError("citation rendering intake state mismatch")
    _ensure_no_private_payload(action)


def _rendered_source_entries(
    source_identity_records: Sequence[Mapping[str, Any]],
    *,
    rendering_id: str,
    rendering_mode: str,
) -> tuple[dict[str, Any], ...]:
    entries: list[dict[str, Any]] = []
    for position, source in enumerate(source_identity_records, start=1):
        source_position = _safe_int(source.get("source_identity_position")) or position
        entry = _compact(
            {
                "rendered_source_entry_id": (
                    f"{rendering_id}:source-entry:{source_position}"
                ),
                "source_identity_position": source_position,
                "citation_id": clean_text(source.get("citation_id"), limit=220),
                "evidence_id": clean_text(source.get("evidence_id"), limit=220),
                "candidate_id": clean_text(source.get("candidate_id"), limit=220),
                "source_id": clean_text(source.get("source_id"), limit=220),
                "requirement_id": clean_token(source.get("requirement_id")),
                "source_obligation_id": clean_token(
                    source.get("source_obligation_id")
                ),
                "stable_source_label": f"S{position}",
                "title": clean_text(source.get("title"), limit=300),
                "domain": clean_text(source.get("domain"), limit=200),
                "url": clean_text(source.get("url"), limit=500),
                "source_class": clean_token(source.get("source_class")),
                "source_tier": clean_token(source.get("source_tier")),
                "packet_local": True,
                "derived_from_r1": True,
                "rendering_mode": clean_token(rendering_mode),
                "rendering_policy": FOLLOWUP_CITATION_RENDERING_POLICY,
            }
        )
        for required in ("rendered_source_entry_id", "citation_id", "source_id"):
            if not entry.get(required):
                raise PermissionError(
                    f"citation rendering requires rendered entry {required}"
                )
        _ensure_no_private_payload(entry)
        entries.append(entry)
    return tuple(entries)


def _citation_rendering_lineage(
    action: Mapping[str, Any],
    *,
    r1_state: Mapping[str, Any],
    q1_state: Mapping[str, Any],
    selection: Mapping[str, Any],
    shell: Mapping[str, Any],
    readiness: Mapping[str, Any],
    recheck: Mapping[str, Any],
    intake: Mapping[str, Any],
    rendered_source_entry_digest: str,
) -> dict[str, Any]:
    return _compact(
        {
            "citation_rendering_id": action.get("citation_rendering_id"),
            "citation_rendering_mode": action.get("citation_rendering_mode"),
            "rendering_policy": FOLLOWUP_CITATION_RENDERING_POLICY,
            "citation_source_handoff_id": r1_state.get("citation_source_handoff_id"),
            "citation_source_handoff_observation_id": r1_state.get("observation_id"),
            "citation_source_handoff_mode": r1_state.get(
                "citation_source_handoff_mode"
            ),
            "followup_citation_source_handoff_digest": action.get(
                "followup_citation_source_handoff_digest"
            ),
            "source_identity_digest": r1_state.get("source_identity_digest"),
            "rendered_source_entry_digest": rendered_source_entry_digest,
            "citation_eligibility_id": q1_state.get("citation_eligibility_id"),
            "citation_eligibility_observation_id": q1_state.get("observation_id"),
            "citation_eligibility_mode": q1_state.get("citation_eligibility_mode"),
            "followup_citation_eligibility_digest": action.get(
                "followup_citation_eligibility_digest"
            ),
            "final_evidence_selection_id": selection.get(
                "final_evidence_selection_id"
            ),
            "final_evidence_selection_observation_id": selection.get(
                "observation_id"
            ),
            "final_evidence_selection_mode": selection.get(
                "final_evidence_selection_mode"
            ),
            "followup_final_evidence_selection_digest": action.get(
                "followup_final_evidence_selection_digest"
            ),
            "blocked_final_answer_packet_shell_id": shell.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "blocked_final_answer_packet_shell_observation_id": shell.get(
                "observation_id"
            ),
            "blocked_final_answer_packet_shell_digest": action.get(
                "blocked_final_answer_packet_shell_digest"
            ),
            "blocked_final_answer_packet_digest": action.get(
                "blocked_final_answer_packet_digest"
            ),
            "packet_preparation_readiness_id": readiness.get(
                "packet_preparation_readiness_id"
            ),
            "readiness_observation_id": readiness.get("observation_id"),
            "followup_final_answer_packet_readiness_digest": action.get(
                "followup_final_answer_packet_readiness_digest"
            ),
            "recheck_id": recheck.get("recheck_id"),
            "followup_sufficiency_recheck_digest": action.get(
                "followup_sufficiency_recheck_digest"
            ),
            "intake_id": intake.get("intake_id"),
            "execution_id": action.get("execution_id"),
            "followup_authorization_consumption_id": action.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": action.get("sealed_candidate_id"),
            "provider_job_kind": action.get("provider_job_kind"),
            "component_id": action.get("component_id"),
            "source_obligation_id": action.get("source_obligation_id"),
            "requirement_ids": list(_strings(action.get("requirement_ids"))),
            "expected_source_classes": list(
                _strings(action.get("expected_source_classes"))
            ),
            "evidence_ledger_projection_digest": action.get(
                "evidence_ledger_projection_digest"
            ),
            "sufficiency_judgment_digest": action.get(
                "sufficiency_judgment_digest"
            ),
            "current_final_answer_packet_digest": action.get(
                "current_final_answer_packet_digest"
            ),
            "derived_only_from_r1_source_identity_records": True,
        }
    )


def _citation_rendering_behavior_boundary_flags() -> dict[str, bool]:
    return citation_rendering_boundary_flags()


def _citation_rendering_redaction_posture() -> dict[str, bool]:
    return {
        **followup_common_redaction_posture(),
        "raw_text_retained": False,
        "provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "private_payload_retained": False,
        "r1_source_identity_records_only": True,
        "machine_readable_source_entries_only": True,
        "citation_rendered_text_retained": False,
        "ordered_source_output_retained": False,
        "author_payload_retained": False,
    }


def _reject_t1_packet_output_refs(payload: Mapping[str, Any]) -> None:
    for field in (
        "author_payload_ref",
        "final_answer_authority_projection",
        "author_input_payload",
        "ordered_sources",
        "ordered_product_source_output",
        "source_list_prose",
        "markdown_source_list",
        "rendered_citation",
        "rendered_citations",
        "formatted_citation",
        "formatted_citations",
        "final_answer_text",
    ):
        if payload.get(field) not in (None, False, [], (), {}):
            raise PermissionError(f"citation rendering packet must not carry {field}")


def _reject_t1_closed_output_fields(
    payload: Mapping[str, Any],
    *,
    context: str,
) -> None:
    for field in (
        "citations_rendered",
        "citation_rendering_changed",
        "citation_behavior_changed",
        "citation_formatter_invoked",
        "author_payload_created",
        "author_activation_allowed",
        "analyst_activation_allowed",
        "analyst_handoff_created",
        "economist_activation_allowed",
        "economist_handoff_created",
        "economist_code_execution_allowed",
        "prompt_behavior_changed",
        "product_answer_behavior_changed",
    ):
        if payload.get(field) is not False:
            raise PermissionError(f"{context} requires {field}=False")
    if payload.get("author_execution_deferred") is not True:
        raise PermissionError(f"{context} requires deferred Author")
    if payload.get("live_validation_not_run") is not True:
        raise PermissionError(f"{context} requires no live validation")
    if payload.get("ordered_product_source_output_created", False) is not False:
        raise PermissionError(
            f"{context} requires ordered_product_source_output_created=False"
        )


def _reject_forbidden_t1_payload(payload: Mapping[str, Any]) -> None:
    forbidden = {
        "analyst_handoff",
        "analyst_handoff_ref",
        "author_authority_block",
        "author_input_payload",
        "author_input_refs",
        "author_payload_ref",
        "economist_handoff",
        "economist_handoff_ref",
        "final_answer_authority_projection",
        "final_answer_citation",
        "final_answer_citation_string",
        "final_answer_text",
        "formatted_citation",
        "formatted_citations",
        "inline_citation",
        "inline_citation_string",
        "markdown_source_list",
        "ordered_product_source_output",
        "ordered_source_output",
        "ordered_sources",
        "prompt",
        "prompt_text",
        "rendered_citation",
        "rendered_citations",
        "source_list_prose",
    }

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                token = clean_token(key, limit=120)
                if token in forbidden:
                    raise PermissionError(
                        "citation rendering must not carry "
                        f"{token}"
                    )
                walk(child)
        elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
            for child in value:
                walk(child)

    walk(payload)


def _ensure_no_private_payload(value: Any) -> None:
    if _contains_private_payload(value):
        raise PermissionError("citation rendering contains raw/private payload")


def _contains_private_payload(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = clean_token(key) or ""
            normalized = token.casefold().replace("-", "_").replace(" ", "_")
            if normalized in {
                "api_key",
                "cache",
                "db",
                "db_row",
                "full_trace",
                "log",
                "logs",
                "output_packet",
                "password",
                "private_log",
                "provider_payload",
                "raw_model_response",
                "raw_payload",
                "raw_prompt",
                "raw_provider_payload",
                "raw_response",
                "raw_text",
                "raw_trace",
                "secret",
                "secrets",
                "snippet",
                "snippets",
                "text",
                "token",
            } or normalized.startswith("raw_") or normalized.startswith("private_"):
                if item in (None, False, [], {}, (), ""):
                    continue
                return True
            if _contains_private_payload(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return any(_contains_private_payload(item) for item in value)
    elif isinstance(value, str):
        lowered = value.casefold()
        return any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS)
    return False


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
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


def _safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "AG96I3T1_CITATION_RENDERING_MODE",
    "FOLLOWUP_CITATION_RENDERING_GATE_REASON",
    "FOLLOWUP_CITATION_RENDERING_POLICY",
    "FOLLOWUP_CITATION_RENDERING_SCHEMA_VERSION",
    "FOLLOWUP_CITATION_RENDERING_STAGE",
    "FOLLOWUP_CITATION_RENDERING_TRACE_KEY",
    "FollowupCitationRenderingActionResult",
    "FollowupCitationRenderingConsumptionRecord",
    "FollowupCitationRenderingObservation",
    "FollowupCitationRenderingRequest",
    "FollowupCitationRenderingResult",
    "build_followup_citation_rendering_record",
    "execute_followup_citation_rendering_action",
]
