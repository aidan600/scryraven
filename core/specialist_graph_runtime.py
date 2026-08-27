"""Generic, closed-by-default Specialist graph work contracts.

This module owns bounded Specialist proposals, capability descriptors, policy,
work nodes, and result artifacts.  It deliberately owns no scheduler,
admission, provider/model transport, retrieval, persistence, or answer path.
Adapters are held only by ``SpecialistCapabilityRegistry`` and are never
included in retained RunKernel state.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

SPECIALIST_WORK_PLANE_STAGE = "specialist_work_plane"
SPECIALIST_WORK_PLANE_OWNER = "RunKernel.SpecialistWorkPlane"
SPECIALIST_NEED_SCHEMA_VERSION = "specialist_need_proposal_v1"
SPECIALIST_PROPOSAL_REJECTION_SCHEMA_VERSION = (
    "specialist_proposal_candidate_rejection_v1"
)
SPECIALIST_WORK_NODE_SCHEMA_VERSION = "specialist_work_node_v2"
SPECIALIST_RESULT_SCHEMA_VERSION = "specialist_result_artifact_v1"
SPECIALIST_DISPOSITION_SCHEMA_VERSION = "specialist_proposal_disposition_v1"
SPECIALIST_HANDOFF_SCHEMA_VERSION = "specialist_need_handoff_v1"
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
VALIDATOR_COMPONENT_ANALYST = "consumed_by_component_analyst"
VALIDATOR_SYNTHESIS = "consumed_by_synthesis_dprime"
VALIDATOR_REJECTED = "rejected_by_validator"
VALIDATOR_CONTESTED = "contested_by_validator"
VALIDATOR_TERMINAL = "terminal"

EXECUTION_COMPLETED = "completed"
EXECUTION_FAILED = "failed_spent"
EXECUTION_BLOCKED = "blocked_spent"
EXECUTION_CONTESTED = "contested_spent"
EXECUTION_STALE = "stale_rejected_spent"

AVAILABILITY_RESULT = "result_available"
AVAILABILITY_POLICY = "unavailable_policy"
AVAILABILITY_CAPABILITY = "unavailable_capability"
AVAILABILITY_TARGET = "unavailable_target"
AVAILABILITY_BUDGET = "unavailable_budget"
AVAILABILITY_FAILED = "failed"
AVAILABILITY_BLOCKED = "blocked"
AVAILABILITY_CONTESTED = "contested"

_TARGET_KINDS = frozenset(
    {"component", "synthesis", "edge", "subgraph", "graph", "whole_case"}
)
_POSTURES = frozenset({"required", "optional"})
SPECIALIST_UNCLASSIFIED_POSTURE = "unclassified_fail_closed"
SPECIALIST_NEED_ALLOWED_FIELDS = frozenset(
    {
        "schema_version",
        "local_need_id",
        "capability_requirement",
        "candidate_capability_hint",
        "bounded_question",
        "target",
        "posture",
        "input_schema_ref",
        "expected_output_schema_ref",
        "input_artifact_refs",
        "assumptions",
        "caveats",
        "nonclaims",
        "advisory_budget_posture",
        "recursion_depth",
        "specialist_parent_ref",
        "capability_request",
    }
)
SPECIALIST_NEED_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "local_need_id",
        "capability_requirement",
        "bounded_question",
        "target",
        "posture",
        "input_schema_ref",
        "expected_output_schema_ref",
        "recursion_depth",
        "specialist_parent_ref",
    }
)
SPECIALIST_NEED_TARGET_FIELDS = frozenset({"target_kind", "target_key"})
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
SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES = 16 * 1024
SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH = 6
SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS = 64
SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS = 64
SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH = 1000
_CAPABILITY_REQUEST_FORBIDDEN_KEYS = frozenset(
    {
        "action",
        "action_id",
        "admission",
        "admission_status",
        "author",
        "author_authority",
        "author_claim",
        "bounded_text",
        "canonical_action",
        "canonical_lease",
        "canonical_state",
        "challenge_id",
        "code",
        "component_id",
        "conversion_expression",
        "db_row",
        "edge_id",
        "env",
        "executable_expression",
        "expression",
        "fap",
        "fap_authority",
        "fetch",
        "field_path",
        "final_answer_packet",
        "formula",
        "formula_expression",
        "formula_string",
        "full_prompt",
        "graph",
        "graph_id",
        "graph_ref",
        "graph_revision",
        "json_path",
        "lease",
        "lease_id",
        "model",
        "model_response",
        "node_id",
        "node_revision",
        "observation_id",
        "password",
        "prompt",
        "proposal_id",
        "provider",
        "read",
        "request_id",
        "response",
        "retrieval",
        "revision",
        "run_id",
        "runkernel_action",
        "runkernel_observation",
        "search",
        "source_path",
        "source_text",
        "url",
        "validation_id",
    }
)
_CAPABILITY_REQUEST_FORBIDDEN_KEY_PARTS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "credential",
        "private",
        "prompt",
        "provider",
        "raw_",
        "response",
        "retrieval",
        "secret",
        "search",
    }
)
_SPECIALIST_FORBIDDEN_AUTHORITY_OR_MATERIAL_KEYS = frozenset(
    _CAPABILITY_REQUEST_FORBIDDEN_KEYS | _RAW_PRIVATE_KEYS
)


class SpecialistGraphRuntimeError(ValueError):
    """Raised when Specialist state would exceed the generic S0 contract."""


class SpecialistProposalCandidateError(SpecialistGraphRuntimeError):
    """Raised with one bounded category for an invalid parsed proposal."""

    def __init__(self, rejection_category: str, reason: str) -> None:
        super().__init__(reason)
        self.rejection_category = rejection_category


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


def _exact_text(
    value: Any,
    *,
    field: str,
    limit: int,
    required: bool = False,
) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value or len(value) > limit:
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            f"Specialist proposal {field} must be one bounded exact string",
        )
    if value != value.strip() or any(char in "\r\n\t" for char in value):
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            f"Specialist proposal {field} is not canonical bounded text",
        )
    return value


def _exact_token(
    value: Any,
    *,
    field: str,
    limit: int = 180,
    required: bool = False,
) -> str | None:
    token = _exact_text(
        value,
        field=field,
        limit=limit,
        required=required,
    )
    if token and any(char.isspace() for char in token):
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            f"Specialist proposal {field} cannot contain whitespace",
        )
    return token


def _exact_text_list(value: Any, *, field: str, limit: int = 500) -> list[str]:
    if not isinstance(value, list):
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            f"Specialist proposal {field} must be one JSON list",
        )
    if len(value) > 20:
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            f"Specialist proposal {field} exceeds its bounded list limit",
        )
    return [
        str(
            _exact_text(
                item,
                field=field,
                limit=limit,
                required=True,
            )
        )
        for item in value
    ]


def _exact_input_refs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 20:
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            "Specialist proposal input_artifact_refs must be one bounded JSON list",
        )
    exact = _validate_exact_specialist_json(
        value,
        context="Specialist proposal input_artifact_refs",
        enforce_bounds=True,
    )
    if not isinstance(exact, list) or any(
        not isinstance(item, dict) or not item for item in exact
    ):
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            "Specialist proposal input_artifact_refs must contain exact mappings",
        )
    return deepcopy(exact)


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


def _normalized_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _validate_exact_specialist_json(
    value: Any,
    *,
    context: str,
    enforce_bounds: bool,
) -> Any:
    """Validate exact generic proposal JSON without coercion or softening."""

    mapping_key_count = 0
    list_item_count = 0

    def reject(reason: str, *, authority: bool = False) -> None:
        raise SpecialistProposalCandidateError(
            (
                "forbidden_authority_or_material"
                if authority
                else "invalid_generic_envelope"
            ),
            reason,
        )

    def validate(item: Any, *, depth: int) -> Any:
        nonlocal mapping_key_count, list_item_count
        if enforce_bounds and depth > SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH:
            reject(f"{context} exceeds maximum nesting depth")
        if not enforce_bounds and depth > 64:
            reject(f"{context} exceeds safe recursive inspection depth")
        if callable(item) or isinstance(item, bytes | bytearray | memoryview):
            reject(f"{context} contains executable or binary material")
        if item is None or isinstance(item, bool | int):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                reject(f"{context} contains a non-finite number")
            return item
        if isinstance(item, str):
            if (
                enforce_bounds
                and len(item) > SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH
            ):
                reject(f"{context} string exceeds maximum length")
            return item
        if isinstance(item, Mapping):
            if enforce_bounds:
                mapping_key_count += len(item)
                if (
                    mapping_key_count
                    > SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS
                ):
                    reject(f"{context} exceeds maximum mapping keys")
            exact_mapping: dict[str, Any] = {}
            for key, child in item.items():
                if not isinstance(key, str) or not key.strip():
                    reject(f"{context} keys must be nonempty strings")
                normalized_key = _normalized_key(key)
                if (
                    normalized_key
                    in _SPECIALIST_FORBIDDEN_AUTHORITY_OR_MATERIAL_KEYS
                    or normalized_key.endswith("_digest")
                    or normalized_key.startswith("runkernel_")
                    or any(
                        part in normalized_key
                        for part in _CAPABILITY_REQUEST_FORBIDDEN_KEY_PARTS
                    )
                ):
                    reject(
                        f"{context} contains forbidden authority or material",
                        authority=True,
                    )
                exact_mapping[key] = validate(child, depth=depth + 1)
            return exact_mapping
        if isinstance(item, list):
            if enforce_bounds:
                list_item_count += len(item)
                if list_item_count > SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS:
                    reject(f"{context} exceeds maximum list items")
            return [validate(child, depth=depth + 1) for child in item]
        reject(f"{context} contains an unknown object type")

    exact = validate(value, depth=1)
    if enforce_bounds:
        encoded = json.dumps(
            exact,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES:
            reject(f"{context} exceeds maximum canonical JSON bytes")
    return exact


def normalize_specialist_capability_request(value: Any) -> dict[str, Any]:
    """Validate and preserve one exact capability-generic request envelope."""

    if not isinstance(value, Mapping):
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            "Specialist capability_request must be one JSON mapping",
        )
    exact = _validate_exact_specialist_json(
        value,
        context="Specialist capability_request",
        enforce_bounds=True,
    )
    return deepcopy(dict(exact))


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


def validate_specialist_need_proposal_candidate(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one exact parsed generic proposal without softening it."""

    if not isinstance(value, Mapping):
        raise SpecialistProposalCandidateError(
            "invalid_generic_envelope",
            "Specialist proposal candidate must be one JSON mapping",
        )
    raw = deepcopy(dict(value))
    _validate_exact_specialist_json(
        raw,
        context="Specialist proposal",
        enforce_bounds=False,
    )
    unknown = set(raw) - SPECIALIST_NEED_ALLOWED_FIELDS
    missing = SPECIALIST_NEED_REQUIRED_FIELDS - set(raw)
    if unknown:
        raise SpecialistProposalCandidateError(
            "unknown_proposal_field",
            "Specialist proposal contains unknown top-level fields",
        )
    if missing:
        category = (
            "missing_proposal_schema"
            if "schema_version" in missing
            else "invalid_generic_envelope"
        )
        raise SpecialistProposalCandidateError(
            category,
            "Specialist proposal is missing required generic fields",
        )
    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, str):
        raise SpecialistProposalCandidateError(
            "non_string_proposal_schema",
            "Specialist proposal schema_version must be a string",
        )
    if schema_version != SPECIALIST_NEED_SCHEMA_VERSION:
        raise SpecialistProposalCandidateError(
            "unsupported_proposal_schema",
            "Specialist proposal schema_version is unsupported",
        )
    target = raw.get("target")
    if not isinstance(target, Mapping) or set(target) != SPECIALIST_NEED_TARGET_FIELDS:
        raise SpecialistProposalCandidateError(
            "invalid_target_shape",
            "Specialist proposal target must contain exactly target_kind and target_key",
        )
    target_kind = target.get("target_kind")
    if not isinstance(target_kind, str) or target_kind not in _TARGET_KINDS:
        raise SpecialistProposalCandidateError(
            "invalid_target_shape",
            "Specialist proposal target_kind is invalid",
        )
    target_key = _exact_token(
        target.get("target_key"),
        field="target.target_key",
        required=True,
    )
    posture = raw.get("posture")
    if not isinstance(posture, str) or posture not in _POSTURES:
        raise SpecialistProposalCandidateError(
            "invalid_posture",
            "Specialist proposal posture is invalid",
        )
    if isinstance(raw.get("recursion_depth"), bool) or raw.get("recursion_depth") != 0:
        raise SpecialistProposalCandidateError(
            "invalid_fixed_generic_field",
            "Specialist proposal recursion_depth must be exact integer zero",
        )
    if raw.get("specialist_parent_ref") is not None:
        raise SpecialistProposalCandidateError(
            "invalid_fixed_generic_field",
            "Specialist proposal specialist_parent_ref must be null",
        )
    validated: dict[str, Any] = {
        "schema_version": schema_version,
        "local_need_id": _exact_token(
            raw.get("local_need_id"), field="local_need_id", required=True
        ),
        "capability_requirement": _exact_token(
            raw.get("capability_requirement"),
            field="capability_requirement",
            required=True,
        ),
        "bounded_question": _exact_text(
            raw.get("bounded_question"),
            field="bounded_question",
            limit=800,
            required=True,
        ),
        "target": {"target_kind": target_kind, "target_key": target_key},
        "posture": posture,
        "input_schema_ref": _exact_token(
            raw.get("input_schema_ref"), field="input_schema_ref", required=True
        ),
        "expected_output_schema_ref": _exact_token(
            raw.get("expected_output_schema_ref"),
            field="expected_output_schema_ref",
            required=True,
        ),
        "recursion_depth": 0,
        "specialist_parent_ref": None,
    }
    if "candidate_capability_hint" in raw:
        validated["candidate_capability_hint"] = _exact_token(
            raw.get("candidate_capability_hint"),
            field="candidate_capability_hint",
            required=True,
        )
    if "input_artifact_refs" in raw:
        validated["input_artifact_refs"] = _exact_input_refs(
            raw.get("input_artifact_refs")
        )
    for field_name in ("assumptions", "caveats", "nonclaims"):
        if field_name in raw:
            validated[field_name] = _exact_text_list(
                raw.get(field_name), field=field_name
            )
    if "advisory_budget_posture" in raw:
        validated["advisory_budget_posture"] = _exact_text(
            raw.get("advisory_budget_posture"),
            field="advisory_budget_posture",
            limit=240,
            required=True,
        )
    if "capability_request" in raw:
        validated["capability_request"] = normalize_specialist_capability_request(
            raw.get("capability_request")
        )
    return deepcopy(validated)


def normalize_specialist_need_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    """Compatibility name for exact generic candidate validation."""

    return validate_specialist_need_proposal_candidate(value)


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

    candidate = validate_specialist_need_proposal_candidate(proposal)
    normalized = {
        **candidate,
        "canonical_identity_claimed": False,
        "lease_authority_claimed": False,
        "dispatch_authority_claimed": False,
        "admission_authority_claimed": False,
    }
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


def safe_specialist_candidate_posture(value: Any) -> str:
    candidate = _mapping(value)
    posture = candidate.get("posture")
    return posture if posture in _POSTURES else SPECIALIST_UNCLASSIFIED_POSTURE


def safe_specialist_candidate_target(value: Any) -> dict[str, str]:
    candidate = _mapping(value)
    target = candidate.get("target")
    if not isinstance(target, Mapping) or set(target) != SPECIALIST_NEED_TARGET_FIELDS:
        return {}
    target_kind = target.get("target_kind")
    target_key = target.get("target_key")
    if (
        not isinstance(target_kind, str)
        or target_kind not in _TARGET_KINDS
        or not isinstance(target_key, str)
        or not target_key
        or len(target_key) > 180
        or target_key != target_key.strip()
        or any(char.isspace() for char in target_key)
    ):
        return {}
    return {"target_kind": target_kind, "target_key": target_key}


def proposal_schema_posture(value: Any) -> str:
    candidate = _mapping(value)
    if "schema_version" not in candidate:
        return "missing"
    schema_version = candidate.get("schema_version")
    if not isinstance(schema_version, str):
        return "non_string"
    return (
        "supported"
        if schema_version == SPECIALIST_NEED_SCHEMA_VERSION
        else "unsupported"
    )


def build_specialist_proposal_rejection(
    *,
    proposal_candidate: Any,
    rejection_category: str,
    quantitative_contract_schema_version: str | None = None,
    quantitative_contract_digest: str | None = None,
    quantitative_contract_instance_digest: str | None = None,
) -> dict[str, Any]:
    """Build a bounded fail-closed receipt without retaining the candidate."""

    category = _token(rejection_category, limit=100, required=True)
    core = {
        "schema_version": SPECIALIST_PROPOSAL_REJECTION_SCHEMA_VERSION,
        "supported_proposal_schema_version": SPECIALIST_NEED_SCHEMA_VERSION,
        "supplied_proposal_schema_posture": proposal_schema_posture(
            proposal_candidate
        ),
        "posture": safe_specialist_candidate_posture(proposal_candidate),
        "safe_local_target": safe_specialist_candidate_target(proposal_candidate),
        "rejection_category": category,
        "proposal_authority": PROPOSAL_REJECTED,
        "quantitative_contract_schema_version": _token(
            quantitative_contract_schema_version
        ),
        "quantitative_contract_digest": _token(
            quantitative_contract_digest
        ),
        "quantitative_contract_instance_digest": _token(
            quantitative_contract_instance_digest
        ),
        "accepted_proposal_authority": False,
        "specialist_work_authority": False,
        "raw_candidate_retained": False,
        "private_material_retained": False,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "rejection_id": f"specialist-proposal-rejection:{digest[:24]}",
        "rejection_digest": digest,
    }


def validate_specialist_proposal_rejection(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    rejection = deepcopy(dict(value))
    declared_id = rejection.pop("rejection_id", None)
    declared_digest = rejection.pop("rejection_digest", None)
    digest = specialist_digest(rejection)
    if (
        rejection.get("schema_version")
        != SPECIALIST_PROPOSAL_REJECTION_SCHEMA_VERSION
        or rejection.get("supported_proposal_schema_version")
        != SPECIALIST_NEED_SCHEMA_VERSION
        or rejection.get("supplied_proposal_schema_posture")
        not in {"missing", "non_string", "supported", "unsupported"}
        or rejection.get("posture")
        not in {*_POSTURES, SPECIALIST_UNCLASSIFIED_POSTURE}
        or _mapping(rejection.get("safe_local_target"))
        != safe_specialist_candidate_target(
            {"target": rejection.get("safe_local_target")}
        )
        or rejection.get("proposal_authority") != PROPOSAL_REJECTED
        or rejection.get("accepted_proposal_authority") is not False
        or rejection.get("specialist_work_authority") is not False
        or rejection.get("raw_candidate_retained") is not False
        or rejection.get("private_material_retained") is not False
        or declared_digest != digest
        or declared_id != f"specialist-proposal-rejection:{digest[:24]}"
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist proposal rejection receipt is invalid"
        )
    _reject_private(rejection, context="Specialist proposal rejection")
    return {
        **rejection,
        "rejection_id": declared_id,
        "rejection_digest": declared_digest,
    }


def build_specialist_work_node(
    *,
    proposal: Mapping[str, Any],
    bounded_input_digest: str,
    bounded_input_lineage_refs: Sequence[Mapping[str, Any]],
    bounded_input_reconstruction_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Build retained Specialist authority without retaining execution input."""

    bound = _mapping(proposal)
    if bound.get("proposal_authority") != PROPOSAL_ACCEPTED:
        raise SpecialistGraphRuntimeError("only an accepted Specialist proposal can become work")
    descriptor = _mapping(bound.get("capability_descriptor"))
    input_digest = _token(bounded_input_digest, required=True)
    if len(str(input_digest)) != 64:
        raise SpecialistGraphRuntimeError(
            "Specialist bounded input digest is invalid"
        )
    lineage_refs = list(_safe_refs(bounded_input_lineage_refs))
    reconstruction_ref = _json_safe(_mapping(bounded_input_reconstruction_ref))
    if not lineage_refs or not reconstruction_ref:
        raise SpecialistGraphRuntimeError(
            "Specialist bounded input authority refs are incomplete"
        )
    _reject_private(
        reconstruction_ref, context="Specialist reconstruction ref"
    )
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
        "bounded_input_digest": input_digest,
        "bounded_input_schema_ref": descriptor.get("input_schema_ref"),
        "bounded_input_lineage_refs": lineage_refs,
        "bounded_input_reconstruction_ref": reconstruction_ref,
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
        "bounded_input_digest": node.get("bounded_input_digest"),
        "bounded_input_schema_ref": node.get("bounded_input_schema_ref"),
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
        or "bounded_inputs" in node
        or "input_digest" in node
        or "input_schema_ref" in node
        or len(str(node.get("bounded_input_digest") or "")) != 64
        or not _token(node.get("bounded_input_schema_ref"), required=True)
        or not _sequence(node.get("bounded_input_lineage_refs"))
        or not _mapping(node.get("bounded_input_reconstruction_ref"))
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
    transient_bounded_input: Mapping[str, Any],
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
    spec = registry.get(
        str(work.get("capability_id") or ""),
        str(work.get("capability_version") or ""),
    )
    if spec.descriptor()["descriptor_digest"] != work.get(
        "capability_descriptor_digest"
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist capability descriptor became stale"
        )
    bounded_input = _json_safe(_mapping(transient_bounded_input))
    _reject_private(
        bounded_input, context="transient Specialist bounded input"
    )
    if not bounded_input or specialist_digest(bounded_input) != work.get(
        "bounded_input_digest"
    ):
        raise SpecialistGraphRuntimeError(
            "transient Specialist input does not match authorized digest"
        )
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
        "bounded_input_digest": work.get("bounded_input_digest"),
        "bounded_input_schema_ref": work.get("bounded_input_schema_ref"),
        "output_schema_ref": work.get("output_schema_ref"),
        "bounded_result": bounded_result,
        "assumptions": list(_text_list(output.get("assumptions"))),
        "caveats": list(_text_list(output.get("caveats"))),
        "blockers": list(_text_list(output.get("blockers"))),
        "confidence_posture": _text(output.get("confidence_posture"), limit=120),
        "execution_posture": posture,
        "validator_route": (
            "component_analyst"
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
        "bounded_input_digest": work.get("bounded_input_digest"),
        "bounded_input_schema_ref": work.get("bounded_input_schema_ref"),
        "output_schema_ref": work.get("output_schema_ref"),
        "bounded_result": {},
        "assumptions": [],
        "caveats": [],
        "blockers": [_text(blocker, limit=500, required=True)],
        "confidence_posture": None,
        "execution_posture": execution_posture,
        "validator_route": (
            "component_analyst"
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
        identity_payload.pop("validator_dprime_artifact_ref", None)
        identity_payload.pop("validator_artifact_ref", None)
    digest = specialist_digest(identity_payload)
    if (
        result.get("schema_version") != SPECIALIST_RESULT_SCHEMA_VERSION
        or declared_digest != digest
        or declared_id != f"specialist-result:{digest[:24]}"
        or validator_consumption
        not in {
            VALIDATOR_PENDING,
            VALIDATOR_COMPONENT_ANALYST,
            VALIDATOR_SYNTHESIS,
            VALIDATOR_CONTESTED,
            VALIDATOR_REJECTED,
        }
        or result.get("recursive_proposal_allowed") is not False
        or "bounded_inputs" in result
        or "input_digest" in result
        or len(str(result.get("bounded_input_digest") or "")) != 64
        or not _token(result.get("bounded_input_schema_ref"), required=True)
        or result.get("execution_posture")
        not in {*_EXECUTION_POSTURES, EXECUTION_STALE}
        or not _valid_specialist_validator_route(result)
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


def _valid_specialist_validator_route(result: Mapping[str, Any]) -> bool:
    """Require the selected component or synthesis validator route."""

    target_kind = str(
        _mapping(result.get("canonical_target_ref")).get("target_kind") or ""
    )
    expected = "component_analyst" if target_kind == "component" else "synthesis_dprime"
    return result.get("validator_route") == expected


def _identity_without_validator_lifecycle(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    identity = deepcopy(dict(value))
    identity["validator_consumption"] = VALIDATOR_PENDING
    identity.pop("validator_consumption_terminal", None)
    identity.pop("validator_validation_status", None)
    identity.pop("validator_dprime_artifact_ref", None)
    identity.pop("validator_artifact_ref", None)
    return identity


def build_specialist_proposal_disposition(
    *,
    proposal: Mapping[str, Any],
    availability_posture: str,
    nonexecution_reason: str | None = None,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one immutable terminal proposal outcome sibling record."""

    bound = validate_bound_specialist_proposal(proposal)
    artifact = validate_specialist_result_artifact(result) if result else {}
    availability = str(availability_posture or "")
    allowed = {
        AVAILABILITY_RESULT,
        AVAILABILITY_POLICY,
        AVAILABILITY_CAPABILITY,
        AVAILABILITY_TARGET,
        AVAILABILITY_BUDGET,
        AVAILABILITY_FAILED,
        AVAILABILITY_BLOCKED,
        AVAILABILITY_CONTESTED,
    }
    reason_by_availability = {
        AVAILABILITY_POLICY: "denied_by_policy",
        AVAILABILITY_CAPABILITY: "unknown_or_incompatible_capability",
        AVAILABILITY_TARGET: "unsupported_target",
        AVAILABILITY_BUDGET: "specialist_pool_exhausted",
    }
    if availability not in allowed:
        raise SpecialistGraphRuntimeError(
            "Specialist disposition availability is invalid"
        )
    expected_reason = reason_by_availability.get(availability)
    if expected_reason and nonexecution_reason != expected_reason:
        raise SpecialistGraphRuntimeError(
            "Specialist disposition reason is invalid"
        )
    if availability in {
        AVAILABILITY_RESULT,
        AVAILABILITY_FAILED,
        AVAILABILITY_BLOCKED,
        AVAILABILITY_CONTESTED,
    } and artifact:
        expected_execution = {
            AVAILABILITY_RESULT: EXECUTION_COMPLETED,
            AVAILABILITY_FAILED: EXECUTION_FAILED,
            AVAILABILITY_BLOCKED: EXECUTION_BLOCKED,
            AVAILABILITY_CONTESTED: EXECUTION_CONTESTED,
        }[availability]
        if (
            not artifact
            or artifact.get("execution_posture") != expected_execution
            or _mapping(artifact.get("proposal_ref")).get("proposal_id")
            != bound.get("proposal_id")
        ):
            raise SpecialistGraphRuntimeError(
                "Specialist disposition result binding is invalid"
            )
        if nonexecution_reason is not None:
            raise SpecialistGraphRuntimeError(
                "executed Specialist disposition cannot name nonexecution"
            )
    elif availability == AVAILABILITY_FAILED:
        if nonexecution_reason != "input_reconstruction_failed":
            raise SpecialistGraphRuntimeError(
                "failed Specialist nonexecution disposition reason is invalid"
            )
    elif availability in {
        AVAILABILITY_RESULT,
        AVAILABILITY_BLOCKED,
        AVAILABILITY_CONTESTED,
    }:
        raise SpecialistGraphRuntimeError(
            "executed Specialist disposition requires a result"
        )
    elif artifact:
        raise SpecialistGraphRuntimeError(
            "nonexecution Specialist disposition cannot contain a result"
        )
    proposal_authority = str(bound.get("proposal_authority") or "")
    capability_resolution = {
        PROPOSAL_ACCEPTED: "capability_resolved",
        PROPOSAL_DENIED_POLICY: "denied_by_policy",
        PROPOSAL_REJECTED: "unknown_or_incompatible_capability",
        PROPOSAL_UNSUPPORTED_TARGET: "unsupported_target",
    }.get(proposal_authority)
    if not capability_resolution:
        raise SpecialistGraphRuntimeError(
            "Specialist disposition proposal authority is invalid"
        )
    core = {
        "schema_version": SPECIALIST_DISPOSITION_SCHEMA_VERSION,
        "proposal_ref": proposal_ref(bound),
        "origin_role": bound.get("origin_role"),
        "origin_action_ref": deepcopy(bound.get("origin_action_ref") or {}),
        "origin_artifact_ref": deepcopy(
            bound.get("origin_artifact_ref") or {}
        ),
        "canonical_target_ref": deepcopy(
            bound.get("canonical_target_ref") or {}
        ),
        "posture": bound.get("posture"),
        "proposal_authority": proposal_authority,
        "capability_resolution_posture": capability_resolution,
        "execution_availability_posture": availability,
        "registry_digest": bound.get("registry_digest"),
        "execution_policy_digest": bound.get("execution_policy_digest"),
        "assumptions": list(bound.get("assumptions") or ()),
        "caveats": list(bound.get("caveats") or ()),
        "nonclaims": list(bound.get("nonclaims") or ()),
        "terminal_nonexecution_reason": nonexecution_reason,
        "result_ref": specialist_result_ref(artifact) if artifact else {},
        "validator_consumption": VALIDATOR_PENDING,
        "transient_input_retained": False,
        "private_material_retained": False,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "disposition_id": f"specialist-disposition:{digest[:24]}",
        "disposition_digest": digest,
    }


def disposition_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    disposition = _mapping(value)
    return {
        "disposition_id": disposition.get("disposition_id"),
        "disposition_digest": disposition.get("disposition_digest"),
        "proposal_ref": deepcopy(disposition.get("proposal_ref") or {}),
        "canonical_target_ref": deepcopy(
            disposition.get("canonical_target_ref") or {}
        ),
        "availability_posture": disposition.get(
            "execution_availability_posture"
        ),
    }


def validate_specialist_proposal_disposition(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    disposition = deepcopy(dict(value))
    declared_id = disposition.pop("disposition_id", None)
    declared_digest = disposition.pop("disposition_digest", None)
    identity = _identity_without_validator_lifecycle(disposition)
    digest = specialist_digest(identity)
    lifecycle = disposition.get("validator_consumption")
    if (
        disposition.get("schema_version")
        != SPECIALIST_DISPOSITION_SCHEMA_VERSION
        or declared_digest != digest
        or declared_id != f"specialist-disposition:{digest[:24]}"
        or lifecycle
        not in {
            VALIDATOR_PENDING,
            VALIDATOR_COMPONENT_ANALYST,
            VALIDATOR_SYNTHESIS,
            VALIDATOR_CONTESTED,
            VALIDATOR_REJECTED,
        }
        or disposition.get("transient_input_retained") is not False
        or disposition.get("private_material_retained") is not False
        or "bounded_inputs" in disposition
        or "bounded_result" in disposition
        or (
            lifecycle == VALIDATOR_PENDING
            and "validator_consumption_terminal" in disposition
        )
        or (
            lifecycle != VALIDATOR_PENDING
            and disposition.get("validator_consumption_terminal")
            != VALIDATOR_TERMINAL
        )
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist proposal disposition is invalid"
        )
    _reject_private(disposition, context="Specialist proposal disposition")
    return {
        **disposition,
        "disposition_id": declared_id,
        "disposition_digest": declared_digest,
    }


def build_specialist_need_handoff(
    *,
    proposal: Mapping[str, Any],
    disposition: Mapping[str, Any],
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bound = validate_bound_specialist_proposal(proposal)
    terminal = validate_specialist_proposal_disposition(disposition)
    artifact = validate_specialist_result_artifact(result) if result else {}
    if (
        _mapping(terminal.get("proposal_ref")).get("proposal_id")
        != bound.get("proposal_id")
        or _mapping(terminal.get("canonical_target_ref"))
        != _mapping(bound.get("canonical_target_ref"))
        or bool(terminal.get("result_ref")) != bool(artifact)
        or (
            artifact
            and _mapping(terminal.get("result_ref"))
            != specialist_result_ref(artifact)
        )
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist handoff lineage is invalid"
        )
    result_payload = (
        {
            "result_ref": specialist_result_ref(artifact),
            "bounded_result": deepcopy(artifact.get("bounded_result") or {}),
            "execution_posture": artifact.get("execution_posture"),
        }
        if artifact
        else {}
    )
    blockers = list(artifact.get("blockers") or ()) if artifact else []
    reason = terminal.get("terminal_nonexecution_reason")
    if reason and reason not in blockers:
        blockers.append(str(reason))
    core = {
        "schema_version": SPECIALIST_HANDOFF_SCHEMA_VERSION,
        "namespace": "specialist_need_handoff",
        "proposal_ref": proposal_ref(bound),
        "disposition_ref": disposition_ref(terminal),
        "origin_role": bound.get("origin_role"),
        "canonical_target_ref": deepcopy(
            bound.get("canonical_target_ref") or {}
        ),
        "availability_posture": terminal.get("execution_availability_posture"),
        "result": result_payload,
        "assumptions": list(terminal.get("assumptions") or ()),
        "caveats": list(terminal.get("caveats") or ()),
        "blockers": blockers,
        "nonclaims": list(terminal.get("nonclaims") or ()),
        "nonexecution_reason": reason,
        "validator_consumption": VALIDATOR_PENDING,
        "transient_input_retained": False,
        "private_material_retained": False,
    }
    digest = specialist_digest(core)
    return {
        **core,
        "handoff_id": f"specialist-handoff:{digest[:24]}",
        "handoff_digest": digest,
    }


def validate_specialist_need_handoff(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    handoff = deepcopy(dict(value))
    declared_id = handoff.pop("handoff_id", None)
    declared_digest = handoff.pop("handoff_digest", None)
    identity = _identity_without_validator_lifecycle(handoff)
    digest = specialist_digest(identity)
    lifecycle = handoff.get("validator_consumption")
    if (
        handoff.get("schema_version") != SPECIALIST_HANDOFF_SCHEMA_VERSION
        or handoff.get("namespace") != "specialist_need_handoff"
        or declared_digest != digest
        or declared_id != f"specialist-handoff:{digest[:24]}"
        or lifecycle
        not in {
            VALIDATOR_PENDING,
            VALIDATOR_COMPONENT_ANALYST,
            VALIDATOR_SYNTHESIS,
            VALIDATOR_CONTESTED,
            VALIDATOR_REJECTED,
        }
        or handoff.get("transient_input_retained") is not False
        or handoff.get("private_material_retained") is not False
        or "bounded_inputs" in handoff
        or (
            lifecycle == VALIDATOR_PENDING
            and "validator_consumption_terminal" in handoff
        )
        or (
            lifecycle != VALIDATOR_PENDING
            and handoff.get("validator_consumption_terminal")
            != VALIDATOR_TERMINAL
        )
    ):
        raise SpecialistGraphRuntimeError("Specialist need handoff is invalid")
    _reject_private(handoff, context="Specialist need handoff")
    return {
        **handoff,
        "handoff_id": declared_id,
        "handoff_digest": declared_digest,
    }


def specialist_need_handoff_packet(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable handoff identity/content consumed by D-prime."""

    handoff = validate_specialist_need_handoff(value)
    return {
        key: deepcopy(handoff.get(key))
        for key in (
            "schema_version",
            "namespace",
            "handoff_id",
            "handoff_digest",
            "proposal_ref",
            "disposition_ref",
            "origin_role",
            "canonical_target_ref",
            "availability_posture",
            "result",
            "assumptions",
            "caveats",
            "blockers",
            "nonclaims",
            "nonexecution_reason",
        )
    }


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
        "proposal_rejections": [],
        "proposal_dispositions": [],
        "need_handoffs": [],
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
        "proposal_rejections": [],
        "proposal_dispositions": [],
        "need_handoffs": [],
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
    state["proposal_rejection_count"] = len(
        state.get("proposal_rejections") or ()
    )
    state["proposal_disposition_count"] = len(
        state.get("proposal_dispositions") or ()
    )
    state["need_handoff_count"] = len(state.get("need_handoffs") or ())
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


def append_specialist_proposal_rejection(
    state: Mapping[str, Any], rejection: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    receipt = validate_specialist_proposal_rejection(rejection)
    if any(
        _mapping(item).get("rejection_id") == receipt.get("rejection_id")
        for item in current.get("proposal_rejections") or ()
    ):
        raise SpecialistGraphRuntimeError("duplicate Specialist proposal rejection")
    current["proposal_rejections"].append(receipt)
    return _refresh_state(current)


def append_specialist_disposition(
    state: Mapping[str, Any],
    *,
    proposal: Mapping[str, Any],
    availability_posture: str,
    nonexecution_reason: str | None = None,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    bound = validate_bound_specialist_proposal(proposal)
    proposal_id = bound.get("proposal_id")
    if proposal_id not in {
        _mapping(item).get("proposal_id")
        for item in current.get("proposals") or ()
    }:
        raise SpecialistGraphRuntimeError(
            "Specialist disposition lacks a retained proposal"
        )
    if any(
        _mapping(_mapping(item).get("proposal_ref")).get("proposal_id")
        == proposal_id
        for item in current.get("proposal_dispositions") or ()
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist proposal already has a disposition"
        )
    disposition = build_specialist_proposal_disposition(
        proposal=bound,
        availability_posture=availability_posture,
        nonexecution_reason=nonexecution_reason,
        result=result,
    )
    handoff = build_specialist_need_handoff(
        proposal=bound,
        disposition=disposition,
        result=result,
    )
    current["proposal_dispositions"].append(disposition)
    current["need_handoffs"].append(handoff)
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
    refreshed = _refresh_state(current)
    availability = {
        EXECUTION_COMPLETED: AVAILABILITY_RESULT,
        EXECUTION_FAILED: AVAILABILITY_FAILED,
        EXECUTION_BLOCKED: AVAILABILITY_BLOCKED,
        EXECUTION_CONTESTED: AVAILABILITY_CONTESTED,
    }.get(str(artifact.get("execution_posture") or ""))
    if not availability:
        raise SpecialistGraphRuntimeError(
            "Specialist result cannot create a terminal disposition"
        )
    proposal = next(
        _mapping(item)
        for item in refreshed.get("proposals") or ()
        if _mapping(item).get("proposal_id") == proposal_id
    )
    return append_specialist_disposition(
        refreshed,
        proposal=proposal,
        availability_posture=availability,
        result=artifact,
    )


def mark_validator_consumption(
    state: Mapping[str, Any],
    *,
    handoff_id: str,
    route: str,
    validation_status: str,
    validator_artifact_ref: Mapping[str, Any] | None = None,
    dprime_artifact_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    handoff_index = next(
        (
            index
            for index, item in enumerate(current.get("need_handoffs") or ())
            if _mapping(item).get("handoff_id") == handoff_id
        ),
        -1,
    )
    if handoff_index < 0:
        raise SpecialistGraphRuntimeError(
            "validator consumed an unknown Specialist handoff"
        )
    handoff = _mapping(current["need_handoffs"][handoff_index])
    if handoff.get("validator_consumption") != VALIDATOR_PENDING:
        raise SpecialistGraphRuntimeError(
            "Specialist handoff was already consumed"
        )
    status = str(validation_status or "")
    if status in {"challenged", "contested"}:
        lifecycle = VALIDATOR_CONTESTED
    elif status in {"blocked", "rejected", "unsupported", "abstain"}:
        lifecycle = VALIDATOR_REJECTED
    elif route == "component_analyst":
        lifecycle = VALIDATOR_COMPONENT_ANALYST
    elif route == "synthesis_dprime":
        lifecycle = VALIDATOR_SYNTHESIS
    else:
        raise SpecialistGraphRuntimeError(
            "Specialist validator route is invalid"
        )
    lifecycle_fields = {
        "validator_consumption": lifecycle,
        "validator_consumption_terminal": VALIDATOR_TERMINAL,
        "validator_validation_status": status,
        "validator_artifact_ref": _json_safe(
            _mapping(validator_artifact_ref or dprime_artifact_ref)
        ),
    }
    handoff.update(lifecycle_fields)
    current["need_handoffs"][handoff_index] = handoff
    disposition_id = _mapping(handoff.get("disposition_ref")).get(
        "disposition_id"
    )
    disposition_index = next(
        index
        for index, item in enumerate(
            current.get("proposal_dispositions") or ()
        )
        if _mapping(item).get("disposition_id") == disposition_id
    )
    disposition = _mapping(current["proposal_dispositions"][disposition_index])
    if disposition.get("validator_consumption") != VALIDATOR_PENDING:
        raise SpecialistGraphRuntimeError(
            "Specialist disposition was already consumed"
        )
    disposition.update(lifecycle_fields)
    current["proposal_dispositions"][disposition_index] = disposition
    result_id = _mapping(
        _mapping(handoff.get("result")).get("result_ref")
    ).get("result_id")
    if result_id:
        result_index = next(
            index
            for index, item in enumerate(current.get("result_artifacts") or ())
            if _mapping(item).get("result_id") == result_id
        )
        result = _mapping(current["result_artifacts"][result_index])
        if result.get("validator_consumption") != VALIDATOR_PENDING:
            raise SpecialistGraphRuntimeError(
                "Specialist result was already consumed"
            )
        result.update(lifecycle_fields)
        current["result_artifacts"][result_index] = result
    return _refresh_state(current)


def pending_proposal_for_target(
    state: Mapping[str, Any], *, target_kind: str, target_key: str
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    completed_ids = {
        _mapping(_mapping(item).get("proposal_ref")).get("proposal_id")
        for item in current.get("work_nodes") or ()
    }
    completed_ids.update(
        _mapping(_mapping(item).get("proposal_ref")).get("proposal_id")
        for item in current.get("proposal_dispositions") or ()
    )
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


def handoff_for_target(
    state: Mapping[str, Any],
    *,
    target_kind: str,
    target_key: str,
    include_consumed: bool = False,
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    matches = [
        _mapping(item)
        for item in current.get("need_handoffs") or ()
        if _mapping(item.get("canonical_target_ref")).get("target_kind")
        == target_kind
        and _mapping(item.get("canonical_target_ref")).get("target_key")
        == target_key
        and (
            include_consumed
            or item.get("validator_consumption") == VALIDATOR_PENDING
        )
    ]
    return deepcopy(matches[-1]) if matches else {}


def handoff_by_id(
    state: Mapping[str, Any], *, handoff_id: str
) -> dict[str, Any]:
    current = validate_specialist_work_plane(state)
    match = next(
        (
            _mapping(item)
            for item in current.get("need_handoffs") or ()
            if _mapping(item).get("handoff_id") == handoff_id
        ),
        {},
    )
    return deepcopy(match)


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
        raise SpecialistGraphRuntimeError(
            "Specialist work-plane state is invalid"
        )
    proposals = [
        validate_bound_specialist_proposal(_mapping(item))
        for item in state.get("proposals") or ()
    ]
    rejections = [
        validate_specialist_proposal_rejection(_mapping(item))
        for item in state.get("proposal_rejections") or ()
    ]
    dispositions = [
        validate_specialist_proposal_disposition(_mapping(item))
        for item in state.get("proposal_dispositions") or ()
    ]
    handoffs = [
        validate_specialist_need_handoff(_mapping(item))
        for item in state.get("need_handoffs") or ()
    ]
    work_nodes = [
        validate_specialist_work_node(_mapping(item))
        for item in state.get("work_nodes") or ()
    ]
    results = [
        validate_specialist_result_artifact(_mapping(item))
        for item in state.get("result_artifacts") or ()
    ]
    identity_groups = (
        (proposals, "proposal_id"),
        (rejections, "rejection_id"),
        (dispositions, "disposition_id"),
        (handoffs, "handoff_id"),
        (work_nodes, "node_id"),
        (results, "result_id"),
    )
    if any(
        len(items) != len({_mapping(item).get(key) for item in items})
        for items, key in identity_groups
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist work-plane identity is duplicate"
        )
    proposal_ids = {_mapping(item).get("proposal_id") for item in proposals}
    disposition_by_id = {
        _mapping(item).get("disposition_id"): _mapping(item)
        for item in dispositions
    }
    if any(
        _mapping(_mapping(item).get("proposal_ref")).get("proposal_id")
        not in proposal_ids
        for item in dispositions
    ) or any(
        _mapping(_mapping(item).get("proposal_ref")).get("proposal_id")
        not in proposal_ids
        or _mapping(_mapping(item).get("disposition_ref")).get(
            "disposition_id"
        )
        not in disposition_by_id
        for item in handoffs
    ):
        raise SpecialistGraphRuntimeError(
            "Specialist disposition/handoff lineage is incomplete"
        )
    if len(dispositions) != len(handoffs):
        raise SpecialistGraphRuntimeError(
            "every terminal Specialist disposition requires exactly one handoff"
        )
    _reject_private(state, context="Specialist retained state")
    refreshed = _refresh_state(state)
    if declared != refreshed.get("state_digest"):
        raise SpecialistGraphRuntimeError("Specialist work-plane digest mismatch")
    return refreshed


__all__ = [
    "AVAILABILITY_BLOCKED",
    "AVAILABILITY_BUDGET",
    "AVAILABILITY_CAPABILITY",
    "AVAILABILITY_CONTESTED",
    "AVAILABILITY_FAILED",
    "AVAILABILITY_POLICY",
    "AVAILABILITY_RESULT",
    "AVAILABILITY_TARGET",
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
    "SPECIALIST_NEED_ALLOWED_FIELDS",
    "SPECIALIST_NEED_REQUIRED_FIELDS",
    "SPECIALIST_NEED_TARGET_FIELDS",
    "SPECIALIST_PROPOSAL_REJECTION_SCHEMA_VERSION",
    "SPECIALIST_UNCLASSIFIED_POSTURE",
    "SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES",
    "SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH",
    "SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS",
    "SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS",
    "SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH",
    "SPECIALIST_DISPOSITION_SCHEMA_VERSION",
    "SPECIALIST_HANDOFF_SCHEMA_VERSION",
    "SPECIALIST_RESULT_SCHEMA_VERSION",
    "SPECIALIST_WORK_NODE_SCHEMA_VERSION",
    "SPECIALIST_WORK_PLANE_STAGE",
    "SpecialistCapabilityRegistry",
    "SpecialistCapabilitySpec",
    "SpecialistExecutionPolicy",
    "SpecialistGraphRuntimeError",
    "SpecialistProposalCandidateError",
    "append_bound_proposal",
    "append_specialist_proposal_rejection",
    "append_specialist_disposition",
    "append_specialist_result",
    "bind_specialist_need_proposal",
    "bind_specialist_work_authority",
    "build_specialist_work_node",
    "build_specialist_need_handoff",
    "build_specialist_proposal_disposition",
    "build_specialist_proposal_rejection",
    "build_specialist_terminal_result",
    "closed_specialist_execution_policy",
    "closed_specialist_registry",
    "execute_specialist_capability",
    "initialize_specialist_work_plane",
    "initialize_specialist_work_plane_from_projections",
    "handoff_by_id",
    "handoff_for_target",
    "mark_validator_consumption",
    "normalize_specialist_need_proposal",
    "normalize_specialist_capability_request",
    "pending_proposal_for_target",
    "proposal_ref",
    "required_rejection_for_target",
    "result_for_target",
    "specialist_digest",
    "specialist_need_handoff_packet",
    "specialist_result_ref",
    "specialist_work_ref",
    "validate_specialist_work_plane",
    "validate_bound_specialist_proposal",
    "validate_specialist_result_artifact",
    "validate_specialist_need_handoff",
    "validate_specialist_proposal_disposition",
    "validate_specialist_proposal_rejection",
    "validate_specialist_need_proposal_candidate",
    "validate_specialist_work_node",
    "VALIDATOR_PENDING",
]
