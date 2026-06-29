"""RunKernel-owned pre-FAP sufficiency readiness reducer.

This module deterministically reduces current contract, ComponentCoverage,
SemanticObservation admission, ScrutineerReview, Specialist calculation, and
follow-up authorization posture into readiness state. It records readiness
posture only. It does not create a FinalAnswerPacket, create Author input,
produce prose, satisfy source obligations, mark citation eligibility, mutate the
current answer contract, call providers/brokers/retrieval/models, or claim
product correctness.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

SUFFICIENCY_READINESS_SCHEMA_VERSION = (
    "sufficiency_readiness_ag_sufficiency_partial_answer_readiness_01_v1"
)
SUFFICIENCY_READINESS_ACTION_SCHEMA_VERSION = (
    "sufficiency_readiness_action_ag_sufficiency_partial_answer_readiness_01_v1"
)
SUFFICIENCY_READINESS_OBSERVATION_SCHEMA_VERSION = (
    "sufficiency_readiness_observation_ag_sufficiency_partial_answer_readiness_01_v1"
)
SUFFICIENCY_READINESS_STAGE = "sufficiency_readiness"
SUFFICIENCY_READINESS_REASON = "sufficiency_readiness_from_runkernel_reducer"
SUFFICIENCY_READINESS_TRACE_KEY = "sufficiency_readiness"
SUFFICIENCY_READINESS_OWNER = "RunKernel.SufficiencyReadiness"
SUFFICIENCY_READINESS_HELPER = (
    "sufficiency_readiness_runtime_ag_sufficiency_partial_answer_readiness_01"
)

READINESS_STATUSES = frozenset(
    {
        "full_answer_ready",
        "partial_answer_ready",
        "blocked",
        "followup_required",
        "contested",
        "insufficient_evidence",
        "not_applicable",
    }
)
_MODE_LABELS = {
    "fast": "Fast",
    "balanced": "Balanced",
    "deep": "Deep",
}
_READY_COVERAGE_STATES = frozenset({"satisfied", "supported_with_caveats"})
_BAD_COVERAGE_STATES = frozenset(
    {
        "blocked",
        "conflicted",
        "stale",
        "unassessed",
        "unsupported",
    }
)
_BAD_CURRENTNESS = frozenset(
    {
        "currentness_unknown",
        "historical_only",
        "not_current",
        "outdated",
        "stale",
        "stale_or_unknown",
        "unknown_material",
    }
)
_CONTESTED_CONFLICT = frozenset(
    {
        "conflicted",
        "contradiction",
        "present",
        "unresolved",
    }
)
_FOLLOWUP_REQUIRED = frozenset(
    {
        "available_required",
        "mandatory",
        "needed",
        "required",
    }
)
_FOLLOWUP_EXHAUSTED = frozenset(
    {
        "budget_exhausted",
        "exhausted",
        "failed",
        "unavailable",
    }
)
_CLOSED_SURFACE_FLAGS = {
    "live_provider_called": False,
    "provider_called": False,
    "broker_called": False,
    "retrieval_executed": False,
    "fetch_read_executed": False,
    "live_fetch_read_executed": False,
    "model_called": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "author_called": False,
    "citation_eligible": False,
    "citation_created": False,
    "source_obligation_satisfied": False,
    "product_correctness_claimed": False,
    "current_answer_contract_mutated": False,
    "provider_routing_changed": False,
    "provider_depth_changed": False,
    "prompt_behavior_changed": False,
}
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
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_SURFACE_FLAGS,
        "author_input_ready",
        "citation_rendered",
        "content_citation_eligible",
        "final_answer_packet_ready",
        "final_evidence_eligible",
        "product_answer_behavior_changed",
        "source_obligation_support_created",
    }
)


class SufficiencyReadinessRuntimeError(ValueError):
    """Raised when readiness state cannot be reduced safely."""


@dataclass(frozen=True, slots=True)
class SufficiencyReadinessResult:
    """Compact result for one RunKernel-reduced readiness decision."""

    readiness_state: Mapping[str, Any]
    readiness_projection: Mapping[str, Any]
    authorization_action_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_kind": "sufficiency_readiness_result",
            "durable_packet": False,
            "helper": SUFFICIENCY_READINESS_HELPER,
            "authorization_action_id": self.authorization_action_id,
            "readiness_ref": readiness_ref_from_state(self.readiness_state),
            "readiness_projection": dict(self.readiness_projection),
            "final_answer_packet_created": False,
            "author_input_created": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "product_correctness_claimed": False,
        }


def build_sufficiency_readiness_action_inputs(
    *,
    run_id: str,
    request_id: str,
    mode: str,
    current_answer_contract: Mapping[str, Any] | None = None,
    component_coverage_projection: Mapping[str, Any] | None = None,
    component_coverage_history: Sequence[Mapping[str, Any]] = (),
    semantic_observation_admission_projection: Mapping[str, Any] | None = None,
    semantic_observation_admission_history: Sequence[Mapping[str, Any]] = (),
    scrutineer_review_projection: Mapping[str, Any] | None = None,
    scrutineer_review_history: Sequence[Mapping[str, Any]] = (),
    specialist_source_bound_calculation_projection: Mapping[str, Any] | None = None,
    specialist_source_bound_calculation_history: Sequence[Mapping[str, Any]] = (),
    followup_search_authorization_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build action inputs that bind the current readiness input context."""

    clean_run_id = _required_token(run_id, "readiness action requires run_id")
    clean_request_id = _required_token(
        request_id,
        "readiness action requires request_id",
    )
    mode_label = _mode_label(mode)
    context_refs = _context_refs(
        current_answer_contract=current_answer_contract,
        component_coverage_projection=component_coverage_projection,
        component_coverage_history=component_coverage_history,
        semantic_observation_admission_projection=(
            semantic_observation_admission_projection
        ),
        semantic_observation_admission_history=(
            semantic_observation_admission_history
        ),
        scrutineer_review_projection=scrutineer_review_projection,
        scrutineer_review_history=scrutineer_review_history,
        specialist_source_bound_calculation_projection=(
            specialist_source_bound_calculation_projection
        ),
        specialist_source_bound_calculation_history=(
            specialist_source_bound_calculation_history
        ),
        followup_search_authorization_projection=(
            followup_search_authorization_projection
        ),
    )
    return {
        "schema_version": SUFFICIENCY_READINESS_ACTION_SCHEMA_VERSION,
        "owner": SUFFICIENCY_READINESS_OWNER,
        "trace_key": SUFFICIENCY_READINESS_TRACE_KEY,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "mode": mode_label,
        "current_answer_contract_ref": _safe_mapping(
            context_refs.get("current_answer_contract_ref")
        ),
        "contract_available": bool(
            _safe_mapping(context_refs.get("current_answer_contract_ref"))
        ),
        "component_count": len(context_refs.get("component_refs") or []),
        "coverage_ref_count": len(context_refs.get("component_coverage_refs") or []),
        "semantic_observation_ref_count": len(
            context_refs.get("semantic_observation_refs") or []
        ),
        "scrutineer_review_ref_count": len(
            context_refs.get("scrutineer_review_refs") or []
        ),
        "specialist_calculation_ref_count": len(
            context_refs.get("specialist_calculation_refs") or []
        ),
        "followup_budget_posture": _followup_budget_posture(
            mode_label,
            followup_search_authorization_projection,
        ),
        "readiness_input_digest": _digest_json(context_refs),
        "readiness_only": True,
        "sufficiency_readiness_is_product_authority": False,
        "creates_final_answer_packet": False,
        "creates_author_input": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_sufficiency_readiness_observation_payload(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the small observation that asks RunKernel to reduce readiness."""

    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != SUFFICIENCY_READINESS_ACTION_SCHEMA_VERSION:
        raise SufficiencyReadinessRuntimeError("readiness action schema mismatch")
    _validate_closed_flags(inputs, context="readiness action inputs")
    return {
        "schema_version": SUFFICIENCY_READINESS_OBSERVATION_SCHEMA_VERSION,
        "owner": SUFFICIENCY_READINESS_OWNER,
        "trace_key": SUFFICIENCY_READINESS_TRACE_KEY,
        "authorized_action_id": _required_token(
            action_id,
            "readiness observation requires action_id",
            limit=200,
        ),
        "readiness_input_digest": inputs.get("readiness_input_digest"),
        "readiness_requested": True,
        "readiness_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_sufficiency_readiness_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    current_answer_contract: Mapping[str, Any] | None = None,
    component_coverage_projection: Mapping[str, Any] | None = None,
    component_coverage_history: Sequence[Mapping[str, Any]] = (),
    semantic_observation_admission_projection: Mapping[str, Any] | None = None,
    semantic_observation_admission_history: Sequence[Mapping[str, Any]] = (),
    scrutineer_review_projection: Mapping[str, Any] | None = None,
    scrutineer_review_history: Sequence[Mapping[str, Any]] = (),
    specialist_source_bound_calculation_projection: Mapping[str, Any] | None = None,
    specialist_source_bound_calculation_history: Sequence[Mapping[str, Any]] = (),
    followup_search_authorization_projection: Mapping[str, Any] | None = None,
    existing_readiness_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the reducer observation and build canonical readiness state."""

    clean_action_id = _required_token(
        action_id,
        "readiness reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(run_id, "readiness reduction requires run_id")
    clean_request_id = _required_token(
        request_id,
        "readiness reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != SUFFICIENCY_READINESS_ACTION_SCHEMA_VERSION:
        raise SufficiencyReadinessRuntimeError("readiness action schema mismatch")
    payload = _safe_mapping(observation_payload)
    if payload.get("schema_version") != SUFFICIENCY_READINESS_OBSERVATION_SCHEMA_VERSION:
        raise SufficiencyReadinessRuntimeError(
            "readiness observation schema mismatch"
        )
    if payload.get("authorized_action_id") != clean_action_id:
        raise SufficiencyReadinessRuntimeError(
            "readiness observation action_id binding mismatch"
        )
    if inputs.get("run_id") != clean_run_id or inputs.get("request_id") != clean_request_id:
        raise SufficiencyReadinessRuntimeError(
            "readiness action run/request binding mismatch"
        )
    if payload.get("readiness_requested") is not True:
        raise SufficiencyReadinessRuntimeError("readiness observation must request readiness")
    _validate_closed_flags(inputs, context="readiness action inputs")
    _validate_closed_flags(payload, context="readiness observation payload")

    mode_label = _mode_label(inputs.get("mode"))
    context_refs = _context_refs(
        current_answer_contract=current_answer_contract,
        component_coverage_projection=component_coverage_projection,
        component_coverage_history=component_coverage_history,
        semantic_observation_admission_projection=(
            semantic_observation_admission_projection
        ),
        semantic_observation_admission_history=(
            semantic_observation_admission_history
        ),
        scrutineer_review_projection=scrutineer_review_projection,
        scrutineer_review_history=scrutineer_review_history,
        specialist_source_bound_calculation_projection=(
            specialist_source_bound_calculation_projection
        ),
        specialist_source_bound_calculation_history=(
            specialist_source_bound_calculation_history
        ),
        followup_search_authorization_projection=(
            followup_search_authorization_projection
        ),
    )
    actual_input_digest = _digest_json(context_refs)
    if inputs.get("readiness_input_digest") != actual_input_digest:
        raise SufficiencyReadinessRuntimeError(
            "readiness action input digest is stale"
        )
    if payload.get("readiness_input_digest") != actual_input_digest:
        raise SufficiencyReadinessRuntimeError(
            "readiness observation input digest is stale"
        )

    contract = _safe_mapping(current_answer_contract)
    component_refs = _contract_components(contract)
    followup_budget_posture = _followup_budget_posture(
        mode_label,
        followup_search_authorization_projection,
    )
    coverage_refs = _coverage_refs(
        component_coverage_projection,
        component_coverage_history,
    )
    admission_refs = _admission_refs(
        semantic_observation_admission_projection,
        semantic_observation_admission_history,
    )
    scrutineer_refs = _scrutineer_review_refs(
        scrutineer_review_projection,
        scrutineer_review_history,
    )
    specialist_refs = _specialist_calculation_refs(
        specialist_source_bound_calculation_projection,
        specialist_source_bound_calculation_history,
    )
    latest_review = scrutineer_refs[-1] if scrutineer_refs else {}

    component_map: dict[str, dict[str, Any]] = {}
    if component_refs:
        coverage_by_component = _coverage_by_component(coverage_refs, component_refs)
        admission_by_component = _refs_by_component(
            admission_refs,
            component_key="answer_component_id",
        )
        specialist_by_component = _refs_by_component(
            specialist_refs,
            component_key="component_id",
        )
        for component in component_refs:
            component_id = str(component["component_id"])
            component_map[component_id] = _component_readiness_entry(
                component=component,
                coverage_refs=coverage_by_component.get(component_id, []),
                admission_refs=admission_by_component.get(component_id, []),
                scrutineer_refs=scrutineer_refs,
                latest_review=latest_review,
                specialist_refs=specialist_by_component.get(component_id, []),
                followup_budget_posture=followup_budget_posture,
            )

    aggregate = _aggregate_answer_readiness(
        mode=mode_label,
        contract=contract,
        component_map=component_map,
        latest_review=latest_review,
        scrutineer_refs=scrutineer_refs,
        followup_budget_posture=followup_budget_posture,
    )
    state_base = {
        "schema_version": SUFFICIENCY_READINESS_SCHEMA_VERSION,
        "record_kind": "sufficiency_readiness_state",
        "trace_key": SUFFICIENCY_READINESS_TRACE_KEY,
        "owner": SUFFICIENCY_READINESS_OWNER,
        "helper": SUFFICIENCY_READINESS_HELPER,
        "canonical_state": True,
        "reduced_state": True,
        "proposal_packet": False,
        "durable_packet": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "mode": mode_label,
        "current_answer_contract_ref": _contract_ref(contract),
        "readiness_input_digest": actual_input_digest,
        "final_readiness_status": aggregate["final_readiness_status"],
        "component_readiness_map": component_map,
        "supported_component_refs": aggregate["supported_component_refs"],
        "missing_component_refs": aggregate["missing_component_refs"],
        "blocked_component_refs": aggregate["blocked_component_refs"],
        "contested_component_refs": aggregate["contested_component_refs"],
        "followup_required_component_refs": (
            aggregate["followup_required_component_refs"]
        ),
        "scrutineer_review_refs": scrutineer_refs,
        "specialist_calculation_refs": specialist_refs,
        "followup_budget_posture": followup_budget_posture,
        "mandatory_caveats": aggregate["mandatory_caveats"],
        "prohibited_upgrades": aggregate["prohibited_upgrades"],
        "fap_handoff_preview": _fap_handoff_preview(aggregate, component_map),
        "sufficiency_readiness_is_product_authority": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "product_correctness_claimed": False,
        "current_answer_contract_mutated": False,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
        **_CLOSED_SURFACE_FLAGS,
    }
    readiness_digest = _digest_json(_state_digest_payload(state_base))
    readiness_id = (
        "sufficiency-readiness:"
        f"{clean_request_id}:{aggregate['final_readiness_status']}:"
        f"{readiness_digest[:16]}"
    )
    history = _readiness_history(
        existing_readiness_projection,
        readiness_id=readiness_id,
        readiness_digest=readiness_digest,
        action_id=clean_action_id,
        mode=mode_label,
        status=aggregate["final_readiness_status"],
    )
    state = {
        **state_base,
        "readiness_id": readiness_id,
        "readiness_digest": readiness_digest,
        "readiness_history": history,
        "readiness_count": len(history),
    }
    return validate_sufficiency_readiness_state(state)


def build_sufficiency_readiness_projection(
    *,
    readiness_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical readiness state with only safe refs and caveats."""

    state = validate_sufficiency_readiness_state(readiness_state)
    return {
        "owner": SUFFICIENCY_READINESS_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SUFFICIENCY_READINESS_TRACE_KEY,
        "canonical_state": True,
        "reduced_state": True,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "readiness_id": state.get("readiness_id"),
        "readiness_digest": state.get("readiness_digest"),
        "mode": state.get("mode"),
        "current_answer_contract_ref": _safe_mapping(
            state.get("current_answer_contract_ref")
        ),
        "final_readiness_status": state.get("final_readiness_status"),
        "component_readiness_map": _safe_mapping(
            state.get("component_readiness_map")
        ),
        "supported_component_refs": _safe_list(state.get("supported_component_refs")),
        "missing_component_refs": _safe_list(state.get("missing_component_refs")),
        "blocked_component_refs": _safe_list(state.get("blocked_component_refs")),
        "contested_component_refs": _safe_list(state.get("contested_component_refs")),
        "followup_required_component_refs": _safe_list(
            state.get("followup_required_component_refs")
        ),
        "scrutineer_review_refs": _safe_list(state.get("scrutineer_review_refs")),
        "specialist_calculation_refs": _safe_list(
            state.get("specialist_calculation_refs")
        ),
        "followup_budget_posture": state.get("followup_budget_posture"),
        "mandatory_caveats": _text_list(state.get("mandatory_caveats"), limit=500),
        "prohibited_upgrades": _text_list(
            state.get("prohibited_upgrades"),
            limit=500,
        ),
        "fap_handoff_preview": _safe_mapping(state.get("fap_handoff_preview")),
        "readiness_history": _safe_list(state.get("readiness_history")),
        "readiness_count": state.get("readiness_count"),
        "sufficiency_readiness_is_product_authority": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "product_correctness_claimed": False,
        "current_answer_contract_mutated": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def reduce_sufficiency_readiness(
    *,
    run_kernel: Any,
    mode: str = "Balanced",
) -> SufficiencyReadinessResult:
    """Authorize and reduce readiness through RunKernel."""

    try:
        action = run_kernel.authorize_sufficiency_readiness(mode=mode)
        from core.run_kernel import Observation, ObservationType, RunStageStatus

        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.SUFFICIENCY_READINESS_DECIDED,
                status=RunStageStatus.COMPLETED,
                payload=build_sufficiency_readiness_observation_payload(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                ),
            )
        )
    except Exception as exc:  # pragma: no cover - translated for callers/tests.
        if exc.__class__.__name__ == "RunKernelTransitionError":
            raise SufficiencyReadinessRuntimeError(str(exc)) from exc
        raise
    return SufficiencyReadinessResult(
        readiness_state=dict(run_kernel.state.sufficiency_readiness_state),
        readiness_projection=dict(
            run_kernel.state.sufficiency_readiness_projection
        ),
        authorization_action_id=action.action_id,
    )


def readiness_ref_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact readiness ref suitable for handoff previews."""

    return _without_empty(
        {
            "readiness_id": state.get("readiness_id"),
            "readiness_digest": state.get("readiness_digest"),
            "final_readiness_status": state.get("final_readiness_status"),
            "mode": state.get("mode"),
        }
    )


def validate_sufficiency_readiness_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and sanitize canonical readiness state."""

    safe = _safe_mapping(state)
    if not safe:
        raise SufficiencyReadinessRuntimeError("readiness state is required")
    if safe.get("owner") != SUFFICIENCY_READINESS_OWNER:
        raise SufficiencyReadinessRuntimeError("readiness state owner mismatch")
    if safe.get("schema_version") != SUFFICIENCY_READINESS_SCHEMA_VERSION:
        raise SufficiencyReadinessRuntimeError("readiness state schema mismatch")
    if safe.get("canonical_state") is not True or safe.get("reduced_state") is not True:
        raise SufficiencyReadinessRuntimeError("readiness state must be canonical")
    if safe.get("proposal_packet") is not False or safe.get("durable_packet") is not False:
        raise SufficiencyReadinessRuntimeError("readiness state must not be a packet")
    if safe.get("final_readiness_status") not in READINESS_STATUSES:
        raise SufficiencyReadinessRuntimeError("unsupported readiness status")
    _validate_closed_flags(safe, context="readiness state")
    declared = _required_token(
        safe.get("readiness_digest"),
        "readiness state requires digest",
        limit=128,
    )
    if declared != _digest_json(_state_digest_payload(safe)):
        raise SufficiencyReadinessRuntimeError("readiness digest mismatch")
    return safe


def _component_readiness_entry(
    *,
    component: Mapping[str, Any],
    coverage_refs: Sequence[Mapping[str, Any]],
    admission_refs: Sequence[Mapping[str, Any]],
    scrutineer_refs: Sequence[Mapping[str, Any]],
    latest_review: Mapping[str, Any],
    specialist_refs: Sequence[Mapping[str, Any]],
    followup_budget_posture: str,
) -> dict[str, Any]:
    component_id = str(component["component_id"])
    role = _component_role(component)
    required_or_material = _is_required_or_material(component)
    latest_coverage = _safe_mapping(coverage_refs[-1]) if coverage_refs else {}
    status = "insufficient_evidence"
    blockers: list[str] = []
    caveats = _text_list(component.get("mandatory_caveats"), limit=500)
    prohibited = _text_list(component.get("prohibited_upgrades"), limit=500)

    if latest_coverage:
        caveats.extend(_text_list(latest_coverage.get("required_caveats"), limit=500))
        prohibited.extend(
            _text_list(latest_coverage.get("prohibited_upgrades"), limit=500)
        )
        coverage_state = _normalized_token(latest_coverage.get("coverage_state"))
        semantic_status = _normalized_token(
            latest_coverage.get("semantic_support_status")
        )
        currentness = _normalized_token(latest_coverage.get("currentness_posture"))
        conflict = _normalized_token(latest_coverage.get("conflict_posture"))
        followup_need = _normalized_token(latest_coverage.get("followup_need"))
        mode_budget = _normalized_token(latest_coverage.get("mode_budget_posture"))
        has_admitted_support = bool(
            latest_coverage.get("accepted_observation_refs")
            or admission_refs
        )
        if coverage_state == "conflicted" or conflict in _CONTESTED_CONFLICT:
            status = "contested"
            blockers.append("material coverage contradiction remains unresolved")
        elif currentness in _BAD_CURRENTNESS and required_or_material:
            status = "contested"
            blockers.append("material currentness posture remains unresolved")
        elif followup_need in _FOLLOWUP_REQUIRED and _budget_available(
            followup_budget_posture,
            mode_budget,
        ):
            status = "followup_required"
            blockers.append("material follow-up remains available before answer")
        elif coverage_state in _BAD_COVERAGE_STATES:
            if followup_need in _FOLLOWUP_REQUIRED and not _budget_available(
                followup_budget_posture,
                mode_budget,
            ):
                status = "blocked"
                blockers.append("required follow-up is unavailable or exhausted")
            else:
                status = "blocked" if required_or_material else "insufficient_evidence"
                blockers.append(f"coverage state is {coverage_state}")
        elif (
            coverage_state in _READY_COVERAGE_STATES
            and semantic_status == "supported"
            and has_admitted_support
        ):
            status = "full_answer_ready"
        else:
            status = "insufficient_evidence"
            blockers.append("coverage is not sufficient answer-bearing support")
    else:
        blockers.append("no current-contract ComponentCoverage ref")
        if required_or_material:
            status = "insufficient_evidence"
        else:
            status = "insufficient_evidence"
            caveats.append(f"Non-critical component {component_id} is unresolved.")

    status, blockers = _apply_specialist_posture(
        status=status,
        blockers=blockers,
        component=component,
        specialist_refs=specialist_refs,
    )
    status, blockers = _apply_scrutineer_posture(
        status=status,
        blockers=blockers,
        component_id=component_id,
        required_or_material=required_or_material,
        latest_review=latest_review,
        followup_budget_posture=followup_budget_posture,
    )
    return {
        "component_id": component_id,
        "component_revision": component.get("component_revision"),
        "component_digest": component.get("component_digest"),
        "component_role": role,
        "materiality": component.get("materiality"),
        "requirement_posture": component.get("requirement_posture"),
        "required_or_material": required_or_material,
        "coverage_refs": [dict(item) for item in coverage_refs],
        "semantic_observation_refs": [dict(item) for item in admission_refs],
        "scrutineer_refs": _component_scrutineer_refs(
            scrutineer_refs,
            component_id,
        ),
        "specialist_calculation_refs": [dict(item) for item in specialist_refs],
        "followup_budget_posture": followup_budget_posture,
        "component_readiness_status": status,
        "blockers": _dedupe_text(blockers),
        "mandatory_caveats": _dedupe_text(caveats),
        "prohibited_upgrades": _dedupe_text(prohibited),
    }


def _aggregate_answer_readiness(
    *,
    mode: str,
    contract: Mapping[str, Any],
    component_map: Mapping[str, Mapping[str, Any]],
    latest_review: Mapping[str, Any],
    scrutineer_refs: Sequence[Mapping[str, Any]],
    followup_budget_posture: str,
) -> dict[str, Any]:
    if not _contract_ref(contract) or not component_map:
        status = "not_applicable"
    else:
        entries = list(component_map.values())
        material_entries = [
            item for item in entries if item.get("required_or_material") is True
        ]
        ready = [
            item
            for item in entries
            if item.get("component_readiness_status") == "full_answer_ready"
        ]
        material_contested = [
            item
            for item in material_entries
            if item.get("component_readiness_status") == "contested"
        ]
        material_followup = [
            item
            for item in material_entries
            if item.get("component_readiness_status") == "followup_required"
        ]
        material_blocked = [
            item
            for item in material_entries
            if item.get("component_readiness_status") == "blocked"
        ]
        material_missing = [
            item
            for item in material_entries
            if item.get("component_readiness_status") == "insufficient_evidence"
        ]
        unresolved = [
            item
            for item in entries
            if item.get("component_readiness_status")
            not in {"full_answer_ready", "not_applicable"}
        ]
        if material_contested or _review_outcome(latest_review) == "contested":
            status = "contested"
        elif material_followup:
            status = "followup_required"
        elif _deep_review_unmet(mode, latest_review):
            status = "blocked"
        elif material_blocked:
            status = "blocked"
        elif not ready:
            status = "insufficient_evidence"
        elif material_missing:
            status = "blocked"
        elif not unresolved:
            status = "full_answer_ready"
        elif _partial_allowed(
            unresolved=unresolved,
            followup_budget_posture=followup_budget_posture,
        ):
            status = "partial_answer_ready"
        else:
            status = "blocked"

    component_refs = [
        _component_status_ref(item) for item in component_map.values()
    ]
    supported = [
        item
        for item in component_refs
        if item.get("component_readiness_status") == "full_answer_ready"
    ]
    missing = [
        item
        for item in component_refs
        if item.get("component_readiness_status") == "insufficient_evidence"
    ]
    blocked = [
        item
        for item in component_refs
        if item.get("component_readiness_status") == "blocked"
    ]
    contested = [
        item
        for item in component_refs
        if item.get("component_readiness_status") == "contested"
    ]
    followup = [
        item
        for item in component_refs
        if item.get("component_readiness_status") == "followup_required"
    ]
    caveats: list[str] = []
    prohibited: list[str] = []
    for entry in component_map.values():
        caveats.extend(_text_list(entry.get("mandatory_caveats"), limit=500))
        prohibited.extend(_text_list(entry.get("prohibited_upgrades"), limit=500))
        if entry.get("component_readiness_status") != "full_answer_ready":
            caveats.append(
                "Unresolved component "
                f"{entry.get('component_id')}: "
                f"{entry.get('component_readiness_status')}"
            )
            prohibited.append(
                "Do not upgrade unresolved component "
                f"{entry.get('component_id')} beyond readiness support."
            )
    if status == "partial_answer_ready":
        prohibited.append("Do not imply full-answer or product-correctness readiness.")
    if scrutineer_refs:
        caveats.append("Scrutineer refs are review posture, not product authority.")
    return {
        "final_readiness_status": status,
        "component_readiness_refs": component_refs,
        "supported_component_refs": supported,
        "missing_component_refs": missing,
        "blocked_component_refs": blocked,
        "contested_component_refs": contested,
        "followup_required_component_refs": followup,
        "mandatory_caveats": _dedupe_text(caveats),
        "prohibited_upgrades": _dedupe_text(prohibited),
    }


def _apply_specialist_posture(
    *,
    status: str,
    blockers: list[str],
    component: Mapping[str, Any],
    specialist_refs: Sequence[Mapping[str, Any]],
) -> tuple[str, list[str]]:
    requires_calculation = bool(
        _clean_token(component.get("calculation_policy"), limit=260)
        or "computed" in _text_list(component.get("allowed_support_kinds"))
    )
    if requires_calculation and not specialist_refs and _is_required_or_material(component):
        return "blocked", [*blockers, "required quantitative component lacks Specialist calculation"]
    for ref in specialist_refs:
        calc_status = _normalized_token(ref.get("calculation_status"))
        if calc_status == "contested":
            return "contested", [*blockers, "Specialist calculation is contested"]
        if calc_status in {"blocked", "invalid_input"} and _is_required_or_material(component):
            return "blocked", [*blockers, f"Specialist calculation is {calc_status}"]
    return status, blockers


def _apply_scrutineer_posture(
    *,
    status: str,
    blockers: list[str],
    component_id: str,
    required_or_material: bool,
    latest_review: Mapping[str, Any],
    followup_budget_posture: str,
) -> tuple[str, list[str]]:
    outcome = _review_outcome(latest_review)
    if outcome == "contested" and _review_applies_to_component(
        latest_review,
        component_id,
    ):
        return "contested", [*blockers, "Scrutineer review is contested"]
    if outcome == "blocked" and required_or_material:
        return "blocked", [*blockers, "Scrutineer review is blocked"]
    if outcome == "remediation_required" and _review_applies_to_component(
        latest_review,
        component_id,
    ):
        if followup_budget_posture == "available":
            return "followup_required", [*blockers, "Scrutineer requires remediation"]
        if required_or_material:
            return "blocked", [*blockers, "Scrutineer remediation budget unavailable"]
    return status, blockers


def _partial_allowed(
    *,
    unresolved: Sequence[Mapping[str, Any]],
    followup_budget_posture: str,
) -> bool:
    for entry in unresolved:
        if entry.get("required_or_material") is True:
            return False
        if entry.get("component_readiness_status") == "contested":
            return False
        if (
            entry.get("component_readiness_status") == "followup_required"
            and followup_budget_posture == "available"
        ):
            return False
    return True


def _deep_review_unmet(mode: str, latest_review: Mapping[str, Any]) -> bool:
    if mode != "Deep":
        return False
    if not latest_review:
        return True
    return not (
        latest_review.get("review_outcome") == "signed_off"
        and latest_review.get("review_pass_kind") == "final_verification"
    )


def _fap_handoff_preview(
    aggregate: Mapping[str, Any],
    component_map: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "readiness_status": aggregate.get("final_readiness_status"),
        "component_readiness_refs": [
            _component_status_ref(item) for item in component_map.values()
        ],
        "supported_component_refs": _safe_list(
            aggregate.get("supported_component_refs")
        ),
        "blocked_component_refs": _safe_list(aggregate.get("blocked_component_refs")),
        "missing_component_refs": _safe_list(aggregate.get("missing_component_refs")),
        "contested_component_refs": _safe_list(
            aggregate.get("contested_component_refs")
        ),
        "followup_required_component_refs": _safe_list(
            aggregate.get("followup_required_component_refs")
        ),
        "mandatory_caveats": _text_list(aggregate.get("mandatory_caveats"), limit=500),
        "prohibited_upgrades": _text_list(
            aggregate.get("prohibited_upgrades"),
            limit=500,
        ),
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "product_correctness_claimed": False,
    }


def _context_refs(
    *,
    current_answer_contract: Mapping[str, Any] | None,
    component_coverage_projection: Mapping[str, Any] | None,
    component_coverage_history: Sequence[Mapping[str, Any]],
    semantic_observation_admission_projection: Mapping[str, Any] | None,
    semantic_observation_admission_history: Sequence[Mapping[str, Any]],
    scrutineer_review_projection: Mapping[str, Any] | None,
    scrutineer_review_history: Sequence[Mapping[str, Any]],
    specialist_source_bound_calculation_projection: Mapping[str, Any] | None,
    specialist_source_bound_calculation_history: Sequence[Mapping[str, Any]],
    followup_search_authorization_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    contract = _safe_mapping(current_answer_contract)
    return {
        "current_answer_contract_ref": _contract_ref(contract),
        "component_refs": _contract_components(contract),
        "component_coverage_refs": _coverage_refs(
            component_coverage_projection,
            component_coverage_history,
        ),
        "semantic_observation_refs": _admission_refs(
            semantic_observation_admission_projection,
            semantic_observation_admission_history,
        ),
        "scrutineer_review_refs": _scrutineer_review_refs(
            scrutineer_review_projection,
            scrutineer_review_history,
        ),
        "specialist_calculation_refs": _specialist_calculation_refs(
            specialist_source_bound_calculation_projection,
            specialist_source_bound_calculation_history,
        ),
        "followup_authorization_ref": _followup_authorization_ref(
            followup_search_authorization_projection
        ),
    }


def _contract_ref(contract: Mapping[str, Any]) -> dict[str, Any]:
    version = _clean_token(
        contract.get("accepted_contract_version")
        or contract.get("current_contract_version")
        or contract.get("contract_version"),
        limit=160,
    )
    digest = _clean_token(
        contract.get("accepted_contract_digest")
        or contract.get("current_contract_digest")
        or contract.get("contract_digest"),
        limit=128,
    )
    if not version or not digest:
        return {}
    return {
        "source": "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _contract_components(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _safe_list(contract.get("accepted_answer_component_refs")):
        mapped = _safe_mapping(item)
        component_id = _clean_token(mapped.get("component_id"), limit=260)
        revision = _clean_token(mapped.get("component_revision"), limit=120)
        digest = _clean_token(mapped.get("component_digest"), limit=128)
        if not component_id or not revision or not digest or component_id in seen:
            continue
        seen.add(component_id)
        refs.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "component_revision": revision,
                    "component_digest": digest,
                    "component_role": _clean_token(
                        mapped.get("component_role") or mapped.get("role"),
                        limit=120,
                    ),
                    "requirement_posture": _clean_token(
                        mapped.get("requirement_posture"),
                        limit=120,
                    )
                    or "required",
                    "materiality": _clean_token(mapped.get("materiality"), limit=120)
                    or "material",
                    "allowed_support_kinds": _text_list(
                        mapped.get("allowed_support_kinds")
                    ),
                    "calculation_policy": _clean_token(
                        mapped.get("calculation_policy"),
                        limit=260,
                    ),
                    "mandatory_caveats": _text_list(
                        mapped.get("mandatory_caveats"),
                        limit=500,
                    ),
                    "prohibited_upgrades": _text_list(
                        mapped.get("prohibited_upgrades"),
                        limit=500,
                    ),
                }
            )
        )
    return refs


def _coverage_refs(
    projection: Mapping[str, Any] | None,
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = []
    for item in [*list(history or ()), projection or {}]:
        mapped = _safe_mapping(item)
        if not mapped:
            continue
        ref = _without_empty(
            {
                "coverage_record_id": mapped.get("coverage_record_id")
                or mapped.get("record_id"),
                "coverage_record_digest": mapped.get("coverage_record_digest")
                or mapped.get("record_digest"),
                "coverage_reduction_digest": mapped.get("coverage_reduction_digest"),
                "answer_component_id": mapped.get("answer_component_id"),
                "component_revision": mapped.get("component_revision"),
                "component_digest": mapped.get("component_digest"),
                "coverage_state": mapped.get("coverage_state"),
                "semantic_support_status": mapped.get("semantic_support_status"),
                "source_obligation_status": mapped.get("source_obligation_status"),
                "content_availability_status": mapped.get(
                    "content_availability_status"
                ),
                "evidence_custody_status": mapped.get("evidence_custody_status"),
                "currentness_posture": mapped.get("currentness_posture"),
                "conflict_posture": mapped.get("conflict_posture"),
                "followup_need": mapped.get("followup_need"),
                "mode_budget_posture": mapped.get("mode_budget_posture"),
                "accepted_observation_refs": _observation_refs(
                    mapped.get("accepted_observation_refs")
                ),
                "content_reference_bindings": _content_binding_refs(
                    mapped.get("content_reference_bindings")
                ),
                "required_caveats": _text_list(
                    mapped.get("required_caveats"),
                    limit=500,
                ),
                "prohibited_upgrades": _text_list(
                    mapped.get("prohibited_upgrades"),
                    limit=500,
                ),
            }
        )
        if ref.get("coverage_record_digest"):
            refs.append(ref)
    return _dedupe_refs(refs, "coverage_record_digest")


def _admission_refs(
    projection: Mapping[str, Any] | None,
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = []
    for item in [*list(history or ()), projection or {}]:
        mapped = _safe_mapping(item)
        if not mapped:
            continue
        ref = _without_empty(
            {
                "observation_id": mapped.get("observation_id"),
                "observation_digest": mapped.get("observation_digest"),
                "answer_component_id": mapped.get("answer_component_id"),
                "component_revision": mapped.get("component_revision"),
                "component_digest": mapped.get("component_digest"),
                "support_status": mapped.get("support_status"),
                "support_posture": mapped.get("support_posture"),
                "content_refs": _text_list(mapped.get("content_refs"), limit=260),
                "evidence_refs": _text_list(mapped.get("evidence_refs"), limit=260),
            }
        )
        if ref.get("observation_digest"):
            refs.append(ref)
    return _dedupe_refs(refs, "observation_digest")


def _scrutineer_review_refs(
    projection: Mapping[str, Any] | None,
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = []
    for item in [*list(history or ()), projection or {}]:
        mapped = _safe_mapping(item)
        if not mapped:
            continue
        ref = _without_empty(
            {
                "review_id": mapped.get("review_id"),
                "review_digest": mapped.get("review_digest"),
                "mode": mapped.get("mode"),
                "review_pass_kind": mapped.get("review_pass_kind"),
                "review_outcome": mapped.get("review_outcome"),
                "issue_count": mapped.get("issue_count"),
                "issues": _issue_refs(mapped.get("issues")),
                "contested": mapped.get("contested") is True,
                "remediation_budget_recommended": (
                    mapped.get("remediation_budget_recommended") is True
                ),
            }
        )
        if ref.get("review_digest"):
            refs.append(ref)
    return _dedupe_refs(refs, "review_digest")


def _specialist_calculation_refs(
    projection: Mapping[str, Any] | None,
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = []
    for item in [*list(history or ()), projection or {}]:
        mapped = _safe_mapping(item)
        if not mapped:
            continue
        input_records = _safe_list(mapped.get("input_records"))
        component_id = None
        for input_record in input_records:
            component_id = _clean_token(
                _safe_mapping(input_record).get("component_id"),
                limit=260,
            )
            if component_id:
                break
        result = _safe_mapping(mapped.get("result"))
        ref = _without_empty(
            {
                "record_id": mapped.get("record_id"),
                "record_digest": mapped.get("record_digest"),
                "component_id": component_id,
                "calculation_kind": mapped.get("calculation_kind"),
                "formula_digest": mapped.get("formula_digest"),
                "calculation_status": mapped.get("calculation_status"),
                "result_digest": result.get("result_digest"),
                "result_unit": result.get("unit"),
                "blocker_count": mapped.get("blocker_count"),
                "blockers": _specialist_blocker_refs(mapped.get("blockers")),
            }
        )
        if ref.get("record_digest"):
            refs.append(ref)
    return _dedupe_refs(refs, "record_digest")


def _followup_authorization_ref(
    projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    mapped = _safe_mapping(projection)
    if not mapped:
        return {}
    latest = _safe_mapping(mapped.get("latest_authorization"))
    return _without_empty(
        {
            "owner": mapped.get("owner"),
            "mode": mapped.get("mode"),
            "authorized_loop_count": mapped.get("authorized_loop_count"),
            "mode_budget": _safe_mapping(mapped.get("mode_budget")),
            "latest_authorization": {
                "authorization_id": latest.get("authorization_id"),
                "authorization_digest": latest.get("authorization_digest"),
                "query_count": latest.get("query_count"),
                "handoff_id": latest.get("handoff_id"),
                "handoff_digest": latest.get("handoff_digest"),
                "fixture_reentry_only": True,
                "live_dispatch_allowed": False,
            },
        }
    )


def _coverage_by_component(
    coverage_refs: Sequence[Mapping[str, Any]],
    component_refs: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    component_by_id = {item["component_id"]: item for item in component_refs}
    out: dict[str, list[dict[str, Any]]] = {}
    for ref in coverage_refs:
        mapped = _safe_mapping(ref)
        component_id = _clean_token(mapped.get("answer_component_id"), limit=260)
        component = component_by_id.get(component_id or "")
        if not component:
            continue
        if mapped.get("component_revision") != component.get("component_revision"):
            continue
        if mapped.get("component_digest") != component.get("component_digest"):
            continue
        out.setdefault(component_id or "", []).append(mapped)
    return out


def _refs_by_component(
    refs: Sequence[Mapping[str, Any]],
    *,
    component_key: str,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for item in refs:
        mapped = _safe_mapping(item)
        component_id = _clean_token(mapped.get(component_key), limit=260)
        if component_id:
            out.setdefault(component_id, []).append(mapped)
    return out


def _followup_budget_posture(
    mode: str,
    followup_projection: Mapping[str, Any] | None,
) -> str:
    if mode == "Fast":
        return "zero_budget"
    projection = _safe_mapping(followup_projection)
    if not projection:
        return "available"
    mode_budget = _safe_mapping(projection.get("mode_budget"))
    max_loops = _bounded_int(mode_budget.get("max_followup_loops"), default=0)
    loop_count = _bounded_int(projection.get("authorized_loop_count"), default=0)
    if max_loops and loop_count >= max_loops:
        return "exhausted"
    return "available"


def _budget_available(readiness_budget: str, coverage_budget: str) -> bool:
    if readiness_budget in {"zero_budget", "exhausted"}:
        return False
    if coverage_budget in _FOLLOWUP_EXHAUSTED:
        return False
    return readiness_budget == "available"


def _component_role(component: Mapping[str, Any]) -> str:
    return (
        _clean_token(component.get("component_role") or component.get("role"))
        or "answer_component"
    )


def _is_required_or_material(component: Mapping[str, Any]) -> bool:
    requirement = _normalized_token(component.get("requirement_posture")) or "required"
    materiality = _normalized_token(component.get("materiality")) or "material"
    return requirement == "required" or materiality == "material"


def _review_outcome(review: Mapping[str, Any]) -> str | None:
    return _clean_token(review.get("review_outcome"), limit=120)


def _review_applies_to_component(review: Mapping[str, Any], component_id: str) -> bool:
    issues = _safe_list(review.get("issues"))
    if not issues:
        return True
    component_issue_seen = False
    for issue in issues:
        issue_component = _clean_token(
            _safe_mapping(issue).get("component_id"),
            limit=260,
        )
        if not issue_component:
            return True
        component_issue_seen = True
        if issue_component == component_id:
            return True
    return not component_issue_seen


def _component_scrutineer_refs(
    refs: Sequence[Mapping[str, Any]],
    component_id: str,
) -> list[dict[str, Any]]:
    out = []
    for ref in refs:
        if _review_applies_to_component(ref, component_id):
            out.append(
                _without_empty(
                    {
                        "review_id": ref.get("review_id"),
                        "review_digest": ref.get("review_digest"),
                        "review_outcome": ref.get("review_outcome"),
                        "review_pass_kind": ref.get("review_pass_kind"),
                    }
                )
            )
    return out


def _component_status_ref(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "component_id": entry.get("component_id"),
        "component_revision": entry.get("component_revision"),
        "component_digest": entry.get("component_digest"),
        "component_readiness_status": entry.get("component_readiness_status"),
        "required_or_material": entry.get("required_or_material") is True,
    }


def _readiness_history(
    existing_projection: Mapping[str, Any] | None,
    *,
    readiness_id: str,
    readiness_digest: str,
    action_id: str,
    mode: str,
    status: str,
) -> list[dict[str, Any]]:
    existing = _safe_mapping(existing_projection)
    history = [
        _safe_mapping(item) for item in _safe_list(existing.get("readiness_history"))
    ]
    history.append(
        {
            "readiness_id": readiness_id,
            "readiness_digest": readiness_digest,
            "authorized_action_id": action_id,
            "mode": mode,
            "final_readiness_status": status,
            "final_answer_packet_created": False,
            "author_input_created": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "product_correctness_claimed": False,
        }
    )
    return history


def _observation_refs(value: Any) -> list[dict[str, Any]]:
    refs = []
    for item in _safe_list(value):
        mapped = _safe_mapping(item)
        ref = _without_empty(
            {
                "observation_id": mapped.get("observation_id"),
                "observation_digest": mapped.get("observation_digest"),
                "answer_component_id": mapped.get("answer_component_id"),
                "support_status": mapped.get("support_status"),
                "content_refs": _text_list(mapped.get("content_refs"), limit=260),
            }
        )
        if ref:
            refs.append(ref)
    return refs


def _content_binding_refs(value: Any) -> list[dict[str, Any]]:
    refs = []
    for item in _safe_list(value):
        mapped = _safe_mapping(item)
        ref = _without_empty(
            {
                "content_ref_id": mapped.get("content_ref_id"),
                "content_digest": mapped.get("content_digest"),
                "evidence_ref_id": mapped.get("evidence_ref_id"),
                "answer_component_id": mapped.get("answer_component_id"),
                "availability_status": mapped.get("availability_status"),
            }
        )
        if ref:
            refs.append(ref)
    return refs


def _issue_refs(value: Any) -> list[dict[str, Any]]:
    refs = []
    for item in _safe_list(value):
        mapped = _safe_mapping(item)
        ref = _without_empty(
            {
                "issue_id": mapped.get("issue_id"),
                "issue_digest": mapped.get("issue_digest"),
                "issue_kind": mapped.get("issue_kind"),
                "severity": mapped.get("severity"),
                "component_id": mapped.get("component_id"),
                "followup_proposal_ref": _safe_mapping(
                    mapped.get("followup_proposal_ref")
                ),
            }
        )
        if ref:
            refs.append(ref)
    return refs


def _specialist_blocker_refs(value: Any) -> list[dict[str, Any]]:
    refs = []
    for item in _safe_list(value):
        mapped = _safe_mapping(item)
        ref = _without_empty(
            {
                "blocker_kind": mapped.get("blocker_kind"),
                "blocker_digest": mapped.get("blocker_digest"),
            }
        )
        if ref:
            refs.append(ref)
    return refs


def _dedupe_refs(
    refs: Sequence[Mapping[str, Any]],
    digest_key: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        mapped = _safe_mapping(ref)
        key = (
            _clean_token(mapped.get(digest_key), limit=128)
            or _clean_token(mapped.get("component_id"), limit=260)
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
        text = _clean_text(item, limit=500)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if value.get(key) is not expected:
            raise SufficiencyReadinessRuntimeError(
                f"{context} must keep {key}=False"
            )
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if flags.get(key) is not expected:
            raise SufficiencyReadinessRuntimeError(
                f"{context} closed_surface_flags must keep {key}=False"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SufficiencyReadinessRuntimeError(
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
    elif isinstance(value, list | tuple | set | frozenset):
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
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=1_000)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key:
                continue
            if _is_raw_or_private_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
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
        raise SufficiencyReadinessRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalized_token(value: Any) -> str:
    text = _clean_token(value, limit=160) or ""
    return text.casefold().replace("-", "_").replace(" ", "_")


def _mode_label(mode: Any) -> str:
    label = _MODE_LABELS.get(str(_clean_token(mode, limit=40) or "").casefold())
    if not label:
        raise SufficiencyReadinessRuntimeError(
            "readiness mode must be Fast, Balanced, or Deep"
        )
    return label


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else default


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _state_digest_payload(state: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(state)
    for key in (
        "readiness_id",
        "readiness_digest",
        "readiness_history",
        "readiness_count",
    ):
        payload.pop(key, None)
    return payload


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "READINESS_STATUSES",
    "SUFFICIENCY_READINESS_ACTION_SCHEMA_VERSION",
    "SUFFICIENCY_READINESS_HELPER",
    "SUFFICIENCY_READINESS_OBSERVATION_SCHEMA_VERSION",
    "SUFFICIENCY_READINESS_OWNER",
    "SUFFICIENCY_READINESS_REASON",
    "SUFFICIENCY_READINESS_SCHEMA_VERSION",
    "SUFFICIENCY_READINESS_STAGE",
    "SUFFICIENCY_READINESS_TRACE_KEY",
    "SufficiencyReadinessResult",
    "SufficiencyReadinessRuntimeError",
    "build_sufficiency_readiness_action_inputs",
    "build_sufficiency_readiness_observation_payload",
    "build_sufficiency_readiness_projection",
    "build_sufficiency_readiness_state",
    "readiness_ref_from_state",
    "reduce_sufficiency_readiness",
    "validate_sufficiency_readiness_state",
]
