"""RunKernel-shaped source-obligation recovery authorization.

This module owns the policy decision for the generic single-relation
post-D-prime source-obligation gate. It does not execute provider acquisition,
call models, create support, adjudicate source authority, satisfy source
obligations, create citations, create FAP/Author material, or claim product
correctness.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.current_source_component_answer_type_binding import (
    current_source_component_answer_type_binding_from_relation_plan,
    current_source_component_answer_type_binding_ref,
)
from core.routing import AcquisitionCapability, DiscoverQualifier
from core.source_of_record_recovery_provider_config import (
    SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
)

SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SCHEMA_VERSION = (
    "single_relation_source_obligation_recovery_authorization_v1"
)
SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SURFACE = (
    "core.single_relation_source_obligation_recovery_authorization"
)
SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER = (
    "RunKernel"
)
SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND = (
    "single_relation_source_obligation_recovery_contract_reducer"
)

SOURCE_CHALLENGE_RECOVERY_PLAN_SCHEMA_VERSION = (
    "generic_single_relation_source_challenge_recovery_plan_v1"
)

AUTHORIZATION_STATUS_NOT_REQUIRED = "not_required"
AUTHORIZATION_STATUS_PRE_DPRIME_GATE_PENDING = (
    "pre_dprime_source_obligation_gate_pending"
)
AUTHORIZATION_STATUS_RECOVERY_REQUIRED_CONFIRMATION_REQUIRED = (
    "recovery_required_confirmation_required"
)
AUTHORIZATION_STATUS_RECOVERY_CALL_AUTHORIZED = "recovery_call_authorized"

TRIGGER_KIND_NONE = "none"
TRIGGER_KIND_PRE_DPRIME_SOURCE_OBLIGATION_GATE = (
    "pre_dprime_source_obligation_gate"
)
TRIGGER_KIND_DPRIME_CHALLENGE_SOURCE_OBLIGATION_GATE = (
    "dprime_challenge_source_obligation_gate"
)
TRIGGER_KIND_DPRIME_SUPPORT_SOURCE_OBLIGATION_GATE = (
    "dprime_support_source_obligation_gate"
)

BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED"
)
BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED = (
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED"
)

DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED = "admitted"
DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED = "challenged"

ANSWER_BEARING_CANDIDATE_WINDOW_ESTABLISHED = (
    "answer_bearing_candidate_window_established"
)
DISCOVER_OPERATION_REQUIREMENT = "search"
DEFAULT_MAX_RESULTS = 5
MAX_RECOVERY_PROVIDER_CALLS = 1

SOURCE_CHALLENGE_RECOVERY_TRIGGER_RELATIONS = frozenset(
    {"weak_or_overclaim_risk", "currentness_mismatch", "contradicts"}
)
DPRIME_SUPPORT_ADMISSION_RELATIONS = frozenset(
    {"directly_supports", "partially_supports"}
)

_CLOSED_SURFACE_FLAGS = {
    "support_created": False,
    "run_kernel_support_admitted": False,
    "source_authority_adjudicated": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "answer_created": False,
    "source_display_created": False,
    "fap_opened": False,
    "author_opened": False,
    "provider_chooser_created": False,
    "provider_bakeoff_created": False,
    "pre_dprime_triage_created": False,
}
_RAW_PRIVATE_RETENTION_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}


@dataclass(frozen=True, slots=True)
class SourceObligationRecoveryAuthorization:
    """Policy-only authorization packet for source-obligation recovery."""

    schema_version: str = (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SCHEMA_VERSION
    )
    authorization_status: str = AUTHORIZATION_STATUS_NOT_REQUIRED
    authorization_owner: str = (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER
    )
    authorization_surface: str = (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SURFACE
    )
    contract_reducer_kind: str = SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND
    contract_reducer_owner: str = "RunKernel"
    current_answer_contract_projection: Mapping[str, Any] = field(
        default_factory=dict
    )
    updated_contract_state: Mapping[str, Any] = field(default_factory=dict)
    authorization_blocker: str | None = None
    trigger_kind: str = TRIGGER_KIND_NONE
    trigger_relation: str | None = None
    trigger_blocker: str | None = None
    dprime_assessment_status: str = "not_reached"
    dprime_support_relation: str | None = None
    selected_candidate_ref: Mapping[str, Any] = field(default_factory=dict)
    selected_candidate_source_class_posture: Mapping[str, Any] = field(
        default_factory=dict
    )
    source_obligation_ref: Mapping[str, Any] = field(default_factory=dict)
    source_authority_requirement_ref: Mapping[str, Any] = field(default_factory=dict)
    source_obligation_status: str = "not_required"
    source_obligation_requires_source_of_record: bool = False
    selected_material_answer_bearing_by_safe_diagnostics: bool = False
    selected_material_official_source_of_record_looking: bool = False
    recovery_required: bool = False
    recovery_call_policy_authorized: bool = False
    recovery_confirmation_required: bool = False
    max_recovery_provider_calls: int = 0
    recovery_reason: str = ""
    provider_neutral_domain_constraints: tuple[str, ...] = ()
    recovery_query_ref: Mapping[str, Any] = field(default_factory=dict)
    source_challenge_recovery_plan: Mapping[str, Any] = field(default_factory=dict)
    support_admission_blocked: bool = False
    answer_display_blocked: bool = False
    source_display_blocked: bool = False
    run_kernel_support_admission_decision_status: str = (
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    raw_private_retention: bool = False
    closed_surface_flags: Mapping[str, bool] = field(
        default_factory=lambda: dict(_CLOSED_SURFACE_FLAGS)
    )

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "schema_version": self.schema_version,
                "authorization_status": self.authorization_status,
                "authorization_owner": self.authorization_owner,
                "authorization_surface": self.authorization_surface,
                "contract_reducer_kind": self.contract_reducer_kind,
                "contract_reducer_owner": self.contract_reducer_owner,
                "current_answer_contract_projection": dict(
                    self.current_answer_contract_projection
                ),
                "updated_contract_state": dict(self.updated_contract_state),
                "authorization_blocker": self.authorization_blocker,
                "trigger_kind": self.trigger_kind,
                "trigger_relation": self.trigger_relation,
                "trigger_blocker": self.trigger_blocker,
                "dprime_assessment_status": self.dprime_assessment_status,
                "dprime_support_relation": self.dprime_support_relation,
                "selected_candidate_ref": dict(self.selected_candidate_ref),
                "selected_candidate_source_class_posture": dict(
                    self.selected_candidate_source_class_posture
                ),
                "source_obligation_ref": dict(self.source_obligation_ref),
                "source_authority_requirement_ref": dict(
                    self.source_authority_requirement_ref
                ),
                "source_obligation_status": self.source_obligation_status,
                "source_obligation_requires_source_of_record": (
                    self.source_obligation_requires_source_of_record
                ),
                "selected_material_answer_bearing_by_safe_diagnostics": (
                    self.selected_material_answer_bearing_by_safe_diagnostics
                ),
                "selected_material_official_source_of_record_looking": (
                    self.selected_material_official_source_of_record_looking
                ),
                "recovery_required": self.recovery_required,
                "recovery_call_policy_authorized": (
                    self.recovery_call_policy_authorized
                ),
                "recovery_confirmation_required": (
                    self.recovery_confirmation_required
                ),
                "max_recovery_provider_calls": self.max_recovery_provider_calls,
                "recovery_reason": self.recovery_reason,
                "provider_neutral_domain_constraints": list(
                    self.provider_neutral_domain_constraints
                ),
                "recovery_query_ref": dict(self.recovery_query_ref),
                "source_challenge_recovery_plan": dict(
                    self.source_challenge_recovery_plan
                ),
                "support_admission_blocked": self.support_admission_blocked,
                "answer_display_blocked": self.answer_display_blocked,
                "source_display_blocked": self.source_display_blocked,
                "run_kernel_support_admission_decision_status": (
                    self.run_kernel_support_admission_decision_status
                ),
                "raw_private_retention": self.raw_private_retention,
                "closed_surface_flags": dict(self.closed_surface_flags),
            }
        )


def build_single_relation_source_obligation_recovery_authorization(
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    selected_candidate_diagnostic: Mapping[str, Any] | None,
    candidate_diagnostics: Sequence[Mapping[str, Any]] = (),
    dprime_status: Mapping[str, Any] | None = None,
    provider_acquisition_attempt_counts: Mapping[str, Any] | None = None,
    evidence_admission_ref: Mapping[str, Any] | None = None,
    recovery_attempt_ref: Mapping[str, Any] | None = None,
    recovery_attempt_counts: Mapping[str, Any] | None = None,
    recovery_confirmation_authorized: bool = False,
) -> SourceObligationRecoveryAuthorization:
    """Reduce source-obligation recovery state for one active relation contract."""

    plan = _safe_mapping(relation_plan)
    acquisition = _safe_mapping(acquisition_plan)
    selected = _safe_mapping(selected_candidate_diagnostic)
    dprime = _safe_mapping(dprime_status)
    source_obligation = _first_mapping(plan.get("source_obligations"))
    source_authority_requirement = _safe_mapping(
        plan.get("source_authority_posture_requirement")
    )
    dprime_assessment_status = (
        _clean_text(dprime.get("assessment_status"), limit=120)
        or ("not_reached" if not dprime else "unknown")
    )
    dprime_support_relation = _clean_text(dprime.get("support_relation"), limit=120)
    source_obligation_requires_source_of_record = (
        _requires_source_of_record_confirmation(
            source_obligation=source_obligation,
            source_authority_requirement=source_authority_requirement,
        )
    )
    source_obligation_status = _source_obligation_status(
        dprime_status=dprime,
        source_obligation=source_obligation,
        requires_source_of_record=source_obligation_requires_source_of_record,
    )
    selected_answer_bearing = candidate_answer_bearing_by_safe_diagnostics(selected)
    selected_official = (
        candidate_official_source_of_record_looking_by_safe_diagnostics(selected)
    )
    selected_ref = selected_candidate_ref_from_diagnostic(selected)
    posture = {
        "answer_bearing_by_safe_diagnostics": selected_answer_bearing,
        "official_source_of_record_looking_by_safe_diagnostics": selected_official,
        "source_authority_created": False,
        "source_obligation_satisfied": source_obligation_status == "satisfied",
        "citation_eligible": False,
    }
    source_posture_requires_gate = bool(
        selected
        and selected_answer_bearing
        and not selected_official
        and source_obligation_requires_source_of_record
        and source_obligation_status == "unsatisfied"
    )
    dprime_trigger_kind = _dprime_trigger_kind(
        assessment_status=dprime_assessment_status,
        support_relation=dprime_support_relation,
    )
    dprime_reached = bool(dprime)
    recovery_required = bool(source_posture_requires_gate and dprime_trigger_kind)
    pre_dprime_gate_pending = bool(source_posture_requires_gate and not dprime_reached)
    recovery_call_policy_authorized = bool(
        recovery_required and recovery_confirmation_authorized
    )
    recovery_confirmation_required = bool(
        recovery_required and not recovery_confirmation_authorized
    )
    trigger_kind = (
        TRIGGER_KIND_PRE_DPRIME_SOURCE_OBLIGATION_GATE
        if pre_dprime_gate_pending
        else dprime_trigger_kind or TRIGGER_KIND_NONE
    )
    authorization_status = _authorization_status(
        pre_dprime_gate_pending=pre_dprime_gate_pending,
        recovery_required=recovery_required,
        recovery_call_policy_authorized=recovery_call_policy_authorized,
    )
    blocker = _authorization_blocker(
        trigger_kind=trigger_kind,
        recovery_confirmation_required=recovery_confirmation_required,
    )
    domains = _observed_official_recovery_domains(candidate_diagnostics)
    recovery_query = _source_challenge_recovery_query(
        acquisition_plan=acquisition,
        observed_domains=domains,
    )
    recovery_reason = _recovery_reason(
        source_posture_requires_gate=source_posture_requires_gate,
        pre_dprime_gate_pending=pre_dprime_gate_pending,
        recovery_required=recovery_required,
        trigger_kind=trigger_kind,
        selected_answer_bearing=selected_answer_bearing,
        selected_official=selected_official,
        source_obligation_requires_source_of_record=(
            source_obligation_requires_source_of_record
        ),
        source_obligation_status=source_obligation_status,
    )
    source_authority_requirement_ref = _source_authority_requirement_ref(
        source_authority_requirement
    )
    recovery_plan = (
        _build_recovery_plan(
            relation_plan=plan,
            acquisition_plan=acquisition,
            dprime_support_relation=dprime_support_relation,
            selected_candidate_ref=selected_ref,
            selected_candidate_posture=posture,
            source_obligation=source_obligation,
            source_authority_requirement_ref=source_authority_requirement_ref,
            recovery_reason=recovery_reason,
            recovery_query=recovery_query,
            domains=domains,
            provider_acquisition_attempt_counts=(
                provider_acquisition_attempt_counts
            ),
        )
        if source_posture_requires_gate
        else {}
    )
    support_admission_blocked = bool(
        source_posture_requires_gate
        and (
            pre_dprime_gate_pending
            or recovery_required
            or dprime_support_relation in DPRIME_SUPPORT_ADMISSION_RELATIONS
        )
    )
    display_blocked = bool(pre_dprime_gate_pending or recovery_required)
    support_admission_status = _support_admission_status(
        support_admission_blocked=support_admission_blocked,
        recovery_required=recovery_required,
        pre_dprime_gate_pending=pre_dprime_gate_pending,
        dprime_support_relation=dprime_support_relation,
    )
    answer_display_status = _display_status(
        display_blocked=display_blocked,
        display_kind="answer",
    )
    source_display_status = _display_status(
        display_blocked=display_blocked,
        display_kind="source",
    )
    current_answer_contract_projection = _current_answer_contract_projection(
        relation_plan=plan,
        acquisition_plan=acquisition,
        source_obligation=source_obligation,
        source_authority_requirement_ref=source_authority_requirement_ref,
        provider_acquisition_attempt_counts=(
            provider_acquisition_attempt_counts
        ),
        selected_candidate_ref=selected_ref,
        selected_candidate_posture=posture,
        evidence_admission_ref=evidence_admission_ref,
        dprime_status=dprime,
        dprime_support_relation=dprime_support_relation,
        source_obligation_status=source_obligation_status,
        support_admission_status=support_admission_status,
        answer_display_status=answer_display_status,
        source_display_status=source_display_status,
        recovery_authorization_status=authorization_status,
        recovery_attempt_ref=recovery_attempt_ref,
        recovery_attempt_counts=recovery_attempt_counts,
        blocker_status=blocker,
    )
    updated_contract_state = _updated_contract_state(
        current_answer_contract_projection=current_answer_contract_projection,
        authorization_status=authorization_status,
        recovery_required=recovery_required,
        recovery_call_policy_authorized=recovery_call_policy_authorized,
        support_admission_status=support_admission_status,
        answer_display_status=answer_display_status,
        source_display_status=source_display_status,
        blocker_status=blocker,
    )
    return SourceObligationRecoveryAuthorization(
        authorization_status=authorization_status,
        current_answer_contract_projection=current_answer_contract_projection,
        updated_contract_state=updated_contract_state,
        authorization_blocker=blocker,
        trigger_kind=trigger_kind,
        trigger_relation=dprime_support_relation,
        trigger_blocker=blocker
        or (
            BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED
            if trigger_kind == TRIGGER_KIND_DPRIME_CHALLENGE_SOURCE_OBLIGATION_GATE
            else None
        ),
        dprime_assessment_status=dprime_assessment_status,
        dprime_support_relation=dprime_support_relation,
        selected_candidate_ref=selected_ref,
        selected_candidate_source_class_posture=posture,
        source_obligation_ref=source_obligation,
        source_authority_requirement_ref=source_authority_requirement_ref,
        source_obligation_status=source_obligation_status,
        source_obligation_requires_source_of_record=(
            source_obligation_requires_source_of_record
        ),
        selected_material_answer_bearing_by_safe_diagnostics=(
            selected_answer_bearing
        ),
        selected_material_official_source_of_record_looking=selected_official,
        recovery_required=recovery_required,
        recovery_call_policy_authorized=recovery_call_policy_authorized,
        recovery_confirmation_required=recovery_confirmation_required,
        max_recovery_provider_calls=(
            MAX_RECOVERY_PROVIDER_CALLS if recovery_call_policy_authorized else 0
        ),
        recovery_reason=recovery_reason,
        provider_neutral_domain_constraints=domains,
        recovery_query_ref={
            "recovery_query": recovery_query,
            "provider_neutral_domain_constraints": list(domains),
        }
        if source_posture_requires_gate
        else {},
        source_challenge_recovery_plan=recovery_plan,
        support_admission_blocked=support_admission_blocked,
        answer_display_blocked=display_blocked,
        source_display_blocked=display_blocked,
        run_kernel_support_admission_decision_status=(
            DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED
            if source_posture_requires_gate
            else DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
        ),
    )


def reduce_single_relation_source_obligation_recovery_contract(
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    selected_candidate_diagnostic: Mapping[str, Any] | None,
    candidate_diagnostics: Sequence[Mapping[str, Any]] = (),
    dprime_status: Mapping[str, Any] | None = None,
    provider_acquisition_attempt_counts: Mapping[str, Any] | None = None,
    evidence_admission_ref: Mapping[str, Any] | None = None,
    recovery_attempt_ref: Mapping[str, Any] | None = None,
    recovery_attempt_counts: Mapping[str, Any] | None = None,
    recovery_confirmation_authorized: bool = False,
) -> SourceObligationRecoveryAuthorization:
    """RunKernel-owned reducer alias for the single-relation contract state."""

    return build_single_relation_source_obligation_recovery_authorization(
        relation_plan=relation_plan,
        acquisition_plan=acquisition_plan,
        selected_candidate_diagnostic=selected_candidate_diagnostic,
        candidate_diagnostics=candidate_diagnostics,
        dprime_status=dprime_status,
        provider_acquisition_attempt_counts=provider_acquisition_attempt_counts,
        evidence_admission_ref=evidence_admission_ref,
        recovery_attempt_ref=recovery_attempt_ref,
        recovery_attempt_counts=recovery_attempt_counts,
        recovery_confirmation_authorized=recovery_confirmation_authorized,
    )


def _support_admission_status(
    *,
    support_admission_blocked: bool,
    recovery_required: bool,
    pre_dprime_gate_pending: bool,
    dprime_support_relation: str | None,
) -> str:
    if support_admission_blocked and pre_dprime_gate_pending:
        return "blocked_pending_dprime_by_source_obligation_contract_reducer"
    if support_admission_blocked and recovery_required:
        return "blocked_by_source_obligation_recovery_authorization"
    if dprime_support_relation in DPRIME_SUPPORT_ADMISSION_RELATIONS:
        return "allowed_by_source_obligation_contract_reducer"
    return "not_reached"


def _display_status(*, display_blocked: bool, display_kind: str) -> str:
    if display_blocked:
        return f"{display_kind}_display_blocked_by_source_obligation_contract_reducer"
    return f"{display_kind}_display_not_blocked_by_this_reducer"


def _current_answer_contract_projection(
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
    source_authority_requirement_ref: Mapping[str, Any],
    provider_acquisition_attempt_counts: Mapping[str, Any] | None,
    selected_candidate_ref: Mapping[str, Any],
    selected_candidate_posture: Mapping[str, Any],
    evidence_admission_ref: Mapping[str, Any] | None,
    dprime_status: Mapping[str, Any],
    dprime_support_relation: str | None,
    source_obligation_status: str,
    support_admission_status: str,
    answer_display_status: str,
    source_display_status: str,
    recovery_authorization_status: str,
    recovery_attempt_ref: Mapping[str, Any] | None,
    recovery_attempt_counts: Mapping[str, Any] | None,
    blocker_status: str | None,
) -> dict[str, Any]:
    provider_counts = _safe_mapping(provider_acquisition_attempt_counts)
    recovery_counts = _safe_mapping(recovery_attempt_counts)
    component_answer_type_binding = (
        current_source_component_answer_type_binding_from_relation_plan(
            relation_plan,
            expected_value_token_kinds=_safe_sequence(
                acquisition_plan.get("expected_value_token_kinds")
            ),
        )
    )
    component_answer_type_binding_ref = current_source_component_answer_type_binding_ref(
        component_answer_type_binding
    )
    payload = {
        "projection_kind": "single_relation_answer_contract_projection",
        "contract_owner": "RunKernel",
        "contract_reducer_kind": SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND,
        "contract_reducer_surface": (
            SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SURFACE
        ),
        "supported_query_class": relation_plan.get("supported_query_class_id"),
        "supported_query_class_boundary": _safe_mapping(
            relation_plan.get("supported_query_class_boundary")
        ),
        "component_ref": {
            "component_id": relation_plan.get("component_id"),
            "component_text": relation_plan.get("component_text"),
            "fact_kind": relation_plan.get("fact_kind"),
            "requested_answer_type": component_answer_type_binding[
                "requested_answer_type"
            ],
            "expected_value_shape": component_answer_type_binding[
                "expected_value_shape"
            ],
            "adjacent_claim_exclusions": list(
                component_answer_type_binding["adjacent_claim_exclusions"]
            ),
            "component_answer_type_binding_ref": component_answer_type_binding_ref,
        },
        "search_requirement_ref": _first_mapping(
            relation_plan.get("search_requirements")
        ),
        "source_obligation_ref": dict(source_obligation),
        "component_answer_type_binding": component_answer_type_binding,
        "component_answer_type_binding_ref": component_answer_type_binding_ref,
        "source_authority_posture_requirement_ref": dict(
            source_authority_requirement_ref
        ),
        "acquisition_plan_ref": {
            "schema_version": acquisition_plan.get("schema_version"),
            "relation_plan_id": acquisition_plan.get("relation_plan_id"),
            "component_id": acquisition_plan.get("component_id"),
            "search_requirement_id": acquisition_plan.get("search_requirement_id"),
            "source_obligation_id": acquisition_plan.get("source_obligation_id"),
            "provider_neutral_requirement": _safe_mapping(
                acquisition_plan.get("provider_neutral_requirement")
            ),
        },
        "completed_provider_route_ref": _safe_mapping(
            provider_counts.get("completed_provider_route")
        ),
        "provider_acquisition_attempt_refs": _provider_acquisition_attempt_refs(
            provider_counts
        ),
        "provider_acquisition_attempt_counts": provider_counts,
        "selected_candidate_window_ref": dict(selected_candidate_ref),
        "selected_candidate_source_class_posture": dict(
            selected_candidate_posture
        ),
        "evidence_admission_ref": _safe_mapping(evidence_admission_ref),
        "dprime_assessment_ref": _safe_mapping(dprime_status.get("assessment_ref")),
        "dprime_support_relation": dprime_support_relation,
        "source_obligation_status": source_obligation_status,
        "support_admission_status": support_admission_status,
        "answer_display_status": answer_display_status,
        "source_display_status": source_display_status,
        "recovery_authorization_status": recovery_authorization_status,
        "recovery_attempt_refs": _recovery_attempt_refs(
            recovery_attempt_ref=recovery_attempt_ref,
            recovery_attempt_counts=recovery_counts,
        ),
        "recovery_attempt_counts": recovery_counts,
        "blocker_status": blocker_status,
        "raw_private_retention_flags": dict(_RAW_PRIVATE_RETENTION_FLAGS),
        "raw_private_retention": False,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    payload["projection_digest"] = _digest_json(payload)
    return _json_safe(payload)


def _updated_contract_state(
    *,
    current_answer_contract_projection: Mapping[str, Any],
    authorization_status: str,
    recovery_required: bool,
    recovery_call_policy_authorized: bool,
    support_admission_status: str,
    answer_display_status: str,
    source_display_status: str,
    blocker_status: str | None,
) -> dict[str, Any]:
    projection_ref = {
        "projection_kind": current_answer_contract_projection.get(
            "projection_kind"
        ),
        "projection_digest": current_answer_contract_projection.get(
            "projection_digest"
        ),
        "contract_owner": "RunKernel",
    }
    state = {
        "state_kind": "single_relation_answer_contract_state",
        "state_owner": "RunKernel",
        "state_transition": "source_obligation_recovery_authorization_reduced",
        "state_reducer_kind": SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND,
        "current_answer_contract_projection_ref": projection_ref,
        "recovery_authorization_status": authorization_status,
        "recovery_required": recovery_required,
        "recovery_call_policy_authorized": recovery_call_policy_authorized,
        "support_admission_status": support_admission_status,
        "answer_display_status": answer_display_status,
        "source_display_status": source_display_status,
        "support_admission_allowed": (
            support_admission_status == "allowed_by_source_obligation_contract_reducer"
        ),
        "answer_display_allowed": not answer_display_status.startswith(
            "answer_display_blocked"
        ),
        "source_display_allowed": not source_display_status.startswith(
            "source_display_blocked"
        ),
        "blocker_status": blocker_status,
        "raw_private_retention_flags": dict(_RAW_PRIVATE_RETENTION_FLAGS),
        "raw_private_retention": False,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    state["state_digest"] = _digest_json(state)
    return _json_safe(state)


def _provider_acquisition_attempt_refs(
    provider_counts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not provider_counts:
        return []
    return [
        {
            "attempt_kind": "initial_product_provider_acquisition",
            "provider_calls_attempted": _bounded_int(
                provider_counts.get("provider_calls_attempted")
            ),
            "provider_calls_completed": _bounded_int(
                provider_counts.get("provider_calls_completed")
            ),
            "provider_results_returned": _bounded_int(
                provider_counts.get("provider_results_returned")
            ),
            "extraction_provider_calls_attempted": _bounded_int(
                provider_counts.get("extraction_provider_calls_attempted")
            ),
            "extraction_provider_calls_completed": _bounded_int(
                provider_counts.get("extraction_provider_calls_completed")
            ),
        }
    ]


def _recovery_attempt_refs(
    *,
    recovery_attempt_ref: Mapping[str, Any] | None,
    recovery_attempt_counts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not recovery_attempt_ref and not recovery_attempt_counts:
        return []
    return [
        {
            "attempt_kind": "source_obligation_recovery_provider_acquisition",
            "recovery_attempt_ref": _safe_mapping(recovery_attempt_ref),
            "provider_calls_attempted": _bounded_int(
                recovery_attempt_counts.get("provider_calls_attempted")
                or recovery_attempt_counts.get(
                    "source_challenge_recovery_provider_calls_attempted"
                )
            ),
            "provider_calls_completed": _bounded_int(
                recovery_attempt_counts.get("provider_calls_completed")
                or recovery_attempt_counts.get(
                    "source_challenge_recovery_provider_calls_completed"
                )
            ),
            "provider_results_returned": _bounded_int(
                recovery_attempt_counts.get("provider_results_returned")
                or recovery_attempt_counts.get(
                    "source_challenge_recovery_provider_results_returned"
                )
            ),
        }
    ]


def candidate_answer_bearing_by_safe_diagnostics(
    diagnostic: Mapping[str, Any] | None,
) -> bool:
    safe = _safe_mapping(diagnostic)
    return (
        safe.get("answer_bearing_candidate_window_status")
        == ANSWER_BEARING_CANDIDATE_WINDOW_ESTABLISHED
        and bool(_safe_sequence(safe.get("matched_value_token_kinds")))
        and _bounded_int(safe.get("matched_anchor_count")) > 0
    )


def candidate_official_source_of_record_looking_by_safe_diagnostics(
    diagnostic: Mapping[str, Any] | None,
) -> bool:
    safe = _safe_mapping(diagnostic)
    features = _safe_mapping(safe.get("candidate_selection_features"))
    return bool(
        safe.get("official_or_source_record_looking_http_candidate") is True
        or features.get("source_of_record_domain_signal") is True
        or features.get("official_domain_signal") is True
        or features.get("public_agency_domain_signal") is True
    )


def selected_candidate_ref_from_diagnostic(
    diagnostic: Mapping[str, Any] | None,
) -> dict[str, Any]:
    safe = _safe_mapping(diagnostic)
    if not safe:
        return {}
    return {
        "candidate_id": _clean_text(safe.get("candidate_id"), limit=320),
        "result_rank": _bounded_int(safe.get("result_rank"), default=0),
        "title": _clean_text(safe.get("title"), limit=220),
        "domain": _clean_domain(safe.get("domain")),
        "url": _clean_text(safe.get("url"), limit=700),
        "answer_bearing_candidate_window_status": safe.get(
            "answer_bearing_candidate_window_status"
        ),
        "matched_value_token_kinds": list(
            _safe_sequence(safe.get("matched_value_token_kinds"))
        ),
        "official_source_of_record_looking": (
            candidate_official_source_of_record_looking_by_safe_diagnostics(safe)
        ),
    }


def _authorization_status(
    *,
    pre_dprime_gate_pending: bool,
    recovery_required: bool,
    recovery_call_policy_authorized: bool,
) -> str:
    if pre_dprime_gate_pending:
        return AUTHORIZATION_STATUS_PRE_DPRIME_GATE_PENDING
    if recovery_call_policy_authorized:
        return AUTHORIZATION_STATUS_RECOVERY_CALL_AUTHORIZED
    if recovery_required:
        return AUTHORIZATION_STATUS_RECOVERY_REQUIRED_CONFIRMATION_REQUIRED
    return AUTHORIZATION_STATUS_NOT_REQUIRED


def _authorization_blocker(
    *,
    trigger_kind: str,
    recovery_confirmation_required: bool,
) -> str | None:
    if not recovery_confirmation_required:
        return None
    if trigger_kind == TRIGGER_KIND_DPRIME_CHALLENGE_SOURCE_OBLIGATION_GATE:
        return BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED
    return BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED


def _dprime_trigger_kind(*, assessment_status: str, support_relation: str | None) -> str:
    if (
        assessment_status == "challenge-recommended"
        or support_relation in SOURCE_CHALLENGE_RECOVERY_TRIGGER_RELATIONS
    ):
        return TRIGGER_KIND_DPRIME_CHALLENGE_SOURCE_OBLIGATION_GATE
    if assessment_status == "assessed" and support_relation in DPRIME_SUPPORT_ADMISSION_RELATIONS:
        return TRIGGER_KIND_DPRIME_SUPPORT_SOURCE_OBLIGATION_GATE
    return ""


def _source_obligation_status(
    *,
    dprime_status: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
    requires_source_of_record: bool,
) -> str:
    if not requires_source_of_record:
        return "not_required"
    if _source_obligation_confirmation_satisfied(dprime_status) or (
        source_obligation.get("satisfaction_claimed") is True
    ):
        return "satisfied"
    return "unsatisfied"


def _source_obligation_confirmation_satisfied(dprime: Mapping[str, Any]) -> bool:
    return bool(
        dprime.get("source_obligation_satisfaction_claimed") is True
        or dprime.get("citation_eligibility_claimed") is True
        or dprime.get("source_obligation_satisfied") is True
    )


def _requires_source_of_record_confirmation(
    *,
    source_obligation: Mapping[str, Any],
    source_authority_requirement: Mapping[str, Any],
) -> bool:
    expected_use = (
        _clean_text(source_obligation.get("expected_source_use_requirement"), limit=80)
        or ""
    ).casefold()
    if expected_use in {"authority", "source_of_record", "official"}:
        return True
    family = [
        str(item).casefold()
        for item in _safe_sequence(
            source_authority_requirement.get("expected_source_class_family")
        )
    ]
    if any(
        "official" in item
        or "source_of_record" in item
        or "government" in item
        or "public_agency" in item
        or "legal" in item
        or "regulatory" in item
        for item in family
    ):
        return True
    text = (
        " ".join(
            str(item or "")
            for item in (
                source_obligation.get("source_obligation_text"),
                source_authority_requirement.get("requirement_id"),
            )
        )
    ).casefold()
    return "official" in text or "source-of-record" in text or "source of record" in text


def _source_authority_requirement_ref(
    requirement: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(requirement)
    return {
        "requirement_id": _clean_text(safe.get("requirement_id"), limit=220),
        "contract_ref": _clean_text(safe.get("contract_ref"), limit=220),
        "expected_source_use_requirement": _clean_text(
            safe.get("expected_source_use_requirement"),
            limit=120,
        ),
        "expected_source_class_family": list(
            _safe_sequence(safe.get("expected_source_class_family"))
        ),
        "actual_source_authority_posture_created": bool(
            safe.get("actual_source_authority_posture_created") is True
        ),
    }


def _recovery_reason(
    *,
    source_posture_requires_gate: bool,
    pre_dprime_gate_pending: bool,
    recovery_required: bool,
    trigger_kind: str,
    selected_answer_bearing: bool,
    selected_official: bool,
    source_obligation_requires_source_of_record: bool,
    source_obligation_status: str,
) -> str:
    if recovery_required and trigger_kind == TRIGGER_KIND_DPRIME_SUPPORT_SOURCE_OBLIGATION_GATE:
        return (
            "D-prime may be evidence-relative directly supportive, but the selected "
            "answer-bearing material is not official/source-of-record-looking and "
            "the source-of-record obligation remains unsatisfied."
        )
    if recovery_required:
        return (
            "D-prime challenge posture combines with selected answer-bearing "
            "non-official material and an unsatisfied source-of-record obligation."
        )
    if pre_dprime_gate_pending:
        return (
            "Selected answer-bearing material is non-official under an unsatisfied "
            "source-of-record obligation; RunKernel support admission must remain "
            "blocked if D-prime later returns an admission-bearing relation."
        )
    if not selected_answer_bearing:
        return "Selected material is not answer-bearing by safe diagnostics."
    if selected_official:
        return (
            "Selected material is already official/source-of-record-looking by safe "
            "diagnostics; this recovery gate is not triggered."
        )
    if not source_obligation_requires_source_of_record:
        return "No source-of-record obligation is active for this gate."
    if source_obligation_status == "satisfied":
        return "Source obligation is already confirmed satisfied."
    if not source_posture_requires_gate:
        return "Source-obligation recovery gate conditions are not met."
    return "D-prime did not return a relation that requires this recovery gate."


def _build_recovery_plan(
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any],
    dprime_support_relation: str | None,
    selected_candidate_ref: Mapping[str, Any],
    selected_candidate_posture: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
    source_authority_requirement_ref: Mapping[str, Any],
    recovery_reason: str,
    recovery_query: str,
    domains: Sequence[str],
    provider_acquisition_attempt_counts: Mapping[str, Any] | None,
) -> dict[str, Any]:
    completed_route = _safe_mapping(
        _safe_mapping(provider_acquisition_attempt_counts).get(
            "completed_provider_route"
        )
    )
    plan = {
        "schema_version": SOURCE_CHALLENGE_RECOVERY_PLAN_SCHEMA_VERSION,
        "authorization_owner": (
            SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER
        ),
        "authorization_surface": (
            SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SURFACE
        ),
        "trigger_relation": dprime_support_relation,
        "trigger_blocker": BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED
        if dprime_support_relation in SOURCE_CHALLENGE_RECOVERY_TRIGGER_RELATIONS
        else None,
        "selected_candidate_ref": dict(selected_candidate_ref),
        "selected_candidate_source_class_posture": dict(
            selected_candidate_posture
        ),
        "source_obligation_id": relation_plan.get("source_obligation_id"),
        "source_obligation_ref": dict(source_obligation),
        "source_authority_requirement_ref": dict(source_authority_requirement_ref),
        "acquisition_plan_ref": {
            "schema_version": acquisition_plan.get("schema_version"),
            "relation_plan_id": acquisition_plan.get("relation_plan_id"),
            "component_id": acquisition_plan.get("component_id"),
            "search_requirement_id": acquisition_plan.get("search_requirement_id"),
            "source_obligation_id": acquisition_plan.get("source_obligation_id"),
        },
        "recovery_reason": recovery_reason,
        "official_source_of_record_recovery_intent": True,
        "candidate_official_domains_observed": list(domains),
        "domain_constraints": list(domains),
        "domain_constraints_acquisition_only": True,
        "recovery_query": recovery_query,
        "provider_neutral_requirement": {
            "capability": AcquisitionCapability.DISCOVER.value,
            "discover_qualifier": DiscoverQualifier.DOMAIN_TARGETED.value,
            "provider_selection_owner": "core.routing",
        },
        "provider_role": SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
        "requested_operation": DISCOVER_OPERATION_REQUIREMENT,
        "max_results": DEFAULT_MAX_RESULTS,
        "ordinary_first_stage_route_ref": completed_route,
        "ordinary_first_stage_provider": completed_route.get(
            "selected_provider"
        ),
        "provider_decision_hardcoded_in_runner": False,
        "include_domains": list(domains),
        "exclude_domains": [],
        "source_of_record_domain_constraints": list(domains),
        "raw_private_retention": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    return _json_safe(plan)


def _source_challenge_recovery_query(
    *,
    acquisition_plan: Mapping[str, Any],
    observed_domains: Sequence[str],
) -> str:
    parts: list[str] = []
    acquisition_query = _clean_text(acquisition_plan.get("acquisition_query"), limit=220)
    if acquisition_query:
        parts.append(acquisition_query)
    parts.extend(
        str(item)
        for item in _safe_sequence(acquisition_plan.get("answer_bearing_anchor_terms"))
        if _clean_text(item, limit=80)
    )
    parts.extend(
        str(item)
        for item in _safe_sequence(acquisition_plan.get("artifact_source_terms"))
        if _clean_text(item, limit=80)
    )
    parts.extend(("official", "current", "source of record"))
    parts.extend(observed_domains)
    return _clean_text(" ".join(_unique_clean_terms(parts, limit=18)), limit=260) or (
        acquisition_query or "official current source of record"
    )


def _observed_official_recovery_domains(
    candidate_diagnostics: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    domains: list[str] = []
    seen: set[str] = set()
    for item in candidate_diagnostics:
        diagnostic = _safe_mapping(item)
        if not candidate_official_source_of_record_looking_by_safe_diagnostics(
            diagnostic
        ):
            continue
        domain = _constraint_domain_from_diagnostic(diagnostic)
        if not domain or domain in seen:
            continue
        seen.add(domain)
        domains.append(domain)
    return tuple(domains[:DEFAULT_MAX_RESULTS])


def _constraint_domain_from_diagnostic(diagnostic: Mapping[str, Any]) -> str | None:
    domain = _clean_domain(diagnostic.get("domain"))
    if not domain:
        url = _clean_text(diagnostic.get("url"), limit=700)
        domain = urlparse(url or "").netloc.casefold() if url else ""
    if not domain:
        return None
    return domain[4:] if domain.startswith("www.") else domain


def _unique_clean_terms(values: Sequence[Any], *, limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value, limit=80)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _first_mapping(value: Any) -> dict[str, Any]:
    seq = _safe_sequence(value)
    return _safe_mapping(seq[0]) if seq else {}


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_domain(value: Any) -> str | None:
    text = _clean_text(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    domain = (parsed.netloc or parsed.path).lower().strip("/")
    return domain[4:] if domain.startswith("www.") else domain


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "AUTHORIZATION_STATUS_NOT_REQUIRED",
    "AUTHORIZATION_STATUS_PRE_DPRIME_GATE_PENDING",
    "AUTHORIZATION_STATUS_RECOVERY_CALL_AUTHORIZED",
    "AUTHORIZATION_STATUS_RECOVERY_REQUIRED_CONFIRMATION_REQUIRED",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED",
    "DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED",
    "DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED",
    "SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND",
    "SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER",
    "SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SCHEMA_VERSION",
    "SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_SURFACE",
    "SOURCE_CHALLENGE_RECOVERY_PLAN_SCHEMA_VERSION",
    "SourceObligationRecoveryAuthorization",
    "build_single_relation_source_obligation_recovery_authorization",
    "candidate_answer_bearing_by_safe_diagnostics",
    "candidate_official_source_of_record_looking_by_safe_diagnostics",
    "selected_candidate_ref_from_diagnostic",
    "reduce_single_relation_source_obligation_recovery_contract",
]
