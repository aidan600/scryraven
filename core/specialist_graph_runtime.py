"""Generic, closed-by-default Specialist graph work contracts.

This module owns bounded Specialist proposals, capability descriptors, policy,
work nodes, and result artifacts.  It deliberately owns no scheduler,
admission, provider/model transport, retrieval, persistence, or answer path.
Adapters are held only by ``SpecialistCapabilityRegistry`` and are never
included in retained RunKernel state.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

SPECIALIST_WORK_PLANE_STAGE = "specialist_work_plane"
SPECIALIST_WORK_PLANE_OWNER = "RunKernel.SpecialistWorkPlane"
SPECIALIST_NEED_SCHEMA_VERSION = "specialist_need_proposal_v1"
SPECIALIST_WORK_NODE_SCHEMA_VERSION = "specialist_work_node_v1"
SPECIALIST_RESULT_SCHEMA_VERSION = "specialist_result_artifact_v1"
SPECIALIST_CAPABILITY_SCHEMA_VERSION = "specialist_capability_spec_v1"
SPECIALIST_REGISTRY_SCHEMA_VERSION = "specialist_capability_registry_v1"
SPECIALIST_POLICY_SCHEMA_VERSION = "specialist_execution_policy_v1"
SPECIALIST_STATE_SCHEMA_VERSION = "specialist_work_plane_state_v1"

WORK_KIND_SPECIALIST = "specialist_capability"
RESOURCE_DETERMINISTIC_SPECIALIST = "deterministic_specialist"
EXECUTOR_REGISTERED_DETERMINISTIC = "registered_deterministic_capability"

PROPOSAL_PROPOSED = "proposed"
PROPOSAL_ACCEPTED = "accepted"
PROPOSAL_REJECTED = "rejected"
PROPOSAL_UNSUPPORTED_TARGET = "unsupported_target"
PROPOSAL_DENIED_POLICY = "denied_by_policy"

VALIDATOR_PENDING = "pending_validator_consumption"
VALIDATOR_COMPONENT = "consumed_by_component_dprime"
VALIDATOR_SYNTHESIS = "consumed_by_synthesis_dprime"
VALIDATOR_REJECTED = "rejected_by_validator"
VALIDATOR_CONTESTED = "contested_by_validator"
VALIDATOR_TERMINAL = "terminal"

EXECUTION_COMPLETED = "completed"
EXECUTION_FAILED = "failed_spent"
EXECUTION_BLOCKED = "blocked_spent"
EXECUTION_CONTESTED = "contested_spent"
EXECUTION_STALE = "stale_rejected_spent"

_TARGET_KINDS = frozenset({"component", "synthesis", "edge", "subgraph", "graph", "whole_case"})
_POSTURES = frozenset({"required", "optional"})
_EXECUTION_POSTURES = frozenset(
    {EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_BLOCKED, EXECUTION_CONTESTED}
)
_RAW_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "credential",
        "database_row",
        "full_trace",
        "header",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "secret",
        "token",
    }
)


class SpecialistGraphRuntimeError(ValueError):
    """Raised when Specialist state would exceed the generic S0 contract."""


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
    raise SpecialistGraphRuntimeError("Specialist material must be bounded JSON data")


def specialist_digest(value: Any) -> str:
    return sha256(
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return []


def _text(value: Any, *, limit: int, required: bool = False) -> str | None:
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        if required:
            raise SpecialistGraphRuntimeError("required Specialist text is missing")
        return None
    return cleaned[:limit]


def _token(value: Any, *, limit: int = 180, required: bool = False) -> str | None:
    cleaned = _text(value, limit=limit, required=required)
    if cleaned and any(char.isspace() for char in cleaned):
        raise SpecialistGraphRuntimeError("Specialist identity tokens cannot contain whitespace")
    return cleaned


def _text_list(value: Any, *, limit: int = 500) -> tuple[str, ...]:
    result: list[str] = []
    for item in _sequence(value):
        cleaned = _text(item, limit=limit)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return tuple(result)


def _safe_refs(value: Any) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    for item in _sequence(value):
        mapped = _mapping(item)
        if not mapped:
            continue
        _reject_private(mapped, context="Specialist input ref")
        safe = _json_safe(mapped)
        if safe not in refs:
            refs.append(safe)
    return tuple(refs)


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key).strip().casefold())
            keys.update(_collect_keys(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for item in value:
            keys.update(_collect_keys(item))
    return keys


def _reject_private(value: Any, *, context: str) -> None:
    forbidden = _collect_keys(value) & _RAW_PRIVATE_KEYS
    if forbidden:
        raise SpecialistGraphRuntimeError(
            f"{context} contains raw/private material: {', '.join(sorted(forbidden))}"
        )


@dataclass(frozen=True, slots=True)
class SpecialistCapabilitySpec:
    capability_id: str
    version: str
    capability_requirement: str
    supported_target_kinds: tuple[str, ...]
    input_schema_ref: str
    output_schema_ref: str
    adapter: Callable[[Mapping[str, Any]], Mapping[str, Any]] = field(
        repr=False, compare=False
    )
    capability_class: str = "generic_deterministic_specialist"
    cost_class: str = "zero_model_cost"
    deterministic: bool = True
    side_effect_free: bool = True
    raw_private_requirements: bool = False
    recursion: bool = False
    parallel_execution: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.capability_id,
            self.version,
            self.capability_requirement,
            self.input_schema_ref,
            self.output_schema_ref,
        ):
            _token(value, required=True)
        targets = tuple(dict.fromkeys(str(item) for item in self.supported_target_kinds))
        if not targets or any(item not in {"component", "synthesis"} for item in targets):
            raise SpecialistGraphRuntimeError("S0 capability target kind is unsupported")
        if not callable(self.adapter):
            raise SpecialistGraphRuntimeError("Specialist capability requires an adapter")
        if (
            not self.deterministic
            or not self.side_effect_free
            or self.raw_private_requirements
            or self.recursion
            or self.parallel_execution
        ):
            raise SpecialistGraphRuntimeError("S0 capability must be deterministic and closed")

    def descriptor(self) -> dict[str, Any]:
        core = {
            "schema_version": SPECIALIST_CAPABILITY_SCHEMA_VERSION,
            "capability_id": self.capability_id,
            "version": self.version,
            "capability_requirement": self.capability_requirement,
            "capability_class": self.capability_class,
            "supported_target_kinds": list(self.supported_target_kinds),
            "input_schema_ref": self.input_schema_ref,
            "output_schema_ref": self.output_schema_ref,
            "resource_class": RESOURCE_DETERMINISTIC_SPECIALIST,
            "executor_class": EXECUTOR_REGISTERED_DETERMINISTIC,
            "cost_class": self.cost_class,
            "deterministic": True,
            "side_effect_free": True,
            "model_calls": False,
            "provider_calls": False,
            "search_calls": False,
            "retrieval_calls": False,
            "raw_private_requirements": False,
            "recursion": False,
            "parallel_execution": False,
        }
        return {**core, "descriptor_digest": specialist_digest(core)}


class SpecialistCapabilityRegistry:
    """Immutable descriptor index with adapters kept outside retained state."""

    def __init__(self, specs: Sequence[SpecialistCapabilitySpec] = ()) -> None:
        index: dict[str, SpecialistCapabilitySpec] = {}
        for spec in specs:
            if spec.capability_id in index:
                raise SpecialistGraphRuntimeError("duplicate Specialist capability id")
            index[spec.capability_id] = spec
        self._specs = index

    def projection(self) -> dict[str, Any]:
        descriptors = [
            self._specs[key].descriptor() for key in sorted(self._specs)
        ]
        core = {
            "schema_version": SPECIALIST_REGISTRY_SCHEMA_VERSION,
            "capability_descriptors": descriptors,
            "capability_count": len(descriptors),
            "authorization_authority": False,
            "admission_authority": False,
            "adapters_retained": False,
        }
        return {**core, "registry_digest": specialist_digest(core)}

    def resolve(
        self,
        *,
        requirement: str,
        target_kind: str,
        input_schema_ref: str,
        output_schema_ref: str,
        enabled_capability_ids: Sequence[str],
    ) -> SpecialistCapabilitySpec:
        enabled = set(enabled_capability_ids)
        candidates = [
            spec
            for spec in self._specs.values()
            if spec.capability_id in enabled
            and spec.capability_requirement == requirement
            and target_kind in spec.supported_target_kinds
            and spec.input_schema_ref == input_schema_ref
            and spec.output_schema_ref == output_schema_ref
        ]
        if not candidates:
            raise SpecialistGraphRuntimeError("no enabled compatible Specialist capability")
        return sorted(candidates, key=lambda item: (item.capability_id, item.version))[0]

    def get(self, capability_id: str, version: str) -> SpecialistCapabilitySpec:
        spec = self._specs.get(capability_id)
        if spec is None or spec.version != version:
            raise SpecialistGraphRuntimeError("authorized Specialist capability is unavailable")
        return spec


@dataclass(frozen=True, slots=True)
class SpecialistExecutionPolicy:
    enabled_capability_ids: tuple[str, ...] = ()
    specialist_work_item_limit: int = 0
    parallelism: bool = False
    recursion: bool = False

    def __post_init__(self) -> None:
        if self.specialist_work_item_limit not in {0, 1}:
            raise SpecialistGraphRuntimeError("S0 Specialist limit must be zero or one")
        if self.parallelism or self.recursion:
            raise SpecialistGraphRuntimeError("S0 Specialist parallelism/recursion is closed")

    def projection(self) -> dict[str, Any]:
        core = {
            "schema_version": SPECIALIST_POLICY_SCHEMA_VERSION,
            "enabled_capability_ids": list(dict.fromkeys(self.enabled_capability_ids)),
            "specialist_work_item_limit": self.specialist_work_item_limit,
            "parallelism": False,
            "recursion": False,
            "serial_width": 1,
            "main_thread_only": True,
        }
        return {**core, "execution_policy_digest": specialist_digest(core)}


def closed_specialist_registry() -> SpecialistCapabilityRegistry:
    return SpecialistCapabilityRegistry()


def closed_specialist_execution_policy() -> SpecialistExecutionPolicy:
    return SpecialistExecutionPolicy()


def normalize_specialist_need_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize proposal-only role output without creating authority ids."""

    raw = _mapping(value)
    _reject_private(raw, context="Specialist proposal")
    target = _mapping(raw.get("target"))
    target_kind = str(target.get("target_kind") or raw.get("target_kind") or "")
    target_key = _token(target.get("target_key") or raw.get("target_key"), required=True)
    posture = str(raw.get("posture") or "optional").strip().casefold()
    if target_kind not in _TARGET_KINDS or posture not in _POSTURES:
        raise SpecialistGraphRuntimeError("Specialist proposal target or posture is invalid")
    if int(raw.get("recursion_depth") or 0) != 0 or raw.get("specialist_parent_ref"):
        raise SpecialistGraphRuntimeError("Specialist recursion is not authorized")
    normalized = {
        "schema_version": SPECIALIST_NEED_SCHEMA_VERSION,
        "local_need_id": _token(raw.get("local_need_id"), required=True),
        "capability_requirement": _token(
            raw.get("capability_requirement"), required=True
        ),
        "candidate_capability_hint": _token(raw.get("candidate_capability_hint")),
        "bounded_question": _text(raw.get("bounded_question"), limit=800, required=True),
        "target": {"target_kind": target_kind, "target_key": target_key},
        "posture": posture,
        "input_schema_ref": _token(raw.get("input_schema_ref"), required=True),
        "expected_output_schema_ref": _token(
            raw.get("expected_output_schema_ref"), required=True
        ),
        "input_artifact_refs": list(_safe_refs(raw.get("input_artifact_refs"))),
        "assumptions": list(_text_list(raw.get("assumptions"))),
        "caveats": list(_text_list(raw.get("caveats"))),
        "nonclaims": list(_text_list(raw.get("nonclaims"))),
        "advisory_budget_posture": _text(
            raw.get("advisory_budget_posture"), limit=240
        ),
        "recursion_depth": 0,
        "specialist_parent_ref": None,
        "canonical_identity_claimed": False,
        "lease_authority_claimed": False,
        "dispatch_authority_claimed": False,
        "admission_authority_claimed": False,
    }
    return _json_safe(normalized)


def bind_specialist_need_proposal(
    *,
    run_id: str,
    request_id: str,
    origin_role: str,
    origin_action_ref: Mapping[str, Any],
    origin_artifact_ref: Mapping[str, Any],
    proposal: Mapping[str, Any],
    canonical_target_ref: Mapping[str, Any],
    accepted_contract_ref: Mapping[str, Any],
    graph_ref: Mapping[str, Any] | None,
    registry: SpecialistCapabilityRegistry,
    policy: SpecialistExecutionPolicy,
    scrutineer_leaf_target_authorized: bool = False,
) -> dict[str, Any]:
    """Bind a model-visible proposal to exact current authority and policy."""

    normalized = normalize_specialist_need_proposal(proposal)
    target = _mapping(normalized["target"])
    canonical_target = _mapping(canonical_target_ref)
    target_matches = (
        target.get("target_kind") == canonical_target.get("target_kind")
        and target.get("target_key") == canonical_target.get("target_key")
    )
    proposal_authority = PROPOSAL_PROPOSED
    rejection_reason: str | None = None
    capability_descriptor: dict[str, Any] = {}
    if not target_matches:
        proposal_authority = PROPOSAL_UNSUPPORTED_TARGET
        rejection_reason = "proposal_target_does_not_match_canonical_origin_target"
    elif origin_role == "scrutineer" and not scrutineer_leaf_target_authorized:
        proposal_authority = PROPOSAL_UNSUPPORTED_TARGET
        rejection_reason = "not_authorized_s0_target_requires_graph_invalidation"
    elif policy.specialist_work_item_limit == 0 or not policy.enabled_capability_ids:
        proposal_authority = PROPOSAL_DENIED_POLICY
        rejection_reason = "specialist_execution_closed_by_policy"
    else:
        try:
            spec = registry.resolve(
                requirement=str(normalized["capability_requirement"]),
                target_kind=str(target["target_kind"]),
                input_schema_ref=str(normalized["input_schema_ref"]),
                output_schema_ref=str(normalized["expected_output_schema_ref"]),
                enabled_capability_ids=policy.enabled_capability_ids,
            )
        except SpecialistGraphRuntimeError:
            proposal_authority = PROPOSAL_REJECTED
            rejection_reason = "unknown_or_incompatible_specialist_capability"
        else:
            proposal_authority = PROPOSAL_ACCEPTED
            capability_descriptor = spec.descriptor()
    core = {
        **normalized,
        "run_id": _token(run_id, required=True),
        "request_id": _token(request_id, required=True),
        "origin_role": _token(origin_role, required=True),
        "origin_action_ref": _json_safe(_mapping(origin_action_ref)),
        "origin_artifact_ref": _json_safe(_mapping(origin_artifact_ref)),
        "canonical_target_ref": _json_safe(canonical_target),
        "accepted_contract_ref": _json_safe(_mapping(accepted_contract_ref)),
        "graph_ref": _json_safe(_mapping(graph_ref)),
        "capability_descriptor": capability_descriptor,
        "registry_digest": registry.projection()["registry_digest"],
        "execution_policy_digest": policy.projection()["execution_policy_digest"],
        "proposal_authority": proposal_authority,
        "rejection_reason": rejection_reason,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "proposal_id": f"specialist-proposal:{digest[:24]}",
        "proposal_digest": digest,
    }


def proposal_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(value)
    return {
        "proposal_id": proposal.get("proposal_id"),
        "proposal_digest": proposal.get("proposal_digest"),
        "proposal_authority": proposal.get("proposal_authority"),
        "posture": proposal.get("posture"),
        "canonical_target_ref": deepcopy(proposal.get("canonical_target_ref") or {}),
    }


def validate_bound_specialist_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    proposal = deepcopy(dict(value))
    declared_id = proposal.pop("proposal_id", None)
    declared_digest = proposal.pop("proposal_digest", None)
    digest = specialist_digest(proposal)
    if (
        declared_digest != digest
        or declared_id != f"specialist-proposal:{digest[:24]}"
        or proposal.get("proposal_authority")
        not in {
            PROPOSAL_ACCEPTED,
            PROPOSAL_REJECTED,
            PROPOSAL_UNSUPPORTED_TARGET,
            PROPOSAL_DENIED_POLICY,
        }
    ):
        raise SpecialistGraphRuntimeError("bound Specialist proposal is invalid")
    _reject_private(proposal, context="bound Specialist proposal")
    return {**proposal, "proposal_id": declared_id, "proposal_digest": declared_digest}


def build_specialist_work_node(
    *, proposal: Mapping[str, Any], bounded_inputs: Mapping[str, Any]
) -> dict[str, Any]:
    bound = _mapping(proposal)
    if bound.get("proposal_authority") != PROPOSAL_ACCEPTED:
        raise SpecialistGraphRuntimeError("only an accepted Specialist proposal can become work")
    descriptor = _mapping(bound.get("capability_descriptor"))
    inputs = _json_safe(_mapping(bounded_inputs))
    _reject_private(inputs, context="Specialist bounded inputs")
    core = {
        "schema_version": SPECIALIST_WORK_NODE_SCHEMA_VERSION,
        "run_id": bound.get("run_id"),
        "request_id": bound.get("request_id"),
        "proposal_ref": proposal_ref(bound),
        "origin_action_ref": deepcopy(bound.get("origin_action_ref") or {}),
        "origin_artifact_ref": deepcopy(bound.get("origin_artifact_ref") or {}),
        "canonical_target_ref": deepcopy(bound.get("canonical_target_ref") or {}),
        "target_revision": _mapping(bound.get("canonical_target_ref")).get("target_revision"),
        "accepted_contract_ref": deepcopy(bound.get("accepted_contract_ref") or {}),
        "graph_ref": deepcopy(bound.get("graph_ref") or {}),
        "capability_id": descriptor.get("capability_id"),
        "capability_version": descriptor.get("version"),
        "capability_descriptor_digest": descriptor.get("descriptor_digest"),
        "bounded_inputs": inputs,
        "input_digest": specialist_digest(inputs),
        "input_schema_ref": descriptor.get("input_schema_ref"),
        "output_schema_ref": descriptor.get("output_schema_ref"),
        "resource_class": RESOURCE_DETERMINISTIC_SPECIALIST,
        "executor_class": EXECUTOR_REGISTERED_DETERMINISTIC,
        "registry_digest": bound.get("registry_digest"),
        "execution_policy_digest": bound.get("execution_policy_digest"),
        "serial_execution": True,
        "recursion_depth": 0,
        "specialist_parent_ref": None,
        "current": True,
        "stale": False,
        "execution_terminal_posture": None,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "node_id": f"specialist-work:{digest[:24]}",
        "node_revision": 1,
        "node_digest": digest,
    }


def specialist_work_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    node = _mapping(value)
    return {
        "node_id": node.get("node_id"),
        "node_revision": node.get("node_revision"),
        "node_digest": node.get("node_digest"),
        "canonical_target_ref": deepcopy(node.get("canonical_target_ref") or {}),
        "capability_id": node.get("capability_id"),
        "capability_version": node.get("capability_version"),
    }


def validate_specialist_work_node(value: Mapping[str, Any]) -> dict[str, Any]:
    node = deepcopy(dict(value))
    declared_id = node.pop("node_id", None)
    declared_revision = node.pop("node_revision", None)
    declared_digest = node.pop("node_digest", None)
    digest = specialist_digest(node)
    if (
        node.get("schema_version") != SPECIALIST_WORK_NODE_SCHEMA_VERSION
        or declared_revision not in {1, 2}
        or declared_digest != digest
        or declared_id != f"specialist-work:{digest[:24]}"
        or node.get("serial_execution") is not True
        or node.get("recursion_depth") != 0
        or node.get("current") is not True
        or node.get("stale") is not False
        or (
            declared_revision == 2
            and any(
                not _mapping(node.get(key))
                for key in (
                    "authorization_action_ref",
                    "grant_action_ref",
                    "dispatch_action_ref",
                    "lease_ref",
                    "specialist_budget_ref",
                )
            )
        )
    ):
        raise SpecialistGraphRuntimeError("Specialist work node is invalid")
    _reject_private(node, context="Specialist work node")
    return {
        **node,
        "node_id": declared_id,
        "node_revision": declared_revision,
        "node_digest": declared_digest,
    }


def bind_specialist_work_authority(
    value: Mapping[str, Any],
    *,
    authorization_action_ref: Mapping[str, Any],
    grant_action_ref: Mapping[str, Any],
    dispatch_action_ref: Mapping[str, Any],
    lease_ref: Mapping[str, Any],
    specialist_budget_ref: Mapping[str, Any],
) -> dict[str, Any]:
    base = validate_specialist_work_node(value)
    for key in ("node_id", "node_revision", "node_digest"):
        base.pop(key, None)
    base.update(
        {
            "authorization_action_ref": _json_safe(
                _mapping(authorization_action_ref)
            ),
            "grant_action_ref": _json_safe(_mapping(grant_action_ref)),
            "dispatch_action_ref": _json_safe(_mapping(dispatch_action_ref)),
            "lease_ref": _json_safe(_mapping(lease_ref)),
            "specialist_budget_ref": _json_safe(_mapping(specialist_budget_ref)),
        }
    )
    digest = specialist_digest(base)
    return {
        **base,
        "node_id": f"specialist-work:{digest[:24]}",
        "node_revision": 2,
        "node_digest": digest,
    }


def execute_specialist_capability(
    *,
    registry: SpecialistCapabilityRegistry,
    work_node: Mapping[str, Any],
    authorization_action_ref: Mapping[str, Any],
    lease_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute one registered deterministic adapter on the main thread."""

    work = validate_specialist_work_node(work_node)
    if (
        _mapping(work.get("authorization_action_ref"))
        != _json_safe(_mapping(authorization_action_ref))
        or _mapping(work.get("lease_ref")) != _json_safe(_mapping(lease_ref))
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist execution authority does not match the work node"
        )
    spec = registry.get(str(work.get("capability_id") or ""), str(work.get("capability_version") or ""))
    if spec.descriptor()["descriptor_digest"] != work.get("capability_descriptor_digest"):
        raise SpecialistGraphRuntimeError("Specialist capability descriptor became stale")
    bounded_input = deepcopy(_mapping(work.get("bounded_inputs")))
    raw_output = spec.adapter(bounded_input)
    if not isinstance(raw_output, Mapping):
        raise SpecialistGraphRuntimeError("Specialist adapter must return one mapping")
    output = _json_safe(dict(raw_output))
    _reject_private(output, context="Specialist result")
    posture = str(output.get("execution_posture") or EXECUTION_COMPLETED)
    if posture not in _EXECUTION_POSTURES:
        raise SpecialistGraphRuntimeError("Specialist execution posture is invalid")
    bounded_result = _json_safe(_mapping(output.get("bounded_result")))
    if posture == EXECUTION_COMPLETED and not bounded_result:
        raise SpecialistGraphRuntimeError("completed Specialist result must be bounded")
    core = {
        "schema_version": SPECIALIST_RESULT_SCHEMA_VERSION,
        "run_id": work.get("run_id"),
        "request_id": work.get("request_id"),
        "work_ref": specialist_work_ref(work),
        "proposal_ref": deepcopy(work.get("proposal_ref") or {}),
        "capability_id": work.get("capability_id"),
        "capability_version": work.get("capability_version"),
        "capability_descriptor_digest": work.get("capability_descriptor_digest"),
        "authorization_action_ref": _json_safe(_mapping(authorization_action_ref)),
        "lease_ref": _json_safe(_mapping(lease_ref)),
        "canonical_target_ref": deepcopy(work.get("canonical_target_ref") or {}),
        "accepted_contract_ref": deepcopy(work.get("accepted_contract_ref") or {}),
        "graph_ref": deepcopy(work.get("graph_ref") or {}),
        "input_digest": work.get("input_digest"),
        "output_schema_ref": work.get("output_schema_ref"),
        "bounded_result": bounded_result,
        "assumptions": list(_text_list(output.get("assumptions"))),
        "caveats": list(_text_list(output.get("caveats"))),
        "blockers": list(_text_list(output.get("blockers"))),
        "confidence_posture": _text(output.get("confidence_posture"), limit=120),
        "execution_posture": posture,
        "dprime_route": (
            "component_dprime"
            if _mapping(work.get("canonical_target_ref")).get("target_kind") == "component"
            else "synthesis_dprime"
        ),
        "validator_consumption": VALIDATOR_PENDING,
        "raw_input_retained": False,
        "raw_output_retained": False,
        "private_material_retained": False,
        "recursive_proposal_allowed": False,
        "component_admission_authority": False,
        "synthesis_admission_authority": False,
        "semantic_observation_authority": False,
        "component_coverage_authority": False,
        "sufficiency_authority": False,
        "final_answer_packet_authority": False,
        "author_authority": False,
        "citation_authority": False,
        "source_obligation_authority": False,
        "provider_request_attempt_count": 0,
        "model_call_count": 0,
        "token_usage": 0,
        "model_cost": 0,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "result_id": f"specialist-result:{digest[:24]}",
        "result_digest": digest,
    }


def build_specialist_terminal_result(
    *,
    work_node: Mapping[str, Any],
    authorization_action_ref: Mapping[str, Any],
    lease_ref: Mapping[str, Any],
    execution_posture: str,
    blocker: str,
) -> dict[str, Any]:
    """Build a bounded failed/blocked/contested result without adapter output."""

    if execution_posture not in {
        EXECUTION_FAILED,
        EXECUTION_BLOCKED,
        EXECUTION_CONTESTED,
        EXECUTION_STALE,
    }:
        raise SpecialistGraphRuntimeError("terminal Specialist posture is invalid")
    work = validate_specialist_work_node(work_node)
    core = {
        "schema_version": SPECIALIST_RESULT_SCHEMA_VERSION,
        "run_id": work.get("run_id"),
        "request_id": work.get("request_id"),
        "work_ref": specialist_work_ref(work),
        "proposal_ref": deepcopy(work.get("proposal_ref") or {}),
        "capability_id": work.get("capability_id"),
        "capability_version": work.get("capability_version"),
        "capability_descriptor_digest": work.get("capability_descriptor_digest"),
        "authorization_action_ref": _json_safe(_mapping(authorization_action_ref)),
        "lease_ref": _json_safe(_mapping(lease_ref)),
        "canonical_target_ref": deepcopy(work.get("canonical_target_ref") or {}),
        "accepted_contract_ref": deepcopy(work.get("accepted_contract_ref") or {}),
        "graph_ref": deepcopy(work.get("graph_ref") or {}),
        "input_digest": work.get("input_digest"),
        "output_schema_ref": work.get("output_schema_ref"),
        "bounded_result": {},
        "assumptions": [],
        "caveats": [],
        "blockers": [_text(blocker, limit=500, required=True)],
        "confidence_posture": None,
        "execution_posture": execution_posture,
        "dprime_route": (
            "component_dprime"
            if _mapping(work.get("canonical_target_ref")).get("target_kind") == "component"
            else "synthesis_dprime"
        ),
        "validator_consumption": VALIDATOR_PENDING,
        "raw_input_retained": False,
        "raw_output_retained": False,
        "private_material_retained": False,
        "recursive_proposal_allowed": False,
        "component_admission_authority": False,
        "synthesis_admission_authority": False,
        "semantic_observation_authority": False,
        "component_coverage_authority": False,
        "sufficiency_authority": False,
        "final_answer_packet_authority": False,
        "author_authority": False,
        "citation_authority": False,
        "source_obligation_authority": False,
        "provider_request_attempt_count": 0,
        "model_call_count": 0,
        "token_usage": 0,
        "model_cost": 0,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "result_id": f"specialist-result:{digest[:24]}",
        "result_digest": digest,
    }


def specialist_result_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _mapping(value)
    return {
        "result_id": result.get("result_id"),
        "result_digest": result.get("result_digest"),
        "work_ref": deepcopy(result.get("work_ref") or {}),
        "canonical_target_ref": deepcopy(result.get("canonical_target_ref") or {}),
        "capability_id": result.get("capability_id"),
        "capability_version": result.get("capability_version"),
        "execution_posture": result.get("execution_posture"),
    }


def validate_specialist_result_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value))
    declared_id = result.pop("result_id", None)
    declared_digest = result.pop("result_digest", None)
    identity_payload = deepcopy(result)
    validator_consumption = identity_payload.get("validator_consumption")
    if validator_consumption != VALIDATOR_PENDING:
        identity_payload["validator_consumption"] = VALIDATOR_PENDING
        identity_payload.pop("validator_consumption_terminal", None)
        identity_payload.pop("validator_validation_status", None)
    digest = specialist_digest(identity_payload)
    if (
        result.get("schema_version") != SPECIALIST_RESULT_SCHEMA_VERSION
        or declared_digest != digest
        or declared_id != f"specialist-result:{digest[:24]}"
        or validator_consumption
        not in {
            VALIDATOR_PENDING,
            VALIDATOR_COMPONENT,
            VALIDATOR_SYNTHESIS,
            VALIDATOR_CONTESTED,
            VALIDATOR_REJECTED,
        }
        or result.get("recursive_proposal_allowed") is not False
        or result.get("execution_posture")
        not in {*_EXECUTION_POSTURES, EXECUTION_STALE}
        or result.get("dprime_route")
        != (
            "component_dprime"
            if _mapping(result.get("canonical_target_ref")).get("target_kind")
            == "component"
            else "synthesis_dprime"
        )
        or any(
            result.get(key) is not False
            for key in (
                "component_admission_authority",
                "synthesis_admission_authority",
                "semantic_observation_authority",
                "component_coverage_authority",
                "sufficiency_authority",
                "final_answer_packet_authority",
                "author_authority",
                "citation_authority",
                "source_obligation_authority",
                "raw_input_retained",
                "raw_output_retained",
                "private_material_retained",
            )
        )
        or any(
            int(result.get(key) or 0) != 0
            for key in (
                "provider_request_attempt_count",
                "model_call_count",
                "token_usage",
                "model_cost",
            )
        )
        or (
            validator_consumption == VALIDATOR_PENDING
            and (
                "validator_consumption_terminal" in result
                or "validator_validation_status" in result
            )
        )
        or (
            validator_consumption != VALIDATOR_PENDING
            and result.get("validator_consumption_terminal") != VALIDATOR_TERMINAL
        )
    ):
        raise SpecialistGraphRuntimeError("Specialist result artifact is invalid")
    _reject_private(result, context="Specialist result artifact")
    return {**result, "result_id": declared_id, "result_digest": declared_digest}


def initialize_specialist_work_plane(
    *, registry: SpecialistCapabilityRegistry, policy: SpecialistExecutionPolicy
) -> dict[str, Any]:
    registry_projection = registry.projection()
    policy_projection = policy.projection()
    state = {
        "schema_version": SPECIALIST_STATE_SCHEMA_VERSION,
        "owner": SPECIALIST_WORK_PLANE_OWNER,
        "canonical_state": True,
        "registry_ref": {
            "registry_digest": registry_projection["registry_digest"],
            "capability_count": registry_projection["capability_count"],
            "adapters_retained": False,
        },
        "execution_policy_ref": {
            "execution_policy_digest": policy_projection["execution_policy_digest"],
            "enabled_capability_ids": list(policy.enabled_capability_ids),
            "specialist_work_item_limit": policy.specialist_work_item_limit,
            "parallelism": False,
            "recursion": False,
        },
        "proposals": [],
        "work_nodes": [],
        "result_artifacts": [],
        "maximum_observed_in_flight": 0,
        "provider_request_attempt_count": 0,
        "model_call_count": 0,
        "token_usage": 0,
        "model_cost": 0,
        "raw_private_material_retained": False,
    }
    return _refresh_state(state)


def initialize_specialist_work_plane_from_projections(
    *, registry_projection: Mapping[str, Any], policy_projection: Mapping[str, Any]
) -> dict[str, Any]:
    registry = _mapping(registry_projection)
    policy = _mapping(policy_projection)
    if (
        registry.get("schema_version") != SPECIALIST_REGISTRY_SCHEMA_VERSION
        or registry.get("registry_digest")
        != specialist_digest(
            {key: value for key, value in registry.items() if key != "registry_digest"}
        )
        or policy.get("schema_version") != SPECIALIST_POLICY_SCHEMA_VERSION
        or policy.get("execution_policy_digest")
        != specialist_digest(
            {
                key: value
                for key, value in policy.items()
                if key != "execution_policy_digest"
            }
        )
    ):
        raise SpecialistGraphRuntimeError("Specialist registry/policy projection is invalid")
    state = {
        "schema_version": SPECIALIST_STATE_SCHEMA_VERSION,
        "owner": SPECIALIST_WORK_PLANE_OWNER,
        "canonical_state": True,
        "registry_ref": {
            "registry_digest": registry["registry_digest"],
            "capability_count": registry.get("capability_count"),
            "adapters_retained": False,
        },
        "execution_policy_ref": {
            "execution_policy_digest": policy["execution_policy_digest"],
            "enabled_capability_ids": deepcopy(policy.get("enabled_capability_ids") or []),
            "specialist_work_item_limit": policy.get("specialist_work_item_limit"),
            "parallelism": False,
            "recursion": False,
        },
        "proposals": [],
        "work_nodes": [],
        "result_artifacts": [],
        "maximum_observed_in_flight": 0,
        "provider_request_attempt_count": 0,
        "model_call_count": 0,
        "token_usage": 0,
        "model_cost": 0,
        "raw_private_material_retained": False,
    }
    return _refresh_state(state)


def _refresh_state(value: Mapping[str, Any]) -> dict[str, Any]:
    state = deepcopy(dict(value))
    state.pop("state_digest", None)
    state["proposal_count"] = len(state.get("proposals") or ())
    state["work_node_count"] = len(state.get("work_nodes") or ())
    state["result_artifact_count"] = len(state.get("result_artifacts") or ())
    state["state_digest"] = specialist_digest(state)
    return state


def append_bound_proposal(state: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    bound = deepcopy(dict(proposal))
    if any(
        _mapping(item).get("proposal_id") == bound.get("proposal_id")
        for item in current.get("proposals") or ()
    ):
        raise SpecialistGraphRuntimeError("duplicate Specialist proposal")
    current["proposals"].append(bound)
    return _refresh_state(current)


def append_specialist_result(
    state: Mapping[str, Any], *, work_node: Mapping[str, Any], result: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    work = validate_specialist_work_node(work_node)
    artifact = validate_specialist_result_artifact(result)
    proposal_id = _mapping(work.get("proposal_ref")).get("proposal_id")
    if proposal_id not in {
        _mapping(item).get("proposal_id") for item in current.get("proposals") or ()
    }:
        raise SpecialistGraphRuntimeError("Specialist work lacks an accepted proposal")
    if any(
        _mapping(item).get("node_id") == work.get("node_id")
        for item in current.get("work_nodes") or ()
    ):
        raise SpecialistGraphRuntimeError("Specialist work already completed")
    if _mapping(artifact.get("work_ref")) != specialist_work_ref(work):
        raise SpecialistGraphRuntimeError("Specialist result does not bind exact work")
    current["work_nodes"].append(work)
    current["result_artifacts"].append(artifact)
    current["maximum_observed_in_flight"] = max(
        int(current.get("maximum_observed_in_flight") or 0), 1
    )
    return _refresh_state(current)


def mark_validator_consumption(
    state: Mapping[str, Any], *, result_id: str, route: str, validation_status: str
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    index = next(
        (
            index
            for index, item in enumerate(current.get("result_artifacts") or ())
            if _mapping(item).get("result_id") == result_id
        ),
        -1,
    )
    if index < 0:
        raise SpecialistGraphRuntimeError("validator consumed an unknown Specialist result")
    result = _mapping(current["result_artifacts"][index])
    if result.get("validator_consumption") != VALIDATOR_PENDING:
        raise SpecialistGraphRuntimeError("Specialist result was already consumed")
    status = str(validation_status or "")
    if status in {"challenged", "contested"}:
        lifecycle = VALIDATOR_CONTESTED
    elif status in {"blocked", "rejected", "unsupported", "abstain"}:
        lifecycle = VALIDATOR_REJECTED
    elif route == "component_dprime":
        lifecycle = VALIDATOR_COMPONENT
    elif route == "synthesis_dprime":
        lifecycle = VALIDATOR_SYNTHESIS
    else:
        raise SpecialistGraphRuntimeError("Specialist validator route is invalid")
    result["validator_consumption"] = lifecycle
    result["validator_consumption_terminal"] = VALIDATOR_TERMINAL
    result["validator_validation_status"] = status
    current["result_artifacts"][index] = result
    return _refresh_state(current)


def pending_proposal_for_target(
    state: Mapping[str, Any], *, target_kind: str, target_key: str
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    completed_ids = {
        _mapping(_mapping(item).get("proposal_ref")).get("proposal_id")
        for item in current.get("work_nodes") or ()
    }
    matches = [
        _mapping(item)
        for item in current.get("proposals") or ()
        if item.get("proposal_authority") == PROPOSAL_ACCEPTED
        and item.get("proposal_id") not in completed_ids
        and _mapping(item.get("canonical_target_ref")).get("target_kind") == target_kind
        and _mapping(item.get("canonical_target_ref")).get("target_key") == target_key
    ]
    return deepcopy(matches[0]) if matches else {}


def result_for_target(
    state: Mapping[str, Any], *, target_kind: str, target_key: str
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    matches = [
        _mapping(item)
        for item in current.get("result_artifacts") or ()
        if _mapping(item.get("canonical_target_ref")).get("target_kind") == target_kind
        and _mapping(item.get("canonical_target_ref")).get("target_key") == target_key
    ]
    return deepcopy(matches[-1]) if matches else {}


def required_rejection_for_target(
    state: Mapping[str, Any], *, target_kind: str, target_key: str
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    matches = [
        _mapping(item)
        for item in current.get("proposals") or ()
        if item.get("posture") == "required"
        and item.get("proposal_authority") != PROPOSAL_ACCEPTED
        and _mapping(item.get("canonical_target_ref")).get("target_kind") == target_kind
        and _mapping(item.get("canonical_target_ref")).get("target_key") == target_key
    ]
    return deepcopy(matches[-1]) if matches else {}


def validate_specialist_work_plane(value: Mapping[str, Any]) -> dict[str, Any]:
    state = deepcopy(dict(value))
    declared = state.pop("state_digest", None)
    if (
        state.get("schema_version") != SPECIALIST_STATE_SCHEMA_VERSION
        or state.get("owner") != SPECIALIST_WORK_PLANE_OWNER
        or state.get("canonical_state") is not True
        or state.get("raw_private_material_retained") is not False
        or int(state.get("maximum_observed_in_flight") or 0) > 1
        or int(state.get("provider_request_attempt_count") or 0) != 0
        or int(state.get("model_call_count") or 0) != 0
        or int(state.get("token_usage") or 0) != 0
        or int(state.get("model_cost") or 0) != 0
    ):
        raise SpecialistGraphRuntimeError("Specialist work-plane state is invalid")
    _reject_private(state, context="Specialist retained state")
    refreshed = _refresh_state(state)
    if declared != refreshed.get("state_digest"):
        raise SpecialistGraphRuntimeError("Specialist work-plane digest mismatch")
    return refreshed


__all__ = [
    "EXECUTION_BLOCKED",
    "EXECUTION_COMPLETED",
    "EXECUTION_CONTESTED",
    "EXECUTION_FAILED",
    "EXECUTION_STALE",
    "EXECUTOR_REGISTERED_DETERMINISTIC",
    "PROPOSAL_ACCEPTED",
    "PROPOSAL_DENIED_POLICY",
    "PROPOSAL_REJECTED",
    "PROPOSAL_UNSUPPORTED_TARGET",
    "RESOURCE_DETERMINISTIC_SPECIALIST",
    "SPECIALIST_NEED_SCHEMA_VERSION",
    "SPECIALIST_RESULT_SCHEMA_VERSION",
    "SPECIALIST_WORK_NODE_SCHEMA_VERSION",
    "SPECIALIST_WORK_PLANE_STAGE",
    "SpecialistCapabilityRegistry",
    "SpecialistCapabilitySpec",
    "SpecialistExecutionPolicy",
    "SpecialistGraphRuntimeError",
    "append_bound_proposal",
    "append_specialist_result",
    "bind_specialist_need_proposal",
    "bind_specialist_work_authority",
    "build_specialist_work_node",
    "build_specialist_terminal_result",
    "closed_specialist_execution_policy",
    "closed_specialist_registry",
    "execute_specialist_capability",
    "initialize_specialist_work_plane",
    "initialize_specialist_work_plane_from_projections",
    "mark_validator_consumption",
    "normalize_specialist_need_proposal",
    "pending_proposal_for_target",
    "proposal_ref",
    "required_rejection_for_target",
    "result_for_target",
    "specialist_digest",
    "specialist_result_ref",
    "specialist_work_ref",
    "validate_specialist_work_plane",
    "validate_bound_specialist_proposal",
    "validate_specialist_result_artifact",
    "validate_specialist_work_node",
]
