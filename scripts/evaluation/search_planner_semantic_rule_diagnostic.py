"""Bounded current-v8 SearchPlanner semantic-rule diagnostic evaluator.

The evaluator invokes the installed product Planner path through initial
AnswerContract acceptance, then stops. Retained packets exclude query text,
prompts, responses, proposals, AnswerContracts, exception text, and provider
payloads.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.cost_accounting import CostAccumulator
from core.query_production_runtime import (
    QueryStrategyConvergenceError,
    execute_initial_search_planner_acceptance,
)
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
)
from core.run_config import RunConfig
from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
)
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
from core.text_utils import clean_json_response
from scripts.evaluation.brokered_model_origination_transport import (
    BrokeredModelRouteAuthorization,
    create_brokered_model_route_transport,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationTransportError,
    EvaluationTransportResponse,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_VERSION,
    CanonicalProductSearchPlannerBoundaryObserver,
)

SEMANTIC_RULE_DIAGNOSTIC_SCHEMA_VERSION = "search_planner_semantic_rule_diagnostic_v1"
CURRENT_MAIN_V8_ONLY = "CURRENT_MAIN_V8_ONLY"
PLANNER_ROLE = "search_planner_semantic_rule_diagnostic"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MAXIMUM_PHYSICAL_MODEL_ATTEMPTS = 6
MAXIMUM_TOTAL_COST_USD = Decimal("2.00")
MAXIMUM_PER_CALL_COST_USD = Decimal("0.333333")
MAXIMUM_INPUT_TOKENS = 16_000
MAXIMUM_OUTPUT_TOKENS = 4_096
REQUIRED_PRODUCT_PROVIDER = "OpenAI"
# The loopback provider-execution contract uses its closed lowercase token.
BROKER_PROVIDER = "openai"
REQUIRED_MODEL = "gpt-5.4-mini"
REQUIRED_REASONING_EFFORT = "medium"
REQUIRED_MODE = "Balanced"
_HEX_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PACKET_KEYS = frozenset(
    {
        "answer_contract",
        "cleaned_proposal",
        "content",
        "exception",
        "exception_text",
        "full_prompt",
        "model_output",
        "model_response",
        "proposal",
        "provider_payload",
        "provider_request",
        "provider_response",
        "query",
        "raw_model_output",
        "raw_prompt",
        "response",
        "secret",
    }
)
_DOWNSTREAM_ZERO_KEYS = (
    "query_plan_execution",
    "embedding",
    "search",
    "read",
    "search_judgment",
    "analyst",
    "d_prime",
    "runkernel_downstream_semantic_admission",
    "component_coverage",
    "sufficiency",
    "final_answer_packet",
    "author",
)


class SearchPlannerSemanticRuleDiagnosticError(RuntimeError):
    """Closed evaluator configuration or integrity failure."""


class SearchPlannerSemanticRuleDiagnosticIntegrityError(SearchPlannerSemanticRuleDiagnosticError):
    """A required evaluator safety guarantee could not be established."""


@dataclass(frozen=True, slots=True)
class DiagnosticScheduleEntry:
    query_case_id: str
    repetition_ordinal: int

    @property
    def call_id(self) -> str:
        return f"{self.query_case_id}-{self.repetition_ordinal}"


SCHEDULE: tuple[DiagnosticScheduleEntry, ...] = (
    DiagnosticScheduleEntry("Q1", 1),
    DiagnosticScheduleEntry("Q2", 1),
    DiagnosticScheduleEntry("Q1", 2),
    DiagnosticScheduleEntry("Q2", 2),
    DiagnosticScheduleEntry("Q1", 3),
    DiagnosticScheduleEntry("Q2", 3),
)
Transport = Callable[..., EvaluationTransportResponse]
TransportFactory = Callable[[BrokeredModelRouteAuthorization], Transport]


@dataclass(slots=True)
class _Budget:
    physical_model_attempts: int = 0
    observed_cost_usd: Decimal = Decimal("0")

    def reserve(self) -> None:
        if self.physical_model_attempts >= MAXIMUM_PHYSICAL_MODEL_ATTEMPTS:
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("maximum_physical_model_attempts_exhausted")
        self.physical_model_attempts += 1

    def add_cost(self, cost: Decimal) -> None:
        if cost < 0 or cost > MAXIMUM_PER_CALL_COST_USD:
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("per_call_cost_cap_invalid")
        self.observed_cost_usd += cost
        if self.observed_cost_usd > MAXIMUM_TOTAL_COST_USD:
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("campaign_cost_cap_exceeded")


@dataclass(slots=True)
class _CapturingAdapter:
    """Retain only whether the production adapter returned successfully."""

    delegate: SearchPlannerModelAdapter
    validated_proposal_returned: bool = False

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.validated_proposal_returned = False
        proposal = self.delegate.produce(planner_input)
        self.validated_proposal_returned = True
        return proposal


class _PlannerBridge:
    """One physical broker attempt for one product-adapter invocation."""

    def __init__(
        self,
        *,
        transport: Transport,
        route: BrokeredModelRouteAuthorization,
        schedule: DiagnosticScheduleEntry,
        budget: _Budget,
    ) -> None:
        self.transport = transport
        self.route = route
        self.schedule = schedule
        self.budget = budget
        self.called = False
        self.integrity_failure = False
        self.physical_attempts = 0
        self.safe_usage: dict[str, Any] | None = None
        self.completion_posture: str | None = None

    def __call__(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if self.called:
            self.integrity_failure = True
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("planner_bridge_permits_one_call")
        self.called = True
        expected = {
            "provider": REQUIRED_PRODUCT_PROVIDER,
            "model": self.route.model,
            "effort": self.route.reasoning_effort,
            "require_json": True,
            "use_reasoning": True,
            "max_tokens": self.route.maximum_output_tokens,
            "cost_phase": "search_planner",
        }
        if any(kwargs.get(key) != value for key, value in expected.items()):
            self.integrity_failure = True
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("product_ask_model_shape_changed")
        accumulator = kwargs.get("cost_accumulator")
        if not isinstance(accumulator, CostAccumulator):
            self.integrity_failure = True
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("canonical_cost_seam_missing")
        unknown = set(kwargs) - {
            *expected,
            "cost_accumulator",
            "safe_response_envelope_sink",
        }
        if unknown:
            self.integrity_failure = True
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("product_ask_model_shape_unexpected")

        response: EvaluationTransportResponse | None = None
        try:
            self.budget.reserve()
            self.physical_attempts += 1
            response = self.transport(
                role=PLANNER_ROLE,
                prompt=prompt,
                system_prompt=system_prompt,
                provider=self.route.provider,
                model=self.route.model,
                maximum_input_tokens=self.route.maximum_input_tokens,
                maximum_output_tokens=self.route.maximum_output_tokens,
                correlation_id=self.schedule.call_id,
            )
            output, safe_usage, completion_posture = _validate_transport_response(
                response,
                route=self.route,
            )
            self.budget.add_cost(Decimal(safe_usage["cost_usd"]))
            accumulator.record_model_call(
                phase="search_planner",
                model=self.route.model,
                input_tokens=safe_usage["input_tokens"],
                output_tokens=safe_usage["output_tokens"],
            )
            self.safe_usage = safe_usage
            self.completion_posture = completion_posture
            sink = kwargs.get("safe_response_envelope_sink")
            if callable(sink):
                sink({"provider_completion_posture": completion_posture})
            return output if response.generation_status == "completed" else ""
        except SearchPlannerSemanticRuleDiagnosticIntegrityError:
            self.integrity_failure = True
            raise
        except EvaluationTransportError:
            self.integrity_failure = True
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("broker_transport_failed_closed") from None
        except Exception:
            self.integrity_failure = True
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("planner_bridge_failed_closed") from None
        finally:
            response = None
            prompt = ""
            system_prompt = ""


def _validate_transport_response(
    response: EvaluationTransportResponse,
    *,
    route: BrokeredModelRouteAuthorization,
) -> tuple[str, dict[str, Any], str]:
    """Inspect one transient response and retain only authorized safe facts."""

    if (
        response.canonical_provider_used != route.provider
        or response.canonical_model_used != route.model
        or response.reasoning_effort != route.reasoning_effort
        or response.provider_request_attempt_count != 1
        or response.raw_material_retained
        or not response.usage_observed
    ):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("broker_response_route_or_retention_invalid")
    for label, value, maximum in (
        ("input_tokens", response.input_tokens, route.maximum_input_tokens),
        ("output_tokens", response.output_tokens, route.maximum_output_tokens),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError(f"broker_response_{label}_invalid")
    try:
        cost = Decimal(str(response.caller_calculated_route_priced_cost_usd))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("broker_response_cost_unavailable") from exc
    if not cost.is_finite() or cost < 0 or cost > MAXIMUM_PER_CALL_COST_USD or response.cost_posture != "exact":
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("broker_response_cost_invalid")
    output = str(response.output or "")
    if (
        response.output_text_character_count != len(output)
        or response.output_text_present != bool(output)
        or not _HEX_SHA256.fullmatch(str(response.output_text_digest or ""))
        or response.output_text_digest != sha256(output.encode("utf-8")).hexdigest()
    ):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("broker_response_output_attestation_invalid")
    posture = (
        "completed"
        if response.generation_status == "completed" and output
        else "length_limited"
        if response.max_output_tokens_reached
        else "empty"
        if not output
        else "other_safe"
    )
    return (
        output,
        {
            "usage_observed": True,
            "input_tokens": response.input_tokens,
            "cached_input_tokens": response.cached_input_tokens,
            "uncached_input_tokens": response.uncached_input_tokens,
            "output_tokens": response.output_tokens,
            "reasoning_tokens": response.reasoning_tokens,
            "non_reasoning_output_tokens": response.non_reasoning_output_tokens,
            "total_tokens": response.total_tokens,
            "cost_usd": format(cost, "f"),
            "cost_posture": "exact",
            "per_call_cost_within_cap": True,
        },
        posture,
    )


def _route() -> BrokeredModelRouteAuthorization:
    return BrokeredModelRouteAuthorization(
        provider=BROKER_PROVIDER,
        model=REQUIRED_MODEL,
        reasoning_effort=REQUIRED_REASONING_EFFORT,
        allowed_model_roles=(PLANNER_ROLE,),
        retry_cap=0,
        timeout_seconds=180.0,
        maximum_input_tokens=MAXIMUM_INPUT_TOKENS,
        maximum_output_tokens=MAXIMUM_OUTPUT_TOKENS,
        per_call_cost_ceiling_usd=format(MAXIMUM_PER_CALL_COST_USD, "f"),
        raw_retention_posture="sanitized_only",
        require_observed_usage=True,
    )


def verify_current_production_posture() -> None:
    """Confirm the safe current configuration is precisely the approved arm."""

    config = RunConfig(query="searchplanner-semantic-rule-diagnostic")
    if (
        config.fast_provider != REQUIRED_PRODUCT_PROVIDER
        or config.fast_model != REQUIRED_MODEL
        or config.fast_reasoning_effort != REQUIRED_REASONING_EFFORT
        or config.mode != REQUIRED_MODE
        or not config.use_reasoning
        or SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION != "search_planner_sparse_model_prompt_v8"
    ):
        raise SearchPlannerSemanticRuleDiagnosticError("current_production_planner_posture_not_approved")


def _validate_cases(case_inputs: Mapping[str, Any]) -> dict[str, str]:
    if set(case_inputs) != {"Q1", "Q2"}:
        raise SearchPlannerSemanticRuleDiagnosticError("case_inputs_must_contain_exactly_Q1_and_Q2")
    result: dict[str, str] = {}
    for case_id in ("Q1", "Q2"):
        value = case_inputs[case_id]
        if not isinstance(value, str) or not value.strip():
            raise SearchPlannerSemanticRuleDiagnosticError("case_input_must_be_nonempty_text")
        result[case_id] = value
    return result


def _static_contract() -> dict[str, Any]:
    return {
        "contract_id": "contract:searchplanner-semantic-rule-diagnostic",
        "schema_version": "searchplanner_semantic_rule_diagnostic_contract_v1",
        "synthesis_mode": "diagnostic_static_precondition",
        "selected_depth": REQUIRED_MODE,
        "source_requirements": [],
    }


def _kernel(repository_sha: str, schedule: DiagnosticScheduleEntry) -> RunKernel:
    suffix = sha256(f"{repository_sha}:{schedule.call_id}:{CURRENT_MAIN_V8_ONLY}".encode()).hexdigest()[:20]
    kernel = RunKernel.start(
        run_id=f"run:semantic-rule-diagnostic:{suffix}",
        request_id=f"request:semantic-rule-diagnostic:{suffix}",
    )
    action = kernel.authorize_run_contract_synthesis()
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload={
                "contract_projection": _static_contract(),
                "validation": {"ok": True, "status": "ok"},
            },
        )
    )
    return kernel


def _router_state(query: str):
    return build_router_query_preparation_state(
        query=query,
        router_text=(
            '{"core_topic":"searchplanner_semantic_rule_diagnostic",'
            '"entities":[],"intent":"general","is_academic":false,'
            '"primary_entity":"","query_type":"other",'
            '"report_type":"general_research"}'
        ),
    )


def _downstream_zero(kernel: RunKernel, *, accepted: bool) -> dict[str, Any]:
    if accepted != bool(kernel.state.initial_answer_contract_projection):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("initial_acceptance_posture_mismatch")
    state_fields = (
        "search_work_plan",
        "search_executor_handoff_state",
        "search_judgment_read_state",
        "searchos_state",
        "live_search_validation_state",
        "semantic_observation_admission_state",
        "component_coverage_state",
        "sufficiency_readiness_state",
        "final_answer_packet_state",
        "author_execution_state",
    )
    if any(bool(getattr(kernel.state, field, {})) for field in state_fields):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("downstream_state_reached")
    return {
        **{key: 0 for key in _DOWNSTREAM_ZERO_KEYS},
        "initial_answer_contract_acceptance": 1 if accepted else 0,
        "stop_after_initial_answer_contract_acceptance": True,
    }


def _failure_fields(
    failure: Exception | None,
    *,
    accepted: bool,
) -> dict[str, str | None]:
    if accepted:
        return {
            "failure_code": None,
            "semantic_proposal_subtype": None,
            "semantic_validation_rule_id": None,
            "branch_field_set_detail": None,
        }
    if isinstance(failure, SearchPlannerModelAdapterError):
        return {
            "failure_code": failure.failure_code.value,
            "semantic_proposal_subtype": (
                failure.semantic_proposal_subtype.value if failure.semantic_proposal_subtype is not None else None
            ),
            "semantic_validation_rule_id": (
                failure.semantic_validation_rule_id.value if failure.semantic_validation_rule_id is not None else None
            ),
            "branch_field_set_detail": (
                failure.branch_field_set_detail.value if failure.branch_field_set_detail is not None else None
            ),
        }
    if isinstance(failure, QueryStrategyConvergenceError):
        code = getattr(failure, "failure_code", None)
        return {
            "failure_code": getattr(code, "value", None),
            "semantic_proposal_subtype": None,
            "semantic_validation_rule_id": None,
            "branch_field_set_detail": None,
        }
    return {
        "failure_code": "UNCLASSIFIED_PRODUCT_BOUNDARY_FAILURE",
        "semantic_proposal_subtype": None,
        "semantic_validation_rule_id": None,
        "branch_field_set_detail": None,
    }


def _prompt_digests(observation: Any) -> dict[str, str]:
    identity = observation.prompt_identity
    if identity is None:
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("canonical_prompt_identity_missing")
    result = {
        "semantic_input_digest": identity.semantic_input_digest,
        "system_prompt_digest": identity.system_prompt_digest,
        "instruction_digest": identity.instruction_digest,
        "full_prompt_digest": identity.full_prompt_digest,
    }
    if not all(_HEX_SHA256.fullmatch(value) for value in result.values()):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("canonical_prompt_identity_invalid")
    return result


def _execute_one(
    *,
    schedule: DiagnosticScheduleEntry,
    query: str,
    repository_sha: str,
    current_date: str,
    route: BrokeredModelRouteAuthorization,
    transport: Transport,
    budget: _Budget,
) -> dict[str, Any]:
    bridge = _PlannerBridge(
        transport=transport,
        route=route,
        schedule=schedule,
        budget=budget,
    )
    observer = CanonicalProductSearchPlannerBoundaryObserver(bridge)
    accumulator = CostAccumulator()

    def ask_model(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        kwargs["cost_accumulator"] = accumulator
        kwargs["cost_phase"] = "search_planner"
        return observer(prompt, system_prompt, **kwargs)

    adapter = _CapturingAdapter(
        SearchPlannerModelAdapter(
            ask_model=ask_model,
            clean_json_response=clean_json_response,
            provider=REQUIRED_PRODUCT_PROVIDER,
            model=route.model,
            effort=route.reasoning_effort,
            use_reasoning=True,
            max_tokens=route.maximum_output_tokens,
            enabled=True,
            licensed=True,
        )
    )
    kernel = _kernel(repository_sha, schedule)
    failure: Exception | None = None
    accepted = False
    try:
        execute_initial_search_planner_acceptance(
            run_kernel=kernel,
            router_query_preparation_contract=_router_state(query),
            query=query,
            strategy=REQUIRED_MODE,
            current_date=current_date,
            include_domains=(),
            exclude_domains=(),
            route_projection={"route_id": "searchplanner-semantic-rule-diagnostic"},
            run_contract_projection=_static_contract(),
            supplied_context=None,
            planner_adapter=adapter,
        )
        accepted = True
    except SearchPlannerModelAdapterError as exc:
        if bridge.integrity_failure:
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("planner_transport_integrity_failure") from None
        failure = exc
    except QueryStrategyConvergenceError as exc:
        failure = exc
    except SearchPlannerSemanticRuleDiagnosticIntegrityError:
        raise
    except Exception:
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("production_prefix_failed_closed") from None

    if bridge.integrity_failure or bridge.physical_attempts != 1:
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("physical_attempt_attestation_invalid")
    if not bridge.safe_usage or bridge.completion_posture is None:
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("safe_execution_facts_missing")
    observation = observer.finalize(
        run_kernel=kernel,
        failure=failure,
        validated_proposal_returned=adapter.validated_proposal_returned,
        safe_usage_refs=(bridge.safe_usage,),
        safe_execution_refs=({"call_id": schedule.call_id, "retention_posture": "sanitized_only"},),
    )
    if (
        observation.model_call_count != 1
        or not observation.product_boundary_reached
        or observation.raw_prompt_retained
        or observation.raw_response_retained
    ):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("canonical_observer_integrity_invalid")
    result = {
        "query_case_id": schedule.query_case_id,
        "prompt_arm_id": CURRENT_MAIN_V8_ONLY,
        "repetition_ordinal": schedule.repetition_ordinal,
        "accepted": accepted,
        **_failure_fields(failure, accepted=accepted),
        "provider_completion_posture": bridge.completion_posture,
        "repository_identity": {
            "repository_sha": repository_sha,
            "planner_prompt_schema_version": SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
            "canonical_product_boundary_version": CANONICAL_PRODUCT_BOUNDARY_VERSION,
        },
        "prompt_input_identity_digests": _prompt_digests(observation),
        "usage_cost_accounting": dict(bridge.safe_usage),
        "physical_attempt_counts": {
            "planner_model_attempts": 1,
            "total_model_attempts": 1,
            "retry_count": 0,
            "fallback_count": 0,
            "replacement_call_count": 0,
            "embedding_attempts": 0,
            "search_attempts": 0,
            "read_attempts": 0,
        },
        "downstream_zero_attestation": _downstream_zero(
            kernel,
            accepted=accepted,
        ),
        "raw_retention_false_attestation": {
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
            "cleaned_proposal_retained": False,
            "answer_contract_retained": False,
            "exception_text_retained": False,
            "provider_payload_retained": False,
            "private_logs_retained": False,
        },
    }
    _assert_safe_packet(result, forbidden_values=(query,))
    return result


def _stability(call_results: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for case_id in ("Q1", "Q2"):
        values = [
            str(item.get("semantic_validation_rule_id") or "")
            for item in call_results
            if item.get("query_case_id") == case_id
        ]
        result[case_id] = (
            "STABLE_RULE_SPECIFIC_CONFORMANCE_FAILURE_PLAUSIBLE"
            if len(values) == 3 and values[0] and len(set(values)) == 1
            else "NO_STABLE_RULE_SPECIFIC_SIGNAL"
        )
    return result


def execute_search_planner_semantic_rule_diagnostic(
    *,
    case_inputs: Mapping[str, Any],
    repository_sha: str,
    current_date: str | None = None,
    output_path: Path | None = None,
    repository_root: Path = REPOSITORY_ROOT,
    transport_factory: TransportFactory | None = None,
) -> dict[str, Any]:
    """Run exactly the licensed schedule or stop with invalid evidence."""

    if not _HEX_GIT_SHA.fullmatch(repository_sha):
        raise SearchPlannerSemanticRuleDiagnosticError("repository_sha_must_be_exact_40_character_hex")
    cases = _validate_cases(case_inputs)
    verify_current_production_posture()
    if transport_factory is not None and getattr(transport_factory, "test_only", False) is not True:
        raise SearchPlannerSemanticRuleDiagnosticError("injected_transport_factory_is_test_only")
    route = _route()
    transport = create_brokered_model_route_transport(route) if transport_factory is None else transport_factory(route)
    if not callable(transport):
        raise SearchPlannerSemanticRuleDiagnosticError("transport_factory_did_not_return_callable")
    evaluation_date = current_date or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", evaluation_date):
        raise SearchPlannerSemanticRuleDiagnosticError("current_date_invalid")

    budget = _Budget()
    results: list[dict[str, Any]] = []
    terminal_posture = "COMPLETED_SIX_CALL_PACKET"
    invalid_evidence_code: str | None = None
    for schedule in SCHEDULE:
        try:
            results.append(
                _execute_one(
                    schedule=schedule,
                    query=cases[schedule.query_case_id],
                    repository_sha=repository_sha,
                    current_date=evaluation_date,
                    route=route,
                    transport=transport,
                    budget=budget,
                )
            )
        except SearchPlannerSemanticRuleDiagnosticIntegrityError:
            terminal_posture = "INVALID_EVIDENCE"
            invalid_evidence_code = "EVALUATOR_INTEGRITY_FAILURE"
            break
    if terminal_posture == "COMPLETED_SIX_CALL_PACKET" and (
        len(results) != MAXIMUM_PHYSICAL_MODEL_ATTEMPTS
        or budget.physical_model_attempts != MAXIMUM_PHYSICAL_MODEL_ATTEMPTS
    ):
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("completed_packet_physical_count_mismatch")
    if budget.physical_model_attempts > MAXIMUM_PHYSICAL_MODEL_ATTEMPTS:
        raise SearchPlannerSemanticRuleDiagnosticIntegrityError("physical_attempt_cap_exceeded")

    packet = {
        "schema_version": SEMANTIC_RULE_DIAGNOSTIC_SCHEMA_VERSION,
        "phase": "SEARCHPLANNER-SEMANTIC-RULE-DIAGNOSTIC-AND-V8-BOUNDARY-EVALUATOR-01",
        "prompt_arm_id": CURRENT_MAIN_V8_ONLY,
        "repository_identity": {
            "repository_sha": repository_sha,
            "planner_prompt_schema_version": SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
            "provider": REQUIRED_PRODUCT_PROVIDER,
            "model": REQUIRED_MODEL,
            "reasoning_effort": REQUIRED_REASONING_EFFORT,
            "mode": REQUIRED_MODE,
        },
        "scheduled_call_order": [entry.call_id for entry in SCHEDULE],
        "call_results": results,
        "aggregate_physical_attempt_counts": {
            "planner_model_attempts": budget.physical_model_attempts,
            "total_model_attempts": budget.physical_model_attempts,
            "maximum_authorized_model_attempts": MAXIMUM_PHYSICAL_MODEL_ATTEMPTS,
            "retry_count": 0,
            "fallback_count": 0,
            "replacement_call_count": 0,
            "embedding_attempts": 0,
            "search_attempts": 0,
            "read_attempts": 0,
        },
        "aggregate_usage_cost_accounting": {
            "observed_cost_usd": format(budget.observed_cost_usd, "f"),
            "maximum_cost_usd": format(MAXIMUM_TOTAL_COST_USD, "f"),
            "cost_within_cap": budget.observed_cost_usd <= MAXIMUM_TOTAL_COST_USD,
        },
        "downstream_zero_attestation": {
            **{key: 0 for key in _DOWNSTREAM_ZERO_KEYS},
            "semantic_judge_calls": 0,
        },
        "raw_retention_false_attestation": {
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
            "cleaned_proposal_retained": False,
            "answer_contract_retained": False,
            "exception_text_retained": False,
            "provider_payload_retained": False,
            "private_logs_retained": False,
        },
        "stability_screening": _stability(results),
        "terminal_posture": terminal_posture,
        "invalid_evidence_code": invalid_evidence_code,
    }
    _assert_safe_packet(packet, forbidden_values=tuple(cases.values()))
    if output_path is not None:
        write_sanitized_packet(
            packet,
            output_path=output_path,
            repository_root=repository_root,
            forbidden_values=tuple(cases.values()),
        )
    return packet


def _assert_safe_packet(
    value: Any,
    *,
    forbidden_values: Sequence[str] = (),
) -> None:
    """Reject forbidden fields and exact raw case text from retained packets."""

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if str(key).casefold() in _FORBIDDEN_PACKET_KEYS:
                    raise SearchPlannerSemanticRuleDiagnosticIntegrityError("forbidden_packet_material_key")
                visit(nested)
        elif isinstance(item, (tuple, list)):
            for nested in item:
                visit(nested)
        elif isinstance(item, str) and item in forbidden_values:
            raise SearchPlannerSemanticRuleDiagnosticIntegrityError("query_material_entered_retained_packet")

    json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    visit(value)


def write_sanitized_packet(
    packet: Mapping[str, Any],
    *,
    output_path: Path,
    repository_root: Path,
    forbidden_values: Sequence[str] = (),
) -> None:
    """Write one sanitized packet outside the repository tree."""

    target = output_path.expanduser().resolve()
    root = repository_root.expanduser().resolve()
    try:
        target.relative_to(root)
    except ValueError:
        pass
    else:
        raise SearchPlannerSemanticRuleDiagnosticError("output_path_must_be_outside_repository")
    if not target.parent.is_dir() or target.exists():
        raise SearchPlannerSemanticRuleDiagnosticError("output_path_unavailable_or_already_exists")
    _assert_safe_packet(packet, forbidden_values=forbidden_values)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(packet, handle, sort_keys=True, indent=2, ensure_ascii=True)
        handle.write("\n")


def current_repository_sha(*, repository_root: Path = REPOSITORY_ROOT) -> str:
    """Return the exact current HEAD without inspecting private data."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SearchPlannerSemanticRuleDiagnosticError("repository_head_unavailable") from exc
    result = completed.stdout.strip()
    if not _HEX_GIT_SHA.fullmatch(result):
        raise SearchPlannerSemanticRuleDiagnosticError("repository_head_identity_invalid")
    return result


def load_case_inputs(
    path: Path,
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, str]:
    """Load Q1/Q2 solely from an external operator-supplied JSON file."""

    target = path.expanduser().resolve()
    try:
        target.relative_to(repository_root.expanduser().resolve())
    except ValueError:
        pass
    else:
        raise SearchPlannerSemanticRuleDiagnosticError("case_input_path_must_be_outside_repository")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SearchPlannerSemanticRuleDiagnosticError("case_inputs_unavailable") from exc
    if not isinstance(raw, Mapping):
        raise SearchPlannerSemanticRuleDiagnosticError("case_inputs_must_be_json_object")
    return _validate_cases(raw)


__all__ = [
    "CURRENT_MAIN_V8_ONLY",
    "MAXIMUM_PHYSICAL_MODEL_ATTEMPTS",
    "MAXIMUM_TOTAL_COST_USD",
    "SCHEDULE",
    "SEMANTIC_RULE_DIAGNOSTIC_SCHEMA_VERSION",
    "SearchPlannerSemanticRuleDiagnosticError",
    "SearchPlannerSemanticRuleDiagnosticIntegrityError",
    "current_repository_sha",
    "execute_search_planner_semantic_rule_diagnostic",
    "load_case_inputs",
    "verify_current_production_posture",
    "write_sanitized_packet",
]
