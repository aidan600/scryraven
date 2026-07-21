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
from typing import Any, Mapping, Sequence

from core.discovery_source_result import normalize_discovery_result_url

SEARCHOS_OWNER = "RunKernel.SearchOSIterativeJudgment"
SEARCHOS_POLICY_SCHEMA_VERSION = "searchos_policy_profile_v1"
SEARCHOS_STATE_SCHEMA_VERSION = "searchos_iterative_judgment_state_v1"
SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION = (
    "searchos_iteration_candidate_set_v1"
)
SEARCHOS_CANDIDATE_USE_OPTION_SCHEMA_VERSION = "searchos_candidate_use_option_v1"
SEARCHOS_CANDIDATE_USE_WINDOW_SCHEMA_VERSION = "candidate_use_window_v1"
SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION = "searchos_judgment_request_v1"
SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION = "searchos_judgment_decision_v1"
SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION = (
    "searchos_semantic_evaluation_handoff_v1"
)
SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION = "searchos_slice_a_readiness_v1"
SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED = (
    "SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED"
)

MAXIMUM_ACTIVE_SLOTS = 8
CANDIDATE_USE_WINDOW_SIZE = 12
MAX_FOLLOWUP_QUERY_CHARS = 300
MAX_UNRESOLVED_REASON_CHARS = 240


class SearchOSRuntimeError(ValueError):
    """Raised when SearchOS authority or lineage validation fails closed."""


class SearchOSProfileName(str, Enum):
    FAST = "Fast"
    BALANCED = "Balanced"
    DEEP = "Deep"


class SearchOSJudgmentAction(str, Enum):
    HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION = (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    )
    REQUEST_READ_PAGE = "REQUEST_READ_PAGE"
    PROPOSE_FOLLOWUP_QUERY = "PROPOSE_FOLLOWUP_QUERY"
    HANDOFF_UNRESOLVED = "HANDOFF_UNRESOLVED"


class SearchOSSlotPosture(str, Enum):
    ACTIVE_UNJUDGED = "active_unjudged"
    AWAITING_READ = "awaiting_read"
    AWAITING_FOLLOWUP_DISCOVER = "awaiting_followup_discover"
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
            "additional_judgment_call_pool_per_active_slot": (
                self.additional_judgment_call_pool_per_active_slot
            ),
            "candidate_windows_per_slot": self.candidate_windows_per_slot,
            "candidate_waves_per_slot": self.candidate_waves_per_slot,
            "read_nominations_per_slot": self.read_nominations_per_slot,
            "followup_query_nominations_per_slot": (
                self.followup_query_nominations_per_slot
            ),
            "navigation_runtime_open": self.navigation_runtime_open,
            "post_analyst_reentry_runtime_open": (
                self.post_analyst_reentry_runtime_open
            ),
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


def searchos_policy_profile(
    profile_name: SearchOSProfileName | str,
) -> SearchOSPolicyProfileV1:
    try:
        key = (
            profile_name
            if isinstance(profile_name, SearchOSProfileName)
            else SearchOSProfileName(str(profile_name))
        )
    except ValueError as exc:
        raise SearchOSRuntimeError("unsupported SearchOS policy profile") from exc
    return _POLICY_PROFILES[key]


def build_searchos_policy_snapshot(
    *,
    run_id: str,
    request_id: str,
    profile_name: SearchOSProfileName | str,
) -> dict[str, Any]:
    profile = searchos_policy_profile(profile_name)
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
    }
    digest = _digest(core)
    return {
        **core,
        "policy_snapshot_id": f"searchos-policy:{digest[:24]}",
        "policy_snapshot_digest": digest,
        "replay_identity": f"searchos-policy:{digest}",
    }


def searchos_policy_snapshot_ref(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(snapshot)
    _require_schema(safe, SEARCHOS_POLICY_SCHEMA_VERSION, "SearchOS policy")
    return {
        "policy_snapshot_id": _token(
            safe.get("policy_snapshot_id"), "policy_snapshot_id"
        ),
        "policy_snapshot_digest": _digest_token(
            safe.get("policy_snapshot_digest"), "policy_snapshot_digest"
        ),
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
    policy_ref = searchos_policy_snapshot_ref(policy_snapshot)
    policy = _mapping(policy_snapshot)
    if policy.get("run_id") != run or policy.get("request_id") != request:
        raise SearchOSRuntimeError("SearchOS policy snapshot scope mismatch")
    if not active_slots or len(active_slots) > int(policy["maximum_active_slots"]):
        raise SearchOSRuntimeError("SearchOS active-slot envelope is empty or exceeded")

    slots_by_id: dict[str, dict[str, Any]] = {}
    required_ids: list[str] = []
    optional_ids: list[str] = []
    for ordinal, raw_slot in enumerate(active_slots, start=1):
        slot = _mapping(raw_slot)
        slot_id = _token(slot.get("slot_id"), "slot_id")
        if slot_id in slots_by_id:
            raise SearchOSRuntimeError("duplicate SearchOS slot identity")
        try:
            requirement = SearchOSRequirementPosture(
                str(slot.get("requirement_posture") or "")
            )
        except ValueError as exc:
            raise SearchOSRuntimeError(
                "SearchOS slot required-versus-optional posture is ambiguous"
            ) from exc
        component_ref = _required_ref(slot.get("component_ref"), "component_ref")
        obligation_ref = _required_ref(
            slot.get("source_obligation_ref"), "source_obligation_ref"
        )
        slot_core = {
            "slot_id": slot_id,
            "slot_ordinal": ordinal,
            "component_ref": component_ref,
            "source_obligation_ref": obligation_ref,
            "requirement_posture": requirement.value,
            "posture": SearchOSSlotPosture.ACTIVE_UNJUDGED.value,
            "latest_reason": None,
            "current_candidate_state_ref": _optional_ref(
                initial_candidate_state_ref
            ),
            "current_window_ref": {},
            "candidate_use_option_refs": [],
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
        }
        slot_identity_digest = _digest(
            {
                "slot_id": slot_id,
                "component_ref": component_ref,
                "source_obligation_ref": obligation_ref,
                "requirement_posture": requirement.value,
            }
        )
        slot_core["slot_ref"] = {
            "slot_id": slot_id,
            "slot_digest": slot_identity_digest,
            "component_id": _first_ref_id(component_ref),
            "source_obligation_id": _first_ref_id(obligation_ref),
        }
        slot_core["slot_state_digest"] = _digest(slot_core)
        slots_by_id[slot_id] = slot_core
        (required_ids if requirement is SearchOSRequirementPosture.REQUIRED else optional_ids).append(
            slot_id
        )

    reserved_per_required = int(
        policy["minimum_reserved_judgment_calls_per_required_slot"]
    )
    shared_pool = len(slots_by_id) * int(
        policy["additional_judgment_call_pool_per_active_slot"]
    )
    budget = {
        "judgment_call_ceiling": len(required_ids) * reserved_per_required
        + shared_pool,
        "reserved_calls_remaining_by_required_slot": {
            slot_id: reserved_per_required for slot_id in required_ids
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
        "optional_slot_ids": optional_ids,
        "initial_candidate_state_ref": _optional_ref(initial_candidate_state_ref),
        "current_candidate_state_ref": _optional_ref(initial_candidate_state_ref),
        "iteration_candidate_set_refs": [],
        "budget": budget,
        "semantic_handoff_refs": [],
        "readiness_projection_ref": {},
        "required_needs_block_ref": {},
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "known_url_read_runtime_open": False,
        "search_attached_content_custody_runtime_open": False,
        "comprehensive_recovery_runtime_open": False,
        "whole_run_stopping_runtime_open": False,
    }
    return _with_state_digest(state_core)


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
    remaining = _mutable_mapping(
        budget["reserved_calls_remaining_by_required_slot"]
    )
    required = set(candidate["required_slot_ids"])
    unavailable = [
        slot_id
        for slot_id in ordered_ids
        if slot_id in required and int(remaining.get(slot_id) or 0) <= 0
    ]
    if unavailable:
        raise SearchOSRuntimeError(
            "complete-round reservation unavailable for required slot(s): "
            + ",".join(unavailable)
        )
    round_ordinal = len(budget["round_history"]) + 1
    reservation_core = {
        "schema_version": "searchos_judgment_round_reservation_v1",
        "round_ordinal": round_ordinal,
        "participating_slot_ids": ordered_ids,
        "required_slot_reservations": [
            {
                "slot_id": slot_id,
                "capacity_source": "required_slot_reserve",
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
    }
    budget["round_history"].append(reservation)
    candidate["budget"] = budget
    return _refresh_state(candidate), deepcopy(reservation)


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
    round_id = _token(reservation_ref.get("reservation_id"), "reservation_id")
    history = list(budget["round_history"])
    round_index = next(
        (index for index, item in enumerate(history) if item.get("reservation_id") == round_id),
        None,
    )
    if round_index is None:
        raise SearchOSRuntimeError("judgment charge reservation is stale")
    round_record = deepcopy(history[round_index])
    if slot_token not in round_record["participating_slot_ids"]:
        raise SearchOSRuntimeError("judgment charge slot was not reserved in this round")
    if any(
        item.get("slot_id") == slot_token and item.get("charged") is True
        for item in budget["charge_history"]
    ):
        # Multiple rounds are legal, so reject only a duplicate charge for this round.
        if any(
            item.get("slot_id") == slot_token
            and item.get("reservation_id") == round_id
            for item in budget["charge_history"]
        ):
            raise SearchOSRuntimeError("judgment reservation was already charged")

    required = slot_token in set(candidate["required_slot_ids"])
    remaining = _mutable_mapping(
        budget["reserved_calls_remaining_by_required_slot"]
    )
    capacity_source = "shared_pool"
    if required and int(remaining.get(slot_token) or 0) > 0:
        remaining[slot_token] = int(remaining[slot_token]) - 1
        capacity_source = "required_slot_reserve"
    else:
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
    budget["charged_logical_judgment_calls"] = int(
        budget["charged_logical_judgment_calls"]
    ) + 1
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
    charge_id = _token(charge_ref.get("charge_id"), "charge_id")
    budget = _mutable_mapping(candidate["budget"])
    charge = next(
        (item for item in budget["charge_history"] if item.get("charge_id") == charge_id),
        None,
    )
    if not charge:
        raise SearchOSRuntimeError("judgment failure charge is stale")
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
    budget["failed_logical_judgment_calls"] = int(
        budget["failed_logical_judgment_calls"]
    ) + 1
    candidate["slots_by_id"] = slots
    candidate["budget"] = budget
    return _refresh_state(candidate)


def mark_searchos_slot_budget_exhausted(
    state: Mapping[str, Any], *, slot_id: str, reason: str
) -> dict[str, Any]:
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


def record_searchos_iteration_candidate_set(
    state: Mapping[str, Any], *, candidate_set: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    admitted = validate_searchos_iteration_candidate_set(candidate_set)
    if admitted.get("run_id") != candidate.get("run_id") or admitted.get(
        "request_id"
    ) != candidate.get("request_id"):
        raise SearchOSRuntimeError("iteration candidate set scope mismatch")
    if _mapping(admitted.get("parent_candidate_state_ref")) != _mapping(
        candidate.get("current_candidate_state_ref")
    ):
        raise SearchOSRuntimeError("iteration candidate set parent became stale")
    slot_id = _token(
        _mapping(admitted.get("active_slot_ref")).get("slot_id"), "slot_id"
    )
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_id not in slots:
        raise SearchOSRuntimeError("iteration candidate set references inactive slot")
    slot = deepcopy(slots[slot_id])
    if slot.get("posture") != (
        SearchOSSlotPosture.AWAITING_FOLLOWUP_DISCOVER.value
    ):
        raise SearchOSRuntimeError(
            "iteration candidate set does not follow an authorized follow-up"
        )
    policy = _mapping(candidate["policy_snapshot"])
    if int(slot["candidate_wave_count"]) >= int(
        policy["candidate_waves_per_slot"]
    ):
        return mark_searchos_slot_budget_exhausted(
            candidate,
            slot_id=slot_id,
            reason="candidate_wave_budget_exhausted",
        )
    ref = searchos_iteration_candidate_set_ref(admitted)
    slot["candidate_wave_count"] = int(slot["candidate_wave_count"]) + 1
    slot["current_candidate_state_ref"] = ref
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
    candidate["current_candidate_state_ref"] = ref
    return _refresh_state(candidate)


def record_searchos_read_custody_material(
    state: Mapping[str, Any], *, custody_material_ref: Mapping[str, Any]
) -> dict[str, Any]:
    """Register exact post-READ EvidenceLedger custody and reopen judgment."""

    candidate = _validated_state_copy(state)
    custody = _required_ref(custody_material_ref, "read_custody_material_ref")
    if custody.get("material_authority") != (
        SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value
    ):
        raise SearchOSRuntimeError("DISCOVER material cannot register as READ custody")
    if custody.get("readable") is not True or custody.get("stale") is True:
        raise SearchOSRuntimeError("READ custody material is unreadable or stale")
    if not _optional_ref(custody.get("evidence_ledger_custody_ref")):
        raise SearchOSRuntimeError(
            "SearchOS READ material requires EvidenceLedger custody"
        )
    option_ref = _required_ref(
        custody.get("candidate_use_option_ref"), "candidate_use_option_ref"
    )
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
    existing = {
        _first_ref_id(item): item for item in slot.get("custody_refs") or ()
    }
    custody_id = _first_ref_id(custody)
    if custody_id not in existing:
        slot["custody_refs"].append(deepcopy(custody))
    elif existing[custody_id] != custody:
        raise SearchOSRuntimeError("READ custody identity collision")
    slot["posture"] = SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    slot["latest_reason"] = "read_custody_admitted_for_rejudgment"
    slot["action_history"].append(
        {
            "event": "read_custody_admitted",
            "read_custody_ref": _compact_ref(custody),
            "same_normalized_url_reused": bool(
                custody.get("same_normalized_url_reused")
            ),
            "support_admitted": False,
        }
    )
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    return _refresh_state(candidate)


def record_searchos_readiness_projection(
    state: Mapping[str, Any], *, readiness: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = _mapping(readiness)
    _require_schema(
        safe, SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION, "Slice A readiness"
    )
    if safe.get("run_id") != candidate.get("run_id") or safe.get(
        "request_id"
    ) != candidate.get("request_id"):
        raise SearchOSRuntimeError("Slice A readiness scope mismatch")
    claimed = _digest_token(
        safe.get("readiness_projection_digest"), "readiness_projection_digest"
    )
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
    candidate["readiness_projection_ref"] = {
        "readiness_projection_id": safe["readiness_projection_id"],
        "readiness_projection_digest": claimed,
    }
    return _refresh_state(candidate)


def record_searchos_required_needs_block(
    state: Mapping[str, Any], *, block: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = _mapping(block)
    if safe.get("schema_version") != "searchos_slice_a_required_needs_block_v1":
        raise SearchOSRuntimeError("required-needs block schema mismatch")
    if safe.get("block_type") != SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED:
        raise SearchOSRuntimeError("required-needs block type mismatch")
    readiness_ref = _required_ref(
        safe.get("readiness_projection_ref"), "readiness_projection_ref"
    )
    if readiness_ref != _mapping(candidate.get("readiness_projection_ref")):
        raise SearchOSRuntimeError("required-needs block readiness ref is stale")
    claimed = _digest_token(safe.get("block_digest"), "block_digest")
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key not in {"block_id", "block_digest", "replay_identity"}
    }
    if _digest(core) != claimed:
        raise SearchOSRuntimeError("required-needs block digest mismatch")
    if any(
        safe.get(field) is not False
        for field in (
            "query_authorized",
            "read_authorized",
            "retry_authorized",
            "recovery_authorized",
            "successful_sufficiency_allowed",
            "final_answer_packet_allowed",
            "author_execution_allowed",
        )
    ):
        raise SearchOSRuntimeError("required-needs block broadens closed authority")
    candidate["required_needs_block_ref"] = {
        "block_id": safe["block_id"],
        "block_digest": claimed,
        "block_type": safe["block_type"],
    }
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
        _required_ref(item, "provider_result_occurrence_ref")
        for item in ordered_provider_result_occurrence_refs
    ]
    if bool(zero_useful_result) == bool(selected):
        raise SearchOSRuntimeError(
            "iteration candidate set zero-useful-result posture is contradictory"
        )
    core = {
        "schema_version": SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": _token(run_id, "run_id"),
        "request_id": _token(request_id, "request_id"),
        "iteration": int(iteration),
        "parent_candidate_state_ref": _required_ref(
            parent_candidate_state_ref, "parent_candidate_state_ref"
        ),
        "active_slot_ref": _required_ref(slot_ref, "slot_ref"),
        "query_plan_item_ref": _required_ref(
            query_plan_item_ref, "query_plan_item_ref"
        ),
        "provider_plan_ref": _required_ref(provider_plan_ref, "provider_plan_ref"),
        "route_refs": [_required_ref(item, "route_ref") for item in route_refs],
        "retrieval_action_refs": [
            _required_ref(item, "retrieval_action_ref")
            for item in retrieval_action_refs
        ],
        "ordered_provider_result_occurrence_refs": occurrences,
        "identity_set_delta_ref": _required_ref(
            identity_set_delta_ref, "identity_set_delta_ref"
        ),
        "selected_candidate_refs": selected,
        "bounded_candidate_material_refs": [
            _required_ref(item, "candidate_material_ref")
            for item in bounded_candidate_material_refs
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


def searchos_iteration_candidate_set_ref(
    candidate_set: Mapping[str, Any]
) -> dict[str, Any]:
    safe = validate_searchos_iteration_candidate_set(candidate_set)
    return {
        "iteration_candidate_set_id": safe["iteration_candidate_set_id"],
        "iteration_candidate_set_digest": safe["iteration_candidate_set_digest"],
        "iteration": safe["iteration"],
        "parent_candidate_state_ref": deepcopy(safe["parent_candidate_state_ref"]),
        "schema_version": SEARCHOS_ITERATION_CANDIDATE_SET_SCHEMA_VERSION,
    }


def validate_searchos_iteration_candidate_set(
    candidate_set: Mapping[str, Any]
) -> dict[str, Any]:
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
    initial_plan_ref = _required_ref(
        revision.get("initial_query_plan_ref"), "revision_1.initial_query_plan_ref"
    )
    initial_identity_ref = _required_ref(
        revision.get("initial_identity_set_ref")
        or revision.get("source_result_identity_set_ref"),
        "revision_1.initial_identity_set_ref",
    )
    initial_plan = [deepcopy(_mapping(item)) for item in initial_query_plan_items]
    current_plan = [deepcopy(_mapping(item)) for item in current_query_plan_items]
    if current_plan[: len(initial_plan)] != initial_plan:
        raise SearchOSRuntimeError(
            "initial QueryPlan snapshot is not an exact current-plan prefix"
        )
    if revision.get("initial_query_plan_items_digest") and revision.get(
        "initial_query_plan_items_digest"
    ) != _digest(initial_plan):
        raise SearchOSRuntimeError("revision 1 initial QueryPlan snapshot became stale")
    initial_identities = [
        deepcopy(_mapping(item)) for item in initial_identity_refs
    ]
    if revision.get("initial_identity_refs_digest") and revision.get(
        "initial_identity_refs_digest"
    ) != _digest(initial_identities):
        raise SearchOSRuntimeError("revision 1 initial identity snapshot became stale")

    expected_parent = _required_ref(
        revision.get("candidate_state_ref")
        or revision.get("packet_ref")
        or revision,
        "revision_1 candidate state ref",
    )
    ordered_sets: list[dict[str, Any]] = []
    reconstructed = list(initial_identities)
    seen_identity_keys = {_ref_key(item) for item in reconstructed}
    previous_iteration = 1
    for raw_set in iteration_candidate_sets:
        item = validate_searchos_iteration_candidate_set(raw_set)
        if int(item["iteration"]) != previous_iteration + 1:
            raise SearchOSRuntimeError("iteration candidate set order is non-contiguous")
        if _mapping(item["parent_candidate_state_ref"]) != expected_parent:
            raise SearchOSRuntimeError("iteration candidate parent ref is stale")
        delta_ref = _mapping(item["identity_set_delta_ref"])
        delta_digest = _first_digest(delta_ref)
        delta = identity_deltas_by_digest.get(delta_digest)
        if delta is None:
            raise SearchOSRuntimeError("iteration identity delta is omitted")
        normalized_delta = [deepcopy(_mapping(value)) for value in delta]
        if delta_ref.get("identity_count") is not None and int(
            delta_ref["identity_count"]
        ) != len(normalized_delta):
            raise SearchOSRuntimeError("iteration identity delta count mismatch")
        if delta_ref.get("identity_refs_digest") and delta_ref.get(
            "identity_refs_digest"
        ) != _digest(normalized_delta):
            raise SearchOSRuntimeError("iteration identity delta digest mismatch")
        for identity in normalized_delta:
            key = _ref_key(identity)
            if key in seen_identity_keys:
                raise SearchOSRuntimeError("iteration identity delta is not additive")
            seen_identity_keys.add(key)
            reconstructed.append(identity)
        expected_parent = searchos_iteration_candidate_set_ref(item)
        ordered_sets.append(item)
        previous_iteration = int(item["iteration"])
    current_identities = [
        deepcopy(_mapping(item)) for item in current_identity_refs
    ]
    if reconstructed != current_identities:
        raise SearchOSRuntimeError(
            "initial identities plus ordered deltas do not equal current candidate state"
        )
    proof_core = {
        "schema_version": "searchos_append_only_lineage_proof_v1",
        "initial_query_plan_ref": initial_plan_ref,
        "initial_identity_set_ref": initial_identity_ref,
        "current_query_plan_items_digest": _digest(current_plan),
        "current_identity_refs_digest": _digest(current_identities),
        "iteration_candidate_set_refs": [
            searchos_iteration_candidate_set_ref(item) for item in ordered_sets
        ],
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
        normalized_url = normalize_discovery_result_url(
            candidate.get("normalized_url") or candidate.get("url")
        )
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
                "title": _bounded_optional(candidate.get("title"), 240),
                "snippet": _bounded_optional(candidate.get("snippet"), 600),
                "candidate_state_ref": _required_ref(
                    candidate.get("candidate_state_ref"), "candidate_state_ref"
                ),
            }
            order.append(key)
        group = grouped[key]
        if _mapping(candidate.get("candidate_state_ref")) != group[
            "candidate_state_ref"
        ]:
            raise SearchOSRuntimeError(
                "candidate-use contributors disagree on admitted candidate state"
            )
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
            raise SearchOSRuntimeError(
                "candidate-use option lacks admitted candidate/occurrence lineage"
            )
        core = {
            "schema_version": SEARCHOS_CANDIDATE_USE_OPTION_SCHEMA_VERSION,
            "owner": SEARCHOS_OWNER,
            "slot_ref": group["slot_ref"],
            "normalized_url": group["normalized_url"],
            "option_ordinal": ordinal,
            "candidate_state_ref": group["candidate_state_ref"],
            "candidate_refs": group["candidate_refs"],
            "query_plan_item_refs": group["query_plan_item_refs"],
            "iteration_set_refs": group["iteration_set_refs"],
            "provider_result_occurrence_refs": group[
                "provider_result_occurrence_refs"
            ],
            "source_material_refs": group["source_material_refs"],
            "title": group["title"],
            "snippet": group["snippet"],
            "material_authority": (
                SearchOSMaterialAuthority.DIRECTIONAL_CANDIDATE_CONTEXT.value
            ),
            "read_eligible": True,
            "support_proposal_eligible": False,
            "read_custody_created": False,
            "same_url_transport_count": 0,
        }
        digest = _digest(core)
        options.append(
            {
                **core,
                "candidate_use_option_id": f"searchos-option:{digest[:24]}",
                "candidate_use_option_digest": digest,
                "replay_identity": f"searchos-option:{digest}",
            }
        )
    return options


def build_candidate_use_window_v1(
    *,
    slot_ref: Mapping[str, Any],
    ordered_options: Sequence[Mapping[str, Any]],
    window_ordinal: int,
    policy_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    slot = _required_ref(slot_ref, "slot_ref")
    slot_id = _token(slot.get("slot_id"), "slot_id")
    options = [deepcopy(_mapping(item)) for item in ordered_options]
    if any(
        _mapping(item.get("slot_ref")).get("slot_id") != slot_id
        for item in options
    ):
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
    remaining_count = max(0, len(options) - start - len(retained))
    core = {
        "schema_version": SEARCHOS_CANDIDATE_USE_WINDOW_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "slot_ref": slot,
        "window_ordinal": ordinal,
        "ordered_candidate_use_option_refs": [
            candidate_use_option_ref(item) for item in retained
        ],
        "retained_option_count": len(retained),
        "remaining_option_count": remaining_count,
        "full_eligible_option_digest": _digest(
            [candidate_use_option_ref(item) for item in options]
        ),
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


def candidate_use_option_ref(option: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(option)
    _require_schema(
        safe, SEARCHOS_CANDIDATE_USE_OPTION_SCHEMA_VERSION, "candidate-use option"
    )
    return {
        "candidate_use_option_id": _token(
            safe.get("candidate_use_option_id"), "candidate_use_option_id"
        ),
        "candidate_use_option_digest": _digest_token(
            safe.get("candidate_use_option_digest"),
            "candidate_use_option_digest",
        ),
        "normalized_url": normalize_discovery_result_url(
            safe.get("normalized_url")
        ),
        "slot_id": _token(
            _mapping(safe.get("slot_ref")).get("slot_id"), "slot_id"
        ),
    }


def candidate_use_window_ref(window: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(window)
    _require_schema(
        safe, SEARCHOS_CANDIDATE_USE_WINDOW_SCHEMA_VERSION, "candidate-use window"
    )
    return {
        "candidate_use_window_id": _token(
            safe.get("candidate_use_window_id"), "candidate_use_window_id"
        ),
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
    charge = _required_ref(charge_ref, "charge_ref")
    if charge.get("slot_id") != token:
        raise SearchOSRuntimeError("judgment charge does not bind current slot")
    request_core = {
        "schema_version": SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": canonical["answer_contract_ref"],
        "policy_snapshot_ref": canonical["policy_snapshot_ref"],
        "slot_ref": slot["slot_ref"],
        "slot_posture": slot["posture"],
        "candidate_state_ref": canonical["current_candidate_state_ref"],
        "candidate_window_ref": window_ref,
        "candidate_use_options": [
            {
                **_mapping(item),
                "material_authority": (
                    SearchOSMaterialAuthority.DIRECTIONAL_CANDIDATE_CONTEXT.value
                ),
                "support_proposal_eligible": False,
            }
            for item in candidate_window.get("ordered_candidate_use_option_refs")
            or ()
        ],
        "read_custody_refs": [
            _required_ref(item, "read_custody_ref") for item in read_custody_refs
        ],
        "charge_ref": charge,
        "legal_actions": [item.value for item in SearchOSJudgmentAction],
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


def validate_searchos_judgment_model_output(
    *, request: Mapping[str, Any], model_output: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate one neutral model-authored action; never synthesize a fallback."""

    request_safe = _mapping(request)
    _require_schema(
        request_safe, SEARCHOS_JUDGMENT_REQUEST_SCHEMA_VERSION, "judgment request"
    )
    output = _mapping(model_output)
    allowed_keys = {
        "schema_version",
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
        "action",
        "candidate_use_option_ref",
        "read_custody_refs",
        "followup_query",
        "reason",
    }
    if set(output) - allowed_keys:
        raise SearchOSRuntimeError("judgment output contains unsupported fields")
    if output.get("schema_version") != SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION:
        raise SearchOSRuntimeError("judgment output schema version mismatch")
    if output.get("judgment_request_id") != request_safe.get(
        "judgment_request_id"
    ) or output.get("judgment_request_digest") != request_safe.get(
        "judgment_request_digest"
    ):
        raise SearchOSRuntimeError("judgment nomination is stale")
    slot_id = _token(output.get("slot_id"), "slot_id")
    if slot_id != _mapping(request_safe.get("slot_ref")).get("slot_id"):
        raise SearchOSRuntimeError("judgment nomination slot is stale")
    try:
        action = SearchOSJudgmentAction(str(output.get("action") or ""))
    except ValueError as exc:
        raise SearchOSRuntimeError("judgment action is not in the neutral vocabulary") from exc
    option_ref = _optional_ref(output.get("candidate_use_option_ref"))
    custody_refs = [
        _required_ref(item, "read_custody_ref")
        for item in output.get("read_custody_refs") or ()
    ]
    followup_query = _bounded_optional(
        output.get("followup_query"), MAX_FOLLOWUP_QUERY_CHARS
    )
    reason = _bounded_reason(output.get("reason"))
    visible_options = {
        item.get("candidate_use_option_id"): item
        for item in request_safe.get("candidate_use_options") or ()
    }
    current_custody = {
        _first_ref_id(item): item for item in request_safe.get("read_custody_refs") or ()
    }
    if action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
        option_id = _first_ref_id(option_ref)
        if not option_ref or option_id not in visible_options:
            raise SearchOSRuntimeError("READ nomination is outside current candidate window")
        if custody_refs or followup_query:
            raise SearchOSRuntimeError("READ nomination contains incompatible payload")
    elif action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
        if not followup_query or option_ref or custody_refs:
            raise SearchOSRuntimeError("follow-up nomination payload is invalid")
    elif action is (
        SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
    ):
        if not custody_refs or option_ref or followup_query:
            raise SearchOSRuntimeError("semantic handoff requires exact READ custody refs")
        if any(_first_ref_id(item) not in current_custody for item in custody_refs):
            raise SearchOSRuntimeError("semantic handoff nominated stale READ custody")
    else:
        if option_ref or custody_refs or followup_query or not reason:
            raise SearchOSRuntimeError("unresolved handoff payload is invalid")
    core = {
        "schema_version": SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION,
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
        "read_custody_refs": custody_refs,
        "followup_query": followup_query,
        "reason": reason,
        "deterministic_fallback_used": False,
    }
    digest = _digest(core)
    return {
        **core,
        "judgment_decision_id": f"searchos-decision:{digest[:24]}",
        "judgment_decision_digest": digest,
        "replay_identity": f"searchos-decision:{digest}",
    }


def reduce_searchos_judgment_decision(
    state: Mapping[str, Any], *, decision: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    reduced = _mapping(decision)
    _require_schema(
        reduced, SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION, "judgment decision"
    )
    slot_id = _token(_mapping(reduced.get("slot_ref")).get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    if slot_id not in slots:
        raise SearchOSRuntimeError("judgment decision references inactive slot")
    if _mapping(reduced.get("candidate_state_ref")) != _mapping(
        candidate.get("current_candidate_state_ref")
    ):
        raise SearchOSRuntimeError("judgment decision candidate state is stale")
    slot = deepcopy(slots[slot_id])
    if slot["posture"] in {
        SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value,
        SearchOSSlotPosture.UNRESOLVED_HANDOFF.value,
        SearchOSSlotPosture.JUDGMENT_FAILED.value,
        SearchOSSlotPosture.BUDGET_EXHAUSTED.value,
        SearchOSSlotPosture.STALE_OR_INVALID.value,
    }:
        raise SearchOSRuntimeError("judgment decision follows a terminal slot posture")
    action = SearchOSJudgmentAction(reduced["action"])
    policy = _mapping(candidate["policy_snapshot"])
    if action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
        if int(slot["read_nomination_count"]) >= int(
            policy["read_nominations_per_slot"]
        ):
            return mark_searchos_slot_budget_exhausted(
                candidate,
                slot_id=slot_id,
                reason="read_nomination_budget_exhausted",
            )
        slot["posture"] = SearchOSSlotPosture.AWAITING_READ.value
        slot["read_nomination_count"] = int(slot["read_nomination_count"]) + 1
        slot["latest_reason"] = "authorized_candidate_read_requested"
    elif action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
        if int(slot["followup_query_nomination_count"]) >= int(
            policy["followup_query_nominations_per_slot"]
        ):
            return mark_searchos_slot_budget_exhausted(
                candidate,
                slot_id=slot_id,
                reason="followup_query_nomination_budget_exhausted",
            )
        slot["posture"] = SearchOSSlotPosture.AWAITING_FOLLOWUP_DISCOVER.value
        slot["followup_query_nomination_count"] = int(
            slot["followup_query_nomination_count"]
        ) + 1
        slot["latest_reason"] = "exact_followup_query_proposed"
    elif action is (
        SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
    ):
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


def build_searchos_semantic_evaluation_handoff_v1(
    *,
    state: Mapping[str, Any],
    slot_id: str,
    judgment_decision_ref: Mapping[str, Any],
    read_custody_material_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    canonical = _validated_state_copy(state)
    token = _token(slot_id, "slot_id")
    slot = deepcopy(_mapping(canonical["slots_by_id"])[token])
    if slot["posture"] != SearchOSSlotPosture.READY_FOR_SEMANTIC_EVALUATION.value:
        raise SearchOSRuntimeError("semantic handoff requires a ready slot")
    custody = [
        _required_ref(item, "read_custody_material_ref")
        for item in read_custody_material_refs
    ]
    if not custody:
        raise SearchOSRuntimeError("semantic handoff requires READ custody material")
    for ref in custody:
        if ref.get("material_authority") != (
            SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value
        ):
            raise SearchOSRuntimeError(
                "directional candidate context cannot enter support-bearing analysis"
            )
        if ref.get("readable") is not True or ref.get("stale") is True:
            raise SearchOSRuntimeError("semantic handoff READ custody is unreadable or stale")
        if _mapping(ref.get("slot_ref")) != _mapping(slot["slot_ref"]):
            raise SearchOSRuntimeError("semantic handoff custody slot lineage mismatch")
    core = {
        "schema_version": SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "run_id": canonical["run_id"],
        "request_id": canonical["request_id"],
        "answer_contract_ref": canonical["answer_contract_ref"],
        "policy_snapshot_ref": canonical["policy_snapshot_ref"],
        "slot_ref": deepcopy(slot["slot_ref"]),
        "candidate_state_ref": canonical["current_candidate_state_ref"],
        "judgment_decision_ref": _required_ref(
            judgment_decision_ref, "judgment_decision_ref"
        ),
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


def record_searchos_semantic_handoff(
    state: Mapping[str, Any], *, handoff: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = _validated_state_copy(state)
    safe = _mapping(handoff)
    _require_schema(
        safe, SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION, "semantic handoff"
    )
    slot_id = _token(_mapping(safe.get("slot_ref")).get("slot_id"), "slot_id")
    slots = _mutable_mapping(candidate["slots_by_id"])
    slot = deepcopy(slots[slot_id])
    if slot["posture"] != SearchOSSlotPosture.READY_FOR_SEMANTIC_EVALUATION.value:
        raise SearchOSRuntimeError("semantic handoff follows stale slot state")
    ref = searchos_semantic_handoff_ref(safe)
    slot["posture"] = SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
    slot["semantic_handoff_refs"].append(ref)
    slot["latest_reason"] = "governed_component_analysis_pending"
    slots[slot_id] = _refresh_slot(slot)
    candidate["slots_by_id"] = slots
    candidate["semantic_handoff_refs"].append(ref)
    return _refresh_state(candidate)


def searchos_semantic_handoff_ref(handoff: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(handoff)
    return {
        "semantic_handoff_id": _token(
            safe.get("semantic_handoff_id"), "semantic_handoff_id"
        ),
        "semantic_handoff_digest": _digest_token(
            safe.get("semantic_handoff_digest"), "semantic_handoff_digest"
        ),
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
            and outcome.get("material_authority")
            == SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value
        )
        reason = None if ready else _readiness_failure_reason(slot, outcome)
        record = {
            "slot_ref": deepcopy(slot["slot_ref"]),
            "requirement_posture": slot["requirement_posture"],
            "latest_judgment_posture": slot["posture"],
            "latest_judgment_reason": slot["latest_reason"],
            "action_history": deepcopy(slot["action_history"]),
            "candidate_state_ref": deepcopy(slot["current_candidate_state_ref"]),
            "custody_refs": deepcopy(slot["custody_refs"]),
            "semantic_handoff_ref": _optional_ref(
                outcome.get("semantic_handoff_ref")
            ),
            "component_analyst_proposal_ref": _optional_ref(
                outcome.get("component_analyst_proposal_ref")
            ),
            "component_dprime_validation_ref": _optional_ref(
                outcome.get("component_dprime_validation_ref")
            ),
            "semantic_admission_outcome_ref": _optional_ref(
                outcome.get("semantic_admission_outcome_ref")
            ),
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
        "required_ready_count": len(canonical["required_slot_ids"])
        - len(unresolved),
        "unresolved_required_slots": unresolved,
        "all_required_slots_slice_a_ready": not unresolved,
        "successful_sufficiency_allowed": not unresolved,
        "final_answer_packet_allowed": not unresolved,
        "author_execution_allowed": not unresolved,
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
) -> dict[str, Any]:
    safe = _mapping(readiness)
    _require_schema(
        safe, SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION, "Slice A readiness"
    )
    unresolved = [
        deepcopy(_mapping(item))
        for item in safe.get("unresolved_required_slots") or ()
    ]
    if not unresolved or safe.get("all_required_slots_slice_a_ready") is not False:
        raise SearchOSRuntimeError("required-needs block requires unresolved slots")
    core = {
        "schema_version": "searchos_slice_a_required_needs_block_v1",
        "owner": SEARCHOS_OWNER,
        "block_type": SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED,
        "run_id": safe.get("run_id"),
        "request_id": safe.get("request_id"),
        "readiness_projection_ref": {
            "readiness_projection_id": safe.get("readiness_projection_id"),
            "readiness_projection_digest": safe.get("readiness_projection_digest"),
        },
        "unresolved_required_slots": unresolved,
        "query_authorized": False,
        "read_authorized": False,
        "retry_authorized": False,
        "recovery_authorized": False,
        "deterministic_semantic_fallback_invoked": False,
        "successful_sufficiency_allowed": False,
        "final_answer_packet_allowed": False,
        "author_execution_allowed": False,
        "satisfaction_or_coverage_upgrade_created": False,
        "stop_insufficient_emitted": False,
        "final_whole_run_stopping_decided": False,
        "safe_blocked_non_author_terminal_required": True,
        "canonical_state": True,
    }
    digest = _digest(core)
    return {
        **core,
        "block_id": f"searchos-required-needs-block:{digest[:24]}",
        "block_digest": digest,
        "replay_identity": f"searchos-required-needs-block:{digest}",
    }


def _readiness_failure_reason(
    slot: Mapping[str, Any], outcome: Mapping[str, Any]
) -> str:
    posture = str(slot.get("posture") or "")
    if posture in {
        SearchOSSlotPosture.UNRESOLVED_HANDOFF.value,
        SearchOSSlotPosture.JUDGMENT_FAILED.value,
        SearchOSSlotPosture.BUDGET_EXHAUSTED.value,
        SearchOSSlotPosture.STALE_OR_INVALID.value,
    }:
        return posture
    if outcome.get("material_authority") != (
        SearchOSMaterialAuthority.READ_CUSTODY_MATERIAL.value
    ):
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
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
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
    "build_searchos_iteration_candidate_set_v1",
    "build_searchos_judgment_request_v1",
    "build_searchos_policy_snapshot",
    "build_searchos_required_needs_block",
    "build_searchos_semantic_evaluation_handoff_v1",
    "build_searchos_slice_a_readiness_v1",
    "candidate_use_option_ref",
    "candidate_use_window_ref",
    "charge_searchos_judgment_call",
    "mark_searchos_slot_budget_exhausted",
    "record_searchos_judgment_failure",
    "record_searchos_iteration_candidate_set",
    "record_searchos_read_custody_material",
    "record_searchos_readiness_projection",
    "record_searchos_required_needs_block",
    "record_searchos_semantic_handoff",
    "reduce_searchos_judgment_decision",
    "searchos_iteration_candidate_set_ref",
    "searchos_policy_profile",
    "searchos_policy_snapshot_ref",
    "searchos_semantic_handoff_ref",
    "validate_searchos_append_only_lineage",
    "validate_searchos_iteration_candidate_set",
    "validate_searchos_judgment_model_output",
    "validate_searchos_state",
]
