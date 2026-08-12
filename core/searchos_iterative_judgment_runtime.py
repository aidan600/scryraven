"""Canonical SearchOS Slice A iterative-judgment contracts.

This module is the neutral post-first-wave owner for SearchOS Slice A.  It is
intentionally provider-agnostic and text-retention-light: DISCOVER material is
directional candidate context only, while support-proposal eligibility begins
only with exact READ custody.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from core.discovery_source_result import normalize_discovery_result_url
from core.query_plan import DiscoveryJobClass

SEARCHOS_OWNER = "RunKernel.SearchOSIterativeJudgment"
SEARCHOS_POLICY_SCHEMA_VERSION = "searchos_policy_profile_v1"
SEARCHOS_STATE_SCHEMA_VERSION = "searchos_iterative_judgment_state_v1"
SEARCHOS_REVISION_1_CANDIDATE_STATE_SCHEMA_VERSION = "searchos_revision_1_candidate_state_v1"

SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION = "searchos_iteration_candidate_set_v1"
SEARCHOS_CANDIDATE_USE_OPTION_SCHEMA_VERSION = "searchos_candidate_use_option_v2"
SEARCHOS_CANDIDATE_LINEAGE_SNAPSHOT_SCHEMA_VERSION = "searchos_candidate_lineage_snapshot_v1"
SEARCHOS_CANDIDATE_USE_WINDOW_SCHEMA_VERSION = "candidate_use_window_v1"
SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION = "searchos_judgment_request_v1"
SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION = "searchos_judgment_decision_v1"
SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION = "searchos_navigation_judgment_request_v1"
SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION = "searchos_navigation_judgment_decision_v1"
SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION = "searchos_semantic_evaluation_handoff_v1"
SEARCHOS_INTERPRETATION_BINDING_SCHEMA_VERSION = (
    "searchos_interpretation_binding_v1"
)
SEARCHOS_EFFECTIVE_SEMANTIC_SLOT_VIEW_SCHEMA_VERSION = (
    "searchos_effective_semantic_slot_view_v1"
)
SEARCHOS_INTERPRETATION_BINDING_CATEGORY_BY_SLOT_KIND = MappingProxyType(
    {
        "entity": "identity_alias",
        "variant": "currentness_version",
        "time_period": "currentness_version",
        "source_basis": "document_lineage",
        "unknown_or_other": "externally_verifiable_terminology",
    }
)
SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION = "searchos_slice_a_readiness_v1"
SEARCHOS_REQUIRED_NEEDS_BLOCK_SCHEMA_VERSION = (
    "searchos_slice_a_required_needs_block_v1"
)
SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED = "SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED"
SEARCHOS_BLOCKER_INTERPRETATION_BY_CLASS = {
    "component_receiver_failure": "structural_or_validation_blocker",
    "gap_basis_rejection": "structural_or_validation_blocker",
    "validation_failure": "structural_or_validation_blocker",
    "provider_or_acquisition_failure": "provider_or_acquisition_blocker",
    "recovery_policy_closed": "lawful_recovery_exhaustion",
    "recovery_ineligible": "lawful_recovery_ineligible",
}
SEARCHOS_BLOCKER_INTERPRETATIONS = frozenset(
    SEARCHOS_BLOCKER_INTERPRETATION_BY_CLASS.values()
)

MAXIMUM_ACTIVE_SLOTS = 8
CANDIDATE_USE_WINDOW_SIZE = 12
MAX_FOLLOWUP_QUERY_CHARS = 300
MAX_UNRESOLVED_REASON_CHARS = 240
COMPLETED_CANDIDATE_OPTION_DISPOSITIONS = frozenset({"custodied", "read_insufficient", "invalid", "declined"})


class SearchOSRuntimeError(ValueError):
    """Raised when SearchOS authority or lineage validation fails closed."""


class SearchOSProfileName(str, Enum):
    FAST = "Fast"
    BALANCED = "Balanced"
    DEEP = "Deep"


class SearchOSJudgmentAction(str, Enum):
    HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION = "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    REQUEST_READ_PAGE = "REQUEST_READ_PAGE"
    REQUEST_NAVIGATE_BREADCRUMB = "REQUEST_NAVIGATE_BREADCRUMB"
    PROPOSE_FOLLOWUP_QUERY = "PROPOSE_FOLLOWUP_QUERY"
    PROPOSE_INTERPRETATION_BINDING = "PROPOSE_INTERPRETATION_BINDING"
    REQUIRE_CLARIFICATION = "REQUIRE_CLARIFICATION"
    HANDOFF_UNRESOLVED = "HANDOFF_UNRESOLVED"


class SearchOSSlotPosture(str, Enum):
    ACTIVE_UNJUDGED = "active_unjudged"
    AWAITING_NAVIGATION_ADMISSION = "awaiting_navigation_admission"
    AWAITING_NAVIGATION_EXECUTION = "awaiting_navigation_execution"
    AWAITING_READ = "awaiting_read"
    AWAITING_FOLLOWUP_DISCOVER = "awaiting_followup_discover"
    AWAITING_INTERPRETATION_BINDING = "awaiting_interpretation_binding"
    CLARIFICATION_REQUIRED = "clarification_required"
    READY_FOR_SEMANTIC_EVALUATION = "ready_for_semantic_evaluation"
    SEMANTICALLY_HANDED_OFF = "semantically_handed_off"
    UNRESOLVED_HANDOFF = "unresolved_handoff"
    JUDGMENT_FAILED = "judgment_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    STALE_OR_INVALID = "stale_or_invalid"


class SearchOSMaterialAuthority(str, Enum):
    DIRECTIONAL_CANDIDATE_CONTEXT = "directional_candidate_context"
    READ_CUSTODY_MATERIAL = "read_custody_material"


class SearchOSRequirementPosture(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass(frozen=True, slots=True)
class SearchOSPolicyProfileV1:
    profile_name: SearchOSProfileName
    minimum_reserved_judgment_calls_per_required_slot: int
    additional_judgment_call_pool_per_active_slot: int
    candidate_windows_per_slot: int
    candidate_waves_per_slot: int
    read_nominations_per_slot: int
    followup_query_nominations_per_slot: int
    orientation_refinements_per_slot: int = 1
    interpretation_bindings_per_slot: int = 1
    maximum_active_slots: int = MAXIMUM_ACTIVE_SLOTS
    candidate_use_window_size: int = CANDIDATE_USE_WINDOW_SIZE
    navigation_runtime_open: bool = False
    post_analyst_reentry_runtime_open: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SEARCHOS_POLICY_SCHEMA_VERSION,
            "owner": SEARCHOS_OWNER,
            "profile_name": self.profile_name.value,
            "maximum_active_slots": self.maximum_active_slots,
            "candidate_use_window_size": self.candidate_use_window_size,
            "minimum_reserved_judgment_calls_per_required_slot": (
                self.minimum_reserved_judgment_calls_per_required_slot
            ),
            "additional_judgment_call_pool_per_active_slot": (self.additional_judgment_call_pool_per_active_slot),
            "candidate_windows_per_slot": self.candidate_windows_per_slot,
            "candidate_waves_per_slot": self.candidate_waves_per_slot,
            "read_nominations_per_slot": self.read_nominations_per_slot,
            "followup_query_nominations_per_slot": (self.followup_query_nominations_per_slot),
            "orientation_refinements_per_slot": self.orientation_refinements_per_slot,
            "interpretation_bindings_per_slot": self.interpretation_bindings_per_slot,
            "navigation_runtime_open": self.navigation_runtime_open,
            "post_analyst_reentry_runtime_open": (self.post_analyst_reentry_runtime_open),
            "provisional_maximum_leash": True,
            "consumption_target": False,
            "permanently_calibrated": False,
        }


_POLICY_PROFILES = {
    SearchOSProfileName.FAST: SearchOSPolicyProfileV1(
        profile_name=SearchOSProfileName.FAST,
        minimum_reserved_judgment_calls_per_required_slot=2,
        additional_judgment_call_pool_per_active_slot=1,
        candidate_windows_per_slot=2,
        candidate_waves_per_slot=2,
        read_nominations_per_slot=2,
        followup_query_nominations_per_slot=1,
    ),
    SearchOSProfileName.BALANCED: SearchOSPolicyProfileV1(
        profile_name=SearchOSProfileName.BALANCED,
        minimum_reserved_judgment_calls_per_required_slot=3,
        additional_judgment_call_pool_per_active_slot=2,
        candidate_windows_per_slot=3,
        candidate_waves_per_slot=3,
        read_nominations_per_slot=3,
        followup_query_nominations_per_slot=2,
    ),
    SearchOSProfileName.DEEP: SearchOSPolicyProfileV1(
        profile_name=SearchOSProfileName.DEEP,
        minimum_reserved_judgment_calls_per_required_slot=4,
        additional_judgment_call_pool_per_active_slot=4,
        candidate_windows_per_slot=4,
        candidate_waves_per_slot=4,
        read_nominations_per_slot=4,
        followup_query_nominations_per_slot=3,
    ),
}

_NAVIGATION_LIMITS_BY_PROFILE = MappingProxyType({
    SearchOSProfileName.FAST: MappingProxyType({
        "navigation_max_depth": 1,
        "navigation_selections_per_slot": 1,
        "navigation_edges_per_run": 8,
    }),
    SearchOSProfileName.BALANCED: MappingProxyType({
        "navigation_max_depth": 2,
        "navigation_selections_per_slot": 2,
        "navigation_edges_per_run": 16,
    }),
    SearchOSProfileName.DEEP: MappingProxyType({
        "navigation_max_depth": 3,
        "navigation_selections_per_slot": 3,
        "navigation_edges_per_run": 24,
    }),
})


def searchos_policy_profile(
    profile_name: SearchOSProfileName | str,
) -> SearchOSPolicyProfileV1:
    try:
        key = profile_name if isinstance(profile_name, SearchOSProfileName) else SearchOSProfileName(str(profile_name))
    except ValueError as exc:
        raise SearchOSRuntimeError("unsupported SearchOS policy profile") from exc
    return _POLICY_PROFILES[key]


def build_searchos_policy_snapshot(
    *,
    run_id: str,
    request_id: str,
    profile_name: SearchOSProfileName | str,
    navigation_runtime_open: bool = False,
    existing_gap_recovery_runtime_open: bool = False,
) -> dict[str, Any]:
    profile = searchos_policy_profile(profile_name)
    recovery_limits = {
        SearchOSProfileName.FAST: {
            "existing_component_cycles": 1,
            "searched_premise_cycles": 0,
            "total_cycles": 1,
        },
        SearchOSProfileName.BALANCED: {
            "existing_component_cycles": 1,
            "searched_premise_cycles": 1,
            "total_cycles": 2,
        },
        SearchOSProfileName.DEEP: {
            "existing_component_cycles": 1,
            "searched_premise_cycles": 2,
            "total_cycles": 3,
        },
    }[profile.profile_name]
    core = {
        **profile.to_dict(),
        "run_id": _token(run_id, "run_id"),
        "request_id": _token(request_id, "request_id"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "prompt_can_override": False,
        "adapter_can_override": False,
        "environment_can_override": False,
        "existing_gap_recovery_policy": {
            "schema_version": "searchos_existing_gap_recovery_policy_v1",
            "runtime_open": bool(existing_gap_recovery_runtime_open),
            "maximum_cycles_per_run": 1,
            "required_gaps_prioritized": True,
            "optional_gap_recovery_authorized": False,
            "same_limits_for_all_profiles": True,
            "whole_run_lease_required": True,
        },
        "recovery_policy": {
            "schema_version": "searchos_recovery_policy_v2",
            "runtime_open": bool(existing_gap_recovery_runtime_open),
            "maximum_existing_component_cycles_per_run": (
                recovery_limits["existing_component_cycles"]
            ),
            "maximum_searched_premise_cycles_per_run": (
                recovery_limits["searched_premise_cycles"]
            ),
            "maximum_total_cycles_per_run": recovery_limits["total_cycles"],
            "one_linear_active_cycle": True,
            "one_searched_premise_per_generation": True,
            "maximum_searched_generation": 2,
            "generation_three_rejected_before_work": True,
            "whole_run_lease_required": True,
        },
    }
    if navigation_runtime_open:
        core.update(
            navigation_runtime_open=True,
            **_NAVIGATION_LIMITS_BY_PROFILE[profile.profile_name],
        )
    digest = _digest(core)
    return {
        **core,
        "policy_snapshot_id": f"searchos-policy:{digest[:24]}",
        "policy_snapshot_digest": digest,
        "replay_identity": f"searchos-policy:{digest}",
    }


def searchos_policy_snapshot_ref(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    safe = _validated_policy_snapshot(snapshot)
    return {
        "policy_snapshot_id": _token(safe.get("policy_snapshot_id"), "policy_snapshot_id"),
        "policy_snapshot_digest": _digest_token(safe.get("policy_snapshot_digest"), "policy_snapshot_digest"),
        "profile_name": _token(safe.get("profile_name"), "profile_name"),
        "schema_version": SEARCHOS_POLICY_SCHEMA_VERSION,
    }


def build_searchos_initial_state(
    *,
    run_id: str,
    request_id: str,
    answer_contract_ref: Mapping[str, Any],
    policy_snapshot: Mapping[str, Any],
    active_slots: Sequence[Mapping[str, Any]],
    initial_candidate_state_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create canonical Slice A state with explicit required/optional posture."""

    run = _token(run_id, "run_id")
    request = _token(request_id, "request_id")
    contract_ref = _required_ref(answer_contract_ref, "answer_contract_ref")
    policy = _validated_policy_snapshot(policy_snapshot)
    policy_ref = searchos_policy_snapshot_ref(policy)
    initial_candidate_ref = _optional_ref(initial_candidate_state_ref)
    initial_zero_useful_result = bool(
        _mapping(
            initial_candidate_ref.get("zero_result_discover_wave_ref")
        ).get("zero_useful_result")
        is True
    )
    if policy.get("run_id") != run or policy.get("request_id") != request:
        raise SearchOSRuntimeError("SearchOS policy snapshot scope mismatch")
    if not active_slots or len(active_slots) > int(policy["maximum_active_slots"]):
        raise SearchOSRuntimeError("SearchOS active-slot envelope is empty or exceeded")

    slots_by_id: dict[str, dict[str, Any]] = {}
    required_ids: list[str] = []
    optional_ids: list[str] = []
    judgment_eligible_required_ids: list[str] = []
    for ordinal, raw_slot in enumerate(active_slots, start=1):
        slot = _mapping(raw_slot)
        slot_id = _token(slot.get("slot_id"), "slot_id")
        if slot_id in slots_by_id:
            raise SearchOSRuntimeError("duplicate SearchOS slot identity")
        try:
            requirement = SearchOSRequirementPosture(str(slot.get("requirement_posture") or ""))
        except ValueError as exc:
            raise SearchOSRuntimeError("SearchOS slot required-versus-optional posture is ambiguous") from exc
        component_ref = _required_ref(slot.get("component_ref"), "component_ref")
        obligation_ref = _required_ref(slot.get("source_obligation_ref"), "source_obligation_ref")
        supplied_semantic_ref = _mapping(slot.get("semantic_slot_ref"))
        legacy_lineage_defaulted = not bool(supplied_semantic_ref)
        semantic_slot_ref = supplied_semantic_ref or {
            "slot_id": f"{slot_id}:legacy-semantic",
            "slot_kind": "unknown_or_other",
            "status": "explicit",
            "materiality": "material",
            "candidate_values": [],
            "selected_value": None,
            "user_confirmation_required": False,
            "unresolved_material": False,
        }
        if (
            not _bounded_optional(semantic_slot_ref.get("slot_id"), 160)
            or not _bounded_optional(semantic_slot_ref.get("slot_kind"), 80)
            or not _bounded_optional(semantic_slot_ref.get("status"), 80)
        ):
            raise SearchOSRuntimeError(
                "SearchOS slot requires exact semantic-slot lineage"
            )
        query_plan_item_ref = _optional_ref(slot.get("query_plan_item_ref"))
        supplied_job_class = slot.get("discovery_job_class")
        if supplied_job_class is None and legacy_lineage_defaulted:
            supplied_job_class = DiscoveryJobClass.STANDARD_DISCOVERY.value
        clarification_required = bool(
            slot.get("clarification_required")
            or semantic_slot_ref.get("user_confirmation_required") is True
        )
        if clarification_required:
            discovery_job_class = None
        else:
            try:
                discovery_job_class = DiscoveryJobClass(
                    str(supplied_job_class or "")
                )
            except ValueError as exc:
                raise SearchOSRuntimeError(
                    "SearchOS active slot requires a provider-neutral discovery job class"
                ) from exc
            if supplied_job_class is not None and not legacy_lineage_defaulted and not query_plan_item_ref:
                raise SearchOSRuntimeError(
                    "SearchOS discovery slot requires exact QueryPlan item lineage"
                )
        support_kind = _bounded_optional(slot.get("support_kind"), 80)
        initial_posture = (
            SearchOSSlotPosture.CLARIFICATION_REQUIRED
            if clarification_required
            else SearchOSSlotPosture.ACTIVE_UNJUDGED
        )
        slot_core = {
            "slot_id": slot_id,
            "slot_ordinal": ordinal,
            "component_ref": component_ref,
            "source_obligation_ref": obligation_ref,
            "requirement_posture": requirement.value,
            "semantic_slot_ref": deepcopy(semantic_slot_ref),
            "current_query_plan_item_ref": query_plan_item_ref,
            "current_discovery_job_class": (
                discovery_job_class.value
                if discovery_job_class is not None
                else None
            ),
            "posture": initial_posture.value,
            "latest_reason": (
                "accepted_semantic_slot_requires_user_confirmation"
                if clarification_required
                else None
            ),
            "binding_posture": (
                "unbound_required"
                if discovery_job_class is DiscoveryJobClass.ORIENTATION
                else "not_required"
            ),
            "interpretation_binding_ref": {},
            "interpretation_binding_count": 0,
            "orientation_refinement_count": 0,
            "clarification_posture": {
                "clarification_required": clarification_required,
                "component_ref": component_ref,
                "semantic_slot_ref": deepcopy(semantic_slot_ref),
                "declared_candidates": list(
                    semantic_slot_ref.get("candidate_values") or ()
                ),
                "reason": (
                    "accepted_semantic_slot_requires_user_confirmation"
                    if clarification_required
                    else None
                ),
            },
            "current_candidate_state_ref": _optional_ref(initial_candidate_state_ref),
            "current_candidate_zero_useful_result": (
                initial_zero_useful_result
            ),
            "current_window_ref": {},
            "candidate_use_option_refs": [],
            "candidate_option_dispositions": {},
            "custody_refs": [],
            "semantic_handoff_refs": [],
            "action_history": [],
            "judgment_call_count": 0,
            "candidate_window_count": 0,
            "candidate_wave_count": 1,
            "read_nomination_count": 0,
            "followup_query_nomination_count": 0,
            "satisfaction_claimed": False,
            "coverage_upgrade_claimed": False,
            "legacy_uncertainty_lineage_defaulted": legacy_lineage_defaulted,
        }
        if support_kind:
            slot_core["support_kind"] = support_kind
        if policy.get("navigation_runtime_open") is True:
            slot_core.update(
                {
                    "pending_navigation_decision_ref": {},
                    "pending_navigation_candidate_ref": {},
                    "navigation_selection_count": 0,
                    "navigation_availability_reason": None,
                }
            )
        slot_identity_digest = _digest(
            {
                "slot_id": slot_id,
                "component_ref": component_ref,
                "source_obligation_ref": obligation_ref,
                "semantic_slot_ref": semantic_slot_ref,
                "current_query_plan_item_ref": query_plan_item_ref,
                "current_discovery_job_class": (
                    discovery_job_class.value
                    if discovery_job_class is not None
                    else None
                ),
                "requirement_posture": requirement.value,
            }
        )
        slot_core["slot_ref"] = {
            "slot_id": slot_id,
            "slot_digest": slot_identity_digest,
            "component_id": _first_ref_id(component_ref),
            "source_obligation_id": _first_ref_id(obligation_ref),
            "component_ref": deepcopy(component_ref),
            "source_obligation_ref": deepcopy(obligation_ref),
            "semantic_slot_ref": deepcopy(semantic_slot_ref),
            "query_plan_item_ref": deepcopy(query_plan_item_ref),
            "discovery_job_class": (
                discovery_job_class.value
                if discovery_job_class is not None
                else None
            ),
        }
        slot_core["slot_state_digest"] = _digest(slot_core)
        slots_by_id[slot_id] = slot_core
        (required_ids if requirement is SearchOSRequirementPosture.REQUIRED else optional_ids).append(slot_id)
        if (
            requirement is SearchOSRequirementPosture.REQUIRED
            and not clarification_required
        ):
            judgment_eligible_required_ids.append(slot_id)

    reserved_per_required = int(policy["minimum_reserved_judgment_calls_per_required_slot"])
    shared_pool = len(slots_by_id) * int(policy["additional_judgment_call_pool_per_active_slot"])
    budget = {
        "judgment_call_ceiling": (
            len(judgment_eligible_required_ids) * reserved_per_required
            + shared_pool
        ),
        "reserved_calls_remaining_by_required_slot": {
            slot_id: reserved_per_required
            for slot_id in judgment_eligible_required_ids
        },
        "shared_calls_remaining": shared_pool,
        "charged_logical_judgment_calls": 0,
        "failed_logical_judgment_calls": 0,
        "returned_pre_call_reservations": 0,
        "round_history": [],
        "charge_history": [],
    }
    state_core = {
        "schema_version": SEARCHOS_STATE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": run,
        "request_id": request,
        "answer_contract_ref": contract_ref,
        "policy_snapshot_ref": policy_ref,
        "policy_snapshot": deepcopy(dict(policy)),
        "slots_by_id": slots_by_id,
        "active_slot_ids": list(slots_by_id),
        "required_slot_ids": required_ids,
        "judgment_eligible_required_slot_ids": judgment_eligible_required_ids,
        "optional_slot_ids": optional_ids,
        "initial_candidate_state_ref": deepcopy(initial_candidate_ref),
        "current_candidate_state_ref": deepcopy(initial_candidate_ref),
        "iteration_candidate_set_refs": [],
        "budget": budget,
        "semantic_handoff_refs": [],
        "interpretation_binding_history": [],
        "readiness_projection_ref": {},
        "required_needs_block_ref": {},
        "required_needs_block": {},
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "known_url_read_runtime_open": False,
        "search_attached_content_custody_runtime_open": False,
        "comprehensive_recovery_runtime_open": False,
        "whole_run_stopping_runtime_open": False,
        "existing_gap_recovery_runtime_open": (
            _mapping(policy.get("existing_gap_recovery_policy")).get(
                "runtime_open"
            )
            is True
        ),
        "existing_gap_recovery_purpose_refs": [],
        "existing_gap_recovery_lease_refs": [],
        "existing_gap_recovery_cycles": [],
        "active_existing_gap_recovery_cycle_ref": {},
        "existing_gap_recovery_terminal_aggregate_ref": {},
        "existing_gap_recovery_terminal_aggregate": {},
        "recovery_lease": {},
        "recovery_lease_history": [],
        "recovery_cycle_admission_history": [],
        "recovery_cycle_terminal_history": [],
        "active_recovery_cycle_ref": {},
        "recovery_expenditure_history": [],
        "recovery_terminal_aggregate": {},
    }
    if policy.get("navigation_runtime_open") is True:
        state_core["navigation"] = {"options_by_id": {}, "edges": []}
    return _with_state_digest(state_core)


def build_searchos_revision_1_candidate_state_v1(
    *,
    run_id: str,
    request_id: str,
    candidate_packet_ref: Mapping[str, Any] | None = None,
    zero_result_discover_wave_ref: Mapping[str, Any] | None = None,
    initial_query_plan_ref: Mapping[str, Any],
    initial_query_plan_items: Sequence[Mapping[str, Any]],
    initial_identity_set_ref: Mapping[str, Any],
    initial_identity_refs: Sequence[Mapping[str, Any]],
    selected_candidate_refs: Sequence[Mapping[str, Any]],
    bounded_candidate_material_refs: Sequence[Mapping[str, Any]],
    selection_facts: Mapping[str, Any],
    overflow_facts: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the immediate post-first-DISCOVER candidate snapshot."""

    query_items = [deepcopy(_mapping(item)) for item in initial_query_plan_items]
    identities = [deepcopy(_mapping(item)) for item in initial_identity_refs]
    selected = [_required_ref(item, "selected_candidate_ref") for item in selected_candidate_refs]
    packet_ref = _mapping(candidate_packet_ref)
    zero_result_ref = _mapping(zero_result_discover_wave_ref)
    if bool(packet_ref) == bool(zero_result_ref):
        raise SearchOSRuntimeError(
            "revision 1 requires exactly one candidate packet or zero-result wave ref"
        )
    if not query_items:
        raise SearchOSRuntimeError(
            "revision 1 requires admitted QueryPlan identity"
        )
    if packet_ref and (not identities or not selected):
        raise SearchOSRuntimeError(
            "candidate-bearing revision 1 requires identity and candidate refs"
        )
    if zero_result_ref and (
        identities
        or selected
        or _mapping(selection_facts).get("zero_useful_result") is not True
    ):
        raise SearchOSRuntimeError(
            "zero-result revision 1 must preserve an empty identity/candidate set"
        )
    core = {
        "schema_version": SEARCHOS_REVISION_1_CANDIDATE_STATE_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": _token(run_id, "run_id"),
        "request_id": _token(request_id, "request_id"),
        "revision": 1,
        "candidate_packet_ref": (
            _required_ref(packet_ref, "candidate_packet_ref")
            if packet_ref
            else {}
        ),
        "zero_result_discover_wave_ref": (
            _required_ref(
                zero_result_ref,
                "zero_result_discover_wave_ref",
            )
            if zero_result_ref
            else {}
        ),
        "initial_query_plan_ref": _required_ref(initial_query_plan_ref, "initial_query_plan_ref"),
        "initial_query_plan_items_digest": _digest(query_items),
        "initial_query_plan_item_count": len(query_items),
        "initial_identity_set_ref": _required_ref(initial_identity_set_ref, "initial_identity_set_ref"),
        "initial_identity_refs_digest": _digest(identities),
        "initial_identity_count": len(identities),
        "selected_candidate_refs": selected,
        "bounded_candidate_material_refs": [
            _required_ref(item, "candidate_material_ref") for item in bounded_candidate_material_refs
        ],
        "selection_facts": _json_mapping(selection_facts),
        "overflow_facts": _json_mapping(overflow_facts),
        "created_immediately_after_first_admitted_discover_wave": True,
        "byte_immutable": True,
        "digest_immutable": True,
        "append_only_parent": True,
        "raw_store_visibility_allowed": False,
        "read_authority_created": False,
        "semantic_authority_created": False,
        "support_authority_created": False,
        "canonical_state": True,
    }
    digest = _digest(core)
    return {
        **core,
        "candidate_state_id": f"searchos-revision-1:{digest[:24]}",
        "candidate_state_digest": digest,
        "replay_identity": f"searchos-revision-1:{digest}",
    }


def validate_searchos_revision_1_candidate_state(
    revision_1: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _mapping(revision_1)
    _require_schema(
        safe,
        SEARCHOS_REVISION_1_CANDIDATE_STATE_SCHEMA_VERSION,
        "SearchOS revision 1",
    )
    claimed = _digest_token(safe.get("candidate_state_digest"), "candidate_state_digest")
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key not in {"candidate_state_id", "candidate_state_digest", "replay_identity"}
    }
    if _digest(core) != claimed:
        raise SearchOSRuntimeError("revision 1 candidate state digest mismatch")
    if (
        safe.get("candidate_state_id") != f"searchos-revision-1:{claimed[:24]}"
        or safe.get("replay_identity") != f"searchos-revision-1:{claimed}"
    ):
        raise SearchOSRuntimeError("revision 1 candidate state identity mismatch")
    if safe.get("revision") != 1 or safe.get("byte_immutable") is not True or safe.get("digest_immutable") is not True:
        raise SearchOSRuntimeError("revision 1 immutability posture is invalid")
    return deepcopy(safe)


def searchos_revision_1_candidate_state_ref(
    revision_1: Mapping[str, Any],
) -> dict[str, Any]:
    safe = validate_searchos_revision_1_candidate_state(revision_1)
    return {
        "candidate_state_id": safe["candidate_state_id"],
        "candidate_state_digest": safe["candidate_state_digest"],
        "revision": 1,
        "candidate_packet_ref": deepcopy(safe["candidate_packet_ref"]),
        "zero_result_discover_wave_ref": deepcopy(
            safe.get("zero_result_discover_wave_ref") or {}
        ),
        "schema_version": SEARCHOS_REVISION_1_CANDIDATE_STATE_SCHEMA_VERSION,
    }


def begin_searchos_judgment_round(
    state: Mapping[str, Any], *, slot_ids: Sequence[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reserve one call for every participating required slot before the round."""

    candidate = _validated_state_copy(state)
    ordered_ids = [_token(item, "slot_id") for item in slot_ids]
    if not ordered_ids or len(set(ordered_ids)) != len(ordered_ids):
        raise SearchOSRuntimeError("judgment round requires unique participating slots")
    slots = _mapping(candidate["slots_by_id"])
    if any(slot_id not in slots for slot_id in ordered_ids):
        raise SearchOSRuntimeError("judgment round contains an inactive slot")
    budget = _mutable_mapping(candidate["budget"])
    remaining = _mutable_mapping(budget["reserved_calls_remaining_by_required_slot"])
    required = set(candidate["required_slot_ids"])
    outstanding = {
        str(item.get("slot_id") or "")
        for round_record in budget["round_history"]
        for item in round_record.get("required_slot_reservations") or ()
        if item.get("charged") is not True and item.get("returned") is not True
    }
    if outstanding & set(ordered_ids):
        raise SearchOSRuntimeError("judgment round overlaps an outstanding required-slot reservation")
    shared_needed = sum(1 for slot_id in ordered_ids if slot_id in required and int(remaining.get(slot_id) or 0) <= 0)
    unavailable = (
        [slot_id for slot_id in ordered_ids if slot_id in required and int(remaining.get(slot_id) or 0) <= 0]
        if int(budget["shared_calls_remaining"]) < shared_needed
        else []
    )
    if unavailable:
        raise SearchOSRuntimeError(
            "complete-round reservation unavailable for required slot(s): " + ",".join(unavailable)
        )
    budget["shared_calls_remaining"] = int(budget["shared_calls_remaining"]) - shared_needed
    round_ordinal = len(budget["round_history"]) + 1
    reservation_core = {
        "schema_version": "searchos_judgment_round_reservation_v1",
        "round_ordinal": round_ordinal,
        "participating_slot_ids": ordered_ids,
        "required_slot_reservations": [
            {
                "slot_id": slot_id,
                "capacity_source": ("required_slot_reserve" if int(remaining.get(slot_id) or 0) > 0 else "shared_pool"),
                "charged": False,
                "returned": False,
            }
            for slot_id in ordered_ids
            if slot_id in required
        ],
        "complete_round_reserved_before_first_call": True,
    }
    reservation_digest = _digest(reservation_core)
    reservation = {
        **reservation_core,
        "reservation_id": f"searchos-round:{reservation_digest[:24]}",
        "reservation_digest": reservation_digest,
        "replay_identity": f"searchos-round:{reservation_digest}",
    }
    budget["round_history"].append(reservation)
    candidate["budget"] = budget
    return _refresh_state(candidate), deepcopy(reservation)


def return_searchos_pre_call_reservation(
    state: Mapping[str, Any],
    *,
    reservation_ref: Mapping[str, Any],
    slot_id: str,
    reason: str,
) -> dict[str, Any]:
    """Release a required-slot hold when work is rejected before model call."""

    candidate = _validated_state_copy(state)
    slot_token = _token(slot_id, "slot_id")
    budget = _mutable_mapping(candidate["budget"])
    reservation = _required_ref(reservation_ref, "reservation_ref")
    round_id = _token(reservation.get("reservation_id"), "reservation_id")
    reservation_digest = _digest_token(reservation.get("reservation_digest"), "reservation_digest")
    if (
        round_id != f"searchos-round:{reservation_digest[:24]}"
        or reservation.get("replay_identity") != f"searchos-round:{reservation_digest}"
    ):
        raise SearchOSRuntimeError("pre-call return reservation identity is invalid")
    history = list(budget["round_history"])
    round_index = next(
        (index for index, item in enumerate(history) if item.get("reservation_id") == round_id),
        None,
    )
    if round_index is None:
        raise SearchOSRuntimeError("pre-call return reservation is stale")
    round_record = deepcopy(history[round_index])
    if reservation.get("reservation_digest") != round_record.get("reservation_digest"):
        raise SearchOSRuntimeError("pre-call return reservation was altered")
    if slot_token not in round_record["participating_slot_ids"]:
        raise SearchOSRuntimeError("pre-call return slot was not reserved")
    required_record = next(
        (item for item in round_record["required_slot_reservations"] if item.get("slot_id") == slot_token),
        None,
    )
    if required_record is not None:
        if required_record.get("charged") is True:
            raise SearchOSRuntimeError("charged judgment capacity cannot be returned")
        if required_record.get("returned") is True:
            raise SearchOSRuntimeError("judgment capacity was already returned")
        required_record["returned"] = True
        required_record["return_reason"] = _bounded_reason(reason)
        if required_record.get("capacity_source") == "shared_pool":
            budget["shared_calls_remaining"] = int(budget["shared_calls_remaining"]) + 1
        budget["returned_pre_call_reservations"] = int(budget["returned_pre_call_reservations"]) + 1
    else:
        rejected = list(round_record.get("optional_pre_call_rejections") or ())
        rejected.append(
            {
                "slot_id": slot_token,
                "reason": _bounded_reason(reason),
            }
        )
        round_record["optional_pre_call_rejections"] = rejected
    history[round_index] = round_record
    budget["round_history"] = history
    candidate["budget"] = budget
    return _refresh_state(candidate)


def charge_searchos_judgment_call(
    state: Mapping[str, Any], *, reservation_ref: Mapping[str, Any], slot_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Charge capacity exactly when a logical model judgment call begins."""

    candidate = _validated_state_copy(state)
    slot_token = _token(slot_id, "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_token not in slots:
        raise SearchOSRuntimeError("judgment charge references an inactive slot")
    budget = _mutable_mapping(candidate["budget"])
    reservation = _required_ref(reservation_ref, "reservation_ref")
    round_id = _token(reservation.get("reservation_id"), "reservation_id")
    reservation_digest = _digest_token(reservation.get("reservation_digest"), "reservation_digest")
    if (
        round_id != f"searchos-round:{reservation_digest[:24]}"
        or reservation.get("replay_identity") != f"searchos-round:{reservation_digest}"
    ):
        raise SearchOSRuntimeError("judgment charge reservation identity is invalid")
    history = list(budget["round_history"])
    round_index = next(
        (index for index, item in enumerate(history) if item.get("reservation_id") == round_id),
        None,
    )
    if round_index is None:
        raise SearchOSRuntimeError("judgment charge reservation is stale")
    round_record = deepcopy(history[round_index])
    if reservation.get("reservation_digest") != round_record.get("reservation_digest"):
        raise SearchOSRuntimeError("judgment charge reservation was altered")
    if slot_token not in round_record["participating_slot_ids"]:
        raise SearchOSRuntimeError("judgment charge slot was not reserved in this round")
    returned = next(
        (
            item
            for item in round_record["required_slot_reservations"]
            if item.get("slot_id") == slot_token and item.get("returned") is True
        ),
        None,
    )
    if returned is not None:
        raise SearchOSRuntimeError("returned judgment reservation cannot be charged")
    if any(item.get("slot_id") == slot_token and item.get("charged") is True for item in budget["charge_history"]):
        # Multiple rounds are legal, so reject only a duplicate charge for this round.
        if any(
            item.get("slot_id") == slot_token and item.get("reservation_id") == round_id
            for item in budget["charge_history"]
        ):
            raise SearchOSRuntimeError("judgment reservation was already charged")

    required = slot_token in set(candidate["required_slot_ids"])
    remaining = _mutable_mapping(budget["reserved_calls_remaining_by_required_slot"])
    reservation_record = next(
        (item for item in round_record["required_slot_reservations"] if item.get("slot_id") == slot_token),
        None,
    )
    capacity_source = (
        str(reservation_record.get("capacity_source")) if reservation_record is not None else "shared_pool"
    )
    if required and capacity_source == "required_slot_reserve":
        if int(remaining.get(slot_token) or 0) <= 0:
            raise SearchOSRuntimeError("required-slot reservation capacity became stale")
        remaining[slot_token] = int(remaining[slot_token]) - 1
    elif not required:
        shared = int(budget["shared_calls_remaining"])
        if shared <= 0:
            raise SearchOSRuntimeError("SearchOS logical judgment budget exhausted")
        budget["shared_calls_remaining"] = shared - 1
    for item in round_record["required_slot_reservations"]:
        if item.get("slot_id") == slot_token:
            item["charged"] = True
    history[round_index] = round_record
    budget["round_history"] = history
    budget["reserved_calls_remaining_by_required_slot"] = remaining
    budget["charged_logical_judgment_calls"] = int(budget["charged_logical_judgment_calls"]) + 1
    charge_core = {
        "schema_version": "searchos_judgment_call_charge_v1",
        "reservation_id": round_id,
        "slot_id": slot_token,
        "logical_call_ordinal": budget["charged_logical_judgment_calls"],
        "capacity_source": capacity_source,
        "call_began": True,
        "successful_capacity_created": False,
    }
    charge_digest = _digest(charge_core)
    charge = {
        **charge_core,
        "charge_id": f"searchos-charge:{charge_digest[:24]}",
        "charge_digest": charge_digest,
        "replay_identity": f"searchos-charge:{charge_digest}",
    }
    budget["charge_history"].append(charge)
    slot = deepcopy(slots[slot_token])
    slot["judgment_call_count"] = int(slot["judgment_call_count"]) + 1
    slots[slot_token] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    candidate["budget"] = budget
    return _refresh_state(candidate), deepcopy(charge)


def record_searchos_judgment_failure(
    state: Mapping[str, Any], *, charge_ref: Mapping[str, Any], reason: str
) -> dict[str, Any]:
    """Record model unavailability/malformed output without a semantic fallback."""

    candidate = _validated_state_copy(state)
    supplied_charge = _required_ref(charge_ref, "charge_ref")
    charge_id = _token(supplied_charge.get("charge_id"), "charge_id")
    budget = _mutable_mapping(candidate["budget"])
    charge = next(
        (item for item in budget["charge_history"] if item.get("charge_id") == charge_id),
        None,
    )
    if not charge:
        raise SearchOSRuntimeError("judgment failure charge is stale")
    if _compact_ref(supplied_charge) != _compact_ref(charge):
        raise SearchOSRuntimeError("judgment failure charge was altered")
    slot_id = _token(charge.get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    slot = deepcopy(slots[slot_id])
    slot["posture"] = SearchOSSlotPosture.JUDGMENT_FAILED.value
    slot["latest_reason"] = _bounded_reason(reason)
    slot["action_history"].append(
        {
            "event": "judgment_failed",
            "charge_ref": _compact_ref(charge),
            "reason": slot["latest_reason"],
            "deterministic_semantic_fallback_invoked": False,
        }
    )
    slots[slot_id] = _refresh_slot(slot)
    budget["failed_logical_judgment_calls"] = int(budget["failed_logical_judgment_calls"]) + 1
    candidate["slots_by_id"] = slots
    candidate["budget"] = budget
    return _refresh_state(candidate)


def mark_searchos_slot_budget_exhausted(state: Mapping[str, Any], *, slot_id: str, reason: str) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    slots = _mutable_mapping(candidate["slots_by_id"])
    token = _token(slot_id, "slot_id")
    if token not in slots:
        raise SearchOSRuntimeError("budget exhaustion references inactive slot")
    slot = deepcopy(slots[token])
    slot["posture"] = SearchOSSlotPosture.BUDGET_EXHAUSTED.value
    slot["latest_reason"] = _bounded_reason(reason)
    slot["action_history"].append(
        {
            "event": "budget_exhausted",
            "reason": slot["latest_reason"],
            "satisfaction_claimed": False,
        }
    )
    slots[token] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def mark_searchos_slot_unresolved(state: Mapping[str, Any], *, slot_id: str, reason: str) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    slots = _mutable_mapping(candidate["slots_by_id"])
    token = _token(slot_id, "slot_id")
    if token not in slots:
        raise SearchOSRuntimeError("unresolved handoff references inactive slot")
    slot = deepcopy(slots[token])
    slot["posture"] = SearchOSSlotPosture.UNRESOLVED_HANDOFF.value
    slot["latest_reason"] = _bounded_reason(reason)
    slot["action_history"].append(
        {
            "event": "HANDOFF_UNRESOLVED",
            "reason": slot["latest_reason"],
            "satisfaction_claimed": False,
        }
    )
    slots[token] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def mark_searchos_slot_stale_or_invalid(state: Mapping[str, Any], *, slot_id: str, reason: str) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    slots = _mutable_mapping(candidate["slots_by_id"])
    token = _token(slot_id, "slot_id")
    if token not in slots:
        raise SearchOSRuntimeError("stale nomination references inactive slot")
    slot = deepcopy(slots[token])
    slot["posture"] = SearchOSSlotPosture.STALE_OR_INVALID.value
    slot["latest_reason"] = _bounded_reason(reason)
    slot["action_history"].append(
        {
            "event": "stale_or_invalid",
            "reason": slot["latest_reason"],
            "deterministic_semantic_fallback_invoked": False,
            "satisfaction_claimed": False,
        }
    )
    slots[token] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def record_searchos_iteration_candidate_set(
    state: Mapping[str, Any], *, candidate_set: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    admitted = validate_searchos_iteration_candidate_set(candidate_set)
    if admitted.get("run_id") != candidate.get("run_id") or admitted.get("request_id") != candidate.get("request_id"):
        raise SearchOSRuntimeError("iteration candidate set scope mismatch")
    slot_id = _token(_mapping(admitted.get("active_slot_ref")).get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_id not in slots:
        raise SearchOSRuntimeError("iteration candidate set references inactive slot")
    slot = deepcopy(slots[slot_id])
    if _mapping(admitted.get("active_slot_ref")) != _mapping(
        slot.get("slot_ref")
    ):
        raise SearchOSRuntimeError(
            "iteration candidate set active-slot lineage is stale or altered"
        )
    if _mapping(admitted.get("parent_candidate_state_ref")) != _mapping(
        slot.get("current_candidate_state_ref")
    ):
        raise SearchOSRuntimeError(
            "iteration candidate set slot-local parent became stale"
        )
    if slot.get("posture") != (SearchOSSlotPosture.AWAITING_FOLLOWUP_DISCOVER.value):
        raise SearchOSRuntimeError("iteration candidate set does not follow an authorized follow-up")
    query_plan_item_ref = _required_ref(
        admitted.get("query_plan_item_ref"),
        "query_plan_item_ref",
    )
    admitted_job_class = query_plan_item_ref.get("discovery_job_class")
    pending_job_class = slot.get("pending_discovery_job_class")
    if slot.get("legacy_uncertainty_lineage_defaulted") is not True:
        try:
            admitted_job = DiscoveryJobClass(str(admitted_job_class or ""))
        except ValueError as exc:
            raise SearchOSRuntimeError(
                "follow-up candidate set lacks provider-neutral job lineage"
            ) from exc
        if admitted_job.value != pending_job_class:
            raise SearchOSRuntimeError(
                "follow-up candidate set job class is stale or altered"
            )
        admitted_component_ref = _mapping(
            query_plan_item_ref.get("component_ref")
        )
        admitted_semantic_ref = _mapping(
            query_plan_item_ref.get("semantic_slot_ref")
        )
        if (
            _first_ref_id(admitted_component_ref)
            != _first_ref_id(_mapping(slot.get("component_ref")))
            or admitted_semantic_ref
            != _mapping(slot.get("semantic_slot_ref"))
        ):
            raise SearchOSRuntimeError(
                "follow-up QueryPlan item crossed component or semantic-slot lineage"
            )
    else:
        admitted_job = DiscoveryJobClass(
            str(
                admitted_job_class
                or pending_job_class
                or slot.get("current_discovery_job_class")
            )
        )
    policy = _mapping(candidate["policy_snapshot"])
    if int(slot["candidate_wave_count"]) >= int(policy["candidate_waves_per_slot"]):
        return mark_searchos_slot_budget_exhausted(
            candidate,
            slot_id=slot_id,
            reason="candidate_wave_budget_exhausted",
        )
    ref = searchos_iteration_candidate_set_ref(admitted)
    slot["candidate_wave_count"] = int(slot["candidate_wave_count"]) + 1
    slot["candidate_window_count"] = 0
    slot["current_window_ref"] = {}
    slot["candidate_use_option_refs"] = []
    slot["current_candidate_state_ref"] = ref
    slot["current_candidate_zero_useful_result"] = bool(
        admitted.get("zero_useful_result")
    )
    slot["current_query_plan_item_ref"] = query_plan_item_ref
    slot["current_discovery_job_class"] = admitted_job.value
    slot.pop("pending_discovery_job_class", None)
    slot["posture"] = SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    slot["latest_reason"] = (
        "followup_discover_zero_useful_result"
        if admitted.get("zero_useful_result") is True
        else "followup_discover_candidate_state_admitted"
    )
    slot["action_history"].append(
        {
            "event": "iteration_candidate_set_admitted",
            "iteration_candidate_set_ref": ref,
            "zero_useful_result": bool(admitted.get("zero_useful_result")),
        }
    )
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    candidate["iteration_candidate_set_refs"].append(ref)
    # This state-level ref is an append-order head only. Slot-local refs remain
    # the authority for candidate cursors and are never overwritten by peers.
    candidate["current_candidate_state_ref"] = ref
    return _refresh_state(candidate)


def record_searchos_read_custody_material(
    state: Mapping[str, Any], *, custody_material_ref: Mapping[str, Any]
) -> dict[str, Any]:
    """Register exact post-READ EvidenceLedger custody and reopen judgment."""

    candidate = _validated_state_copy(state)
    custody = _validated_read_custody_material_ref(custody_material_ref)
    if custody.get("material_authority") != (SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value):
        raise SearchOSRuntimeError("DISCOVER material cannot register as READ custody")
    if custody.get("readable") is not True or custody.get("stale") is True:
        raise SearchOSRuntimeError("READ custody material is unreadable or stale")
    if not _optional_ref(custody.get("evidence_ledger_custody_ref")):
        raise SearchOSRuntimeError("SearchOS READ material requires EvidenceLedger custody")
    option_ref = _required_ref(custody.get("candidate_use_option_ref"), "candidate_use_option_ref")
    slot_ref = _required_ref(custody.get("slot_ref"), "slot_ref")
    slot_id = _token(slot_ref.get("slot_id"), "slot_id")
    if option_ref.get("slot_id") != slot_id:
        raise SearchOSRuntimeError("READ custody option and slot lineage mismatch")
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_id not in slots or _mapping(slots[slot_id].get("slot_ref")) != slot_ref:
        raise SearchOSRuntimeError("READ custody slot lineage is stale")
    slot = deepcopy(slots[slot_id])
    if slot.get("posture") != SearchOSSlotPosture.AWAITING_READ.value:
        raise SearchOSRuntimeError("READ custody does not follow REQUEST_READ_PAGE")
    existing = {_first_ref_id(item): item for item in slot.get("custody_refs") or ()}
    custody_id = _first_ref_id(custody)
    if custody_id not in existing:
        slot["custody_refs"].append(deepcopy(custody))
    elif existing[custody_id] != custody:
        raise SearchOSRuntimeError("READ custody identity collision")
    slot["posture"] = SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    option_id = _first_ref_id(option_ref)
    dispositions = dict(slot.get("candidate_option_dispositions") or {})
    dispositions[option_id] = {
        "candidate_use_option_id": option_id,
        "candidate_use_option_digest": option_ref.get("candidate_use_option_digest"),
        "disposition": "custodied",
        "read_custody_ref": deepcopy(custody),
    }
    slot["candidate_option_dispositions"] = dispositions
    slot["latest_reason"] = "read_custody_admitted_for_rejudgment"
    slot["action_history"].append(
        {
            "event": "read_custody_admitted",
            "read_custody_ref": _compact_ref(custody),
            "same_normalized_url_reused": bool(custody.get("same_normalized_url_reused")),
            "support_admitted": False,
        }
    )
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def build_searchos_read_custody_material_ref(
    *,
    slot_ref: Mapping[str, Any],
    candidate_use_option_ref: Mapping[str, Any],
    custody_record: Mapping[str, Any],
    same_normalized_url_reused: bool,
) -> dict[str, Any]:
    slot = _required_ref(slot_ref, "slot_ref")
    option = _required_ref(candidate_use_option_ref, "candidate_use_option_ref")
    custody = _mapping(custody_record)
    normalized_url = normalize_discovery_result_url(custody.get("normalized_url") or option.get("normalized_url"))
    if option.get("slot_id") != slot.get("slot_id"):
        raise SearchOSRuntimeError("READ custody option does not bind the active slot")
    packet_ref = _required_ref(
        custody.get("fetch_read_content_packet_ref"),
        "fetch_read_content_packet_ref",
    )
    ledger_ref = _required_ref(
        custody.get("evidence_ledger_custody_ref"),
        "evidence_ledger_custody_ref",
    )
    core = {
        "schema_version": "searchos_read_custody_material_ref_v1",
        "owner": SEARCHOS_OWNER,
        "slot_ref": slot,
        "candidate_use_option_ref": option,
        "normalized_url": normalized_url,
        "fetch_read_content_packet_ref": packet_ref,
        "evidence_ledger_custody_ref": ledger_ref,
        "evidence_ledger_candidate_id": _token(
            custody.get("evidence_ledger_candidate_id"),
            "evidence_ledger_candidate_id",
        ),
        "terminal_receipt_ref": _required_ref(custody.get("terminal_receipt_ref"), "terminal_receipt_ref"),
        "custody_authorization_ref": _required_ref(
            custody.get("custody_authorization_ref"),
            "custody_authorization_ref",
        ),
        "material_authority": SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value,
        "readable": custody.get("bounded_content_present") is True,
        "bounded_retention": True,
        "stale": False,
        "same_normalized_url_reused": bool(same_normalized_url_reused),
        "component_analyst_proposal_eligible": True,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
    }
    digest = _digest(core)
    return {
        **core,
        "read_custody_material_id": f"searchos-read-custody:{digest[:24]}",
        "read_custody_material_digest": digest,
        "replay_identity": f"searchos-read-custody:{digest}",
    }


def record_searchos_readiness_projection(state: Mapping[str, Any], *, readiness: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = _mapping(readiness)
    _require_schema(safe, SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION, "Slice A readiness")
    if safe.get("run_id") != candidate.get("run_id") or safe.get("request_id") != candidate.get("request_id"):
        raise SearchOSRuntimeError("Slice A readiness scope mismatch")
    claimed = _digest_token(safe.get("readiness_projection_digest"), "readiness_projection_digest")
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key
        not in {
            "readiness_projection_id",
            "readiness_projection_digest",
            "replay_identity",
        }
    }
    if _digest(core) != claimed:
        raise SearchOSRuntimeError("Slice A readiness digest mismatch")
    if (
        safe.get("readiness_projection_id") != (f"searchos-readiness:{claimed[:24]}")
        or safe.get("replay_identity") != f"searchos-readiness:{claimed}"
    ):
        raise SearchOSRuntimeError("Slice A readiness identity mismatch")
    candidate["readiness_projection_ref"] = {
        "readiness_projection_id": safe["readiness_projection_id"],
        "readiness_projection_digest": claimed,
    }
    return _refresh_state(candidate)


def record_searchos_required_needs_block(state: Mapping[str, Any], *, block: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = validate_searchos_required_needs_block(
        block,
        state=candidate,
    )
    readiness_ref = _required_ref(safe.get("readiness_projection_ref"), "readiness_projection_ref")
    if readiness_ref != _mapping(candidate.get("readiness_projection_ref")):
        raise SearchOSRuntimeError("required-needs block readiness ref is stale")
    claimed = _digest_token(safe.get("block_digest"), "block_digest")
    candidate["required_needs_block_ref"] = {
        "block_id": safe["block_id"],
        "block_digest": claimed,
        "block_type": safe["block_type"],
    }
    candidate["required_needs_block"] = deepcopy(safe)
    return _refresh_state(candidate)


def validate_searchos_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return _validated_state_copy(state)


def build_searchos_iteration_candidate_set_v1(
    *,
    run_id: str,
    request_id: str,
    iteration: int,
    parent_candidate_state_ref: Mapping[str, Any],
    slot_ref: Mapping[str, Any],
    query_plan_item_ref: Mapping[str, Any],
    provider_plan_ref: Mapping[str, Any],
    route_refs: Sequence[Mapping[str, Any]],
    retrieval_action_refs: Sequence[Mapping[str, Any]],
    ordered_provider_result_occurrence_refs: Sequence[Mapping[str, Any]],
    identity_set_delta_ref: Mapping[str, Any],
    selected_candidate_refs: Sequence[Mapping[str, Any]],
    bounded_candidate_material_refs: Sequence[Mapping[str, Any]],
    selection_facts: Mapping[str, Any],
    overflow_facts: Mapping[str, Any],
    zero_useful_result: bool,
) -> dict[str, Any]:
    if int(iteration) < 2:
        raise SearchOSRuntimeError("iteration candidate set requires iteration >= 2")
    selected = [_required_ref(item, "selected_candidate_ref") for item in selected_candidate_refs]
    occurrences = [
        _required_ref(item, "provider_result_occurrence_ref") for item in ordered_provider_result_occurrence_refs
    ]
    if bool(zero_useful_result) == bool(selected):
        raise SearchOSRuntimeError("iteration candidate set zero-useful-result posture is contradictory")
    core = {
        "schema_version": SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": _token(run_id, "run_id"),
        "request_id": _token(request_id, "request_id"),
        "iteration": int(iteration),
        "parent_candidate_state_ref": _required_ref(parent_candidate_state_ref, "parent_candidate_state_ref"),
        "active_slot_ref": _required_ref(slot_ref, "slot_ref"),
        "query_plan_item_ref": _required_ref(query_plan_item_ref, "query_plan_item_ref"),
        "provider_plan_ref": _required_ref(provider_plan_ref, "provider_plan_ref"),
        "route_refs": [_required_ref(item, "route_ref") for item in route_refs],
        "retrieval_action_refs": [_required_ref(item, "retrieval_action_ref") for item in retrieval_action_refs],
        "ordered_provider_result_occurrence_refs": occurrences,
        "identity_set_delta_ref": _required_ref(identity_set_delta_ref, "identity_set_delta_ref"),
        "selected_candidate_refs": selected,
        "bounded_candidate_material_refs": [
            _required_ref(item, "candidate_material_ref") for item in bounded_candidate_material_refs
        ],
        "selection_facts": _json_mapping(selection_facts),
        "overflow_facts": _json_mapping(overflow_facts),
        "zero_useful_result": bool(zero_useful_result),
        "raw_store_visibility_allowed": False,
        "read_authority_created": False,
        "semantic_authority_created": False,
        "support_authority_created": False,
        "canonical_state": True,
        "append_only": True,
    }
    digest = _digest(core)
    return {
        **core,
        "iteration_candidate_set_id": f"searchos-iteration:{iteration}:{digest[:20]}",
        "iteration_candidate_set_digest": digest,
        "replay_identity": f"searchos-iteration:{digest}",
    }


def searchos_iteration_candidate_set_ref(candidate_set: Mapping[str, Any]) -> dict[str, Any]:
    safe = validate_searchos_iteration_candidate_set(candidate_set)
    return {
        "iteration_candidate_set_id": safe["iteration_candidate_set_id"],
        "iteration_candidate_set_digest": safe["iteration_candidate_set_digest"],
        "iteration": safe["iteration"],
        "schema_version": SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION,
    }


def validate_searchos_iteration_candidate_set(candidate_set: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(candidate_set)
    _require_schema(
        safe,
        SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION,
        "SearchOS iteration candidate set",
    )
    claimed = _digest_token(
        safe.get("iteration_candidate_set_digest"),
        "iteration_candidate_set_digest",
    )
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key
        not in {
            "iteration_candidate_set_id",
            "iteration_candidate_set_digest",
            "replay_identity",
        }
    }
    if _digest(core) != claimed:
        raise SearchOSRuntimeError("iteration candidate set digest mismatch")
    if (
        safe.get("iteration_candidate_set_id")
        != (f"searchos-iteration:{int(safe.get('iteration') or 0)}:{claimed[:20]}")
        or safe.get("replay_identity") != f"searchos-iteration:{claimed}"
    ):
        raise SearchOSRuntimeError("iteration candidate set identity mismatch")
    if safe.get("raw_store_visibility_allowed") is not False:
        raise SearchOSRuntimeError("raw discovery store cannot become judgment-visible")
    return deepcopy(safe)


def validate_searchos_append_only_lineage(
    *,
    revision_1: Mapping[str, Any],
    initial_query_plan_items: Sequence[Mapping[str, Any]],
    current_query_plan_items: Sequence[Mapping[str, Any]],
    initial_identity_refs: Sequence[Mapping[str, Any]],
    iteration_candidate_sets: Sequence[Mapping[str, Any]],
    identity_deltas_by_digest: Mapping[str, Sequence[Mapping[str, Any]]],
    current_identity_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prove frozen-revision ancestry and exact ordered candidate identity deltas."""

    revision = _mapping(revision_1)
    initial_plan_ref = _required_ref(revision.get("initial_query_plan_ref"), "revision_1.initial_query_plan_ref")
    initial_identity_ref = _required_ref(
        revision.get("initial_identity_set_ref") or revision.get("source_result_identity_set_ref"),
        "revision_1.initial_identity_set_ref",
    )
    initial_plan = [deepcopy(_mapping(item)) for item in initial_query_plan_items]
    current_plan = [deepcopy(_mapping(item)) for item in current_query_plan_items]
    if current_plan[: len(initial_plan)] != initial_plan:
        raise SearchOSRuntimeError("initial QueryPlan snapshot is not an exact current-plan prefix")
    if revision.get("initial_query_plan_items_digest") and revision.get("initial_query_plan_items_digest") != _digest(
        initial_plan
    ):
        raise SearchOSRuntimeError("revision 1 initial QueryPlan snapshot became stale")
    initial_identities = [deepcopy(_mapping(item)) for item in initial_identity_refs]
    if revision.get("initial_identity_refs_digest") and revision.get("initial_identity_refs_digest") != _digest(
        initial_identities
    ):
        raise SearchOSRuntimeError("revision 1 initial identity snapshot became stale")

    initial_parent = (
        searchos_revision_1_candidate_state_ref(revision)
        if revision.get("schema_version") == SEARCHOS_REVISION_1_CANDIDATE_STATE_SCHEMA_VERSION
        else _required_ref(
            revision.get("candidate_state_ref") or revision.get("packet_ref") or revision,
            "revision_1 candidate state ref",
        )
    )
    ordered_sets: list[dict[str, Any]] = []
    expected_parent_by_slot: dict[str, dict[str, Any]] = {}
    reconstructed = list(initial_identities)
    seen_identity_keys = {_ref_key(item) for item in reconstructed}
    previous_iteration = 1
    for raw_set in iteration_candidate_sets:
        item = validate_searchos_iteration_candidate_set(raw_set)
        if int(item["iteration"]) != previous_iteration + 1:
            raise SearchOSRuntimeError("iteration candidate set order is non-contiguous")
        slot_id = _token(
            _mapping(item.get("active_slot_ref")).get("slot_id"),
            "active_slot_ref.slot_id",
        )
        expected_parent = expected_parent_by_slot.get(
            slot_id,
            initial_parent,
        )
        if _mapping(item["parent_candidate_state_ref"]) != expected_parent:
            raise SearchOSRuntimeError(
                "iteration candidate slot-local parent ref is stale"
            )
        delta_ref = _mapping(item["identity_set_delta_ref"])
        delta_digest = _first_digest(delta_ref)
        delta = identity_deltas_by_digest.get(delta_digest)
        if delta is None:
            raise SearchOSRuntimeError("iteration identity delta is omitted")
        normalized_delta = [deepcopy(_mapping(value)) for value in delta]
        if delta_ref.get("identity_count") is not None and int(delta_ref["identity_count"]) != len(normalized_delta):
            raise SearchOSRuntimeError("iteration identity delta count mismatch")
        if delta_ref.get("identity_refs_digest") and delta_ref.get("identity_refs_digest") != _digest(normalized_delta):
            raise SearchOSRuntimeError("iteration identity delta digest mismatch")
        for identity in normalized_delta:
            key = _ref_key(identity)
            if key in seen_identity_keys:
                raise SearchOSRuntimeError("iteration identity delta is not additive")
            seen_identity_keys.add(key)
            reconstructed.append(identity)
        expected_parent_by_slot[slot_id] = searchos_iteration_candidate_set_ref(
            item
        )
        ordered_sets.append(item)
        previous_iteration = int(item["iteration"])
    current_identities = [deepcopy(_mapping(item)) for item in current_identity_refs]
    if reconstructed != current_identities:
        raise SearchOSRuntimeError("initial identities plus ordered deltas do not equal current candidate state")
    proof_core = {
        "schema_version": "searchos_append_only_lineage_proof_v1",
        "initial_query_plan_ref": initial_plan_ref,
        "initial_identity_set_ref": initial_identity_ref,
        "current_query_plan_items_digest": _digest(current_plan),
        "current_identity_refs_digest": _digest(current_identities),
        "iteration_candidate_set_refs": [searchos_iteration_candidate_set_ref(item) for item in ordered_sets],
        "slot_local_candidate_ancestry_proven": True,
        "peer_slot_cursors_preserved": True,
        "initial_plan_is_exact_prefix": True,
        "identity_delta_equality_proven": True,
        "revision_1_compared_to_frozen_snapshots_only": True,
    }
    proof_digest = _digest(proof_core)
    return {
        **proof_core,
        "lineage_proof_id": f"searchos-lineage:{proof_digest[:24]}",
        "lineage_proof_digest": proof_digest,
    }


def build_candidate_use_options_v1(
    admitted_candidates: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate one judgment-visible option per slot plus normalized URL."""

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    order: list[tuple[str, str]] = []
    for raw in admitted_candidates:
        candidate = _mapping(raw)
        slot_ref = _required_ref(candidate.get("slot_ref"), "slot_ref")
        slot_id = _token(slot_ref.get("slot_id"), "slot_id")
        normalized_url = normalize_discovery_result_url(candidate.get("normalized_url") or candidate.get("url"))
        key = (slot_id, normalized_url)
        if key not in grouped:
            grouped[key] = {
                "slot_ref": slot_ref,
                "normalized_url": normalized_url,
                "candidate_refs": [],
                "query_plan_item_refs": [],
                "iteration_set_refs": [],
                "provider_result_occurrence_refs": [],
                "source_material_refs": [],
                "candidate_state_origin_refs": [],
            }
            order.append(key)
        group = grouped[key]
        origin_ref = _required_ref(candidate.get("candidate_state_ref"), "candidate_state_ref")
        if origin_ref not in group["candidate_state_origin_refs"]:
            group["candidate_state_origin_refs"].append(origin_ref)
        for field, source_name in (
            ("candidate_refs", "candidate_ref"),
            ("query_plan_item_refs", "query_plan_item_ref"),
            ("iteration_set_refs", "iteration_set_ref"),
            ("provider_result_occurrence_refs", "provider_result_occurrence_ref"),
            ("source_material_refs", "source_material_ref"),
        ):
            ref = _optional_ref(candidate.get(source_name))
            if ref and ref not in group[field]:
                group[field].append(ref)
        for ref in candidate.get("additional_provider_result_occurrence_refs") or ():
            admitted_ref = _required_ref(ref, "provider_result_occurrence_ref")
            if admitted_ref not in group["provider_result_occurrence_refs"]:
                group["provider_result_occurrence_refs"].append(admitted_ref)

    options: list[dict[str, Any]] = []
    for ordinal, key in enumerate(order, start=1):
        group = grouped[key]
        if not group["candidate_refs"] or not group["provider_result_occurrence_refs"]:
            raise SearchOSRuntimeError("candidate-use option lacks admitted candidate/occurrence lineage")
        stable_core = {
            "schema_version": SEARCHOS_CANDIDATE_USE_OPTION_SCHEMA_VERSION,
            "owner": SEARCHOS_OWNER,
            "slot_ref": group["slot_ref"],
            "normalized_url": group["normalized_url"],
        }
        stable_digest = _digest(stable_core)
        stable_ref = {
            "candidate_use_option_id": f"searchos-option:{stable_digest[:24]}",
            "candidate_use_option_digest": stable_digest,
            "normalized_url": group["normalized_url"],
            "slot_id": _token(group["slot_ref"].get("slot_id"), "slot_id"),
        }
        lineage_core = {
            "schema_version": SEARCHOS_CANDIDATE_LINEAGE_SNAPSHOT_SCHEMA_VERSION,
            "owner": SEARCHOS_OWNER,
            "candidate_use_option_ref": stable_ref,
            "candidate_state_origin_refs": group["candidate_state_origin_refs"],
            "candidate_refs": group["candidate_refs"],
            "query_plan_item_refs": group["query_plan_item_refs"],
            "iteration_set_refs": group["iteration_set_refs"],
            "provider_result_occurrence_refs": group["provider_result_occurrence_refs"],
            "source_material_refs": group["source_material_refs"],
        }
        complete_lineage_digest = _digest(lineage_core)
        lineage_core["complete_lineage_digest"] = complete_lineage_digest
        lineage_core["lineage_revision"] = max(
            1,
            len(group["provider_result_occurrence_refs"]),
        )
        lineage_digest = _digest(lineage_core)
        lineage_snapshot = {
            **lineage_core,
            "lineage_snapshot_id": f"searchos-option-lineage:{lineage_digest[:24]}",
            "lineage_snapshot_digest": lineage_digest,
        }
        lineage_ref = {
            "lineage_snapshot_id": lineage_snapshot["lineage_snapshot_id"],
            "lineage_snapshot_digest": lineage_digest,
            "complete_lineage_digest": complete_lineage_digest,
            "lineage_revision": lineage_core["lineage_revision"],
        }
        option = {
            **stable_core,
            "option_ordinal": ordinal,
            "candidate_state_origin_refs": group["candidate_state_origin_refs"],
            "candidate_refs": group["candidate_refs"],
            "query_plan_item_refs": group["query_plan_item_refs"],
            "iteration_set_refs": group["iteration_set_refs"],
            "provider_result_occurrence_refs": group["provider_result_occurrence_refs"],
            "source_material_refs": group["source_material_refs"],
            "lineage_snapshot": lineage_snapshot,
            "lineage_snapshot_ref": lineage_ref,
            "material_authority": (SearchOSMaterialAuthority.DIRECTIONAL_CANDIDATE_CONTEXT.value),
            "read_eligible": True,
            "support_proposal_eligible": False,
            "read_custody_created": False,
            "same_url_transport_count": 0,
            **stable_ref,
            "replay_identity": f"searchos-option:{stable_digest}",
        }
        options.append(option)
    return options


def build_candidate_use_window_v1(
    *,
    slot_ref: Mapping[str, Any],
    ordered_options: Sequence[Mapping[str, Any]],
    window_ordinal: int,
    policy_snapshot: Mapping[str, Any],
    option_dispositions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    slot = _required_ref(slot_ref, "slot_ref")
    slot_id = _token(slot.get("slot_id"), "slot_id")
    options = [deepcopy(_mapping(item)) for item in ordered_options]
    if any(_mapping(item.get("slot_ref")).get("slot_id") != slot_id for item in options):
        raise SearchOSRuntimeError("candidate window contains a different slot")
    ordinal = int(window_ordinal)
    if ordinal <= 0:
        raise SearchOSRuntimeError("candidate window ordinal must be positive")
    policy = _mapping(policy_snapshot)
    maximum_windows = int(policy.get("candidate_windows_per_slot") or 0)
    size = int(policy.get("candidate_use_window_size") or 0)
    if ordinal > maximum_windows:
        raise SearchOSRuntimeError("candidate window policy budget exhausted")
    start = (ordinal - 1) * size
    retained = options[start : start + size]
    dispositions = dict(option_dispositions or {})
    remaining_count = max(0, len(options) - start - len(retained))
    core = {
        "schema_version": SEARCHOS_CANDIDATE_USE_WINDOW_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "slot_ref": slot,
        "window_ordinal": ordinal,
        "ordered_candidate_use_option_refs": [candidate_use_option_ref(item) for item in retained],
        "model_visible_candidate_use_options": [
            {
                "candidate_use_option_ref": candidate_use_option_ref(item),
                "normalized_url": item.get("normalized_url"),
                "material_authority": (SearchOSMaterialAuthority.DIRECTIONAL_CANDIDATE_CONTEXT.value),
                "support_proposal_eligible": False,
                "current_disposition": dispositions.get(
                    _first_ref_id(candidate_use_option_ref(item)),
                    "available",
                ),
            }
            for item in retained
            if dispositions.get(
                _first_ref_id(candidate_use_option_ref(item)),
                "available",
            )
            not in COMPLETED_CANDIDATE_OPTION_DISPOSITIONS
        ],
        "retained_option_count": len(retained),
        "remaining_option_count": remaining_count,
        "full_eligible_option_digest": _digest([candidate_use_option_ref(item) for item in options]),
        "next_window_available": remaining_count > 0 and ordinal < maximum_windows,
        "next_window_requires_new_query": False,
        "next_window_requires_provider_dispatch": False,
        "next_window_requires_acquisition_proposal": False,
        "next_window_consumes_read_budget": False,
    }
    digest = _digest(core)
    return {
        **core,
        "candidate_use_window_id": f"searchos-window:{digest[:24]}",
        "candidate_use_window_digest": digest,
        "replay_identity": f"searchos-window:{digest}",
    }


def record_searchos_candidate_window(state: Mapping[str, Any], *, window: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = _validated_candidate_use_window(window)
    slot_ref = _required_ref(safe.get("slot_ref"), "slot_ref")
    slot_id = _token(slot_ref.get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_id not in slots or _mapping(slots[slot_id].get("slot_ref")) != slot_ref:
        raise SearchOSRuntimeError("candidate window slot lineage is stale")
    slot = deepcopy(slots[slot_id])
    ordinal = int(safe.get("window_ordinal") or 0)
    prior_count = int(slot.get("candidate_window_count") or 0)
    if ordinal not in {prior_count, prior_count + 1}:
        raise SearchOSRuntimeError("candidate window progression is non-contiguous")
    if ordinal == prior_count and _mapping(slot.get("current_window_ref")) != (candidate_use_window_ref(safe)):
        prior_option_refs = [_mapping(item) for item in slot.get("candidate_use_option_refs") or ()]
        current_option_refs = [_mapping(item) for item in safe.get("ordered_candidate_use_option_refs") or ()]
        stable_ref_fields = (
            "candidate_use_option_id",
            "candidate_use_option_digest",
            "normalized_url",
            "slot_id",
        )
        if [{key: item.get(key) for key in stable_ref_fields} for item in prior_option_refs] != [
            {key: item.get(key) for key in stable_ref_fields} for item in current_option_refs
        ]:
            raise SearchOSRuntimeError("candidate window replay changes stable options without progression")
        slot["current_window_ref"] = candidate_use_window_ref(safe)
        slot["candidate_use_option_refs"] = current_option_refs
        slot["action_history"].append(
            {
                "event": "candidate_window_snapshot_advanced",
                "candidate_use_window_ref": candidate_use_window_ref(safe),
                "new_query_created": False,
                "provider_dispatched": False,
                "acquisition_proposal_created": False,
                "read_budget_consumed": False,
            }
        )
    if ordinal == prior_count + 1:
        slot["candidate_window_count"] = ordinal
        slot["current_window_ref"] = candidate_use_window_ref(safe)
        slot["candidate_use_option_refs"] = [
            deepcopy(_mapping(item)) for item in safe.get("ordered_candidate_use_option_refs") or ()
        ]
        slot["action_history"].append(
            {
                "event": "candidate_window_exposed",
                "candidate_use_window_ref": candidate_use_window_ref(safe),
                "new_query_created": False,
                "provider_dispatched": False,
                "acquisition_proposal_created": False,
                "read_budget_consumed": False,
            }
        )
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def candidate_use_option_ref(option: Mapping[str, Any]) -> dict[str, Any]:
    safe = _validated_candidate_use_option(option)
    return {
        "candidate_use_option_id": _token(safe.get("candidate_use_option_id"), "candidate_use_option_id"),
        "candidate_use_option_digest": _digest_token(
            safe.get("candidate_use_option_digest"),
            "candidate_use_option_digest",
        ),
        "normalized_url": normalize_discovery_result_url(safe.get("normalized_url")),
        "slot_id": _token(_mapping(safe.get("slot_ref")).get("slot_id"), "slot_id"),
        "lineage_snapshot_ref": _required_ref(safe.get("lineage_snapshot_ref"), "lineage_snapshot_ref"),
    }


def candidate_use_window_ref(window: Mapping[str, Any]) -> dict[str, Any]:
    safe = _validated_candidate_use_window(window)
    return {
        "candidate_use_window_id": _token(safe.get("candidate_use_window_id"), "candidate_use_window_id"),
        "candidate_use_window_digest": _digest_token(
            safe.get("candidate_use_window_digest"),
            "candidate_use_window_digest",
        ),
        "window_ordinal": int(safe.get("window_ordinal") or 0),
        "full_eligible_option_digest": _digest_token(
            safe.get("full_eligible_option_digest"),
            "full_eligible_option_digest",
        ),
    }


def build_searchos_judgment_request_v1(
    *,
    state: Mapping[str, Any],
    slot_id: str,
    charge_ref: Mapping[str, Any],
    candidate_window: Mapping[str, Any],
    read_custody_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    canonical = _validated_state_copy(state)
    token = _token(slot_id, "slot_id")
    slot = deepcopy(_mapping(canonical["slots_by_id"])[token])
    window_ref = candidate_use_window_ref(candidate_window)
    if _mapping(candidate_window.get("slot_ref")).get("slot_id") != token:
        raise SearchOSRuntimeError("judgment window does not bind current slot")
    if window_ref != _mapping(slot.get("current_window_ref")):
        raise SearchOSRuntimeError("judgment window is not the current exposed window")
    charge = _required_ref(charge_ref, "charge_ref")
    if charge.get("slot_id") != token:
        raise SearchOSRuntimeError("judgment charge does not bind current slot")
    current_charge = next(
        (
            item
            for item in _mapping(canonical["budget"]).get("charge_history") or ()
            if _mapping(item).get("charge_id") == charge.get("charge_id")
        ),
        None,
    )
    if current_charge is None or _mapping(current_charge) != charge:
        raise SearchOSRuntimeError("judgment charge is stale or altered")
    custody_refs = [_validated_read_custody_material_ref(item) for item in read_custody_refs]
    if custody_refs != list(slot.get("custody_refs") or ()):
        raise SearchOSRuntimeError("judgment READ custody refs are stale")
    completed_option_ids = {
        option_id
        for option_id, raw_record in dict(slot.get("candidate_option_dispositions") or {}).items()
        if _mapping(raw_record).get("disposition") in COMPLETED_CANDIDATE_OPTION_DISPOSITIONS
    }
    visible_options = [
        deepcopy(_mapping(item))
        for item in candidate_window.get("model_visible_candidate_use_options") or ()
        if _first_ref_id(_mapping(_mapping(item).get("candidate_use_option_ref"))) not in completed_option_ids
    ]
    current_job = slot.get("current_discovery_job_class")
    binding_required = slot.get("binding_posture") == "unbound_required"
    legal_actions = [SearchOSJudgmentAction.HANDOFF_UNRESOLVED.value]
    allowed_followup_job_classes: list[str] = []
    policy = _mapping(canonical["policy_snapshot"])
    if (
        current_job == DiscoveryJobClass.ORIENTATION.value
        and int(slot.get("orientation_refinement_count") or 0)
        < int(policy.get("orientation_refinements_per_slot") or 0)
    ):
        allowed_followup_job_classes = [DiscoveryJobClass.ORIENTATION.value]
    elif current_job == DiscoveryJobClass.STANDARD_DISCOVERY.value:
        allowed_followup_job_classes = [
            DiscoveryJobClass.STANDARD_DISCOVERY.value,
            DiscoveryJobClass.DEEP_DISCOVERY.value,
        ]
    elif current_job == DiscoveryJobClass.DEEP_DISCOVERY.value:
        allowed_followup_job_classes = [DiscoveryJobClass.DEEP_DISCOVERY.value]
    if allowed_followup_job_classes:
        legal_actions.insert(
            0,
            SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY.value,
        )
    if binding_required:
        legal_actions.insert(
            0,
            SearchOSJudgmentAction.REQUIRE_CLARIFICATION.value,
        )
        if (
            (visible_options or custody_refs)
            and slot.get("interpretation_binding_ref") in ({}, None)
            and int(slot.get("interpretation_binding_count") or 0)
            < int(policy.get("interpretation_bindings_per_slot") or 0)
        ):
            legal_actions.insert(
                0,
                SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING.value,
            )
    if custody_refs and not binding_required:
        legal_actions.insert(
            0,
            SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION.value,
        )
    if visible_options:
        insertion = 1 if custody_refs else 0
        legal_actions.insert(
            insertion,
            SearchOSJudgmentAction.REQUEST_READ_PAGE.value,
        )
    request_core = {
        "schema_version": SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": canonical["answer_contract_ref"],
        "policy_snapshot_ref": canonical["policy_snapshot_ref"],
        "slot_ref": slot["slot_ref"],
        "slot_posture": slot["posture"],
        "candidate_state_ref": slot["current_candidate_state_ref"],
        "candidate_window_ref": window_ref,
        "candidate_use_options": visible_options,
        "read_custody_refs": custody_refs,
        "charge_ref": charge,
        "legal_actions": legal_actions,
        "allowed_followup_job_classes": allowed_followup_job_classes,
        "interpretation_binding_contract": {
            "enabled": binding_required,
            "semantic_slot_ref": deepcopy(slot["semantic_slot_ref"]),
            "resolved_value_must_equal_declared_candidate": True,
            "candidate_basis_refs": [
                deepcopy(
                    _mapping(item).get("candidate_use_option_ref")
                )
                for item in visible_options
            ],
            "read_basis_refs": deepcopy(custody_refs),
            "binding_is_evidence": False,
            "binding_satisfies_source_obligation": False,
        },
        "exactly_one_action_required": True,
        "free_text_url_execution_allowed": False,
        "deterministic_semantic_fallback_allowed": False,
    }
    digest = _digest(request_core)
    return {
        **request_core,
        "judgment_request_id": f"searchos-judgment-request:{digest[:24]}",
        "judgment_request_digest": digest,
        "replay_identity": f"searchos-judgment-request:{digest}",
    }


def build_searchos_navigation_judgment_request_v1(
    *,
    state: Mapping[str, Any],
    slot_id: str,
    charge_ref: Mapping[str, Any],
    candidate_window: Mapping[str, Any],
    navigation_window: Sequence[Mapping[str, Any]],
    read_custody_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the explicit, closed-by-default navigation judgment contract."""

    from core.searchos_navigation_runtime import project_navigation_window

    canonical = _validated_state_copy(state)
    policy = _mapping(canonical.get("policy_snapshot"))
    if policy.get("navigation_runtime_open") is not True:
        raise SearchOSRuntimeError("navigation judgment requires an explicitly opened owner composition")
    token = _token(slot_id, "slot_id")
    supplied_navigation = [deepcopy(_mapping(item)) for item in navigation_window]
    if supplied_navigation != project_navigation_window(canonical, slot_id=token):
        raise SearchOSRuntimeError("navigation judgment window is stale or altered")
    v1 = build_searchos_judgment_request_v1(
        state=canonical,
        slot_id=token,
        charge_ref=charge_ref,
        candidate_window=candidate_window,
        read_custody_refs=read_custody_refs,
    )
    slot = _mapping(_mapping(canonical["slots_by_id"])[token])
    edge_count = len(_mapping(canonical.get("navigation")).get("edges") or ())
    if int(slot.get("navigation_selection_count") or 0) >= int(policy.get("navigation_selections_per_slot") or 0):
        availability = "navigation_selection_limit_exhausted"
    elif edge_count >= int(policy.get("navigation_edges_per_run") or 0):
        availability = "navigation_run_edge_limit_exhausted"
    elif int(slot.get("read_nomination_count") or 0) >= int(policy.get("read_nominations_per_slot") or 0):
        availability = "navigation_read_nomination_limit_exhausted"
    elif supplied_navigation:
        availability = "navigation_available"
    else:
        availability = "navigation_no_selectable_options"
    visible_navigation = supplied_navigation if availability == "navigation_available" else []
    legal_actions = list(v1["legal_actions"])
    if visible_navigation:
        insertion = (
            1
            if legal_actions
            and legal_actions[0] == SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION.value
            else 0
        )
        legal_actions.insert(
            insertion,
            SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
        )
    request_core = {
        key: deepcopy(value)
        for key, value in v1.items()
        if key
        not in {
            "schema_version",
            "judgment_request_id",
            "judgment_request_digest",
            "replay_identity",
            "legal_actions",
        }
    }
    request_core.update(
        {
            "schema_version": SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION,
            "navigation_options": visible_navigation,
            "navigation_availability_reason": availability,
            "legal_actions": legal_actions,
            "navigation_options_directional_only": True,
            "navigation_options_support_bearing": False,
            "model_authored_destination_allowed": False,
        }
    )
    digest = _digest(request_core)
    return {
        **request_core,
        "judgment_request_id": f"searchos-navigation-judgment:{digest[:24]}",
        "judgment_request_digest": digest,
        "replay_identity": f"searchos-navigation-judgment:{digest}",
    }


def validate_searchos_judgment_model_output(
    *, request: Mapping[str, Any], model_output: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate one neutral model-authored action; never synthesize a fallback."""

    request_safe = _mapping(request)
    request_schema = request_safe.get("schema_version")
    if request_schema not in {
        SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION,
        SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION,
    }:
        raise SearchOSRuntimeError("judgment request schema version mismatch")
    navigation_enabled = request_schema == SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION
    output = _mapping(model_output)
    allowed_keys = {
        "schema_version",
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
        "action",
        "candidate_use_option_ref",
        "navigation_candidate_ref",
        "read_custody_refs",
        "followup_query",
        "discovery_job_class",
        "interpretation_binding",
        "reason",
        "read_custody_assessments",
    }
    if not navigation_enabled:
        allowed_keys.remove("navigation_candidate_ref")
    if set(output) - allowed_keys:
        raise SearchOSRuntimeError("judgment output contains unsupported fields")
    expected_decision_schema = (
        SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION
        if navigation_enabled
        else SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION
    )
    if output.get("schema_version") != expected_decision_schema:
        raise SearchOSRuntimeError("judgment output schema version mismatch")
    if output.get("judgment_request_id") != request_safe.get("judgment_request_id") or output.get(
        "judgment_request_digest"
    ) != request_safe.get("judgment_request_digest"):
        raise SearchOSRuntimeError("judgment nomination is stale")
    slot_id = _token(output.get("slot_id"), "slot_id")
    if slot_id != _mapping(request_safe.get("slot_ref")).get("slot_id"):
        raise SearchOSRuntimeError("judgment nomination slot is stale")
    try:
        action = SearchOSJudgmentAction(str(output.get("action") or ""))
    except ValueError as exc:
        raise SearchOSRuntimeError("judgment action is not in the neutral vocabulary") from exc
    if action.value not in set(request_safe.get("legal_actions") or ()):
        raise SearchOSRuntimeError("judgment action is not currently authorized")
    option_ref = _optional_ref(output.get("candidate_use_option_ref"))
    navigation_ref = _optional_ref(output.get("navigation_candidate_ref"))
    custody_refs = [_required_ref(item, "read_custody_ref") for item in output.get("read_custody_refs") or ()]
    custody_ids = [_first_ref_id(item) for item in custody_refs]
    if len(custody_ids) != len(set(custody_ids)):
        raise SearchOSRuntimeError("semantic handoff repeats READ custody")
    followup_query = _bounded_optional(output.get("followup_query"), MAX_FOLLOWUP_QUERY_CHARS)
    discovery_job_class: str | None = None
    if output.get("discovery_job_class") is not None:
        try:
            discovery_job_class = DiscoveryJobClass(
                str(output.get("discovery_job_class"))
            ).value
        except ValueError as exc:
            raise SearchOSRuntimeError(
                "follow-up discovery job class is invalid"
            ) from exc
    interpretation_binding = _mapping(output.get("interpretation_binding"))
    reason = _bounded_reason(output.get("reason"))
    visible_options = {
        _first_ref_id(_mapping(_mapping(item).get("candidate_use_option_ref"))): item
        for item in request_safe.get("candidate_use_options") or ()
    }
    visible_navigation = {
        _first_ref_id(_mapping(item).get("navigation_candidate_ref")): _mapping(item).get("navigation_candidate_ref")
        for item in request_safe.get("navigation_options") or ()
    }
    current_custody = {_first_ref_id(item): item for item in request_safe.get("read_custody_refs") or ()}
    visible_candidate_refs = {
        _first_ref_id(
            _mapping(_mapping(item).get("candidate_use_option_ref"))
        ): _mapping(_mapping(item).get("candidate_use_option_ref"))
        for item in request_safe.get("candidate_use_options") or ()
    }
    assessments: list[dict[str, Any]] = []
    for raw_assessment in output.get("read_custody_assessments") or ():
        assessment = _mapping(raw_assessment)
        if set(assessment) != {
            "reviewed_custody_ref",
            "material_disposition",
            "reason_code",
        }:
            raise SearchOSRuntimeError("READ custody assessment shape is invalid")
        reviewed = _required_ref(
            assessment.get("reviewed_custody_ref"),
            "reviewed_custody_ref",
        )
        custody_id = _first_ref_id(reviewed)
        if custody_id not in current_custody or reviewed != _mapping(current_custody[custody_id]):
            raise SearchOSRuntimeError("READ custody assessment is stale or altered")
        if assessment.get("material_disposition") != "read_insufficient":
            raise SearchOSRuntimeError("READ custody assessment disposition is invalid")
        reason_code = _reason_code(assessment.get("reason_code"))
        assessments.append(
            {
                "reviewed_custody_ref": reviewed,
                "material_disposition": "read_insufficient",
                "reason_code": reason_code,
            }
        )
    assessed_ids = [_first_ref_id(item["reviewed_custody_ref"]) for item in assessments]
    if len(assessed_ids) != len(set(assessed_ids)):
        raise SearchOSRuntimeError("READ custody assessment repeats material")
    if action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
        option_id = _first_ref_id(option_ref)
        if not option_ref or option_id not in visible_options:
            raise SearchOSRuntimeError("READ nomination is outside current candidate window")
        if option_ref != _mapping(_mapping(visible_options[option_id]).get("candidate_use_option_ref")):
            raise SearchOSRuntimeError("READ nomination ref is stale or altered")
        if custody_refs or followup_query or navigation_ref:
            raise SearchOSRuntimeError("READ nomination contains incompatible payload")
    elif action is SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB:
        if not navigation_enabled:
            raise SearchOSRuntimeError("navigation nomination requires navigation request")
        navigation_id = _first_ref_id(navigation_ref)
        if not navigation_ref or navigation_id not in visible_navigation:
            raise SearchOSRuntimeError("navigation nomination is outside current navigation window")
        if navigation_ref != _mapping(visible_navigation[navigation_id]):
            raise SearchOSRuntimeError("navigation nomination ref is stale or altered")
        if option_ref or custody_refs or followup_query:
            raise SearchOSRuntimeError("navigation nomination contains incompatible payload")
    elif action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
        if (
            not followup_query
            or not discovery_job_class
            or discovery_job_class
            not in set(request_safe.get("allowed_followup_job_classes") or ())
            or option_ref
            or navigation_ref
            or custody_refs
            or interpretation_binding
        ):
            raise SearchOSRuntimeError("follow-up nomination payload is invalid")
    elif action is SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING:
        if set(interpretation_binding) != {
            "semantic_slot_ref",
            "resolved_value",
            "basis_candidate_refs",
            "basis_read_custody_refs",
            "disclose_assumption",
        }:
            raise SearchOSRuntimeError(
                "interpretation-binding proposal shape is invalid"
            )
        binding_contract = _mapping(
            request_safe.get("interpretation_binding_contract")
        )
        semantic_slot_ref = _mapping(
            interpretation_binding.get("semantic_slot_ref")
        )
        if (
            binding_contract.get("enabled") is not True
            or semantic_slot_ref
            != _mapping(binding_contract.get("semantic_slot_ref"))
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding semantic slot is stale or altered"
            )
        resolved_value = _bounded_optional(
            interpretation_binding.get("resolved_value"),
            220,
        )
        declared_candidates = [
            str(value)
            for value in semantic_slot_ref.get("candidate_values") or ()
        ]
        if (
            not resolved_value
            or not declared_candidates
            or resolved_value not in declared_candidates
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding value violates declared candidate policy"
            )
        basis_candidate_refs = [
            _required_ref(item, "basis_candidate_ref")
            for item in interpretation_binding.get("basis_candidate_refs")
            or ()
        ]
        basis_read_refs = [
            _required_ref(item, "basis_read_custody_ref")
            for item in interpretation_binding.get("basis_read_custody_refs")
            or ()
        ]
        if not basis_candidate_refs and not basis_read_refs:
            raise SearchOSRuntimeError(
                "interpretation binding requires exact current basis refs"
            )
        candidate_basis_ids = [
            _first_ref_id(item) for item in basis_candidate_refs
        ]
        read_basis_ids = [_first_ref_id(item) for item in basis_read_refs]
        if (
            len(candidate_basis_ids) != len(set(candidate_basis_ids))
            or len(read_basis_ids) != len(set(read_basis_ids))
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding basis refs repeat identity"
            )
        for item in basis_candidate_refs:
            identity = _first_ref_id(item)
            if (
                identity not in visible_candidate_refs
                or item != visible_candidate_refs[identity]
            ):
                raise SearchOSRuntimeError(
                    "interpretation-binding candidate basis is stale or altered"
                )
        for item in basis_read_refs:
            identity = _first_ref_id(item)
            if (
                identity not in current_custody
                or item != _mapping(current_custody[identity])
            ):
                raise SearchOSRuntimeError(
                    "interpretation-binding READ basis is stale or altered"
                )
        if not isinstance(
            interpretation_binding.get("disclose_assumption"), bool
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding assumption disclosure must be boolean"
            )
        interpretation_binding = {
            "semantic_slot_ref": semantic_slot_ref,
            "resolved_value": resolved_value,
            "basis_candidate_refs": basis_candidate_refs,
            "basis_read_custody_refs": basis_read_refs,
            "disclose_assumption": interpretation_binding[
                "disclose_assumption"
            ],
        }
        if (
            option_ref
            or navigation_ref
            or custody_refs
            or followup_query
            or discovery_job_class
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding proposal contains incompatible payload"
            )
    elif action is SearchOSJudgmentAction.REQUIRE_CLARIFICATION:
        if (
            option_ref
            or navigation_ref
            or custody_refs
            or followup_query
            or discovery_job_class
            or interpretation_binding
        ):
            raise SearchOSRuntimeError(
                "clarification decision contains incompatible payload"
            )
    elif action is (SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION):
        if not custody_refs or option_ref or navigation_ref or followup_query or assessments:
            raise SearchOSRuntimeError("semantic handoff requires exact READ custody refs")
        for item in custody_refs:
            custody_id = _first_ref_id(item)
            if custody_id not in current_custody or item != _mapping(current_custody[custody_id]):
                raise SearchOSRuntimeError("semantic handoff nominated stale or altered READ custody")
    else:
        if option_ref or navigation_ref or custody_refs or followup_query or not reason:
            raise SearchOSRuntimeError("unresolved handoff payload is invalid")
    assessment_exempt_actions = {
        SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION,
        SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING,
    }
    if current_custody and action not in assessment_exempt_actions:
        if set(assessed_ids) != set(current_custody):
            raise SearchOSRuntimeError("post-READ action requires exact read_insufficient assessments")
    elif assessments:
        raise SearchOSRuntimeError("pre-READ action cannot assess custody")
    exact_fields = {
        "schema_version",
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
        "action",
        "reason",
    }
    if action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
        exact_fields.add("candidate_use_option_ref")
    elif action is SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB:
        exact_fields.add("navigation_candidate_ref")
    elif action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
        exact_fields.update({"followup_query", "discovery_job_class"})
    elif action is SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING:
        exact_fields.add("interpretation_binding")
    elif action is (
        SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
    ):
        exact_fields.add("read_custody_refs")
    if current_custody and action not in assessment_exempt_actions:
        exact_fields.add("read_custody_assessments")
    if set(output) != exact_fields:
        raise SearchOSRuntimeError("judgment action fields are not exact")
    core = {
        "schema_version": expected_decision_schema,
        "owner": SEARCHOS_OWNER,
        "judgment_request_ref": {
            "judgment_request_id": request_safe["judgment_request_id"],
            "judgment_request_digest": request_safe["judgment_request_digest"],
        },
        "slot_ref": deepcopy(request_safe["slot_ref"]),
        "candidate_state_ref": deepcopy(request_safe["candidate_state_ref"]),
        "candidate_window_ref": deepcopy(request_safe["candidate_window_ref"]),
        "charge_ref": deepcopy(request_safe["charge_ref"]),
        "action": action.value,
        "candidate_use_option_ref": option_ref,
        **({"navigation_candidate_ref": navigation_ref} if navigation_enabled else {}),
        "read_custody_refs": custody_refs,
        "followup_query": followup_query,
        "discovery_job_class": discovery_job_class,
        "interpretation_binding": interpretation_binding,
        "reason": reason,
        "read_custody_assessments": assessments,
        "deterministic_fallback_used": False,
    }
    digest = _digest(core)
    return {
        **core,
        "judgment_decision_id": f"searchos-decision:{digest[:24]}",
        "judgment_decision_digest": digest,
        "replay_identity": f"searchos-decision:{digest}",
    }


def reduce_searchos_judgment_decision(state: Mapping[str, Any], *, decision: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    reduced = _mapping(decision)
    if reduced.get("schema_version") not in {
        SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION,
        SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
    }:
        raise SearchOSRuntimeError("judgment decision schema version mismatch")
    slot_id = _token(_mapping(reduced.get("slot_ref")).get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_id not in slots:
        raise SearchOSRuntimeError("judgment decision references inactive slot")
    slot = deepcopy(slots[slot_id])
    if _mapping(reduced.get("candidate_state_ref")) != _mapping(
        slot.get("current_candidate_state_ref")
    ):
        raise SearchOSRuntimeError("judgment decision candidate state is stale")
    if slot["posture"] in {
        SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value,
        SearchOSSlotPosture.UNRESOLVED_HANDOFF.value,
        SearchOSSlotPosture.JUDGMENT_FAILED.value,
        SearchOSSlotPosture.BUDGET_EXHAUSTED.value,
        SearchOSSlotPosture.STALE_OR_INVALID.value,
        SearchOSSlotPosture.CLARIFICATION_REQUIRED.value,
    }:
        raise SearchOSRuntimeError("judgment decision follows a terminal slot posture")
    action = SearchOSJudgmentAction(reduced["action"])
    dispositions = dict(slot.get("candidate_option_dispositions") or {})
    admitted_custody = {_first_ref_id(item): item for item in slot.get("custody_refs") or ()}
    for assessment in reduced.get("read_custody_assessments") or ():
        custody = admitted_custody.get(_first_ref_id(_mapping(assessment).get("reviewed_custody_ref")))
        if custody is None:
            raise SearchOSRuntimeError("judgment assessment custody is no longer admitted")
        if _mapping(custody).get("origin") == "searchos_navigation":
            from core.searchos_navigation_runtime import (
                _validate_navigation_custody_lineage_after_admission,
            )

            _validate_navigation_custody_lineage_after_admission(candidate, custody)
            continue
        option_ref = _mapping(_mapping(custody).get("candidate_use_option_ref"))
        option_id = _first_ref_id(option_ref)
        dispositions[option_id] = {
            "candidate_use_option_id": option_id,
            "candidate_use_option_digest": option_ref.get("candidate_use_option_digest"),
            "disposition": "read_insufficient",
            "read_custody_ref": deepcopy(custody),
            "reason_code": _mapping(assessment).get("reason_code"),
        }
    slot["candidate_option_dispositions"] = dispositions
    policy = _mapping(candidate["policy_snapshot"])
    if action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
        if int(slot["read_nomination_count"]) >= int(policy["read_nominations_per_slot"]):
            return mark_searchos_slot_budget_exhausted(
                candidate,
                slot_id=slot_id,
                reason="read_nomination_budget_exhausted",
            )
        slot["posture"] = SearchOSSlotPosture.AWAITING_READ.value
        slot["read_nomination_count"] = int(slot["read_nomination_count"]) + 1
        slot["latest_reason"] = "authorized_candidate_read_requested"
    elif action is SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB:
        if policy.get("navigation_runtime_open") is not True:
            raise SearchOSRuntimeError("navigation_runtime_closed")
        if slot.get("pending_navigation_decision_ref") or slot.get("pending_navigation_candidate_ref"):
            raise SearchOSRuntimeError("navigation judgment conflicts with pending admission")
        navigation_ref = _required_ref(
            reduced.get("navigation_candidate_ref"),
            "navigation_candidate_ref",
        )
        slot["posture"] = SearchOSSlotPosture.AWAITING_NAVIGATION_ADMISSION.value
        slot["pending_navigation_decision_ref"] = _compact_ref(reduced)
        slot["pending_navigation_candidate_ref"] = navigation_ref
        slot["navigation_availability_reason"] = None
        slot["latest_reason"] = "navigation_breadcrumb_pending_admission"
    elif action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
        if int(slot["followup_query_nomination_count"]) >= int(policy["followup_query_nominations_per_slot"]):
            return mark_searchos_slot_budget_exhausted(
                candidate,
                slot_id=slot_id,
                reason="followup_query_nomination_budget_exhausted",
            )
        try:
            proposed_job = DiscoveryJobClass(
                str(reduced.get("discovery_job_class") or "")
            )
            current_job = DiscoveryJobClass(
                str(slot.get("current_discovery_job_class") or "")
            )
        except ValueError as exc:
            raise SearchOSRuntimeError(
                "follow-up decision lacks provider-neutral job lineage"
            ) from exc
        legal_transitions = {
            DiscoveryJobClass.ORIENTATION: {DiscoveryJobClass.ORIENTATION},
            DiscoveryJobClass.STANDARD_DISCOVERY: {
                DiscoveryJobClass.STANDARD_DISCOVERY,
                DiscoveryJobClass.DEEP_DISCOVERY,
            },
            DiscoveryJobClass.DEEP_DISCOVERY: {
                DiscoveryJobClass.DEEP_DISCOVERY,
            },
        }
        if proposed_job not in legal_transitions[current_job]:
            raise SearchOSRuntimeError(
                "follow-up discovery job transition is not lawful"
            )
        if current_job is DiscoveryJobClass.ORIENTATION:
            if int(slot.get("orientation_refinement_count") or 0) >= int(
                policy.get("orientation_refinements_per_slot") or 0
            ):
                raise SearchOSRuntimeError(
                    "orientation refinement budget is exhausted"
                )
            slot["orientation_refinement_count"] = (
                int(slot.get("orientation_refinement_count") or 0) + 1
            )
        slot["posture"] = SearchOSSlotPosture.AWAITING_FOLLOWUP_DISCOVER.value
        slot["pending_discovery_job_class"] = proposed_job.value
        slot["followup_query_nomination_count"] = int(slot["followup_query_nomination_count"]) + 1
        slot["latest_reason"] = "exact_followup_query_proposed"
    elif action is SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING:
        if slot.get("binding_posture") != "unbound_required":
            raise SearchOSRuntimeError(
                "interpretation binding is not required for this slot"
            )
        if int(slot.get("interpretation_binding_count") or 0) >= int(
            policy.get("interpretation_bindings_per_slot") or 0
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding budget is exhausted"
            )
        slot["posture"] = (
            SearchOSSlotPosture.AWAITING_INTERPRETATION_BINDING.value
        )
        slot["pending_interpretation_binding_decision_ref"] = _compact_ref(
            reduced
        )
        slot["latest_reason"] = "interpretation_binding_pending_admission"
    elif action is SearchOSJudgmentAction.REQUIRE_CLARIFICATION:
        if slot.get("binding_posture") != "unbound_required":
            raise SearchOSRuntimeError(
                "clarification is not licensed for a stable semantic slot"
            )
        slot["posture"] = SearchOSSlotPosture.CLARIFICATION_REQUIRED.value
        slot["clarification_posture"] = {
            "clarification_required": True,
            "component_ref": deepcopy(slot["component_ref"]),
            "semantic_slot_ref": deepcopy(slot["semantic_slot_ref"]),
            "declared_candidates": list(
                _mapping(slot["semantic_slot_ref"]).get("candidate_values")
                or ()
            ),
            "reason": _bounded_reason(reduced.get("reason")),
            "provider_dispatch_allowed": False,
        }
        slot["latest_reason"] = "search_judgment_requires_clarification"
    elif action is (SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION):
        if slot.get("binding_posture") == "unbound_required":
            raise SearchOSRuntimeError(
                "semantic handoff cannot bypass required interpretation binding"
            )
        slot["posture"] = SearchOSSlotPosture.READY_FOR_SEMANTIC_EVALUATION.value
        slot["latest_reason"] = "read_custody_selected_for_semantic_evaluation"
    else:
        slot["posture"] = SearchOSSlotPosture.UNRESOLVED_HANDOFF.value
        slot["latest_reason"] = _bounded_reason(reduced.get("reason"))
    slot["action_history"].append(
        {
            "judgment_decision_ref": _compact_ref(reduced),
            "action": action.value,
            "posture_after": slot["posture"],
            "reason": slot["latest_reason"],
        }
    )
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def build_searchos_interpretation_binding_v1(
    *,
    state: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    judgment_decision: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one factual, bounded, non-evidentiary interpretation binding."""

    canonical = _validated_state_copy(state)
    decision = _validated_searchos_judgment_decision(judgment_decision)
    if (
        decision.get("action")
        != SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING.value
    ):
        raise SearchOSRuntimeError(
            "interpretation binding requires its exact SearchJudgment action"
        )
    slot_id = _token(
        _mapping(decision.get("slot_ref")).get("slot_id"),
        "slot_id",
    )
    slots = _mapping(canonical.get("slots_by_id"))
    if slot_id not in slots:
        raise SearchOSRuntimeError(
            "interpretation binding references an inactive slot"
        )
    slot = _mapping(slots[slot_id])
    if _mapping(decision.get("slot_ref")) != _mapping(slot.get("slot_ref")):
        raise SearchOSRuntimeError(
            "interpretation binding slot lineage is stale or altered"
        )
    if _mapping(decision.get("candidate_state_ref")) != _mapping(
        slot.get("current_candidate_state_ref")
    ):
        raise SearchOSRuntimeError(
            "interpretation binding candidate state is stale"
        )
    if (
        slot.get("posture")
        != SearchOSSlotPosture.AWAITING_INTERPRETATION_BINDING.value
        or _mapping(slot.get("pending_interpretation_binding_decision_ref"))
        != _compact_ref(decision)
    ):
        raise SearchOSRuntimeError(
            "interpretation binding does not follow its pending judgment"
        )
    component_ref, semantic_slot_ref = _accepted_binding_scope(
        canonical,
        accepted_contract,
        slot,
    )
    proposal = _mapping(decision.get("interpretation_binding"))
    if _mapping(proposal.get("semantic_slot_ref")) != semantic_slot_ref:
        raise SearchOSRuntimeError(
            "interpretation binding semantic slot is stale or altered"
        )
    resolved_value = _bounded_optional(proposal.get("resolved_value"), 220)
    declared_candidates = [
        str(value) for value in semantic_slot_ref.get("candidate_values") or ()
    ]
    if not resolved_value or resolved_value not in declared_candidates:
        raise SearchOSRuntimeError(
            "interpretation binding must select one declared candidate"
        )
    candidate_basis = [
        _required_ref(item, "basis_candidate_ref")
        for item in proposal.get("basis_candidate_refs") or ()
    ]
    read_basis = [
        _required_ref(item, "basis_read_custody_ref")
        for item in proposal.get("basis_read_custody_refs") or ()
    ]
    _validate_binding_basis_refs(
        slot,
        candidate_basis=candidate_basis,
        read_basis=read_basis,
    )
    if not isinstance(proposal.get("disclose_assumption"), bool):
        raise SearchOSRuntimeError(
            "interpretation binding requires explicit assumption disclosure"
        )
    slot_kind = _token(semantic_slot_ref.get("slot_kind"), "slot_kind")
    binding_category = SEARCHOS_INTERPRETATION_BINDING_CATEGORY_BY_SLOT_KIND.get(
        slot_kind
    )
    if not binding_category:
        raise SearchOSRuntimeError(
            "interpretation binding is limited to factual uncertainty kinds"
        )
    core = {
        "schema_version": SEARCHOS_INTERPRETATION_BINDING_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": deepcopy(canonical["answer_contract_ref"]),
        "slot_ref": deepcopy(slot["slot_ref"]),
        "component_ref": component_ref,
        "semantic_slot_ref": semantic_slot_ref,
        "candidate_state_ref": deepcopy(slot["current_candidate_state_ref"]),
        "binding_category": binding_category,
        "resolved_value": resolved_value,
        "basis_candidate_refs": candidate_basis,
        "basis_read_custody_refs": read_basis,
        "disclose_assumption": proposal["disclose_assumption"],
        "judgment_decision_ref": _compact_ref(decision),
        "reason": _bounded_reason(decision.get("reason")),
        "search_planning_resolution_only": True,
        "base_answer_contract_mutated": False,
        "evidence_admitted": False,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "coverage_created": False,
        "citation_eligible": False,
        "append_only": True,
        "canonical_state": True,
    }
    digest = _digest(core)
    return validate_searchos_interpretation_binding(
        {
            **core,
            "interpretation_binding_id": (
                f"searchos-interpretation-binding:{digest[:24]}"
            ),
            "interpretation_binding_digest": digest,
            "replay_identity": f"searchos-interpretation-binding:{digest}",
        },
        state=canonical,
        accepted_contract=accepted_contract,
    )


def validate_searchos_interpretation_binding(
    binding: Mapping[str, Any],
    *,
    state: Mapping[str, Any] | None = None,
    accepted_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    safe = _validated_digest_envelope(
        binding,
        schema_version=SEARCHOS_INTERPRETATION_BINDING_SCHEMA_VERSION,
        digest_field="interpretation_binding_digest",
        id_field="interpretation_binding_id",
        identity_prefix="searchos-interpretation-binding",
        label="SearchOS interpretation binding",
    )
    exact_fields = {
        "schema_version",
        "owner",
        "run_id",
        "request_id",
        "answer_contract_ref",
        "slot_ref",
        "component_ref",
        "semantic_slot_ref",
        "candidate_state_ref",
        "binding_category",
        "resolved_value",
        "basis_candidate_refs",
        "basis_read_custody_refs",
        "disclose_assumption",
        "judgment_decision_ref",
        "reason",
        "search_planning_resolution_only",
        "base_answer_contract_mutated",
        "evidence_admitted",
        "support_admitted",
        "source_obligation_satisfied",
        "coverage_created",
        "citation_eligible",
        "append_only",
        "canonical_state",
        "interpretation_binding_id",
        "interpretation_binding_digest",
        "replay_identity",
    }
    if set(safe) != exact_fields:
        raise SearchOSRuntimeError(
            "interpretation-binding fields are not exact"
        )
    if safe.get("owner") != SEARCHOS_OWNER:
        raise SearchOSRuntimeError("interpretation-binding owner mismatch")
    for field, expected in {
        "search_planning_resolution_only": True,
        "base_answer_contract_mutated": False,
        "evidence_admitted": False,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "coverage_created": False,
        "citation_eligible": False,
        "append_only": True,
        "canonical_state": True,
    }.items():
        if safe.get(field) is not expected:
            raise SearchOSRuntimeError(
                f"interpretation-binding authority field {field} is invalid"
            )
    semantic_slot_ref = _mapping(safe.get("semantic_slot_ref"))
    slot_kind = _token(semantic_slot_ref.get("slot_kind"), "slot_kind")
    if safe.get("binding_category") != (
        SEARCHOS_INTERPRETATION_BINDING_CATEGORY_BY_SLOT_KIND.get(slot_kind)
    ):
        raise SearchOSRuntimeError(
            "interpretation-binding category does not match factual slot kind"
        )
    resolved_value = _bounded_optional(safe.get("resolved_value"), 220)
    if resolved_value not in {
        str(value) for value in semantic_slot_ref.get("candidate_values") or ()
    }:
        raise SearchOSRuntimeError(
            "interpretation-binding value is not a declared candidate"
        )
    if not isinstance(safe.get("disclose_assumption"), bool):
        raise SearchOSRuntimeError(
            "interpretation-binding disclosure posture is invalid"
        )
    _bounded_reason(safe.get("reason"))
    _required_ref(safe.get("slot_ref"), "slot_ref")
    _required_ref(safe.get("component_ref"), "component_ref")
    _required_ref(safe.get("candidate_state_ref"), "candidate_state_ref")
    _required_ref(safe.get("judgment_decision_ref"), "judgment_decision_ref")
    candidate_basis = [
        _required_ref(item, "basis_candidate_ref")
        for item in safe.get("basis_candidate_refs") or ()
    ]
    read_basis = [
        _required_ref(item, "basis_read_custody_ref")
        for item in safe.get("basis_read_custody_refs") or ()
    ]
    if not candidate_basis and not read_basis:
        raise SearchOSRuntimeError(
            "interpretation binding requires bounded factual basis"
        )
    if len({_ref_key(item) for item in candidate_basis}) != len(
        candidate_basis
    ) or len({_ref_key(item) for item in read_basis}) != len(read_basis):
        raise SearchOSRuntimeError(
            "interpretation-binding basis repeats identity"
        )
    if state is not None:
        canonical = _validated_state_copy(state)
        if (
            safe.get("run_id") != canonical.get("run_id")
            or safe.get("request_id") != canonical.get("request_id")
            or _mapping(safe.get("answer_contract_ref"))
            != _mapping(canonical.get("answer_contract_ref"))
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding run or contract scope mismatch"
            )
        slot_id = _token(
            _mapping(safe.get("slot_ref")).get("slot_id"),
            "slot_id",
        )
        slot = _mapping(_mapping(canonical.get("slots_by_id")).get(slot_id))
        if (
            not slot
            or _mapping(safe.get("slot_ref"))
            != _mapping(slot.get("slot_ref"))
            or _mapping(safe.get("component_ref"))
            != _mapping(slot.get("component_ref"))
            or _mapping(safe.get("semantic_slot_ref"))
            != _mapping(slot.get("semantic_slot_ref"))
            or _mapping(safe.get("candidate_state_ref"))
            != _mapping(slot.get("current_candidate_state_ref"))
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding active-slot lineage is stale"
            )
        _validate_binding_basis_refs(
            slot,
            candidate_basis=candidate_basis,
            read_basis=read_basis,
        )
        if accepted_contract is not None:
            expected_component, expected_semantic = _accepted_binding_scope(
                canonical,
                accepted_contract,
                slot,
            )
            if (
                _mapping(safe.get("component_ref")) != expected_component
                or _mapping(safe.get("semantic_slot_ref"))
                != expected_semantic
            ):
                raise SearchOSRuntimeError(
                    "interpretation binding changed accepted semantic identity"
                )
    return deepcopy(safe)


def searchos_interpretation_binding_ref(
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    safe = validate_searchos_interpretation_binding(binding)
    return {
        "interpretation_binding_id": safe["interpretation_binding_id"],
        "interpretation_binding_digest": safe[
            "interpretation_binding_digest"
        ],
        "semantic_slot_id": _token(
            _mapping(safe.get("semantic_slot_ref")).get("slot_id"),
            "semantic_slot_id",
        ),
        "binding_category": safe["binding_category"],
        "schema_version": SEARCHOS_INTERPRETATION_BINDING_SCHEMA_VERSION,
    }


def record_searchos_interpretation_binding(
    state: Mapping[str, Any],
    *,
    accepted_contract: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Admit one append-only binding with exact replay and conflict safety."""

    candidate = _validated_state_copy(state)
    safe = validate_searchos_interpretation_binding(
        binding,
        state=candidate,
        accepted_contract=accepted_contract,
    )
    history = [
        deepcopy(_mapping(item))
        for item in candidate.get("interpretation_binding_history") or ()
    ]
    binding_key = _interpretation_binding_key(safe)
    for existing in history:
        if _interpretation_binding_key(existing) == binding_key:
            if existing != safe:
                raise SearchOSRuntimeError(
                    "interpretation-binding identity collision"
                )
            return candidate
    component_id = _first_ref_id(_mapping(safe.get("component_ref")))
    semantic_slot_id = _token(
        _mapping(safe.get("semantic_slot_ref")).get("slot_id"),
        "semantic_slot_id",
    )
    for existing in history:
        if (
            _first_ref_id(_mapping(existing.get("component_ref")))
            == component_id
            and _mapping(existing.get("semantic_slot_ref")).get("slot_id")
            == semantic_slot_id
        ):
            raise SearchOSRuntimeError(
                "conflicting interpretation binding for semantic slot"
            )
    slot_id = _token(
        _mapping(safe.get("slot_ref")).get("slot_id"),
        "slot_id",
    )
    slots = _mutable_mapping(candidate.get("slots_by_id"))
    target = deepcopy(_mapping(slots.get(slot_id)))
    if (
        target.get("posture")
        != SearchOSSlotPosture.AWAITING_INTERPRETATION_BINDING.value
        or _mapping(target.get("pending_interpretation_binding_decision_ref"))
        != _mapping(safe.get("judgment_decision_ref"))
    ):
        raise SearchOSRuntimeError(
            "interpretation-binding admission follows stale slot state"
        )
    policy = _mapping(candidate.get("policy_snapshot"))
    if int(target.get("interpretation_binding_count") or 0) >= int(
        policy.get("interpretation_bindings_per_slot") or 0
    ):
        raise SearchOSRuntimeError(
            "interpretation-binding admission exceeds its bounded policy"
        )
    ref = searchos_interpretation_binding_ref(safe)
    for peer_slot_id, raw_peer in list(slots.items()):
        peer = deepcopy(_mapping(raw_peer))
        if (
            _first_ref_id(_mapping(peer.get("component_ref")))
            != component_id
            or _mapping(peer.get("semantic_slot_ref")).get("slot_id")
            != semantic_slot_id
        ):
            continue
        if peer.get("binding_posture") not in {
            "unbound_required",
            "bound",
        }:
            raise SearchOSRuntimeError(
                "interpretation binding crossed a stable semantic slot"
            )
        peer["binding_posture"] = "bound"
        peer["interpretation_binding_ref"] = deepcopy(ref)
        peer["interpretation_binding_count"] = max(
            1,
            int(peer.get("interpretation_binding_count") or 0),
        )
        peer["current_discovery_job_class"] = (
            DiscoveryJobClass.STANDARD_DISCOVERY.value
        )
        if peer_slot_id == slot_id:
            peer["posture"] = SearchOSSlotPosture.ACTIVE_UNJUDGED.value
            peer.pop("pending_interpretation_binding_decision_ref", None)
            peer["latest_reason"] = "interpretation_binding_admitted"
            peer["action_history"].append(
                {
                    "event": "interpretation_binding_admitted",
                    "interpretation_binding_ref": deepcopy(ref),
                    "base_answer_contract_mutated": False,
                    "evidence_admitted": False,
                    "source_obligation_satisfied": False,
                }
            )
        slots[peer_slot_id] = _refresh_slot(peer)
    candidate["slots_by_id"] = slots
    candidate["interpretation_binding_history"].append(deepcopy(safe))
    return _refresh_state(candidate)


def build_searchos_effective_semantic_slot_view(
    *,
    state: Mapping[str, Any],
    semantic_slot_id: str,
    component_id: str | None = None,
    accepted_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project accepted slot plus binding without mutating the base contract."""

    canonical = _validated_state_copy(state)
    token = _token(semantic_slot_id, "semantic_slot_id")
    component_token = (
        _token(component_id, "component_id")
        if component_id is not None
        else None
    )
    matching_slots = [
        _mapping(item)
        for item in _mapping(canonical.get("slots_by_id")).values()
        if _mapping(_mapping(item).get("semantic_slot_ref")).get("slot_id")
        == token
        and (
            component_token is None
            or _first_ref_id(_mapping(item.get("component_ref")))
            == component_token
        )
    ]
    if not matching_slots:
        raise SearchOSRuntimeError(
            "effective semantic-slot view references an inactive slot"
        )
    component_ids = {
        _first_ref_id(_mapping(item.get("component_ref")))
        for item in matching_slots
    }
    if len(component_ids) != 1:
        raise SearchOSRuntimeError(
            "semantic-slot identity is ambiguous across components"
        )
    slot = matching_slots[0]
    if accepted_contract is not None:
        component_ref, base_semantic_ref = _accepted_binding_scope(
            canonical,
            accepted_contract,
            slot,
            require_binding_eligible=False,
        )
    else:
        component_ref = deepcopy(_mapping(slot.get("component_ref")))
        base_semantic_ref = deepcopy(_mapping(slot.get("semantic_slot_ref")))
    binding_ref = _mapping(slot.get("interpretation_binding_ref"))
    binding = {}
    if binding_ref:
        binding = next(
            (
                deepcopy(_mapping(item))
                for item in canonical.get("interpretation_binding_history")
                or ()
                if _interpretation_binding_key(_mapping(item))
                == _interpretation_binding_key(binding_ref)
            ),
            {},
        )
        if not binding:
            raise SearchOSRuntimeError(
                "effective semantic-slot binding ref is orphaned"
            )
        validate_searchos_interpretation_binding(binding)
    resolved_value = (
        binding.get("resolved_value")
        if binding
        else base_semantic_ref.get("selected_value")
    )
    core = {
        "schema_version": SEARCHOS_EFFECTIVE_SEMANTIC_SLOT_VIEW_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": deepcopy(canonical["answer_contract_ref"]),
        "component_ref": component_ref,
        "base_semantic_slot_ref": base_semantic_ref,
        "interpretation_binding_ref": deepcopy(binding_ref),
        "effective_status": (
            "resolved_for_search_planning"
            if binding
            else str(base_semantic_ref.get("status") or "explicit")
        ),
        "effective_value": resolved_value,
        "resolution_source": (
            "interpretation_binding"
            if binding
            else "accepted_answer_contract"
        ),
        "binding_category": binding.get("binding_category"),
        "disclose_assumption": (
            binding.get("disclose_assumption") if binding else False
        ),
        "base_answer_contract_mutated": False,
        "evidence_admitted": False,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "coverage_created": False,
        "search_planning_view_only": True,
        "canonical_state": True,
    }
    digest = _digest(core)
    return {
        **core,
        "effective_semantic_slot_view_id": (
            f"searchos-effective-slot:{digest[:24]}"
        ),
        "effective_semantic_slot_view_digest": digest,
        "replay_identity": f"searchos-effective-slot:{digest}",
    }


def build_searchos_semantic_evaluation_handoff_v1(
    *,
    state: Mapping[str, Any],
    slot_id: str,
    judgment_decision_ref: Mapping[str, Any],
    read_custody_material_refs: Sequence[Mapping[str, Any]],
    accepted_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    canonical = _validated_state_copy(state)
    token = _token(slot_id, "slot_id")
    slot = deepcopy(_mapping(canonical["slots_by_id"])[token])
    if slot["posture"] != SearchOSSlotPosture.READY_FOR_SEMANTIC_EVALUATION.value:
        raise SearchOSRuntimeError("semantic handoff requires a ready slot")
    if slot.get("binding_posture") == "unbound_required":
        raise SearchOSRuntimeError(
            "semantic handoff requires an admitted interpretation binding"
        )
    custody = [_required_ref(item, "read_custody_material_ref") for item in read_custody_material_refs]
    if not custody:
        raise SearchOSRuntimeError("semantic handoff requires READ custody material")
    admitted_custody = {_first_ref_id(item): deepcopy(_mapping(item)) for item in slot.get("custody_refs") or ()}
    for ref in custody:
        custody_id = _first_ref_id(ref)
        if custody_id not in admitted_custody or ref != admitted_custody[custody_id]:
            raise SearchOSRuntimeError("semantic handoff custody is not exact current admitted material")
        if ref.get("material_authority") != (SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value):
            raise SearchOSRuntimeError("directional candidate context cannot enter support-bearing analysis")
        if ref.get("readable") is not True or ref.get("stale") is True:
            raise SearchOSRuntimeError("semantic handoff READ custody is unreadable or stale")
        if _mapping(ref.get("slot_ref")) != _mapping(slot["slot_ref"]):
            raise SearchOSRuntimeError("semantic handoff custody slot lineage mismatch")
    decision_ref = _compact_ref(_required_ref(judgment_decision_ref, "judgment_decision_ref"))
    latest_action = _mapping((slot.get("action_history") or [{}])[-1])
    if decision_ref != _mapping(latest_action.get("judgment_decision_ref")):
        raise SearchOSRuntimeError("semantic handoff judgment decision is stale")
    core = {
        "schema_version": SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": canonical["answer_contract_ref"],
        "policy_snapshot_ref": canonical["policy_snapshot_ref"],
        "slot_ref": deepcopy(slot["slot_ref"]),
        "candidate_state_ref": slot["current_candidate_state_ref"],
        "effective_semantic_slot_view": (
            build_searchos_effective_semantic_slot_view(
                state=canonical,
                semantic_slot_id=_token(
                    _mapping(slot.get("semantic_slot_ref")).get("slot_id"),
                    "semantic_slot_id",
                ),
                component_id=_first_ref_id(_mapping(slot.get("component_ref"))),
                accepted_contract=(
                    None
                    if slot.get("legacy_uncertainty_lineage_defaulted") is True
                    else accepted_contract
                ),
            )
        ),
        "judgment_decision_ref": decision_ref,
        "read_custody_material_refs": custody,
        "material_authority": SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value,
        "component_analyst_proposal_eligible": True,
        "semantic_observation_admitted": False,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "direct_semantic_producer_allowed": False,
        "n_component_receiver_required": True,
    }
    digest = _digest(core)
    return {
        **core,
        "semantic_handoff_id": f"searchos-semantic-handoff:{digest[:24]}",
        "semantic_handoff_digest": digest,
        "replay_identity": f"searchos-semantic-handoff:{digest}",
    }


def record_searchos_semantic_handoff(state: Mapping[str, Any], *, handoff: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = _validated_semantic_handoff(handoff)
    slot_id = _token(_mapping(safe.get("slot_ref")).get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    slot = deepcopy(slots[slot_id])
    if slot["posture"] != SearchOSSlotPosture.READY_FOR_SEMANTIC_EVALUATION.value:
        raise SearchOSRuntimeError("semantic handoff follows stale slot state")
    if _mapping(safe.get("candidate_state_ref")) != _mapping(
        slot.get("current_candidate_state_ref")
    ):
        raise SearchOSRuntimeError("semantic handoff candidate state is stale")
    ref = searchos_semantic_handoff_ref(safe)
    slot["posture"] = SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
    slot["semantic_handoff_refs"].append(ref)
    slot["latest_reason"] = "governed_component_analysis_pending"
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    candidate["semantic_handoff_refs"].append(ref)
    return _refresh_state(candidate)


def searchos_semantic_handoff_ref(handoff: Mapping[str, Any]) -> dict[str, Any]:
    safe = _validated_semantic_handoff(handoff)
    return {
        "semantic_handoff_id": _token(safe.get("semantic_handoff_id"), "semantic_handoff_id"),
        "semantic_handoff_digest": _digest_token(safe.get("semantic_handoff_digest"), "semantic_handoff_digest"),
        "slot_ref": _required_ref(safe.get("slot_ref"), "slot_ref"),
        "schema_version": SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
    }


def build_searchos_slice_a_readiness_v1(
    *,
    state: Mapping[str, Any],
    semantic_outcomes_by_slot: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive readiness only from the complete governed semantic chain."""

    canonical = _validated_state_copy(state)
    slot_records: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for slot_id in canonical["active_slot_ids"]:
        slot = deepcopy(_mapping(canonical["slots_by_id"])[slot_id])
        outcome = _mapping(semantic_outcomes_by_slot.get(slot_id))
        required = slot["requirement_posture"] == SearchOSRequirementPosture.REQUIRED.value
        recovery_cycle_ref = _optional_ref(
            outcome.get("searchos_recovery_cycle_ref")
        )
        recovery_evidence_ref = _optional_ref(
            outcome.get("searchos_recovery_evidence_ref")
        )
        exact_chain = all(
            (
                _optional_ref(outcome.get("semantic_handoff_ref")),
                _optional_ref(outcome.get("component_analyst_proposal_ref")),
                _optional_ref(outcome.get("component_dprime_validation_ref")),
                _optional_ref(outcome.get("semantic_admission_outcome_ref")),
            )
        )
        ready = (
            slot["posture"] == SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
            and exact_chain
            and outcome.get("component_analyst_proposal_status") == "proposed"
            and outcome.get("component_dprime_validation_status") == "accepted"
            and outcome.get("semantic_admission_status") == "admitted"
            and outcome.get("material_authority") == SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value
        )
        reason = None if ready else _readiness_failure_reason(slot, outcome)
        record = {
            "slot_ref": deepcopy(slot["slot_ref"]),
            "requirement_posture": slot["requirement_posture"],
            "support_kind": slot.get("support_kind"),
            "latest_judgment_posture": slot["posture"],
            "latest_judgment_reason": slot["latest_reason"],
            "judgment_call_count": int(slot.get("judgment_call_count") or 0),
            "action_history": deepcopy(slot["action_history"]),
            "candidate_state_ref": deepcopy(slot["current_candidate_state_ref"]),
            "semantic_slot_ref": deepcopy(slot.get("semantic_slot_ref")),
            "current_discovery_job_class": slot.get(
                "current_discovery_job_class"
            ),
            "binding_posture": slot.get("binding_posture"),
            "interpretation_binding_ref": deepcopy(
                slot.get("interpretation_binding_ref") or {}
            ),
            "clarification_posture": deepcopy(
                slot.get("clarification_posture") or {}
            ),
            "custody_refs": deepcopy(slot["custody_refs"]),
            "semantic_handoff_ref": _optional_ref(outcome.get("semantic_handoff_ref")),
            "component_analyst_proposal_ref": _optional_ref(outcome.get("component_analyst_proposal_ref")),
            "component_dprime_validation_ref": _optional_ref(outcome.get("component_dprime_validation_ref")),
            "semantic_admission_outcome_ref": _optional_ref(outcome.get("semantic_admission_outcome_ref")),
            "searchos_recovery_cycle_ref": recovery_cycle_ref,
            "searchos_recovery_evidence_ref": recovery_evidence_ref,
            "slice_a_ready": ready,
            "unresolved_reason": reason,
            "satisfaction_claimed_by_readiness": False,
            "coverage_upgrade_claimed_by_readiness": False,
        }
        slot_records.append(record)
        if required and not ready:
            unresolved.append(
                {
                    "slot_ref": deepcopy(slot["slot_ref"]),
                    "reason": reason,
                    "latest_judgment_posture": slot["posture"],
                }
            )
    core = {
        "schema_version": SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": canonical["answer_contract_ref"],
        "policy_snapshot_ref": canonical["policy_snapshot_ref"],
        "slot_records": slot_records,
        "required_slot_count": len(canonical["required_slot_ids"]),
        "optional_slot_count": len(canonical["optional_slot_ids"]),
        "required_ready_count": len(canonical["required_slot_ids"]) - len(unresolved),
        "unresolved_required_slots": unresolved,
        "all_required_slots_slice_a_ready": not unresolved,
        "semantic_receiver_ready": not unresolved,
        "sufficiency_adjudication_required": True,
        "comprehensive_recovery_authorized": False,
        "whole_run_stop_decided": False,
        "stop_insufficient_emitted": False,
        "canonical_state": True,
    }
    digest = _digest(core)
    return {
        **core,
        "readiness_projection_id": f"searchos-readiness:{digest[:24]}",
        "readiness_projection_digest": digest,
        "replay_identity": f"searchos-readiness:{digest}",
    }


def build_searchos_required_needs_block(
    readiness: Mapping[str, Any],
    *,
    blocker_facts: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    safe = _mapping(readiness)
    _require_schema(safe, SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION, "Slice A readiness")
    unresolved = [deepcopy(_mapping(item)) for item in safe.get("unresolved_required_slots") or ()]
    if not unresolved or safe.get("all_required_slots_slice_a_ready") is not False:
        raise SearchOSRuntimeError("required-needs block requires unresolved slots")
    readiness_digest = _digest_token(
        safe.get("readiness_projection_digest"),
        "readiness_projection_digest",
    )
    readiness_core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key
        not in {
            "readiness_projection_id",
            "readiness_projection_digest",
            "replay_identity",
        }
    }
    if (
        safe.get("owner") != SEARCHOS_OWNER
        or safe.get("canonical_state") is not True
        or _digest(readiness_core) != readiness_digest
        or safe.get("readiness_projection_id")
        != f"searchos-readiness:{readiness_digest[:24]}"
        or safe.get("replay_identity")
        != f"searchos-readiness:{readiness_digest}"
    ):
        raise SearchOSRuntimeError(
            "required-needs block requires canonical current readiness"
        )
    unresolved_slot_refs = [
        _required_ref(item.get("slot_ref"), "unresolved slot_ref")
        for item in unresolved
    ]
    unresolved_slot_ids = [
        _token(item.get("slot_id"), "unresolved slot_id", limit=200)
        for item in unresolved_slot_refs
    ]
    if (
        len(unresolved_slot_ids) != len(set(unresolved_slot_ids))
        or any(
            not ref.get("component_id")
            or not ref.get("source_obligation_id")
            for ref in unresolved_slot_refs
        )
    ):
        raise SearchOSRuntimeError(
            "required-needs block has malformed unresolved slot identity"
        )
    validated_blocker_facts = _validated_searchos_blocker_facts(
        blocker_facts,
        unresolved_slot_ids=unresolved_slot_ids,
    )
    core = {
        "schema_version": SEARCHOS_REQUIRED_NEEDS_BLOCK_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "block_type": SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED,
        "run_id": safe.get("run_id"),
        "request_id": safe.get("request_id"),
        "readiness_projection_ref": {
            "readiness_projection_id": safe.get("readiness_projection_id"),
            "readiness_projection_digest": safe.get("readiness_projection_digest"),
        },
        "unresolved_required_slots": unresolved,
        "blocker_facts": validated_blocker_facts,
        "query_authorized": False,
        "read_authorized": False,
        "retry_authorized": False,
        "recovery_authorized": False,
        "deterministic_semantic_fallback_invoked": False,
        "semantic_receiver_ready": False,
        "sufficiency_adjudication_required": True,
        "satisfaction_or_coverage_upgrade_created": False,
        "stop_insufficient_emitted": False,
        "final_whole_run_stopping_decided": False,
        "subordinate_to_sufficiency": True,
        "canonical_state": True,
    }
    digest = _digest(core)
    block = {
        **core,
        "block_id": f"searchos-required-needs-block:{digest[:24]}",
        "block_digest": digest,
        "replay_identity": f"searchos-required-needs-block:{digest}",
    }
    return validate_searchos_required_needs_block(block)


def _validated_searchos_blocker_facts(
    blocker_facts: Sequence[Mapping[str, Any]],
    *,
    unresolved_slot_ids: Sequence[str],
) -> list[dict[str, str]]:
    unresolved_ids = set(unresolved_slot_ids)
    if not blocker_facts:
        raise SearchOSRuntimeError(
            "required-needs block requires canonical blocker facts"
        )
    facts: list[dict[str, str]] = []
    seen_event_keys: set[tuple[str, str]] = set()
    covered_slot_ids: set[str] = set()
    for item in blocker_facts:
        if not isinstance(item, Mapping):
            raise SearchOSRuntimeError(
                "required-needs blocker fact must be a mapping"
            )
        blocker_class = _token(
            item.get("blocker_class"),
            "blocker_class",
            limit=80,
        )
        interpretation = _token(
            item.get("interpretation"),
            "blocker interpretation",
            limit=80,
        )
        reason_code = _token(
            item.get("reason_code"),
            "blocker reason_code",
            limit=240,
        )
        slot_id = _token(
            item.get("slot_id"),
            "blocker slot_id",
            limit=200,
        )
        expected_interpretation = (
            SEARCHOS_BLOCKER_INTERPRETATION_BY_CLASS.get(blocker_class)
        )
        if (
            interpretation not in SEARCHOS_BLOCKER_INTERPRETATIONS
            or expected_interpretation != interpretation
        ):
            raise SearchOSRuntimeError(
                "required-needs blocker interpretation is absent, unknown, "
                "or inconsistent with its producing branch"
            )
        if slot_id not in unresolved_ids:
            raise SearchOSRuntimeError(
                "required-needs blocker slot identity is stale or foreign"
            )
        event_key = (slot_id, blocker_class)
        if event_key in seen_event_keys:
            raise SearchOSRuntimeError(
                "required-needs blocker facts ambiguously duplicate one "
                "exact slot event"
            )
        seen_event_keys.add(event_key)
        covered_slot_ids.add(slot_id)
        facts.append(
            {
                "blocker_class": blocker_class,
                "interpretation": interpretation,
                "reason_code": reason_code,
                "slot_id": slot_id,
            }
        )
    if covered_slot_ids != unresolved_ids:
        raise SearchOSRuntimeError(
            "required-needs blocker facts do not cover every unresolved slot"
        )
    return facts


def validate_searchos_required_needs_block(
    block: Mapping[str, Any],
    *,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    safe = _mapping(block)
    if (
        safe.get("schema_version")
        != SEARCHOS_REQUIRED_NEEDS_BLOCK_SCHEMA_VERSION
        or safe.get("owner") != SEARCHOS_OWNER
        or safe.get("block_type")
        != SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED
        or safe.get("canonical_state") is not True
    ):
        raise SearchOSRuntimeError(
            "required-needs block schema, owner, type, or canonical state mismatch"
        )
    claimed = _digest_token(safe.get("block_digest"), "block_digest")
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key not in {"block_id", "block_digest", "replay_identity"}
    }
    if (
        _digest(core) != claimed
        or safe.get("block_id")
        != f"searchos-required-needs-block:{claimed[:24]}"
        or safe.get("replay_identity")
        != f"searchos-required-needs-block:{claimed}"
    ):
        raise SearchOSRuntimeError(
            "required-needs block digest or identity mismatch"
        )
    run_id = _token(safe.get("run_id"), "block run_id")
    request_id = _token(safe.get("request_id"), "block request_id")
    readiness_ref = _required_ref(
        safe.get("readiness_projection_ref"),
        "readiness_projection_ref",
    )
    _token(
        readiness_ref.get("readiness_projection_id"),
        "readiness_projection_id",
        limit=200,
    )
    _digest_token(
        readiness_ref.get("readiness_projection_digest"),
        "readiness_projection_digest",
    )
    unresolved = [
        _mapping(item)
        for item in safe.get("unresolved_required_slots") or ()
        if isinstance(item, Mapping)
    ]
    unresolved_slot_refs = [
        _required_ref(item.get("slot_ref"), "unresolved slot_ref")
        for item in unresolved
    ]
    unresolved_slot_ids = [
        _token(item.get("slot_id"), "unresolved slot_id", limit=200)
        for item in unresolved_slot_refs
    ]
    if (
        not unresolved_slot_ids
        or len(unresolved_slot_ids) != len(set(unresolved_slot_ids))
        or any(
            not ref.get("component_id")
            or not ref.get("source_obligation_id")
            for ref in unresolved_slot_refs
        )
    ):
        raise SearchOSRuntimeError(
            "required-needs block has malformed unresolved slot identity"
        )
    raw_facts = safe.get("blocker_facts")
    if not isinstance(raw_facts, Sequence) or isinstance(
        raw_facts, str | bytes
    ):
        raise SearchOSRuntimeError(
            "required-needs block blocker facts are malformed"
        )
    _validated_searchos_blocker_facts(
        list(raw_facts),
        unresolved_slot_ids=unresolved_slot_ids,
    )
    if any(
        safe.get(field) is not False
        for field in (
            "query_authorized",
            "read_authorized",
            "retry_authorized",
            "recovery_authorized",
        )
    ):
        raise SearchOSRuntimeError(
            "required-needs block broadens closed authority"
        )
    if (
        safe.get("semantic_receiver_ready") is not False
        or safe.get("sufficiency_adjudication_required") is not True
        or safe.get("subordinate_to_sufficiency") is not True
        or any(
            field in safe
            for field in (
                "successful_sufficiency_allowed",
                "final_answer_packet_allowed",
                "author_execution_allowed",
            )
        )
    ):
        raise SearchOSRuntimeError(
            "required-needs block must remain subordinate to Sufficiency"
        )
    if state is not None:
        canonical_state = _validated_state_copy(state)
        if (
            canonical_state.get("run_id") != run_id
            or canonical_state.get("request_id") != request_id
            or _mapping(canonical_state.get("readiness_projection_ref"))
            != readiness_ref
        ):
            raise SearchOSRuntimeError(
                "required-needs block run, request, or readiness ref is stale"
            )
        required_slot_ids = set(
            canonical_state.get("required_slot_ids") or ()
        )
        slots_by_id = _mapping(canonical_state.get("slots_by_id"))
        for slot_ref in unresolved_slot_refs:
            slot_id = slot_ref["slot_id"]
            if (
                slot_id not in required_slot_ids
                or _mapping(_mapping(slots_by_id.get(slot_id)).get("slot_ref"))
                != slot_ref
            ):
                raise SearchOSRuntimeError(
                    "required-needs block unresolved slot is stale or foreign"
                )
        current_ref = _mapping(
            canonical_state.get("required_needs_block_ref")
        )
        if current_ref and current_ref != {
            "block_id": safe["block_id"],
            "block_digest": claimed,
            "block_type": safe["block_type"],
        }:
            raise SearchOSRuntimeError(
                "required-needs block reference is not current"
            )
        current_block = _mapping(
            canonical_state.get("required_needs_block")
        )
        if current_block and current_block != safe:
            raise SearchOSRuntimeError(
                "required-needs block payload is not current"
            )
    return deepcopy(safe)


def _readiness_failure_reason(slot: Mapping[str, Any], outcome: Mapping[str, Any]) -> str:
    posture = str(slot.get("posture") or "")
    if posture in {
        SearchOSSlotPosture.UNRESOLVED_HANDOFF.value,
        SearchOSSlotPosture.JUDGMENT_FAILED.value,
        SearchOSSlotPosture.BUDGET_EXHAUSTED.value,
        SearchOSSlotPosture.STALE_OR_INVALID.value,
        SearchOSSlotPosture.CLARIFICATION_REQUIRED.value,
        SearchOSSlotPosture.AWAITING_INTERPRETATION_BINDING.value,
    }:
        return posture
    if outcome.get("material_authority") != (SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value):
        return "candidate_only_or_directional_context_only"
    if not _optional_ref(outcome.get("semantic_handoff_ref")):
        return "semantic_handoff_missing_or_rejected"
    if not _optional_ref(outcome.get("component_analyst_proposal_ref")):
        return "component_analyst_proposal_missing_or_rejected"
    if outcome.get("component_dprime_validation_status") != "accepted":
        return "component_dprime_validation_missing_or_rejected"
    if outcome.get("semantic_admission_status") != "admitted":
        return "runkernel_semantic_admission_missing_or_rejected"
    return "stale_or_invalid"


def _validated_policy_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _validated_digest_envelope(
        value,
        schema_version=SEARCHOS_POLICY_SCHEMA_VERSION,
        digest_field="policy_snapshot_digest",
        id_field="policy_snapshot_id",
        identity_prefix="searchos-policy",
        label="SearchOS policy",
    )
    fields = set(next(iter(_NAVIGATION_LIMITS_BY_PROFILE.values())))
    present = fields.intersection(safe)
    if safe.get("navigation_runtime_open") is True:
        try:
            limits = _NAVIGATION_LIMITS_BY_PROFILE[SearchOSProfileName(str(safe.get("profile_name")))]
        except (KeyError, ValueError) as exc:
            raise SearchOSRuntimeError("navigation policy profile is invalid") from exc
        if present != fields or any(safe.get(key) != value for key, value in limits.items()):
            raise SearchOSRuntimeError("opened navigation policy limits are invalid")
    elif safe.get("navigation_runtime_open") is not False or present:
        raise SearchOSRuntimeError("closed navigation policy contains navigation limits")
    recovery = _mapping(safe.get("existing_gap_recovery_policy"))
    if (
        recovery.get("schema_version")
        != "searchos_existing_gap_recovery_policy_v1"
        or not isinstance(recovery.get("runtime_open"), bool)
        or int(recovery.get("maximum_cycles_per_run") or -1) != 1
        or recovery.get("required_gaps_prioritized") is not True
        or recovery.get("optional_gap_recovery_authorized") is not False
        or recovery.get("same_limits_for_all_profiles") is not True
        or recovery.get("whole_run_lease_required") is not True
    ):
        raise SearchOSRuntimeError(
            "existing-gap recovery policy is invalid or profile-dependent"
        )
    generalized = _mapping(safe.get("recovery_policy"))
    expected_limits = {
        "fast": (1, 0, 1),
        "balanced": (1, 1, 2),
        "deep": (1, 2, 3),
    }.get(str(safe.get("profile_name") or "").casefold())
    if (
        generalized.get("schema_version") != "searchos_recovery_policy_v2"
        or not isinstance(generalized.get("runtime_open"), bool)
        or expected_limits is None
        or (
            generalized.get("maximum_existing_component_cycles_per_run"),
            generalized.get("maximum_searched_premise_cycles_per_run"),
            generalized.get("maximum_total_cycles_per_run"),
        )
        != expected_limits
        or generalized.get("one_linear_active_cycle") is not True
        or generalized.get("one_searched_premise_per_generation") is not True
        or generalized.get("maximum_searched_generation") != 2
        or generalized.get("generation_three_rejected_before_work") is not True
        or generalized.get("whole_run_lease_required") is not True
    ):
        raise SearchOSRuntimeError("generalized SearchOS recovery policy is invalid")
    return safe


def _validated_candidate_use_option(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(value)
    _require_schema(
        safe,
        SEARCHOS_CANDIDATE_USE_OPTION_SCHEMA_VERSION,
        "candidate-use option",
    )
    normalized_url = normalize_discovery_result_url(safe.get("normalized_url"))
    if safe.get("owner") != SEARCHOS_OWNER or safe.get("normalized_url") != normalized_url:
        raise SearchOSRuntimeError("candidate-use option stable fields are invalid")
    if int(safe.get("option_ordinal") or 0) <= 0:
        raise SearchOSRuntimeError("candidate-use option ordinal is invalid")
    stable_core = {
        "schema_version": safe.get("schema_version"),
        "owner": safe.get("owner"),
        "slot_ref": _required_ref(safe.get("slot_ref"), "slot_ref"),
        "normalized_url": normalized_url,
    }
    digest = _digest(stable_core)
    if safe.get("candidate_use_option_digest") != digest:
        raise SearchOSRuntimeError("candidate-use option stable digest mismatch")
    if (
        safe.get("candidate_use_option_id") != f"searchos-option:{digest[:24]}"
        or safe.get("replay_identity") != f"searchos-option:{digest}"
    ):
        raise SearchOSRuntimeError("candidate-use option stable identity mismatch")
    lineage = _mapping(safe.get("lineage_snapshot"))
    _require_schema(
        lineage,
        SEARCHOS_CANDIDATE_LINEAGE_SNAPSHOT_SCHEMA_VERSION,
        "candidate lineage snapshot",
    )
    lineage_core = {
        key: deepcopy(item)
        for key, item in lineage.items()
        if key not in {"lineage_snapshot_id", "lineage_snapshot_digest"}
    }
    complete_lineage_core = {
        key: deepcopy(item)
        for key, item in lineage_core.items()
        if key not in {"complete_lineage_digest", "lineage_revision"}
    }
    complete_lineage_digest = _digest(complete_lineage_core)
    if lineage.get("complete_lineage_digest") != complete_lineage_digest:
        raise SearchOSRuntimeError("candidate complete lineage digest mismatch")
    if lineage.get("owner") != SEARCHOS_OWNER:
        raise SearchOSRuntimeError("candidate lineage owner mismatch")
    if _mapping(lineage.get("candidate_use_option_ref")) != {
        "candidate_use_option_id": safe.get("candidate_use_option_id"),
        "candidate_use_option_digest": safe.get("candidate_use_option_digest"),
        "normalized_url": safe.get("normalized_url"),
        "slot_id": _mapping(safe.get("slot_ref")).get("slot_id"),
    }:
        raise SearchOSRuntimeError("candidate lineage stable option ref mismatch")
    lineage_digest = _digest(lineage_core)
    if (
        lineage.get("lineage_snapshot_digest") != lineage_digest
        or lineage.get("lineage_snapshot_id") != f"searchos-option-lineage:{lineage_digest[:24]}"
    ):
        raise SearchOSRuntimeError("candidate lineage snapshot identity mismatch")
    expected_ref = {
        "lineage_snapshot_id": lineage["lineage_snapshot_id"],
        "lineage_snapshot_digest": lineage_digest,
        "complete_lineage_digest": lineage.get("complete_lineage_digest"),
        "lineage_revision": lineage.get("lineage_revision"),
    }
    if _mapping(safe.get("lineage_snapshot_ref")) != expected_ref:
        raise SearchOSRuntimeError("candidate lineage snapshot ref mismatch")
    for projection_field in (
        "candidate_state_origin_refs",
        "candidate_refs",
        "query_plan_item_refs",
        "iteration_set_refs",
        "provider_result_occurrence_refs",
        "source_material_refs",
    ):
        if lineage.get(projection_field) != safe.get(projection_field):
            raise SearchOSRuntimeError(f"candidate lineage {projection_field} projection mismatch")
    occurrences = lineage.get("provider_result_occurrence_refs") or ()
    if int(lineage.get("lineage_revision") or 0) != max(1, len(occurrences)):
        raise SearchOSRuntimeError("candidate lineage revision mismatch")
    if (
        safe.get("material_authority") != SearchOSMaterialAuthority.DIRECTIONAL_CANDIDATE_CONTEXT.value
        or safe.get("read_eligible") is not True
        or safe.get("support_proposal_eligible") is not False
    ):
        raise SearchOSRuntimeError("candidate-use option authority fields are invalid")
    return deepcopy(safe)


def _validated_candidate_use_window(value: Mapping[str, Any]) -> dict[str, Any]:
    return _validated_digest_envelope(
        value,
        schema_version=SEARCHOS_CANDIDATE_USE_WINDOW_SCHEMA_VERSION,
        digest_field="candidate_use_window_digest",
        id_field="candidate_use_window_id",
        identity_prefix="searchos-window",
        label="candidate-use window",
    )


def _validated_read_custody_material_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return _validated_digest_envelope(
        value,
        schema_version="searchos_read_custody_material_ref_v1",
        digest_field="read_custody_material_digest",
        id_field="read_custody_material_id",
        identity_prefix="searchos-read-custody",
        label="SearchOS READ custody material",
    )


def _validated_semantic_handoff(value: Mapping[str, Any]) -> dict[str, Any]:
    return _validated_digest_envelope(
        value,
        schema_version=SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
        digest_field="semantic_handoff_digest",
        id_field="semantic_handoff_id",
        identity_prefix="searchos-semantic-handoff",
        label="SearchOS semantic handoff",
    )


def _validated_searchos_judgment_decision(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _mapping(value)
    if safe.get("schema_version") not in {
        SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION,
        SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
    }:
        raise SearchOSRuntimeError(
            "SearchOS judgment decision schema version mismatch"
        )
    claimed = _digest_token(
        safe.get("judgment_decision_digest"),
        "judgment_decision_digest",
    )
    core = {
        key: deepcopy(item)
        for key, item in safe.items()
        if key
        not in {
            "judgment_decision_id",
            "judgment_decision_digest",
            "replay_identity",
        }
    }
    if _digest(core) != claimed:
        raise SearchOSRuntimeError("SearchOS judgment decision digest mismatch")
    if (
        safe.get("judgment_decision_id")
        != f"searchos-decision:{claimed[:24]}"
        or safe.get("replay_identity") != f"searchos-decision:{claimed}"
    ):
        raise SearchOSRuntimeError(
            "SearchOS judgment decision identity mismatch"
        )
    return deepcopy(safe)


def _accepted_binding_scope(
    state: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    slot: Mapping[str, Any],
    *,
    require_binding_eligible: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _mapping(accepted_contract)
    contract_digest = _digest_token(
        contract.get("accepted_contract_digest"),
        "accepted_contract_digest",
    )
    contract_version = _token(
        contract.get("accepted_contract_version"),
        "accepted_contract_version",
    )
    answer_contract_ref = _mapping(state.get("answer_contract_ref"))
    if (
        answer_contract_ref.get("answer_contract_digest") != contract_digest
        or answer_contract_ref.get("contract_version") != contract_version
        or (
            contract.get("run_id")
            and contract.get("run_id") != state.get("run_id")
        )
        or (
            contract.get("request_id")
            and contract.get("request_id") != state.get("request_id")
        )
    ):
        raise SearchOSRuntimeError(
            "accepted AnswerContract does not match SearchOS state"
        )
    slot_component_ref = _mapping(slot.get("component_ref"))
    component_id = _first_ref_id(slot_component_ref)
    accepted_component = next(
        (
            _mapping(item)
            for item in contract.get("accepted_answer_component_refs") or ()
            if _mapping(item).get("component_id") == component_id
        ),
        {},
    )
    if not accepted_component:
        raise SearchOSRuntimeError(
            "SearchOS binding component is absent from accepted AnswerContract"
        )
    for field in (
        "component_id",
        "component_revision",
        "component_digest",
    ):
        if slot_component_ref.get(field) != accepted_component.get(field):
            raise SearchOSRuntimeError(
                "SearchOS binding component identity is stale"
            )
    slot_semantic_ref = _mapping(slot.get("semantic_slot_ref"))
    semantic_slot_id = _token(
        slot_semantic_ref.get("slot_id"),
        "semantic_slot_id",
    )
    if semantic_slot_id not in {
        str(value)
        for value in accepted_component.get("semantic_slot_ids") or ()
    }:
        raise SearchOSRuntimeError(
            "semantic slot is not owned by the accepted component"
        )
    accepted_semantic = next(
        (
            _mapping(item)
            for item in contract.get("accepted_semantic_slot_refs") or ()
            if _mapping(item).get("slot_id") == semantic_slot_id
        ),
        {},
    )
    if not accepted_semantic:
        raise SearchOSRuntimeError(
            "semantic slot is absent from accepted AnswerContract"
        )
    expected_semantic = {
        "slot_id": semantic_slot_id,
        "slot_kind": _bounded_optional(
            accepted_semantic.get("slot_kind"), 80
        ),
        "status": _bounded_optional(accepted_semantic.get("status"), 80),
        "materiality": _bounded_optional(
            accepted_semantic.get("materiality"), 80
        ),
        "candidate_values": [
            str(value)
            for value in accepted_semantic.get("candidate_values") or ()
        ],
        "selected_value": _bounded_optional(
            accepted_semantic.get("selected_value"), 220
        ),
        "user_confirmation_required": bool(
            accepted_semantic.get("user_confirmation_required", False)
        ),
        "unresolved_material": bool(
            accepted_semantic.get("unresolved_material", False)
        ),
    }
    if slot_semantic_ref != expected_semantic:
        raise SearchOSRuntimeError(
            "SearchOS semantic-slot projection is stale or altered"
        )
    if require_binding_eligible:
        if (
            expected_semantic.get("slot_kind")
            not in SEARCHOS_INTERPRETATION_BINDING_CATEGORY_BY_SLOT_KIND
            or expected_semantic.get("unresolved_material") is not True
            or expected_semantic.get("user_confirmation_required") is True
            or not expected_semantic.get("candidate_values")
            or expected_semantic.get("selected_value") is not None
        ):
            raise SearchOSRuntimeError(
                "accepted semantic slot is not eligible for factual binding"
            )
    return deepcopy(slot_component_ref), expected_semantic


def _validate_binding_basis_refs(
    slot: Mapping[str, Any],
    *,
    candidate_basis: Sequence[Mapping[str, Any]],
    read_basis: Sequence[Mapping[str, Any]],
) -> None:
    if not candidate_basis and not read_basis:
        raise SearchOSRuntimeError(
            "interpretation binding requires exact current basis refs"
        )
    current_candidates = {
        _first_ref_id(_mapping(item)): _mapping(item)
        for item in slot.get("candidate_use_option_refs") or ()
    }
    current_custody = {
        _first_ref_id(_mapping(item)): _mapping(item)
        for item in slot.get("custody_refs") or ()
    }
    for item in candidate_basis:
        identity = _first_ref_id(item)
        if identity not in current_candidates or _mapping(item) != _mapping(
            current_candidates[identity]
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding candidate basis is stale or altered"
            )
    for item in read_basis:
        identity = _first_ref_id(item)
        if identity not in current_custody or _mapping(item) != _mapping(
            current_custody[identity]
        ):
            raise SearchOSRuntimeError(
                "interpretation-binding READ basis is stale or altered"
            )


def _validated_digest_envelope(
    value: Mapping[str, Any],
    *,
    schema_version: str,
    digest_field: str,
    id_field: str,
    identity_prefix: str,
    label: str,
) -> dict[str, Any]:
    safe = _mapping(value)
    _require_schema(safe, schema_version, label)
    claimed = _digest_token(safe.get(digest_field), digest_field)
    _token(safe.get(id_field), id_field)
    core = {key: deepcopy(item) for key, item in safe.items() if key not in {id_field, digest_field, "replay_identity"}}
    if _digest(core) != claimed:
        raise SearchOSRuntimeError(f"{label} digest mismatch")
    if (
        safe.get(id_field) != f"{identity_prefix}:{claimed[:24]}"
        or safe.get("replay_identity") != f"{identity_prefix}:{claimed}"
    ):
        raise SearchOSRuntimeError(f"{label} identity mismatch")
    return deepcopy(safe)


def _with_state_digest(core: Mapping[str, Any]) -> dict[str, Any]:
    safe = deepcopy(dict(core))
    digest = _digest(safe)
    return {
        **safe,
        "state_id": f"searchos-state:{digest[:24]}",
        "state_digest": digest,
        "replay_identity": f"searchos-state:{digest}",
    }


def _refresh_state(state: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in state.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    return _with_state_digest(core)


def _validated_state_copy(state: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(state)
    _require_schema(safe, SEARCHOS_STATE_SCHEMA_VERSION, "SearchOS state")
    claimed = _digest_token(safe.get("state_digest"), "state_digest")
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key not in {"state_id", "state_digest", "replay_identity"}
    }
    if _digest(core) != claimed:
        raise SearchOSRuntimeError("SearchOS state digest mismatch")
    if (
        safe.get("state_id") != f"searchos-state:{claimed[:24]}"
        or safe.get("replay_identity") != f"searchos-state:{claimed}"
    ):
        raise SearchOSRuntimeError("SearchOS state identity mismatch")
    return deepcopy(safe)


def _refresh_slot(slot: Mapping[str, Any]) -> dict[str, Any]:
    safe = deepcopy(dict(slot))
    safe.pop("slot_state_digest", None)
    safe["slot_state_digest"] = _digest(safe)
    return safe


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mutable_mapping(value: Any) -> dict[str, Any]:
    return deepcopy(_mapping(value))


def _json_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchOSRuntimeError("expected bounded mapping")
    try:
        return json.loads(json.dumps(dict(value), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise SearchOSRuntimeError("mapping is not JSON-safe") from exc


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise SearchOSRuntimeError("SearchOS contract is not JSON-safe") from exc
    return sha256(encoded.encode("utf-8")).hexdigest()


def _token(value: Any, label: str, *, limit: int = 320) -> str:
    token = str(value or "").strip()
    if not token or len(token) > limit:
        raise SearchOSRuntimeError(f"SearchOS contract requires bounded {label}")
    return token


def _digest_token(value: Any, label: str) -> str:
    token = _token(value, label, limit=128)
    if len(token) != 64 or any(character not in "0123456789abcdef" for character in token):
        raise SearchOSRuntimeError(f"SearchOS contract requires sha256 {label}")
    return token


def _bounded_optional(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    token = " ".join(str(value).split()).strip()
    if not token:
        return None
    if len(token) > limit:
        raise SearchOSRuntimeError("SearchOS bounded text exceeds its contract")
    return token


def _bounded_reason(value: Any) -> str:
    reason = _bounded_optional(value, MAX_UNRESOLVED_REASON_CHARS)
    if not reason:
        raise SearchOSRuntimeError("SearchOS action requires a bounded reason")
    return reason


def _reason_code(value: Any) -> str:
    code = _token(value, "reason_code", limit=80)
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_.:-" for character in code):
        raise SearchOSRuntimeError("SearchOS reason_code is not bounded vocabulary")
    return code


def _required_ref(value: Any, label: str) -> dict[str, Any]:
    ref = _mapping(value)
    if not ref or not _first_ref_id(ref) or not _first_digest(ref):
        raise SearchOSRuntimeError(f"SearchOS contract requires exact {label}")
    return deepcopy(ref)


def _optional_ref(value: Any) -> dict[str, Any]:
    ref = _mapping(value)
    if not ref:
        return {}
    if not _first_ref_id(ref) or not _first_digest(ref):
        raise SearchOSRuntimeError("SearchOS optional ref is incomplete")
    return deepcopy(ref)


def _first_ref_id(ref: Mapping[str, Any]) -> str:
    for key, value in ref.items():
        if key.endswith("_id") and value:
            return str(value)
    return ""


def _first_digest(ref: Mapping[str, Any]) -> str:
    for key, value in ref.items():
        if key.endswith("_digest") and isinstance(value, str) and len(value) == 64:
            return value
    return ""


def _ref_key(ref: Mapping[str, Any]) -> tuple[str, str]:
    key = (_first_ref_id(ref), _first_digest(ref))
    if not all(key):
        raise SearchOSRuntimeError("SearchOS lineage contains incomplete ref")
    return key


def _interpretation_binding_key(
    ref: Mapping[str, Any],
) -> tuple[str, str]:
    safe = _mapping(ref)
    binding_id = _token(
        safe.get("interpretation_binding_id"),
        "interpretation_binding_id",
    )
    binding_digest = str(
        safe.get("interpretation_binding_digest") or ""
    )
    if len(binding_digest) != 64:
        raise SearchOSRuntimeError(
            "interpretation-binding ref lacks exact identity"
        )
    return binding_id, binding_digest


def _compact_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(value)
    out = {
        key: item
        for key, item in safe.items()
        if key.endswith("_id") or key.endswith("_digest") or key == "schema_version"
    }
    if not _first_ref_id(out) or not _first_digest(out):
        raise SearchOSRuntimeError("SearchOS compact ref lacks identity")
    return out


def _require_schema(value: Mapping[str, Any], expected: str, label: str) -> None:
    if value.get("schema_version") != expected:
        raise SearchOSRuntimeError(f"{label} schema version mismatch")


__all__ = [
    "CANDIDATE_USE_WINDOW_SIZE",
    "MAXIMUM_ACTIVE_SLOTS",
    "SEARCHOS_BLOCKER_INTERPRETATION_BY_CLASS",
    "SEARCHOS_BLOCKER_INTERPRETATIONS",
    "SEARCHOS_EFFECTIVE_SEMANTIC_SLOT_VIEW_SCHEMA_VERSION",
    "SEARCHOS_INTERPRETATION_BINDING_SCHEMA_VERSION",
    "SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION",
    "SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION",
    "SEARCHOS_REQUIRED_NEEDS_BLOCK_SCHEMA_VERSION",
    "SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED",
    "SearchOSJudgmentAction",
    "SearchOSMaterialAuthority",
    "SearchOSPolicyProfileV1",
    "SearchOSProfileName",
    "SearchOSRequirementPosture",
    "SearchOSRuntimeError",
    "SearchOSSlotPosture",
    "begin_searchos_judgment_round",
    "build_candidate_use_options_v1",
    "build_candidate_use_window_v1",
    "build_searchos_initial_state",
    "build_searchos_effective_semantic_slot_view",
    "build_searchos_interpretation_binding_v1",
    "build_searchos_iteration_candidate_set_v1",
    "build_searchos_judgment_request_v1",
    "build_searchos_navigation_judgment_request_v1",
    "build_searchos_policy_snapshot",
    "build_searchos_read_custody_material_ref",
    "build_searchos_revision_1_candidate_state_v1",
    "build_searchos_required_needs_block",
    "build_searchos_semantic_evaluation_handoff_v1",
    "build_searchos_slice_a_readiness_v1",
    "candidate_use_option_ref",
    "candidate_use_window_ref",
    "charge_searchos_judgment_call",
    "mark_searchos_slot_budget_exhausted",
    "mark_searchos_slot_stale_or_invalid",
    "mark_searchos_slot_unresolved",
    "record_searchos_candidate_window",
    "record_searchos_judgment_failure",
    "record_searchos_iteration_candidate_set",
    "record_searchos_interpretation_binding",
    "record_searchos_read_custody_material",
    "record_searchos_readiness_projection",
    "return_searchos_pre_call_reservation",
    "record_searchos_required_needs_block",
    "record_searchos_semantic_handoff",
    "reduce_searchos_judgment_decision",
    "searchos_iteration_candidate_set_ref",
    "searchos_interpretation_binding_ref",
    "searchos_policy_profile",
    "searchos_policy_snapshot_ref",
    "searchos_revision_1_candidate_state_ref",
    "searchos_semantic_handoff_ref",
    "validate_searchos_append_only_lineage",
    "validate_searchos_iteration_candidate_set",
    "validate_searchos_interpretation_binding",
    "validate_searchos_judgment_model_output",
    "validate_searchos_required_needs_block",
    "validate_searchos_revision_1_candidate_state",
    "validate_searchos_state",
]
