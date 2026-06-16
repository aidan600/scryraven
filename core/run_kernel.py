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
from core.followup_author_gate_runtime import (
    FOLLOWUP_AUTHOR_GATE_MODE,
    build_followup_author_gate_record,
)
from core.followup_author_gate_runtime import (
    FOLLOWUP_AUTHOR_GATE_STAGE as FOLLOWUP_AUTHOR_GATE_STAGE_NAME,
)
from core.followup_author_observation_runtime import (
    FOLLOWUP_AUTHOR_OBSERVATION_MODE,
    build_followup_author_observation_record,
    derive_followup_author_observation_compliance,
    reject_followup_author_observation_boundary_spoof,
)
from core.followup_author_observation_runtime import (
    FOLLOWUP_AUTHOR_OBSERVATION_STAGE as FOLLOWUP_AUTHOR_OBSERVATION_STAGE_NAME,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
    build_followup_final_answer_packet_record,
    followup_projection_digest,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_ANSWER_PACKET_STAGE as FOLLOWUP_FINAL_ANSWER_PACKET_STAGE_NAME,
)
from core.followup_fixture_boundaries import (
    FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS,
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    build_followup_sufficiency_recheck_record,
    evidence_ledger_custody_summary,
    evidence_ledger_projection_digest,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_STAGE as FOLLOWUP_SUFFICIENCY_RECHECK_STAGE_NAME,
)

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
FOLLOWUP_AUTHORIZATION_STAGE = "followup_authorization_consumption"
FOLLOWUP_EXECUTION_STAGE = "followup_fixture_execution"
FOLLOWUP_EVIDENCE_INTAKE_STAGE = "followup_evidence_intake"
FOLLOWUP_SUFFICIENCY_RECHECK_STAGE = FOLLOWUP_SUFFICIENCY_RECHECK_STAGE_NAME
FOLLOWUP_FINAL_ANSWER_PACKET_STAGE = FOLLOWUP_FINAL_ANSWER_PACKET_STAGE_NAME
FOLLOWUP_AUTHOR_GATE_STAGE = FOLLOWUP_AUTHOR_GATE_STAGE_NAME
FOLLOWUP_AUTHOR_OBSERVATION_STAGE = FOLLOWUP_AUTHOR_OBSERVATION_STAGE_NAME

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

_FOLLOWUP_NO_LIVE_FALSE_FLAGS = FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:]
_FOLLOWUP_EXECUTION_FALSE_FLAGS = (
    "live_provider_call_executed",
    "search_executed",
    "retrieval_executed",
    "fetch_executed",
    "model_called",
    "evidence_ledger_mutated",
)
_FOLLOWUP_INTAKE_FALSE_FLAGS = (
    *_FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    "sufficiency_judgment_rechecked",
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "final_answer_packet_updated",
    "final_answer_behavior_changed",
    "author_prose_behavior_changed",
    "citation_behavior_changed",
)
_FOLLOWUP_RECHECK_FALSE_FLAGS = (
    *_FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "final_answer_packet_updated",
    "final_answer_behavior_changed",
    "author_prose_behavior_changed",
    "citation_behavior_changed",
)
_FOLLOWUP_PACKET_FALSE_FLAGS = (
    *_FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
)
_FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS = (
    *_FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "sufficiency_judgment_rechecked",
    "final_answer_packet_rebuilt",
    "final_answer_packet_updated",
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
)
_FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS = (
    *_FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "sufficiency_judgment_rechecked",
    "final_answer_packet_rebuilt",
    "final_answer_packet_updated",
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    "final_text_included",
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
    FOLLOWUP_AUTHORIZATION_CONSUME = "followup_authorization_consume"
    FOLLOWUP_FIXTURE_EXECUTE = "followup_fixture_execute"
    FOLLOWUP_EVIDENCE_INTAKE = "followup_evidence_intake"
    FOLLOWUP_SUFFICIENCY_RECHECK = "followup_sufficiency_recheck"
    FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE = "followup_final_answer_packet_prepare"
    FOLLOWUP_AUTHOR_GATE = "followup_author_gate"
    FOLLOWUP_AUTHOR_OBSERVATION = "followup_author_observation"


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
    FOLLOWUP_AUTHORIZATION_CONSUMED = "followup_authorization_consumed"
    FOLLOWUP_EXECUTION_OBSERVED = "followup_execution_observed"
    FOLLOWUP_EVIDENCE_INTAKE_OBSERVED = "followup_evidence_intake_observed"
    FOLLOWUP_SUFFICIENCY_RECHECK_OBSERVED = (
        "followup_sufficiency_recheck_observed"
    )
    FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED = (
        "followup_final_answer_packet_prepared"
    )
    FOLLOWUP_AUTHOR_GATE_OBSERVED = "followup_author_gate_observed"
    FOLLOWUP_AUTHOR_OBSERVATION_OBSERVED = (
        "followup_author_observation_observed"
    )


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
    followup_authorization_state: dict[str, Any] = field(default_factory=dict)
    followup_authorization_projection: dict[str, Any] = field(default_factory=dict)
    followup_authorization_history: list[dict[str, Any]] = field(default_factory=list)
    followup_execution_state: dict[str, Any] = field(default_factory=dict)
    followup_execution_projection: dict[str, Any] = field(default_factory=dict)
    followup_execution_history: list[dict[str, Any]] = field(default_factory=list)
    followup_evidence_intake_state: dict[str, Any] = field(default_factory=dict)
    followup_evidence_intake_projection: dict[str, Any] = field(default_factory=dict)
    followup_evidence_intake_history: list[dict[str, Any]] = field(default_factory=list)
    followup_sufficiency_recheck_state: dict[str, Any] = field(default_factory=dict)
    followup_sufficiency_recheck_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_sufficiency_recheck_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_final_answer_packet_state: dict[str, Any] = field(default_factory=dict)
    followup_final_answer_packet_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_final_answer_packet_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_gate_state: dict[str, Any] = field(default_factory=dict)
    followup_author_gate_projection: dict[str, Any] = field(default_factory=dict)
    followup_author_gate_history: list[dict[str, Any]] = field(default_factory=list)
    followup_author_observation_state: dict[str, Any] = field(default_factory=dict)
    followup_author_observation_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_observation_history: list[dict[str, Any]] = field(
        default_factory=list
    )
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
            followup_authorization_state=deepcopy(self.followup_authorization_state),
            followup_authorization_projection=deepcopy(
                self.followup_authorization_projection
            ),
            followup_authorization_history=deepcopy(
                self.followup_authorization_history
            ),
            followup_execution_state=deepcopy(self.followup_execution_state),
            followup_execution_projection=deepcopy(
                self.followup_execution_projection
            ),
            followup_execution_history=deepcopy(self.followup_execution_history),
            followup_evidence_intake_state=deepcopy(
                self.followup_evidence_intake_state
            ),
            followup_evidence_intake_projection=deepcopy(
                self.followup_evidence_intake_projection
            ),
            followup_evidence_intake_history=deepcopy(
                self.followup_evidence_intake_history
            ),
            followup_sufficiency_recheck_state=deepcopy(
                self.followup_sufficiency_recheck_state
            ),
            followup_sufficiency_recheck_projection=deepcopy(
                self.followup_sufficiency_recheck_projection
            ),
            followup_sufficiency_recheck_history=deepcopy(
                self.followup_sufficiency_recheck_history
            ),
            followup_final_answer_packet_state=deepcopy(
                self.followup_final_answer_packet_state
            ),
            followup_final_answer_packet_projection=deepcopy(
                self.followup_final_answer_packet_projection
            ),
            followup_final_answer_packet_history=deepcopy(
                self.followup_final_answer_packet_history
            ),
            followup_author_gate_state=deepcopy(self.followup_author_gate_state),
            followup_author_gate_projection=deepcopy(
                self.followup_author_gate_projection
            ),
            followup_author_gate_history=deepcopy(
                self.followup_author_gate_history
            ),
            followup_author_observation_state=deepcopy(
                self.followup_author_observation_state
            ),
            followup_author_observation_projection=deepcopy(
                self.followup_author_observation_projection
            ),
            followup_author_observation_history=deepcopy(
                self.followup_author_observation_history
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
    followup_authorization_state: Mapping[str, Any]
    followup_authorization_projection: Mapping[str, Any]
    followup_authorization_history: Sequence[Mapping[str, Any]]
    followup_execution_state: Mapping[str, Any]
    followup_execution_projection: Mapping[str, Any]
    followup_execution_history: Sequence[Mapping[str, Any]]
    followup_evidence_intake_state: Mapping[str, Any]
    followup_evidence_intake_projection: Mapping[str, Any]
    followup_evidence_intake_history: Sequence[Mapping[str, Any]]
    followup_sufficiency_recheck_state: Mapping[str, Any]
    followup_sufficiency_recheck_projection: Mapping[str, Any]
    followup_sufficiency_recheck_history: Sequence[Mapping[str, Any]]
    followup_final_answer_packet_state: Mapping[str, Any]
    followup_final_answer_packet_projection: Mapping[str, Any]
    followup_final_answer_packet_history: Sequence[Mapping[str, Any]]
    followup_author_gate_state: Mapping[str, Any]
    followup_author_gate_projection: Mapping[str, Any]
    followup_author_gate_history: Sequence[Mapping[str, Any]]
    followup_author_observation_state: Mapping[str, Any]
    followup_author_observation_projection: Mapping[str, Any]
    followup_author_observation_history: Sequence[Mapping[str, Any]]
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
            "followup_authorization_state": _safe_mapping(
                self.followup_authorization_state
            ),
            "followup_authorization_projection": _safe_mapping(
                self.followup_authorization_projection
            ),
            "followup_authorization_history": [
                _safe_mapping(item) for item in self.followup_authorization_history
            ],
            "followup_execution_state": _safe_mapping(self.followup_execution_state),
            "followup_execution_projection": _safe_mapping(
                self.followup_execution_projection
            ),
            "followup_execution_history": [
                _safe_mapping(item) for item in self.followup_execution_history
            ],
            "followup_evidence_intake_state": _safe_mapping(
                self.followup_evidence_intake_state
            ),
            "followup_evidence_intake_projection": _safe_mapping(
                self.followup_evidence_intake_projection
            ),
            "followup_evidence_intake_history": [
                _safe_mapping(item) for item in self.followup_evidence_intake_history
            ],
            "followup_sufficiency_recheck_state": _safe_mapping(
                self.followup_sufficiency_recheck_state
            ),
            "followup_sufficiency_recheck_projection": _safe_mapping(
                self.followup_sufficiency_recheck_projection
            ),
            "followup_sufficiency_recheck_history": [
                _safe_mapping(item)
                for item in self.followup_sufficiency_recheck_history
            ],
            "followup_final_answer_packet_state": _safe_mapping(
                self.followup_final_answer_packet_state
            ),
            "followup_final_answer_packet_projection": _safe_mapping(
                self.followup_final_answer_packet_projection
            ),
            "followup_final_answer_packet_history": [
                _safe_mapping(item)
                for item in self.followup_final_answer_packet_history
            ],
            "followup_author_gate_state": _safe_mapping(
                self.followup_author_gate_state
            ),
            "followup_author_gate_projection": _safe_mapping(
                self.followup_author_gate_projection
            ),
            "followup_author_gate_history": [
                _safe_mapping(item) for item in self.followup_author_gate_history
            ],
            "followup_author_observation_state": _safe_mapping(
                self.followup_author_observation_state
            ),
            "followup_author_observation_projection": _safe_mapping(
                self.followup_author_observation_projection
            ),
            "followup_author_observation_history": [
                _safe_mapping(item)
                for item in self.followup_author_observation_history
            ],
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

    def authorize_followup_authorization_consumption(
        self,
        *,
        reason: str = "ag96i2a_followup_checkpoint_runtime_consumption",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=FOLLOWUP_AUTHORIZATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHORIZATION_CONSUME,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.FOLLOWUP_AUTHORIZATION_CONSUMED,
        )

    def authorize_followup_fixture_execution(
        self,
        *,
        candidate_id: str,
        reason: str = "ag96i2b_followup_fixture_execution_observation",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_authorization_state:
            raise RunKernelTransitionError(
                "follow-up fixture execution requires reduced follow-up authorization state"
            )
        candidate = _followup_sealed_candidate(
            self.state.followup_authorization_state,
            candidate_id,
        )
        merged_inputs = {
            **dict(inputs or {}),
            "followup_authorization_consumption_id": (
                self.state.followup_authorization_state.get("consumption_id")
            ),
            "sealed_candidate_id": candidate.get("candidate_id"),
            "fixture_execution_mode": "fixture_only",
            "provider_job_kind": candidate.get("provider_job_kind"),
            "provider_execution_licensed": False,
            "requirement_ids": candidate.get("requirement_ids", []),
        }
        if merged_inputs.get("fixture_execution_mode") != "fixture_only":
            raise RunKernelTransitionError(
                "follow-up fixture execution only authorizes fixture_only mode"
            )
        return self.authorize(
            stage=FOLLOWUP_EXECUTION_STAGE,
            action_type=ActionType.FOLLOWUP_FIXTURE_EXECUTE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.FOLLOWUP_EXECUTION_OBSERVED,
        )

    def authorize_followup_evidence_intake(
        self,
        *,
        reason: str = "ag96i2c_followup_fixture_evidence_ledger_intake",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_execution_state:
            raise RunKernelTransitionError(
                "follow-up evidence intake requires reduced follow-up execution state"
            )
        execution_state = self.state.followup_execution_state
        merged_inputs = {
            **dict(inputs or {}),
            "followup_authorization_consumption_id": execution_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
            "followup_execution_id": execution_state.get("execution_id"),
            "execution_id": execution_state.get("execution_id"),
            "followup_execution_observation_id": execution_state.get(
                "observation_id"
            ),
            "observation_id": execution_state.get("observation_id"),
            "fixture_execution_mode": execution_state.get("fixture_execution_mode"),
            "provider_job_kind": execution_state.get("provider_job_kind"),
            "component_id": execution_state.get("component_id"),
            "source_obligation_id": execution_state.get("source_obligation_id"),
            "requirement_ids": execution_state.get("requirement_ids", []),
            "expected_source_classes": execution_state.get(
                "expected_source_classes",
                [],
            ),
            "result_status": execution_state.get("result_status"),
            "bridge_only": execution_state.get("bridge_only"),
            "provider_execution_licensed": False,
            "evidence_ledger_intake_mode": "fixture_only_followup_intake",
            "expected_observation_record_type": (
                "followup_evidence_intake_consumption_record"
            ),
        }
        if merged_inputs.get("fixture_execution_mode") != "fixture_only":
            raise RunKernelTransitionError(
                "follow-up evidence intake only authorizes fixture_only execution state"
            )
        return self.authorize(
            stage=FOLLOWUP_EVIDENCE_INTAKE_STAGE,
            action_type=ActionType.FOLLOWUP_EVIDENCE_INTAKE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_EVIDENCE_INTAKE_OBSERVED
            ),
        )

    def authorize_followup_sufficiency_recheck(
        self,
        *,
        reason: str = "ag96i2d_followup_fixture_sufficiency_recheck",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_evidence_intake_state:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires reduced follow-up "
                "EvidenceLedger intake state"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires canonical intake state"
            )
        if intake_state.get("evidence_ledger_intake_mode") != (
            "fixture_only_followup_intake"
        ):
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires fixture-only intake state"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires canonical EvidenceLedger"
            )
        if int(ledger_projection.get("requirement_count") or 0) <= 0:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires EvidenceLedger requirements"
            )
        canonical_inputs = {
            "run_id": intake_state.get("run_id"),
            "checkpoint_id": intake_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": intake_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": intake_state.get("sealed_candidate_id"),
            "followup_execution_id": intake_state.get("followup_execution_id"),
            "execution_id": intake_state.get("execution_id"),
            "followup_execution_observation_id": intake_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": intake_state.get("intake_id"),
            "intake_id": intake_state.get("intake_id"),
            "followup_evidence_intake_observation_id": intake_state.get(
                "observation_id"
            ),
            "provider_job_kind": intake_state.get("provider_job_kind"),
            "component_id": intake_state.get("component_id"),
            "source_obligation_id": intake_state.get("source_obligation_id"),
            "requirement_ids": intake_state.get("requirement_ids", []),
            "expected_source_classes": intake_state.get(
                "expected_source_classes",
                [],
            ),
            "result_status": intake_state.get("result_status"),
            "bridge_only": intake_state.get("bridge_only"),
            "fixture_execution_mode": intake_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": intake_state.get(
                "evidence_ledger_intake_mode"
            ),
            "provider_execution_licensed": False,
            "sufficiency_recheck_mode": FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "evidence_ledger_custody_summary": evidence_ledger_custody_summary(
                ledger_projection
            ),
            "final_answer_packet_deferred": True,
            "author_activation_allowed": False,
            "citation_behavior_changed": False,
            "citation_eligible": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_sufficiency_recheck_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
            action_type=ActionType.FOLLOWUP_SUFFICIENCY_RECHECK,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_SUFFICIENCY_RECHECK_OBSERVED
            ),
        )

    def authorize_followup_final_answer_packet_prepare(
        self,
        *,
        reason: str = "ag96i2e_followup_fixture_final_answer_packet_prepare",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_sufficiency_recheck_state:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires reduced "
                "follow-up sufficiency recheck state"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "recheck state"
            )
        if recheck_state.get("sufficiency_recheck_mode") != (
            FOLLOWUP_SUFFICIENCY_RECHECK_MODE
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires fixture-only "
                "sufficiency recheck mode"
            )
        if recheck_state.get("final_answer_packet_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires recheck packet "
                "deferral posture"
            )
        if recheck_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires Author closed"
            )
        if self.state.followup_final_answer_packet_state.get("recheck_id") == (
            recheck_state.get("recheck_id")
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket already prepared for this recheck"
            )
        if not self.state.sufficiency_judgment_projection:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "SufficiencyJudgment projection"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires "
                "RunAuthority SufficiencyJudgment"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires EvidenceLedger "
                "projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "EvidenceLedger"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "EvidenceLedger intake state"
            )
        canonical_inputs = {
            "run_id": recheck_state.get("run_id"),
            "checkpoint_id": recheck_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": recheck_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": recheck_state.get("sealed_candidate_id"),
            "followup_execution_id": recheck_state.get("followup_execution_id"),
            "execution_id": recheck_state.get("execution_id"),
            "followup_execution_observation_id": recheck_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": recheck_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": recheck_state.get("intake_id"),
            "followup_evidence_intake_observation_id": recheck_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": recheck_state.get("recheck_id"),
            "recheck_id": recheck_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": recheck_state.get(
                "observation_id"
            ),
            "provider_job_kind": recheck_state.get("provider_job_kind"),
            "component_id": recheck_state.get("component_id"),
            "source_obligation_id": recheck_state.get("source_obligation_id"),
            "requirement_ids": recheck_state.get("requirement_ids", []),
            "expected_source_classes": list(
                _followup_expected_source_classes(recheck_state)
            ),
            "fixture_execution_mode": recheck_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": recheck_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": recheck_state.get(
                "sufficiency_recheck_mode"
            ),
            "provider_execution_licensed": False,
            "final_answer_packet_mode": FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "evidence_ledger_custody_summary": evidence_ledger_custody_summary(
                ledger_projection
            ),
            "final_answer_packet_prepared": False,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_final_answer_packet_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
            action_type=ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED
            ),
        )

    def authorize_followup_author_gate(
        self,
        *,
        reason: str = "ag96i2f_followup_fixture_author_gate_consumption",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_final_answer_packet_state:
            raise RunKernelTransitionError(
                "follow-up Author gate requires reduced follow-up FinalAnswerPacket state"
            )
        packet_state = self.state.followup_final_answer_packet_state
        if packet_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical FinalAnswerPacket state"
            )
        if packet_state.get("final_answer_packet_mode") != (
            FOLLOWUP_FINAL_ANSWER_PACKET_MODE
        ):
            raise RunKernelTransitionError(
                "follow-up Author gate requires fixture-only FinalAnswerPacket mode"
            )
        if packet_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author activation closed"
            )
        if packet_state.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires deferred Author execution"
            )
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical FinalAnswerPacket"
            )
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical FinalAnswerPacket "
                "authority projection"
            )
        authority = self.state.final_answer_authority_projection
        if authority.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "follow-up Author gate requires RunKernel FinalAnswerPacket owner"
            )
        if authority.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical packet authority"
            )
        if authority.get("packet_id") != self.state.final_answer_packet.get(
            "packet_id"
        ):
            raise RunKernelTransitionError(
                "follow-up Author gate requires packet/projection packet_id match"
            )
        if authority.get("packet_id") != packet_state.get("packet_id"):
            raise RunKernelTransitionError(
                "follow-up Author gate requires follow-up packet_id match"
            )
        payload_ref = _safe_mapping(authority.get("author_payload_ref"))
        if payload_ref.get("status") != "author_execution_deferred":
            raise RunKernelTransitionError(
                "follow-up Author gate requires deferred Author payload"
            )
        if authority.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author activation closed"
            )
        if authority.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author execution deferred"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author execution not yet reduced"
            )
        if self.state.followup_author_gate_state.get(
            "packet_preparation_id"
        ) == packet_state.get("packet_preparation_id"):
            raise RunKernelTransitionError(
                "follow-up Author gate already consumed this packet"
            )
        canonical_inputs = {
            "run_id": packet_state.get("run_id"),
            "checkpoint_id": packet_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": packet_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": packet_state.get("sealed_candidate_id"),
            "followup_execution_id": packet_state.get("followup_execution_id"),
            "execution_id": packet_state.get("execution_id"),
            "followup_evidence_intake_id": packet_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": packet_state.get("intake_id"),
            "followup_sufficiency_recheck_id": packet_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": packet_state.get("recheck_id"),
            "followup_final_answer_packet_id": packet_state.get(
                "packet_preparation_id"
            ),
            "packet_preparation_id": packet_state.get("packet_preparation_id"),
            "packet_id": self.state.final_answer_packet.get("packet_id"),
            "provider_job_kind": packet_state.get("provider_job_kind"),
            "component_id": packet_state.get("component_id"),
            "source_obligation_id": packet_state.get("source_obligation_id"),
            "requirement_ids": packet_state.get("requirement_ids", []),
            "expected_source_classes": packet_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": packet_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": packet_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": packet_state.get(
                "sufficiency_recheck_mode"
            ),
            "final_answer_packet_mode": packet_state.get(
                "final_answer_packet_mode"
            ),
            "final_answer_packet_digest": followup_projection_digest(
                self.state.final_answer_packet
            ),
            "final_answer_authority_projection_digest": followup_projection_digest(
                authority
            ),
            "provider_execution_licensed": False,
            "author_gate_mode": FOLLOWUP_AUTHOR_GATE_MODE,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_author_gate_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_GATE_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_GATE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.FOLLOWUP_AUTHOR_GATE_OBSERVED,
        )

    def authorize_followup_author_observation(
        self,
        *,
        reason: str = "ag96i2h_followup_fixture_author_output_observation",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_author_gate_state:
            raise RunKernelTransitionError(
                "follow-up Author observation requires reduced Author gate state"
            )
        gate_state = self.state.followup_author_gate_state
        if gate_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical Author gate state"
            )
        if gate_state.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
            raise RunKernelTransitionError(
                "follow-up Author observation requires fixture-only Author gate"
            )
        if gate_state.get("packet_authority_consumed") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires consumed packet authority"
            )
        if gate_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author activation closed"
            )
        if gate_state.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires deferred Author execution"
            )
        if gate_state.get("final_text_included") is not False:
            raise RunKernelTransitionError(
                "follow-up Author observation requires no final text in gate state"
            )
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical FinalAnswerPacket"
            )
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical packet authority"
            )
        authority = self.state.final_answer_authority_projection
        if authority.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "follow-up Author observation requires RunKernel packet authority"
            )
        if authority.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical packet authority"
            )
        if authority.get("packet_id") != self.state.final_answer_packet.get(
            "packet_id"
        ):
            raise RunKernelTransitionError(
                "follow-up Author observation requires packet/projection match"
            )
        if authority.get("packet_id") != gate_state.get("packet_id"):
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author gate packet match"
            )
        payload_ref = _safe_mapping(authority.get("author_payload_ref"))
        if payload_ref.get("status") != "author_execution_deferred":
            raise RunKernelTransitionError(
                "follow-up Author observation requires deferred Author payload"
            )
        if authority.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author activation closed"
            )
        if authority.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author execution deferred"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "follow-up Author observation requires product Author output closed"
            )
        if self.state.followup_author_observation_state.get(
            "author_gate_id"
        ) == gate_state.get("author_gate_id"):
            raise RunKernelTransitionError(
                "follow-up Author observation already reduced for this Author gate"
            )
        canonical_inputs = {
            "run_id": gate_state.get("run_id"),
            "checkpoint_id": gate_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": gate_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": gate_state.get("sealed_candidate_id"),
            "followup_execution_id": gate_state.get("followup_execution_id"),
            "execution_id": gate_state.get("execution_id"),
            "followup_evidence_intake_id": gate_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": gate_state.get("intake_id"),
            "followup_sufficiency_recheck_id": gate_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": gate_state.get("recheck_id"),
            "followup_final_answer_packet_id": gate_state.get(
                "followup_final_answer_packet_id"
            ),
            "packet_preparation_id": gate_state.get("packet_preparation_id"),
            "followup_author_gate_id": gate_state.get("author_gate_id"),
            "author_gate_id": gate_state.get("author_gate_id"),
            "packet_id": self.state.final_answer_packet.get("packet_id"),
            "provider_job_kind": gate_state.get("provider_job_kind"),
            "component_id": gate_state.get("component_id"),
            "source_obligation_id": gate_state.get("source_obligation_id"),
            "requirement_ids": gate_state.get("requirement_ids", []),
            "expected_source_classes": gate_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": gate_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": gate_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": gate_state.get(
                "sufficiency_recheck_mode"
            ),
            "final_answer_packet_mode": gate_state.get(
                "final_answer_packet_mode"
            ),
            "author_gate_mode": gate_state.get("author_gate_mode"),
            "fixture_author_observation_mode": FOLLOWUP_AUTHOR_OBSERVATION_MODE,
            "final_answer_packet_digest": followup_projection_digest(
                self.state.final_answer_packet
            ),
            "final_answer_authority_projection_digest": followup_projection_digest(
                authority
            ),
            "followup_author_gate_digest": followup_projection_digest(gate_state),
            "provider_execution_licensed": False,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "model_called": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_text_included": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_author_observation_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_OBSERVATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_OBSERVATION_OBSERVED
            ),
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
            self.state.sufficiency_judgment_projection = (
                _canonical_sufficiency_judgment_projection(
                    judgment_projection=judgment_projection,
                    validation=validation,
                    observation_payload=observation.payload,
                )
            )
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
        elif action.action_type is ActionType.FOLLOWUP_AUTHORIZATION_CONSUME:
            followup_state = _safe_mapping(
                observation.payload.get("followup_authorization_state")
            )
            if not followup_state:
                raise RunKernelTransitionError(
                    "follow-up authorization observation requires "
                    "followup_authorization_state"
                )
            for sealed in followup_state.get("sealed_candidates", []) or []:
                if not isinstance(sealed, Mapping):
                    continue
                gate = sealed.get("execution_gate", {})
                if not isinstance(gate, Mapping):
                    raise RunKernelTransitionError(
                        "follow-up authorization seal requires execution gate"
                    )
                if (
                    gate.get("execution_permission") is not False
                    or gate.get("executable_in_current_phase") is not False
                    or gate.get("provider_execution_licensed") is not False
                ):
                    raise RunKernelTransitionError(
                        "AG-96I2A follow-up authorization must be non-executable"
                    )
            gate = followup_state.get("execution_gate", {})
            if not isinstance(gate, Mapping) or gate.get("execution_permission") is not False:
                raise RunKernelTransitionError(
                    "AG-96I2A follow-up authorization state requires closed execution gate"
                )
            self.state.followup_authorization_state = followup_state
            self.state.followup_authorization_projection = {
                "owner": "RunKernel.FollowupAuthorization",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": followup_state.get("schema_version"),
                "consumption_id": followup_state.get("consumption_id"),
                "checkpoint_id": followup_state.get("checkpoint_id"),
                "run_id": followup_state.get("run_id"),
                "mode": followup_state.get("mode"),
                "input_checkpoint_hash": followup_state.get("input_checkpoint_hash"),
                "validation_status": followup_state.get("validation", {}).get(
                    "status"
                ),
                "status": followup_state.get("status"),
                "selected_authorization_candidate_ids": followup_state.get(
                    "selected_authorization_candidate_ids",
                    [],
                ),
                "denied_candidate_ids": followup_state.get(
                    "denied_candidate_ids",
                    [],
                ),
                "sealed_candidate_count": followup_state.get(
                    "sealed_candidate_count",
                    0,
                ),
                "selected_mode_insufficient": followup_state.get(
                    "selected_mode_insufficient"
                ),
                "needs_balanced_or_deep": followup_state.get(
                    "needs_balanced_or_deep"
                ),
                "needs_deep": followup_state.get("needs_deep"),
                "execution_gate": _safe_mapping(gate),
                "behavior_boundary_flags": _safe_mapping(
                    followup_state.get("behavior_boundary_flags")
                ),
            }
            self.state.followup_authorization_history.append(
                deepcopy(self.state.followup_authorization_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_authorization_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_FIXTURE_EXECUTE:
            execution_state = _safe_mapping(
                observation.payload.get("followup_execution_state")
            )
            if not execution_state:
                raise RunKernelTransitionError(
                    "follow-up execution observation requires followup_execution_state"
                )
            if not self.state.followup_authorization_state:
                raise RunKernelTransitionError(
                    "follow-up execution requires existing authorization state"
                )
            if (
                execution_state.get("followup_authorization_consumption_id")
                != self.state.followup_authorization_state.get("consumption_id")
            ):
                raise RunKernelTransitionError(
                    "follow-up execution must reference current authorization state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _validate_followup_execution_action_binding(
                action_inputs=action_inputs,
                execution_state=execution_state,
            )
            gate = _safe_mapping(execution_state.get("execution_gate"))
            flags = _safe_mapping(execution_state.get("behavior_boundary_flags"))
            if gate.get("allowed_execution_mode") != "fixture_only":
                raise RunKernelTransitionError(
                    "follow-up execution reducer only accepts fixture_only observations"
                )
            if gate.get("provider_execution_licensed") is not False:
                raise RunKernelTransitionError(
                    "follow-up execution observation must keep provider execution unlicensed"
                )
            _require_followup_flags_false(
                flags,
                _FOLLOWUP_EXECUTION_FALSE_FLAGS,
                context="follow-up execution observation",
            )
            if execution_state.get("evidence_ledger_intake_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up execution must defer EvidenceLedger intake"
                )
            if execution_state.get("evidence_ledger_evidence_admitted") is not False:
                raise RunKernelTransitionError(
                    "follow-up execution must not admit EvidenceLedger evidence"
                )
            self.state.followup_execution_state = execution_state
            self.state.followup_execution_projection = {
                "owner": "RunKernel.FollowupFixtureExecution",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": execution_state.get("schema_version"),
                "execution_id": execution_state.get("execution_id"),
                "observation_id": execution_state.get("observation_id"),
                "run_id": execution_state.get("run_id"),
                "checkpoint_id": execution_state.get("checkpoint_id"),
                "followup_authorization_consumption_id": execution_state.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
                "provider_job_kind": execution_state.get("provider_job_kind"),
                "component_id": execution_state.get("component_id"),
                "source_obligation_id": execution_state.get("source_obligation_id"),
                "requirement_ids": execution_state.get("requirement_ids", []),
                "result_status": execution_state.get("result_status"),
                "fixture_execution_mode": execution_state.get(
                    "fixture_execution_mode"
                ),
                "bridge_only": execution_state.get("bridge_only"),
                "final_evidence_satisfied": execution_state.get(
                    "final_evidence_satisfied"
                ),
                "citation_eligible": execution_state.get("citation_eligible"),
                "evidence_ledger_intake_deferred": execution_state.get(
                    "evidence_ledger_intake_deferred"
                ),
                "budget_semantics": _safe_mapping(
                    execution_state.get("budget_semantics")
                ),
                "execution_gate": gate,
                "behavior_boundary_flags": flags,
            }
            self.state.followup_execution_history.append(
                deepcopy(self.state.followup_execution_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_execution_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_EVIDENCE_INTAKE:
            intake_state = _safe_mapping(
                observation.payload.get("followup_evidence_intake_state")
            )
            if not intake_state:
                raise RunKernelTransitionError(
                    "follow-up evidence intake observation requires "
                    "followup_evidence_intake_state"
                )
            if not self.state.followup_execution_state:
                raise RunKernelTransitionError(
                    "follow-up evidence intake requires existing execution state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _validate_followup_evidence_intake_action_binding(
                action_inputs=action_inputs,
                execution_state=self.state.followup_execution_state,
                intake_state=intake_state,
            )
            flags = _safe_mapping(intake_state.get("behavior_boundary_flags"))
            _require_followup_flags_false(
                flags,
                _FOLLOWUP_INTAKE_FALSE_FLAGS,
                context="follow-up evidence intake observation",
            )
            if flags.get("evidence_ledger_mutated") is not True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must be the EvidenceLedger mutation seam"
                )
            if flags.get("evidence_ledger_intake_only_opened_surface") is not True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake may only open EvidenceLedger intake"
                )
            if intake_state.get("provider_execution_licensed") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must keep provider execution unlicensed"
                )
            if intake_state.get("evidence_ledger_intake_mode") != (
                "fixture_only_followup_intake"
            ):
                raise RunKernelTransitionError(
                    "follow-up evidence intake requires fixture_only intake mode"
                )
            if intake_state.get("final_evidence_satisfied") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not satisfy final evidence"
                )
            if intake_state.get("citation_eligible") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not create citation eligibility"
                )
            ledger_observation = _build_followup_evidence_intake_ledger_observation(
                intake_state=intake_state,
                execution_state=self.state.followup_execution_state,
            )
            derived_outcome = _followup_evidence_intake_outcome(ledger_observation)
            intake_state = {
                **intake_state,
                **derived_outcome,
                "ledger_observation": deepcopy(ledger_observation),
                "ledger_requirements": deepcopy(
                    ledger_observation.get("requirements", [])
                ),
                "ledger_candidates": deepcopy(ledger_observation.get("candidates", [])),
                "ledger_requirement_links": deepcopy(
                    ledger_observation.get("requirement_links", [])
                ),
                "ledger_followup_fixture_intake": deepcopy(
                    ledger_observation.get("followup_fixture_intake", {})
                ),
            }
            self.state.evidence_ledger.reduce_observation(ledger_observation)
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            self.state.projections[EVIDENCE_LEDGER_STAGE] = deepcopy(
                ledger_projection
            )
            self.state.followup_evidence_intake_state = intake_state
            self.state.followup_evidence_intake_projection = {
                "owner": "RunKernel.FollowupEvidenceIntake",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": intake_state.get("schema_version"),
                "intake_id": intake_state.get("intake_id"),
                "observation_id": intake_state.get("observation_id"),
                "run_id": intake_state.get("run_id"),
                "checkpoint_id": intake_state.get("checkpoint_id"),
                "followup_authorization_consumption_id": intake_state.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": intake_state.get("sealed_candidate_id"),
                "followup_execution_id": intake_state.get("followup_execution_id"),
                "execution_id": intake_state.get("execution_id"),
                "followup_execution_observation_id": intake_state.get(
                    "followup_execution_observation_id"
                ),
                "provider_job_kind": intake_state.get("provider_job_kind"),
                "component_id": intake_state.get("component_id"),
                "source_obligation_id": intake_state.get("source_obligation_id"),
                "requirement_ids": intake_state.get("requirement_ids", []),
                "expected_source_classes": intake_state.get(
                    "expected_source_classes",
                    [],
                ),
                "result_status": intake_state.get("result_status"),
                "bridge_only": intake_state.get("bridge_only"),
                "evidence_ledger_intake_mode": intake_state.get(
                    "evidence_ledger_intake_mode"
                ),
                "evidence_ledger_observation_id": ledger_observation.get(
                    "observation_id"
                ),
                "evidence_ledger_candidate_count": ledger_projection.get(
                    "candidate_count"
                ),
                "evidence_ledger_requirement_count": ledger_projection.get(
                    "requirement_count"
                ),
                "evidence_ledger_custody_record_count": ledger_projection.get(
                    "custody_record_count"
                ),
                "source_obligation_satisfied": intake_state.get(
                    "source_obligation_satisfied"
                ),
                "final_evidence_satisfied": intake_state.get(
                    "final_evidence_satisfied"
                ),
                "citation_eligible": intake_state.get("citation_eligible"),
                "sufficiency_judgment_recheck_deferred": intake_state.get(
                    "sufficiency_judgment_recheck_deferred"
                ),
                "behavior_boundary_flags": flags,
            }
            self.state.followup_evidence_intake_history.append(
                deepcopy(self.state.followup_evidence_intake_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_evidence_intake_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_SUFFICIENCY_RECHECK:
            observed_recheck_state = _safe_mapping(
                observation.payload.get("followup_sufficiency_recheck_state")
            )
            if not observed_recheck_state:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck observation requires "
                    "followup_sufficiency_recheck_state"
                )
            if not self.state.followup_evidence_intake_state:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck requires existing intake state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _validate_followup_sufficiency_recheck_observation_binding(
                action_inputs=action_inputs,
                observed_recheck_state=observed_recheck_state,
            )
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            try:
                canonical_record = build_followup_sufficiency_recheck_record(
                    action_inputs=action_inputs,
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                    evidence_ledger_projection=ledger_projection,
                    prior_sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    sufficiency_handoff=_safe_mapping(
                        self.state.followup_authorization_state.get(
                            "sufficiency_handoff"
                        )
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            recheck_state = canonical_record.to_dict()
            judgment_projection = _safe_mapping(
                recheck_state.get("sufficiency_judgment_projection")
            )
            if not judgment_projection:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck requires SufficiencyJudgment "
                    "projection"
                )
            flags = _safe_mapping(recheck_state.get("behavior_boundary_flags"))
            _require_followup_flags_false(
                flags,
                _FOLLOWUP_RECHECK_FALSE_FLAGS,
                context="follow-up sufficiency recheck",
            )
            if flags.get("sufficiency_judgment_rechecked") is not True:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must recheck SufficiencyJudgment"
                )
            if recheck_state.get("final_answer_packet_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must defer FinalAnswerPacket"
                )
            if recheck_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must keep Author closed"
                )
            if recheck_state.get("citation_behavior_changed") is not False:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must not change citations"
                )
            recheck_state = {
                **recheck_state,
                "owner": "RunKernel.FollowupSufficiencyRecheck",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_recheck_state.get("observation_id"),
            }
            self.state.followup_sufficiency_recheck_state = recheck_state
            validation = _safe_mapping(judgment_projection.get("validation"))
            self.state.sufficiency_judgment = judgment_projection
            self.state.sufficiency_judgment_projection = (
                _canonical_sufficiency_judgment_projection(
                    judgment_projection=judgment_projection,
                    validation=validation,
                    observation_payload=judgment_projection,
                )
            )
            self.state.sufficiency_judgment_history.append(
                deepcopy(self.state.sufficiency_judgment_projection)
            )
            self.state.projections[SUFFICIENCY_JUDGMENT_STAGE] = deepcopy(
                self.state.sufficiency_judgment_projection
            )
            self.state.followup_sufficiency_recheck_projection = {
                "owner": "RunKernel.FollowupSufficiencyRecheck",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": recheck_state.get("schema_version"),
                "recheck_id": recheck_state.get("recheck_id"),
                "observation_id": recheck_state.get("observation_id"),
                "run_id": recheck_state.get("run_id"),
                "checkpoint_id": recheck_state.get("checkpoint_id"),
                "followup_authorization_consumption_id": recheck_state.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": recheck_state.get("sealed_candidate_id"),
                "followup_execution_id": recheck_state.get("followup_execution_id"),
                "execution_id": recheck_state.get("execution_id"),
                "followup_execution_observation_id": recheck_state.get(
                    "followup_execution_observation_id"
                ),
                "followup_evidence_intake_id": recheck_state.get(
                    "followup_evidence_intake_id"
                ),
                "intake_id": recheck_state.get("intake_id"),
                "followup_evidence_intake_observation_id": recheck_state.get(
                    "followup_evidence_intake_observation_id"
                ),
                "provider_job_kind": recheck_state.get("provider_job_kind"),
                "component_id": recheck_state.get("component_id"),
                "source_obligation_id": recheck_state.get("source_obligation_id"),
                "requirement_ids": recheck_state.get("requirement_ids", []),
                "expected_source_classes": recheck_state.get(
                    "expected_source_classes",
                    [],
                ),
                "result_status": recheck_state.get("result_status"),
                "bridge_only": recheck_state.get("bridge_only"),
                "sufficiency_recheck_mode": recheck_state.get(
                    "sufficiency_recheck_mode"
                ),
                "evidence_ledger_projection_digest": recheck_state.get(
                    "evidence_ledger_projection_digest"
                ),
                "source_requirement_status_summary": recheck_state.get(
                    "source_requirement_status_summary",
                    {},
                ),
                "fixture_sufficiency_posture": recheck_state.get(
                    "fixture_sufficiency_posture"
                ),
                "sufficiency_judgment_ref": recheck_state.get(
                    "sufficiency_judgment_ref",
                    {},
                ),
                "final_answer_packet_deferred": recheck_state.get(
                    "final_answer_packet_deferred"
                ),
                "author_activation_allowed": recheck_state.get(
                    "author_activation_allowed"
                ),
                "citation_behavior_changed": recheck_state.get(
                    "citation_behavior_changed"
                ),
                "citation_eligible": recheck_state.get("citation_eligible"),
                "live_validation_not_run": recheck_state.get(
                    "live_validation_not_run"
                ),
                "behavior_boundary_flags": flags,
            }
            self.state.followup_sufficiency_recheck_history.append(
                deepcopy(self.state.followup_sufficiency_recheck_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_sufficiency_recheck_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
        ):
            observed_packet_state = _safe_mapping(
                observation.payload.get("followup_final_answer_packet_state")
            )
            if not observed_packet_state:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket observation requires "
                    "followup_final_answer_packet_state"
                )
            if not self.state.followup_sufficiency_recheck_state:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket requires existing recheck state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _validate_followup_final_answer_packet_observation_binding(
                action_inputs=action_inputs,
                observed_packet_state=observed_packet_state,
            )
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            try:
                canonical_record = build_followup_final_answer_packet_record(
                    action_inputs=action_inputs,
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    evidence_ledger_projection=ledger_projection,
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            packet_state = {
                **canonical_record.to_dict(),
                "owner": "RunKernel.FollowupFinalAnswerPacket",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
            }
            packet_projection = _safe_mapping(packet_state.get("packet_projection"))
            if not packet_projection:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket requires packet_projection"
                )
            flags = _safe_mapping(packet_state.get("behavior_boundary_flags"))
            _require_followup_flags_false(
                flags,
                _FOLLOWUP_PACKET_FALSE_FLAGS,
                context="follow-up FinalAnswerPacket",
            )
            if flags.get("final_answer_packet_prepared") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must prepare packet state"
                )
            if flags.get("final_answer_packet_updated") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must update packet projection"
                )
            if flags.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must keep Author closed"
                )
            if flags.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must defer Author execution"
                )
            if flags.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must not run live validation"
                )
            self.state.followup_final_answer_packet_state = packet_state
            citation_eligible = list(packet_projection.get("citation_eligible") or [])
            citation_eligible_source_ids = [
                item.get("source_id")
                for item in citation_eligible
                if isinstance(item, Mapping) and item.get("source_id") is not None
            ]
            author_payload_ref = {
                "packet_id": packet_projection.get("packet_id"),
                "status": "author_execution_deferred",
                "prompt_text_included": False,
                "fixture_only": True,
                "author_activation_allowed": False,
                "author_execution_deferred": True,
                "not_for_product_answer_activation": True,
                "citation_formatter_invoked": False,
            }
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
                "citation_eligible_source_ids": citation_eligible_source_ids,
                "citation_eligibility_refs": packet_state.get(
                    "citation_eligibility_refs",
                    [],
                ),
                "missing_source_obligation_count": len(
                    packet_state.get("missing_required_obligations", []) or []
                ),
                "partial_source_obligation_count": len(
                    packet_state.get("partial_obligations", []) or []
                ),
                "satisfied_source_obligation_count": len(
                    packet_state.get("satisfied_obligations", []) or []
                ),
                "source_bound_numeric_unknown_count": len(
                    packet_state.get("source_bound_unknowns", []) or []
                ),
                "mandatory_caveat_count": len(
                    packet_state.get("mandatory_caveats", []) or []
                ),
                "prohibited_upgrade_count": len(
                    packet_state.get("prohibited_upgrades", []) or []
                ),
                "author_authority_payload_ref": packet_state.get(
                    "packet_authority_payload",
                    {},
                ),
                "final_answer_packet_prepared": True,
                "author_activation_allowed": False,
                "author_execution_deferred": True,
                "citation_rendering_changed": False,
                "citation_formatter_invoked": False,
                "product_answer_behavior_changed": False,
                "live_validation_not_run": True,
                "followup_packet_preparation_id": packet_state.get(
                    "packet_preparation_id"
                ),
                "followup_recheck_id": packet_state.get("recheck_id"),
            }
            self.state.projections[FINAL_ANSWER_PACKET_STAGE] = deepcopy(
                self.state.final_answer_authority_projection
            )
            self.state.followup_final_answer_packet_projection = {
                "owner": "RunKernel.FollowupFinalAnswerPacket",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": packet_state.get("schema_version"),
                "packet_preparation_id": packet_state.get("packet_preparation_id"),
                "observation_id": packet_state.get("observation_id"),
                "run_id": packet_state.get("run_id"),
                "checkpoint_id": packet_state.get("checkpoint_id"),
                "followup_authorization_consumption_id": packet_state.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": packet_state.get("sealed_candidate_id"),
                "followup_execution_id": packet_state.get("followup_execution_id"),
                "execution_id": packet_state.get("execution_id"),
                "followup_execution_observation_id": packet_state.get(
                    "followup_execution_observation_id"
                ),
                "followup_evidence_intake_id": packet_state.get(
                    "followup_evidence_intake_id"
                ),
                "intake_id": packet_state.get("intake_id"),
                "followup_evidence_intake_observation_id": packet_state.get(
                    "followup_evidence_intake_observation_id"
                ),
                "followup_sufficiency_recheck_id": packet_state.get(
                    "followup_sufficiency_recheck_id"
                ),
                "recheck_id": packet_state.get("recheck_id"),
                "followup_sufficiency_recheck_observation_id": packet_state.get(
                    "followup_sufficiency_recheck_observation_id"
                ),
                "provider_job_kind": packet_state.get("provider_job_kind"),
                "component_id": packet_state.get("component_id"),
                "source_obligation_id": packet_state.get("source_obligation_id"),
                "requirement_ids": packet_state.get("requirement_ids", []),
                "expected_source_classes": packet_state.get(
                    "expected_source_classes",
                    [],
                ),
                "final_answer_packet_mode": packet_state.get(
                    "final_answer_packet_mode"
                ),
                "packet_id": packet_projection.get("packet_id"),
                "readiness_status": packet_projection.get("readiness_status"),
                "final_evidence_refs": packet_state.get("final_evidence_refs", []),
                "citation_eligibility_refs": packet_state.get(
                    "citation_eligibility_refs",
                    [],
                ),
                "mandatory_caveats": packet_state.get("mandatory_caveats", []),
                "prohibited_upgrades": packet_state.get("prohibited_upgrades", []),
                "missing_required_obligations": packet_state.get(
                    "missing_required_obligations",
                    [],
                ),
                "partial_obligations": packet_state.get("partial_obligations", []),
                "satisfied_obligations": packet_state.get(
                    "satisfied_obligations",
                    [],
                ),
                "source_bound_unknowns": packet_state.get(
                    "source_bound_unknowns",
                    [],
                ),
                "unresolved_conflicts": packet_state.get(
                    "unresolved_conflicts",
                    [],
                ),
                "final_answer_packet_prepared": True,
                "author_activation_allowed": False,
                "author_execution_deferred": True,
                "citation_rendering_changed": False,
                "citation_formatter_invoked": False,
                "product_answer_behavior_changed": False,
                "live_validation_not_run": True,
                "behavior_boundary_flags": flags,
                "canonical_final_answer_packet_ref": {
                    "owner": "RunKernel.FinalAnswerPacket",
                    "canonical_state": True,
                    "packet_id": packet_projection.get("packet_id"),
                    "projection_stage": FINAL_ANSWER_PACKET_STAGE,
                },
            }
            self.state.followup_final_answer_packet_history.append(
                deepcopy(self.state.followup_final_answer_packet_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_final_answer_packet_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_GATE:
            observed_gate_state = _safe_mapping(
                observation.payload.get("followup_author_gate_state")
            )
            if not observed_gate_state:
                raise RunKernelTransitionError(
                    "follow-up Author gate observation requires "
                    "followup_author_gate_state"
                )
            if not self.state.followup_final_answer_packet_state:
                raise RunKernelTransitionError(
                    "follow-up Author gate requires existing packet state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _validate_followup_author_gate_observation_binding(
                action_inputs=action_inputs,
                observed_gate_state=observed_gate_state,
            )
            try:
                canonical_record = build_followup_author_gate_record(
                    action_inputs=action_inputs,
                    followup_final_answer_packet_state=(
                        self.state.followup_final_answer_packet_state
                    ),
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            gate_state = {
                **canonical_record.to_dict(),
                "owner": "RunKernel.FollowupAuthorGate",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
            }
            flags = _safe_mapping(gate_state.get("behavior_boundary_flags"))
            _require_followup_flags_false(
                flags,
                _FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS,
                context="follow-up Author gate",
            )
            if gate_state.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate must consume packet authority"
                )
            if flags.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate flags must consume packet authority"
                )
            if gate_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author gate must keep Author activation closed"
                )
            if gate_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate must defer Author execution"
                )
            if gate_state.get("final_text_included") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author gate must not include final text"
                )
            if gate_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate must not run live validation"
                )
            self.state.followup_author_gate_state = gate_state
            self.state.followup_author_gate_projection = {
                "owner": "RunKernel.FollowupAuthorGate",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": gate_state.get("schema_version"),
                "author_gate_id": gate_state.get("author_gate_id"),
                "observation_id": gate_state.get("observation_id"),
                "run_id": gate_state.get("run_id"),
                "checkpoint_id": gate_state.get("checkpoint_id"),
                "followup_authorization_consumption_id": gate_state.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": gate_state.get("sealed_candidate_id"),
                "followup_execution_id": gate_state.get("followup_execution_id"),
                "execution_id": gate_state.get("execution_id"),
                "followup_evidence_intake_id": gate_state.get(
                    "followup_evidence_intake_id"
                ),
                "intake_id": gate_state.get("intake_id"),
                "followup_sufficiency_recheck_id": gate_state.get(
                    "followup_sufficiency_recheck_id"
                ),
                "recheck_id": gate_state.get("recheck_id"),
                "followup_final_answer_packet_id": gate_state.get(
                    "followup_final_answer_packet_id"
                ),
                "packet_preparation_id": gate_state.get("packet_preparation_id"),
                "packet_id": gate_state.get("packet_id"),
                "provider_job_kind": gate_state.get("provider_job_kind"),
                "component_id": gate_state.get("component_id"),
                "source_obligation_id": gate_state.get("source_obligation_id"),
                "requirement_ids": gate_state.get("requirement_ids", []),
                "expected_source_classes": gate_state.get(
                    "expected_source_classes",
                    [],
                ),
                "final_answer_packet_mode": gate_state.get(
                    "final_answer_packet_mode"
                ),
                "author_gate_mode": gate_state.get("author_gate_mode"),
                "final_answer_packet_digest": gate_state.get(
                    "final_answer_packet_digest"
                ),
                "final_answer_authority_projection_digest": gate_state.get(
                    "final_answer_authority_projection_digest"
                ),
                "author_gate_decision": gate_state.get("author_gate_decision"),
                "author_gate_reason": gate_state.get("author_gate_reason"),
                "packet_authority_consumed": True,
                "answer_readiness_posture": gate_state.get(
                    "answer_readiness_posture",
                    {},
                ),
                "author_payload_ref": gate_state.get("author_payload_ref", {}),
                "final_answer_authority_payload_ref": gate_state.get(
                    "final_answer_authority_payload_ref",
                    {},
                ),
                "mandatory_caveats": gate_state.get("mandatory_caveats", []),
                "prohibited_upgrades": gate_state.get("prohibited_upgrades", []),
                "missing_required_obligations": gate_state.get(
                    "missing_required_obligations",
                    [],
                ),
                "partial_obligations": gate_state.get("partial_obligations", []),
                "satisfied_obligations": gate_state.get(
                    "satisfied_obligations",
                    [],
                ),
                "source_bound_unknowns": gate_state.get(
                    "source_bound_unknowns",
                    [],
                ),
                "unresolved_conflicts": gate_state.get(
                    "unresolved_conflicts",
                    [],
                ),
                "citation_eligibility_refs": gate_state.get(
                    "citation_eligibility_refs",
                    [],
                ),
                "citation_eligible_source_ids": gate_state.get(
                    "citation_eligible_source_ids",
                    [],
                ),
                "author_activation_allowed": False,
                "author_execution_deferred": True,
                "author_executor_invoked": False,
                "author_prompt_changed": False,
                "author_prose_behavior_changed": False,
                "citation_rendering_changed": False,
                "citation_formatter_invoked": False,
                "product_answer_behavior_changed": False,
                "final_text_included": False,
                "live_validation_not_run": True,
                "behavior_boundary_flags": flags,
                "canonical_final_answer_packet_ref": {
                    "owner": "RunKernel.FinalAnswerPacket",
                    "canonical_state": True,
                    "packet_id": gate_state.get("packet_id"),
                    "projection_stage": FINAL_ANSWER_PACKET_STAGE,
                },
            }
            self.state.followup_author_gate_history.append(
                deepcopy(self.state.followup_author_gate_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_gate_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION:
            observed_author_state = _safe_mapping(
                observation.payload.get("followup_author_observation_state")
            )
            if not observed_author_state:
                raise RunKernelTransitionError(
                    "follow-up Author observation requires "
                    "followup_author_observation_state"
                )
            if not self.state.followup_author_gate_state:
                raise RunKernelTransitionError(
                    "follow-up Author observation requires existing Author gate state"
                )
            try:
                reject_followup_author_observation_boundary_spoof(
                    observed_author_state
                )
            except PermissionError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            action_inputs = _safe_mapping(action.inputs)
            _validate_followup_author_observation_binding(
                action_inputs=action_inputs,
                observed_author_state=observed_author_state,
            )
            observed_output_facts = _safe_mapping(
                observed_author_state.get("observed_output_facts")
            )
            if not observed_output_facts:
                raise RunKernelTransitionError(
                    "follow-up Author observation requires sanitized output facts"
                )
            try:
                canonical_record = build_followup_author_observation_record(
                    action_inputs=action_inputs,
                    followup_author_gate_state=self.state.followup_author_gate_state,
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    observed_output_facts=observed_output_facts,
                )
                compliance = derive_followup_author_observation_compliance(
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    followup_author_gate_state=self.state.followup_author_gate_state,
                    observed_output_facts=observed_output_facts,
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            author_state = {
                **canonical_record.to_dict(),
                **compliance,
                "owner": "RunKernel.FollowupAuthorObservation",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
            }
            flags = _safe_mapping(author_state.get("behavior_boundary_flags"))
            _require_followup_flags_false(
                flags,
                _FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS,
                context="follow-up Author observation",
            )
            if author_state.get("author_output_observed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must observe Author output facts"
                )
            if author_state.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must consume packet authority"
                )
            if flags.get("author_output_observed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation flags must record output observation"
                )
            if flags.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation flags must consume packet authority"
                )
            if author_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author observation must keep Author activation closed"
                )
            if author_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must defer Author execution"
                )
            if author_state.get("final_text_included") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author observation must not retain final text"
                )
            if author_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must not run live validation"
                )
            self.state.followup_author_observation_state = author_state
            self.state.followup_author_observation_projection = {
                "owner": "RunKernel.FollowupAuthorObservation",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": author_state.get("schema_version"),
                "author_observation_id": author_state.get(
                    "author_observation_id"
                ),
                "observation_id": author_state.get("observation_id"),
                "run_id": author_state.get("run_id"),
                "checkpoint_id": author_state.get("checkpoint_id"),
                "followup_authorization_consumption_id": author_state.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": author_state.get("sealed_candidate_id"),
                "followup_execution_id": author_state.get("followup_execution_id"),
                "execution_id": author_state.get("execution_id"),
                "followup_evidence_intake_id": author_state.get(
                    "followup_evidence_intake_id"
                ),
                "intake_id": author_state.get("intake_id"),
                "followup_sufficiency_recheck_id": author_state.get(
                    "followup_sufficiency_recheck_id"
                ),
                "recheck_id": author_state.get("recheck_id"),
                "followup_final_answer_packet_id": author_state.get(
                    "followup_final_answer_packet_id"
                ),
                "packet_preparation_id": author_state.get("packet_preparation_id"),
                "followup_author_gate_id": author_state.get(
                    "followup_author_gate_id"
                ),
                "author_gate_id": author_state.get("author_gate_id"),
                "packet_id": author_state.get("packet_id"),
                "provider_job_kind": author_state.get("provider_job_kind"),
                "component_id": author_state.get("component_id"),
                "source_obligation_id": author_state.get("source_obligation_id"),
                "requirement_ids": author_state.get("requirement_ids", []),
                "expected_source_classes": author_state.get(
                    "expected_source_classes",
                    [],
                ),
                "final_answer_packet_mode": author_state.get(
                    "final_answer_packet_mode"
                ),
                "author_gate_mode": author_state.get("author_gate_mode"),
                "fixture_author_observation_mode": author_state.get(
                    "fixture_author_observation_mode"
                ),
                "final_answer_packet_digest": author_state.get(
                    "final_answer_packet_digest"
                ),
                "final_answer_authority_projection_digest": author_state.get(
                    "final_answer_authority_projection_digest"
                ),
                "followup_author_gate_digest": author_state.get(
                    "followup_author_gate_digest"
                ),
                "author_output_observed": True,
                "packet_authority_consumed": True,
                "packet_authority_compliance_status": author_state.get(
                    "packet_authority_compliance_status"
                ),
                "citation_compliance_status": author_state.get(
                    "citation_compliance_status"
                ),
                "caveat_compliance_status": author_state.get(
                    "caveat_compliance_status"
                ),
                "prohibited_upgrade_compliance_status": author_state.get(
                    "prohibited_upgrade_compliance_status"
                ),
                "source_bound_unknown_compliance_status": author_state.get(
                    "source_bound_unknown_compliance_status"
                ),
                "missing_obligation_compliance_status": author_state.get(
                    "missing_obligation_compliance_status"
                ),
                "citation_eligible_source_ids": author_state.get(
                    "citation_eligible_source_ids",
                    [],
                ),
                "cited_source_ids": author_state.get("cited_source_ids", []),
                "unauthorized_citation_source_ids": author_state.get(
                    "unauthorized_citation_source_ids",
                    [],
                ),
                "missing_mandatory_caveats": author_state.get(
                    "missing_mandatory_caveats",
                    [],
                ),
                "prohibited_upgrade_violations": author_state.get(
                    "prohibited_upgrade_violations",
                    [],
                ),
                "unacknowledged_source_bound_unknowns": author_state.get(
                    "unacknowledged_source_bound_unknowns",
                    [],
                ),
                "unacknowledged_missing_obligations": author_state.get(
                    "unacknowledged_missing_obligations",
                    [],
                ),
                "report_hash": author_state.get("report_hash"),
                "report_length": author_state.get("report_length"),
                "final_text_hash": author_state.get("final_text_hash"),
                "final_text_length": author_state.get("final_text_length"),
                "final_text_included": False,
                "author_activation_allowed": False,
                "author_execution_deferred": True,
                "author_executor_invoked": False,
                "model_called": False,
                "author_prompt_changed": False,
                "author_prose_behavior_changed": False,
                "citation_rendering_changed": False,
                "citation_formatter_invoked": False,
                "product_answer_behavior_changed": False,
                "live_validation_not_run": True,
                "behavior_boundary_flags": flags,
                "canonical_final_answer_packet_ref": {
                    "owner": "RunKernel.FinalAnswerPacket",
                    "canonical_state": True,
                    "packet_id": author_state.get("packet_id"),
                    "projection_stage": FINAL_ANSWER_PACKET_STAGE,
                },
                "canonical_followup_author_gate_ref": {
                    "owner": "RunKernel.FollowupAuthorGate",
                    "canonical_state": True,
                    "author_gate_id": author_state.get("author_gate_id"),
                    "projection_stage": FOLLOWUP_AUTHOR_GATE_STAGE,
                },
            }
            self.state.followup_author_observation_history.append(
                deepcopy(self.state.followup_author_observation_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_observation_projection
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


def _require_followup_flags_false(
    flags: Mapping[str, Any],
    flag_names: Sequence[str],
    *,
    context: str,
) -> None:
    for flag in flag_names:
        if flags.get(flag) is not False:
            raise RunKernelTransitionError(f"{context} requires {flag}=False")


def _canonical_sufficiency_judgment_projection(
    *,
    judgment_projection: Mapping[str, Any],
    validation: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    validation_mapping = _safe_mapping(validation)
    judgment_validation = _safe_mapping(judgment_projection.get("validation"))
    return {
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
        "source_bound_numeric_resolutions": judgment_projection.get(
            "source_bound_numeric_resolutions",
            [],
        ),
        "weak_or_thin_evidence": judgment_projection.get(
            "weak_or_thin_evidence",
            [],
        ),
        "failure_card_authorized": judgment_projection.get(
            "failure_card_authorized"
        ),
        "final_answer_allowed": judgment_projection.get("final_answer_allowed"),
        "final_answer_posture": judgment_projection.get("final_answer_posture"),
        "mandatory_caveats": judgment_projection.get("mandatory_caveats", []),
        "prohibited_upgrades": judgment_projection.get("prohibited_upgrades", []),
        "readiness_reasons": judgment_projection.get("readiness_reasons", []),
        "final_packet_inputs": judgment_projection.get("final_packet_inputs", {}),
        "rationale": judgment_projection.get("rationale"),
        "validation_status": validation_mapping.get("status")
        or judgment_validation.get("status"),
        "prompt_hash": validation_mapping.get("prompt_hash")
        or observation_payload.get("prompt_hash"),
        "prompt_length": validation_mapping.get("prompt_length")
        or observation_payload.get("prompt_length"),
        "model_identity": {
            "provider": validation_mapping.get("provider"),
            "model": validation_mapping.get("model"),
            "effort": validation_mapping.get("effort"),
            "use_reasoning": validation_mapping.get("use_reasoning"),
        },
        "prompt_text_retained": False,
        "model_response_text_retained": False,
        "provider_payload_retained": False,
    }


def _followup_sealed_candidate(
    followup_state: Mapping[str, Any],
    candidate_id: str,
) -> Mapping[str, Any]:
    expected = _clean_text(candidate_id, limit=160)
    expected = expected.casefold().replace("-", "_").replace(" ", "_") if expected else ""
    for candidate in followup_state.get("sealed_candidates", []) or []:
        if not isinstance(candidate, Mapping):
            continue
        actual = _clean_text(candidate.get("candidate_id"), limit=160)
        actual = actual.casefold().replace("-", "_").replace(" ", "_") if actual else ""
        if actual == expected:
            return candidate
    raise RunKernelTransitionError(
        f"follow-up fixture execution candidate {candidate_id!r} is not sealed"
    )


def _validate_followup_execution_action_binding(
    *,
    action_inputs: Mapping[str, Any],
    execution_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "fixture_execution_mode",
    ):
        if execution_state.get(binding_field) != action_inputs.get(binding_field):
            raise RunKernelTransitionError(
                "follow-up execution observation "
                f"{binding_field} does not match authorized action"
            )
    if action_inputs.get("fixture_execution_mode") != "fixture_only":
        raise RunKernelTransitionError(
            "follow-up fixture execution action must be bound to fixture_only mode"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise RunKernelTransitionError(
            "follow-up fixture execution action must keep provider execution unlicensed"
        )
    if list(execution_state.get("requirement_ids", []) or []) != list(
        action_inputs.get("requirement_ids", []) or []
    ):
        raise RunKernelTransitionError(
            "follow-up execution observation requirement_ids does not match authorized action"
        )
    action_job_kind = action_inputs.get("provider_job_kind")
    execution_job_kind = execution_state.get("provider_job_kind")
    if (action_job_kind or execution_job_kind) and action_job_kind != execution_job_kind:
        raise RunKernelTransitionError(
            "follow-up execution observation provider_job_kind does not match authorized action"
        )


def _validate_followup_evidence_intake_action_binding(
    *,
    action_inputs: Mapping[str, Any],
    execution_state: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "fixture_execution_mode",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
    ):
        if intake_state.get(binding_field) != action_inputs.get(binding_field):
            raise RunKernelTransitionError(
                "follow-up evidence intake observation "
                f"{binding_field} does not match authorized action"
            )
        if intake_state.get(binding_field) != execution_state.get(binding_field):
            raise RunKernelTransitionError(
                "follow-up evidence intake observation "
                f"{binding_field} does not match execution state"
            )
    if list(intake_state.get("requirement_ids", []) or []) != list(
        action_inputs.get("requirement_ids", []) or []
    ):
        raise RunKernelTransitionError(
            "follow-up evidence intake observation requirement_ids do not match "
            "authorized action"
        )
    if list(intake_state.get("requirement_ids", []) or []) != list(
        execution_state.get("requirement_ids", []) or []
    ):
        raise RunKernelTransitionError(
            "follow-up evidence intake observation requirement_ids do not match "
            "execution state"
        )
    if list(intake_state.get("expected_source_classes", []) or []) != list(
        action_inputs.get("expected_source_classes", []) or []
    ):
        raise RunKernelTransitionError(
            "follow-up evidence intake observation expected_source_classes do not "
            "match authorized action"
        )
    if list(intake_state.get("expected_source_classes", []) or []) != list(
        execution_state.get("expected_source_classes", []) or []
    ):
        raise RunKernelTransitionError(
            "follow-up evidence intake observation expected_source_classes do not "
            "match execution state"
        )
    for action_field, state_field in (
        ("followup_execution_id", "execution_id"),
        ("execution_id", "execution_id"),
        ("followup_execution_observation_id", "observation_id"),
    ):
        if intake_state.get(action_field) != action_inputs.get(action_field):
            raise RunKernelTransitionError(
                "follow-up evidence intake observation "
                f"{action_field} does not match authorized action"
            )
        if intake_state.get(action_field) != execution_state.get(state_field):
            raise RunKernelTransitionError(
                "follow-up evidence intake observation "
                f"{action_field} does not match execution state"
            )
    if action_inputs.get("fixture_execution_mode") != "fixture_only":
        raise RunKernelTransitionError(
            "follow-up evidence intake action must be bound to fixture_only mode"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise RunKernelTransitionError(
            "follow-up evidence intake action must keep provider execution unlicensed"
        )
    if action_inputs.get("evidence_ledger_intake_mode") != (
        "fixture_only_followup_intake"
    ):
        raise RunKernelTransitionError(
            "follow-up evidence intake action must be fixture-only"
        )


def _validate_followup_sufficiency_recheck_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_recheck_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "evidence_ledger_projection_digest",
    ):
        if observed_recheck_state.get(binding_field) != action_inputs.get(binding_field):
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck observation "
                f"{binding_field} does not match authorized action"
            )
    if _followup_token_list(
        observed_recheck_state.get("requirement_ids")
    ) != _followup_token_list(action_inputs.get("requirement_ids")):
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck observation requirement_ids do not "
            "match authorized action"
        )
    if _followup_token_list(
        observed_recheck_state.get("expected_source_classes")
    ) != _followup_token_list(action_inputs.get("expected_source_classes")):
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck observation expected_source_classes do "
            "not match authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck action must keep provider unlicensed"
        )
    if action_inputs.get("sufficiency_recheck_mode") != (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    ):
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck action must be fixture-only"
        )
    if action_inputs.get("final_answer_packet_deferred") is not True:
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck action must defer FinalAnswerPacket"
        )
    if action_inputs.get("author_activation_allowed") is not False:
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck action must keep Author closed"
        )
    if action_inputs.get("citation_behavior_changed") is not False:
        raise RunKernelTransitionError(
            "follow-up sufficiency recheck action must not change citations"
        )


def _validate_followup_final_answer_packet_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_packet_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_sufficiency_recheck_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "evidence_ledger_projection_digest",
        "sufficiency_judgment_digest",
        "followup_sufficiency_recheck_digest",
    ):
        if observed_packet_state.get(binding_field) != action_inputs.get(
            binding_field
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket observation "
                f"{binding_field} does not match authorized action"
            )
    if _followup_token_list(
        observed_packet_state.get("requirement_ids")
    ) != _followup_token_list(action_inputs.get("requirement_ids")):
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket observation requirement_ids do not "
            "match authorized action"
        )
    if _followup_token_list(
        observed_packet_state.get("expected_source_classes")
    ) != _followup_token_list(action_inputs.get("expected_source_classes")):
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket observation expected_source_classes do "
            "not match authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket action must keep provider unlicensed"
        )
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket action must be fixture-only"
        )
    if action_inputs.get("author_activation_allowed") is not False:
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket action must keep Author closed"
        )
    if action_inputs.get("citation_rendering_changed") is not False:
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket action must not render citations"
        )
    if action_inputs.get("product_answer_behavior_changed") is not False:
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket action must not change product answers"
        )
    if action_inputs.get("live_validation_not_run") is not True:
        raise RunKernelTransitionError(
            "follow-up FinalAnswerPacket action must not run live validation"
        )


def _validate_followup_author_gate_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_gate_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_final_answer_packet_id",
        "packet_preparation_id",
        "packet_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "author_gate_mode",
        "final_answer_packet_digest",
        "final_answer_authority_projection_digest",
    ):
        if observed_gate_state.get(binding_field) != action_inputs.get(
            binding_field
        ):
            raise RunKernelTransitionError(
                "follow-up Author gate observation "
                f"{binding_field} does not match authorized action"
            )
    if _followup_token_list(
        observed_gate_state.get("requirement_ids")
    ) != _followup_token_list(action_inputs.get("requirement_ids")):
        raise RunKernelTransitionError(
            "follow-up Author gate observation requirement_ids do not match "
            "authorized action"
        )
    if _followup_token_list(
        observed_gate_state.get("expected_source_classes")
    ) != _followup_token_list(action_inputs.get("expected_source_classes")):
        raise RunKernelTransitionError(
            "follow-up Author gate observation expected_source_classes do not "
            "match authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise RunKernelTransitionError(
            "follow-up Author gate action must keep provider unlicensed"
        )
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise RunKernelTransitionError(
            "follow-up Author gate action must consume fixture-only packet"
        )
    if action_inputs.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
        raise RunKernelTransitionError(
            "follow-up Author gate action must be fixture-only"
        )
    for flag in (
        "author_activation_allowed",
        "author_executor_invoked",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
    ):
        if action_inputs.get(flag) is not False:
            raise RunKernelTransitionError(
                f"follow-up Author gate action must keep {flag}=False"
            )
    if action_inputs.get("author_execution_deferred") is not True:
        raise RunKernelTransitionError(
            "follow-up Author gate action must defer Author execution"
        )
    if action_inputs.get("live_validation_not_run") is not True:
        raise RunKernelTransitionError(
            "follow-up Author gate action must not run live validation"
        )


def _validate_followup_author_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_author_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_final_answer_packet_id",
        "packet_preparation_id",
        "followup_author_gate_id",
        "author_gate_id",
        "packet_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "author_gate_mode",
        "fixture_author_observation_mode",
        "final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "followup_author_gate_digest",
    ):
        if observed_author_state.get(binding_field) != action_inputs.get(
            binding_field
        ):
            raise RunKernelTransitionError(
                "follow-up Author observation "
                f"{binding_field} does not match authorized action"
            )
    if _followup_token_list(
        observed_author_state.get("requirement_ids")
    ) != _followup_token_list(action_inputs.get("requirement_ids")):
        raise RunKernelTransitionError(
            "follow-up Author observation requirement_ids do not match "
            "authorized action"
        )
    if _followup_token_list(
        observed_author_state.get("expected_source_classes")
    ) != _followup_token_list(action_inputs.get("expected_source_classes")):
        raise RunKernelTransitionError(
            "follow-up Author observation expected_source_classes do not match "
            "authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise RunKernelTransitionError(
            "follow-up Author observation action must keep provider unlicensed"
        )
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise RunKernelTransitionError(
            "follow-up Author observation action must consume fixture-only packet"
        )
    if action_inputs.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
        raise RunKernelTransitionError(
            "follow-up Author observation action must consume fixture-only gate"
        )
    if action_inputs.get("fixture_author_observation_mode") != (
        FOLLOWUP_AUTHOR_OBSERVATION_MODE
    ):
        raise RunKernelTransitionError(
            "follow-up Author observation action must be fixture-only"
        )
    for flag in (
        "author_activation_allowed",
        "author_executor_invoked",
        "model_called",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
        "final_text_included",
    ):
        if action_inputs.get(flag) is not False:
            raise RunKernelTransitionError(
                f"follow-up Author observation action must keep {flag}=False"
            )
    if action_inputs.get("author_execution_deferred") is not True:
        raise RunKernelTransitionError(
            "follow-up Author observation action must defer Author execution"
        )
    if action_inputs.get("live_validation_not_run") is not True:
        raise RunKernelTransitionError(
            "follow-up Author observation action must not run live validation"
        )


def _build_followup_evidence_intake_ledger_observation(
    *,
    intake_state: Mapping[str, Any],
    execution_state: Mapping[str, Any],
) -> dict[str, Any]:
    summary = _safe_mapping(execution_state.get("sanitized_fixture_result_summary"))
    requirement_id = _followup_intake_requirement_id(execution_state)
    expected_source_classes = _followup_expected_source_classes(execution_state)
    required_source_class = _followup_required_source_class(expected_source_classes)
    candidate_id = _followup_intake_candidate_id(execution_state)
    disposition = _followup_intake_candidate_disposition(
        result_status=execution_state.get("result_status"),
        bridge_only=bool(execution_state.get("bridge_only")),
        source_class=summary.get("source_class"),
        expected_source_classes=expected_source_classes,
    )
    candidate = {
        "candidate_id": candidate_id,
        "url": summary.get("url"),
        "title": summary.get("title") or summary.get("summary"),
        "domain": summary.get("domain"),
        "source_label": (
            "fixture follow-up intake "
            f"{execution_state.get('component_id')} "
            f"{execution_state.get('source_obligation_id')} "
            f"{execution_state.get('sealed_candidate_id')}"
        ),
        "provider_name": "followup_fixture",
        "provider_role": execution_state.get("provider_job_kind"),
        "retrieval_pass_id": execution_state.get("observation_id"),
        "query_ref": "fixture_only_followup_intake",
        "action_ref": execution_state.get("execution_id"),
        "source_tier": summary.get("source_tier")
        or _followup_default_source_tier(required_source_class),
        "source_class": summary.get("source_class") or "unknown",
        "currentness_signal": summary.get("currentness_signal") or "fixture_current",
        "readable_status": summary.get("readable_status")
        or (
            "readable"
            if execution_state.get("result_status") == "fixture_success"
            else "not_readable"
        ),
        "fetchable_status": summary.get("fetchable_status")
        or (
            "fetchable"
            if execution_state.get("result_status") == "fixture_success"
            else "not_fetchable"
        ),
        "disposition": disposition,
        "record_kind": "fact",
        "requirement_id": requirement_id,
        "eligible_for_stronger_obligation": (
            disposition == "accepted"
            and bool(
                summary.get("eligible_for_stronger_obligation")
                or summary.get("source_tier") in {"official", "primary", "canonical"}
            )
        ),
        "final_evidence_eligible": False,
        "reason": _followup_intake_candidate_reason(
            result_status=execution_state.get("result_status"),
            bridge_only=bool(execution_state.get("bridge_only")),
            disposition=disposition,
        ),
        "followup_execution_id": execution_state.get("execution_id"),
        "followup_execution_observation_id": execution_state.get("observation_id"),
        "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
        "component_id": execution_state.get("component_id"),
    }
    return {
        "observation_id": f"ledger:{execution_state.get('execution_id')}",
        "observation_source": "followup_fixture_evidence_intake",
        "requirements": [
            {
                "requirement_id": requirement_id,
                "requirement_kind": _followup_requirement_kind(required_source_class),
                "origin_ref": (
                    f"followup_fixture_execution:{execution_state.get('execution_id')}"
                ),
                "required_source_class": required_source_class,
                "required_source_tier": _followup_default_source_tier(
                    required_source_class
                ),
                "required_currentness": summary.get("required_currentness")
                or summary.get("currentness_signal")
                or "current",
            }
        ],
        "candidates": [candidate],
        "requirement_links": [
            {
                "requirement_id": requirement_id,
                "candidate_id": candidate_id,
                "link_reason": "followup_fixture_execution_binding",
                "link_status": disposition,
            }
        ],
        "followup_fixture_intake": {
            "schema_version": intake_state.get("schema_version"),
            "run_id": execution_state.get("run_id"),
            "checkpoint_id": execution_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": execution_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
            "followup_execution_id": execution_state.get("execution_id"),
            "followup_execution_observation_id": execution_state.get("observation_id"),
            "provider_job_kind": execution_state.get("provider_job_kind"),
            "component_id": execution_state.get("component_id"),
            "source_obligation_id": execution_state.get("source_obligation_id"),
            "requirement_ids": list(execution_state.get("requirement_ids", []) or []),
            "expected_source_classes": list(expected_source_classes),
            "result_status": execution_state.get("result_status"),
            "bridge_only": bool(execution_state.get("bridge_only")),
            "fixture_only_provenance": {
                "origin": "ag96i2b_followup_fixture_execution",
                "intake_bridge": "ag96i2c_followup_evidence_ledger_intake",
                "fixture_only": True,
                "live_provider_result": False,
                "provider_job_executor_connected": False,
            },
        },
    }


def _followup_evidence_intake_outcome(
    ledger_observation: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = list(ledger_observation.get("candidates", []) or [])
    candidate = _safe_mapping(next(iter(candidates), {}))
    disposition = candidate.get("disposition")
    admitted = disposition == "accepted"
    bridge_only = disposition == "contextual"
    return {
        "intake_status": (
            "fixture_intake_admitted"
            if admitted
            else (
                "fixture_bridge_only_recorded"
                if bridge_only
                else "fixture_no_admission_recorded"
            )
        ),
        "evidence_ledger_candidate_admitted": admitted,
        "source_obligation_satisfied": admitted,
    }


def _followup_intake_requirement_id(execution_state: Mapping[str, Any]) -> str:
    requirement_ids = list(execution_state.get("requirement_ids", []) or [])
    requirement_id = next(iter(requirement_ids), None) or execution_state.get(
        "source_obligation_id"
    )
    text = _followup_token(requirement_id) or "followup_requirement"
    if ":" not in text:
        return f"source_requirement:{text}"
    return text


def _followup_intake_candidate_id(execution_state: Mapping[str, Any]) -> str:
    return _followup_token(
        "followup_fixture:"
        f"{execution_state.get('sealed_candidate_id')}:"
        f"{execution_state.get('execution_id')}"
    )


def _followup_expected_source_classes(
    execution_state: Mapping[str, Any],
) -> tuple[str, ...]:
    expected = [
        _followup_token(item)
        for item in list(execution_state.get("expected_source_classes", []) or [])
    ]
    expected = [item for item in expected if item and item != "[redacted]"]
    if expected:
        return tuple(expected)
    job_kind = _followup_token(execution_state.get("provider_job_kind"))
    by_job = {
        "official_current_candidate_acquisition": (
            "official_government",
            "official_current_rules",
        ),
        "legal_current_primary_acquisition": (
            "primary_legal",
            "legal_or_regulatory_text",
        ),
        "canonical_doc_acquisition": ("canonical", "primary_source_documents"),
        "source_bound_numeric_extraction_calculation_support": (
            "sourced_numeric_values",
        ),
        "conflict_currentness_check": ("current_primary_or_official",),
        "reconciliation_support": ("source_family_map",),
        "fetch_read_extract": ("answer_bearing_extract",),
    }
    return by_job.get(job_kind, ("answer_bearing_candidate",))


def _followup_required_source_class(expected_source_classes: Sequence[str]) -> str:
    preferred = (
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "current_primary_or_official",
        "sourced_numeric_values",
    )
    for item in preferred:
        if item in expected_source_classes:
            return item
    return next(iter(expected_source_classes), "unknown")


def _followup_intake_candidate_disposition(
    *,
    result_status: Any,
    bridge_only: bool,
    source_class: Any,
    expected_source_classes: Sequence[str],
) -> str:
    if bridge_only:
        return "contextual"
    if (
        result_status == "fixture_success"
        and _followup_token(source_class) in expected_source_classes
    ):
        return "accepted"
    return "rejected"


def _followup_intake_candidate_reason(
    *,
    result_status: Any,
    bridge_only: bool,
    disposition: str,
) -> str:
    if bridge_only:
        return "bridge_only_fixture_result_not_satisfying"
    if result_status == "fixture_success" and disposition != "accepted":
        return "fixture_success_source_class_outside_sealed_contract"
    if result_status == "fixture_success":
        return "fixture_success_followup_evidence_intake"
    return f"{_followup_token(result_status)}_not_admitted_as_satisfying_evidence"


def _followup_default_source_tier(required_source_class: str) -> str | None:
    if required_source_class in {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
    }:
        return "official"
    return None


def _followup_requirement_kind(required_source_class: str) -> str:
    if required_source_class in {"official_current_rules", "current_primary_or_official"}:
        return "official_current"
    if required_source_class == "legal_or_regulatory_text":
        return "legal"
    if required_source_class in {"primary_source_documents", "archival_primary_text"}:
        return "canonical"
    return "general"


def _followup_token(value: Any, *, limit: int = 220) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        return ""
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def _followup_token_list(value: Any) -> list[str]:
    if value is None or isinstance(value, str):
        values = [value] if value else []
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        values = [value]
    out: list[str] = []
    for item in values:
        token = _followup_token(item)
        if token and token not in out:
            out.append(token)
    return out


__all__ = [
    "AUTHOR_EXECUTION_STAGE",
    "FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_AUTHORIZATION_STAGE",
    "FOLLOWUP_EVIDENCE_INTAKE_STAGE",
    "FOLLOWUP_EXECUTION_STAGE",
    "FOLLOWUP_AUTHOR_GATE_STAGE",
    "FOLLOWUP_AUTHOR_OBSERVATION_STAGE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_SUFFICIENCY_RECHECK_STAGE",
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
