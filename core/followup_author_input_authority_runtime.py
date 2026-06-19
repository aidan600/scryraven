"""AG-96I3U1 Author-input authority projection runtime.

This module packages canonical T1 rendered source entries and the existing
FinalAnswerPacket/P1/Q1/R1 authority chain as sanitized machine-readable refs
for a later Author gate. It does not build prompt text, final answer text,
product source output, ordered source lists, or invoke Author/providers/search.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_citation_rendering_runtime import AG96I3T1_CITATION_RENDERING_MODE
from core.followup_citation_source_handoff_runtime import (
    AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
)
from core.followup_deliberation import clean_text, safe_json, stable_hash
from core.followup_final_answer_packet_runtime import (
    AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
    AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE,
    AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE,
    AG96I3Q1_CITATION_ELIGIBILITY_MODE,
    followup_projection_digest,
)
from core.followup_fixture_boundaries import (
    followup_closed_surface_boundary_flags,
    followup_common_redaction_posture,
)
from core.followup_sufficiency_recheck_runtime import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
)

FOLLOWUP_AUTHOR_INPUT_AUTHORITY_SCHEMA_VERSION = (
    "followup_author_input_authority_ag96i3u1_v1"
)
FOLLOWUP_AUTHOR_INPUT_AUTHORITY_TRACE_KEY = "followup_author_input_authority_runtime"
FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE = "followup_author_input_authority"
AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE = (
    "ag96i3u1_author_input_authority_projection"
)
FOLLOWUP_AUTHOR_INPUT_AUTHORITY_GATE_REASON = (
    "ag96i3u1_author_input_authority_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS = "author_payload_ready_execution_deferred"
FOLLOWUP_AUTHOR_INPUT_REFS_STATUS = "author_execution_deferred"

_CLOSED_FALSE_FIELDS = (
    "prompt_text_included",
    "final_text_included",
    "author_activation_allowed",
    "product_answer_ready",
)

_FORBIDDEN_KEY_PARTS = (
    "prompt_text",
    "final_answer_text",
    "final_text",
    "ordered_sources",
    "ordered_product_source_output",
    "markdown_source_list",
    "source_list_prose",
    "inline_citation",
    "final_answer_citation",
    "rendered_citation",
    "formatted_citation",
    "author_input_payload",
    "author_prompt",
    "author_prose",
    "analyst_handoff",
    "economist_handoff",
    "raw_prompt",
    "raw_provider",
    "raw_payload",
    "raw_trace",
    "raw_text",
    "provider_payload",
    "model_response",
    "db_row",
    "private_log",
    "secret",
    "api_key",
)

_SOURCE_ENTRY_REF_FIELDS = (
    "rendered_source_entry_id",
    "source_identity_position",
    "citation_id",
    "evidence_id",
    "candidate_id",
    "source_id",
    "requirement_id",
    "source_obligation_id",
    "stable_source_label",
    "title",
    "domain",
    "url",
    "source_class",
    "source_tier",
    "packet_local",
    "derived_from_r1",
    "rendering_mode",
)

_SOURCE_HANDOFF_REF_FIELDS = (
    "source_identity_position",
    "citation_id",
    "evidence_id",
    "candidate_id",
    "source_id",
    "requirement_id",
    "source_obligation_id",
    "title",
    "domain",
    "url",
    "source_class",
    "source_tier",
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorInputAuthorityActionResult:
    record: "FollowupAuthorInputAuthorityRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorInputAuthorityRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def execute_followup_author_input_authority_action(
    action: Any,
    *,
    evidence_ledger_projection: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    followup_final_answer_packet_readiness_state: Mapping[str, Any],
    followup_final_answer_packet_readiness_projection: Mapping[str, Any],
    followup_final_answer_packet_readiness_history: Sequence[Mapping[str, Any]],
    followup_blocked_final_answer_packet_shell_state: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_projection: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_history: Sequence[Mapping[str, Any]],
    followup_final_evidence_selection_state: Mapping[str, Any],
    followup_final_evidence_selection_projection: Mapping[str, Any],
    followup_final_evidence_selection_history: Sequence[Mapping[str, Any]],
    followup_citation_eligibility_state: Mapping[str, Any],
    followup_citation_eligibility_projection: Mapping[str, Any],
    followup_citation_eligibility_history: Sequence[Mapping[str, Any]],
    followup_citation_source_handoff_state: Mapping[str, Any],
    followup_citation_source_handoff_projection: Mapping[str, Any],
    followup_citation_source_handoff_history: Sequence[Mapping[str, Any]],
    followup_citation_rendering_state: Mapping[str, Any],
    followup_citation_rendering_projection: Mapping[str, Any],
    followup_citation_rendering_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorInputAuthorityActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
        stage=FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY_PREPARED
        ),
    )
    record = build_followup_author_input_authority_record(
        action_inputs=_mapping(action.inputs),
        evidence_ledger_projection=evidence_ledger_projection,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        followup_evidence_intake_state=followup_evidence_intake_state,
        followup_sufficiency_recheck_state=followup_sufficiency_recheck_state,
        followup_final_answer_packet_readiness_state=(
            followup_final_answer_packet_readiness_state
        ),
        followup_final_answer_packet_readiness_projection=(
            followup_final_answer_packet_readiness_projection
        ),
        followup_final_answer_packet_readiness_history=(
            followup_final_answer_packet_readiness_history
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
        followup_final_evidence_selection_state=followup_final_evidence_selection_state,
        followup_final_evidence_selection_projection=(
            followup_final_evidence_selection_projection
        ),
        followup_final_evidence_selection_history=(
            followup_final_evidence_selection_history
        ),
        followup_citation_eligibility_state=followup_citation_eligibility_state,
        followup_citation_eligibility_projection=followup_citation_eligibility_projection,
        followup_citation_eligibility_history=followup_citation_eligibility_history,
        followup_citation_source_handoff_state=followup_citation_source_handoff_state,
        followup_citation_source_handoff_projection=(
            followup_citation_source_handoff_projection
        ),
        followup_citation_source_handoff_history=(
            followup_citation_source_handoff_history
        ),
        followup_citation_rendering_state=followup_citation_rendering_state,
        followup_citation_rendering_projection=followup_citation_rendering_projection,
        followup_citation_rendering_history=followup_citation_rendering_history,
        final_answer_packet=final_answer_packet,
        final_answer_authority_projection=final_answer_authority_projection,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY_PREPARED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_input_authority_state": record.to_dict()},
    )
    return FollowupAuthorInputAuthorityActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_input_authority_record(
    *,
    action_inputs: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    followup_final_answer_packet_readiness_state: Mapping[str, Any],
    followup_final_answer_packet_readiness_projection: Mapping[str, Any],
    followup_final_answer_packet_readiness_history: Sequence[Mapping[str, Any]],
    followup_blocked_final_answer_packet_shell_state: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_projection: Mapping[str, Any],
    followup_blocked_final_answer_packet_shell_history: Sequence[Mapping[str, Any]],
    followup_final_evidence_selection_state: Mapping[str, Any],
    followup_final_evidence_selection_projection: Mapping[str, Any],
    followup_final_evidence_selection_history: Sequence[Mapping[str, Any]],
    followup_citation_eligibility_state: Mapping[str, Any],
    followup_citation_eligibility_projection: Mapping[str, Any],
    followup_citation_eligibility_history: Sequence[Mapping[str, Any]],
    followup_citation_source_handoff_state: Mapping[str, Any],
    followup_citation_source_handoff_projection: Mapping[str, Any],
    followup_citation_source_handoff_history: Sequence[Mapping[str, Any]],
    followup_citation_rendering_state: Mapping[str, Any],
    followup_citation_rendering_projection: Mapping[str, Any],
    followup_citation_rendering_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorInputAuthorityRecord:
    action = _mapping(action_inputs)
    packet = _mapping(final_answer_packet)
    t1 = _mapping(followup_citation_rendering_state)
    r1 = _mapping(followup_citation_source_handoff_state)
    q1 = _mapping(followup_citation_eligibility_state)
    p1 = _mapping(followup_final_evidence_selection_state)
    o2 = _mapping(followup_blocked_final_answer_packet_shell_state)
    o1 = _mapping(followup_final_answer_packet_readiness_state)
    n_state = _mapping(followup_sufficiency_recheck_state)
    m2_state = _mapping(followup_evidence_intake_state)
    sufficiency = _mapping(sufficiency_judgment_projection)
    ledger = _mapping(evidence_ledger_projection)

    _validate_u1_action_flags(action)
    _validate_packet_before_u1(packet)
    if _mapping(final_answer_authority_projection):
        raise PermissionError("U1 requires empty final_answer_authority_projection")
    _validate_authority_chain(
        action=action,
        packet=packet,
        t1=t1,
        t1_projection=followup_citation_rendering_projection,
        t1_history=followup_citation_rendering_history,
        r1=r1,
        r1_projection=followup_citation_source_handoff_projection,
        r1_history=followup_citation_source_handoff_history,
        q1=q1,
        q1_projection=followup_citation_eligibility_projection,
        q1_history=followup_citation_eligibility_history,
        p1=p1,
        p1_projection=followup_final_evidence_selection_projection,
        p1_history=followup_final_evidence_selection_history,
        o2=o2,
        o2_projection=followup_blocked_final_answer_packet_shell_projection,
        o2_history=followup_blocked_final_answer_packet_shell_history,
        o1=o1,
        o1_projection=followup_final_answer_packet_readiness_projection,
        o1_history=followup_final_answer_packet_readiness_history,
        n_state=n_state,
        m2_state=m2_state,
        sufficiency=sufficiency,
        ledger=ledger,
    )

    rendered_refs = _compact_refs(t1.get("rendered_source_entries"), _SOURCE_ENTRY_REF_FIELDS)
    source_handoff_refs = _compact_refs(
        r1.get("source_identity_records"),
        _SOURCE_HANDOFF_REF_FIELDS,
    )
    final_evidence_refs = _mappings(packet.get("evidence_allowed"))
    citation_eligible_refs = _mappings(packet.get("citation_eligible"))
    citation_ineligible_refs = _mappings(packet.get("citation_ineligible"))

    projection_core = {
        "owner": "RunKernel.FollowupAuthorInputAuthority",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": FOLLOWUP_AUTHOR_INPUT_AUTHORITY_SCHEMA_VERSION,
        "author_input_authority_id": action.get("author_input_authority_id"),
        "author_input_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
        "run_id": action.get("run_id"),
        "checkpoint_id": action.get("checkpoint_id"),
        "followup_authorization_consumption_id": action.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": action.get("sealed_candidate_id"),
        "followup_execution_id": action.get("followup_execution_id"),
        "execution_id": action.get("execution_id"),
        "followup_execution_observation_id": action.get(
            "followup_execution_observation_id"
        ),
        "followup_evidence_intake_id": action.get("followup_evidence_intake_id"),
        "intake_id": action.get("intake_id"),
        "followup_sufficiency_recheck_id": action.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": action.get("recheck_id"),
        "packet_preparation_readiness_id": action.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": action.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "packet_id": packet.get("packet_id"),
        "current_final_answer_packet_digest": followup_projection_digest(packet),
        "final_evidence_selection_id": p1.get("final_evidence_selection_id"),
        "citation_eligibility_id": q1.get("citation_eligibility_id"),
        "citation_source_handoff_id": r1.get("citation_source_handoff_id"),
        "citation_rendering_id": t1.get("citation_rendering_id"),
        "final_evidence_refs": safe_json(final_evidence_refs),
        "citation_eligibility_refs": safe_json(
            citation_eligible_refs + citation_ineligible_refs
        ),
        "citation_eligible_refs": safe_json(citation_eligible_refs),
        "citation_ineligible_refs": safe_json(citation_ineligible_refs),
        "source_handoff_refs": safe_json(source_handoff_refs),
        "rendered_source_entry_refs": safe_json(rendered_refs),
        "rendered_source_entry_count": len(rendered_refs),
        "rendered_source_entry_digest": t1.get("rendered_source_entry_digest"),
        "source_identity_digest": r1.get("source_identity_digest"),
        "author_allowed_evidence_refs": safe_json(final_evidence_refs),
        "author_allowed_citation_refs": safe_json(citation_eligible_refs),
        "author_rendered_source_entry_refs": safe_json(rendered_refs),
        "mandatory_caveat_refs": _strings(packet.get("mandatory_caveats")),
        "prohibited_upgrade_refs": _strings(packet.get("prohibited_upgrades")),
        "missing_obligation_refs": _mappings(packet.get("missing_obligations")),
        "partial_obligation_refs": _mappings(packet.get("partial_obligations")),
        "satisfied_obligation_refs": _mappings(packet.get("satisfied_obligations")),
        "source_bound_unknown_refs": _mappings(
            packet.get("source_bound_numeric_unknowns")
        )
        or _mappings(packet.get("source_bound_unknowns")),
        "conflict_refs": _strings(packet.get("unresolved_conflicts"))
        or _strings(sufficiency.get("unresolved_conflicts")),
        "author_mandatory_caveat_refs": _strings(packet.get("mandatory_caveats")),
        "author_prohibited_upgrade_refs": _strings(packet.get("prohibited_upgrades")),
        "author_missing_obligation_refs": _mappings(packet.get("missing_obligations")),
        "missing_or_unsatisfied_obligation_posture": _posture(
            packet,
            "missing_obligations",
            "partial_obligations",
        ),
        "conflict_posture": {
            "unresolved_conflicts": _strings(packet.get("unresolved_conflicts"))
            or _strings(sufficiency.get("unresolved_conflicts")),
        },
        "source_bound_unknown_posture": {
            "source_bound_numeric_unknowns": _mappings(
                packet.get("source_bound_numeric_unknowns")
            )
            or _mappings(packet.get("source_bound_unknowns")),
        },
        "inference_posture": _mapping(
            packet.get("inference_posture")
            or sufficiency.get("inference_posture")
            or {}
        ),
        "prompt_text_included": False,
        "final_text_included": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_gate_deferred": True,
        "product_answer_ready": False,
        "live_validation_not_run": True,
        "not_role_consumption_payload": True,
        "not_for_product_answer_activation": True,
        "author_payload_ref_created": True,
        "author_payload_created": False,
        "product_answer_behavior_changed": False,
        "ordered_product_source_output_created": False,
        "behavior_boundary_flags": _u1_boundary_flags(),
        "redaction_posture": followup_common_redaction_posture(
            sanitized_fixture_summary_only=False,
            packet_authority_refs_only=True,
            final_text_retained=False,
        ),
        "lineage": _lineage(action, ledger=ledger, m2=m2_state, n_state=n_state),
    }
    authority_projection_digest = followup_projection_digest(projection_core)
    payload_ref = {
        "payload_ref_id": f"author-payload-ref:{action['author_input_authority_id']}",
        "packet_id": packet.get("packet_id"),
        "authority_projection_digest": authority_projection_digest,
        "citation_rendering_id": t1.get("citation_rendering_id"),
        "rendered_source_entry_digest": t1.get("rendered_source_entry_digest"),
        "status": FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "prompt_text_included": False,
        "final_text_included": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "not_for_product_answer_activation": True,
    }
    projection = {**projection_core, "author_payload_ref": payload_ref}
    projection_digest = followup_projection_digest(projection)
    author_input_refs = {
        "status": FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "packet_id": packet.get("packet_id"),
        "current_final_answer_packet_digest": followup_projection_digest(packet),
        "final_evidence_selection_id": p1.get("final_evidence_selection_id"),
        "citation_eligibility_id": q1.get("citation_eligibility_id"),
        "citation_source_handoff_id": r1.get("citation_source_handoff_id"),
        "citation_rendering_id": t1.get("citation_rendering_id"),
        "author_input_authority_id": action.get("author_input_authority_id"),
        "final_answer_authority_projection_digest": projection_digest,
        "authority_projection_digest": authority_projection_digest,
        "author_payload_ref_id": payload_ref["payload_ref_id"],
        "rendered_source_entry_digest": t1.get("rendered_source_entry_digest"),
        "source_identity_digest": r1.get("source_identity_digest"),
        "evidence_ledger_projection_digest": evidence_ledger_projection_digest(ledger),
        "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
        "followup_evidence_intake_digest": followup_projection_digest(m2_state),
        "followup_sufficiency_recheck_digest": followup_projection_digest(n_state),
        "followup_final_answer_packet_readiness_digest": followup_projection_digest(o1),
        "blocked_final_answer_packet_shell_digest": followup_projection_digest(o2),
        "followup_final_evidence_selection_digest": followup_projection_digest(p1),
        "followup_citation_eligibility_digest": followup_projection_digest(q1),
        "followup_citation_source_handoff_digest": followup_projection_digest(r1),
        "followup_citation_rendering_digest": followup_projection_digest(t1),
        "prompt_text_included": False,
        "final_text_included": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_gate_deferred": True,
    }
    packet_mutation = {
        "author_input_refs": safe_json(author_input_refs),
        "author_payload_ref": safe_json(payload_ref),
        "author_input_authority_prepared": True,
        "author_payload_ref_created": True,
        "prompt_text_included": False,
        "final_text_included": False,
        "author_gate_deferred": True,
        "product_answer_ready": False,
    }
    state = {
        **projection,
        "record_type": "followup_author_input_authority_record",
        "status": "author_input_authority_prepared_execution_deferred",
        "final_answer_authority_projection": safe_json(projection),
        "final_answer_authority_projection_digest": projection_digest,
        "authority_projection_digest": authority_projection_digest,
        "author_input_refs": safe_json(author_input_refs),
        "packet_mutation": packet_mutation,
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorInputAuthorityRecord(state=safe_json(state))


def validate_followup_author_input_authority_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_author_input_authority_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_author_input_authority_state)
    if not observed:
        raise PermissionError("U1 observation requires author input authority state")
    _validate_u1_action_flags(action)
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
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "packet_preparation_readiness_id",
        "blocked_final_answer_packet_shell_id",
        "final_evidence_selection_id",
        "citation_eligibility_id",
        "citation_source_handoff_id",
        "citation_rendering_id",
        "author_input_authority_id",
        "author_input_authority_mode",
        "current_final_answer_packet_digest",
        "rendered_source_entry_digest",
    ):
        if observed.get(field) != action.get(field):
            raise PermissionError(f"U1 observation {field} does not match action")
    if observed.get("author_execution_deferred") is not True:
        raise PermissionError("U1 observation must defer Author execution")
    if observed.get("author_gate_deferred") is not True:
        raise PermissionError("U1 observation must defer Author gate")
    for field in _CLOSED_FALSE_FIELDS:
        if observed.get(field) is not False:
            raise PermissionError(f"U1 observation must keep {field}=False")
    _reject_forbidden_payload(observed)


def u1_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    packet = _mapping(current_packet)
    record = _mapping(record_state)
    mutation = _mapping(record.get("packet_mutation"))
    _validate_packet_before_u1(packet)
    updated = deepcopy(packet)
    updated.update(mutation)
    if updated.get("readiness_status") != "blocked":
        raise PermissionError("U1 must keep packet blocked")
    if updated.get("final_answer_allowed") is not False:
        raise PermissionError("U1 must keep final_answer_allowed=false")
    if updated.get("answer_ready") is not False:
        raise PermissionError("U1 must keep answer_ready=false")
    if updated.get("author_activation_allowed") is not False:
        raise PermissionError("U1 must keep Author activation closed")
    if updated.get("author_execution_deferred") is not True:
        raise PermissionError("U1 must keep Author execution deferred")
    _reject_forbidden_payload(
        {key: value for key, value in updated.items() if key in mutation}
    )
    return safe_json(updated)


def _validate_authority_chain(
    *,
    action: Mapping[str, Any],
    packet: Mapping[str, Any],
    t1: Mapping[str, Any],
    t1_projection: Mapping[str, Any],
    t1_history: Sequence[Mapping[str, Any]],
    r1: Mapping[str, Any],
    r1_projection: Mapping[str, Any],
    r1_history: Sequence[Mapping[str, Any]],
    q1: Mapping[str, Any],
    q1_projection: Mapping[str, Any],
    q1_history: Sequence[Mapping[str, Any]],
    p1: Mapping[str, Any],
    p1_projection: Mapping[str, Any],
    p1_history: Sequence[Mapping[str, Any]],
    o2: Mapping[str, Any],
    o2_projection: Mapping[str, Any],
    o2_history: Sequence[Mapping[str, Any]],
    o1: Mapping[str, Any],
    o1_projection: Mapping[str, Any],
    o1_history: Sequence[Mapping[str, Any]],
    n_state: Mapping[str, Any],
    m2_state: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> None:
    _require_owner_mode(t1, "RunKernel.FollowupCitationRendering", AG96I3T1_CITATION_RENDERING_MODE, "citation_rendering_mode")
    _require_current("T1", t1, t1_projection, t1_history)
    _require_owner_mode(r1, "RunKernel.FollowupCitationSourceHandoff", AG96I3R1_CITATION_SOURCE_HANDOFF_MODE, "citation_source_handoff_mode")
    _require_current("R1", r1, r1_projection, r1_history)
    _require_owner_mode(q1, "RunKernel.FollowupCitationEligibility", AG96I3Q1_CITATION_ELIGIBILITY_MODE, "citation_eligibility_mode")
    _require_current("Q1", q1, q1_projection, q1_history)
    _require_owner_mode(p1, "RunKernel.FollowupFinalEvidenceSelection", AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE, "final_evidence_selection_mode")
    _require_current("P1", p1, p1_projection, p1_history)
    _require_owner_mode(o2, "RunKernel.FollowupBlockedFinalAnswerPacketShell", AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE, "blocked_final_answer_packet_mode")
    _require_current("O2", o2, o2_projection, o2_history)
    _require_owner_mode(o1, "RunKernel.FollowupFinalAnswerPacketReadiness", AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE, "packet_preparation_readiness_mode")
    _require_current("O1", o1, o1_projection, o1_history)
    _require_owner_mode(n_state, "RunKernel.FollowupSufficiencyRecheck", FOLLOWUP_SUFFICIENCY_RECHECK_MODE, "sufficiency_recheck_mode")
    _require_owner_mode(m2_state, "RunKernel.FollowupEvidenceIntake", AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE, "evidence_ledger_intake_mode")
    if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
        raise PermissionError("U1 requires canonical SufficiencyJudgment")
    if sufficiency.get("canonical_state") is not True:
        raise PermissionError("U1 requires canonical SufficiencyJudgment")
    if ledger.get("owner") != "RunKernel.EvidenceLedger":
        raise PermissionError("U1 requires canonical EvidenceLedger")
    if ledger.get("canonical_state") is not True:
        raise PermissionError("U1 requires canonical EvidenceLedger")

    packet_digest = followup_projection_digest(packet)
    _expect(action, "current_final_answer_packet_digest", packet_digest)
    _expect(t1, "current_final_answer_packet_digest", packet_digest)
    _expect(action, "followup_citation_rendering_digest", followup_projection_digest(t1))
    _expect(action, "rendered_source_entry_digest", t1.get("rendered_source_entry_digest"))
    for state, key in (
        (p1, "final_evidence_selection_id"),
        (q1, "citation_eligibility_id"),
        (r1, "citation_source_handoff_id"),
        (t1, "citation_rendering_id"),
    ):
        _expect(action, key, state.get(key))
    digest_pairs = (
        ("evidence_ledger_projection_digest", evidence_ledger_projection_digest(ledger)),
        ("sufficiency_judgment_digest", followup_projection_digest(sufficiency)),
        ("followup_evidence_intake_digest", followup_projection_digest(m2_state)),
        ("followup_sufficiency_recheck_digest", followup_projection_digest(n_state)),
        ("followup_final_answer_packet_readiness_digest", followup_projection_digest(o1)),
        ("blocked_final_answer_packet_shell_digest", followup_projection_digest(o2)),
        ("followup_final_evidence_selection_digest", followup_projection_digest(p1)),
        ("followup_citation_eligibility_digest", followup_projection_digest(q1)),
        ("followup_citation_source_handoff_digest", followup_projection_digest(r1)),
    )
    for key, digest in digest_pairs:
        _expect(action, key, digest)

    rendered = _mappings(t1.get("rendered_source_entries"))
    identities = _mappings(r1.get("source_identity_records"))
    if not rendered:
        raise PermissionError("U1 requires non-empty T1 rendered source entries")
    if not t1.get("rendered_source_entry_digest"):
        raise PermissionError("U1 requires T1 rendered source entry digest")
    if stable_hash(safe_json(rendered)) != t1.get("rendered_source_entry_digest"):
        raise PermissionError("U1 rendered source entry digest mismatch")
    if len(rendered) != len(identities):
        raise PermissionError("U1 rendered source entry count mismatch")
    if [item.get("source_id") for item in rendered] != [
        item.get("source_id") for item in identities
    ]:
        raise PermissionError("U1 source IDs must match R1 identity order")
    expected_labels = [f"S{index}" for index in range(1, len(rendered) + 1)]
    if [item.get("stable_source_label") for item in rendered] != expected_labels:
        raise PermissionError("U1 rendered source labels must match R1 order")
    if packet.get("packet_id") != t1.get("packet_id"):
        raise PermissionError("U1 packet ID mismatch")
    if packet.get("evidence_allowed") != p1.get("evidence_allowed"):
        raise PermissionError("U1 final evidence differs from P1 packet selection")
    if packet.get("citation_eligible") != q1.get("citation_eligible"):
        raise PermissionError("U1 citation eligibility differs from Q1 packet state")


def _validate_u1_action_flags(action: Mapping[str, Any]) -> None:
    if action.get("author_input_authority_mode") != AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE:
        raise PermissionError("U1 action requires AG-96I3U1 mode")
    for field in _CLOSED_FALSE_FIELDS:
        if action.get(field) is not False:
            raise PermissionError(f"U1 action must keep {field}=False")
    for field in (
        "author_execution_deferred",
        "author_gate_deferred",
        "live_validation_not_run",
    ):
        if action.get(field) is not True:
            raise PermissionError(f"U1 action must set {field}=True")


def _validate_packet_before_u1(packet: Mapping[str, Any]) -> None:
    if packet.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("U1 requires RunKernel FinalAnswerPacket")
    if packet.get("canonical_state") is not True:
        raise PermissionError("U1 requires canonical FinalAnswerPacket")
    if packet.get("readiness_status") != "blocked":
        raise PermissionError("U1 requires blocked FinalAnswerPacket")
    if packet.get("final_answer_allowed") is not False:
        raise PermissionError("U1 requires final_answer_allowed=false")
    if packet.get("answer_ready") is not False:
        raise PermissionError("U1 requires answer_ready=false")
    if packet.get("author_input_refs") != {}:
        raise PermissionError("U1 requires empty packet author_input_refs")
    if packet.get("author_payload_ref") not in (None, False, [], {}, ()):
        raise PermissionError("U1 requires no packet author_payload_ref")
    if not _mappings(packet.get("evidence_allowed")):
        raise PermissionError("U1 requires P1-selected final evidence")
    if not _mappings(packet.get("citation_eligible")):
        raise PermissionError("U1 requires Q1 packet-local citation eligibility")
    for field in (
        "author_activation_allowed",
        "author_payload_created",
        "analyst_activation_allowed",
        "analyst_handoff_created",
        "economist_activation_allowed",
        "economist_handoff_created",
        "economist_code_execution_allowed",
        "prompt_behavior_changed",
        "product_answer_behavior_changed",
        "ordered_product_source_output_created",
    ):
        if packet.get(field, False) is not False:
            raise PermissionError(f"U1 requires packet {field}=False")
    if packet.get("author_execution_deferred") is not True:
        raise PermissionError("U1 requires deferred Author execution")
    if packet.get("live_validation_not_run") is not True:
        raise PermissionError("U1 requires live_validation_not_run=true")


def _require_owner_mode(
    state: Mapping[str, Any],
    owner: str,
    mode: str,
    mode_key: str,
) -> None:
    if state.get("owner") != owner:
        raise PermissionError(f"U1 requires {owner}")
    if state.get("canonical_state") is not True:
        raise PermissionError(f"U1 requires canonical {owner}")
    if state.get("trace_only") is not False or state.get("storage_only") is not False:
        raise PermissionError(f"U1 requires active canonical {owner}")
    if state.get(mode_key) != mode:
        raise PermissionError(f"U1 requires {mode}")


def _require_current(
    label: str,
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> None:
    projection_map = _mapping(projection)
    if not projection_map:
        raise PermissionError(f"U1 requires {label} projection")
    if projection_map.get("canonical_state") is not True:
        raise PermissionError(f"U1 requires canonical {label} projection")
    if not history:
        raise PermissionError(f"U1 requires {label} history")
    if _mapping(history[-1]) != projection_map:
        raise PermissionError(f"U1 requires current {label} history")
    state_id = (
        state.get("citation_rendering_id")
        or state.get("citation_source_handoff_id")
        or state.get("citation_eligibility_id")
        or state.get("final_evidence_selection_id")
        or state.get("blocked_final_answer_packet_shell_id")
        or state.get("packet_preparation_readiness_id")
    )
    if state_id and state_id not in projection_map.values():
        raise PermissionError(f"U1 {label} projection does not reference current state")


def _u1_boundary_flags() -> dict[str, bool]:
    flags = {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_consumed": True,
        "blocked_final_answer_packet_shell_consumed": True,
        "final_evidence_selection_consumed": True,
        "citation_eligibility_consumed": True,
        "citation_source_handoff_consumed": True,
        "citation_rendering_consumed": True,
        "t1_rendered_source_entries_consumed": True,
        "author_input_authority_projection_created": True,
        "author_payload_ref_created": True,
        "canonical_final_answer_packet_mutated": True,
        "final_answer_packet_updated": True,
        "final_answer_packet_rebuilt": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "author_gate_deferred": True,
        "product_answer_ready": False,
        "ordered_product_source_output_created": False,
    }
    flags["author_payload_created"] = False
    flags["author_activation_allowed"] = False
    flags["author_execution_deferred"] = True
    return flags


def _lineage(
    action: Mapping[str, Any],
    *,
    ledger: Mapping[str, Any],
    m2: Mapping[str, Any],
    n_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": action.get("run_id"),
        "checkpoint_id": action.get("checkpoint_id"),
        "evidence_ledger_projection_digest": evidence_ledger_projection_digest(ledger),
        "followup_evidence_intake_id": m2.get("followup_evidence_intake_id"),
        "followup_sufficiency_recheck_id": n_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "packet_preparation_readiness_id": action.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": action.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "final_evidence_selection_id": action.get("final_evidence_selection_id"),
        "citation_eligibility_id": action.get("citation_eligibility_id"),
        "citation_source_handoff_id": action.get("citation_source_handoff_id"),
        "citation_rendering_id": action.get("citation_rendering_id"),
        "author_input_authority_id": action.get("author_input_authority_id"),
    }


def _posture(packet: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    return {field: safe_json(packet.get(field, [])) for field in fields}


def _compact_refs(value: Any, fields: Sequence[str]) -> list[dict[str, Any]]:
    refs = []
    for item in _mappings(value):
        refs.append({field: item.get(field) for field in fields if field in item})
    return refs


def _expect(mapping: Mapping[str, Any], key: str, expected: Any) -> None:
    if mapping.get(key) != expected:
        raise PermissionError(f"U1 {key} digest/id mismatch")


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key or "").casefold()
            if key_text in {"prompt_text_included", "final_text_included"}:
                if item is not False:
                    raise PermissionError(f"U1 {key_text} must be false")
                continue
            if any(part in key_text for part in _FORBIDDEN_KEY_PARTS):
                if item in (None, False, [], {}, (), ""):
                    continue
                raise PermissionError(f"U1 payload includes closed field {key!r}")
            _reject_forbidden_payload(item)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            _reject_forbidden_payload(item)
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in ("api_key", "authorization:", "bearer ", "raw prompt", "sk-"):
            if marker in lowered:
                raise PermissionError("U1 payload includes private text marker")


def _mapping(value: Any) -> dict[str, Any]:
    safe = safe_json(value or {})
    return dict(safe) if isinstance(safe, Mapping) else {}


def _mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    return [_mapping(item) for item in value if isinstance(item, Mapping)]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        cleaned = clean_text(value)
        return [cleaned] if cleaned else []
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return []
    return [item for item in (clean_text(item) for item in value) if item]


__all__ = [
    "AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE",
    "FOLLOWUP_AUTHOR_INPUT_AUTHORITY_GATE_REASON",
    "FOLLOWUP_AUTHOR_INPUT_AUTHORITY_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE",
    "FOLLOWUP_AUTHOR_INPUT_AUTHORITY_TRACE_KEY",
    "FOLLOWUP_AUTHOR_INPUT_REFS_STATUS",
    "FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS",
    "FollowupAuthorInputAuthorityActionResult",
    "FollowupAuthorInputAuthorityRecord",
    "build_followup_author_input_authority_record",
    "execute_followup_author_input_authority_action",
    "u1_packet_projection_from_record",
    "validate_followup_author_input_authority_observation_binding",
]
