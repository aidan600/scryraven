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

from core.evidence_ledger import EvidenceLedger

RUN_KERNEL_TRACE_KEY = "run_kernel"

ROUTE_REQUEST_STAGE = "route_request"
QUERY_PRODUCTION_STAGE = "query_production"
QUERY_PLAN_ADMISSION_STAGE = "query_plan_admission"
RUN_CONTRACT_STAGE = "run_contract"
SEARCH_WORK_PLAN_CONSTRUCTION_STAGE = "search_work_plan_construction"
MAIN_RETRIEVAL_STAGE = "main_retrieval"
RETRIEVAL_STOP_CHECKPOINT_STAGE = "retrieval_stop_checkpoint"
EVIDENCE_LEDGER_STAGE = "evidence_ledger"
SEARCH_JUDGMENT_STAGE = "search_judgment"
SUFFICIENCY_JUDGMENT_STAGE = "sufficiency_judgment"
FINAL_ANSWER_PACKET_STAGE = "final_answer_packet"
AUTHOR_EXECUTION_STAGE = "author_execution"

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
    RUN_CONTRACT_SYNTHESIZE = "run_contract_synthesize"
    SEARCH_WORK_PLAN_CONSTRUCT = "search_work_plan_construct"
    QUERY_PRODUCTION = "query_production"
    QUERY_PLAN_ADMISSION = "query_plan_admission"
    MAIN_RETRIEVAL_PASS = "main_retrieval_pass"
    RETRIEVAL_STOP_CHECKPOINT = "retrieval_stop_checkpoint"
    EVIDENCE_LEDGER_REDUCE = "evidence_ledger_reduce"
    SEARCH_JUDGMENT_DECIDE = "search_judgment_decide"
    SUFFICIENCY_JUDGMENT_DECIDE = "sufficiency_judgment_decide"
    FINAL_ANSWER_PACKET_PREPARE = "final_answer_packet_prepare"
    AUTHOR_EXECUTE = "author_execute"


class ObservationType(str, Enum):
    """Observation vocabulary returned by bounded executors/adapters."""

    ROUTE_RESULT = "route_result"
    RUN_CONTRACT_SYNTHESIZED = "run_contract_synthesized"
    SEARCH_WORK_PLAN_CONSTRUCTED = "search_work_plan_constructed"
    QUERY_CANDIDATES_PRODUCED = "query_candidates_produced"
    QUERY_PLAN_ADMITTED = "query_plan_admitted"
    RETRIEVAL_PASS_RESULT = "retrieval_pass_result"
    RETRIEVAL_STOP_DECISION = "retrieval_stop_decision"
    EVIDENCE_CUSTODY_OBSERVED = "evidence_custody_observed"
    SEARCH_JUDGMENT_DECIDED = "search_judgment_decided"
    SUFFICIENCY_JUDGMENT_DECIDED = "sufficiency_judgment_decided"
    FINAL_ANSWER_PACKET_PREPARED = "final_answer_packet_prepared"
    AUTHOR_OUTPUT_OBSERVED = "author_output_observed"


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


def _validation_status(validation: Mapping[str, Any]) -> str | None:
    status = validation.get("status")
    if status:
        return str(status)
    ok = validation.get("ok")
    if ok is True:
        return "ok"
    if ok is False:
        return "errors"
    plan_validation = validation.get("search_work_plan")
    if isinstance(plan_validation, Mapping):
        if plan_validation.get("ok") is True:
            return "ok"
        if plan_validation.get("ok") is False:
            return "errors"
    return None


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
    run_contract: dict[str, Any] = field(default_factory=dict)
    run_contract_projection: dict[str, Any] = field(default_factory=dict)
    run_contract_validation: dict[str, Any] = field(default_factory=dict)
    search_work_plan: dict[str, Any] = field(default_factory=dict)
    search_work_plan_projection: dict[str, Any] = field(default_factory=dict)
    search_work_plan_validation: dict[str, Any] = field(default_factory=dict)
    evidence_ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    search_judgment: dict[str, Any] = field(default_factory=dict)
    search_judgment_projection: dict[str, Any] = field(default_factory=dict)
    search_judgment_history: list[dict[str, Any]] = field(default_factory=list)
    sufficiency_judgment: dict[str, Any] = field(default_factory=dict)
    sufficiency_judgment_projection: dict[str, Any] = field(default_factory=dict)
    sufficiency_judgment_history: list[dict[str, Any]] = field(default_factory=list)
    final_answer_packet: dict[str, Any] = field(default_factory=dict)
    author_observation: dict[str, Any] = field(default_factory=dict)
    final_answer_outcome: dict[str, Any] = field(default_factory=dict)
    final_answer_authority_projection: dict[str, Any] = field(default_factory=dict)
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
            run_contract=deepcopy(self.run_contract),
            run_contract_projection=deepcopy(self.run_contract_projection),
            run_contract_validation=deepcopy(self.run_contract_validation),
            search_work_plan=deepcopy(self.search_work_plan),
            search_work_plan_projection=deepcopy(self.search_work_plan_projection),
            search_work_plan_validation=deepcopy(self.search_work_plan_validation),
            evidence_ledger=self.evidence_ledger.to_projection().to_dict(),
            search_judgment=deepcopy(self.search_judgment),
            search_judgment_projection=deepcopy(self.search_judgment_projection),
            search_judgment_history=deepcopy(self.search_judgment_history),
            sufficiency_judgment=deepcopy(self.sufficiency_judgment),
            sufficiency_judgment_projection=deepcopy(
                self.sufficiency_judgment_projection
            ),
            sufficiency_judgment_history=deepcopy(
                self.sufficiency_judgment_history
            ),
            final_answer_packet=deepcopy(self.final_answer_packet),
            author_observation=deepcopy(self.author_observation),
            final_answer_outcome=deepcopy(self.final_answer_outcome),
            final_answer_authority_projection=deepcopy(
                self.final_answer_authority_projection
            ),
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
    run_contract: Mapping[str, Any]
    run_contract_projection: Mapping[str, Any]
    run_contract_validation: Mapping[str, Any]
    search_work_plan: Mapping[str, Any]
    search_work_plan_projection: Mapping[str, Any]
    search_work_plan_validation: Mapping[str, Any]
    evidence_ledger: Mapping[str, Any]
    search_judgment: Mapping[str, Any]
    search_judgment_projection: Mapping[str, Any]
    search_judgment_history: Sequence[Mapping[str, Any]]
    sufficiency_judgment: Mapping[str, Any]
    sufficiency_judgment_projection: Mapping[str, Any]
    sufficiency_judgment_history: Sequence[Mapping[str, Any]]
    final_answer_packet: Mapping[str, Any]
    author_observation: Mapping[str, Any]
    final_answer_outcome: Mapping[str, Any]
    final_answer_authority_projection: Mapping[str, Any]
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
            "run_contract": _safe_mapping(self.run_contract),
            "run_contract_projection": _safe_mapping(self.run_contract_projection),
            "run_contract_validation": _safe_mapping(self.run_contract_validation),
            "search_work_plan": _safe_mapping(self.search_work_plan),
            "search_work_plan_projection": _safe_mapping(
                self.search_work_plan_projection
            ),
            "search_work_plan_validation": _safe_mapping(
                self.search_work_plan_validation
            ),
            "evidence_ledger": _safe_mapping(self.evidence_ledger),
            "search_judgment": _safe_mapping(self.search_judgment),
            "search_judgment_projection": _safe_mapping(
                self.search_judgment_projection
            ),
            "search_judgment_history": [
                _safe_mapping(item) for item in self.search_judgment_history
            ],
            "sufficiency_judgment": _safe_mapping(self.sufficiency_judgment),
            "sufficiency_judgment_projection": _safe_mapping(
                self.sufficiency_judgment_projection
            ),
            "sufficiency_judgment_history": [
                _safe_mapping(item) for item in self.sufficiency_judgment_history
            ],
            "final_answer_packet": _safe_mapping(self.final_answer_packet),
            "author_observation": _safe_mapping(self.author_observation),
            "final_answer_outcome": _safe_mapping(self.final_answer_outcome),
            "final_answer_authority_projection": _safe_mapping(
                self.final_answer_authority_projection
            ),
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

    def authorize_run_contract_synthesis(
        self,
        *,
        reason: str = "run_authority_contract_synthesis_before_query_production",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=RUN_CONTRACT_STAGE,
            action_type=ActionType.RUN_CONTRACT_SYNTHESIZE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
        )

    def authorize_search_work_plan_construction(
        self,
        *,
        reason: str = "search_work_plan_shadow_construction_after_run_contract",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.run_contract_projection:
            raise RunKernelTransitionError(
                "SearchWorkPlan construction requires a reduced RunAuthority contract"
            )
        merged_inputs = {
            "run_contract_ref": {
                "contract_id": self.state.run_contract_projection.get("contract_id"),
                "schema_version": self.state.run_contract_projection.get(
                    "schema_version"
                ),
            },
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
            action_type=ActionType.SEARCH_WORK_PLAN_CONSTRUCT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED,
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

    def authorize_evidence_ledger_reduction(
        self,
        *,
        reason: str = "evidence_custody_observation_reduction",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=EVIDENCE_LEDGER_STAGE,
            action_type=ActionType.EVIDENCE_LEDGER_REDUCE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.EVIDENCE_CUSTODY_OBSERVED,
        )

    def authorize_search_judgment(
        self,
        *,
        reason: str = "run_authority_iterative_search_judgment",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.run_contract_projection:
            raise RunKernelTransitionError(
                "search judgment requires a reduced RunAuthority contract"
            )
        if self.state.evidence_ledger.to_projection().to_dict().get(
            "requirement_count",
            0,
        ) <= 0:
            raise RunKernelTransitionError(
                "search judgment requires a reduced EvidenceLedger projection"
            )
        return self.authorize(
            stage=SEARCH_JUDGMENT_STAGE,
            action_type=ActionType.SEARCH_JUDGMENT_DECIDE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.SEARCH_JUDGMENT_DECIDED,
        )

    def authorize_sufficiency_judgment(
        self,
        *,
        reason: str = "run_authority_final_sufficiency_judgment",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.run_contract_projection:
            raise RunKernelTransitionError(
                "sufficiency judgment requires a reduced RunAuthority contract"
            )
        if self.state.evidence_ledger.to_projection().to_dict().get(
            "requirement_count",
            0,
        ) <= 0:
            raise RunKernelTransitionError(
                "sufficiency judgment requires a reduced EvidenceLedger projection"
            )
        return self.authorize(
            stage=SUFFICIENCY_JUDGMENT_STAGE,
            action_type=ActionType.SUFFICIENCY_JUDGMENT_DECIDE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.SUFFICIENCY_JUDGMENT_DECIDED,
        )

    def authorize_final_answer_packet_prepare(
        self,
        *,
        reason: str = "final_answer_packet_preparation_before_author_execution",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=FINAL_ANSWER_PACKET_STAGE,
            action_type=ActionType.FINAL_ANSWER_PACKET_PREPARE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
        )

    def authorize_author_execution(
        self,
        *,
        reason: str = "author_execution_from_final_answer_packet_payload",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "author execution requires a reduced FinalAnswerPacket"
            )
        payload_ref = self.state.final_answer_authority_projection.get(
            "author_payload_ref",
            {},
        )
        if payload_ref.get("status") != "author_input_ready":
            raise RunKernelTransitionError(
                "author execution requires packet-ready author input payload"
            )
        merged_inputs = {
            "packet_id": self.state.final_answer_packet.get("packet_id"),
            "author_payload_status": payload_ref.get("status"),
            "author_system_prompt_key": payload_ref.get("author_system_prompt_key"),
            "author_effort": payload_ref.get("author_effort"),
            "author_provider": payload_ref.get("author_provider"),
            "author_model": payload_ref.get("author_model"),
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=AUTHOR_EXECUTION_STAGE,
            action_type=ActionType.AUTHOR_EXECUTE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
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
        if action.action_type is ActionType.RUN_CONTRACT_SYNTHESIZE:
            contract_projection = _safe_mapping(
                observation.payload.get("contract_projection")
            )
            if not contract_projection:
                raise RunKernelTransitionError(
                    "run contract synthesis observation requires contract_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            self.state.run_contract = contract_projection
            self.state.run_contract_projection = {
                "owner": "RunKernel.RunAuthorityContract",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "contract_id": contract_projection.get("contract_id"),
                "schema_version": contract_projection.get("schema_version"),
                "synthesis_mode": contract_projection.get("synthesis_mode"),
                "selected_template_ids": contract_projection.get(
                    "selected_template_ids",
                    [],
                ),
                "query_ref": contract_projection.get("query_ref")
                or contract_projection.get("user_query_ref", {}),
                "user_query_ref": contract_projection.get("user_query_ref", {}),
                "selected_depth": contract_projection.get("selected_depth"),
                "source_requirement_summary": contract_projection.get(
                    "source_requirement_summary",
                    [],
                ),
                "source_requirements": contract_projection.get(
                    "source_requirements",
                    [],
                ),
                "inference_policy": contract_projection.get("inference_policy", {}),
                "conflict_policy": contract_projection.get("conflict_policy", {}),
                "numeric_policy": contract_projection.get("numeric_policy", {}),
                "final_posture_policy": contract_projection.get(
                    "final_posture_policy",
                    {},
                ),
                "downstream_hints": contract_projection.get("downstream_hints", {}),
                "validation_status": validation.get("status"),
                "prompt_hash": validation.get("prompt_hash")
                or observation.payload.get("prompt_hash"),
                "prompt_length": validation.get("prompt_length")
                or observation.payload.get("prompt_length"),
                "model_identity": {
                    "provider": validation.get("provider"),
                    "model": validation.get("model"),
                    "effort": validation.get("effort"),
                    "use_reasoning": validation.get("use_reasoning"),
                },
                "prompt_text_retained": False,
                "model_response_text_retained": False,
                "provider_payload_retained": False,
            }
            self.state.run_contract_validation = validation
            self.state.projections[action.stage] = deepcopy(
                self.state.run_contract_projection
            )
        elif action.action_type is ActionType.SEARCH_WORK_PLAN_CONSTRUCT:
            construction_result = _safe_mapping(
                observation.payload.get("construction_result")
            )
            plan_projection = _safe_mapping(
                observation.payload.get("search_work_plan_projection")
            )
            if not plan_projection:
                plan_projection = _safe_mapping(
                    construction_result.get("search_work_plan")
                )
            if not plan_projection:
                raise RunKernelTransitionError(
                    "SearchWorkPlan construction observation requires "
                    "search_work_plan_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            if not validation:
                validation = _safe_mapping(construction_result.get("validation"))
            follow_up_authority = _safe_mapping(
                plan_projection.get("follow_up_authority")
            )
            self.state.search_work_plan = plan_projection
            self.state.search_work_plan_validation = validation
            self.state.search_work_plan_projection = {
                "owner": "RunKernel.SearchWorkPlan",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "construction_id": plan_projection.get("metadata", {}).get(
                    "construction_id"
                )
                or construction_result.get("construction_id"),
                "schema_version": plan_projection.get("schema_version"),
                "planning_posture": plan_projection.get("planning_posture"),
                "requested_mode": plan_projection.get("requested_mode", {}),
                "effective_contract": plan_projection.get("effective_contract", {}),
                "query_shape": plan_projection.get("query_shape", {}),
                "component_count": len(plan_projection.get("components", []) or []),
                "provider_job_count": len(
                    plan_projection.get("provider_jobs", []) or []
                ),
                "quant_work_unit_count": len(
                    plan_projection.get("quant_work_units", []) or []
                ),
                "audit_job_count": len(plan_projection.get("audit_jobs", []) or []),
                "stop_condition_count": len(
                    plan_projection.get("stop_conditions", []) or []
                ),
                "follow_up_permission": follow_up_authority.get("permission"),
                "validation_status": _validation_status(validation),
                "search_work_plan_runtime_consumed": False,
                "runtime_consumed_by_query_plan": False,
                "provider_search_behavior_changed": False,
                "query_plan_behavior_changed": False,
                "prompt_behavior_changed": False,
                "final_answer_behavior_changed": False,
            }
            self.state.projections[action.stage] = deepcopy(
                self.state.search_work_plan_projection
            )
        elif action.action_type is ActionType.EVIDENCE_LEDGER_REDUCE:
            self.state.evidence_ledger.reduce_observation(observation.payload)
            self.state.projections[action.stage] = (
                self.state.evidence_ledger.to_projection().to_dict()
            )
        elif action.action_type is ActionType.SEARCH_JUDGMENT_DECIDE:
            judgment_projection = _safe_mapping(
                observation.payload.get("judgment_projection")
            )
            if not judgment_projection:
                raise RunKernelTransitionError(
                    "search judgment observation requires judgment_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            self.state.search_judgment = judgment_projection
            self.state.search_judgment_projection = {
                "owner": "RunKernel.RunAuthoritySearchJudgment",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": judgment_projection.get("schema_version"),
                "judgment_id": judgment_projection.get("judgment_id"),
                "decision": judgment_projection.get("decision"),
                "mode": judgment_projection.get("mode"),
                "classifications": judgment_projection.get("classifications", []),
                "contract_id": judgment_projection.get("contract_id"),
                "selected_template_ids": judgment_projection.get(
                    "selected_template_ids",
                    [],
                ),
                "satisfaction": judgment_projection.get("satisfaction", {}),
                "gaps": judgment_projection.get("gaps", []),
                "redundancy": judgment_projection.get("redundancy", {}),
                "continuation": judgment_projection.get("continuation", {}),
                "target_source_classes": judgment_projection.get(
                    "target_source_classes",
                    [],
                ),
                "recommended_queries": judgment_projection.get(
                    "recommended_queries",
                    [],
                ),
                "helper_assessments": judgment_projection.get(
                    "helper_assessments",
                    {},
                ),
                "insufficient_posture": judgment_projection.get(
                    "insufficient_posture",
                    {},
                ),
                "rationale": judgment_projection.get("rationale"),
                "validation_status": validation.get("status")
                or judgment_projection.get("validation", {}).get("status"),
                "prompt_hash": validation.get("prompt_hash")
                or observation.payload.get("prompt_hash"),
                "prompt_length": validation.get("prompt_length")
                or observation.payload.get("prompt_length"),
                "model_identity": {
                    "provider": validation.get("provider"),
                    "model": validation.get("model"),
                    "effort": validation.get("effort"),
                    "use_reasoning": validation.get("use_reasoning"),
                },
                "prompt_text_retained": False,
                "model_response_text_retained": False,
                "provider_payload_retained": False,
            }
            self.state.search_judgment_history.append(
                deepcopy(self.state.search_judgment_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.search_judgment_projection
            )
        elif action.action_type is ActionType.SUFFICIENCY_JUDGMENT_DECIDE:
            judgment_projection = _safe_mapping(
                observation.payload.get("judgment_projection")
            )
            if not judgment_projection:
                raise RunKernelTransitionError(
                    "sufficiency judgment observation requires judgment_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            self.state.sufficiency_judgment = judgment_projection
            self.state.sufficiency_judgment_projection = {
                "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": judgment_projection.get("schema_version"),
                "judgment_id": judgment_projection.get("judgment_id"),
                "decision": judgment_projection.get("decision"),
                "mode": judgment_projection.get("mode"),
                "contract_id": judgment_projection.get("contract_id"),
                "selected_template_ids": judgment_projection.get(
                    "selected_template_ids",
                    [],
                ),
                "contract_fulfilled": judgment_projection.get("contract_fulfilled"),
                "required_obligations_satisfied": judgment_projection.get(
                    "required_obligations_satisfied"
                ),
                "missing_required_obligations": judgment_projection.get(
                    "missing_required_obligations",
                    [],
                ),
                "partial_obligations": judgment_projection.get(
                    "partial_obligations",
                    [],
                ),
                "satisfied_obligations": judgment_projection.get(
                    "satisfied_obligations",
                    [],
                ),
                "unresolved_conflicts": judgment_projection.get(
                    "unresolved_conflicts",
                    [],
                ),
                "indirect_inference_claims": judgment_projection.get(
                    "indirect_inference_claims",
                    [],
                ),
                "source_bound_numeric_unknowns": judgment_projection.get(
                    "source_bound_numeric_unknowns",
                    [],
                ),
                "weak_or_thin_evidence": judgment_projection.get(
                    "weak_or_thin_evidence",
                    [],
                ),
                "failure_card_authorized": judgment_projection.get(
                    "failure_card_authorized"
                ),
                "final_answer_allowed": judgment_projection.get(
                    "final_answer_allowed"
                ),
                "final_answer_posture": judgment_projection.get(
                    "final_answer_posture"
                ),
                "mandatory_caveats": judgment_projection.get(
                    "mandatory_caveats",
                    [],
                ),
                "prohibited_upgrades": judgment_projection.get(
                    "prohibited_upgrades",
                    [],
                ),
                "readiness_reasons": judgment_projection.get(
                    "readiness_reasons",
                    [],
                ),
                "final_packet_inputs": judgment_projection.get(
                    "final_packet_inputs",
                    {},
                ),
                "rationale": judgment_projection.get("rationale"),
                "validation_status": validation.get("status")
                or judgment_projection.get("validation", {}).get("status"),
                "prompt_hash": validation.get("prompt_hash")
                or observation.payload.get("prompt_hash"),
                "prompt_length": validation.get("prompt_length")
                or observation.payload.get("prompt_length"),
                "model_identity": {
                    "provider": validation.get("provider"),
                    "model": validation.get("model"),
                    "effort": validation.get("effort"),
                    "use_reasoning": validation.get("use_reasoning"),
                },
                "prompt_text_retained": False,
                "model_response_text_retained": False,
                "provider_payload_retained": False,
            }
            self.state.sufficiency_judgment_history.append(
                deepcopy(self.state.sufficiency_judgment_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.sufficiency_judgment_projection
            )
        elif action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE:
            packet_projection = _safe_mapping(
                observation.payload.get("packet_projection")
            )
            if not packet_projection:
                raise RunKernelTransitionError(
                    "final answer packet observation requires packet_projection"
                )
            author_payload_ref = _safe_mapping(
                observation.payload.get("author_payload_ref")
            )
            self.state.final_answer_packet = packet_projection
            self.state.final_answer_authority_projection = {
                "owner": "RunKernel.FinalAnswerPacket",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "packet_id": packet_projection.get("packet_id"),
                "readiness_status": packet_projection.get("readiness_status"),
                "readiness_reasons": packet_projection.get("readiness_reasons", []),
                "author_payload_ref": author_payload_ref,
                "citation_eligible_source_ids": author_payload_ref.get(
                    "citation_source_ids",
                    [],
                ),
                "missing_source_obligation_count": len(
                    author_payload_ref.get("missing_source_obligations", []) or []
                ),
                "partial_source_obligation_count": len(
                    author_payload_ref.get("partial_source_obligations", []) or []
                ),
                "satisfied_source_obligation_count": len(
                    author_payload_ref.get("satisfied_source_obligations", []) or []
                ),
                "source_bound_numeric_unknown_count": len(
                    author_payload_ref.get("source_bound_numeric_unknowns", []) or []
                ),
                "mandatory_caveat_count": author_payload_ref.get(
                    "mandatory_caveat_count",
                    0,
                ),
                "prohibited_upgrade_count": author_payload_ref.get(
                    "prohibited_upgrade_count",
                    0,
                ),
                "author_authority_payload_ref": author_payload_ref.get(
                    "authority_payload",
                    {},
                ),
            }
            self.state.projections[action.stage] = deepcopy(
                self.state.final_answer_authority_projection
            )
        elif action.action_type is ActionType.AUTHOR_EXECUTE:
            payload = _safe_mapping(observation.payload)
            self.state.author_observation = payload
            self.state.final_answer_outcome = {
                "owner": "RunKernel.AuthorObservation",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "packet_id": payload.get("packet_id"),
                "report_hash": payload.get("report_hash"),
                "report_length": payload.get("report_length"),
                "author_seconds": payload.get("author_seconds"),
                "stream_displayed": payload.get("stream_displayed"),
                "author_provider": payload.get("author_provider"),
                "author_model": payload.get("author_model"),
                "author_effort": payload.get("author_effort"),
                "final_text_included": False,
            }
            self.state.projections[action.stage] = deepcopy(
                self.state.final_answer_outcome
            )
        else:
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
    "AUTHOR_EXECUTION_STAGE",
    "FINAL_ANSWER_PACKET_STAGE",
    "MAIN_RETRIEVAL_STAGE",
    "EVIDENCE_LEDGER_STAGE",
    "SEARCH_JUDGMENT_STAGE",
    "SEARCH_WORK_PLAN_CONSTRUCTION_STAGE",
    "SUFFICIENCY_JUDGMENT_STAGE",
    "RUN_CONTRACT_STAGE",
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
