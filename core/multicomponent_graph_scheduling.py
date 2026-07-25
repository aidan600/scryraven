"""RunKernel-owned serial scheduler and semantic-call lease authority.

The scheduler is an execution overlay over the installed AnswerContract,
ComponentWorkGraph V1, component-admission, recovery, and selective-closure
authorities.  It derives only work whose exact input packet can be constructed
from current canonical state.  It does not plan semantics, admit artifacts, or
execute transport.
"""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    SELECTIVE_CROSS_COMPONENT_SCHEMA,
    SUPPORTED_QUERY_CLASS,
    safe_packet_digest,
    validate_multicomponent_role_artifact,
)

MULTICOMPONENT_SCHEDULER_STAGE = "multicomponent_graph_scheduler"
MULTICOMPONENT_SCHEDULER_OWNER = "RunKernel.MulticomponentGraphScheduler"
MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION = "multicomponent_graph_scheduler_v1"
MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION = "multicomponent_graph_scheduler_v2"
MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION = "multicomponent_graph_scheduler_v3"
MULTICOMPONENT_LEASE_SCHEMA_VERSION = "multicomponent_semantic_work_lease_v1"
MULTICOMPONENT_LEASE_V2_SCHEMA_VERSION = "multicomponent_semantic_work_lease_v2"
MULTICOMPONENT_WORK_SCHEMA_VERSION = "multicomponent_semantic_work_v1"
MULTICOMPONENT_BATCH_SCHEMA_VERSION = "multicomponent_semantic_work_batch_v1"
MULTICOMPONENT_BATCH_LEASE_GROUP_SCHEMA_VERSION = (
    "multicomponent_semantic_batch_lease_group_v1"
)
MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION = (
    "multicomponent_private_child_action_descriptor_v1"
)
MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION = (
    "multicomponent_private_child_action_descriptor_set_v1"
)
MULTICOMPONENT_PREPARED_TRANSPORT_CALL_SCHEMA_VERSION = (
    "multicomponent_prepared_transport_call_v1"
)
MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION = (
    "multicomponent_safe_worker_result_v1"
)
MULTICOMPONENT_BATCH_ACCOUNTING_SUMMARY_SCHEMA_VERSION = (
    "multicomponent_batch_accounting_summary_v1"
)

BACKEND_HOSTED_API = "hosted_api"
BACKEND_LOCAL_OPENAI_COMPATIBLE = "local_openai_compatible"
BACKEND_CONSERVATIVE_UNKNOWN = "conservative_unknown"

PARALLEL_INITIAL_COMPONENT_ANALYST = "parallel_initial_component_analyst"
PARALLEL_INITIAL_COMPONENT_DPRIME = "parallel_initial_component_dprime"
PARALLEL_SERIAL_ONLY = "serial_only"

WORK_KIND_SEMANTIC_ROLE = "semantic_role"
WORK_KIND_SPECIALIST_CAPABILITY = "specialist_capability"
RESOURCE_HOSTED_MODEL_TRANSPORT = "hosted_model_transport"
RESOURCE_LOCAL_MODEL_TRANSPORT = "local_model_transport"
RESOURCE_DETERMINISTIC_SPECIALIST = "deterministic_specialist"
EXECUTOR_STRICT_ONE_SHOT_MODEL = "strict_one_shot_model_transport"
EXECUTOR_REGISTERED_DETERMINISTIC = "registered_deterministic_capability"

# This is the one authoritative compatibility mapping.  The existing role-call
# authorization and the Phase 4 scheduler both consume it.
MULTICOMPONENT_ROLE_CALL_LIMITS: Mapping[str, int] = {
    ROLE_COMPONENT_ANALYST: 5,
    ROLE_COMPONENT_DPRIME: 5,
    ROLE_CROSS_COMPONENT_ANALYST: 2,
    ROLE_SYNTHESIS_DPRIME: 8,
    ROLE_SCRUTINEER: 2,
}

LEASE_GRANTED = "granted_reserved"
LEASE_EXECUTION_STARTED = "execution_started_spent"
LEASE_COMPLETED = "completed"
LEASE_DENIED_EXHAUSTED = "denied_exhausted"
LEASE_CANCELLED = "cancelled_predispatch_returned"
LEASE_FAILED = "failed_spent"
LEASE_STALE = "stale_rejected_spent"
LEASE_BLOCKED = "blocked_spent"
LEASE_CONTESTED = "contested_spent"

_RESERVED_STATUSES = frozenset({LEASE_GRANTED})
_SPENT_STATUSES = frozenset(
    {
        LEASE_EXECUTION_STARTED,
        LEASE_COMPLETED,
        LEASE_FAILED,
        LEASE_STALE,
        LEASE_BLOCKED,
        LEASE_CONTESTED,
    }
)
_ACTIVE_STATUSES = frozenset({LEASE_GRANTED, LEASE_EXECUTION_STARTED})
_TERMINAL_STATUSES = frozenset(
    {
        LEASE_COMPLETED,
        LEASE_DENIED_EXHAUSTED,
        LEASE_CANCELLED,
        LEASE_FAILED,
        LEASE_STALE,
        LEASE_BLOCKED,
        LEASE_CONTESTED,
    }
)

_BATCH_SCHEDULER_VERSIONS = frozenset(
    {MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION, MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION}
)


class MulticomponentGraphSchedulingError(ValueError):
    """Raised when scheduler identity, authority, or arithmetic is invalid."""


def derive_multicomponent_compatibility_envelope() -> int:
    """Return the internal compatibility envelope derived from shared caps."""

    return sum(MULTICOMPONENT_ROLE_CALL_LIMITS.values())


def derive_multicomponent_transport_profile(configured_provider: Any) -> dict[str, Any]:
    """Derive the RunKernel-owned safe execution profile from product config."""

    from core.strict_accounted_model_route import (
        PROVIDER_LOCAL,
        PROVIDER_OPENAI,
        PROVIDER_OPENROUTER,
        normalize_fast_model_provider,
    )

    provider = normalize_fast_model_provider(configured_provider)
    if provider in {PROVIDER_OPENAI, PROVIDER_OPENROUTER}:
        backend_class = BACKEND_HOSTED_API
        effective_width = 2
    elif provider == PROVIDER_LOCAL:
        backend_class = BACKEND_LOCAL_OPENAI_COMPATIBLE
        effective_width = 1
    else:
        backend_class = BACKEND_CONSERVATIVE_UNKNOWN
        effective_width = 1
    return {
        "configured_provider_class": provider,
        "backend_class": backend_class,
        "effective_width": effective_width,
        "hard_cap": effective_width,
        "runtime_parallelism": effective_width == 2,
        "serial_scheduling": effective_width == 1,
        "maximum_active_physical_leases": effective_width,
    }


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 12:
        return None
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe(item, depth=depth + 1) for item in value]
    return str(value)


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _contract_ref(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner": contract.get("owner"),
        "canonical_state": contract.get("canonical_state") is True,
        "run_id": contract.get("run_id"),
        "request_id": contract.get("request_id"),
        "accepted_contract_version": contract.get("accepted_contract_version"),
        "accepted_contract_digest": contract.get("accepted_contract_digest"),
        "parent_question_meaning_record_id": contract.get(
            "parent_question_meaning_record_id"
        ),
        "parent_question_meaning_record_digest": contract.get(
            "parent_question_meaning_record_digest"
        ),
        "accepted_answer_component_count": contract.get(
            "accepted_answer_component_count"
        ),
    }


def _graph_ref(graph: Mapping[str, Any]) -> dict[str, Any]:
    if not graph:
        return {}
    return {
        "graph_id": graph.get("graph_id"),
        "graph_revision": graph.get("graph_revision"),
        "graph_digest": graph.get("graph_digest"),
    }


def _node_ref(node: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "node_id": node.get("node_id"),
        "node_revision": node.get("node_revision"),
        "node_digest": node.get("node_digest"),
    }


def _component_admission_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "component_id": value.get("component_id"),
        "action_id": value.get("action_id"),
        "admission_status": value.get("admission_status"),
        "accepted_contract_version": value.get("accepted_contract_version"),
        "accepted_contract_digest": value.get("accepted_contract_digest"),
        "analyst_artifact_digest": _mapping(
            value.get("analyst_finding_ref")
        ).get("artifact_digest"),
        "dprime_artifact_digest": _mapping(
            value.get("dprime_validation_ref")
        ).get("artifact_digest"),
    }


def _scheduler_without_digest(state: Mapping[str, Any]) -> dict[str, Any]:
    payload = deepcopy(dict(state))
    payload.pop("scheduler_digest", None)
    return payload


def _refresh_scheduler(state: Mapping[str, Any]) -> dict[str, Any]:
    current = deepcopy(dict(state))
    leases = [_mapping(item) for item in current.get("lease_history") or ()]
    semantic_leases = [
        lease
        for lease in leases
        if _mapping(lease.get("work")).get("work_kind")
        != WORK_KIND_SPECIALIST_CAPABILITY
    ]
    specialist_leases = [
        lease
        for lease in leases
        if _mapping(lease.get("work")).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    ]
    reserved = sum(
        1 for lease in semantic_leases if lease.get("status") in _RESERVED_STATUSES
    )
    spent = sum(
        1 for lease in semantic_leases if lease.get("status") in _SPENT_STATUSES
    )
    active = [lease for lease in leases if lease.get("status") in _ACTIVE_STATUSES]
    envelope = _mapping(current.get("compatibility_envelope"))
    total = int(envelope.get("total_units") or 0)
    remaining = int(envelope.get("remaining_units") or 0)
    returned = int(envelope.get("returned_units") or 0)
    if (
        _mapping(envelope.get("role_limits"))
        != dict(MULTICOMPONENT_ROLE_CALL_LIMITS)
        or total != derive_multicomponent_compatibility_envelope()
    ):
        raise MulticomponentGraphSchedulingError(
            "scheduler envelope disagrees with the shared role-cap mapping"
        )
    if total != remaining + reserved + spent:
        raise MulticomponentGraphSchedulingError(
            "scheduler live allocation invariant is invalid"
        )
    maximum_active = int(current.get("maximum_active_physical_leases") or 0)
    if len(active) > maximum_active:
        raise MulticomponentGraphSchedulingError(
            "scheduler exceeds its maximum active physical leases"
        )
    role_reserved = {role: 0 for role in MULTICOMPONENT_ROLE_CALL_LIMITS}
    role_spent = {role: 0 for role in MULTICOMPONENT_ROLE_CALL_LIMITS}
    for lease in semantic_leases:
        role = str(_mapping(lease.get("work")).get("role") or "")
        if role not in MULTICOMPONENT_ROLE_CALL_LIMITS:
            raise MulticomponentGraphSchedulingError("lease role is unknown")
        if lease.get("status") in _RESERVED_STATUSES:
            role_reserved[role] += 1
        if lease.get("status") in _SPENT_STATUSES:
            role_spent[role] += 1
    for role, limit in MULTICOMPONENT_ROLE_CALL_LIMITS.items():
        if role_reserved[role] + role_spent[role] > limit:
            raise MulticomponentGraphSchedulingError(
                "scheduler role allocation exceeds the shared role cap"
            )
    if current.get("schema_version") in _BATCH_SCHEDULER_VERSIONS:
        counters = _mapping(current.get("accounting_counters"))
        names = (
            "dispatch_committed_unit_count",
            "transport_submission_count",
            "transport_started_count",
            "transport_completed_count",
            "provider_request_attempt_count",
            "successful_artifact_count",
            "failed_submission_count",
            "failed_transport_count",
            "stale_result_count",
            "maximum_observed_in_flight_transports",
        )
        values = {name: int(counters.get(name) or 0) for name in names}
        outcomes = sum(
            values[name]
            for name in (
                "successful_artifact_count",
                "failed_submission_count",
                "failed_transport_count",
                "stale_result_count",
            )
        )
        batch_leases = [lease for lease in semantic_leases if lease.get("batch_id")]
        active_batch_leases = [
            lease for lease in batch_leases if lease.get("status") in _ACTIVE_STATUSES
        ]
        if (
            any(value < 0 for value in values.values())
            or values["provider_request_attempt_count"]
            > values["transport_started_count"]
            or values["transport_started_count"]
            > values["transport_submission_count"]
            or values["transport_completed_count"] > values["transport_started_count"]
            or values["transport_submission_count"]
            > values["dispatch_committed_unit_count"]
            or outcomes > values["dispatch_committed_unit_count"]
            or values["maximum_observed_in_flight_transports"]
            > int(current.get("effective_width") or 0)
            or counters.get("physical_overlap_observed")
            is not (values["maximum_observed_in_flight_transports"] > 1)
            or (
                not active_batch_leases
                and outcomes != values["dispatch_committed_unit_count"]
            )
        ):
            raise MulticomponentGraphSchedulingError(
                "scheduler V2 transport accounting invariant is invalid"
            )
    if current.get("schema_version") == MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION:
        pool = _mapping(current.get("specialist_compatibility_pool"))
        limit = int(pool.get("specialist_work_item_limit") or 0)
        specialist_reserved = sum(
            1 for lease in specialist_leases if lease.get("status") in _RESERVED_STATUSES
        )
        specialist_spent = sum(
            1 for lease in specialist_leases if lease.get("status") in _SPENT_STATUSES
        )
        specialist_remaining = int(pool.get("specialist_remaining") or 0)
        if (
            limit not in {0, 1}
            or specialist_remaining < 0
            or limit
            != specialist_remaining + specialist_reserved + specialist_spent
            or sum(
                1
                for lease in specialist_leases
                if lease.get("status") in _ACTIVE_STATUSES
            )
            > 1
        ):
            raise MulticomponentGraphSchedulingError(
                "scheduler V3 Specialist allocation invariant is invalid"
            )
        pool.update(
            {
                "specialist_reserved": specialist_reserved,
                "specialist_spent": specialist_spent,
                "specialist_total": limit,
            }
        )
        current["specialist_compatibility_pool"] = pool
    envelope.update(
        {
            "reserved_units": reserved,
            "spent_units": spent,
            "returned_units": returned,
            "role_reserved_units": role_reserved,
            "role_spent_units": role_spent,
        }
    )
    current["compatibility_envelope"] = envelope
    current["active_physical_lease_count"] = len(active)
    current["scheduler_digest"] = _digest(_scheduler_without_digest(current))
    return current


def initialize_scheduler_state(*, run_id: str, request_id: str) -> dict[str, Any]:
    """Construct the retained historical Phase 4 scheduler V1 projection."""

    total = derive_multicomponent_compatibility_envelope()
    caps = dict(MULTICOMPONENT_ROLE_CALL_LIMITS)
    envelope_core = {
        "owner": MULTICOMPONENT_SCHEDULER_OWNER,
        "role_limits": caps,
        "total_units": total,
    }
    state = {
        "schema_version": MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION,
        "owner": MULTICOMPONENT_SCHEDULER_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "run_id": run_id,
        "request_id": request_id,
        "supported_query_class": SUPPORTED_QUERY_CLASS,
        "status": "active",
        "scheduler_revision": 1,
        "runtime_parallelism": False,
        "serial_scheduling": True,
        "maximum_active_physical_leases": 1,
        "active_physical_lease_count": 0,
        "compatibility_envelope": {
            **envelope_core,
            "envelope_id": f"multicomponent-envelope:{_digest(envelope_core)[:20]}",
            "envelope_digest": _digest(envelope_core),
            "remaining_units": total,
            "reserved_units": 0,
            "spent_units": 0,
            "returned_units": 0,
            "role_reserved_units": {role: 0 for role in caps},
            "role_spent_units": {role: 0 for role in caps},
        },
        "lease_history": [],
        "transition_history": [
            {
                "transition": "scheduler_initialized",
                "scheduler_revision": 1,
                "runtime_parallelism": False,
            }
        ],
        "last_ready_work": [],
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "private_log_retained": False,
        "full_trace_retained": False,
    }
    return _refresh_scheduler(state)


def initialize_scheduler_v2_state(
    *, run_id: str, request_id: str, configured_provider: Any
) -> dict[str, Any]:
    """Construct the ordinary Phase 5A scheduler from configured provider only."""

    total = derive_multicomponent_compatibility_envelope()
    caps = dict(MULTICOMPONENT_ROLE_CALL_LIMITS)
    profile = derive_multicomponent_transport_profile(configured_provider)
    envelope_core = {
        "owner": MULTICOMPONENT_SCHEDULER_OWNER,
        "role_limits": caps,
        "total_units": total,
    }
    accounting = {
        "schema_version": MULTICOMPONENT_BATCH_ACCOUNTING_SUMMARY_SCHEMA_VERSION,
        "dispatch_committed_unit_count": 0,
        "transport_submission_count": 0,
        "transport_started_count": 0,
        "transport_completed_count": 0,
        "provider_request_attempt_count": 0,
        "successful_artifact_count": 0,
        "failed_submission_count": 0,
        "failed_transport_count": 0,
        "stale_result_count": 0,
        "batch_count": 0,
        "parallel_batch_count": 0,
        "width_1_batch_count": 0,
        "maximum_observed_in_flight_transports": 0,
        "physical_overlap_observed": False,
    }
    state = {
        "schema_version": MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION,
        "owner": MULTICOMPONENT_SCHEDULER_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "run_id": run_id,
        "request_id": request_id,
        "supported_query_class": SUPPORTED_QUERY_CLASS,
        "status": "active",
        "terminal_posture": None,
        "scheduler_revision": 1,
        **profile,
        "active_physical_lease_count": 0,
        "compatibility_envelope": {
            **envelope_core,
            "envelope_id": f"multicomponent-envelope:{_digest(envelope_core)[:20]}",
            "envelope_digest": _digest(envelope_core),
            "remaining_units": total,
            "reserved_units": 0,
            "spent_units": 0,
            "returned_units": 0,
            "role_reserved_units": {role: 0 for role in caps},
            "role_spent_units": {role: 0 for role in caps},
        },
        "batch_history": [],
        "lease_history": [],
        "transition_history": [
            {
                "transition": "scheduler_initialized",
                "scheduler_revision": 1,
                "runtime_parallelism": profile["runtime_parallelism"],
                "effective_width": profile["effective_width"],
                "backend_class": profile["backend_class"],
            }
        ],
        "accounting_counters": accounting,
        "last_ready_work": [],
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "private_descriptor_retained": False,
        "prepared_transport_retained": False,
        "worker_result_retained": False,
        "private_log_retained": False,
        "full_trace_retained": False,
        "local_parallelism_enabled": False,
        "adaptive_rate_limit_enabled": False,
        "live_characterization_run": False,
    }
    return _refresh_scheduler(state)


def initialize_scheduler_v3_state(
    *,
    run_id: str,
    request_id: str,
    configured_provider: Any,
    specialist_work_item_limit: int,
    specialist_registry_digest: str,
    specialist_execution_policy_digest: str,
) -> dict[str, Any]:
    """Construct the versioned one-authority scheduler with Specialist work."""

    if specialist_work_item_limit not in {0, 1}:
        raise MulticomponentGraphSchedulingError(
            "scheduler V3 Specialist limit must be zero or one"
        )
    state = initialize_scheduler_v2_state(
        run_id=run_id,
        request_id=request_id,
        configured_provider=configured_provider,
    )
    state.pop("scheduler_digest", None)
    state["schema_version"] = MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION
    state["scheduler_revision"] = 1
    state["specialist_compatibility_pool"] = {
        "schema_version": "specialist_budget_state_v1",
        "specialist_work_item_limit": specialist_work_item_limit,
        "specialist_total": specialist_work_item_limit,
        "specialist_remaining": specialist_work_item_limit,
        "specialist_reserved": 0,
        "specialist_spent": 0,
        "specialist_returned": 0,
    }
    state["specialist_registry_digest"] = specialist_registry_digest
    state["specialist_execution_policy_digest"] = (
        specialist_execution_policy_digest
    )
    state["specialist_parallelism"] = False
    state["specialist_recursion"] = False
    state["specialist_maximum_in_flight"] = 1
    state["transition_history"] = [
        {
            **state["transition_history"][0],
            "transition": "scheduler_v3_initialized",
            "specialist_work_item_limit": specialist_work_item_limit,
        }
    ]
    return _refresh_scheduler(state)


def validate_scheduler_state(value: Mapping[str, Any]) -> dict[str, Any]:
    state = deepcopy(dict(value))
    schema_version = state.get("schema_version")
    common_invalid = (
        state.get("owner") != MULTICOMPONENT_SCHEDULER_OWNER
        or state.get("canonical_state") is not True
    )
    if schema_version == MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION:
        v2_only_fields = {
            "configured_provider_class",
            "backend_class",
            "effective_width",
            "hard_cap",
            "batch_history",
            "accounting_counters",
            "private_descriptor_retained",
            "prepared_transport_retained",
            "worker_result_retained",
        }
        invalid = (
            common_invalid
            or state.get("runtime_parallelism") is not False
            or state.get("serial_scheduling") is not True
            or state.get("maximum_active_physical_leases") != 1
            or any(field in state for field in v2_only_fields)
        )
    elif schema_version in _BATCH_SCHEDULER_VERSIONS:
        profile = derive_multicomponent_transport_profile(
            state.get("configured_provider_class")
        )
        invalid = common_invalid or any(
            state.get(field) != expected for field, expected in profile.items()
        )
        invalid = invalid or (
            state.get("hard_cap") not in {1, 2}
            or not isinstance(state.get("batch_history"), list)
            or not isinstance(state.get("accounting_counters"), Mapping)
            or any(
                state.get(flag) is not False
                for flag in (
                    "raw_prompt_retained",
                    "raw_model_response_retained",
                    "raw_provider_payload_retained",
                    "private_descriptor_retained",
                    "prepared_transport_retained",
                    "worker_result_retained",
                    "private_log_retained",
                    "full_trace_retained",
                    "local_parallelism_enabled",
                    "adaptive_rate_limit_enabled",
                    "live_characterization_run",
                )
            )
        )
        if schema_version == MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION:
            invalid = invalid or (
                not isinstance(state.get("specialist_compatibility_pool"), Mapping)
                or not state.get("specialist_registry_digest")
                or not state.get("specialist_execution_policy_digest")
                or state.get("specialist_parallelism") is not False
                or state.get("specialist_recursion") is not False
                or state.get("specialist_maximum_in_flight") != 1
            )
        else:
            invalid = invalid or any(
                field in state
                for field in (
                    "specialist_compatibility_pool",
                    "specialist_registry_digest",
                    "specialist_execution_policy_digest",
                )
            )
    else:
        invalid = True
    if invalid:
        raise MulticomponentGraphSchedulingError("scheduler schema or owner mismatch")
    declared = state.pop("scheduler_digest", None)
    refreshed = _refresh_scheduler(state)
    if declared != refreshed.get("scheduler_digest"):
        raise MulticomponentGraphSchedulingError("scheduler digest mismatch")
    if (
        refreshed.get("status")
        in {
            "completed",
            "blocked_exhausted",
            "blocked_required_work_failed",
            "blocked_required_specialist_proposal",
            "blocked_required_specialist_work",
        }
        and refreshed.get("active_physical_lease_count") != 0
    ):
        raise MulticomponentGraphSchedulingError(
            "terminal scheduler state cannot contain an active semantic lease"
        )
    return refreshed


def block_required_specialist_proposal(
    *, state: Any, proposal: Mapping[str, Any]
) -> dict[str, Any]:
    """Safely block V3 on a denied required or unclassified proposal."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    item = _mapping(proposal)
    posture = item.get("posture")
    rejection_id = item.get("rejection_id")
    rejection_digest = item.get("rejection_digest")
    proposal_id = item.get("proposal_id") or rejection_id
    proposal_digest = item.get("proposal_digest") or rejection_digest
    rejection_reason = item.get("rejection_reason") or item.get(
        "rejection_category"
    )
    if (
        scheduler.get("schema_version") != MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION
        or scheduler.get("status") != "active"
        or posture not in {"required", "unclassified_fail_closed"}
        or item.get("proposal_authority") == "accepted"
        or not proposal_id
        or not proposal_digest
        or any(
            _mapping(lease).get("status") in _ACTIVE_STATUSES
            for lease in scheduler.get("lease_history") or ()
        )
    ):
        raise MulticomponentGraphSchedulingError(
            "required Specialist proposal cannot block this scheduler state"
        )
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["status"] = "blocked_required_specialist_proposal"
    scheduler["terminal_posture"] = "blocked_required_specialist_proposal"
    scheduler["failed_required_work_ref"] = {
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "proposal_authority": item.get("proposal_authority"),
        "rejection_reason": rejection_reason,
    }
    scheduler["transition_history"].append(
        {
            "transition": "blocked_required_specialist_proposal",
            "scheduler_revision": scheduler["scheduler_revision"],
            "proposal_id": proposal_id,
            "rejection_reason": rejection_reason,
        }
    )
    return _refresh_scheduler(scheduler)


def block_required_specialist_reconstruction_failure(
    *,
    state: Any,
    proposal: Mapping[str, Any],
    work_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Block V3 after one required Specialist reservation was returned."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    item = _mapping(proposal)
    requested_work = _mapping(work_ref)
    cancelled = [
        _mapping(lease)
        for lease in scheduler.get("lease_history") or ()
        if _mapping(lease).get("status") == LEASE_CANCELLED
        and _mapping(lease).get("settlement_reason")
        == "exact_batch_packet_reconstruction_failed"
        and _mapping(_mapping(lease).get("work")).get("work_id")
        == requested_work.get("work_id")
        and _mapping(_mapping(lease).get("work")).get("work_digest")
        == requested_work.get("work_digest")
    ]
    work = _mapping(cancelled[0].get("work")) if len(cancelled) == 1 else {}
    proposal_ref = _mapping(work.get("specialist_proposal_ref"))
    if (
        scheduler.get("schema_version")
        != MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION
        or scheduler.get("status") != "active"
        or item.get("posture") != "required"
        or item.get("proposal_authority") != "accepted"
        or len(cancelled) != 1
        or proposal_ref.get("proposal_id") != item.get("proposal_id")
        or proposal_ref.get("proposal_digest") != item.get("proposal_digest")
        or any(
            _mapping(lease).get("status") in _ACTIVE_STATUSES
            for lease in scheduler.get("lease_history") or ()
        )
    ):
        raise MulticomponentGraphSchedulingError(
            "required Specialist reconstruction failure cannot block this scheduler"
        )
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["status"] = "blocked_required_specialist_work"
    scheduler["terminal_posture"] = "blocked_required_specialist_work"
    scheduler["failed_required_work_ref"] = {
        **_work_ref(work),
        "proposal_id": item.get("proposal_id"),
        "proposal_digest": item.get("proposal_digest"),
        "settlement": LEASE_CANCELLED,
        "nonexecution_reason": "input_reconstruction_failed",
    }
    scheduler["transition_history"].append(
        {
            "transition": "blocked_required_specialist_work",
            "scheduler_revision": scheduler["scheduler_revision"],
            "work_id": work.get("work_id"),
            "proposal_id": item.get("proposal_id"),
            "settlement": LEASE_CANCELLED,
            "nonexecution_reason": "input_reconstruction_failed",
        }
    )
    return _refresh_scheduler(scheduler)


def _completed_artifact(state: Any, role: str, evaluation_key: str) -> dict[str, Any]:
    raw = _mapping(
        state.projections.get(f"multicomponent_role:{role}:{evaluation_key}")
    )
    if raw.get("schema_version") != "multicomponent_semantic_role_artifact_v1":
        return {}
    return validate_multicomponent_role_artifact(raw, expected_role=role)


def _component_admissions(state: Any) -> dict[str, dict[str, Any]]:
    from core.multicomponent_component_admission import (
        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
    )

    aggregate = _mapping(state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE))
    return {
        str(item.get("component_id")): _mapping(item)
        for item in aggregate.get("component_admission_refs") or ()
        if isinstance(item, Mapping) and item.get("component_id")
    }


def _work(
    *,
    state: Any,
    scheduler: Mapping[str, Any],
    role: str,
    evaluation_key: str,
    input_packet: Mapping[str, Any],
    target_kind: str,
    component_id: str | None = None,
    synthesis_key: str | None = None,
    node_ref: Mapping[str, Any] | None = None,
    graph: Mapping[str, Any] | None = None,
    prerequisite_refs: Sequence[Mapping[str, Any]] = (),
    output_schema_variant: str | None = None,
    recovery_binding: Mapping[str, Any] | None = None,
    closure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = state.current_answer_contract or state.initial_answer_contract
    envelope = _mapping(scheduler.get("compatibility_envelope"))
    core: dict[str, Any] = {
        "schema_version": MULTICOMPONENT_WORK_SCHEMA_VERSION,
        "run_id": state.run_id,
        "request_id": state.request_id,
        "accepted_contract_ref": _contract_ref(contract),
        "graph_ref": _graph_ref(graph or {}),
        "target_kind": target_kind,
        "component_id": component_id,
        "synthesis_key": synthesis_key,
        "node_ref": _mapping(node_ref),
        "role": role,
        "logical_evaluation_key": evaluation_key,
        "input_packet_digest": safe_packet_digest(input_packet),
        "prerequisite_refs": [deepcopy(dict(item)) for item in prerequisite_refs],
        "parent_envelope_ref": {
            "envelope_id": envelope.get("envelope_id"),
            "envelope_digest": envelope.get("envelope_digest"),
        },
        "scheduler_revision": scheduler.get("scheduler_revision"),
        "output_schema_variant": output_schema_variant,
    }
    specialist_handoff_digest = _mapping(
        input_packet.get("specialist_need_handoff")
    ).get("handoff_digest")
    if specialist_handoff_digest:
        core["specialist_handoff_digest"] = specialist_handoff_digest
    if scheduler.get("schema_version") == MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION:
        core.update(
            {
                "work_kind": WORK_KIND_SEMANTIC_ROLE,
                "resource_class": (
                    RESOURCE_LOCAL_MODEL_TRANSPORT
                    if scheduler.get("backend_class") == BACKEND_LOCAL_OPENAI_COMPATIBLE
                    else RESOURCE_HOSTED_MODEL_TRANSPORT
                ),
                "executor_class": EXECUTOR_STRICT_ONE_SHOT_MODEL,
            }
        )
    recovery = _mapping(recovery_binding)
    if recovery:
        authorization = _mapping(recovery.get("recovery_authorization_ref"))
        amendment = _mapping(recovery.get("contract_amendment_admission_ref"))
        application = _mapping(recovery.get("contract_amendment_application_ref"))
        core["recovery_authorization_ref"] = {
            "recovery_authorization_id": authorization.get("authorization_id"),
            "recovery_authorization_digest": authorization.get(
                "authorization_digest"
            ),
        }
        core["contract_amendment_admission_ref"] = {
            "amendment_record_id": amendment.get("amendment_record_id"),
            "amendment_record_digest": amendment.get("amendment_record_digest"),
            "authorized_action_id": amendment.get("authorized_action_id"),
            "admission_digest": amendment.get("admission_digest"),
        }
        core["contract_amendment_application_ref"] = {
            "amendment_record_id": application.get("amendment_record_id"),
            "authorized_action_id": application.get("authorized_action_id"),
            "application_digest": application.get("application_digest"),
        }
    canonical_closure = _mapping(closure)
    if canonical_closure:
        core["selective_closure_ref"] = {
            "closure_id": canonical_closure.get("closure_id"),
            "closure_digest": canonical_closure.get("closure_digest"),
        }
    core["parallel_class"] = classify_work_parallelism(core)
    digest = _digest(core)
    return {
        **core,
        "work_id": f"multicomponent-work:{digest[:24]}",
        "work_digest": digest,
    }


def _specialist_work(
    *,
    state: Any,
    scheduler: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    from core.specialist_graph_runtime import build_specialist_work_node

    input_authority = reconstruct_specialist_bounded_input(
        state=state,
        proposal=proposal,
    )
    node = build_specialist_work_node(
        proposal=proposal,
        bounded_input_digest=str(input_authority["bounded_input_digest"]),
        bounded_input_lineage_refs=tuple(
            input_authority["bounded_input_lineage_refs"]
        ),
        bounded_input_reconstruction_ref=_mapping(
            input_authority["bounded_input_reconstruction_ref"]
        ),
    )
    target = _mapping(node.get("canonical_target_ref"))
    core = {
        "schema_version": MULTICOMPONENT_WORK_SCHEMA_VERSION,
        "run_id": state.run_id,
        "request_id": state.request_id,
        "accepted_contract_ref": deepcopy(node.get("accepted_contract_ref") or {}),
        "graph_ref": deepcopy(node.get("graph_ref") or {}),
        "target_kind": target.get("target_kind"),
        "component_id": (
            target.get("target_key") if target.get("target_kind") == "component" else None
        ),
        "synthesis_key": (
            target.get("target_key") if target.get("target_kind") == "synthesis" else None
        ),
        "node_ref": deepcopy(target),
        "role": WORK_KIND_SPECIALIST_CAPABILITY,
        "logical_evaluation_key": node.get("node_id"),
        "input_packet_digest": node.get("bounded_input_digest"),
        "prerequisite_refs": [
            deepcopy(node.get("proposal_ref") or {}),
            deepcopy(target),
        ],
        "scheduler_revision": scheduler.get("scheduler_revision"),
        "output_schema_variant": node.get("output_schema_ref"),
        "parallel_class": PARALLEL_SERIAL_ONLY,
        "work_kind": WORK_KIND_SPECIALIST_CAPABILITY,
        "resource_class": RESOURCE_DETERMINISTIC_SPECIALIST,
        "executor_class": EXECUTOR_REGISTERED_DETERMINISTIC,
        "specialist_work_node": node,
        "capability_id": node.get("capability_id"),
        "capability_version": node.get("capability_version"),
        "capability_descriptor_digest": node.get("capability_descriptor_digest"),
        "specialist_proposal_ref": deepcopy(node.get("proposal_ref") or {}),
    }
    digest = _digest(core)
    return {
        **core,
        "work_id": f"multicomponent-work:{digest[:24]}",
        "work_digest": digest,
    }


def reconstruct_specialist_bounded_input(
    *, state: Any, proposal: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct transient input and its retained digest/ref authority."""

    from core.component_work_graph_v1 import (
        COMPONENT_WORK_GRAPH_V1_STAGE,
        validate_component_work_graph_v1,
    )
    from core.specialist_graph_runtime import (
        proposal_ref,
        specialist_digest,
        validate_bound_specialist_proposal,
    )

    bound = validate_bound_specialist_proposal(proposal)
    if bound.get("proposal_authority") != "accepted":
        raise MulticomponentGraphSchedulingError(
            "Specialist input reconstruction requires an accepted proposal"
        )
    target = _mapping(bound.get("canonical_target_ref"))
    target_kind = str(target.get("target_kind") or "")
    target_key = str(target.get("target_key") or "")
    proposal_authority_ref = proposal_ref(bound)
    if target_kind == "component":
        context = _mapping(state.multicomponent_scheduler_context)
        analyst_input = _mapping(
            _mapping(context.get("component_analyst_input_packets")).get(
                target_key
            )
        )
        analyst = _completed_artifact(
            state, ROLE_COMPONENT_ANALYST, target_key
        )
        contract = (
            state.current_answer_contract or state.initial_answer_contract
        )
        component_ref = next(
            (
                _mapping(item)
                for item in contract.get("accepted_answer_component_refs")
                or ()
                if _mapping(item).get("component_id") == target_key
            ),
            {},
        )
        if (
            not analyst_input
            or not analyst
            or not component_ref
            or component_ref.get("component_revision")
            != target.get("target_revision")
            or component_ref.get("component_digest")
            != target.get("target_digest")
        ):
            raise MulticomponentGraphSchedulingError(
                "component Specialist input authority is stale or incomplete"
            )
        analyst_ref = {
            "artifact_id": analyst.get("artifact_id"),
            "artifact_digest": analyst.get("artifact_digest"),
        }
        analyst_input_digest = safe_packet_digest(analyst_input)
        packet = {
            "bounded_question": bound.get("bounded_question"),
            "canonical_target_ref": deepcopy(target),
            "analyst_artifact_ref": analyst_ref,
            "exact_component_and_evidence_input": deepcopy(analyst_input),
            "proposal_input_artifact_refs": deepcopy(
                bound.get("input_artifact_refs") or []
            ),
        }
        if bound.get("capability_request") is not None:
            from core.quantitative_specialist_product_activation import (
                build_component_quantitative_source_catalog,
            )

            packet["capability_request"] = deepcopy(
                bound.get("capability_request")
            )
            packet["quantitative_source_catalog"] = (
                build_component_quantitative_source_catalog(
                    component_ref=_mapping(analyst_input.get("component_ref")),
                    evidence_input=_mapping(
                        analyst_input.get("component_evidence")
                    ),
                    include_material=True,
                )
            )
            nominated_claim = str(
                _mapping(analyst.get("semantic_output")).get("claim_text")
                or ""
            )
            packet["nominated_claim"] = {
                "claim_text": nominated_claim,
                "claim_digest": specialist_digest(
                    {"claim_text": nominated_claim}
                ),
                "claim_source": "component_analyst_proposal",
            }
        lineage_refs = [
            proposal_authority_ref,
            deepcopy(target),
            analyst_ref,
            {"component_analyst_input_packet_digest": analyst_input_digest},
        ]
        reconstruction_core = {
            "schema_version": "specialist_bounded_input_reconstruction_ref_v1",
            "owner": "RunState.current_component_specialist_inputs",
            "proposal_ref": proposal_authority_ref,
            "canonical_target_ref": deepcopy(target),
            "accepted_contract_ref": _contract_ref(contract),
            "analyst_artifact_ref": analyst_ref,
            "component_analyst_input_packet_digest": analyst_input_digest,
        }
    elif target_kind == "synthesis":
        graph = validate_component_work_graph_v1(
            _mapping(state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
        )
        node = next(
            (
                _mapping(item)
                for item in graph.get("synthesis_nodes") or ()
                if _mapping(item).get("synthesis_key") == target_key
            ),
            {},
        )
        node_ref = _node_ref(node) if node else {}
        allowed_statuses = (
            {"proposed", "challenged", "blocked"}
            if bound.get("origin_role") == ROLE_SCRUTINEER
            else {"proposed"}
        )
        if (
            not node
            or node.get("status") not in allowed_statuses
            or node.get("node_revision") != target.get("target_revision")
            or node.get("node_digest") != target.get("target_digest")
        ):
            raise MulticomponentGraphSchedulingError(
                "synthesis Specialist input authority is stale or incomplete"
            )
        admitted_input_refs = [
            deepcopy(_mapping(item))
            for item in node.get("input_node_refs") or ()
        ]
        packet = {
            "bounded_question": bound.get("bounded_question"),
            "canonical_target_ref": deepcopy(target),
            "nominated_synthesis_ref": node_ref,
            "admitted_input_refs": admitted_input_refs,
            "proposal_input_artifact_refs": deepcopy(
                bound.get("input_artifact_refs") or []
            ),
        }
        if bound.get("capability_request") is not None:
            from core.quantitative_specialist_product_activation import (
                build_synthesis_quantitative_source_catalog,
            )

            context = _mapping(state.multicomponent_scheduler_context)
            packet["capability_request"] = deepcopy(
                bound.get("capability_request")
            )
            packet["quantitative_source_catalog"] = (
                build_synthesis_quantitative_source_catalog(
                    component_nodes=tuple(
                        _mapping(item)
                        for item in graph.get("component_nodes") or ()
                    ),
                    component_analyst_input_packets=_mapping(
                        context.get("component_analyst_input_packets")
                    ),
                    include_material=True,
                )
            )
            nominated_claim = str(node.get("claim_text") or "")
            packet["nominated_claim"] = {
                "claim_text": nominated_claim,
                "claim_digest": specialist_digest(
                    {"claim_text": nominated_claim}
                ),
                "claim_source": "cross_component_analyst_proposal",
            }
        graph_ref = _graph_ref(graph)
        admitted_input_refs_digest = specialist_digest(admitted_input_refs)
        lineage_refs = [
            proposal_authority_ref,
            deepcopy(target),
            graph_ref,
            node_ref,
            *admitted_input_refs,
        ]
        reconstruction_core = {
            "schema_version": "specialist_bounded_input_reconstruction_ref_v1",
            "owner": "RunState.current_synthesis_specialist_inputs",
            "proposal_ref": proposal_authority_ref,
            "canonical_target_ref": deepcopy(target),
            "graph_ref": graph_ref,
            "nominated_synthesis_ref": node_ref,
            "admitted_input_ref_count": len(admitted_input_refs),
            "admitted_input_refs_digest": admitted_input_refs_digest,
        }
    else:
        raise MulticomponentGraphSchedulingError(
            "Specialist input reconstruction target kind is unsupported"
        )
    reconstruction_ref = {
        **reconstruction_core,
        "reconstruction_ref_digest": _digest(reconstruction_core),
    }
    return {
        "transient_bounded_input": packet,
        "bounded_input_digest": specialist_digest(packet),
        "bounded_input_lineage_refs": lineage_refs,
        "bounded_input_reconstruction_ref": reconstruction_ref,
    }


def reconstruct_specialist_input_for_work(
    *, state: Any, work: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct and validate the exact transient packet for granted work."""

    from core.specialist_graph_runtime import validate_specialist_work_node

    item = _mapping(work)
    if item.get("work_kind") != WORK_KIND_SPECIALIST_CAPABILITY:
        raise MulticomponentGraphSchedulingError(
            "transient Specialist reconstruction requires Specialist work"
        )
    node = validate_specialist_work_node(
        _mapping(item.get("specialist_work_node"))
    )
    proposal_id = str(
        _mapping(node.get("proposal_ref")).get("proposal_id") or ""
    )
    plane = _mapping(state.projections.get("specialist_work_plane"))
    proposal = next(
        (
            _mapping(candidate)
            for candidate in plane.get("proposals") or ()
            if _mapping(candidate).get("proposal_id") == proposal_id
        ),
        {},
    )
    if not proposal:
        raise MulticomponentGraphSchedulingError(
            "Specialist work lost its bound proposal authority"
        )
    authority = reconstruct_specialist_bounded_input(
        state=state, proposal=proposal
    )
    if (
        authority.get("bounded_input_digest")
        != node.get("bounded_input_digest")
        or item.get("input_packet_digest") != node.get("bounded_input_digest")
        or authority.get("bounded_input_lineage_refs")
        != node.get("bounded_input_lineage_refs")
        or authority.get("bounded_input_reconstruction_ref")
        != node.get("bounded_input_reconstruction_ref")
    ):
        raise MulticomponentGraphSchedulingError(
            "reconstructed Specialist input does not match authorized work"
        )
    return deepcopy(_mapping(authority.get("transient_bounded_input")))


def classify_work_parallelism(work: Mapping[str, Any]) -> str:
    """Classify Phase 5A eligibility from exact canonical work facts."""

    item = _mapping(work)
    if item.get("work_kind") == WORK_KIND_SPECIALIST_CAPABILITY:
        return PARALLEL_SERIAL_ONLY
    initial_component = (
        item.get("target_kind") == "component"
        and bool(item.get("component_id"))
        and not _mapping(item.get("graph_ref"))
        and not _mapping(item.get("recovery_authorization_ref"))
        and not _mapping(item.get("contract_amendment_admission_ref"))
        and not _mapping(item.get("contract_amendment_application_ref"))
        and not _mapping(item.get("selective_closure_ref"))
    )
    if initial_component and item.get("role") == ROLE_COMPONENT_ANALYST:
        return PARALLEL_INITIAL_COMPONENT_ANALYST
    if initial_component and item.get("role") == ROLE_COMPONENT_DPRIME:
        return PARALLEL_INITIAL_COMPONENT_DPRIME
    return PARALLEL_SERIAL_ONLY


def derive_ready_work(state: Any, *, allow_active_lease: bool = False) -> list[dict[str, Any]]:
    """Incrementally derive current semantic work from canonical owners."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("status") != "active" and not (
        allow_active_lease
        and scheduler.get("status") == "draining_required_work_failed"
    ):
        return []
    if not allow_active_lease and any(
        _mapping(lease).get("status") in _ACTIVE_STATUSES
        for lease in scheduler.get("lease_history") or ()
    ):
        return []
    context = _mapping(state.multicomponent_scheduler_context)
    packets = {
        str(key): _mapping(value)
        for key, value in _mapping(context.get("component_analyst_input_packets")).items()
    }
    recovery_bindings = _mapping(context.get("recovery_bindings"))
    contract = state.current_answer_contract or state.initial_answer_contract
    all_component_refs = [
        _mapping(item) for item in contract.get("accepted_answer_component_refs") or ()
    ]
    component_refs = [
        item
        for item in all_component_refs
        if "direct" in list(item.get("allowed_support_kinds") or ("direct",))
    ]
    admissions = _component_admissions(state)
    specialist_state = _mapping(
        state.projections.get("specialist_work_plane")
    )
    specialist_remaining = int(
        _mapping(scheduler.get("specialist_compatibility_pool")).get(
            "specialist_remaining"
        )
        or 0
    )
    active_specialist_proposal_ids = {
        str(
            _mapping(_mapping(lease).get("work"))
            .get("specialist_proposal_ref", {})
            .get("proposal_id")
            or ""
        )
        for lease in scheduler.get("lease_history") or ()
        if _mapping(lease).get("status") in _ACTIVE_STATUSES
        and _mapping(_mapping(lease).get("work")).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    }

    def specialist_proposal_can_schedule(proposal: Mapping[str, Any]) -> bool:
        return bool(
            proposal.get("posture") == "required"
            or specialist_remaining > 0
            or (
                allow_active_lease
                and str(proposal.get("proposal_id") or "")
                in active_specialist_proposal_ids
            )
        )
    ready: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    for index, component_ref in enumerate(component_refs):
        component_id = str(component_ref.get("component_id") or "")
        analyst_input = packets.get(component_id, {})
        if not component_id or not analyst_input or component_id in admissions:
            continue
        recovery = _mapping(recovery_bindings.get(component_id))
        analyst = _completed_artifact(state, ROLE_COMPONENT_ANALYST, component_id)
        if not analyst:
            ready.append(
                (
                    (index, 0, component_id),
                    _work(
                        state=state,
                        scheduler=scheduler,
                        role=ROLE_COMPONENT_ANALYST,
                        evaluation_key=component_id,
                        input_packet=analyst_input,
                        target_kind="component",
                        component_id=component_id,
                        node_ref={
                            "component_id": component_id,
                            "component_revision": component_ref.get(
                                "component_revision"
                            ),
                            "component_digest": component_ref.get("component_digest"),
                        },
                        prerequisite_refs=(
                            _contract_ref(contract),
                            {"component_input_packet_digest": safe_packet_digest(analyst_input)},
                        ),
                        recovery_binding=recovery,
                    ),
                )
            )
            continue
        if specialist_state:
            from core.specialist_graph_runtime import pending_proposal_for_target

            pending_specialist = pending_proposal_for_target(
                specialist_state,
                target_kind="component",
                target_key=component_id,
            )
            if pending_specialist and specialist_proposal_can_schedule(
                pending_specialist
            ):
                return [
                    _specialist_work(
                        state=state,
                        scheduler=scheduler,
                        proposal=pending_specialist,
                    )
                ]
        dprime = _completed_artifact(state, ROLE_COMPONENT_DPRIME, component_id)
        if not dprime:
            from core.multicomponent_component_admission import (
                component_dprime_input_packet,
            )

            specialist_handoff = {}
            if specialist_state:
                from core.specialist_graph_runtime import handoff_for_target

                specialist_handoff = handoff_for_target(
                    specialist_state,
                    target_kind="component",
                    target_key=component_id,
                )
            dprime_input = component_dprime_input_packet(
                analyst_artifact=analyst,
                analyst_input_packet=analyst_input,
                specialist_need_handoff=specialist_handoff or None,
            )
            ready.append(
                (
                    (index, 1, component_id),
                    _work(
                        state=state,
                        scheduler=scheduler,
                        role=ROLE_COMPONENT_DPRIME,
                        evaluation_key=component_id,
                        input_packet=dprime_input,
                        target_kind="component",
                        component_id=component_id,
                        node_ref={
                            "component_id": component_id,
                            "component_revision": component_ref.get(
                                "component_revision"
                            ),
                            "component_digest": component_ref.get("component_digest"),
                        },
                        prerequisite_refs=(
                            _mapping(analyst.get("authorized_action_ref")),
                            {"analyst_artifact_digest": analyst.get("artifact_digest")},
                        ),
                        recovery_binding=recovery,
                    ),
                )
            )
    if ready:
        return [item for _, item in sorted(ready, key=lambda pair: pair[0])]

    from core.component_work_graph_v1 import (
        COMPONENT_WORK_GRAPH_V1_STAGE,
        MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
        cross_component_input_packet,
        scrutineer_input_packet,
        selective_cross_component_input_packet,
        synthesis_dprime_input_packet,
        validate_component_work_graph_v1,
        validate_selective_recomputation_closure,
    )

    graph_raw = _mapping(state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
    if not graph_raw:
        if len(admissions) != len(component_refs):
            return []
        if len(component_refs) == 1 and len(all_component_refs) == 1:
            # The installed N-component receiver terminates N=1 directly from
            # its admitted component; no cross-component relation exists to
            # schedule or synthesize.
            return []
        from core.component_work_node import component_work_node_v1_from_admitted_component

        nodes = [
            component_work_node_v1_from_admitted_component(
                run_id=state.run_id,
                request_id=state.request_id,
                accepted_component_ref=component_ref,
                component_admission_ref=admissions[str(component_ref["component_id"])],
            )
            for component_ref in component_refs
        ]
        packet = cross_component_input_packet(
            component_nodes=nodes,
            accepted_contract_ref=_contract_ref(contract),
            requested_synthesis_directive=str(
                context.get("requested_synthesis_directive") or ""
            ),
            component_analyst_input_packets=packets,
            accepted_component_refs=all_component_refs,
            requested_mode=str(context.get("requested_mode") or "Balanced"),
        )
        work = _work(
            state=state,
            scheduler=scheduler,
            role=ROLE_CROSS_COMPONENT_ANALYST,
            evaluation_key="graph-v1",
            input_packet=packet,
            target_kind="graph",
            prerequisite_refs=tuple(
                _component_admission_ref(admissions[str(item["component_id"])])
                for item in component_refs
            ),
        )
        return [work]

    graph = validate_component_work_graph_v1(graph_raw)
    closure: dict[str, Any] = {}
    closure_raw = _mapping(
        state.projections.get(MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE)
    )
    if closure_raw and int(graph.get("selective_recomputation_rounds") or 0) == 1:
        closure = validate_selective_recomputation_closure(closure_raw)
    if graph.get("dependency_posture") == "requires_selective_resynthesis":
        if not closure:
            raise MulticomponentGraphSchedulingError(
                "selective graph posture lacks current closure authority"
            )
        if not graph.get("selective_cross_component_analyst_ref"):
            packet = selective_cross_component_input_packet(graph, closure=closure)
            key = f"selective:graph-revision:{graph['graph_revision']}"
            return [
                _work(
                    state=state,
                    scheduler=scheduler,
                    role=ROLE_CROSS_COMPONENT_ANALYST,
                    evaluation_key=key,
                    input_packet=packet,
                    target_kind="graph",
                    graph=graph,
                    prerequisite_refs=(
                        _graph_ref(graph),
                        {
                            "closure_id": closure.get("closure_id"),
                            "closure_digest": closure.get("closure_digest"),
                        },
                    ),
                    output_schema_variant=SELECTIVE_CROSS_COMPONENT_SCHEMA,
                    closure=closure,
                )
            ]

    topological = list(graph.get("synthesis_topological_order") or ())
    for index, synthesis_key in enumerate(topological):
        node = next(
            _mapping(item)
            for item in graph.get("synthesis_nodes") or ()
            if _mapping(item).get("synthesis_key") == synthesis_key
        )
        if node.get("status") != "proposed":
            continue
        if specialist_state:
            from core.specialist_graph_runtime import pending_proposal_for_target

            pending_specialist = pending_proposal_for_target(
                specialist_state,
                target_kind="synthesis",
                target_key=str(synthesis_key),
            )
            if pending_specialist and specialist_proposal_can_schedule(
                pending_specialist
            ):
                return [
                    _specialist_work(
                        state=state,
                        scheduler=scheduler,
                        proposal=pending_specialist,
                    )
                ]
        try:
            specialist_handoff = {}
            if specialist_state:
                from core.specialist_graph_runtime import handoff_for_target

                specialist_handoff = handoff_for_target(
                    specialist_state,
                    target_kind="synthesis",
                    target_key=str(synthesis_key),
                )
            packet = synthesis_dprime_input_packet(
                graph,
                synthesis_key=synthesis_key,
                specialist_need_handoff=specialist_handoff or None,
            )
        except ValueError:
            # A proposed downstream node is not actionable until its exact
            # upstream synthesis authority has been admitted.
            continue
        if closure:
            key = f"{synthesis_key}:selective:graph-revision:{graph['graph_revision']}"
        elif int(graph.get("recovery_rounds") or 0):
            key = f"{synthesis_key}:graph-revision:{graph['graph_revision']}"
        elif node.get("specialist_result_ref"):
            key = (
                f"{synthesis_key}:specialist:"
                f"graph-revision:{graph['graph_revision']}"
            )
        else:
            key = str(synthesis_key)
        ready.append(
            (
                (len(component_refs) + 1, index, str(synthesis_key)),
                _work(
                    state=state,
                    scheduler=scheduler,
                    role=ROLE_SYNTHESIS_DPRIME,
                    evaluation_key=key,
                    input_packet=packet,
                    target_kind="synthesis",
                    synthesis_key=str(synthesis_key),
                    node_ref=_node_ref(node),
                    graph=graph,
                    prerequisite_refs=tuple(
                        _mapping(item) for item in node.get("input_node_refs") or ()
                    ),
                    closure=closure,
                ),
            )
        )
    if ready:
        return [item for _, item in sorted(ready, key=lambda pair: pair[0])]

    statuses = {
        str(_mapping(node).get("status") or "")
        for node in graph.get("synthesis_nodes") or ()
    }
    scrutiny_done = graph.get("scrutineer_status") in {
        "passed",
        "passed_with_caveats",
        "challenged",
        "blocked",
        "recovery_proposed",
    }
    if scrutiny_done and specialist_state:
        from core.specialist_graph_runtime import pending_proposal_for_target

        for node in graph.get("synthesis_nodes") or ():
            mapped_node = _mapping(node)
            key = str(mapped_node.get("synthesis_key") or "")
            pending_specialist = pending_proposal_for_target(
                specialist_state,
                target_kind="synthesis",
                target_key=key,
            )
            if pending_specialist and specialist_proposal_can_schedule(
                pending_specialist
            ):
                return [
                    _specialist_work(
                        state=state,
                        scheduler=scheduler,
                        proposal=pending_specialist,
                    )
                ]
    if (
        graph.get("scrutineer_required") is True
        and not scrutiny_done
        and "proposed" not in statuses
    ):
        if closure:
            key = f"full-case:selective:graph-revision:{graph['graph_revision']}"
        elif int(graph.get("recovery_rounds") or 0):
            key = f"full-case:graph-revision:{graph['graph_revision']}"
        elif graph.get("specialist_result_refs"):
            key = f"full-case:specialist:graph-revision:{graph['graph_revision']}"
        else:
            key = "full-case"
        packet = scrutineer_input_packet(graph)
        return [
            _work(
                state=state,
                scheduler=scheduler,
                role=ROLE_SCRUTINEER,
                evaluation_key=key,
                input_packet=packet,
                target_kind="whole_case",
                graph=graph,
                prerequisite_refs=tuple(
                    _node_ref(_mapping(item))
                    for item in graph.get("synthesis_nodes") or ()
                ),
                closure=closure,
            )
        ]
    return []


def work_is_current(state: Any, work: Mapping[str, Any]) -> bool:
    target = _mapping(work)
    try:
        return any(
            _semantic_work_identity(candidate) == _semantic_work_identity(target)
            for candidate in derive_ready_work(state, allow_active_lease=True)
        )
    except MulticomponentGraphSchedulingError:
        return False


def _semantic_work_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    identity = deepcopy(dict(value))
    for key in ("work_id", "work_digest", "scheduler_revision"):
        identity.pop(key, None)
    return identity


def _work_ref(work: Mapping[str, Any]) -> dict[str, Any]:
    item = _mapping(work)
    return {
        "work_id": item.get("work_id"),
        "work_digest": item.get("work_digest"),
        "role": item.get("role"),
        "parallel_class": item.get("parallel_class"),
        "logical_evaluation_key": item.get("logical_evaluation_key"),
        "input_packet_digest": item.get("input_packet_digest"),
        "target_kind": item.get("target_kind"),
        "component_id": item.get("component_id"),
        "synthesis_key": item.get("synthesis_key"),
        "work_kind": item.get("work_kind"),
        "resource_class": item.get("resource_class"),
        "executor_class": item.get("executor_class"),
        "capability_id": item.get("capability_id"),
        "capability_version": item.get("capability_version"),
        "specialist_handoff_digest": item.get("specialist_handoff_digest"),
    }


def derive_ready_batch_work(state: Any) -> list[dict[str, Any]]:
    """Return the exact contiguous V2 prefix eligible for one atomic grant."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("schema_version") not in _BATCH_SCHEDULER_VERSIONS:
        raise MulticomponentGraphSchedulingError("batch membership requires scheduler V2/V3")
    ready = derive_ready_work(state)
    if not ready:
        return []
    envelope = _mapping(scheduler.get("compatibility_envelope"))
    remaining = int(envelope.get("remaining_units") or 0)
    first = _mapping(ready[0])
    role = str(first.get("role") or "")
    parallel_class = classify_work_parallelism(first)
    if first.get("parallel_class") != parallel_class:
        raise MulticomponentGraphSchedulingError("work parallel classification mismatch")
    if first.get("work_kind") == WORK_KIND_SPECIALIST_CAPABILITY:
        pool = _mapping(scheduler.get("specialist_compatibility_pool"))
        if int(pool.get("specialist_remaining") or 0) <= 0:
            return []
        limit = 1
    else:
        if remaining <= 0:
            return []
        role_used = int(_mapping(envelope.get("role_reserved_units")).get(role) or 0) + int(
            _mapping(envelope.get("role_spent_units")).get(role) or 0
        )
        role_remaining = int(MULTICOMPONENT_ROLE_CALL_LIMITS[role]) - role_used
        if role_remaining <= 0:
            return []
        effective_width = int(scheduler.get("effective_width") or 0)
        width = 1 if parallel_class == PARALLEL_SERIAL_ONLY else effective_width
        limit = min(width, remaining, role_remaining)
    selected: list[dict[str, Any]] = []
    seen: dict[str, set[str]] = {
        "work_id": set(),
        "logical_evaluation_key": set(),
        "component_id": set(),
        "input_packet_digest": set(),
    }
    for candidate_raw in ready:
        if len(selected) >= limit:
            break
        candidate = _mapping(candidate_raw)
        candidate_class = classify_work_parallelism(candidate)
        if (
            candidate.get("role") != role
            or candidate.get("work_kind") != first.get("work_kind")
            or candidate_class != parallel_class
            or candidate.get("parallel_class") != candidate_class
            or candidate.get("scheduler_revision") != first.get("scheduler_revision")
        ):
            break
        duplicate = False
        for key in seen:
            value = str(candidate.get(key) or "")
            if (not value and key != "component_id") or (
                value and value in seen[key]
            ):
                duplicate = True
                break
        if duplicate:
            raise MulticomponentGraphSchedulingError(
                "batch membership contains duplicate canonical identity"
            )
        selected.append(deepcopy(candidate))
        for key in seen:
            value = str(candidate.get(key) or "")
            if value:
                seen[key].add(value)
    return selected


def _batch_index(scheduler: Mapping[str, Any], batch_id: str) -> int:
    for index, item in enumerate(scheduler.get("batch_history") or ()):
        if _mapping(item).get("batch_id") == batch_id:
            return index
    raise MulticomponentGraphSchedulingError("unknown scheduler batch")


def grant_next_batch(
    *, state: Any, action_ref: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Atomically reserve the exact V2 contiguous prefix and its leases."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("schema_version") not in _BATCH_SCHEDULER_VERSIONS:
        raise MulticomponentGraphSchedulingError("batch grant requires scheduler V2/V3")
    ready = derive_ready_work(state)
    if not ready:
        raise MulticomponentGraphSchedulingError("scheduler has no current ready work")
    selected = derive_ready_batch_work(state)
    next_revision = int(scheduler.get("scheduler_revision") or 0) + 1
    first = _mapping(ready[0])
    parallel_class = classify_work_parallelism(first)
    batch_seed = {
        "schema_version": MULTICOMPONENT_BATCH_SCHEMA_VERSION,
        "run_id": state.run_id,
        "request_id": state.request_id,
        "scheduler_revision_at_derivation": first.get("scheduler_revision"),
        "accepted_contract_ref": deepcopy(first.get("accepted_contract_ref")),
        "graph_ref": deepcopy(first.get("graph_ref")),
        "backend_class": scheduler.get("backend_class"),
        "effective_width": scheduler.get("effective_width"),
        "parallel_class": parallel_class,
        "work_kind": first.get("work_kind", WORK_KIND_SEMANTIC_ROLE),
        "resource_class": first.get("resource_class"),
        "executor_class": first.get("executor_class"),
        "ordered_work_refs": [_work_ref(item) for item in (selected or [first])],
    }
    batch_digest = _digest(batch_seed)
    batch_id = f"multicomponent-batch:{batch_digest[:24]}"
    envelope = _mapping(scheduler.get("compatibility_envelope"))
    exhausted = not selected
    batch: dict[str, Any] = {
        **batch_seed,
        "batch_id": batch_id,
        "batch_digest": batch_digest,
        "lease_group": {
            "schema_version": MULTICOMPONENT_BATCH_LEASE_GROUP_SCHEMA_VERSION,
            "batch_id": batch_id,
            "batch_digest": batch_digest,
            "ordered_lease_refs": [],
        },
        "ordered_lease_refs": [],
        "ordered_child_action_refs": [],
        "status": LEASE_DENIED_EXHAUSTED if exhausted else LEASE_GRANTED,
        "grant_action_ref": deepcopy(dict(action_ref)),
        "dispatch_action_ref": {},
        "cancellation_action_ref": {},
        "terminal_settlement_summary": {},
        "safe_accounting_summary": {},
    }
    leases: list[dict[str, Any]] = []
    if exhausted:
        lease_core = {
            "schema_version": MULTICOMPONENT_LEASE_V2_SCHEMA_VERSION,
            "run_id": state.run_id,
            "request_id": state.request_id,
            "batch_id": batch_id,
            "batch_digest": batch_digest,
            "batch_index": 0,
            "work": deepcopy(first),
            "grant_action_ref": deepcopy(dict(action_ref)),
            "scheduler_revision_at_derivation": first.get("scheduler_revision"),
            "scheduler_revision_at_grant": next_revision,
            "reservation_units": 0,
            "status": LEASE_DENIED_EXHAUSTED,
            "dispatch_action_ref": {},
            "role_action_ref": {},
            "settlement_reason": (
                "specialist_compatibility_pool_exhausted"
                if first.get("work_kind") == WORK_KIND_SPECIALIST_CAPABILITY
                else "compatibility_envelope_exhausted"
            ),
        }
        lease_digest = _digest(lease_core)
        denied_lease = {
            **lease_core,
            "lease_id": f"multicomponent-lease:{lease_digest[:24]}",
            "lease_digest": lease_digest,
        }
        denied_ref = {
            "lease_id": denied_lease["lease_id"],
            "lease_digest": denied_lease["lease_digest"],
            "batch_index": 0,
            "work_id": first.get("work_id"),
            "work_digest": first.get("work_digest"),
        }
        batch["ordered_lease_refs"] = [deepcopy(denied_ref)]
        batch["lease_group"]["ordered_lease_refs"] = [deepcopy(denied_ref)]
        scheduler["lease_history"].append(denied_lease)
        scheduler["status"] = "blocked_exhausted"
        scheduler["terminal_posture"] = "blocked_exhausted"
        scheduler["exhausted_required_work_ref"] = _work_ref(first)
    else:
        for batch_index, work in enumerate(selected):
            lease_core = {
                "schema_version": MULTICOMPONENT_LEASE_V2_SCHEMA_VERSION,
                "run_id": state.run_id,
                "request_id": state.request_id,
                "batch_id": batch_id,
                "batch_digest": batch_digest,
                "batch_index": batch_index,
                "work": deepcopy(work),
                "grant_action_ref": deepcopy(dict(action_ref)),
                "scheduler_revision_at_derivation": work.get("scheduler_revision"),
                "scheduler_revision_at_grant": next_revision,
                "reservation_units": 1,
                "status": LEASE_GRANTED,
                "dispatch_action_ref": {},
                "role_action_ref": {},
                "settlement_reason": None,
            }
            lease_digest = _digest(lease_core)
            lease = {
                **lease_core,
                "lease_id": f"multicomponent-lease:{lease_digest[:24]}",
                "lease_digest": lease_digest,
            }
            leases.append(lease)
        lease_refs = [
            {
                "lease_id": lease["lease_id"],
                "lease_digest": lease["lease_digest"],
                "batch_index": lease["batch_index"],
                "work_id": _mapping(lease["work"]).get("work_id"),
                "work_digest": _mapping(lease["work"]).get("work_digest"),
            }
            for lease in leases
        ]
        batch["ordered_lease_refs"] = deepcopy(lease_refs)
        batch["lease_group"]["ordered_lease_refs"] = deepcopy(lease_refs)
        if first.get("work_kind") == WORK_KIND_SPECIALIST_CAPABILITY:
            pool = _mapping(scheduler.get("specialist_compatibility_pool"))
            pool["specialist_remaining"] = int(pool["specialist_remaining"]) - len(leases)
            scheduler["specialist_compatibility_pool"] = pool
        else:
            envelope["remaining_units"] = int(envelope["remaining_units"]) - len(leases)
            scheduler["compatibility_envelope"] = envelope
        scheduler["lease_history"].extend(leases)
    scheduler["scheduler_revision"] = next_revision
    scheduler["last_ready_work"] = [deepcopy(item) for item in ready]
    scheduler["batch_history"].append(batch)
    counters = _mapping(scheduler.get("accounting_counters"))
    counters["batch_count"] = int(counters.get("batch_count") or 0) + 1
    if len(leases) > 1:
        counters["parallel_batch_count"] = int(
            counters.get("parallel_batch_count") or 0
        ) + 1
    else:
        counters["width_1_batch_count"] = int(counters.get("width_1_batch_count") or 0) + 1
    scheduler["accounting_counters"] = counters
    scheduler["transition_history"].append(
        {
            "transition": batch["status"],
            "scheduler_revision": next_revision,
            "batch_id": batch_id,
            "ordered_work_ids": [item["work_id"] for item in batch["ordered_work_refs"]],
            "ordered_lease_ids": [item["lease_id"] for item in batch["ordered_lease_refs"]],
            "ready_work_count": len(ready),
        }
    )
    return _refresh_scheduler(scheduler), deepcopy(batch)


def cancel_batch(
    *, state: Any, batch_id: str, action_ref: Mapping[str, Any], reason: str
) -> dict[str, Any]:
    """Atomically return every still-granted reservation in one V2 batch."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("schema_version") not in _BATCH_SCHEDULER_VERSIONS:
        raise MulticomponentGraphSchedulingError("batch cancellation requires scheduler V2/V3")
    batch_index = _batch_index(scheduler, batch_id)
    batch = _mapping(scheduler["batch_history"][batch_index])
    if batch.get("status") != LEASE_GRANTED:
        raise MulticomponentGraphSchedulingError("batch is not cancellable")
    lease_ids = [
        str(_mapping(item).get("lease_id") or "")
        for item in batch.get("ordered_lease_refs") or ()
    ]
    lease_indexes = [_lease_index(scheduler, lease_id) for lease_id in lease_ids]
    leases = [_mapping(scheduler["lease_history"][index]) for index in lease_indexes]
    if not leases or any(lease.get("status") != LEASE_GRANTED for lease in leases):
        raise MulticomponentGraphSchedulingError(
            "batch cancellation requires every reservation to remain granted"
        )
    cancellation_reason = str(reason or "predispatch_batch_cancellation")[:160]
    for index, lease in zip(lease_indexes, leases, strict=True):
        lease["status"] = LEASE_CANCELLED
        lease["settlement_reason"] = cancellation_reason
        scheduler["lease_history"][index] = lease
    next_revision = int(scheduler["scheduler_revision"]) + 1
    batch["status"] = LEASE_CANCELLED
    batch["cancellation_action_ref"] = deepcopy(dict(action_ref))
    batch["terminal_settlement_summary"] = {
        "settlement": LEASE_CANCELLED,
        "lease_count": len(leases),
        "all_reservations_returned": True,
    }
    scheduler["batch_history"][batch_index] = batch
    specialist_batch = all(
        _mapping(lease.get("work")).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
        for lease in leases
    )
    if specialist_batch:
        pool = _mapping(scheduler.get("specialist_compatibility_pool"))
        pool["specialist_remaining"] = int(pool["specialist_remaining"]) + len(leases)
        pool["specialist_returned"] = int(pool.get("specialist_returned") or 0) + len(leases)
        scheduler["specialist_compatibility_pool"] = pool
    else:
        envelope = _mapping(scheduler.get("compatibility_envelope"))
        envelope["remaining_units"] = int(envelope["remaining_units"]) + len(leases)
        envelope["returned_units"] = int(envelope.get("returned_units") or 0) + len(leases)
        scheduler["compatibility_envelope"] = envelope
    scheduler["scheduler_revision"] = next_revision
    scheduler["transition_history"].append(
        {
            "transition": LEASE_CANCELLED,
            "scheduler_revision": next_revision,
            "batch_id": batch_id,
            "ordered_lease_ids": lease_ids,
            "returned_units": len(leases),
        }
    )
    return _refresh_scheduler(scheduler)


def dispatch_batch(
    *,
    state: Any,
    batch_id: str,
    dispatch_action_ref: Mapping[str, Any],
    descriptor_set: Mapping[str, Any],
    child_action_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Atomically spend a V2 batch and bind its canonical child actions."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("schema_version") not in _BATCH_SCHEDULER_VERSIONS:
        raise MulticomponentGraphSchedulingError("batch dispatch requires scheduler V2/V3")
    batch_index = _batch_index(scheduler, batch_id)
    batch = _mapping(scheduler["batch_history"][batch_index])
    if batch.get("status") != LEASE_GRANTED:
        raise MulticomponentGraphSchedulingError("batch is not dispatchable")
    lease_refs = [_mapping(item) for item in batch.get("ordered_lease_refs") or ()]
    lease_indexes = [
        _lease_index(scheduler, str(item.get("lease_id") or "")) for item in lease_refs
    ]
    leases = [_mapping(scheduler["lease_history"][index]) for index in lease_indexes]
    if not leases or any(lease.get("status") != LEASE_GRANTED for lease in leases):
        raise MulticomponentGraphSchedulingError(
            "batch dispatch requires every exact granted lease"
        )
    current_ready = derive_ready_work(state, allow_active_lease=True)
    if len(current_ready) < len(leases) or any(
        _semantic_work_identity(current_ready[index])
        != _semantic_work_identity(_mapping(lease.get("work")))
        for index, lease in enumerate(leases)
    ):
        raise MulticomponentGraphSchedulingError(
            "batch dispatch membership is not the current contiguous ready prefix"
        )
    descriptors = _mapping(descriptor_set)
    declared_set_digest = descriptors.get("descriptor_set_digest")
    descriptor_set_core = deepcopy(descriptors)
    descriptor_set_core.pop("descriptor_set_digest", None)
    if (
        descriptors.get("schema_version")
        != MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION
        or descriptors.get("batch_id") != batch.get("batch_id")
        or descriptors.get("batch_digest") != batch.get("batch_digest")
        or declared_set_digest != _digest(descriptor_set_core)
    ):
        raise MulticomponentGraphSchedulingError("descriptor-set identity mismatch")
    descriptor_items = [
        _mapping(item) for item in descriptors.get("ordered_descriptors") or ()
    ]
    action_refs = [_mapping(item) for item in child_action_refs]
    if len(descriptor_items) != len(leases) or len(action_refs) != len(leases):
        raise MulticomponentGraphSchedulingError(
            "batch dispatch child cardinality mismatch"
        )
    expected_action_types = {
        ROLE_COMPONENT_ANALYST: "multicomponent_component_analyst_execute",
        ROLE_COMPONENT_DPRIME: "multicomponent_component_dprime_execute",
        ROLE_CROSS_COMPONENT_ANALYST: "multicomponent_cross_analyst_execute",
        ROLE_SYNTHESIS_DPRIME: "multicomponent_synthesis_dprime_execute",
        ROLE_SCRUTINEER: "multicomponent_scrutineer_execute",
        WORK_KIND_SPECIALIST_CAPABILITY: "specialist_capability_execute",
    }
    seen_keys: set[str] = set()
    for batch_index_value, (lease, descriptor, action_ref) in enumerate(
        zip(leases, descriptor_items, action_refs, strict=True)
    ):
        work = _mapping(lease.get("work"))
        descriptor_core = deepcopy(descriptor)
        declared_descriptor_digest = descriptor_core.pop("descriptor_digest", None)
        expected = {
            "schema_version": MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION,
            "batch_id": batch.get("batch_id"),
            "batch_digest": batch.get("batch_digest"),
            "batch_index": batch_index_value,
            "work_id": work.get("work_id"),
            "work_digest": work.get("work_digest"),
            "lease_id": lease.get("lease_id"),
            "lease_digest": lease.get("lease_digest"),
            "role": work.get("role"),
            "action_type": expected_action_types[str(work.get("role") or "")],
            "logical_evaluation_key": work.get("logical_evaluation_key"),
            "input_packet_digest": work.get("input_packet_digest"),
            "output_schema_variant": work.get("output_schema_variant"),
        }
        if any(descriptor_core.get(key) != value for key, value in expected.items()):
            raise MulticomponentGraphSchedulingError(
                "private child descriptor and granted lease disagree"
            )
        if declared_descriptor_digest != _digest(descriptor_core):
            raise MulticomponentGraphSchedulingError("private child descriptor digest mismatch")
        logical_key = str(work.get("logical_evaluation_key") or "")
        if logical_key in seen_keys:
            raise MulticomponentGraphSchedulingError("descriptor logical key is duplicate")
        seen_keys.add(logical_key)
        expected_ref = {
            "batch_index": batch_index_value,
            "role": work.get("role"),
            "logical_evaluation_key": logical_key,
            "input_packet_digest": work.get("input_packet_digest"),
            "lease_id": lease.get("lease_id"),
            "lease_digest": lease.get("lease_digest"),
            "work_id": work.get("work_id"),
            "work_digest": work.get("work_digest"),
        }
        if any(action_ref.get(key) != value for key, value in expected_ref.items()):
            raise MulticomponentGraphSchedulingError(
                "child action ref and descriptor binding disagree"
            )
    child_sequences = [int(item.get("sequence") or 0) for item in action_refs]
    if child_sequences != list(range(child_sequences[0], child_sequences[0] + len(leases))):
        raise MulticomponentGraphSchedulingError("child action sequences are not contiguous")
    for index, (lease_index, lease, action_ref) in enumerate(
        zip(lease_indexes, leases, action_refs, strict=True)
    ):
        lease["status"] = LEASE_EXECUTION_STARTED
        lease["dispatch_action_ref"] = deepcopy(dict(dispatch_action_ref))
        lease["role_action_ref"] = deepcopy(action_ref)
        scheduler["lease_history"][lease_index] = lease
    next_revision = int(scheduler["scheduler_revision"]) + 1
    batch["status"] = "dispatch_committed"
    batch["dispatch_action_ref"] = deepcopy(dict(dispatch_action_ref))
    batch["descriptor_set_digest"] = declared_set_digest
    batch["ordered_child_action_refs"] = deepcopy(action_refs)
    specialist_batch = all(
        _mapping(lease.get("work")).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
        for lease in leases
    )
    batch["safe_accounting_summary"] = (
        {
            "schema_version": "specialist_batch_accounting_summary_v1",
            "specialist_dispatch_committed_unit_count": len(leases),
            "deterministic_execution_started_count": 0,
            "deterministic_execution_completed_count": 0,
            "provider_request_attempt_count": 0,
            "model_call_count": 0,
            "token_usage": 0,
            "model_cost": 0,
        }
        if specialist_batch
        else {
            "schema_version": MULTICOMPONENT_BATCH_ACCOUNTING_SUMMARY_SCHEMA_VERSION,
            "dispatch_committed_unit_count": len(leases),
            "transport_submission_count": 0,
            "transport_started_count": 0,
            "transport_completed_count": 0,
            "provider_request_attempt_count": 0,
            "successful_artifact_count": 0,
            "failed_submission_count": 0,
            "failed_transport_count": 0,
            "stale_result_count": 0,
        }
    )
    scheduler["batch_history"][batch_index] = batch
    counters = _mapping(scheduler.get("accounting_counters"))
    if not specialist_batch:
        counters["dispatch_committed_unit_count"] = int(
            counters.get("dispatch_committed_unit_count") or 0
        ) + len(leases)
    scheduler["accounting_counters"] = counters
    scheduler["scheduler_revision"] = next_revision
    scheduler["transition_history"].append(
        {
            "transition": "batch_dispatch_committed",
            "scheduler_revision": next_revision,
            "batch_id": batch_id,
            "dispatch_action_id": _mapping(dispatch_action_ref).get("action_id"),
            "ordered_child_action_ids": [item.get("action_id") for item in action_refs],
            "dispatch_committed_unit_count": len(leases),
        }
    )
    return _refresh_scheduler(scheduler)


def grant_next_lease(
    *, state: Any, action_ref: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    ready = derive_ready_work(state)
    if not ready:
        raise MulticomponentGraphSchedulingError("scheduler has no current ready work")
    work = ready[0]
    envelope = _mapping(scheduler.get("compatibility_envelope"))
    role = str(work.get("role") or "")
    role_used = int(_mapping(envelope.get("role_reserved_units")).get(role) or 0) + int(
        _mapping(envelope.get("role_spent_units")).get(role) or 0
    )
    exhausted = int(envelope.get("remaining_units") or 0) <= 0 or role_used >= int(
        MULTICOMPONENT_ROLE_CALL_LIMITS[role]
    )
    next_revision = int(scheduler.get("scheduler_revision") or 0) + 1
    lease_core = {
        "schema_version": MULTICOMPONENT_LEASE_SCHEMA_VERSION,
        "run_id": state.run_id,
        "request_id": state.request_id,
        "work": deepcopy(work),
        "grant_action_ref": deepcopy(dict(action_ref)),
        "scheduler_revision_at_derivation": work.get("scheduler_revision"),
        "scheduler_revision_at_grant": next_revision,
        "reservation_units": 0 if exhausted else 1,
        "status": LEASE_DENIED_EXHAUSTED if exhausted else LEASE_GRANTED,
        "dispatch_action_ref": {},
        "role_action_ref": {},
        "settlement_reason": "compatibility_envelope_exhausted" if exhausted else None,
    }
    lease_digest = _digest(lease_core)
    lease = {
        **lease_core,
        "lease_id": f"multicomponent-lease:{lease_digest[:24]}",
        "lease_digest": lease_digest,
    }
    scheduler["scheduler_revision"] = next_revision
    scheduler["last_ready_work"] = [deepcopy(item) for item in ready]
    scheduler["lease_history"].append(lease)
    scheduler["transition_history"].append(
        {
            "transition": lease["status"],
            "scheduler_revision": next_revision,
            "lease_id": lease["lease_id"],
            "work_id": work["work_id"],
            "role": role,
            "ready_work_count": len(ready),
        }
    )
    if exhausted:
        scheduler["status"] = "blocked_exhausted"
        scheduler["exhausted_required_work_ref"] = {
            "work_id": work["work_id"],
            "work_digest": work["work_digest"],
            "role": role,
            "target_kind": work.get("target_kind"),
            "component_id": work.get("component_id"),
            "synthesis_key": work.get("synthesis_key"),
        }
    else:
        envelope["remaining_units"] = int(envelope["remaining_units"]) - 1
        scheduler["compatibility_envelope"] = envelope
    return _refresh_scheduler(scheduler), deepcopy(lease)


def _lease_index(scheduler: Mapping[str, Any], lease_id: str) -> int:
    for index, item in enumerate(scheduler.get("lease_history") or ()):
        if _mapping(item).get("lease_id") == lease_id:
            return index
    raise MulticomponentGraphSchedulingError("unknown scheduler lease")


def dispatch_lease(
    *,
    state: Any,
    lease_id: str,
    dispatch_action_ref: Mapping[str, Any],
    role_action_ref: Mapping[str, Any],
) -> dict[str, Any]:
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    index = _lease_index(scheduler, lease_id)
    lease = _mapping(scheduler["lease_history"][index])
    if lease.get("status") != LEASE_GRANTED:
        raise MulticomponentGraphSchedulingError("lease is not dispatchable")
    if not work_is_current(state, _mapping(lease.get("work"))):
        raise MulticomponentGraphSchedulingError("lease semantic authority is stale")
    role_action = _mapping(role_action_ref)
    work = _mapping(lease.get("work"))
    expected = {
        "role": work.get("role"),
        "logical_evaluation_key": work.get("logical_evaluation_key"),
        "input_packet_digest": work.get("input_packet_digest"),
        "lease_id": lease.get("lease_id"),
        "lease_digest": lease.get("lease_digest"),
        "work_id": work.get("work_id"),
        "work_digest": work.get("work_digest"),
    }
    if any(role_action.get(key) != value for key, value in expected.items()):
        raise MulticomponentGraphSchedulingError("role action and lease binding disagree")
    lease["status"] = LEASE_EXECUTION_STARTED
    lease["dispatch_action_ref"] = deepcopy(dict(dispatch_action_ref))
    lease["role_action_ref"] = deepcopy(role_action)
    scheduler["lease_history"][index] = lease
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["transition_history"].append(
        {
            "transition": LEASE_EXECUTION_STARTED,
            "scheduler_revision": scheduler["scheduler_revision"],
            "lease_id": lease_id,
            "work_id": work.get("work_id"),
            "role_action_id": role_action.get("action_id"),
        }
    )
    return _refresh_scheduler(scheduler)


def settle_role_lease(
    *,
    state: Any,
    action_inputs: Mapping[str, Any],
    settlement: str,
) -> dict[str, Any]:
    if settlement not in {LEASE_COMPLETED, LEASE_FAILED, LEASE_STALE}:
        raise MulticomponentGraphSchedulingError("invalid postdispatch settlement")
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    inputs = _mapping(action_inputs)
    index = _lease_index(scheduler, str(inputs.get("lease_id") or ""))
    lease = _mapping(scheduler["lease_history"][index])
    work = _mapping(lease.get("work"))
    if lease.get("status") != LEASE_EXECUTION_STARTED:
        raise MulticomponentGraphSchedulingError("lease is not awaiting settlement")
    for key in (
        "batch_id",
        "batch_digest",
        "batch_index",
        "lease_digest",
        "work_id",
        "work_digest",
        "role",
        "logical_evaluation_key",
        "input_packet_digest",
    ):
        expected = (
            lease.get(key)
            if key in {"batch_id", "batch_digest", "batch_index", "lease_digest"}
            else work.get(key)
        )
        if inputs.get(key) != expected:
            raise MulticomponentGraphSchedulingError(
                "role action settlement binding mismatch"
            )
    current = work_is_current(state, work)
    if settlement == LEASE_COMPLETED and not current:
        raise MulticomponentGraphSchedulingError(
            "stale semantic work cannot complete successfully"
        )
    if settlement == LEASE_STALE and current:
        raise MulticomponentGraphSchedulingError(
            "current semantic work cannot be settled as stale"
        )
    lease["status"] = settlement
    lease["settlement_reason"] = inputs.get("failure_kind")
    scheduler["lease_history"][index] = lease
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["transition_history"].append(
        {
            "transition": settlement,
            "scheduler_revision": scheduler["scheduler_revision"],
            "lease_id": lease.get("lease_id"),
            "work_id": work.get("work_id"),
            "role": work.get("role"),
        }
    )
    if (
        scheduler.get("schema_version") in _BATCH_SCHEDULER_VERSIONS
        and inputs.get("batch_id")
    ):
        submitted = inputs.get("transport_submitted") is True
        started = inputs.get("transport_started") is True
        completed = inputs.get("transport_completed") is True
        attempt_count = max(
            0, min(1, int(inputs.get("provider_request_attempt_count") or 0))
        )
        if started and not submitted or completed and not started:
            raise MulticomponentGraphSchedulingError(
                "transport accounting facts are not monotonic"
            )
        if attempt_count and not started:
            raise MulticomponentGraphSchedulingError(
                "provider request attempts require a started transport"
            )
        counters = _mapping(scheduler.get("accounting_counters"))
        counters["transport_submission_count"] = int(
            counters.get("transport_submission_count") or 0
        ) + int(submitted)
        counters["transport_started_count"] = int(
            counters.get("transport_started_count") or 0
        ) + int(started)
        counters["transport_completed_count"] = int(
            counters.get("transport_completed_count") or 0
        ) + int(completed)
        counters["provider_request_attempt_count"] = int(
            counters.get("provider_request_attempt_count") or 0
        ) + attempt_count
        if settlement == LEASE_COMPLETED:
            outcome_key = "successful_artifact_count"
        elif settlement == LEASE_STALE:
            outcome_key = "stale_result_count"
        elif inputs.get("failure_kind") in {
            "executor_initialization_failure",
            "failed_submission",
        }:
            outcome_key = "failed_submission_count"
        else:
            outcome_key = "failed_transport_count"
        counters[outcome_key] = int(counters.get(outcome_key) or 0) + 1
        observed_max = max(0, int(inputs.get("observed_batch_max_in_flight") or 0))
        counters["maximum_observed_in_flight_transports"] = max(
            int(counters.get("maximum_observed_in_flight_transports") or 0),
            observed_max,
        )
        counters["physical_overlap_observed"] = (
            counters.get("maximum_observed_in_flight_transports", 0) > 1
        )
        scheduler["accounting_counters"] = counters
        batch_id = str(inputs.get("batch_id") or "")
        batch_index = _batch_index(scheduler, batch_id)
        batch = _mapping(scheduler["batch_history"][batch_index])
        summary = _mapping(batch.get("safe_accounting_summary"))
        summary["transport_submission_count"] = int(
            summary.get("transport_submission_count") or 0
        ) + int(submitted)
        summary["transport_started_count"] = int(
            summary.get("transport_started_count") or 0
        ) + int(started)
        summary["transport_completed_count"] = int(
            summary.get("transport_completed_count") or 0
        ) + int(completed)
        summary["provider_request_attempt_count"] = int(
            summary.get("provider_request_attempt_count") or 0
        ) + attempt_count
        summary[outcome_key] = int(summary.get(outcome_key) or 0) + 1
        batch["safe_accounting_summary"] = summary
        batch_leases = [
            _mapping(scheduler["lease_history"][_lease_index(scheduler, str(ref["lease_id"]))])
            for ref in batch.get("ordered_lease_refs") or ()
        ]
        batch_active = [
            item for item in batch_leases if item.get("status") in _ACTIVE_STATUSES
        ]
        if batch_active:
            batch["status"] = "draining"
        else:
            settlements = [str(item.get("status") or "") for item in batch_leases]
            batch["status"] = "settled"
            batch["terminal_settlement_summary"] = {
                "lease_count": len(batch_leases),
                "ordered_settlements": settlements,
                "all_leases_terminal": all(
                    status in _TERMINAL_STATUSES for status in settlements
                ),
            }
        scheduler["batch_history"][batch_index] = batch
    if settlement in {LEASE_FAILED, LEASE_STALE}:
        scheduler["failed_required_work_ref"] = {
            "work_id": work.get("work_id"),
            "work_digest": work.get("work_digest"),
            "role": work.get("role"),
            "settlement": settlement,
        }
    active_after = [
        item
        for item in scheduler["lease_history"]
        if _mapping(item).get("status") in _ACTIVE_STATUSES
    ]
    if scheduler.get("failed_required_work_ref"):
        scheduler["status"] = (
            "draining_required_work_failed"
            if active_after
            else "blocked_required_work_failed"
        )
        scheduler["terminal_posture"] = (
            None if active_after else "blocked_required_work_failed"
        )
    return _refresh_scheduler(scheduler)


def settle_specialist_lease(
    *, state: Any, action_inputs: Mapping[str, Any], settlement: str
) -> dict[str, Any]:
    """Settle deterministic Specialist work without semantic/model accounting."""

    if settlement not in {
        LEASE_COMPLETED,
        LEASE_FAILED,
        LEASE_BLOCKED,
        LEASE_CONTESTED,
        LEASE_STALE,
    }:
        raise MulticomponentGraphSchedulingError(
            "invalid Specialist postdispatch settlement"
        )
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("schema_version") != MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION:
        raise MulticomponentGraphSchedulingError("Specialist settlement requires scheduler V3")
    inputs = _mapping(action_inputs)
    index = _lease_index(scheduler, str(inputs.get("lease_id") or ""))
    lease = _mapping(scheduler["lease_history"][index])
    work = _mapping(lease.get("work"))
    if (
        lease.get("status") != LEASE_EXECUTION_STARTED
        or work.get("work_kind") != WORK_KIND_SPECIALIST_CAPABILITY
    ):
        raise MulticomponentGraphSchedulingError(
            "Specialist lease is not awaiting deterministic settlement"
        )
    for key in (
        "batch_id",
        "batch_digest",
        "batch_index",
        "lease_digest",
        "work_id",
        "work_digest",
        "logical_evaluation_key",
        "input_packet_digest",
        "capability_id",
        "capability_version",
    ):
        expected = (
            lease.get(key)
            if key in {"batch_id", "batch_digest", "batch_index", "lease_digest"}
            else work.get(key)
        )
        if inputs.get(key) != expected:
            raise MulticomponentGraphSchedulingError(
                "Specialist action settlement binding mismatch"
            )
    current = work_is_current(state, work)
    if settlement in {LEASE_COMPLETED, LEASE_BLOCKED, LEASE_CONTESTED, LEASE_FAILED} and not current:
        raise MulticomponentGraphSchedulingError(
            "stale Specialist work cannot settle as current"
        )
    if settlement == LEASE_STALE and current:
        raise MulticomponentGraphSchedulingError(
            "current Specialist work cannot settle as stale"
        )
    lease["status"] = settlement
    lease["settlement_reason"] = inputs.get("failure_kind")
    scheduler["lease_history"][index] = lease
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["transition_history"].append(
        {
            "transition": settlement,
            "scheduler_revision": scheduler["scheduler_revision"],
            "lease_id": lease.get("lease_id"),
            "work_id": work.get("work_id"),
            "work_kind": WORK_KIND_SPECIALIST_CAPABILITY,
            "capability_id": work.get("capability_id"),
        }
    )
    batch_index = _batch_index(scheduler, str(inputs.get("batch_id") or ""))
    batch = _mapping(scheduler["batch_history"][batch_index])
    summary = _mapping(batch.get("safe_accounting_summary"))
    summary["deterministic_execution_started_count"] = 1
    summary["deterministic_execution_completed_count"] = 1
    summary["settlement"] = settlement
    batch["safe_accounting_summary"] = summary
    batch["status"] = "settled"
    batch["terminal_settlement_summary"] = {
        "lease_count": 1,
        "ordered_settlements": [settlement],
        "all_leases_terminal": True,
    }
    scheduler["batch_history"][batch_index] = batch
    required = _mapping(work.get("specialist_proposal_ref")).get("posture") == "required"
    if required and settlement != LEASE_COMPLETED:
        scheduler["failed_required_work_ref"] = {
            **_work_ref(work),
            "settlement": settlement,
        }
        scheduler["status"] = "blocked_required_specialist_work"
        scheduler["terminal_posture"] = "blocked_required_specialist_work"
    return _refresh_scheduler(scheduler)


def validate_role_lease_settlement(
    *,
    state: Any,
    action_id: str,
    action_inputs: Mapping[str, Any],
    observation_failed: bool,
    observation_payload: Mapping[str, Any],
) -> None:
    """Validate a role settlement before RunKernel marks its action reduced."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    inputs = _mapping(action_inputs)
    index = _lease_index(scheduler, str(inputs.get("lease_id") or ""))
    lease = _mapping(scheduler["lease_history"][index])
    work = _mapping(lease.get("work"))
    if (
        lease.get("status") != LEASE_EXECUTION_STARTED
        or _mapping(lease.get("role_action_ref")).get("action_id") != action_id
    ):
        raise MulticomponentGraphSchedulingError(
            "role settlement requires the exact active spent lease"
        )
    for key in (
        "batch_id",
        "batch_digest",
        "batch_index",
        "lease_digest",
        "work_id",
        "work_digest",
        "role",
        "logical_evaluation_key",
        "input_packet_digest",
    ):
        expected = (
            lease.get(key)
            if key in {"batch_id", "batch_digest", "batch_index", "lease_digest"}
            else work.get(key)
        )
        if inputs.get(key) != expected:
            raise MulticomponentGraphSchedulingError(
                "role action and active lease settlement binding disagree"
            )
    payload = _mapping(observation_payload)
    if observation_failed:
        settlement = str(payload.get("lease_settlement") or LEASE_FAILED)
        if settlement not in {LEASE_FAILED, LEASE_STALE}:
            raise MulticomponentGraphSchedulingError(
                "role failure names an invalid lease settlement"
            )
        current = work_is_current(state, work)
        if settlement == LEASE_STALE and current:
            raise MulticomponentGraphSchedulingError(
                "current work cannot claim stale-result settlement"
            )
        return
    artifact = validate_multicomponent_role_artifact(
        _mapping(payload.get("semantic_role_artifact")),
        expected_role=str(inputs.get("role") or ""),
    )
    for key in (
        "run_id",
        "request_id",
        "input_packet_digest",
        "logical_evaluation_key",
        "batch_id",
        "batch_digest",
        "batch_index",
        "descriptor_digest",
        "lease_id",
        "lease_digest",
        "work_id",
        "work_digest",
        "grant_action_ref",
        "dispatch_action_ref",
        "accepted_contract_ref",
        "graph_ref",
        "target_kind",
        "component_id",
        "synthesis_key",
        "node_ref",
        "recovery_authorization_ref",
        "contract_amendment_admission_ref",
        "contract_amendment_application_ref",
        "selective_closure_ref",
        "scheduler_revision_at_grant",
        "output_schema_variant",
    ):
        expected = (
            state.run_id
            if key == "run_id"
            else state.request_id
            if key == "request_id"
            else inputs.get(key)
        )
        if artifact.get(key) != expected:
            raise MulticomponentGraphSchedulingError(
                "semantic artifact and active lease lineage disagree"
            )
    if _mapping(artifact.get("authorized_action_ref")).get("action_id") != action_id:
        raise MulticomponentGraphSchedulingError(
            "semantic artifact names a different role action"
        )
    if not work_is_current(state, work):
        raise MulticomponentGraphSchedulingError(
            "stale semantic work cannot claim successful completion"
        )


def cancel_lease(*, state: Any, lease_id: str, reason: str) -> dict[str, Any]:
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    index = _lease_index(scheduler, lease_id)
    lease = _mapping(scheduler["lease_history"][index])
    if lease.get("status") != LEASE_GRANTED:
        raise MulticomponentGraphSchedulingError(
            "only a granted reservation may be returned"
        )
    lease["status"] = LEASE_CANCELLED
    lease["settlement_reason"] = str(reason or "predispatch_cancellation")[:160]
    scheduler["lease_history"][index] = lease
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    work = _mapping(lease.get("work"))
    if work.get("work_kind") == WORK_KIND_SPECIALIST_CAPABILITY:
        pool = _mapping(scheduler.get("specialist_compatibility_pool"))
        pool["specialist_remaining"] = int(pool["specialist_remaining"]) + 1
        pool["specialist_returned"] = int(pool.get("specialist_returned") or 0) + 1
        scheduler["specialist_compatibility_pool"] = pool
    else:
        envelope = _mapping(scheduler.get("compatibility_envelope"))
        envelope["remaining_units"] = int(envelope["remaining_units"]) + 1
        envelope["returned_units"] = int(envelope.get("returned_units") or 0) + 1
        scheduler["compatibility_envelope"] = envelope
    scheduler["transition_history"].append(
        {
            "transition": LEASE_CANCELLED,
            "scheduler_revision": scheduler["scheduler_revision"],
            "lease_id": lease_id,
            "work_id": _mapping(lease.get("work")).get("work_id"),
        }
    )
    return _refresh_scheduler(scheduler)


_AUTHORITY_TRANSITION_CONTRACT = "contract_amendment_applied"
_AUTHORITY_TRANSITION_GRAPH = "component_work_graph_reduced"
_AUTHORITY_TRANSITION_CLOSURE = "selective_closure_installed"
_AUTHORITY_TRANSITION_RECOVERY_CONTEXT = "recovery_scheduler_context_registered"
_AUTHORITY_TRANSITIONS = frozenset(
    {
        _AUTHORITY_TRANSITION_CONTRACT,
        _AUTHORITY_TRANSITION_GRAPH,
        _AUTHORITY_TRANSITION_CLOSURE,
        _AUTHORITY_TRANSITION_RECOVERY_CONTEXT,
    }
)


def _canonical_authority_ref(state: Any, transition: str) -> dict[str, Any]:
    if transition == _AUTHORITY_TRANSITION_CONTRACT:
        return {"contract_ref": _contract_ref(state.current_answer_contract)}
    if transition == _AUTHORITY_TRANSITION_GRAPH:
        return {
            "graph_ref": _graph_ref(
                _mapping(
                    state.projections.get(
                        "multicomponent_component_work_graph_v1"
                    )
                )
            )
        }
    if transition == _AUTHORITY_TRANSITION_CLOSURE:
        closure = _mapping(
            state.projections.get(
                "multicomponent_selective_recomputation_closure"
            )
        )
        return {
            "selective_closure_ref": {
                "closure_id": closure.get("closure_id"),
                "closure_digest": closure.get("closure_digest"),
            }
        }
    if transition == _AUTHORITY_TRANSITION_RECOVERY_CONTEXT:
        context = _mapping(state.multicomponent_scheduler_context)
        packets = _mapping(context.get("component_analyst_input_packets"))
        recoveries = _mapping(context.get("recovery_bindings"))
        return {
            "component_input_packet_digests": {
                str(key): safe_packet_digest(_mapping(value))
                for key, value in sorted(packets.items())
            },
            "recovery_component_ids": sorted(str(key) for key in recoveries),
        }
    raise MulticomponentGraphSchedulingError(
        "scheduler authority transition is not an internal canonical transition"
    )


def _settle_for_canonical_authority_transition(
    *, state: Any, transition: str
) -> dict[str, Any]:
    """Settle exact stale work against a reducer-constructed candidate state."""

    if transition not in _AUTHORITY_TRANSITIONS:
        raise MulticomponentGraphSchedulingError(
            "scheduler authority transition is not an internal canonical transition"
        )
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("status") != "active":
        return scheduler
    active = [
        (index, _mapping(item))
        for index, item in enumerate(scheduler.get("lease_history") or ())
        if _mapping(item).get("status") in _ACTIVE_STATUSES
    ]
    affected = [
        (index, lease)
        for index, lease in active
        if not work_is_current(state, _mapping(lease.get("work")))
    ]
    granted_affected = [item for item in affected if item[1].get("status") == LEASE_GRANTED]
    if granted_affected and scheduler.get("schema_version") in (
        _BATCH_SCHEDULER_VERSIONS
    ) and all(lease.get("batch_id") for _, lease in active):
        batch_ids = {str(lease.get("batch_id") or "") for _, lease in active}
        if len(batch_ids) != 1 or any(
            lease.get("status") != LEASE_GRANTED for _, lease in active
        ):
            raise MulticomponentGraphSchedulingError(
                "predispatch authority change cannot partially cancel a V2 batch"
            )
        scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
        for index, lease in active:
            lease["status"] = LEASE_CANCELLED
            lease["settlement_reason"] = transition
            scheduler["lease_history"][index] = lease
        if all(
            _mapping(lease.get("work")).get("work_kind")
            == WORK_KIND_SPECIALIST_CAPABILITY
            for _, lease in active
        ):
            pool = _mapping(scheduler.get("specialist_compatibility_pool"))
            pool["specialist_remaining"] = int(pool["specialist_remaining"]) + len(active)
            pool["specialist_returned"] = int(pool.get("specialist_returned") or 0) + len(active)
            scheduler["specialist_compatibility_pool"] = pool
        else:
            envelope = _mapping(scheduler.get("compatibility_envelope"))
            envelope["remaining_units"] = int(envelope["remaining_units"]) + len(active)
            envelope["returned_units"] = int(envelope.get("returned_units") or 0) + len(active)
            scheduler["compatibility_envelope"] = envelope
        batch_id = next(iter(batch_ids))
        batch_index = _batch_index(scheduler, batch_id)
        batch = _mapping(scheduler["batch_history"][batch_index])
        batch["status"] = LEASE_CANCELLED
        batch["terminal_settlement_summary"] = {
            "settlement": LEASE_CANCELLED,
            "lease_count": len(active),
            "authority_change_settlement": True,
        }
        scheduler["batch_history"][batch_index] = batch
        scheduler["transition_history"].append(
            {
                "transition": LEASE_CANCELLED,
                "scheduler_revision": scheduler["scheduler_revision"],
                "batch_id": batch_id,
                "ordered_lease_ids": [lease.get("lease_id") for _, lease in active],
                "authority_change_settlement": True,
            }
        )
    else:
        for index, lease in affected:
            scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
            work = _mapping(lease.get("work"))
            if lease.get("status") == LEASE_GRANTED:
                lease["status"] = LEASE_CANCELLED
                if work.get("work_kind") == WORK_KIND_SPECIALIST_CAPABILITY:
                    pool = _mapping(scheduler.get("specialist_compatibility_pool"))
                    pool["specialist_remaining"] = int(pool["specialist_remaining"]) + 1
                    pool["specialist_returned"] = int(pool.get("specialist_returned") or 0) + 1
                    scheduler["specialist_compatibility_pool"] = pool
                else:
                    envelope = _mapping(scheduler.get("compatibility_envelope"))
                    envelope["remaining_units"] = int(envelope["remaining_units"]) + 1
                    envelope["returned_units"] = int(envelope.get("returned_units") or 0) + 1
                    scheduler["compatibility_envelope"] = envelope
                settlement = LEASE_CANCELLED
            else:
                lease["status"] = LEASE_STALE
                settlement = LEASE_STALE
                if (
                    scheduler.get("schema_version") in _BATCH_SCHEDULER_VERSIONS
                    and lease.get("batch_id")
                    and work.get("work_kind") != WORK_KIND_SPECIALIST_CAPABILITY
                ):
                    counters = _mapping(scheduler.get("accounting_counters"))
                    counters["stale_result_count"] = int(
                        counters.get("stale_result_count") or 0
                    ) + 1
                    scheduler["accounting_counters"] = counters
            lease["settlement_reason"] = transition
            scheduler["lease_history"][index] = lease
            scheduler["transition_history"].append(
                {
                    "transition": settlement,
                    "scheduler_revision": scheduler["scheduler_revision"],
                    "lease_id": lease.get("lease_id"),
                    "work_id": work.get("work_id"),
                    "authority_change_settlement": True,
                }
            )
        if affected and scheduler.get("schema_version") in _BATCH_SCHEDULER_VERSIONS:
            affected_batch_ids = {
                str(lease.get("batch_id") or "")
                for _, lease in affected
                if lease.get("batch_id")
            }
            for batch_id in affected_batch_ids:
                batch_index = _batch_index(scheduler, batch_id)
                batch = _mapping(scheduler["batch_history"][batch_index])
                batch_leases = [
                    _mapping(
                        scheduler["lease_history"][
                            _lease_index(scheduler, str(_mapping(ref).get("lease_id") or ""))
                        ]
                    )
                    for ref in batch.get("ordered_lease_refs") or ()
                ]
                if all(item.get("status") in _TERMINAL_STATUSES for item in batch_leases):
                    batch["status"] = "settled"
                    batch["terminal_settlement_summary"] = {
                        "lease_count": len(batch_leases),
                        "ordered_settlements": [item.get("status") for item in batch_leases],
                        "all_leases_terminal": True,
                    }
                scheduler["batch_history"][batch_index] = batch
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["transition_history"].append(
        {
            "transition": transition,
            "scheduler_revision": scheduler["scheduler_revision"],
            "authority_ref": _canonical_authority_ref(state, transition),
            "affected_active_lease": bool(affected),
            "affected_active_lease_count": len(affected),
        }
    )
    scheduler["last_ready_work"] = []
    return _refresh_scheduler(scheduler)


def complete_scheduler(state: Any) -> dict[str, Any]:
    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("status") != "active":
        return scheduler
    active = [
        lease
        for lease in scheduler["lease_history"]
        if lease["status"] in _ACTIVE_STATUSES
    ]
    if active:
        raise MulticomponentGraphSchedulingError(
            "scheduler cannot complete while a semantic lease is active"
        )
    if derive_ready_work(state, allow_active_lease=True):
        raise MulticomponentGraphSchedulingError(
            "scheduler cannot complete while semantic work remains ready"
        )
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["status"] = "completed"
    scheduler["last_ready_work"] = []
    scheduler["transition_history"].append(
        {
            "transition": "scheduler_completed",
            "scheduler_revision": scheduler["scheduler_revision"],
        }
    )
    return _refresh_scheduler(scheduler)


def scheduler_trace_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the already-sanitized canonical scheduler projection."""

    return validate_scheduler_state(state)


__all__ = [
    "EXECUTOR_REGISTERED_DETERMINISTIC",
    "LEASE_BLOCKED",
    "LEASE_CANCELLED",
    "LEASE_COMPLETED",
    "LEASE_CONTESTED",
    "LEASE_DENIED_EXHAUSTED",
    "LEASE_EXECUTION_STARTED",
    "LEASE_FAILED",
    "LEASE_GRANTED",
    "LEASE_STALE",
    "MULTICOMPONENT_LEASE_SCHEMA_VERSION",
    "MULTICOMPONENT_LEASE_V2_SCHEMA_VERSION",
    "MULTICOMPONENT_BATCH_ACCOUNTING_SUMMARY_SCHEMA_VERSION",
    "MULTICOMPONENT_BATCH_LEASE_GROUP_SCHEMA_VERSION",
    "MULTICOMPONENT_BATCH_SCHEMA_VERSION",
    "MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION",
    "MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION",
    "MULTICOMPONENT_PREPARED_TRANSPORT_CALL_SCHEMA_VERSION",
    "MULTICOMPONENT_ROLE_CALL_LIMITS",
    "MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_OWNER",
    "MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_STAGE",
    "MULTICOMPONENT_WORK_SCHEMA_VERSION",
    "MulticomponentGraphSchedulingError",
    "RESOURCE_DETERMINISTIC_SPECIALIST",
    "WORK_KIND_SPECIALIST_CAPABILITY",
    "block_required_specialist_reconstruction_failure",
    "block_required_specialist_proposal",
    "cancel_batch",
    "cancel_lease",
    "classify_work_parallelism",
    "complete_scheduler",
    "derive_multicomponent_compatibility_envelope",
    "derive_multicomponent_transport_profile",
    "derive_ready_work",
    "derive_ready_batch_work",
    "dispatch_lease",
    "dispatch_batch",
    "grant_next_lease",
    "grant_next_batch",
    "initialize_scheduler_state",
    "initialize_scheduler_v2_state",
    "initialize_scheduler_v3_state",
    "reconstruct_specialist_bounded_input",
    "reconstruct_specialist_input_for_work",
    "scheduler_trace_projection",
    "settle_role_lease",
    "settle_specialist_lease",
    "validate_scheduler_state",
    "validate_role_lease_settlement",
    "work_is_current",
]
