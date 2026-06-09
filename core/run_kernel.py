"""Canonical RunKernel state, actions, observations, and trace projection.

AG-91H intentionally keeps this spine small. It authorizes bounded runtime
actions, reduces executor observations into RunState, and projects trace from
that state. It does not call models, search providers, persistence, prompts, or
ranking/citation/final-answer code.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

RUN_KERNEL_TRACE_KEY = "run_kernel"

ROUTE_REQUEST_STAGE = "route_request"
QUERY_PRODUCTION_STAGE = "query_production"
QUERY_PLAN_ADMISSION_STAGE = "query_plan_admission"
MAIN_RETRIEVAL_STAGE = "main_retrieval"
RETRIEVAL_STOP_CHECKPOINT_STAGE = "retrieval_stop_checkpoint"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)


class ActionType(str, Enum):
    """Bounded action vocabulary authorized by RunKernel."""

    ROUTE_REQUEST = "route_request"
    QUERY_PRODUCTION = "query_production"
    QUERY_PLAN_ADMISSION = "query_plan_admission"
    MAIN_RETRIEVAL_PASS = "main_retrieval_pass"
    RETRIEVAL_STOP_CHECKPOINT = "retrieval_stop_checkpoint"


class ObservationType(str, Enum):
    """Observation vocabulary returned by bounded executors/adapters."""

    ROUTE_RESULT = "route_result"
    QUERY_CANDIDATES_PRODUCED = "query_candidates_produced"
    QUERY_PLAN_ADMITTED = "query_plan_admitted"
    RETRIEVAL_PASS_RESULT = "retrieval_pass_result"
    RETRIEVAL_STOP_DECISION = "retrieval_stop_decision"


class RunStageStatus(str, Enum):
    """Compact stage/action lifecycle status."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    COMPLETED = "completed"
    FAILED = "failed"


class RunKernelTransitionError(ValueError):
    """Raised when an observation does not match the authorized transition."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text[:limit]


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_text(key, limit=100)
            if not key_text:
                continue
            if key_text.casefold() in _SENSITIVE_KEYS:
                out[key_text] = "[redacted]"
            else:
                out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        ordered = list(value)
        if isinstance(value, (set, frozenset)):
            ordered = sorted(ordered, key=str)
        return [_json_safe(item, depth=depth + 1) for item in ordered[:80]]
    return _clean_text(value, limit=300)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _json_safe(dict(value or {}))
    return dict(safe) if isinstance(safe, Mapping) else {}


@dataclass(frozen=True, slots=True)
class AuthorizedAction:
    """One bounded action RunKernel authorizes an executor/adapter to consume."""

    action_id: str
    run_id: str
    stage: str
    action_type: ActionType
    reason: str
    inputs: Mapping[str, Any]
    expected_observation_type: ObservationType
    sequence: int

    def __post_init__(self) -> None:
        if not _clean_text(self.action_id, limit=120):
            raise ValueError("authorized action requires action_id")
        if not _clean_text(self.run_id, limit=120):
            raise ValueError("authorized action requires run_id")
        if not _clean_text(self.stage, limit=120):
            raise ValueError("authorized action requires stage")
        if int(self.sequence or 0) <= 0:
            raise ValueError("authorized action sequence must be positive")
        object.__setattr__(self, "action_type", ActionType(self.action_type))
        object.__setattr__(
            self,
            "expected_observation_type",
            ObservationType(self.expected_observation_type),
        )
        object.__setattr__(self, "inputs", _safe_mapping(self.inputs))

    def validate(
        self,
        *,
        action_type: ActionType | str,
        stage: str,
        expected_observation_type: ObservationType | str | None = None,
    ) -> None:
        expected_action_type = ActionType(action_type)
        if self.action_type is not expected_action_type:
            raise ValueError(
                f"authorized action type {self.action_type.value!r} does not match "
                f"{expected_action_type.value!r}"
            )
        if self.stage != stage:
            raise ValueError(
                f"authorized action stage {self.stage!r} does not match {stage!r}"
            )
        if expected_observation_type is not None:
            expected = ObservationType(expected_observation_type)
            if self.expected_observation_type is not expected:
                raise ValueError(
                    "authorized action expected observation type "
                    f"{self.expected_observation_type.value!r} does not match "
                    f"{expected.value!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "run_id": self.run_id,
            "stage": self.stage,
            "action_type": self.action_type.value,
            "reason": self.reason,
            "inputs": _safe_mapping(self.inputs),
            "expected_observation_type": self.expected_observation_type.value,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class Observation:
    """Facts returned by a bounded executor for exactly one AuthorizedAction."""

    observation_id: str
    run_id: str
    action_id: str
    stage: str
    observation_type: ObservationType
    status: RunStageStatus
    payload: Mapping[str, Any]
    sequence: int

    def __post_init__(self) -> None:
        if not _clean_text(self.observation_id, limit=120):
            raise ValueError("observation requires observation_id")
        if not _clean_text(self.run_id, limit=120):
            raise ValueError("observation requires run_id")
        if not _clean_text(self.action_id, limit=120):
            raise ValueError("observation requires action_id")
        if not _clean_text(self.stage, limit=120):
            raise ValueError("observation requires stage")
        if int(self.sequence or 0) <= 0:
            raise ValueError("observation sequence must be positive")
        object.__setattr__(self, "observation_type", ObservationType(self.observation_type))
        object.__setattr__(self, "status", RunStageStatus(self.status))
        object.__setattr__(self, "payload", _safe_mapping(self.payload))

    @classmethod
    def from_action(
        cls,
        action: AuthorizedAction,
        *,
        observation_type: ObservationType | str,
        status: RunStageStatus | str,
        payload: Mapping[str, Any] | None = None,
    ) -> "Observation":
        return cls(
            observation_id=f"{action.action_id}:observation",
            run_id=action.run_id,
            action_id=action.action_id,
            stage=action.stage,
            observation_type=ObservationType(observation_type),
            status=RunStageStatus(status),
            payload=dict(payload or {}),
            sequence=action.sequence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "run_id": self.run_id,
            "action_id": self.action_id,
            "stage": self.stage,
            "observation_type": self.observation_type.value,
            "status": self.status.value,
            "payload": _safe_mapping(self.payload),
            "sequence": self.sequence,
        }


@dataclass(slots=True)
class RunState:
    """Canonical run state for stages migrated to RunKernel."""

    run_id: str
    request_id: str
    request: Mapping[str, Any] = field(default_factory=dict)
    stage_statuses: dict[str, RunStageStatus] = field(default_factory=dict)
    action_statuses: dict[str, RunStageStatus] = field(default_factory=dict)
    issued_actions: dict[str, AuthorizedAction] = field(default_factory=dict)
    reduced_action_ids: set[str] = field(default_factory=set)
    observations: list[Observation] = field(default_factory=list)
    projections: dict[str, dict[str, Any]] = field(default_factory=dict)
    next_action_sequence: int = 1
    next_observation_sequence: int = 1

    def __post_init__(self) -> None:
        if not _clean_text(self.run_id, limit=120):
            raise ValueError("run state requires run_id")
        if not _clean_text(self.request_id, limit=120):
            raise ValueError("run state requires request_id")
        self.request = _safe_mapping(self.request)

    def to_trace_projection(self) -> "KernelTraceProjection":
        return KernelTraceProjection(
            run_id=self.run_id,
            request_id=self.request_id,
            request=_safe_mapping(self.request),
            stage_statuses={
                stage: status.value for stage, status in self.stage_statuses.items()
            },
            action_statuses={
                action_id: status.value
                for action_id, status in self.action_statuses.items()
            },
            actions=[action.to_dict() for action in self.issued_actions.values()],
            observations=[observation.to_dict() for observation in self.observations],
            projections=deepcopy(self.projections),
            next_action_sequence=self.next_action_sequence,
            next_observation_sequence=self.next_observation_sequence,
        )


@dataclass(frozen=True, slots=True)
class KernelTraceProjection:
    """Trace/export view derived only from RunState."""

    run_id: str
    request_id: str
    request: Mapping[str, Any]
    stage_statuses: Mapping[str, str]
    action_statuses: Mapping[str, str]
    actions: Sequence[Mapping[str, Any]]
    observations: Sequence[Mapping[str, Any]]
    projections: Mapping[str, Any]
    next_action_sequence: int
    next_observation_sequence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "request": _safe_mapping(self.request),
            "stage_statuses": dict(self.stage_statuses),
            "action_statuses": dict(self.action_statuses),
            "actions": [_safe_mapping(action) for action in self.actions],
            "observations": [
                _safe_mapping(observation) for observation in self.observations
            ],
            "projections": _safe_mapping(self.projections),
            "next_action_sequence": self.next_action_sequence,
            "next_observation_sequence": self.next_observation_sequence,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {RUN_KERNEL_TRACE_KEY: self.to_dict()}


class RunKernel:
    """Small runtime-consumed authority spine for migrated stages."""

    def __init__(self, state: RunState) -> None:
        self.state = state

    @classmethod
    def start(
        cls,
        *,
        run_id: str,
        request_id: str,
        request: Mapping[str, Any] | None = None,
    ) -> "RunKernel":
        return cls(
            RunState(
                run_id=run_id,
                request_id=request_id,
                request=dict(request or {}),
            )
        )

    def authorize(
        self,
        *,
        stage: str,
        action_type: ActionType | str,
        reason: str,
        inputs: Mapping[str, Any] | None,
        expected_observation_type: ObservationType | str,
    ) -> AuthorizedAction:
        action_type_value = ActionType(action_type)
        observation_type_value = ObservationType(expected_observation_type)
        sequence = self.state.next_action_sequence
        action = AuthorizedAction(
            action_id=f"{self.state.run_id}:action:{sequence}:{action_type_value.value}",
            run_id=self.state.run_id,
            stage=stage,
            action_type=action_type_value,
            reason=reason,
            inputs=dict(inputs or {}),
            expected_observation_type=observation_type_value,
            sequence=sequence,
        )
        self.state.issued_actions[action.action_id] = action
        self.state.action_statuses[action.action_id] = RunStageStatus.AUTHORIZED
        self.state.stage_statuses[stage] = RunStageStatus.AUTHORIZED
        self.state.next_action_sequence += 1
        return action

    def authorize_route_request(
        self,
        *,
        reason: str = "route_request_before_model_execution",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=ROUTE_REQUEST_STAGE,
            action_type=ActionType.ROUTE_REQUEST,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.ROUTE_RESULT,
        )

    def authorize_query_plan_admission(
        self,
        *,
        reason: str = "query_plan_admission_before_queryplan_consumption",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=QUERY_PLAN_ADMISSION_STAGE,
            action_type=ActionType.QUERY_PLAN_ADMISSION,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.QUERY_PLAN_ADMITTED,
        )

    def authorize_query_production(
        self,
        *,
        reason: str = "query_production_before_candidate_generation",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=QUERY_PRODUCTION_STAGE,
            action_type=ActionType.QUERY_PRODUCTION,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.QUERY_CANDIDATES_PRODUCED,
        )

    def authorize_main_retrieval_pass(
        self,
        *,
        reason: str = "main_retrieval_scheduling_dispatch",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=MAIN_RETRIEVAL_STAGE,
            action_type=ActionType.MAIN_RETRIEVAL_PASS,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
        )

    def authorize_retrieval_stop_checkpoint(
        self,
        *,
        reason: str = "retrieval_stop_continue_checkpoint",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=RETRIEVAL_STOP_CHECKPOINT_STAGE,
            action_type=ActionType.RETRIEVAL_STOP_CHECKPOINT,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.RETRIEVAL_STOP_DECISION,
        )

    def reduce(self, observation: Observation) -> RunState:
        action = self.state.issued_actions.get(observation.action_id)
        if action is None:
            raise RunKernelTransitionError(
                f"observation {observation.observation_id!r} has no matching issued action"
            )
        if observation.run_id != self.state.run_id or observation.run_id != action.run_id:
            raise RunKernelTransitionError("observation run_id does not match RunKernel/action")
        if observation.action_id != action.action_id:
            raise RunKernelTransitionError("observation action_id does not match authorized action")
        if observation.stage != action.stage:
            raise RunKernelTransitionError(
                f"observation stage {observation.stage!r} does not match action stage {action.stage!r}"
            )
        if observation.observation_type is not action.expected_observation_type:
            raise RunKernelTransitionError(
                "observation type "
                f"{observation.observation_type.value!r} does not match expected "
                f"{action.expected_observation_type.value!r}"
            )
        if observation.sequence != action.sequence:
            raise RunKernelTransitionError("observation sequence does not match action sequence")
        if action.action_id in self.state.reduced_action_ids:
            raise RunKernelTransitionError("authorized action was already reduced")
        if observation.sequence != self.state.next_observation_sequence:
            raise RunKernelTransitionError(
                "observation reduced out of order: "
                f"expected sequence {self.state.next_observation_sequence}, "
                f"got {observation.sequence}"
            )

        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = observation.status
        self.state.stage_statuses[action.stage] = observation.status
        self.state.projections[action.stage] = _safe_mapping(observation.payload)
        self.state.observations.append(observation)
        self.state.next_observation_sequence += 1
        return self.state

    def trace_projection(self) -> KernelTraceProjection:
        return self.state.to_trace_projection()

    def to_trace_fragment(self) -> dict[str, Any]:
        return self.trace_projection().to_trace_fragment()


def validate_authorized_action(
    action: AuthorizedAction | None,
    *,
    action_type: ActionType | str,
    stage: str,
    expected_observation_type: ObservationType | str | None = None,
) -> AuthorizedAction:
    if not isinstance(action, AuthorizedAction):
        raise ValueError("executor requires an AuthorizedAction")
    action.validate(
        action_type=action_type,
        stage=stage,
        expected_observation_type=expected_observation_type,
    )
    return action


__all__ = [
    "MAIN_RETRIEVAL_STAGE",
    "QUERY_PRODUCTION_STAGE",
    "QUERY_PLAN_ADMISSION_STAGE",
    "RETRIEVAL_STOP_CHECKPOINT_STAGE",
    "ROUTE_REQUEST_STAGE",
    "RUN_KERNEL_TRACE_KEY",
    "ActionType",
    "AuthorizedAction",
    "KernelTraceProjection",
    "Observation",
    "ObservationType",
    "RunKernel",
    "RunKernelTransitionError",
    "RunStageStatus",
    "RunState",
    "validate_authorized_action",
]
