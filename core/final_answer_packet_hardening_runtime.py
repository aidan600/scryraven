"""RunKernel-owned hardened FinalAnswerPacket reducer.

AG-FINAL-ANSWER-PACKET-HARDENING-01 consumes only SufficiencyReadiness state
and projection surfaces. It creates a structured, non-executable
FinalAnswerPacket handoff for a future Author phase without creating Author
input, prose, citation eligibility/rendering, source-obligation satisfaction,
live calls, or product-correctness claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.quantitative_finalization_authority import (
    build_quantitative_finalization_authority_manifest,
)
from core.sufficiency_readiness_runtime import (
    READINESS_STATUSES,
    validate_sufficiency_readiness_state,
)

FINAL_ANSWER_PACKET_HARDENING_SCHEMA_VERSION = (
    "final_answer_packet_hardening_ag_final_answer_packet_hardening_01_v1"
)
FINAL_ANSWER_PACKET_HARDENING_ACTION_SCHEMA_VERSION = (
    "final_answer_packet_hardening_action_ag_final_answer_packet_hardening_01_v1"
)
FINAL_ANSWER_PACKET_HARDENING_OBSERVATION_SCHEMA_VERSION = (
    "final_answer_packet_hardening_observation_ag_final_answer_packet_hardening_01_v1"
)
FINAL_ANSWER_PACKET_HARDENING_STAGE = "final_answer_packet"
FINAL_ANSWER_PACKET_HARDENING_REASON = (
    "final_answer_packet_hardening_from_sufficiency_readiness"
)
FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY = "final_answer_packet"
FINAL_ANSWER_PACKET_OWNER = "RunKernel.FinalAnswerPacket"
FINAL_ANSWER_PACKET_KIND = "hardened_final_answer_packet"

READINESS_TO_FAP_STATUS = {
    "full_answer_ready": "full_answer_packet_ready",
    "partial_answer_ready": "partial_answer_packet_ready",
    "blocked": "blocked_answer_packet",
    "followup_required": "followup_required_packet",
    "contested": "contested_answer_packet",
    "insufficient_evidence": "insufficient_evidence_packet",
    "not_applicable": "not_applicable",
}
FAP_STATUSES = frozenset(READINESS_TO_FAP_STATUS.values())
PACKET_CREATED_STATUSES = FAP_STATUSES - {"not_applicable"}

_COMPONENT_STATUS_TO_FAP_STATUS = {
    "full_answer_ready": "supported_component",
    "insufficient_evidence": "insufficient_evidence_component",
    "blocked": "blocked_component",
    "contested": "contested_component",
    "followup_required": "followup_required_component",
    "not_applicable": "not_applicable_component",
}
_SAFE_SUPPORT_FAP_STATUSES = {
    "full_answer_packet_ready",
    "partial_answer_packet_ready",
}
_MODE_LABELS = {
    "fast": "Fast",
    "balanced": "Balanced",
    "deep": "Deep",
}
_CLOSED_SURFACE_FLAGS = {
    "fap_is_answer": False,
    "author_input_created": False,
    "author_payload_created": False,
    "author_input_materialized": False,
    "author_execution_allowed": False,
    "author_called": False,
    "author_observation_created": False,
    "author_output_created": False,
    "author_prompt_created": False,
    "author_prose_created": False,
    "generated_final_answer_created": False,
    "citation_eligible": False,
    "citation_eligibility_created": False,
    "citations_rendered": False,
    "citation_rendering_changed": False,
    "source_obligation_satisfied": False,
    "product_correctness_claimed": False,
    "current_answer_contract_mutated": False,
    "live_provider_called": False,
    "provider_called": False,
    "broker_called": False,
    "search_executed": False,
    "retrieval_executed": False,
    "fetch_read_executed": False,
    "model_called": False,
    "followup_authorized": False,
    "followup_search_authorized": False,
    "pipeline_orchestrator_called": False,
}
_DANGEROUS_TRUE_KEYS = frozenset(_CLOSED_SURFACE_FLAGS)
_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "body",
        "bounded_text",
        "cache",
        "cookie",
        "db",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "snippet",
        "source_text",
        "text",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_SAFE_FALSE_RAW_RETENTION_KEYS = frozenset(
    {
        "raw_content_retained",
        "raw_headers_retained",
        "raw_model_response_retained",
        "raw_page_content_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)


class FinalAnswerPacketHardeningRuntimeError(ValueError):
    """Raised when hardened FinalAnswerPacket state cannot reduce safely."""


@dataclass(frozen=True, slots=True)
class HardenedFinalAnswerPacketResult:
    """Compact result for one RunKernel-reduced hardened FAP transition."""

    fap_state: Mapping[str, Any]
    final_answer_authority_projection: Mapping[str, Any]
    authorization_action_id: str

    def to_dict(self) -> dict[str, Any]:
        projection = dict(self.final_answer_authority_projection)
        return {
            "result_kind": "hardened_final_answer_packet_result",
            "helper": "final_answer_packet_hardening_runtime",
            "authorization_action_id": self.authorization_action_id,
            "packet_created": projection.get("packet_created") is True,
            "fap_status": projection.get("fap_status"),
            "packet_ref": _packet_ref(self.fap_state),
            "final_answer_authority_projection": projection,
            **_CLOSED_SURFACE_FLAGS,
        }


def build_final_answer_packet_hardening_action_inputs(
    *,
    run_id: str,
    request_id: str,
    sufficiency_readiness_state: Mapping[str, Any],
    sufficiency_readiness_projection: Mapping[str, Any],
    sufficiency_readiness_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build action inputs binding the current SufficiencyReadiness surface."""

    clean_run_id = _required_token(run_id, "FAP hardening action requires run_id")
    clean_request_id = _required_token(
        request_id,
        "FAP hardening action requires request_id",
    )
    readiness_state = validate_sufficiency_readiness_state(
        sufficiency_readiness_state
    )
    readiness_projection = _validate_readiness_projection(
        readiness_state=readiness_state,
        readiness_projection=sufficiency_readiness_projection,
    )
    if readiness_state.get("run_id") != clean_run_id:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening action run_id binding mismatch"
        )
    if readiness_state.get("request_id") != clean_request_id:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening action request_id binding mismatch"
        )
    context_refs = _readiness_context_refs(
        readiness_state=readiness_state,
        readiness_projection=readiness_projection,
        readiness_history=sufficiency_readiness_history,
    )
    readiness_status = _readiness_status(readiness_state)
    fap_status = _fap_status(readiness_status)
    packet_created = fap_status in PACKET_CREATED_STATUSES
    return {
        "schema_version": FINAL_ANSWER_PACKET_HARDENING_ACTION_SCHEMA_VERSION,
        "owner": FINAL_ANSWER_PACKET_OWNER,
        "trace_key": FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "mode": _mode_label(readiness_state.get("mode")),
        "readiness_ref": _readiness_ref(readiness_state),
        "readiness_digest": readiness_state.get("readiness_digest"),
        "readiness_status": readiness_status,
        "fap_status": fap_status,
        "packet_created": packet_created,
        "readiness_context_digest": _digest_json(context_refs),
        "component_count": len(
            _safe_mapping(readiness_state.get("component_readiness_map"))
        ),
        "supported_component_count": len(
            _safe_list(readiness_state.get("supported_component_refs"))
        ),
        "blocked_component_count": len(
            _safe_list(readiness_state.get("blocked_component_refs"))
        ),
        "missing_component_count": len(
            _safe_list(readiness_state.get("missing_component_refs"))
        ),
        "contested_component_count": len(
            _safe_list(readiness_state.get("contested_component_refs"))
        ),
        "followup_required_component_count": len(
            _safe_list(readiness_state.get("followup_required_component_refs"))
        ),
        "hardened_fap_requested": True,
        "author_future_phase_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_final_answer_packet_hardening_observation_payload(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the observation payload that asks RunKernel to harden FAP state."""

    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != (
        FINAL_ANSWER_PACKET_HARDENING_ACTION_SCHEMA_VERSION
    ):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening action schema mismatch"
        )
    _validate_closed_flags(inputs, context="FAP hardening action inputs")
    return {
        "schema_version": FINAL_ANSWER_PACKET_HARDENING_OBSERVATION_SCHEMA_VERSION,
        "owner": FINAL_ANSWER_PACKET_OWNER,
        "trace_key": FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY,
        "authorized_action_id": _required_token(
            action_id,
            "FAP hardening observation requires action_id",
            limit=220,
        ),
        "readiness_ref": _safe_mapping(inputs.get("readiness_ref")),
        "readiness_digest": inputs.get("readiness_digest"),
        "readiness_status": inputs.get("readiness_status"),
        "fap_status": inputs.get("fap_status"),
        "packet_created": inputs.get("packet_created") is True,
        "readiness_context_digest": inputs.get("readiness_context_digest"),
        "hardened_fap_requested": True,
        "author_future_phase_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_hardened_final_answer_packet_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    sufficiency_readiness_state: Mapping[str, Any],
    sufficiency_readiness_projection: Mapping[str, Any],
    sufficiency_readiness_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate bindings and build canonical hardened FAP or no-packet state."""

    clean_action_id = _required_token(
        action_id,
        "FAP hardening reduction requires action_id",
        limit=220,
    )
    clean_run_id = _required_token(run_id, "FAP hardening reduction requires run_id")
    clean_request_id = _required_token(
        request_id,
        "FAP hardening reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != (
        FINAL_ANSWER_PACKET_HARDENING_ACTION_SCHEMA_VERSION
    ):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening action schema mismatch"
        )
    payload = _safe_mapping(observation_payload)
    if payload.get("schema_version") != (
        FINAL_ANSWER_PACKET_HARDENING_OBSERVATION_SCHEMA_VERSION
    ):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening observation schema mismatch"
        )
    if payload.get("authorized_action_id") != clean_action_id:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening observation action_id binding mismatch"
        )
    if inputs.get("run_id") != clean_run_id or inputs.get("request_id") != (
        clean_request_id
    ):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening action run/request binding mismatch"
        )
    if payload.get("hardened_fap_requested") is not True:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening observation must request hardening"
        )
    _validate_closed_flags(inputs, context="FAP hardening action inputs")
    _validate_closed_flags(payload, context="FAP hardening observation payload")

    readiness_state = validate_sufficiency_readiness_state(
        sufficiency_readiness_state
    )
    readiness_projection = _validate_readiness_projection(
        readiness_state=readiness_state,
        readiness_projection=sufficiency_readiness_projection,
    )
    if readiness_state.get("run_id") != clean_run_id:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness run_id binding mismatch"
        )
    if readiness_state.get("request_id") != clean_request_id:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness request_id binding mismatch"
        )

    readiness_status = _readiness_status(readiness_state)
    fap_status = _fap_status(readiness_status)
    readiness_digest = readiness_state.get("readiness_digest")
    context_refs = _readiness_context_refs(
        readiness_state=readiness_state,
        readiness_projection=readiness_projection,
        readiness_history=sufficiency_readiness_history,
    )
    actual_context_digest = _digest_json(context_refs)
    for source, label in ((inputs, "action"), (payload, "observation")):
        if source.get("readiness_digest") != readiness_digest:
            raise FinalAnswerPacketHardeningRuntimeError(
                f"FAP hardening {label} readiness digest is stale"
            )
        if source.get("readiness_status") != readiness_status:
            raise FinalAnswerPacketHardeningRuntimeError(
                f"FAP hardening {label} readiness status is stale"
            )
        if source.get("fap_status") != fap_status:
            raise FinalAnswerPacketHardeningRuntimeError(
                f"FAP hardening {label} FAP status is stale"
            )
        if source.get("readiness_context_digest") != actual_context_digest:
            raise FinalAnswerPacketHardeningRuntimeError(
                f"FAP hardening {label} readiness context digest is stale"
            )

    if fap_status == "not_applicable":
        return _build_no_packet_state(
            action_id=clean_action_id,
            run_id=clean_run_id,
            request_id=clean_request_id,
            readiness_state=readiness_state,
            readiness_context_digest=actual_context_digest,
        )

    component_entries = _component_packet_entries(readiness_state, fap_status)
    source_support_refs = _source_support_refs(component_entries)
    quantitative_manifest = build_quantitative_finalization_authority_manifest(
        source_fap_ref={
            "owner": FINAL_ANSWER_PACKET_OWNER,
            "run_id": clean_run_id,
            "request_id": clean_request_id,
            "readiness_digest": readiness_digest,
            "fap_status": fap_status,
        },
        component_packet_entries=component_entries,
    )
    state_base = {
        "schema_version": FINAL_ANSWER_PACKET_HARDENING_SCHEMA_VERSION,
        "record_kind": "hardened_final_answer_packet_state",
        "packet_kind": FINAL_ANSWER_PACKET_KIND,
        "trace_key": FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY,
        "owner": FINAL_ANSWER_PACKET_OWNER,
        "canonical_state": True,
        "reduced_state": True,
        "packet_created": True,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "mode": _mode_label(readiness_state.get("mode")),
        "fap_status": fap_status,
        "readiness_ref": _readiness_ref(readiness_state),
        "readiness_digest": readiness_digest,
        "readiness_context_digest": actual_context_digest,
        "current_answer_contract_ref": _safe_mapping(
            readiness_state.get("current_answer_contract_ref")
        ),
        "component_packet_entries": component_entries,
        "quantitative_finalization_authority_manifest": quantitative_manifest,
        "supported_component_refs": _safe_list(
            readiness_state.get("supported_component_refs")
        ),
        "blocked_component_refs": _safe_list(
            readiness_state.get("blocked_component_refs")
        ),
        "missing_component_refs": _safe_list(
            readiness_state.get("missing_component_refs")
        ),
        "contested_component_refs": _safe_list(
            readiness_state.get("contested_component_refs")
        ),
        "followup_required_component_refs": _safe_list(
            readiness_state.get("followup_required_component_refs")
        ),
        "scrutineer_review_refs": _safe_list(
            readiness_state.get("scrutineer_review_refs")
        ),
        "specialist_calculation_refs": _safe_list(
            readiness_state.get("specialist_calculation_refs")
        ),
        "source_support_refs": source_support_refs,
        "citation_requirements": _citation_requirements(
            component_entries=component_entries,
            source_support_refs=source_support_refs,
        ),
        "citation_posture": "requirements_preserved_eligibility_deferred",
        "source_obligation_posture": (
            "requirements_preserved_not_satisfied_by_fap"
        ),
        "mandatory_caveats": _text_list(
            readiness_state.get("mandatory_caveats"),
            limit=600,
        ),
        "prohibited_upgrades": _text_list(
            readiness_state.get("prohibited_upgrades"),
            limit=600,
        ),
        "author_handoff_constraints": _author_handoff_constraints(
            fap_status=fap_status,
            readiness_state=readiness_state,
            component_entries=component_entries,
        ),
        "author_allowed_response_posture": _author_allowed_response_posture(
            fap_status=fap_status,
            readiness_state=readiness_state,
            component_entries=component_entries,
        ),
        "author_prohibited_claims": _author_prohibited_claims(
            fap_status=fap_status,
            readiness_state=readiness_state,
            component_entries=component_entries,
        ),
        "final_answer_packet_created": True,
        "author_future_phase_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    packet_digest = _digest_json(_state_digest_payload(state_base))
    packet_id = (
        "hardened-final-answer-packet:"
        f"{clean_request_id}:{fap_status}:{packet_digest[:16]}"
    )
    state = {
        **state_base,
        "packet_id": packet_id,
        "packet_digest": packet_digest,
    }
    return validate_hardened_final_answer_packet_state(state)


def build_hardened_final_answer_packet_projection(
    *,
    fap_state: Mapping[str, Any],
    existing_final_answer_authority_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project hardened FAP state into the canonical FAP authority slot."""

    state = validate_hardened_final_answer_packet_state(fap_state)
    packet_created = state.get("packet_created") is True
    projection = {
        "owner": FINAL_ANSWER_PACKET_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY,
        "canonical_state": True,
        "reduced_state": True,
        "stage": FINAL_ANSWER_PACKET_HARDENING_STAGE,
        "packet_created": packet_created,
        "final_answer_packet_created": packet_created,
        "fap_status": state.get("fap_status"),
        "readiness_ref": _safe_mapping(state.get("readiness_ref")),
        "readiness_digest": state.get("readiness_digest"),
        "readiness_context_digest": state.get("readiness_context_digest"),
        "mode": state.get("mode"),
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "current_answer_contract_ref": _safe_mapping(
            state.get("current_answer_contract_ref")
        ),
        "component_packet_entries": _safe_list(
            state.get("component_packet_entries")
        ),
        "quantitative_finalization_authority_manifest": _safe_mapping(
            state.get("quantitative_finalization_authority_manifest")
        ),
        "supported_component_refs": _safe_list(
            state.get("supported_component_refs")
        ),
        "blocked_component_refs": _safe_list(state.get("blocked_component_refs")),
        "missing_component_refs": _safe_list(state.get("missing_component_refs")),
        "contested_component_refs": _safe_list(
            state.get("contested_component_refs")
        ),
        "followup_required_component_refs": _safe_list(
            state.get("followup_required_component_refs")
        ),
        "scrutineer_review_refs": _safe_list(
            state.get("scrutineer_review_refs")
        ),
        "specialist_calculation_refs": _safe_list(
            state.get("specialist_calculation_refs")
        ),
        "source_support_refs": _safe_list(state.get("source_support_refs")),
        "citation_requirements": _safe_mapping(state.get("citation_requirements")),
        "citation_posture": state.get("citation_posture"),
        "source_obligation_posture": state.get("source_obligation_posture"),
        "mandatory_caveats": _text_list(state.get("mandatory_caveats"), limit=600),
        "prohibited_upgrades": _text_list(
            state.get("prohibited_upgrades"),
            limit=600,
        ),
        "author_handoff_constraints": _safe_mapping(
            state.get("author_handoff_constraints")
        ),
        "author_allowed_response_posture": _safe_mapping(
            state.get("author_allowed_response_posture")
        ),
        "author_prohibited_claims": _text_list(
            state.get("author_prohibited_claims"),
            limit=600,
        ),
        "author_future_phase_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    if packet_created:
        projection.update(
            {
                "packet_id": state.get("packet_id"),
                "packet_digest": state.get("packet_digest"),
                "packet_kind": state.get("packet_kind"),
                "component_entry_count": len(
                    _safe_list(state.get("component_packet_entries"))
                ),
            }
        )
    else:
        projection.update(
            {
                "no_packet_state_kind": state.get("record_kind"),
                "no_packet_record_digest": state.get("no_packet_record_digest"),
                "component_entry_count": 0,
            }
        )
    projection["final_answer_packet_history"] = _projection_history(
        existing_final_answer_authority_projection,
        projection,
    )
    projection["final_answer_packet_count"] = len(
        projection["final_answer_packet_history"]
    )
    _validate_closed_flags(projection, context="FAP hardening projection")
    return projection


def reduce_hardened_final_answer_packet(
    *,
    run_kernel: Any,
) -> HardenedFinalAnswerPacketResult:
    """Authorize and reduce hardened FAP state through RunKernel."""

    try:
        action = run_kernel.authorize_final_answer_packet_hardening()
        from core.run_kernel import Observation, ObservationType, RunStageStatus

        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.FINAL_ANSWER_PACKET_HARDENED,
                status=RunStageStatus.COMPLETED,
                payload=build_final_answer_packet_hardening_observation_payload(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                ),
            )
        )
    except Exception as exc:  # pragma: no cover - translated for callers/tests.
        if exc.__class__.__name__ == "RunKernelTransitionError":
            raise FinalAnswerPacketHardeningRuntimeError(str(exc)) from exc
        raise
    return HardenedFinalAnswerPacketResult(
        fap_state=dict(run_kernel.state.final_answer_packet),
        final_answer_authority_projection=dict(
            run_kernel.state.final_answer_authority_projection
        ),
        authorization_action_id=action.action_id,
    )


def validate_hardened_final_answer_packet_state(
    state: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate canonical hardened FAP or not-applicable no-packet state."""

    safe = _safe_mapping(state)
    if not safe:
        raise FinalAnswerPacketHardeningRuntimeError("FAP hardening state is required")
    if safe.get("owner") != FINAL_ANSWER_PACKET_OWNER:
        raise FinalAnswerPacketHardeningRuntimeError("FAP hardening owner mismatch")
    if safe.get("schema_version") != FINAL_ANSWER_PACKET_HARDENING_SCHEMA_VERSION:
        raise FinalAnswerPacketHardeningRuntimeError("FAP hardening schema mismatch")
    if safe.get("canonical_state") is not True or safe.get("reduced_state") is not True:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening state must be canonical"
        )
    if safe.get("fap_status") not in FAP_STATUSES:
        raise FinalAnswerPacketHardeningRuntimeError("unsupported FAP status")
    _validate_closed_flags(safe, context="FAP hardening state")
    packet_created = safe.get("packet_created") is True
    if safe.get("fap_status") == "not_applicable":
        if packet_created:
            raise FinalAnswerPacketHardeningRuntimeError(
                "not_applicable FAP must not create packet"
            )
        if safe.get("packet_id") or safe.get("packet_digest"):
            raise FinalAnswerPacketHardeningRuntimeError(
                "not_applicable FAP must not carry packet identity"
            )
        declared = _required_token(
            safe.get("no_packet_record_digest"),
            "no-packet state requires digest",
            limit=128,
        )
        if declared != _digest_json(_state_digest_payload(safe)):
            raise FinalAnswerPacketHardeningRuntimeError(
                "no-packet state digest mismatch"
            )
        return safe

    if not packet_created:
        raise FinalAnswerPacketHardeningRuntimeError(
            "answer-bearing FAP status must create packet"
        )
    if safe.get("packet_kind") != FINAL_ANSWER_PACKET_KIND:
        raise FinalAnswerPacketHardeningRuntimeError("FAP packet kind mismatch")
    declared_packet_digest = _required_token(
        safe.get("packet_digest"),
        "FAP state requires packet digest",
        limit=128,
    )
    if declared_packet_digest != _digest_json(_state_digest_payload(safe)):
        raise FinalAnswerPacketHardeningRuntimeError("FAP packet digest mismatch")
    if not _clean_token(safe.get("packet_id"), limit=260):
        raise FinalAnswerPacketHardeningRuntimeError("FAP state requires packet_id")
    return safe


def _build_no_packet_state(
    *,
    action_id: str,
    run_id: str,
    request_id: str,
    readiness_state: Mapping[str, Any],
    readiness_context_digest: str,
) -> dict[str, Any]:
    state_base = {
        "schema_version": FINAL_ANSWER_PACKET_HARDENING_SCHEMA_VERSION,
        "record_kind": "hardened_final_answer_no_packet_state",
        "trace_key": FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY,
        "owner": FINAL_ANSWER_PACKET_OWNER,
        "canonical_state": True,
        "reduced_state": True,
        "packet_created": False,
        "final_answer_packet_created": False,
        "run_id": run_id,
        "request_id": request_id,
        "authorized_action_id": action_id,
        "mode": _mode_label(readiness_state.get("mode")),
        "fap_status": "not_applicable",
        "readiness_ref": _readiness_ref(readiness_state),
        "readiness_digest": readiness_state.get("readiness_digest"),
        "readiness_context_digest": readiness_context_digest,
        "current_answer_contract_ref": _safe_mapping(
            readiness_state.get("current_answer_contract_ref")
        ),
        "component_packet_entries": [],
        "supported_component_refs": [],
        "blocked_component_refs": [],
        "missing_component_refs": [],
        "contested_component_refs": [],
        "followup_required_component_refs": [],
        "scrutineer_review_refs": _safe_list(
            readiness_state.get("scrutineer_review_refs")
        ),
        "specialist_calculation_refs": _safe_list(
            readiness_state.get("specialist_calculation_refs")
        ),
        "source_support_refs": [],
        "citation_requirements": {
            "requirements_preserved": True,
            "citation_eligible": False,
            "citation_eligibility_created": False,
            "citations_rendered": False,
            "eligible_source_ids_created": False,
            "final_citation_list_created": False,
        },
        "citation_posture": "requirements_preserved_eligibility_deferred",
        "source_obligation_posture": (
            "requirements_preserved_not_satisfied_by_fap"
        ),
        "mandatory_caveats": _text_list(
            readiness_state.get("mandatory_caveats"),
            limit=600,
        ),
        "prohibited_upgrades": _dedupe_text(
            [
                *_text_list(readiness_state.get("prohibited_upgrades"), limit=600),
                "Do not create an answer packet for not_applicable readiness.",
            ]
        ),
        "author_handoff_constraints": {
            "future_author_phase_required": True,
            "author_execution_allowed": False,
            "packet_created": False,
            "allowed_scope": "no_answer_packet_not_applicable",
            "must_not_answer": True,
        },
        "author_allowed_response_posture": {
            "posture": "no_answer_packet_not_applicable",
            "packet_created": False,
            "author_execution_allowed": False,
            "supported_claims_allowed": False,
        },
        "author_prohibited_claims": [
            "Do not treat not_applicable readiness as an answer packet.",
            "Do not create Author input or final prose from this no-packet posture.",
            "Do not claim citation eligibility, source-obligation satisfaction, or product correctness.",
        ],
        "author_future_phase_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    no_packet_digest = _digest_json(_state_digest_payload(state_base))
    state = {
        **state_base,
        "no_packet_record_digest": no_packet_digest,
    }
    return validate_hardened_final_answer_packet_state(state)


def _component_packet_entries(
    readiness_state: Mapping[str, Any],
    fap_status: str,
) -> list[dict[str, Any]]:
    component_map = _safe_mapping(readiness_state.get("component_readiness_map"))
    entries = []
    for component_id in sorted(component_map):
        entry = _safe_mapping(component_map.get(component_id))
        if not entry:
            continue
        entries.append(_component_packet_entry(entry, fap_status))
    return entries


def _component_packet_entry(
    entry: Mapping[str, Any],
    fap_status: str,
) -> dict[str, Any]:
    component_status = _normalized_token(entry.get("component_readiness_status"))
    fap_component_status = _COMPONENT_STATUS_TO_FAP_STATUS.get(
        component_status,
        "insufficient_evidence_component",
    )
    caveats = _text_list(entry.get("mandatory_caveats"), limit=600)
    prohibited = _text_list(entry.get("prohibited_upgrades"), limit=600)
    treatment = _allowed_author_treatment(
        component_status=component_status,
        fap_status=fap_status,
        caveats=caveats,
    )
    followup_refs = _component_followup_refs(entry)
    source_refs = _component_source_refs(entry)
    safe_claim_text = _clean_text(entry.get("safe_answer_claim_text"), limit=1_000)
    claim_text_authority_path = _fap_claim_text_authority_path(
        entry.get("claim_text_authority_path")
    )
    supported_claim_allowed = (
        component_status == "full_answer_ready"
        and fap_status in _SAFE_SUPPORT_FAP_STATUSES
    )
    return _without_empty(
        {
            "component_id": entry.get("component_id"),
            "component_revision": entry.get("component_revision"),
            "component_digest": entry.get("component_digest"),
            "component_readiness_status": component_status,
            "fap_component_status": fap_component_status,
            "allowed_author_treatment": treatment,
            "author_treatment_constraints": _author_treatment_constraints(
                component_status=component_status,
                fap_status=fap_status,
                caveats=caveats,
            ),
            "supported_claim_allowed": supported_claim_allowed,
            "supported_safe_claim_allowed": supported_claim_allowed
            and bool(safe_claim_text),
            "safe_answer_claim_text": safe_claim_text,
            "primary_answer_value": _clean_text(
                entry.get("primary_answer_value"),
                limit=1_000,
            ),
            "selected_current_value": _clean_text(
                entry.get("selected_current_value"),
                limit=1_000,
            ),
            "claim_text_source": _clean_token(entry.get("claim_text_source")),
            "claim_text_source_ref": _clean_text(
                entry.get("claim_text_source_ref"),
                limit=260,
            ),
            "claim_text_authority_path": claim_text_authority_path,
            "bound_contract_component_id": _clean_token(
                entry.get("bound_contract_component_id"),
                limit=260,
            ),
            "bound_contract_source_obligation_id": _clean_token(
                entry.get("bound_contract_source_obligation_id"),
                limit=260,
            ),
            "source_obligation_candidate_ids": _text_list(
                entry.get("source_obligation_candidate_ids"),
                limit=260,
            ),
            "semantic_observation_ref": _safe_mapping(
                entry.get("semantic_observation_ref")
            ),
            "component_coverage_ref": _safe_mapping(
                entry.get("component_coverage_ref")
            ),
            "fap_safe_claim_ref": _fap_safe_claim_ref(
                entry=entry,
                fap_status=fap_status,
                safe_claim_text=safe_claim_text,
                claim_text_authority_path=claim_text_authority_path,
            ),
            "must_not_answer": not supported_claim_allowed,
            "supporting_coverage_refs": _safe_list(entry.get("coverage_refs")),
            "semantic_observation_refs": _safe_list(
                entry.get("semantic_observation_refs")
            ),
            "safe_source_content_refs": source_refs,
            "scrutineer_refs": _safe_list(entry.get("scrutineer_refs")),
            "specialist_refs": _safe_list(entry.get("specialist_calculation_refs")),
            "followup_refs": followup_refs,
            "blockers": _text_list(entry.get("blockers"), limit=600),
            "caveats": caveats,
            "mandatory_caveats": caveats,
            "prohibited_upgrades": prohibited,
            "citation_eligible": False,
            "citation_eligibility_created": False,
            "source_obligation_satisfied": False,
            "product_correctness_claimed": False,
        }
    )


def _fap_safe_claim_ref(
    *,
    entry: Mapping[str, Any],
    fap_status: str,
    safe_claim_text: str | None,
    claim_text_authority_path: str | None,
) -> dict[str, Any]:
    if not safe_claim_text:
        return {}
    return _without_empty(
        {
            "fap_status": fap_status,
            "component_id": entry.get("component_id"),
            "safe_answer_claim_text": safe_claim_text,
            "claim_text_source": entry.get("claim_text_source"),
            "claim_text_source_ref": entry.get("claim_text_source_ref"),
            "claim_text_authority_path": claim_text_authority_path,
            "bound_contract_component_id": entry.get(
                "bound_contract_component_id"
            ),
            "bound_contract_source_obligation_id": entry.get(
                "bound_contract_source_obligation_id"
            ),
            "semantic_observation_ref": _safe_mapping(
                entry.get("semantic_observation_ref")
            ),
            "component_coverage_ref": _safe_mapping(
                entry.get("component_coverage_ref")
            ),
        }
    )


def _fap_claim_text_authority_path(value: Any) -> str | None:
    path = _clean_text(value, limit=400)
    if not path:
        return None
    if "FAP" in path:
        return path
    return f"{path} -> FAP safe claim text"


def _allowed_author_treatment(
    *,
    component_status: str,
    fap_status: str,
    caveats: Sequence[str],
) -> str:
    if (
        component_status == "full_answer_ready"
        and fap_status in _SAFE_SUPPORT_FAP_STATUSES
    ):
        return "may_state_with_caveat" if caveats else "may_state_as_supported"
    if component_status == "contested":
        return "must_state_as_contested"
    if fap_status == "insufficient_evidence_packet":
        return "must_not_answer"
    if component_status in {"blocked", "insufficient_evidence", "followup_required"}:
        return "must_state_as_unresolved"
    return "must_not_answer"


def _author_treatment_constraints(
    *,
    component_status: str,
    fap_status: str,
    caveats: Sequence[str],
) -> list[str]:
    constraints: list[str] = []
    if (
        component_status == "full_answer_ready"
        and fap_status in _SAFE_SUPPORT_FAP_STATUSES
    ):
        constraints.append("may_state_as_supported")
        if caveats:
            constraints.append("must_preserve_caveats")
    elif component_status == "contested":
        constraints.extend(["must_state_as_contested", "must_not_present_as_fact"])
    elif component_status == "followup_required":
        constraints.extend(
            [
                "must_state_remediation_required",
                "must_not_authorize_followup",
                "must_not_answer_unsupported_component",
            ]
        )
    elif component_status == "blocked":
        constraints.extend(
            ["must_state_as_unresolved", "must_not_answer_unsupported_component"]
        )
    else:
        constraints.extend(["must_not_answer", "must_state_insufficient_evidence"])
    if fap_status == "partial_answer_packet_ready":
        constraints.append("must_not_imply_full_answer")
    if fap_status == "insufficient_evidence_packet":
        constraints.append("no_supported_claims_allowed")
    return _dedupe_text(constraints)


def _component_source_refs(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    component_id = entry.get("component_id")
    for coverage in _safe_list(entry.get("coverage_refs")):
        coverage_ref = _safe_mapping(coverage)
        if not coverage_ref:
            continue
        for binding in _safe_list(coverage_ref.get("content_reference_bindings")):
            content = _safe_mapping(binding)
            refs.append(
                _without_empty(
                    {
                        "component_id": component_id,
                        "coverage_record_id": coverage_ref.get("coverage_record_id"),
                        "coverage_record_digest": coverage_ref.get(
                            "coverage_record_digest"
                        ),
                        "content_ref_id": content.get("content_ref_id"),
                        "content_digest": content.get("content_digest"),
                        "evidence_ref_id": content.get("evidence_ref_id"),
                        "availability_status": content.get("availability_status"),
                        "citation_eligible": False,
                        "source_obligation_satisfied": False,
                    }
                )
            )
        for observation in _safe_list(coverage_ref.get("accepted_observation_refs")):
            obs = _safe_mapping(observation)
            refs.append(
                _without_empty(
                    {
                        "component_id": component_id,
                        "coverage_record_id": coverage_ref.get("coverage_record_id"),
                        "coverage_record_digest": coverage_ref.get(
                            "coverage_record_digest"
                        ),
                        "observation_id": obs.get("observation_id"),
                        "observation_digest": obs.get("observation_digest"),
                        "support_status": obs.get("support_status"),
                        "content_refs": _text_list(obs.get("content_refs"), limit=260),
                        "citation_eligible": False,
                        "source_obligation_satisfied": False,
                    }
                )
            )
    for observation in _safe_list(entry.get("semantic_observation_refs")):
        obs = _safe_mapping(observation)
        refs.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "observation_id": obs.get("observation_id"),
                    "observation_digest": obs.get("observation_digest"),
                    "support_status": obs.get("support_status"),
                    "content_refs": _text_list(obs.get("content_refs"), limit=260),
                    "evidence_refs": _text_list(obs.get("evidence_refs"), limit=260),
                    "citation_eligible": False,
                    "source_obligation_satisfied": False,
                }
            )
        )
    return _dedupe_refs(refs)


def _component_followup_refs(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for ref in _safe_list(entry.get("scrutineer_refs")):
        mapped = _safe_mapping(ref)
        if mapped.get("review_outcome") == "remediation_required":
            refs.append(
                _without_empty(
                    {
                        "component_id": entry.get("component_id"),
                        "review_id": mapped.get("review_id"),
                        "review_digest": mapped.get("review_digest"),
                        "followup_authorized_by_fap": False,
                    }
                )
            )
    if _normalized_token(entry.get("component_readiness_status")) == (
        "followup_required"
    ):
        refs.append(
            _without_empty(
                {
                    "component_id": entry.get("component_id"),
                    "followup_budget_posture": entry.get("followup_budget_posture"),
                    "followup_authorized_by_fap": False,
                }
            )
        )
    return _dedupe_refs(refs)


def _source_support_refs(
    component_entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in component_entries:
        component_id = component.get("component_id")
        for ref in _safe_list(component.get("safe_source_content_refs")):
            mapped = _safe_mapping(ref)
            if not mapped:
                continue
            refs.append(
                _without_empty(
                    {
                        **mapped,
                        "component_id": component_id,
                        "citation_eligible": False,
                        "source_obligation_satisfied": False,
                    }
                )
            )
    return _dedupe_refs(refs)


def _citation_requirements(
    *,
    component_entries: Sequence[Mapping[str, Any]],
    source_support_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "requirements_preserved": True,
        "component_count": len(component_entries),
        "source_support_ref_count": len(source_support_refs),
        "citation_eligible": False,
        "citation_eligibility_created": False,
        "citations_rendered": False,
        "eligible_source_ids_created": False,
        "final_citation_list_created": False,
        "future_author_or_citation_phase_required": True,
    }


def _author_handoff_constraints(
    *,
    fap_status: str,
    readiness_state: Mapping[str, Any],
    component_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    constraints = {
        "future_author_phase_required": True,
        "author_execution_allowed": False,
        "author_input_materialized": False,
        "author_payload_created": False,
        "must_preserve_fap_status": fap_status,
        "must_preserve_readiness_status": readiness_state.get(
            "final_readiness_status"
        ),
        "must_preserve_readiness_digest": readiness_state.get("readiness_digest"),
        "must_preserve_caveats": True,
        "must_preserve_prohibited_upgrades": True,
        "must_not_render_citations_from_fap": True,
        "must_not_satisfy_source_obligations_from_fap": True,
        "must_not_claim_product_correctness": True,
        "supported_component_ids": [
            item.get("component_id")
            for item in component_entries
            if item.get("supported_claim_allowed") is True
        ],
        "unsupported_component_ids": [
            item.get("component_id")
            for item in component_entries
            if item.get("supported_claim_allowed") is not True
        ],
    }
    if fap_status == "full_answer_packet_ready":
        constraints["allowed_scope"] = "full_answer_posture_preserving_caveats"
    elif fap_status == "partial_answer_packet_ready":
        constraints["allowed_scope"] = "partial_answer_only"
        constraints["must_not_imply_full_answer"] = True
    elif fap_status == "blocked_answer_packet":
        constraints["allowed_scope"] = "blocker_explanation_only"
        constraints["must_not_answer_unsupported_components"] = True
    elif fap_status == "followup_required_packet":
        constraints["allowed_scope"] = "remediation_required_explanation_only"
        constraints["followup_authorized_by_fap"] = False
        constraints["must_not_authorize_followup"] = True
    elif fap_status == "contested_answer_packet":
        constraints["allowed_scope"] = "contested_posture_only"
        constraints["must_not_smooth_disagreement_into_fact"] = True
    elif fap_status == "insufficient_evidence_packet":
        constraints["allowed_scope"] = "insufficient_evidence_explanation_only"
        constraints["supported_claims_allowed"] = False
    return constraints


def _author_allowed_response_posture(
    *,
    fap_status: str,
    readiness_state: Mapping[str, Any],
    component_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    posture_by_status = {
        "full_answer_packet_ready": "future_full_answer_allowed_with_constraints",
        "partial_answer_packet_ready": "future_partial_answer_only",
        "blocked_answer_packet": "future_blocker_explanation_only",
        "followup_required_packet": "future_remediation_required_explanation_only",
        "contested_answer_packet": "future_contested_explanation_only",
        "insufficient_evidence_packet": "future_insufficient_evidence_explanation_only",
        "not_applicable": "no_answer_packet_not_applicable",
    }
    supported = [
        item.get("component_id")
        for item in component_entries
        if item.get("supported_claim_allowed") is True
    ]
    unresolved = [
        item.get("component_id")
        for item in component_entries
        if item.get("supported_claim_allowed") is not True
    ]
    return {
        "posture": posture_by_status.get(fap_status, "future_unresolved_only"),
        "readiness_status": readiness_state.get("final_readiness_status"),
        "supported_component_ids": supported,
        "unresolved_component_ids": unresolved,
        "full_answer_implication_allowed": fap_status == "full_answer_packet_ready",
        "supported_claims_allowed": bool(supported)
        and fap_status in _SAFE_SUPPORT_FAP_STATUSES,
        "author_execution_allowed": False,
        "author_input_created": False,
    }


def _author_prohibited_claims(
    *,
    fap_status: str,
    readiness_state: Mapping[str, Any],
    component_entries: Sequence[Mapping[str, Any]],
) -> list[str]:
    claims = [
        "Do not treat this FinalAnswerPacket as final prose.",
        "Do not claim product correctness from FAP hardening.",
        "Do not render citations or create citation eligibility from this FAP.",
        "Do not claim source obligations are satisfied by this FAP.",
        "Do not create executable Author input or Author payload.",
        *_text_list(readiness_state.get("prohibited_upgrades"), limit=600),
    ]
    if fap_status == "partial_answer_packet_ready":
        claims.append("Do not imply full-answer readiness.")
    elif fap_status == "blocked_answer_packet":
        claims.append("Do not answer blocked or unsupported components.")
    elif fap_status == "followup_required_packet":
        claims.append("Do not authorize follow-up or imply remediation completed.")
    elif fap_status == "contested_answer_packet":
        claims.append("Do not smooth contested disagreement into fact.")
    elif fap_status == "insufficient_evidence_packet":
        claims.append("Do not present unsupported claims as supported.")
    for component in component_entries:
        for upgrade in _text_list(component.get("prohibited_upgrades"), limit=600):
            claims.append(upgrade)
    return _dedupe_text(claims)


def _projection_history(
    existing_projection: Mapping[str, Any] | None,
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    existing = _safe_mapping(existing_projection)
    history = [
        _safe_mapping(item)
        for item in _safe_list(existing.get("final_answer_packet_history"))
    ]
    entry = {
        "packet_created": projection.get("packet_created") is True,
        "fap_status": projection.get("fap_status"),
        "readiness_digest": projection.get("readiness_digest"),
        "authorized_action_id": projection.get("authorized_action_id"),
    }
    if projection.get("packet_created") is True:
        entry["packet_id"] = projection.get("packet_id")
        entry["packet_digest"] = projection.get("packet_digest")
    else:
        entry["no_packet_record_digest"] = projection.get("no_packet_record_digest")
    history.append(_without_empty(entry))
    return history


def _validate_readiness_projection(
    *,
    readiness_state: Mapping[str, Any],
    readiness_projection: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _safe_mapping(readiness_projection)
    if not projection:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening requires sufficiency_readiness_projection"
        )
    if projection.get("owner") != "RunKernel.SufficiencyReadiness":
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness projection owner mismatch"
        )
    if projection.get("readiness_digest") != readiness_state.get("readiness_digest"):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness projection digest mismatch"
        )
    if projection.get("final_readiness_status") != (
        readiness_state.get("final_readiness_status")
    ):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness projection status mismatch"
        )
    if projection.get("run_id") != readiness_state.get("run_id"):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness projection run_id mismatch"
        )
    if projection.get("request_id") != readiness_state.get("request_id"):
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening readiness projection request_id mismatch"
        )
    return projection


def _readiness_context_refs(
    *,
    readiness_state: Mapping[str, Any],
    readiness_projection: Mapping[str, Any],
    readiness_history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    history_refs = []
    for item in _safe_list(readiness_history):
        mapped = _safe_mapping(item)
        if mapped:
            history_refs.append(
                _without_empty(
                    {
                        "readiness_id": mapped.get("readiness_id"),
                        "readiness_digest": mapped.get("readiness_digest"),
                        "final_readiness_status": mapped.get(
                            "final_readiness_status"
                        ),
                        "mode": mapped.get("mode"),
                    }
                )
            )
    return {
        "readiness_ref": _readiness_ref(readiness_state),
        "readiness_projection_digest": _digest_json(readiness_projection),
        "readiness_history_refs": history_refs,
        "readiness_history_count": len(history_refs),
    }


def _readiness_ref(state: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "readiness_id": state.get("readiness_id"),
            "readiness_digest": state.get("readiness_digest"),
            "final_readiness_status": state.get("final_readiness_status"),
            "mode": state.get("mode"),
        }
    )


def _readiness_status(state: Mapping[str, Any]) -> str:
    status = _normalized_token(state.get("final_readiness_status"))
    if status not in READINESS_STATUSES:
        raise FinalAnswerPacketHardeningRuntimeError(
            "unsupported SufficiencyReadiness status"
        )
    return status


def _fap_status(readiness_status: str) -> str:
    status = READINESS_TO_FAP_STATUS.get(readiness_status)
    if status not in FAP_STATUSES:
        raise FinalAnswerPacketHardeningRuntimeError(
            "unsupported FAP status mapping"
        )
    return status


def _packet_ref(state: Mapping[str, Any]) -> dict[str, Any]:
    mapped = _safe_mapping(state)
    if mapped.get("packet_created") is not True:
        return {
            "packet_created": False,
            "fap_status": mapped.get("fap_status"),
            "no_packet_record_digest": mapped.get("no_packet_record_digest"),
        }
    return _without_empty(
        {
            "packet_created": True,
            "packet_id": mapped.get("packet_id"),
            "packet_digest": mapped.get("packet_digest"),
            "fap_status": mapped.get("fap_status"),
        }
    )


def _state_digest_payload(state: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(state)
    for key in (
        "packet_id",
        "packet_digest",
        "no_packet_record_digest",
        "final_answer_packet_history",
        "final_answer_packet_count",
    ):
        payload.pop(key, None)
    return payload


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if value.get(key) is not expected:
            raise FinalAnswerPacketHardeningRuntimeError(
                f"{context} must keep {key}=False"
            )
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if flags.get(key) is not expected:
            raise FinalAnswerPacketHardeningRuntimeError(
                f"{context} closed_surface_flags must keep {key}=False"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise FinalAnswerPacketHardeningRuntimeError(
            f"{context} opens closed surfaces: " + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=1_000)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=140)
            if not clean_key:
                continue
            if _is_raw_or_private_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, (tuple, list, set, frozenset)):
        items = list(value)
        if isinstance(value, (set, frozenset)):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _is_raw_or_private_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RAW_RETENTION_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _RAW_OR_PRIVATE_KEYS


def _dedupe_refs(refs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        mapped = _safe_mapping(ref)
        key = (
            _clean_token(mapped.get("content_digest"), limit=128)
            or _clean_token(mapped.get("observation_digest"), limit=128)
            or _clean_token(mapped.get("coverage_record_digest"), limit=128)
            or _digest_json(mapped)
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(mapped)
    return out


def _dedupe_text(values: Sequence[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_text(item, limit=600)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if isinstance(value, str):
        text = _clean_token(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_token(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise FinalAnswerPacketHardeningRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalized_token(value: Any) -> str:
    text = _clean_token(value, limit=180) or ""
    return text.casefold().replace("-", "_").replace(" ", "_")


def _mode_label(mode: Any) -> str:
    label = _MODE_LABELS.get(str(_clean_token(mode, limit=40) or "").casefold())
    if not label:
        raise FinalAnswerPacketHardeningRuntimeError(
            "FAP hardening mode must be Fast, Balanced, or Deep"
        )
    return label


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "FINAL_ANSWER_PACKET_HARDENING_ACTION_SCHEMA_VERSION",
    "FINAL_ANSWER_PACKET_HARDENING_OBSERVATION_SCHEMA_VERSION",
    "FINAL_ANSWER_PACKET_HARDENING_REASON",
    "FINAL_ANSWER_PACKET_HARDENING_SCHEMA_VERSION",
    "FINAL_ANSWER_PACKET_HARDENING_STAGE",
    "FINAL_ANSWER_PACKET_HARDENING_TRACE_KEY",
    "FINAL_ANSWER_PACKET_KIND",
    "FINAL_ANSWER_PACKET_OWNER",
    "FAP_STATUSES",
    "HardenedFinalAnswerPacketResult",
    "FinalAnswerPacketHardeningRuntimeError",
    "PACKET_CREATED_STATUSES",
    "READINESS_TO_FAP_STATUS",
    "build_final_answer_packet_hardening_action_inputs",
    "build_final_answer_packet_hardening_observation_payload",
    "build_hardened_final_answer_packet_projection",
    "build_hardened_final_answer_packet_state",
    "reduce_hardened_final_answer_packet",
    "validate_hardened_final_answer_packet_state",
]
