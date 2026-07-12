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
MULTICOMPONENT_LEASE_SCHEMA_VERSION = "multicomponent_semantic_work_lease_v1"
MULTICOMPONENT_WORK_SCHEMA_VERSION = "multicomponent_semantic_work_v1"
MULTICOMPONENT_BATCH_SCHEMA_VERSION = "multicomponent_semantic_work_batch_v1"
MULTICOMPONENT_BATCH_LEASE_GROUP_SCHEMA_VERSION = (
    "multicomponent_semantic_batch_lease_group_v1"
)
MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION = (
    "multicomponent_private_child_action_descriptor_v1"
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

_RESERVED_STATUSES = frozenset({LEASE_GRANTED})
_SPENT_STATUSES = frozenset(
    {LEASE_EXECUTION_STARTED, LEASE_COMPLETED, LEASE_FAILED, LEASE_STALE}
)
_ACTIVE_STATUSES = frozenset({LEASE_GRANTED, LEASE_EXECUTION_STARTED})
_TERMINAL_STATUSES = frozenset(
    {
        LEASE_COMPLETED,
        LEASE_DENIED_EXHAUSTED,
        LEASE_CANCELLED,
        LEASE_FAILED,
        LEASE_STALE,
    }
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
    reserved = sum(1 for lease in leases if lease.get("status") in _RESERVED_STATUSES)
    spent = sum(1 for lease in leases if lease.get("status") in _SPENT_STATUSES)
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
    for lease in leases:
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
    elif schema_version == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION:
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
        in {"completed", "blocked_exhausted", "blocked_required_work_failed"}
        and refreshed.get("active_physical_lease_count") != 0
    ):
        raise MulticomponentGraphSchedulingError(
            "terminal scheduler state cannot contain an active semantic lease"
        )
    return refreshed


def _completed_artifact(state: Any, role: str, evaluation_key: str) -> dict[str, Any]:
    raw = _mapping(
        state.projections.get(f"multicomponent_role:{role}:{evaluation_key}")
    )
    if not raw:
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
    digest = _digest(core)
    return {
        **core,
        "work_id": f"multicomponent-work:{digest[:24]}",
        "work_digest": digest,
    }


def derive_ready_work(state: Any, *, allow_active_lease: bool = False) -> list[dict[str, Any]]:
    """Incrementally derive current semantic work from canonical owners."""

    scheduler = validate_scheduler_state(
        _mapping(state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    )
    if scheduler.get("status") != "active":
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
    component_refs = [
        _mapping(item) for item in contract.get("accepted_answer_component_refs") or ()
    ]
    admissions = _component_admissions(state)
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
        dprime = _completed_artifact(state, ROLE_COMPONENT_DPRIME, component_id)
        if not dprime:
            from core.multicomponent_component_admission import (
                component_dprime_input_packet,
            )

            dprime_input = component_dprime_input_packet(
                analyst_artifact=analyst,
                analyst_input_packet=analyst_input,
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
        try:
            packet = synthesis_dprime_input_packet(graph, synthesis_key=synthesis_key)
        except ValueError:
            # A proposed downstream node is not actionable until its exact
            # upstream synthesis authority has been admitted.
            continue
        if closure:
            key = f"{synthesis_key}:selective:graph-revision:{graph['graph_revision']}"
        elif int(graph.get("recovery_rounds") or 0):
            key = f"{synthesis_key}:graph-revision:{graph['graph_revision']}"
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
    if (
        graph.get("scrutineer_required") is True
        and not scrutiny_done
        and "proposed" not in statuses
    ):
        if closure:
            key = f"full-case:selective:graph-revision:{graph['graph_revision']}"
        elif int(graph.get("recovery_rounds") or 0):
            key = f"full-case:graph-revision:{graph['graph_revision']}"
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
    def semantic_identity(value: Mapping[str, Any]) -> dict[str, Any]:
        identity = deepcopy(dict(value))
        for key in ("work_id", "work_digest", "scheduler_revision"):
            identity.pop(key, None)
        return identity
    try:
        return any(
            semantic_identity(candidate) == semantic_identity(target)
            for candidate in derive_ready_work(state, allow_active_lease=True)
        )
    except MulticomponentGraphSchedulingError:
        return False


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
        "lease_digest",
        "work_id",
        "work_digest",
        "role",
        "logical_evaluation_key",
        "input_packet_digest",
    ):
        expected = lease.get(key) if key == "lease_digest" else work.get(key)
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
    if settlement in {LEASE_FAILED, LEASE_STALE}:
        scheduler["status"] = "blocked_required_work_failed"
        scheduler["failed_required_work_ref"] = {
            "work_id": work.get("work_id"),
            "work_digest": work.get("work_digest"),
            "role": work.get("role"),
            "settlement": settlement,
        }
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
        "lease_digest",
        "work_id",
        "work_digest",
        "role",
        "logical_evaluation_key",
        "input_packet_digest",
    ):
        expected = lease.get(key) if key == "lease_digest" else work.get(key)
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
    affected = False
    if active:
        index, lease = active[0]
        work = _mapping(lease.get("work"))
        affected = not work_is_current(state, work)
    if active and affected:
        scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
        if lease.get("status") == LEASE_GRANTED:
            lease["status"] = LEASE_CANCELLED
            envelope = _mapping(scheduler.get("compatibility_envelope"))
            envelope["remaining_units"] = int(envelope["remaining_units"]) + 1
            envelope["returned_units"] = int(envelope.get("returned_units") or 0) + 1
            scheduler["compatibility_envelope"] = envelope
            settlement = LEASE_CANCELLED
        else:
            lease["status"] = LEASE_STALE
            settlement = LEASE_STALE
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
    scheduler["scheduler_revision"] = int(scheduler["scheduler_revision"]) + 1
    scheduler["transition_history"].append(
        {
            "transition": transition,
            "scheduler_revision": scheduler["scheduler_revision"],
            "authority_ref": _canonical_authority_ref(state, transition),
            "affected_active_lease": affected,
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
    "LEASE_CANCELLED",
    "LEASE_COMPLETED",
    "LEASE_DENIED_EXHAUSTED",
    "LEASE_EXECUTION_STARTED",
    "LEASE_FAILED",
    "LEASE_GRANTED",
    "LEASE_STALE",
    "MULTICOMPONENT_LEASE_SCHEMA_VERSION",
    "MULTICOMPONENT_BATCH_ACCOUNTING_SUMMARY_SCHEMA_VERSION",
    "MULTICOMPONENT_BATCH_LEASE_GROUP_SCHEMA_VERSION",
    "MULTICOMPONENT_BATCH_SCHEMA_VERSION",
    "MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION",
    "MULTICOMPONENT_PREPARED_TRANSPORT_CALL_SCHEMA_VERSION",
    "MULTICOMPONENT_ROLE_CALL_LIMITS",
    "MULTICOMPONENT_SAFE_WORKER_RESULT_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_OWNER",
    "MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION",
    "MULTICOMPONENT_SCHEDULER_STAGE",
    "MULTICOMPONENT_WORK_SCHEMA_VERSION",
    "MulticomponentGraphSchedulingError",
    "cancel_lease",
    "complete_scheduler",
    "derive_multicomponent_compatibility_envelope",
    "derive_multicomponent_transport_profile",
    "derive_ready_work",
    "dispatch_lease",
    "grant_next_lease",
    "initialize_scheduler_state",
    "initialize_scheduler_v2_state",
    "scheduler_trace_projection",
    "settle_role_lease",
    "validate_scheduler_state",
    "validate_role_lease_settlement",
    "work_is_current",
]
