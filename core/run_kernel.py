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
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND,
    FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON,
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
)
from core.followup_runkernel_reducers import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    FollowupRunKernelReducerError,
    ag96i3m2_admission_review_authorization_projection,
    ag96i3m2_intake_binding_authorization_projection,
    build_final_answer_authority_projection,
    build_followup_author_gate_projection,
    build_followup_author_observation_projection,
    build_followup_authorization_projection,
    build_followup_evidence_intake_ledger_observation,
    build_followup_evidence_intake_projection,
    build_followup_execution_projection,
    build_followup_final_answer_packet_projection,
    build_followup_sufficiency_recheck_projection,
    followup_evidence_intake_outcome,
    followup_expected_source_classes,
    followup_sealed_candidate,
    require_followup_flags_false,
    validate_followup_author_gate_observation_binding,
    validate_followup_author_observation_binding,
    validate_followup_evidence_intake_action_binding,
    validate_followup_execution_action_binding,
    validate_followup_final_answer_packet_observation_binding,
    validate_followup_provider_job_execution_action_binding,
    validate_followup_sufficiency_recheck_observation_binding,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS as _FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS as _FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_EXECUTION_FALSE_FLAGS as _FOLLOWUP_EXECUTION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_INTAKE_FALSE_FLAGS as _FOLLOWUP_INTAKE_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_PACKET_FALSE_FLAGS as _FOLLOWUP_PACKET_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS as _FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_RECHECK_FALSE_FLAGS as _FOLLOWUP_RECHECK_FALSE_FLAGS,
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
FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE = "followup_provider_job_execution"
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
    FOLLOWUP_PROVIDER_JOB_EXECUTE = "followup_provider_job_execute"
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
    FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED = (
        "followup_provider_job_execution_observed"
    )
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
        candidate = _followup_checked(
            followup_sealed_candidate,
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

    def authorize_followup_provider_job_execution(
        self,
        *,
        candidate_id: str,
        reason: str = "ag96i3a_offline_followup_provider_job_execution",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_authorization_state:
            raise RunKernelTransitionError(
                "follow-up provider-job execution requires reduced follow-up "
                "authorization state"
            )
        candidate = _followup_checked(
            followup_sealed_candidate,
            self.state.followup_authorization_state,
            candidate_id,
        )
        if candidate.get("provider_job_kind") != FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND:
            raise RunKernelTransitionError(
                "AG-96I3A only authorizes official_current_candidate_acquisition"
            )
        expected_update = _safe_mapping(
            candidate.get("expected_evidence_ledger_custody_update")
        )
        expected_source_classes = _string_list(expected_update.get("source_classes"))
        if not expected_source_classes or "[redacted]" in expected_source_classes:
            expected_source_classes = [
                "official_government",
                "official_current_rules",
            ]
        if not set(expected_source_classes).intersection(
            {"official_government", "official_current_rules"}
        ):
            raise RunKernelTransitionError(
                "follow-up provider-job execution requires official/current source classes"
            )
        authorized_query_ref = _clean_text(
            candidate.get("authorized_query_ref"),
            limit=180,
        )
        authorized_query = _clean_text(candidate.get("authorized_query"), limit=300)
        if not (authorized_query_ref or authorized_query):
            raise RunKernelTransitionError(
                "follow-up provider-job execution requires authorized query/ref"
            )
        budget_debit = _safe_mapping(candidate.get("budget_debit"))
        _require_followup_provider_job_budget(
            authorization_state=self.state.followup_authorization_state,
            budget_debit=budget_debit,
        )
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "checkpoint_id": self.state.followup_authorization_state.get(
                "checkpoint_id"
            ),
            "followup_authorization_consumption_id": (
                self.state.followup_authorization_state.get("consumption_id")
            ),
            "sealed_candidate_id": candidate.get("candidate_id"),
            "execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
            "provider_job_kind": candidate.get("provider_job_kind"),
            "component_id": candidate.get("component_id"),
            "source_obligation_id": candidate.get("source_obligation_id"),
            "requirement_ids": candidate.get("requirement_ids", []),
            "expected_source_classes": expected_source_classes,
            "expected_evidence_ledger_custody_update": expected_update,
            "budget_debit": budget_debit,
            "authorized_query_ref": authorized_query_ref,
            "authorized_query": authorized_query,
            "provider_execution_licensed": False,
            "live_provider_call_executed": False,
            "search_executed": False,
            "retrieval_executed": False,
            "fetch_executed": False,
            "model_called": False,
            "author_activation_allowed": False,
            "author_executor_invoked": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
        }
        return self.authorize(
            stage=FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
            action_type=ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED
            ),
        )

    def authorize_followup_evidence_intake(
        self,
        *,
        reason: str = "ag96i2c_followup_fixture_evidence_ledger_intake",
        inputs: Mapping[str, Any] | None = None,
        ag96i3l_admission_review_candidate: Mapping[str, Any] | None = None,
        evidence_ledger_intake_binding: Any | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_execution_state:
            raise RunKernelTransitionError(
                "follow-up evidence intake requires reduced follow-up execution state"
            )
        execution_state = self.state.followup_execution_state
        caller_inputs = dict(inputs or {})
        requested_mode = caller_inputs.get("evidence_ledger_intake_mode")
        candidate_projection = (
            ag96i3m2_admission_review_authorization_projection(
                ag96i3l_admission_review_candidate
            )
            if ag96i3l_admission_review_candidate is not None
            else {}
        )
        binding_projection = (
            ag96i3m2_intake_binding_authorization_projection(
                evidence_ledger_intake_binding
            )
            if evidence_ledger_intake_binding is not None
            else {}
        )
        ag96i3m2_intake_requested = bool(
            requested_mode == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
            or candidate_projection
            or binding_projection
        )
        merged_inputs = {
            **caller_inputs,
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
            "execution_mode": execution_state.get("execution_mode")
            or execution_state.get("fixture_execution_mode"),
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
            "authorized_query_ref": execution_state.get("authorized_query_ref"),
            "authorized_query": execution_state.get("authorized_query"),
            "provider_execution_licensed": False,
            "evidence_ledger_intake_mode": (
                AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
                if ag96i3m2_intake_requested
                else (
                    "bounded_provider_job_offline_followup_intake"
                    if (
                        execution_state.get("execution_mode")
                        == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
                    )
                    else "fixture_only_followup_intake"
                )
            ),
            "expected_observation_record_type": (
                "followup_evidence_intake_consumption_record"
            ),
        }
        if ag96i3m2_intake_requested:
            merged_inputs["ag96i3m2_admission_review_candidate"] = (
                candidate_projection
            )
            merged_inputs["ag96i3m2_evidence_ledger_intake_binding"] = (
                binding_projection
            )
        if merged_inputs.get("execution_mode") not in {
            "fixture_only",
            FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
        }:
            raise RunKernelTransitionError(
                "follow-up evidence intake only authorizes known execution modes"
            )
        if merged_inputs.get("evidence_ledger_intake_mode") not in {
            "fixture_only_followup_intake",
            "bounded_provider_job_offline_followup_intake",
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
        }:
            raise RunKernelTransitionError(
                "follow-up evidence intake only authorizes known intake modes"
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
        execution_mode = (
            intake_state.get("execution_mode")
            or intake_state.get("fixture_execution_mode")
        )
        if intake_state.get("evidence_ledger_intake_mode") not in {
            "fixture_only_followup_intake",
            "bounded_provider_job_offline_followup_intake",
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
        }:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires known intake state"
            )
        if intake_state.get(
            "evidence_ledger_intake_mode"
        ) == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE:
            if intake_state.get("runtime_evidence_intake_occurred") is not True:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck requires runtime "
                    "EvidenceLedger intake"
                )
            if intake_state.get("source_obligation_satisfied") not in {
                True,
                False,
            }:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck requires explicit source "
                    "obligation posture"
                )
            if intake_state.get("sufficiency_judgment_recheck_deferred") is not True:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck requires deferred "
                    "SufficiencyJudgment"
                )
            if intake_state.get("citation_eligible") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must keep citations closed"
                )
            if intake_state.get("final_evidence_satisfied") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must not consume final evidence"
                )
            if intake_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must keep Author closed"
                )
            if intake_state.get("final_answer_packet_updated") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must not update FinalAnswerPacket"
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
            "execution_mode": execution_mode,
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
                followup_expected_source_classes(recheck_state)
            ),
            "fixture_execution_mode": recheck_state.get("fixture_execution_mode"),
            "execution_mode": recheck_state.get("execution_mode")
            or recheck_state.get("fixture_execution_mode"),
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
            self.state.followup_authorization_projection = (
                build_followup_authorization_projection(
                    followup_state=followup_state,
                    execution_gate=_safe_mapping(gate),
                    behavior_boundary_flags=_safe_mapping(
                        followup_state.get("behavior_boundary_flags")
                    ),
                )
            )
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
            _followup_checked(
                validate_followup_execution_action_binding,
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
            _followup_checked(
                require_followup_flags_false,
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
            self.state.followup_execution_projection = (
                build_followup_execution_projection(
                    execution_state=execution_state,
                    execution_gate=gate,
                    behavior_boundary_flags=flags,
                    budget_semantics=_safe_mapping(
                        execution_state.get("budget_semantics")
                    ),
                )
            )
            self.state.followup_execution_history.append(
                deepcopy(self.state.followup_execution_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_execution_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE:
            observed_execution_state = _safe_mapping(
                observation.payload.get("followup_execution_state")
            )
            if not observed_execution_state:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution observation requires "
                    "followup_execution_state"
                )
            if not self.state.followup_authorization_state:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution requires existing "
                    "authorization state"
                )
            if (
                observed_execution_state.get("followup_authorization_consumption_id")
                != self.state.followup_authorization_state.get("consumption_id")
            ):
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must reference current "
                    "authorization state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_provider_job_execution_action_binding,
                action_inputs=action_inputs,
                execution_state=observed_execution_state,
            )
            if _followup_provider_job_closed_surface_claimed(
                observed_execution_state
            ):
                raise RunKernelTransitionError(
                    "follow-up provider-job execution observation claims closed "
                    "answer authority"
                )
            flags = _safe_mapping(
                observed_execution_state.get("behavior_boundary_flags")
            )
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS,
                context="follow-up provider-job execution observation",
            )
            for field_name in (
                "provider_execution_licensed",
                "live_provider_call_executed",
                "search_executed",
                "retrieval_executed",
                "fetch_executed",
                "model_called",
            ):
                if observed_execution_state.get(field_name) is not False:
                    raise RunKernelTransitionError(
                        "follow-up provider-job execution observation requires "
                        f"{field_name}=False"
                    )
            if observed_execution_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must not run live validation"
                )
            if observed_execution_state.get("offline_live_shaped_execution") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must be offline live-shaped"
                )
            if observed_execution_state.get("adapter_result_injected") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution requires injected adapter result"
                )
            if observed_execution_state.get("evidence_ledger_intake_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must defer EvidenceLedger intake"
                )
            if observed_execution_state.get("evidence_ledger_evidence_admitted") is not False:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must not admit EvidenceLedger evidence"
                )
            summary = _safe_mapping(
                observed_execution_state.get("sanitized_candidate_summary")
            )
            canonical_budget_semantics = (
                _canonical_followup_provider_job_budget_semantics(
                    _safe_mapping(action_inputs.get("budget_debit"))
                )
            )
            canonical_execution_gate = (
                _canonical_followup_provider_job_execution_gate()
            )
            canonical_redaction_posture = (
                _canonical_followup_provider_job_redaction_posture()
            )
            execution_state = {
                **observed_execution_state,
                "owner": "RunKernel.FollowupProviderJobExecution",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "run_id": action_inputs.get("run_id"),
                "checkpoint_id": action_inputs.get("checkpoint_id"),
                "followup_authorization_consumption_id": action_inputs.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": action_inputs.get("sealed_candidate_id"),
                "execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
                "provider_job_kind": action_inputs.get("provider_job_kind"),
                "component_id": action_inputs.get("component_id"),
                "source_obligation_id": action_inputs.get("source_obligation_id"),
                "requirement_ids": action_inputs.get("requirement_ids", []),
                "expected_source_classes": action_inputs.get(
                    "expected_source_classes",
                    [],
                ),
                "expected_evidence_ledger_custody_update": action_inputs.get(
                    "expected_evidence_ledger_custody_update",
                    {},
                ),
                "budget_debit": action_inputs.get("budget_debit", {}),
                "authorized_query_ref": action_inputs.get("authorized_query_ref"),
                "authorized_query": action_inputs.get("authorized_query"),
                "sanitized_candidate_summary": summary,
                "provider_execution_licensed": False,
                "live_provider_call_executed": False,
                "search_executed": False,
                "retrieval_executed": False,
                "fetch_executed": False,
                "model_called": False,
                "live_validation_not_run": True,
                "source_obligation_satisfied": False,
                "final_evidence_satisfied": False,
                "citation_eligible": False,
                "sufficiency_ready": False,
                "final_answer_packet_ready": False,
                "author_activation_allowed": False,
                "author_executor_invoked": False,
                "citation_rendering_changed": False,
                "citation_formatter_invoked": False,
                "product_answer_behavior_changed": False,
                "evidence_ledger_intake_deferred": True,
                "evidence_ledger_evidence_admitted": False,
                "budget_semantics": canonical_budget_semantics,
                "execution_gate": canonical_execution_gate,
                "redaction_posture": canonical_redaction_posture,
                "behavior_boundary_flags": {
                    **flags,
                    "provider_execution_licensed": False,
                    "live_provider_call_executed": False,
                    "provider_job_scheduled": False,
                    "provider_job_dispatched": False,
                    "search_executed": False,
                    "retrieval_executed": False,
                    "fetch_executed": False,
                    "model_called": False,
                    "query_generation_changed": False,
                    "retrieval_ranking_filtering_changed": False,
                    "pipeline_orchestrator_domain_logic_changed": False,
                    "evidence_ledger_mutated": False,
                    "sufficiency_judgment_rechecked": False,
                    "final_answer_packet_updated": False,
                    "author_executor_invoked": False,
                    "citation_formatter_invoked": False,
                    "citation_behavior_changed": False,
                    "product_answer_behavior_changed": False,
                    "final_answer_behavior_changed": False,
                },
            }
            self.state.followup_execution_state = execution_state
            canonical_flags = _safe_mapping(
                execution_state.get("behavior_boundary_flags")
            )
            self.state.followup_execution_projection = (
                build_followup_execution_projection(
                    execution_state=execution_state,
                    execution_gate=_safe_mapping(execution_state.get("execution_gate")),
                    behavior_boundary_flags=canonical_flags,
                    budget_semantics=canonical_budget_semantics,
                )
            )
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
            _followup_checked(
                validate_followup_evidence_intake_action_binding,
                action_inputs=action_inputs,
                execution_state=self.state.followup_execution_state,
                intake_state=intake_state,
            )
            flags = _safe_mapping(intake_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
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
            if intake_state.get("evidence_ledger_intake_mode") not in {
                "fixture_only_followup_intake",
                "bounded_provider_job_offline_followup_intake",
                AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
            }:
                raise RunKernelTransitionError(
                    "follow-up evidence intake requires known intake mode"
                )
            if intake_state.get("final_evidence_satisfied") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not satisfy final evidence"
                )
            if intake_state.get("citation_eligible") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not create citation eligibility"
                )
            if intake_state.get("author_activation_allowed") is True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not activate Author"
                )
            if intake_state.get("final_answer_packet_updated") is True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not update FinalAnswerPacket"
                )
            ledger_observation = build_followup_evidence_intake_ledger_observation(
                intake_state=intake_state,
                execution_state=self.state.followup_execution_state,
            )
            derived_outcome = followup_evidence_intake_outcome(ledger_observation)
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
                "ledger_followup_provider_job_intake": deepcopy(
                    ledger_observation.get("followup_provider_job_intake", {})
                ),
            }
            self.state.evidence_ledger.reduce_observation(ledger_observation)
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            self.state.projections[EVIDENCE_LEDGER_STAGE] = deepcopy(
                ledger_projection
            )
            self.state.followup_evidence_intake_state = intake_state
            self.state.followup_evidence_intake_projection = (
                build_followup_evidence_intake_projection(
                    intake_state=intake_state,
                    ledger_observation=ledger_observation,
                    ledger_projection=ledger_projection,
                    behavior_boundary_flags=flags,
                )
            )
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
            _followup_checked(
                validate_followup_sufficiency_recheck_observation_binding,
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
            _followup_checked(
                require_followup_flags_false,
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
            self.state.followup_sufficiency_recheck_projection = (
                build_followup_sufficiency_recheck_projection(
                    recheck_state=recheck_state,
                    behavior_boundary_flags=flags,
                )
            )
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
            _followup_checked(
                validate_followup_final_answer_packet_observation_binding,
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
            _followup_checked(
                require_followup_flags_false,
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
            self.state.final_answer_authority_projection = (
                build_final_answer_authority_projection(
                    packet_state=packet_state,
                    packet_projection=packet_projection,
                    author_payload_ref=author_payload_ref,
                    citation_eligible_source_ids=citation_eligible_source_ids,
                )
            )
            self.state.projections[FINAL_ANSWER_PACKET_STAGE] = deepcopy(
                self.state.final_answer_authority_projection
            )
            self.state.followup_final_answer_packet_projection = (
                build_followup_final_answer_packet_projection(
                    packet_state=packet_state,
                    packet_projection=packet_projection,
                    behavior_boundary_flags=flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                )
            )
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
            _followup_checked(
                validate_followup_author_gate_observation_binding,
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
            _followup_checked(
                require_followup_flags_false,
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
            self.state.followup_author_gate_projection = (
                build_followup_author_gate_projection(
                    gate_state=gate_state,
                    behavior_boundary_flags=flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                )
            )
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
            _followup_checked(
                validate_followup_author_observation_binding,
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
            _followup_checked(
                require_followup_flags_false,
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
            self.state.followup_author_observation_projection = (
                build_followup_author_observation_projection(
                    author_state=author_state,
                    behavior_boundary_flags=flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                    followup_author_gate_stage=FOLLOWUP_AUTHOR_GATE_STAGE,
                )
            )
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


def _followup_checked(callable_: Any, /, *args: Any, **kwargs: Any) -> Any:
    try:
        return callable_(*args, **kwargs)
    except FollowupRunKernelReducerError as exc:
        raise RunKernelTransitionError(str(exc)) from exc


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_text(item, limit=180)
        if text:
            token = text.casefold().replace("-", "_").replace(" ", "_")
            if token not in out:
                out.append(token)
    return out


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _require_followup_provider_job_budget(
    *,
    authorization_state: Mapping[str, Any],
    budget_debit: Mapping[str, Any],
) -> None:
    required = {
        "cost_points": budget_debit.get("cost_points"),
        "provider_calls": budget_debit.get("provider_calls"),
        "fetches_reserved": budget_debit.get("fetches_reserved"),
        "read_units_reserved": budget_debit.get("read_units_reserved"),
        "followup_rounds": budget_debit.get("followup_rounds"),
    }
    exhausted = [name for name, value in required.items() if _positive_int(value) <= 0]
    if exhausted:
        raise RunKernelTransitionError(
            "follow-up provider-job execution requires authorized budget debit for "
            + ", ".join(exhausted)
        )
    for decision in authorization_state.get("consumed_budget_decisions", []) or []:
        if not isinstance(decision, Mapping):
            continue
        if decision.get("debit_authorized_for_future_phase") is not True:
            continue
        planned = _safe_mapping(decision.get("planned_or_denied_debit"))
        if all(
            _positive_int(planned.get(name)) == _positive_int(budget_debit.get(name))
            for name in required
        ):
            return
    raise RunKernelTransitionError(
        "follow-up provider-job execution requires budget authorized by sealed state"
    )


def _canonical_followup_provider_job_budget_semantics(
    budget_debit: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "planned_debit_authorized": dict(budget_debit),
        "offline_provider_job_execution_did_not_incur_live_cost": True,
        "actual_provider_search_fetch_read_cost_incurred": False,
        "actual_provider_account_debited": False,
        "provider_cost_accounting_deferred": True,
    }


def _canonical_followup_provider_job_execution_gate() -> dict[str, Any]:
    return {
        "allowed_execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
        "provider_job_kind_allowlist": [FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND],
        "provider_execution_licensed": False,
        "provider_execution_available_in_this_phase": False,
        "offline_live_shaped_execution": True,
        "adapter_result_injected_required": True,
        "reason": FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON,
    }


def _canonical_followup_provider_job_redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_candidate_facts_only": True,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_text_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "provider_payload_retained": False,
        "provider_payloads_retained": False,
        "secrets_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_trace_retained": False,
    }


def _followup_provider_job_closed_surface_claimed(value: Any) -> bool:
    dangerous_true_keys = {
        "source_obligation_satisfied",
        "final_evidence_satisfied",
        "citation_eligible",
        "sufficiency_ready",
        "sufficiency_judgment_ready",
        "final_answer_packet_ready",
        "author_activation_allowed",
        "author_executor_invoked",
        "citation_rendered",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
        "final_answer_behavior_changed",
        "query_generation_changed",
        "query_mutation_changed",
        "provider_routing_changed",
        "provider_selection_changed",
        "provider_depth_changed",
        "search_depth_changed",
        "retrieval_ranking_filtering_changed",
        "raw_payload_retained",
        "raw_text_retained",
        "provider_payload_retained",
    }
    dangerous_false_keys = {
        "live_validation_not_run",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")
            if token in {
                "budget_semantics",
                "execution_gate",
                "redaction_posture",
            }:
                continue
            if token in dangerous_true_keys and item is True:
                return True
            if token in dangerous_false_keys and item is False:
                return True
            if _followup_provider_job_closed_surface_claimed(item):
                return True
    elif isinstance(value, (list, tuple, set, frozenset)):
        return any(_followup_provider_job_closed_surface_claimed(item) for item in value)
    return False


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


__all__ = [
    "AUTHOR_EXECUTION_STAGE",
    "FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_AUTHORIZATION_STAGE",
    "FOLLOWUP_EVIDENCE_INTAKE_STAGE",
    "FOLLOWUP_EXECUTION_STAGE",
    "FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE",
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
