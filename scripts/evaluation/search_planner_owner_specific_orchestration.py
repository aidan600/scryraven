"""Default-closed orchestration for owner-specific SearchPlanner evaluation."""

from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from core.cost_accounting import CostAccumulator
from core.query_production_runtime import (
    execute_initial_query_strategy_convergence,
)
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_planner_model_adapter import SearchPlannerModelAdapter
from core.text_utils import clean_json_response
from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation.brokered_model_origination_transport import (
    BrokeredModelRouteAuthorization,
    create_brokered_model_route_transport,
)
from scripts.evaluation.brokered_search_planner_semantic_judge import (
    BrokeredSearchPlannerSemanticJudge,
    BrokeredSemanticJudgeError,
    BrokeredSemanticJudgmentOutcome,
    SearchPlannerSemanticJudgeExecutionObservation,
    validate_semantic_result_execution_pair,
)
from scripts.evaluation.model_origination_evaluation_reporting import (
    ModelOriginationEvaluationDecisionCoordinator,
    ModelOriginationEvaluationReportAssembler,
)
from scripts.evaluation.model_origination_experiment_authority import (
    ExperimentDesign,
    PromptIdentity,
    TrialObservation,
    attribute_prompt_comparison,
    build_call_identity,
    build_experiment_identity,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
    EvaluationTransportResponse,
)
from scripts.evaluation.search_planner_mechanical_validation import (
    MechanicalValidationResult,
    validate_product_observation,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    GENERIC_BROKER_TRANSPORT_FACTORY_SPEC,
    OUTCOME_METRIC,
    OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION,
    OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
    PLANNER_ROLE,
    POLICY_CANONICALIZATION_VERSION,
    SEMANTIC_JUDGE_ROLE,
    STOCHASTIC_ATTRIBUTION_CEILING,
    OwnerSpecificAuthorizationError,
    OwnerSpecificLiveAuthorization,
    OwnerSpecificScenarioPacket,
    PlannerRouteAuthorization,
    SemanticJudgeRouteAuthorization,
    TrialScheduleEntry,
    canonical_sha256,
    normalize_repository_relative_path,
    validate_authorization_context,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CanonicalProductSearchPlannerBoundaryObserver,
    ProductBoundaryObservation,
)
from scripts.evaluation.search_planner_prompt_variant import (
    PromptVariantDispatchObservation,
    PromptVariantSpecification,
    dispatch_search_planner_prompt,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    SemanticJudgmentResult,
    build_semantic_judgment_request,
)

# fmt: off

OWNER_SPECIFIC_PLAN_SCHEMA_VERSION = (
    "search_planner_owner_specific_plan_v1"
)
OWNER_SPECIFIC_ORCHESTRATION_PACKET_SCHEMA_VERSION = (
    "search_planner_owner_specific_orchestration_packet_v1"
)
PLANNER_BROKER_EXECUTION_OBSERVATION_VERSION = (
    "search_planner_broker_execution_observation_v1"
)
_OUTPUT_ENVELOPE_IDENTITY = "strict_json_search_planner_proposal_v1"
_DIGEST_CHARS = frozenset("0123456789abcdef")


class OwnerSpecificOrchestrationError(RuntimeError):
    """Raised for an infrastructure or orchestration integrity stop."""


class ModelTransport(Protocol):
    def __call__(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
        maximum_input_tokens: int,
        maximum_output_tokens: int,
        correlation_id: str,
    ) -> EvaluationTransportResponse: ...


TransportFactory = Callable[
    [BrokeredModelRouteAuthorization],
    ModelTransport,
]


@dataclass(frozen=True, slots=True)
class PlannerBrokerExecutionObservation:
    schema_version: str
    owner: str
    call_id: str
    execution_identity_digest: str
    route_identity_digest: str
    dispatched_prompt_identity_digest: str
    response_digest: str
    response_length: int
    response_presence_posture: str
    generation_status: str
    generation_incomplete_reason_digest: str | None
    route_attestation: Mapping[str, Any]
    usage_attestation: Mapping[str, Any]
    token_accounting: Mapping[str, Any]
    cost_accounting_usd: str
    retention_posture: Mapping[str, bool]

    def __post_init__(self) -> None:
        if (
            self.schema_version
            != PLANNER_BROKER_EXECUTION_OBSERVATION_VERSION
        ):
            raise OwnerSpecificOrchestrationError(
                "Planner broker observation version is unsupported"
            )
        if self.owner != "SearchPlannerBrokerExecutionObservation":
            raise OwnerSpecificOrchestrationError(
                "Planner broker observation owner is invalid"
            )
        if not self.call_id:
            raise OwnerSpecificOrchestrationError(
                "Planner broker call ID must be explicit"
            )
        for label in (
            "execution_identity_digest",
            "route_identity_digest",
            "dispatched_prompt_identity_digest",
            "response_digest",
        ):
            _require_digest(getattr(self, label), label)
        if self.generation_incomplete_reason_digest is not None:
            _require_digest(
                self.generation_incomplete_reason_digest,
                "generation_incomplete_reason_digest",
            )
        if self.response_length < 0:
            raise OwnerSpecificOrchestrationError(
                "Planner response length cannot be negative"
            )
        if self.response_presence_posture not in {"PRESENT", "MISSING"}:
            raise OwnerSpecificOrchestrationError(
                "Planner response-presence posture is unsupported"
            )
        _nonnegative_decimal(
            self.cost_accounting_usd,
            "Planner call cost",
        )
        if (
            set(self.retention_posture)
            != {
                "raw_planner_prompt_retained",
                "raw_planner_response_retained",
                "provider_payload_retained",
            }
            or any(self.retention_posture.values())
        ):
            raise OwnerSpecificOrchestrationError(
                "Planner broker retention posture is invalid"
            )
        _reject_outer_forbidden_material(asdict(self))

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)

    @property
    def observation_digest(self) -> str:
        return canonical_sha256(self.to_packet())


class SearchPlannerBrokerBridge:
    """Bridge the product ask_model signature to one authorized broker call."""

    def __init__(
        self,
        *,
        transport: ModelTransport,
        route: PlannerRouteAuthorization,
        prompt_variant: PromptVariantSpecification,
        arm_id: str,
        call_id: str,
    ) -> None:
        route.__post_init__()
        prompt_variant.__post_init__()
        self._transport = transport
        self._route = route
        self._prompt_variant = prompt_variant
        self._arm_id = arm_id
        self._call_id = call_id
        self.dispatch_observation: (
            PromptVariantDispatchObservation | None
        ) = None
        self.execution_observation: (
            PlannerBrokerExecutionObservation | None
        ) = None

    def __call__(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if self.dispatch_observation is not None:
            raise OwnerSpecificOrchestrationError(
                "Planner bridge permits exactly one physical call"
            )
        expected = {
            "provider": self._route.provider,
            "model": self._route.model,
            "effort": self._route.reasoning_effort,
            "require_json": True,
            "use_reasoning": True,
            "max_tokens": self._route.maximum_output_tokens,
            "cost_phase": "search_planner",
        }
        if any(kwargs.get(key) != value for key, value in expected.items()):
            prompt = ""
            system_prompt = ""
            raise OwnerSpecificOrchestrationError(
                "product ask_model arguments differ from the exact Planner route"
            )
        if kwargs.get("cost_accumulator") is None:
            prompt = ""
            system_prompt = ""
            raise OwnerSpecificOrchestrationError(
                "product ask_model call omitted the canonical cost seam"
            )
        completion_sink = kwargs.get("safe_response_envelope_sink")
        unknown = set(kwargs) - {
            *expected,
            "cost_accumulator",
            "safe_response_envelope_sink",
        }
        if unknown:
            prompt = ""
            system_prompt = ""
            raise OwnerSpecificOrchestrationError(
                "product ask_model call contains unexpected arguments"
            )
        dispatch = dispatch_search_planner_prompt(
            product_built_prompt=prompt,
            system_prompt=system_prompt,
            arm_id=self._arm_id,
            specification=self._prompt_variant,
        )
        self.dispatch_observation = dispatch.observation
        route_digest = canonical_sha256(self._route.to_packet())
        execution_digest = canonical_sha256(
            {
                "call_id": self._call_id,
                "route_identity_digest": route_digest,
                "dispatched_prompt_identity_digest": (
                    dispatch.observation.dispatched_full_prompt_digest
                ),
                "system_prompt_digest": (
                    dispatch.observation.dispatched_system_prompt_digest
                ),
            }
        )
        response = self._transport(
            role=self._route.role,
            prompt=dispatch.dispatched_prompt,
            system_prompt=system_prompt,
            provider=self._route.provider,
            model=self._route.model,
            maximum_input_tokens=self._route.maximum_input_tokens,
            maximum_output_tokens=self._route.maximum_output_tokens,
            correlation_id=self._call_id,
        )
        prompt = ""
        system_prompt = ""
        safe = _validate_transport_response(
            response,
            role=self._route.role,
            provider=self._route.provider,
            model=self._route.model,
            reasoning_effort=self._route.reasoning_effort,
            maximum_input_tokens=self._route.maximum_input_tokens,
            maximum_output_tokens=self._route.maximum_output_tokens,
            per_call_cost_ceiling_usd=(
                self._route.per_call_cost_ceiling_usd
            ),
        )
        output_text = str(response.output or "")
        incomplete_reason_digest = (
            sha256(
                str(response.generation_incomplete_reason).encode(
                    "utf-8"
                )
            ).hexdigest()
            if response.generation_incomplete_reason is not None
            else None
        )
        self.execution_observation = PlannerBrokerExecutionObservation(
            schema_version=(
                PLANNER_BROKER_EXECUTION_OBSERVATION_VERSION
            ),
            owner="SearchPlannerBrokerExecutionObservation",
            call_id=self._call_id,
            execution_identity_digest=execution_digest,
            route_identity_digest=route_digest,
            dispatched_prompt_identity_digest=(
                dispatch.observation.dispatched_full_prompt_digest
            ),
            response_digest=sha256(
                output_text.encode("utf-8")
            ).hexdigest(),
            response_length=len(output_text),
            response_presence_posture=(
                "PRESENT"
                if response.output_text_present and output_text
                else "MISSING"
            ),
            generation_status=response.generation_status,
            generation_incomplete_reason_digest=(
                incomplete_reason_digest
            ),
            route_attestation=safe["route_attestation"],
            usage_attestation=safe["usage_attestation"],
            token_accounting=safe["token_accounting"],
            cost_accounting_usd=safe["cost_accounting_usd"],
            retention_posture={
                "raw_planner_prompt_retained": False,
                "raw_planner_response_retained": False,
                "provider_payload_retained": False,
            },
        )
        if callable(completion_sink):
            posture = (
                "completed"
                if response.generation_status == "completed" and output_text
                else "length_limited"
                if response.max_output_tokens_reached
                else "empty"
                if not output_text
                else "other_safe"
            )
            completion_sink({"provider_completion_posture": posture})
        if (
            response.generation_status != "completed"
            or not response.output_text_present
        ):
            output_text = ""
        response = None
        return output_text

    def safe_usage_ref(self) -> dict[str, Any]:
        if self.execution_observation is None:
            return {}
        observation = self.execution_observation
        return {
            "call_id": observation.call_id,
            "usage_posture": observation.usage_attestation.get(
                "posture"
            ),
            "input_tokens": observation.token_accounting.get(
                "input_tokens"
            ),
            "output_tokens": observation.token_accounting.get(
                "output_tokens"
            ),
            "cost_usd": observation.cost_accounting_usd,
        }

    def safe_execution_ref(self) -> dict[str, Any]:
        if self.execution_observation is None:
            return {}
        observation = self.execution_observation
        return {
            "call_id": observation.call_id,
            "execution_identity_digest": (
                observation.execution_identity_digest
            ),
            "route_identity_digest": observation.route_identity_digest,
            "generation_status": observation.generation_status,
            "retention_posture": "sanitized_only",
        }


@dataclass(slots=True)
class _CapturedPlannerAdapter:
    delegate: SearchPlannerModelAdapter
    planner_input: Mapping[str, Any] | None = field(
        default=None,
        repr=False,
    )
    validated_proposal_returned: bool = False

    def produce(
        self,
        planner_input: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.planner_input = deepcopy(dict(planner_input))
        self.validated_proposal_returned = False
        proposal = self.delegate.produce(planner_input)
        self.validated_proposal_returned = True
        return proposal


@dataclass(slots=True)
class _ProductTrialExecution:
    schedule: TrialScheduleEntry
    product_observation: ProductBoundaryObservation
    mechanical_result: MechanicalValidationResult
    prompt_dispatch: PromptVariantDispatchObservation
    planner_execution: PlannerBrokerExecutionObservation
    planner_input: Mapping[str, Any] = field(repr=False)
    proposed_plan: Mapping[str, Any] = field(repr=False)
    semantic_result: SemanticJudgmentResult | None
    semantic_execution: (
        SearchPlannerSemanticJudgeExecutionObservation | None
    )


class _BudgetLedger:
    """Reserve the exact manifest and enforce observed call/cost consumption."""

    def __init__(
        self,
        authorization: OwnerSpecificLiveAuthorization,
        *,
        started_at: float,
        clock: Callable[[], float],
    ) -> None:
        self._authorization = authorization
        self._clock = clock
        self._started_at = started_at
        self._reserved: dict[str, str] = {}
        for item in authorization.prompt_experiment.trial_schedule:
            self._reserved[item.planner_call_id] = "planner"
            self._reserved[item.primary_judge_call_id] = "primary"
            self._reserved[item.adversarial_judge_call_id] = (
                "adversarial"
            )
        if len(self._reserved) != (
            len(authorization.prompt_experiment.trial_schedule) * 3
        ):
            raise OwnerSpecificOrchestrationError(
                "call manifest reservation contains an identity collision"
            )
        self._attempted: list[str] = []
        self._completed: list[str] = []
        self._cost = Decimal("0")

    def check_elapsed(self) -> None:
        elapsed = self._clock() - self._started_at
        if elapsed < 0 or elapsed > (
            self._authorization.whole_evaluation_caps.maximum_wall_clock_seconds
        ):
            raise OwnerSpecificOrchestrationError(
                "whole-evaluation wall-clock cap was exceeded"
            )

    def before_call(self, *, role: str, call_id: str) -> None:
        self.check_elapsed()
        if call_id not in self._reserved:
            raise OwnerSpecificOrchestrationError(
                "transport call is absent from the reserved manifest"
            )
        if call_id in self._attempted:
            raise OwnerSpecificOrchestrationError(
                "transport call identity was already consumed"
            )
        call_kind = self._reserved[call_id]
        expected_role = (
            PLANNER_ROLE
            if call_kind == "planner"
            else SEMANTIC_JUDGE_ROLE
        )
        if role != expected_role:
            raise OwnerSpecificOrchestrationError(
                "transport role differs from the reserved call identity"
            )
        used_by_kind = sum(
            self._reserved[item] == call_kind
            for item in self._attempted
        )
        cap = {
            "planner": (
                self._authorization.planner_route.maximum_planner_calls
            ),
            "primary": (
                self._authorization.semantic_judge_route.maximum_primary_judge_calls
            ),
            "adversarial": (
                self._authorization.semantic_judge_route.maximum_adversarial_judge_calls
            ),
        }[call_kind]
        if used_by_kind >= cap:
            raise OwnerSpecificOrchestrationError(
                f"{call_kind} call cap would be exceeded"
            )
        if len(self._attempted) >= (
            self._authorization.whole_evaluation_caps.maximum_total_broker_calls
        ):
            raise OwnerSpecificOrchestrationError(
                "whole-evaluation broker-call cap would be exceeded"
            )
        self._attempted.append(call_id)

    def after_call(
        self,
        *,
        call_id: str,
        response: EvaluationTransportResponse,
        route: PlannerRouteAuthorization
        | SemanticJudgeRouteAuthorization,
    ) -> None:
        if call_id not in self._attempted:
            raise OwnerSpecificOrchestrationError(
                "unreserved response cannot consume budget"
            )
        safe = _validate_transport_response(
            response,
            role=route.role,
            provider=route.provider,
            model=route.model,
            reasoning_effort=route.reasoning_effort,
            maximum_input_tokens=route.maximum_input_tokens,
            maximum_output_tokens=route.maximum_output_tokens,
            per_call_cost_ceiling_usd=(
                route.per_call_cost_ceiling_usd
            ),
        )
        self._cost += Decimal(safe["cost_accounting_usd"])
        if self._cost > Decimal(
            self._authorization.whole_evaluation_caps.maximum_total_observed_cost_usd
        ):
            raise OwnerSpecificOrchestrationError(
                "whole-evaluation observed-cost cap was exceeded"
            )
        self._completed.append(call_id)
        self.check_elapsed()

    def snapshot(self) -> dict[str, Any]:
        counts = {
            kind: sum(
                self._reserved[item] == kind
                for item in self._attempted
            )
            for kind in ("planner", "primary", "adversarial")
        }
        return {
            "reserved_call_count": len(self._reserved),
            "attempted_call_count": len(self._attempted),
            "completed_call_count": len(self._completed),
            "planner_calls_consumed": counts["planner"],
            "primary_judge_calls_consumed": counts["primary"],
            "adversarial_judge_calls_consumed": counts["adversarial"],
            "total_observed_cost_usd": format(self._cost, "f"),
            "maximum_total_observed_cost_usd": (
                self._authorization.whole_evaluation_caps.maximum_total_observed_cost_usd
            ),
            "unused_authorized_call_ids": [
                item
                for item in self._reserved
                if item not in self._attempted
            ],
            "raw_material_retained": False,
        }


@dataclass(slots=True)
class _BudgetedTransport:
    delegate: ModelTransport
    route: PlannerRouteAuthorization | SemanticJudgeRouteAuthorization
    ledger: _BudgetLedger

    def __call__(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
        maximum_input_tokens: int,
        maximum_output_tokens: int,
        correlation_id: str,
    ) -> EvaluationTransportResponse:
        self.ledger.before_call(role=role, call_id=correlation_id)
        response = self.delegate(
            role=role,
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            maximum_input_tokens=maximum_input_tokens,
            maximum_output_tokens=maximum_output_tokens,
            correlation_id=correlation_id,
        )
        self.ledger.after_call(
            call_id=correlation_id,
            response=response,
            route=self.route,
        )
        return response


def build_plan_only_packet(
    *,
    repository_sha: str,
) -> dict[str, Any]:
    """Build a complete zero-live plan without inspecting credentials."""

    packet = {
        "schema_version": OWNER_SPECIFIC_PLAN_SCHEMA_VERSION,
        "owner": "SearchPlannerOwnerSpecificEvaluationOrchestration",
        "orchestrator_version": OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
        "repository_sha": repository_sha,
        "execution_mode": "plan_only",
        "responsibility_owners": {
            "product_execution_and_observation": (
                "CanonicalProductSearchPlannerBoundary"
            ),
            "prompt_variant_dispatch": (
                "SearchPlannerPromptVariantDispatch"
            ),
            "mechanical_validation": (
                "CanonicalSearchPlannerMechanicalAuthority"
            ),
            "semantic_meaning": "SearchPlannerSemanticJudgment",
            "semantic_broker_execution": (
                "SearchPlannerSemanticJudgeExecutionObservation"
            ),
            "experiment_comparability": (
                "ModelOriginationExperimentAuthority"
            ),
            "attribution": "ModelOriginationExperimentAuthority",
            "combined_decision": (
                "ModelOriginationEvaluationDecisionCoordinator"
            ),
            "passive_reporting": (
                "ModelOriginationEvaluationReportAssembler"
            ),
            "execution_packaging": (
                "SearchPlannerOwnerSpecificEvaluationOrchestration"
            ),
        },
        "owner_results": {
            "product_boundary": "NOT_RUN",
            "prompt_variant_dispatch": "NOT_RUN",
            "mechanical_validation": "NOT_RUN",
            "semantic_judgment": "NOT_RUN",
            "semantic_execution_observation": "NOT_RUN",
            "experiment_attribution": "NOT_RUN",
            "combined_decision": "NOT_RUN",
            "passive_report": "NOT_RUN",
        },
        "call_manifest": {
            "status": "AUTHORIZATION_REQUIRED",
            "required_call_classes": [
                "one Planner call per scheduled trial",
                "one primary semantic call after each mechanical PASS",
                "one adversarial semantic call after each primary pass attempt",
            ],
            "call_ids_must_be_pre_reserved": True,
            "retry_cap": 0,
            "actual_broker_calls": 0,
        },
        "cap_manifest": {
            "status": "AUTHORIZATION_REQUIRED",
            "required_exact_caps": [
                "Planner calls",
                "primary judge calls",
                "adversarial judge calls",
                "total broker calls",
                "Planner-boundary runs",
                "per-route input and output tokens",
                "per-call route-priced cost",
                "whole-evaluation observed cost",
                "wall clock",
            ],
            "actual_cost_usd": "0",
        },
        "future_authorization_requirements": {
            "authorization_schema_version": (
                OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION
            ),
            "transport_factory_spec": (
                GENERIC_BROKER_TRANSPORT_FACTORY_SPEC
            ),
            "policy_canonicalization_version": (
                POLICY_CANONICALIZATION_VERSION
            ),
            "outcome_metric": OUTCOME_METRIC,
            "stochastic_attribution_ceiling": (
                STOCHASTIC_ATTRIBUTION_CEILING
            ),
            "exact_fields_required": [
                "evaluation identity",
                "fictional scenario packet identity",
                "control and bounded instruction variant",
                "ordered precommitted trial schedule",
                "Planner route and caps",
                "semantic-judge route and pass caps",
                "whole-evaluation caps",
                "all-false retention policy",
                "installed owner identities",
                "teacher-free semantic requirement packet",
                "complete canonical policy packet and digest",
                "exact authority_policy binding",
                "canonical CLI command and digest",
                "temporary loopback broker session",
            ],
            "provider_selected": False,
            "model_selected": False,
            "scenario_selected": False,
            "instruction_variant_selected": False,
        },
        "call_counts": {
            "model_calls": 0,
            "broker_calls": 0,
            "provider_calls": 0,
            "search_calls": 0,
            "retrieval_calls": 0,
            "external_calls": 0,
        },
        "transport_created": False,
        "credentials_accessed": False,
        "raw_material_retained": False,
        "terminal_posture": "PLANNED_NOT_RUN",
    }
    _reject_outer_forbidden_material(packet)
    return packet


def execute_owner_specific_evaluation(
    *,
    authorization: OwnerSpecificLiveAuthorization,
    scenario_packet: OwnerSpecificScenarioPacket,
    repository_sha: str,
    live_addendum_path: str,
    scenario_packet_path: str,
    output_packet_path: str,
    actual_argv: Sequence[str],
    repository_root: Path,
    transport_factory: TransportFactory | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Execute the exact authorized schedule or fail before/at its owner seam."""

    validate_authorization_context(
        authorization,
        scenario_packet=scenario_packet,
        repository_sha=repository_sha,
        live_addendum_path=live_addendum_path,
        scenario_packet_path=scenario_packet_path,
        output_packet_path=output_packet_path,
        actual_argv=actual_argv,
        repository_root=repository_root,
    )
    output_relative = normalize_repository_relative_path(
        output_packet_path,
        label="output packet path",
        repository_root=repository_root,
        require_output_local=True,
    )
    output_target = repository_root.resolve() / output_relative
    if output_target.exists():
        raise OwnerSpecificAuthorizationError(
            "output packet path already exists"
        )
    session_present = bool(
        os.environ.get(broker_client.TOKEN_ENV_VAR, "")
    )
    if not session_present:
        raise OwnerSpecificAuthorizationError(
            "execute requires a temporary loopback broker session"
        )
    if not broker_client._is_loopback_broker_url(
        broker_client.DEFAULT_BROKER_URL
    ):
        raise OwnerSpecificAuthorizationError(
            "execute requires the fixed loopback broker endpoint"
        )
    if (
        transport_factory is not None
        and getattr(transport_factory, "test_only", False) is not True
    ):
        raise OwnerSpecificAuthorizationError(
            "injected transport factories are confined to explicit test doubles"
        )
    try:
        output_target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OwnerSpecificAuthorizationError(
            "output packet parent is not writable"
        ) from exc

    selected_factory = (
        create_brokered_model_route_transport
        if transport_factory is None
        else transport_factory
    )
    started_at = clock()
    ledger = _BudgetLedger(
        authorization,
        started_at=started_at,
        clock=clock,
    )
    planner_route = _broker_route_authorization(
        authorization.planner_route
    )
    judge_route = _broker_route_authorization(
        authorization.semantic_judge_route
    )
    planner_transport = _BudgetedTransport(
        delegate=selected_factory(planner_route),
        route=authorization.planner_route,
        ledger=ledger,
    )
    judge_transport = _BudgetedTransport(
        delegate=selected_factory(judge_route),
        route=authorization.semantic_judge_route,
        ledger=ledger,
    )
    semantic_adapter = BrokeredSearchPlannerSemanticJudge(
        transport=judge_transport,
        route=authorization.semantic_judge_route,
    )

    trial_executions: list[_ProductTrialExecution] = []
    for scheduled in authorization.prompt_experiment.trial_schedule:
        ledger.check_elapsed()
        product_execution = _execute_product_trial(
            schedule=scheduled,
            scenario_packet=scenario_packet,
            planner_route=authorization.planner_route,
            prompt_variant=(
                authorization.prompt_experiment.prompt_variant_specification
            ),
            planner_transport=planner_transport,
        )
        semantic_result: SemanticJudgmentResult | None = None
        semantic_execution: (
            SearchPlannerSemanticJudgeExecutionObservation | None
        ) = None
        if product_execution.mechanical_result.semantic_judgment_allowed:
            semantic_request = build_semantic_judgment_request(
                normalized_user_request=(
                    scenario_packet.normalized_fictional_user_request
                ),
                planner_input=product_execution.planner_input,
                essential_requirements=(
                    authorization.semantic_requirement_packet.essential_requirements
                ),
                proposed_plan=product_execution.proposed_plan,
                mechanical_validation_summary=(
                    product_execution.mechanical_result.to_packet()
                ),
                evaluation_budget_identity=(
                    "owner-specific-budget:"
                    + authorization.authorization_sha256
                ),
                essential_architecture_constraints=(
                    authorization.semantic_requirement_packet.essential_architecture_constraints
                ),
                prohibited_upgrades_or_shortcuts=(
                    authorization.semantic_requirement_packet.prohibited_upgrades_or_shortcuts
                ),
            )
            try:
                semantic_outcome: BrokeredSemanticJudgmentOutcome = (
                    semantic_adapter.judge(
                        semantic_request,
                        primary_call_id=scheduled.primary_judge_call_id,
                        adversarial_call_id=(
                            scheduled.adversarial_judge_call_id
                        ),
                    )
                )
            except OwnerSpecificOrchestrationError:
                raise
            except (
                BrokeredSemanticJudgeError,
                EvaluationConfigurationError,
                EvaluationTransportError,
            ) as exc:
                raise OwnerSpecificOrchestrationError(
                    "semantic-judge broker execution failed closed: "
                    f"{type(exc).__name__}"
                ) from exc
            semantic_result = semantic_outcome.semantic_result
            semantic_execution = (
                semantic_outcome.execution_observation
            )
            if semantic_result is not None:
                validate_semantic_result_execution_pair(
                    semantic_result,
                    semantic_execution,
                )
        trial_executions.append(
            _ProductTrialExecution(
                schedule=scheduled,
                product_observation=(
                    product_execution.product_observation
                ),
                mechanical_result=product_execution.mechanical_result,
                prompt_dispatch=product_execution.prompt_dispatch,
                planner_execution=product_execution.planner_execution,
                planner_input=product_execution.planner_input,
                proposed_plan=product_execution.proposed_plan,
                semantic_result=semantic_result,
                semantic_execution=semantic_execution,
            )
        )

    ledger.check_elapsed()
    packet = _assemble_outer_packet(
        authorization=authorization,
        scenario_packet=scenario_packet,
        trial_executions=trial_executions,
        budget_snapshot=ledger.snapshot(),
        repository_sha=repository_sha,
    )
    try:
        with output_target.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(
                packet,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            handle.write("\n")
    except FileExistsError as exc:
        raise OwnerSpecificOrchestrationError(
            "output packet collision occurred before final write"
        ) from exc
    return packet


@dataclass(slots=True)
class _ProductExecutionResult:
    product_observation: ProductBoundaryObservation
    mechanical_result: MechanicalValidationResult
    prompt_dispatch: PromptVariantDispatchObservation
    planner_execution: PlannerBrokerExecutionObservation
    planner_input: Mapping[str, Any] = field(repr=False)
    proposed_plan: Mapping[str, Any] = field(repr=False)


def _execute_product_trial(
    *,
    schedule: TrialScheduleEntry,
    scenario_packet: OwnerSpecificScenarioPacket,
    planner_route: PlannerRouteAuthorization,
    prompt_variant: PromptVariantSpecification,
    planner_transport: ModelTransport,
) -> _ProductExecutionResult:
    bridge = SearchPlannerBrokerBridge(
        transport=planner_transport,
        route=planner_route,
        prompt_variant=prompt_variant,
        arm_id=schedule.arm_id,
        call_id=schedule.planner_call_id,
    )
    observer = CanonicalProductSearchPlannerBoundaryObserver(bridge)
    product_cost_seam = CostAccumulator()

    def ask_search_planner_model(
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        kwargs["cost_accumulator"] = product_cost_seam
        kwargs["cost_phase"] = "search_planner"
        return observer(prompt, system_prompt, **kwargs)

    product_adapter = SearchPlannerModelAdapter(
        ask_model=ask_search_planner_model,
        clean_json_response=clean_json_response,
        provider=planner_route.provider,
        model=planner_route.model,
        effort=planner_route.reasoning_effort,
        use_reasoning=True,
        max_tokens=planner_route.maximum_output_tokens,
        enabled=True,
        licensed=True,
    )
    capturing_adapter = _CapturedPlannerAdapter(product_adapter)
    kernel = _kernel_with_authorized_run_contract(scenario_packet)
    router_state = build_router_query_preparation_state(
        query=scenario_packet.normalized_fictional_user_request,
        router_text=json.dumps(
            dict(scenario_packet.router_input),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ),
    )
    failure: Exception | None = None
    try:
        execute_initial_query_strategy_convergence(
            run_kernel=kernel,
            router_query_preparation_contract=router_state,
            query=scenario_packet.normalized_fictional_user_request,
            strategy=scenario_packet.requested_mode,
            current_date=scenario_packet.current_date,
            focus_academic=scenario_packet.focus_academic,
            force_intent_news=scenario_packet.force_intent_news,
            include_domains=scenario_packet.include_domains,
            exclude_domains=scenario_packet.exclude_domains,
            news_preferred_domains=(
                scenario_packet.news_preferred_domains
            ),
            route_projection=scenario_packet.route_projection,
            run_contract_projection=(
                scenario_packet.run_contract_projection
            ),
            supplied_context=scenario_packet.supplied_context,
            planner_adapter=capturing_adapter,
            provider_diagnostics=[],
        )
    except Exception as exc:
        infrastructure_failure = _find_infrastructure_failure(exc)
        if isinstance(
            infrastructure_failure,
            OwnerSpecificOrchestrationError,
        ):
            raise infrastructure_failure
        if infrastructure_failure is not None:
            raise OwnerSpecificOrchestrationError(
                "Planner broker infrastructure failed closed: "
                f"{type(infrastructure_failure).__name__}"
            ) from infrastructure_failure
        failure = exc
    safe_usage = bridge.safe_usage_ref()
    safe_execution = bridge.safe_execution_ref()
    product_observation = observer.finalize(
        run_kernel=kernel,
        failure=failure,
        validated_proposal_returned=(
            capturing_adapter.validated_proposal_returned
        ),
        safe_usage_refs=((safe_usage,) if safe_usage else ()),
        safe_execution_refs=(
            (safe_execution,) if safe_execution else ()
        ),
    )
    mechanical_result = validate_product_observation(
        product_observation
    )
    if (
        bridge.dispatch_observation is None
        or bridge.execution_observation is None
        or capturing_adapter.planner_input is None
    ):
        raise OwnerSpecificOrchestrationError(
            "canonical product Planner boundary was not observed"
        )
    proposed_plan = dict(
        kernel.state.search_planner_proposal_state or {}
    )
    if mechanical_result.semantic_judgment_allowed and not proposed_plan:
        raise OwnerSpecificOrchestrationError(
            "mechanical PASS has no canonical proposed plan"
        )
    return _ProductExecutionResult(
        product_observation=product_observation,
        mechanical_result=mechanical_result,
        prompt_dispatch=bridge.dispatch_observation,
        planner_execution=bridge.execution_observation,
        planner_input=capturing_adapter.planner_input,
        proposed_plan=proposed_plan,
    )


def _find_infrastructure_failure(
    failure: BaseException,
) -> BaseException | None:
    current: BaseException | None = failure
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(
            current,
            (
                OwnerSpecificOrchestrationError,
                EvaluationConfigurationError,
                EvaluationTransportError,
            ),
        ):
            return current
        current = current.__cause__ or current.__context__
    return None


def _kernel_with_authorized_run_contract(
    scenario: OwnerSpecificScenarioPacket,
) -> RunKernel:
    stable_suffix = canonical_sha256(
        {
            "scenario_id": scenario.scenario_id,
            "request": scenario.normalized_fictional_user_request,
            "mode": scenario.requested_mode,
        }
    )[:20]
    kernel = RunKernel.start(
        run_id=f"run:owner-specific:{stable_suffix}",
        request_id=f"request:owner-specific:{stable_suffix}",
    )
    action = kernel.authorize_run_contract_synthesis()
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload={
                "contract_projection": dict(
                    scenario.run_contract_projection
                ),
                "validation": {"ok": True, "status": "ok"},
            },
        )
    )
    return kernel


def _assemble_outer_packet(
    *,
    authorization: OwnerSpecificLiveAuthorization,
    scenario_packet: OwnerSpecificScenarioPacket,
    trial_executions: Sequence[_ProductTrialExecution],
    budget_snapshot: Mapping[str, Any],
    repository_sha: str,
) -> dict[str, Any]:
    if len(trial_executions) != len(
        authorization.prompt_experiment.trial_schedule
    ):
        raise OwnerSpecificOrchestrationError(
            "completed trial set differs from the authorized schedule"
        )
    if [
        item.schedule for item in trial_executions
    ] != list(authorization.prompt_experiment.trial_schedule):
        raise OwnerSpecificOrchestrationError(
            "completed trial order differs from the authorized schedule"
        )
    policy_digest = authorization.canonical_policy_packet.sha256
    if (
        policy_digest != authorization.policy_packet_sha256
        or authorization.authority_policy
        != f"owner-specific-policy:{policy_digest}"
    ):
        raise OwnerSpecificOrchestrationError(
            "policy equality failed before attribution"
        )

    call_identities = []
    trial_observations: list[TrialObservation] = []
    safe_trial_materials: list[dict[str, Any]] = []
    for item in trial_executions:
        dispatch = item.prompt_dispatch
        experiment = build_experiment_identity(
            repository_sha=repository_sha,
            scenario_id=scenario_packet.scenario_id,
            semantic_input_digest=(
                dispatch.dispatched_semantic_input_digest
            ),
            system_prompt_digest=(
                dispatch.dispatched_system_prompt_digest
            ),
            provider=authorization.planner_route.provider,
            model=authorization.planner_route.model,
            reasoning_effort=(
                authorization.planner_route.reasoning_effort
            ),
            output_envelope=_OUTPUT_ENVELOPE_IDENTITY,
            product_boundary_version=(
                authorization.owner_identities.product_boundary_version
            ),
            mechanical_validator_version=(
                authorization.owner_identities.mechanical_validator_version
            ),
            semantic_judge_contract_version=(
                authorization.owner_identities.semantic_contract_version
            ),
            authority_policy=authorization.authority_policy,
        )
        result_packet = {
            "product_boundary_result": (
                item.product_observation.to_packet()
            ),
            "mechanical_validation_result": (
                item.mechanical_result.to_packet()
            ),
            "semantic_judgment_result": (
                item.semantic_result.to_packet()
                if item.semantic_result is not None
                else None
            ),
            "semantic_execution_observation": (
                item.semantic_execution.to_packet()
                if item.semantic_execution is not None
                else None
            ),
            "planner_execution_observation": (
                item.planner_execution.to_packet()
            ),
        }
        call_identity = build_call_identity(
            call_id=item.schedule.planner_call_id,
            experiment=experiment,
            instruction_variant=item.schedule.arm_id,
            prompt_identity=PromptIdentity(
                semantic_input_digest=(
                    dispatch.dispatched_semantic_input_digest
                ),
                system_prompt_digest=(
                    dispatch.dispatched_system_prompt_digest
                ),
                instruction_digest=(
                    dispatch.dispatched_instruction_digest
                ),
                full_prompt_digest=(
                    dispatch.dispatched_full_prompt_digest
                ),
            ),
            execution_command={
                "canonical_operator_command_digest": (
                    authorization.evaluation_identity.canonical_operator_command_digest
                ),
                "trial_id": item.schedule.trial_id,
                "planner_call_id": item.schedule.planner_call_id,
            },
            authorization_packet=authorization.to_packet(),
            result_packet=result_packet,
        )
        semantic_status = (
            item.semantic_result.final_status
            if item.semantic_result is not None
            else "NOT_RUN"
        )
        outcome_value = (
            1.0
            if semantic_status == "MET"
            else 0.0
        )
        complete = (
            item.product_observation.boundary_status == "PASS"
            and item.mechanical_result.overall_posture == "PASS"
            and item.semantic_result is not None
        )
        trial_observation = TrialObservation(
            call_identity=call_identity,
            product_status=item.product_observation.boundary_status,
            mechanical_status=item.mechanical_result.overall_posture,
            semantic_status=semantic_status,
            outcome_value=outcome_value,
            complete=complete,
        )
        call_identities.append(call_identity)
        trial_observations.append(trial_observation)
        safe_trial_materials.append(result_packet)

    design = ExperimentDesign(
        design_kind=authorization.prompt_experiment.design_kind,
        stochastic=True,
        preregistered=True,
        required_observations_per_variant=(
            authorization.prompt_experiment.required_observations_per_arm
        ),
        sampling_policy=(
            authorization.prompt_experiment.sampling_policy
        ),
        outcome_metric=authorization.prompt_experiment.outcome_metric,
        decision_statistic="difference_in_means",
        uncertainty_method=(
            "standard_error_of_mean_difference"
            if authorization.prompt_experiment.required_observations_per_arm
            > 1
            else None
        ),
        confidence_multiplier=(
            1.96
            if authorization.prompt_experiment.required_observations_per_arm
            > 1
            else None
        ),
        error_threshold=0.0,
        randomized_order=(
            authorization.prompt_experiment.randomized_order
        ),
        blinded_judging=(
            authorization.prompt_experiment.blinded_judging
        ),
        replication_verified=(
            authorization.prompt_experiment.required_observations_per_arm
            > 1
        ),
        unplanned_exclusions=0,
    )
    control = [
        trial
        for trial in trial_observations
        if trial.call_identity.instruction_variant
        == authorization.prompt_experiment.control_arm_id
    ]
    variant = [
        trial
        for trial in trial_observations
        if trial.call_identity.instruction_variant
        == authorization.prompt_experiment.variant_arm_id
    ]
    attribution = attribute_prompt_comparison(
        control=control,
        variant=variant,
        design=design,
    )
    if attribution.status == "CAUSAL_SUPPORT_ESTABLISHED":
        raise OwnerSpecificOrchestrationError(
            "stochastic owner-specific evaluation exceeded its attribution ceiling"
        )

    coordinator = ModelOriginationEvaluationDecisionCoordinator()
    assembler = ModelOriginationEvaluationReportAssembler()
    trial_packets: list[dict[str, Any]] = []
    semantic_observation_count = 0
    model_failure_seen = False
    for item, call_identity, trial_observation, material in zip(
        trial_executions,
        call_identities,
        trial_observations,
        safe_trial_materials,
    ):
        if item.semantic_execution is not None:
            semantic_observation_count += 1
        if item.semantic_result is not None:
            if item.semantic_execution is None:
                raise OwnerSpecificOrchestrationError(
                    "live-derived semantic result lacks its execution observation"
                )
            validate_semantic_result_execution_pair(
                item.semantic_result,
                item.semantic_execution,
            )
        combined = coordinator.coordinate(
            product=item.product_observation,
            mechanical=item.mechanical_result,
            semantic=item.semantic_result,
            attribution=attribution,
        )
        per_trial_cost = Decimal(
            item.planner_execution.cost_accounting_usd
        )
        if item.semantic_execution is not None:
            per_trial_cost += Decimal(
                item.semantic_execution.cumulative_semantic_judge_cost_usd
            )
        execution_refs = [
            {
                "planner_call_id": item.schedule.planner_call_id,
                "planner_execution_identity_digest": (
                    item.planner_execution.execution_identity_digest
                ),
                "prompt_dispatch_observation_digest": canonical_sha256(
                    item.prompt_dispatch.to_packet()
                ),
            }
        ]
        if item.semantic_execution is not None:
            execution_refs.append(
                {
                    "semantic_execution_observation_digest": (
                        item.semantic_execution.observation_digest
                    ),
                    "primary_call_id": (
                        item.semantic_execution.primary_pass.call_id
                    ),
                    "adversarial_call_id": (
                        item.semantic_execution.adversarial_pass.call_id
                    ),
                }
            )
        report = assembler.assemble(
            combined=combined,
            product=item.product_observation,
            mechanical=item.mechanical_result,
            semantic=item.semantic_result,
            attribution=attribution,
            safe_usage_and_cost_metadata={
                "usage_observed": True,
                "per_trial_observed_cost_usd": format(
                    per_trial_cost,
                    "f",
                ),
                "raw_material_retained": False,
            },
            execution_references=execution_refs,
        )
        if not trial_observation.complete:
            model_failure_seen = True
        trial_packets.append(
            {
                "trial_id": item.schedule.trial_id,
                "arm_id": item.schedule.arm_id,
                "prompt_variant_dispatch_observation": (
                    item.prompt_dispatch.to_packet()
                ),
                **material,
                "experiment_call_identity": asdict(call_identity),
                "trial_observation": asdict(trial_observation),
                "passive_evaluation_report": report.to_packet(),
            }
        )

    schedule_packet = authorization.prompt_experiment.schedule_packet()
    packet = {
        "schema_version": (
            OWNER_SPECIFIC_ORCHESTRATION_PACKET_SCHEMA_VERSION
        ),
        "owner": "SearchPlannerOwnerSpecificEvaluationOrchestration",
        "orchestrator_version": OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
        "repository_sha": repository_sha,
        "execution_mode": "execute",
        "authorization_identity": {
            "reference": (
                authorization.evaluation_identity.reference
            ),
            "authorization_sha256": (
                authorization.authorization_sha256
            ),
            "policy_packet_sha256": (
                authorization.policy_packet_sha256
            ),
            "authority_policy": authorization.authority_policy,
            "scenario_id": scenario_packet.scenario_id,
            "scenario_packet_sha256": scenario_packet.sha256,
            "canonical_operator_command_digest": (
                authorization.evaluation_identity.canonical_operator_command_digest
            ),
            "transport_factory_spec": (
                authorization.evaluation_identity.transport_factory_spec
            ),
        },
        "schedule_identity": {
            "trial_schedule_sha256": canonical_sha256(
                schedule_packet
            ),
            "trial_count": len(
                authorization.prompt_experiment.trial_schedule
            ),
            "schedule": schedule_packet,
        },
        "owner_identities": (
            authorization.owner_identities.to_packet()
        ),
        "prompt_experiment": (
            authorization.prompt_experiment.safe_packet()
        ),
        "canonical_experiment_policy_packet": (
            authorization.canonical_policy_packet.to_packet()
        ),
        "policy_packet_sha256": authorization.policy_packet_sha256,
        "authority_policy": authorization.authority_policy,
        "trial_results": trial_packets,
        "semantic_execution_observation_count": (
            semantic_observation_count
        ),
        "experiment_attribution_result": attribution.to_packet(),
        "budget_and_cap_consumption": dict(budget_snapshot),
        "terminal_orchestration_posture": (
            "COMPLETED_WITH_MODEL_FAILURES"
            if model_failure_seen
            else "COMPLETED"
        ),
        "causal_language_allowed": False,
        "real_prompt_effect_proved": False,
        "prompt_quality_winner": None,
        "raw_prompt_retained": False,
        "raw_response_retained": False,
        "raw_provider_payload_retained": False,
        "variant_instruction_retained": False,
        "broker_session_token_retained": False,
    }
    packet = json.loads(
        json.dumps(
            packet,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    _validate_outer_packet(packet, authorization)
    return packet


def _validate_outer_packet(
    packet: Mapping[str, Any],
    authorization: OwnerSpecificLiveAuthorization,
) -> None:
    if packet.get("schema_version") != (
        OWNER_SPECIFIC_ORCHESTRATION_PACKET_SCHEMA_VERSION
    ):
        raise OwnerSpecificOrchestrationError(
            "outer orchestration packet version is invalid"
        )
    if packet.get("owner") != (
        "SearchPlannerOwnerSpecificEvaluationOrchestration"
    ):
        raise OwnerSpecificOrchestrationError(
            "outer orchestration packet owner is invalid"
        )
    if (
        packet.get("policy_packet_sha256")
        != authorization.policy_packet_sha256
        or packet.get("authority_policy")
        != authorization.authority_policy
        or packet.get("canonical_experiment_policy_packet")
        != authorization.canonical_policy_packet.to_packet()
    ):
        raise OwnerSpecificOrchestrationError(
            "outer packet does not retain the exact canonical policy"
        )
    if (
        packet.get("causal_language_allowed") is not False
        or packet.get("real_prompt_effect_proved") is not False
        or packet.get("prompt_quality_winner") is not None
    ):
        raise OwnerSpecificOrchestrationError(
            "outer packet upgraded the attribution owner"
        )
    if any(
        packet.get(flag) is not False
        for flag in (
            "raw_prompt_retained",
            "raw_response_retained",
            "raw_provider_payload_retained",
            "variant_instruction_retained",
            "broker_session_token_retained",
        )
    ):
        raise OwnerSpecificOrchestrationError(
            "outer packet retention posture is invalid"
        )
    _reject_outer_forbidden_material(packet)
    canonical_json = json.dumps(
        packet,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    variant_text = (
        authorization.prompt_experiment.prompt_variant_specification.variant_instruction_text
    )
    if variant_text in canonical_json:
        raise OwnerSpecificOrchestrationError(
            "outer packet retained the variant instruction text"
        )


def validate_owner_specific_result_packet_metadata(
    packet: Mapping[str, Any],
    *,
    authorization: OwnerSpecificLiveAuthorization,
    repository_sha: str,
) -> dict[str, int | str]:
    """Validate one completed packet and project only exact safe totals.

    The caller receives no trial material, route content, prompt material, or
    provider output. This narrow projection exists for operator stop
    attestation, where exact counts and cost are truthful only after the normal
    result packet has passed its existing owner validation.
    """

    _validate_outer_packet(packet, authorization)
    if packet.get("repository_sha") != repository_sha or packet.get("execution_mode") != "execute":
        raise OwnerSpecificOrchestrationError("result packet does not bind the exact execute checkout")
    authorization_identity = packet.get("authorization_identity")
    if (
        not isinstance(authorization_identity, Mapping)
        or (authorization_identity.get("authorization_sha256") != authorization.authorization_sha256)
        or (authorization_identity.get("policy_packet_sha256") != authorization.policy_packet_sha256)
        or (
            authorization_identity.get("canonical_operator_command_digest")
            != authorization.evaluation_identity.canonical_operator_command_digest
        )
    ):
        raise OwnerSpecificOrchestrationError("result packet authorization identity is invalid")
    budget = packet.get("budget_and_cap_consumption")
    if not isinstance(budget, Mapping):
        raise OwnerSpecificOrchestrationError("result packet budget projection is invalid")

    def count(label: str) -> int:
        value = budget.get(label)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise OwnerSpecificOrchestrationError(f"result packet {label} is invalid")
        return value

    planner_calls = count("planner_calls_consumed")
    primary_judge_calls = count("primary_judge_calls_consumed")
    adversarial_judge_calls = count("adversarial_judge_calls_consumed")
    total_broker_calls = count("attempted_call_count")
    completed_call_count = count("completed_call_count")
    if (
        total_broker_calls != completed_call_count
        or total_broker_calls != planner_calls + primary_judge_calls + adversarial_judge_calls
        or planner_calls > authorization.planner_route.maximum_planner_calls
        or primary_judge_calls > authorization.semantic_judge_route.maximum_primary_judge_calls
        or adversarial_judge_calls > authorization.semantic_judge_route.maximum_adversarial_judge_calls
        or total_broker_calls > authorization.whole_evaluation_caps.maximum_total_broker_calls
    ):
        raise OwnerSpecificOrchestrationError("result packet call-consumption projection is invalid")
    observed_cost = _nonnegative_decimal(
        budget.get("total_observed_cost_usd"),
        "result packet observed cost",
    )
    if observed_cost > Decimal(authorization.whole_evaluation_caps.maximum_total_observed_cost_usd):
        raise OwnerSpecificOrchestrationError("result packet observed cost exceeds the exact authorization")
    return {
        "planner_calls": planner_calls,
        "primary_judge_calls": primary_judge_calls,
        "adversarial_judge_calls": adversarial_judge_calls,
        "total_broker_calls": total_broker_calls,
        "observed_cost_usd": format(observed_cost, "f"),
    }


def _broker_route_authorization(
    route: PlannerRouteAuthorization
    | SemanticJudgeRouteAuthorization,
) -> BrokeredModelRouteAuthorization:
    return BrokeredModelRouteAuthorization(
        provider=route.provider,
        model=route.model,
        reasoning_effort=route.reasoning_effort,
        allowed_model_roles=(route.role,),
        retry_cap=route.retry_cap,
        timeout_seconds=route.timeout_seconds,
        maximum_input_tokens=route.maximum_input_tokens,
        maximum_output_tokens=route.maximum_output_tokens,
        per_call_cost_ceiling_usd=(
            route.per_call_cost_ceiling_usd
        ),
        raw_retention_posture="sanitized_only",
        require_observed_usage=True,
    )


def _validate_transport_response(
    response: EvaluationTransportResponse,
    *,
    role: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    maximum_input_tokens: int,
    maximum_output_tokens: int,
    per_call_cost_ceiling_usd: str,
) -> dict[str, Any]:
    del role
    if (
        response.canonical_provider_used != provider
        or response.canonical_model_used != model
        or response.reasoning_effort != reasoning_effort
        or response.provider_request_attempt_count != 1
        or response.raw_material_retained
    ):
        raise OwnerSpecificOrchestrationError(
            "broker response route or retention attestation is invalid"
        )
    if not response.usage_observed:
        raise OwnerSpecificOrchestrationError(
            "unknown usage is not live-admissible"
        )
    for label, value, maximum in (
        (
            "input_tokens",
            response.input_tokens,
            maximum_input_tokens,
        ),
        (
            "output_tokens",
            response.output_tokens,
            maximum_output_tokens,
        ),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > maximum
        ):
            raise OwnerSpecificOrchestrationError(
                f"broker response {label} is invalid or exceeds its cap"
            )
    cost = _nonnegative_decimal(
        response.caller_calculated_route_priced_cost_usd,
        "broker response cost",
    )
    if (
        response.cost_posture != "exact"
        or cost > Decimal(per_call_cost_ceiling_usd)
    ):
        raise OwnerSpecificOrchestrationError(
            "broker response cost is unknown or exceeds its cap"
        )
    output = str(response.output or "")
    if (
        response.output_text_character_count != len(output)
        or response.output_text_digest
        != sha256(output.encode("utf-8")).hexdigest()
        or response.output_text_present != bool(output)
    ):
        raise OwnerSpecificOrchestrationError(
            "broker response safe output identity is invalid"
        )
    return {
        "route_attestation": {
            "provider_matches_authorization": True,
            "model_matches_authorization": True,
            "reasoning_effort_matches_authorization": True,
            "physical_attempt_count": 1,
            "raw_material_retained": False,
        },
        "usage_attestation": {
            "posture": "OBSERVED_AND_WITHIN_CAP",
            "input_within_cap": True,
            "output_within_cap": True,
            "cost_within_cap": True,
        },
        "token_accounting": {
            "input_tokens": response.input_tokens,
            "cached_input_tokens": response.cached_input_tokens,
            "uncached_input_tokens": response.uncached_input_tokens,
            "output_tokens": response.output_tokens,
            "reasoning_tokens": response.reasoning_tokens,
            "non_reasoning_output_tokens": (
                response.non_reasoning_output_tokens
            ),
            "total_tokens": response.total_tokens,
        },
        "cost_accounting_usd": format(cost, "f"),
    }


def _nonnegative_decimal(
    value: str | None,
    label: str,
) -> Decimal:
    if value is None:
        raise OwnerSpecificOrchestrationError(
            f"{label} must be observed"
        )
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise OwnerSpecificOrchestrationError(
            f"{label} must be an exact decimal"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise OwnerSpecificOrchestrationError(
            f"{label} must be finite and nonnegative"
        )
    return parsed


def _require_digest(value: str, label: str) -> None:
    if len(value) != 64 or any(
        item not in _DIGEST_CHARS for item in value
    ):
        raise OwnerSpecificOrchestrationError(
            f"{label} must be one SHA-256 digest"
        )


def _reject_outer_forbidden_material(value: Any) -> None:
    forbidden = {
        "api_key",
        "authorization_header",
        "chain_of_thought",
        "credential",
        "credentials",
        "full_prompt",
        "private_log",
        "prompt_text",
        "provider_payload",
        "raw_judge_response",
        "raw_model_response",
        "raw_planner_response",
        "raw_prompt",
        "raw_provider_payload",
        "reasoning_trace",
        "secret",
        "session_token",
        "token_value",
        "variant_instruction_text",
    }
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = (
                str(key).strip().casefold().replace("-", "_")
            )
            if normalized in forbidden:
                raise OwnerSpecificOrchestrationError(
                    f"orchestration packet contains forbidden field: {normalized}"
                )
            _reject_outer_forbidden_material(nested)
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes),
    ):
        for item in value:
            _reject_outer_forbidden_material(item)


__all__ = [
    "OWNER_SPECIFIC_ORCHESTRATION_PACKET_SCHEMA_VERSION",
    "OWNER_SPECIFIC_PLAN_SCHEMA_VERSION",
    "OwnerSpecificOrchestrationError",
    "PlannerBrokerExecutionObservation",
    "SearchPlannerBrokerBridge",
    "build_plan_only_packet",
    "execute_owner_specific_evaluation",
    "validate_owner_specific_result_packet_metadata",
]
# fmt: on
