"""Narrow compatibility planner for AnalystOS model-origination evaluation.

The historical evaluator combined product-boundary interception, mechanical
validation, semantic scoring, prompt attribution, and final reporting.  Those
responsibilities now have separate owners.  This module keeps only the
provider-neutral configuration contracts needed by the ignored live-addendum
preparer and a sanitized ``plan_only`` manifest.

The legacy ``execute`` entrypoint is intentionally fail-closed.  A later phase
may install owner-specific live orchestration, but this compatibility module
must never regain combined evaluation authority.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.multicomponent_role_runtime import (  # noqa: E402
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
)
from core.searchos_iterative_judgment_runtime import (  # noqa: E402
    build_searchos_policy_snapshot,
)
from scripts.evaluation.model_origination_experiment_authority import (  # noqa: E402
    ExecutionIdentity,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (  # noqa: E402
    SCENARIO_BY_ID,
    SCENARIOS,
)

PLANNED_PACKET_SCHEMA_VERSION = "analystos_model_origination_responsibility_split_plan_v1"
LIVE_ADDENDUM_SCHEMA_VERSION = "analystos_model_origination_live_addendum_v2"
GPT54_MODEL_ID = "gpt-5.4-2026-03-05"
GPT54_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh"})

ROLE_SEARCH_PLANNER = "search_planner"
ANALYST_ROLES = frozenset({ROLE_COMPONENT_ANALYST, ROLE_CROSS_COMPONENT_ANALYST})
MODEL_ROLES = frozenset({ROLE_SEARCH_PLANNER, *ANALYST_ROLES})
EVALUATION_PASSES = frozenset({"planner_only", "analyst_only", "combined"})
EXECUTION_MODES = frozenset({"plan_only", "execute"})
DETERMINISTIC_DOWNSTREAM_OWNERS = (
    "synthesis_dprime",
    "searchos_fictional_acquisition_corpus",
    "runkernel_admission",
    "component_work_graph_v1",
    "sufficiency",
    "final_answer_packet",
    "author",
)
RESPONSIBILITY_OWNERS = {
    "product_boundary_observation": (
        "CanonicalProductSearchPlannerBoundary (observed by CanonicalProductSearchPlannerBoundaryObserver)"
    ),
    "mechanical_validation": (
        "CanonicalSearchPlannerMechanicalAuthority (search_planner_mechanical_validation.validate_product_observation)"
    ),
    "semantic_judgment": ("SearchPlannerSemanticJudgment (search_planner_semantic_judgment contract)"),
    "experiment_identity_and_attribution": ("ModelOriginationExperimentAuthority"),
    "decision_coordination": ("ModelOriginationEvaluationDecisionCoordinator"),
    "passive_reporting": "ModelOriginationEvaluationReportAssembler",
}
ALL_LIVE_LICENSE_FIELDS = (
    "schema_version",
    "reference",
    "repository_sha",
    "provider",
    "model",
    "reasoning_effort",
    "allowed_evaluation_pass",
    "allowed_model_roles",
    "allowed_scenario_ids",
    "maximum_model_calls",
    "maximum_scryraven_runs",
    "retry_cap",
    "timeout_seconds",
    "maximum_input_tokens",
    "maximum_output_tokens",
    "cost_ceiling",
    "output_packet_path",
    "decision",
    "stop_condition",
    "raw_retention_posture",
    "transport_factory_spec",
    "canonical_operator_command",
    "canonical_operator_command_digest",
)
FORBIDDEN_PACKET_KEYS = frozenset(
    {
        "api_key",
        "authorization_header",
        "chain_of_thought",
        "credential",
        "credentials",
        "database_row",
        "db_row",
        "full_prompt",
        "full_trace",
        "model_response",
        "private_log",
        "prompt_text",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "reasoning_trace",
        "secret",
        "token_value",
    }
)


class EvaluationConfigurationError(ValueError):
    """Raised before any transport exists when configuration is unsafe."""


class EvaluationTransportError(RuntimeError):
    """Compatibility error for the separately owned broker transport."""


class EvaluationTransport(Protocol):
    """Provider-neutral broker callable; never constructed by this module."""

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
    ) -> "EvaluationTransportResponse": ...


@dataclass(frozen=True, slots=True)
class EvaluationTransportResponse:
    """Transient output plus bounded safe accounting from one physical call."""

    output: Any = field(repr=False, compare=False)
    reasoning_effort: str
    generation_status: str
    generation_incomplete_reason: str | None
    max_output_tokens_reached: bool
    output_text_present: bool
    output_text_character_count: int
    output_text_digest: str
    usage_observed: bool
    input_tokens: int | None
    cached_input_tokens: int | None
    uncached_input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    non_reasoning_output_tokens: int | None
    total_tokens: int | None
    caller_calculated_route_priced_cost_usd: str | None
    cost_posture: str
    output_token_utilization: str | None
    reasoning_token_share: str | None
    provider_elapsed_milliseconds_total: int
    canonical_provider_used: str
    canonical_model_used: str
    provider_request_attempt_count: int = 1
    raw_material_retained: bool = False
    credentials_accessed: bool | None = None


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    evaluation_pass: str
    execution_mode: str = "plan_only"
    scenario_ids: tuple[str, ...] = ()
    selected_model_roles: tuple[str, ...] = ()
    reasoning_effort: str | None = None
    output_packet_path: str | None = None


@dataclass(frozen=True, slots=True)
class LiveAuthorization:
    reference: str
    repository_sha: str
    provider: str
    model: str
    reasoning_effort: str
    allowed_evaluation_pass: str
    allowed_model_roles: tuple[str, ...]
    allowed_scenario_ids: tuple[str, ...]
    maximum_model_calls: int
    maximum_scryraven_runs: int
    retry_cap: int
    timeout_seconds: float
    maximum_input_tokens: int
    maximum_output_tokens: int
    cost_ceiling: float
    output_packet_path: str
    decision: str
    stop_condition: str
    raw_retention_posture: str
    transport_factory_spec: str
    canonical_operator_command: str
    canonical_operator_command_digest: str
    schema_version: str = LIVE_ADDENDUM_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LiveAuthorization":
        missing = [name for name in ALL_LIVE_LICENSE_FIELDS if name not in value]
        if missing:
            raise EvaluationConfigurationError("live addendum is incomplete: " + ", ".join(missing))
        unknown = sorted(set(value) - set(ALL_LIVE_LICENSE_FIELDS))
        if unknown:
            raise EvaluationConfigurationError("live addendum contains unknown fields: " + ", ".join(unknown))
        try:
            authorization = cls(
                schema_version=str(value["schema_version"] or ""),
                reference=str(value["reference"] or ""),
                repository_sha=str(value["repository_sha"] or ""),
                provider=str(value["provider"] or ""),
                model=str(value["model"] or ""),
                reasoning_effort=str(value["reasoning_effort"] or ""),
                allowed_evaluation_pass=str(value["allowed_evaluation_pass"] or ""),
                allowed_model_roles=tuple(str(item) for item in value["allowed_model_roles"]),
                allowed_scenario_ids=tuple(str(item) for item in value["allowed_scenario_ids"]),
                maximum_model_calls=int(value["maximum_model_calls"]),
                maximum_scryraven_runs=int(value["maximum_scryraven_runs"]),
                retry_cap=int(value["retry_cap"]),
                timeout_seconds=float(value["timeout_seconds"]),
                maximum_input_tokens=int(value["maximum_input_tokens"]),
                maximum_output_tokens=int(value["maximum_output_tokens"]),
                cost_ceiling=float(value["cost_ceiling"]),
                output_packet_path=str(value["output_packet_path"] or ""),
                decision=str(value["decision"] or ""),
                stop_condition=str(value["stop_condition"] or ""),
                raw_retention_posture=str(value["raw_retention_posture"] or ""),
                transport_factory_spec=str(value["transport_factory_spec"] or ""),
                canonical_operator_command=str(value["canonical_operator_command"] or ""),
                canonical_operator_command_digest=str(value["canonical_operator_command_digest"] or ""),
            )
        except (TypeError, ValueError) as exc:
            raise EvaluationConfigurationError("live addendum contains a field with an invalid type") from exc
        if len(set(authorization.allowed_model_roles)) != len(authorization.allowed_model_roles):
            raise EvaluationConfigurationError("live addendum model roles contain duplicates")
        if len(set(authorization.allowed_scenario_ids)) != len(authorization.allowed_scenario_ids):
            raise EvaluationConfigurationError("live addendum scenario IDs contain duplicates")
        return authorization


@dataclass(frozen=True, slots=True)
class PlannedCall:
    call_id: str
    evaluation_pass: str
    execution_mode: str
    scenario_id: str
    scryraven_mode: str
    model_role: str
    reasoning_effort: str
    logical_call_purpose: str
    maximum_physical_calls: int
    retry_allowance: int
    expected_input_packet_owner: str
    expected_output_schema: str
    downstream_deterministic_owners: tuple[str, ...]
    skip_after_fail_closed_conditions: tuple[str, ...]
    expected_concept: str | None = None
    expected_cross_call_index: int | None = None

    def to_packet(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CallManifest:
    evaluation_pass: str
    execution_mode: str
    selected_model_roles: tuple[str, ...]
    reasoning_effort: str
    scenario_ids: tuple[str, ...]
    calls: tuple[PlannedCall, ...]
    deterministic_roles: tuple[str, ...]
    maximum_scryraven_runs: int
    total_maximum_physical_model_calls: int
    retry_allowance: int
    calls_by_role: Mapping[str, int]
    calls_by_scenario: Mapping[str, int]
    calls_by_pass: Mapping[str, int]
    conditional_call_ids: tuple[str, ...]

    def to_packet(self) -> dict[str, Any]:
        return {
            "evaluation_pass": self.evaluation_pass,
            "execution_mode": self.execution_mode,
            "selected_model_roles": list(self.selected_model_roles),
            "reasoning_effort": self.reasoning_effort,
            "scenario_ids": list(self.scenario_ids),
            "calls": [item.to_packet() for item in self.calls],
            "deterministic_roles": list(self.deterministic_roles),
            "maximum_scryraven_runs": self.maximum_scryraven_runs,
            "total_maximum_physical_model_calls": (self.total_maximum_physical_model_calls),
            "retry_allowance": self.retry_allowance,
            "calls_by_role": dict(self.calls_by_role),
            "calls_by_scenario": dict(self.calls_by_scenario),
            "calls_by_pass": dict(self.calls_by_pass),
            "conditional_call_ids": list(self.conditional_call_ids),
        }


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(rendered.encode("utf-8")).hexdigest()


def _nonempty(value: str, label: str) -> str:
    cleaned = " ".join(str(value or "").split())
    if not cleaned:
        raise EvaluationConfigurationError(f"{label} must be explicit")
    return cleaned


def current_repository_sha(repository_root: Path = ROOT) -> str:
    """Read only the current Git object identity."""

    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def resolve_request(request: EvaluationRequest) -> EvaluationRequest:
    """Normalize a request without constructing any provider transport."""

    evaluation_pass = str(request.evaluation_pass or "").strip()
    execution_mode = str(request.execution_mode or "plan_only").strip()
    if evaluation_pass not in EVALUATION_PASSES:
        raise EvaluationConfigurationError("evaluation_pass is invalid")
    if execution_mode not in EXECUTION_MODES:
        raise EvaluationConfigurationError("execution_mode is invalid")

    known_order = tuple(item.scenario_id for item in SCENARIOS)
    scenario_ids = tuple(request.scenario_ids) or known_order
    if len(set(scenario_ids)) != len(scenario_ids):
        raise EvaluationConfigurationError("scenario selection contains duplicates")
    unknown = sorted(set(scenario_ids) - set(known_order))
    if unknown:
        raise EvaluationConfigurationError("unknown scenario selection: " + ", ".join(unknown))
    scenario_ids = tuple(item for item in known_order if item in scenario_ids)

    requested_roles = tuple(dict.fromkeys(request.selected_model_roles))
    if any(role not in MODEL_ROLES for role in requested_roles):
        raise EvaluationConfigurationError("model role selection is invalid")
    if evaluation_pass == "planner_only":
        roles = requested_roles or (ROLE_SEARCH_PLANNER,)
        if set(roles) != {ROLE_SEARCH_PLANNER}:
            raise EvaluationConfigurationError("planner_only requires SearchPlanner as the sole model role")
    elif evaluation_pass == "analyst_only":
        roles = requested_roles or (
            ROLE_COMPONENT_ANALYST,
            ROLE_CROSS_COMPONENT_ANALYST,
        )
        if not set(roles) or not set(roles) <= ANALYST_ROLES:
            raise EvaluationConfigurationError(
                "analyst_only requires Component Analyst, Cross-Component Analyst, or both"
            )
    else:
        roles = requested_roles or (
            ROLE_SEARCH_PLANNER,
            ROLE_COMPONENT_ANALYST,
            ROLE_CROSS_COMPONENT_ANALYST,
        )
        if set(roles) != MODEL_ROLES:
            raise EvaluationConfigurationError(
                "combined requires explicit isolation of all three installed model roles"
            )

    canonical_role_order = (
        ROLE_SEARCH_PLANNER,
        ROLE_COMPONENT_ANALYST,
        ROLE_CROSS_COMPONENT_ANALYST,
    )
    roles = tuple(role for role in canonical_role_order if role in roles)
    reasoning_effort = str(request.reasoning_effort or "").strip() or None
    if execution_mode == "execute" and reasoning_effort is None:
        raise EvaluationConfigurationError("execute requires an explicit reasoning_effort")
    if reasoning_effort is not None and reasoning_effort not in GPT54_REASONING_EFFORTS:
        raise EvaluationConfigurationError("reasoning_effort is unsupported")
    return EvaluationRequest(
        evaluation_pass=evaluation_pass,
        execution_mode=execution_mode,
        scenario_ids=scenario_ids,
        selected_model_roles=roles,
        reasoning_effort=reasoning_effort,
        output_packet_path=request.output_packet_path,
    )


def _normalize_repository_relative_path(
    value: str,
    *,
    label: str,
    repository_root: Path = ROOT,
) -> str:
    text = _nonempty(value, label)
    root = repository_root.resolve()
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        relative = candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise EvaluationConfigurationError(f"{label} must remain inside the repository") from exc
    normalized = relative.as_posix()
    if not normalized or normalized == ".":
        raise EvaluationConfigurationError(f"{label} must name a repository file")
    return normalized


def _validate_transport_factory_spec(spec: str) -> str:
    normalized = _nonempty(spec, "transport factory spec")
    if not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*"
        r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
        r":[A-Za-z_][A-Za-z0-9_]*",
        normalized,
    ):
        raise EvaluationConfigurationError("transport factory spec must be one exact module.path:callable")
    return normalized


def build_execution_identity(
    request: EvaluationRequest,
    *,
    repository_sha: str,
    live_addendum_path: str,
    transport_factory_spec: str,
    repository_root: Path = ROOT,
) -> ExecutionIdentity:
    """Derive an exact command identity under experiment ownership."""

    resolved = resolve_request(request)
    if resolved.execution_mode != "execute":
        raise EvaluationConfigurationError("execution identity applies only to execute")
    exact_sha = _nonempty(repository_sha, "repository SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", exact_sha):
        raise EvaluationConfigurationError("repository SHA must be one exact lowercase Git object ID")
    addendum_path = _normalize_repository_relative_path(
        live_addendum_path,
        label="live addendum path",
        repository_root=repository_root,
    )
    if not resolved.output_packet_path:
        raise EvaluationConfigurationError("execute requires an explicit output packet path")
    output_path = _normalize_repository_relative_path(
        resolved.output_packet_path,
        label="output packet path",
        repository_root=repository_root,
    )
    factory_spec = _validate_transport_factory_spec(transport_factory_spec)
    argv: list[str] = [
        "scripts/evaluation/run_analystos_model_origination_evaluation.py",
        "--repository-sha",
        exact_sha,
        "--evaluation-pass",
        resolved.evaluation_pass,
        "--execution-mode",
        "execute",
        "--reasoning-effort",
        str(resolved.reasoning_effort),
    ]
    for role in resolved.selected_model_roles:
        argv.extend(("--role", role))
    for scenario_id in resolved.scenario_ids:
        argv.extend(("--scenario", scenario_id))
    argv.extend(
        (
            "--live-addendum",
            addendum_path,
            "--transport-factory",
            factory_spec,
            "--output",
            output_path,
        )
    )
    canonical_command = json.dumps(argv, ensure_ascii=True, separators=(",", ":"))
    command_digest = sha256(canonical_command.encode("utf-8")).hexdigest()
    identity_material = {
        "repository_sha": exact_sha,
        "evaluation_pass": resolved.evaluation_pass,
        "execution_mode": resolved.execution_mode,
        "reasoning_effort": resolved.reasoning_effort,
        "selected_model_roles": resolved.selected_model_roles,
        "scenario_ids": resolved.scenario_ids,
        "live_addendum_path": addendum_path,
        "transport_factory_spec": factory_spec,
        "output_packet_path": output_path,
        "canonical_operator_command_digest": command_digest,
    }
    return ExecutionIdentity(
        repository_sha=exact_sha,
        evaluation_pass=resolved.evaluation_pass,
        execution_mode=resolved.execution_mode,
        reasoning_effort=str(resolved.reasoning_effort),
        selected_model_roles=resolved.selected_model_roles,
        scenario_ids=resolved.scenario_ids,
        live_addendum_path=addendum_path,
        transport_factory_spec=factory_spec,
        output_packet_path=output_path,
        canonical_argv=tuple(argv),
        canonical_operator_command=canonical_command,
        canonical_operator_command_digest=command_digest,
        execution_identity_digest=_digest(identity_material),
    )


def validate_canonical_cli_invocation(
    execution_identity: ExecutionIdentity,
    actual_argv: Sequence[str],
) -> None:
    """Reject any reordered, omitted, duplicated, or added CLI token."""

    if tuple(actual_argv) != execution_identity.canonical_argv:
        raise EvaluationConfigurationError("actual CLI invocation differs from the licensed canonical command")


def _component_call_concepts(scenario: Any) -> tuple[str, ...]:
    """Derive call identity from scenario inputs, never teacher expectations."""

    concepts = [item.component_id for item in scenario.direct_facts]
    if scenario.unavailable_recovery:
        return tuple(concepts)
    generation_limit = _searched_generation_limit(scenario)
    generations = scenario.recovery_generations[:generation_limit]
    for generation in generations:
        concepts.extend(item.semantic_key for item in generation)
    return tuple(dict.fromkeys(concepts))


def _cross_call_specs(
    scenario: Any,
) -> tuple[dict[str, str | None], ...]:
    """Derive structural call census from recovery inputs and target graph."""

    specs: list[dict[str, str | None]] = []
    generation_limit = _searched_generation_limit(scenario)
    available_generations = scenario.recovery_generations[
        :generation_limit
    ]
    for index, _generation in enumerate(available_generations, start=1):
        if not scenario.targets:
            break
        target = scenario.targets[min(index - 1, len(scenario.targets) - 1)]
        specs.append(
            {
                "target_concept": target.component_id,
                "purpose": (f"originate the searched-premise proposal required before {target.component_id}"),
                "conditional_skip_reason": (
                    None if index == 1 else "skip when the prior searched generation fails closed"
                ),
            }
        )
    recovery_is_structurally_complete = (
        not scenario.unavailable_recovery
        and len(scenario.recovery_generations) <= generation_limit
    )
    if recovery_is_structurally_complete:
        for target in scenario.targets:
            specs.append(
                {
                    "target_concept": target.component_id,
                    "purpose": (f"originate the current-state inferred conclusion for {target.component_id}"),
                    "conditional_skip_reason": (
                        "skip when a required premise remains unresolved" if scenario.recovery_generations else None
                    ),
                }
            )
    return tuple(specs)


def _searched_generation_limit(scenario: Any) -> int:
    policy = build_searchos_policy_snapshot(
        run_id="model-origination-call-manifest",
        request_id=str(scenario.scenario_id),
        profile_name=str(scenario.mode),
        existing_gap_recovery_runtime_open=True,
    )
    return int(
        policy["recovery_policy"][
            "maximum_searched_premise_cycles_per_run"
        ]
    )


def build_call_manifest(
    request: EvaluationRequest,
    *,
    retry_allowance: int = 0,
) -> CallManifest:
    """Construct a call census without making or judging any call."""

    resolved = resolve_request(request)
    if retry_allowance < 0:
        raise EvaluationConfigurationError("retry allowance cannot be negative")
    calls: list[PlannedCall] = []
    physical_per_logical = 1 + retry_allowance
    for scenario_id in resolved.scenario_ids:
        scenario = SCENARIO_BY_ID[scenario_id]
        if ROLE_SEARCH_PLANNER in resolved.selected_model_roles:
            calls.append(
                PlannedCall(
                    call_id=f"{scenario_id}:search_planner:initial",
                    evaluation_pass=resolved.evaluation_pass,
                    execution_mode=resolved.execution_mode,
                    scenario_id=scenario_id,
                    scryraven_mode=scenario.mode,
                    model_role=ROLE_SEARCH_PLANNER,
                    reasoning_effort=str(resolved.reasoning_effort),
                    logical_call_purpose=("originate root-query meaning, components, dependencies, and search needs"),
                    maximum_physical_calls=physical_per_logical,
                    retry_allowance=retry_allowance,
                    expected_input_packet_owner=("core.search_planner_runtime.SearchPlannerInput"),
                    expected_output_schema=("core.search_planner_model_adapter validated planner proposal"),
                    downstream_deterministic_owners=(
                        "search_planner_parser",
                        "answer_contract_acceptance",
                        *DETERMINISTIC_DOWNSTREAM_OWNERS,
                    ),
                    skip_after_fail_closed_conditions=(),
                )
            )
        if ROLE_COMPONENT_ANALYST in resolved.selected_model_roles:
            direct_ids = {item.component_id for item in scenario.direct_facts}
            for index, concept in enumerate(_component_call_concepts(scenario), start=1):
                recovery = concept not in direct_ids
                conditions = (
                    ("skip after planner failure",) if ROLE_SEARCH_PLANNER in resolved.selected_model_roles else ()
                )
                if recovery:
                    conditions += (
                        "skip unless deterministic fictional SearchOS recovery reaches component evidence custody",
                    )
                calls.append(
                    PlannedCall(
                        call_id=(f"{scenario_id}:component_analyst:{index}:{concept}"),
                        evaluation_pass=resolved.evaluation_pass,
                        execution_mode=resolved.execution_mode,
                        scenario_id=scenario_id,
                        scryraven_mode=scenario.mode,
                        model_role=ROLE_COMPONENT_ANALYST,
                        reasoning_effort=str(resolved.reasoning_effort),
                        logical_call_purpose=(
                            f"originate direct support posture for {concept}"
                            if not recovery
                            else f"originate recovered direct-premise support posture for {concept}"
                        ),
                        maximum_physical_calls=physical_per_logical,
                        retry_allowance=retry_allowance,
                        expected_input_packet_owner=(
                            "ordinary component Analyst input packet"
                            if not recovery
                            else "SearchOS recovery component Analyst input packet"
                        ),
                        expected_output_schema=("multicomponent component_analyst semantic role artifact"),
                        downstream_deterministic_owners=(DETERMINISTIC_DOWNSTREAM_OWNERS),
                        skip_after_fail_closed_conditions=conditions,
                        expected_concept=concept,
                    )
                )
        if ROLE_CROSS_COMPONENT_ANALYST in resolved.selected_model_roles:
            for index, cross in enumerate(_cross_call_specs(scenario), start=1):
                conditions = []
                if ROLE_SEARCH_PLANNER in resolved.selected_model_roles:
                    conditions.append("skip after planner failure")
                if cross["conditional_skip_reason"]:
                    conditions.append(cross["conditional_skip_reason"])
                calls.append(
                    PlannedCall(
                        call_id=(f"{scenario_id}:cross_component_analyst:{index}"),
                        evaluation_pass=resolved.evaluation_pass,
                        execution_mode=resolved.execution_mode,
                        scenario_id=scenario_id,
                        scryraven_mode=scenario.mode,
                        model_role=ROLE_CROSS_COMPONENT_ANALYST,
                        reasoning_effort=str(resolved.reasoning_effort),
                        logical_call_purpose=cross["purpose"],
                        maximum_physical_calls=physical_per_logical,
                        retry_allowance=retry_allowance,
                        expected_input_packet_owner=("ordinary current-state Cross-Component Analyst input packet"),
                        expected_output_schema=("multicomponent cross_component_analyst semantic role artifact"),
                        downstream_deterministic_owners=(DETERMINISTIC_DOWNSTREAM_OWNERS),
                        skip_after_fail_closed_conditions=tuple(conditions),
                        expected_concept=cross["target_concept"],
                        expected_cross_call_index=index,
                    )
                )

    logical_by_role = Counter(item.model_role for item in calls)
    logical_by_scenario = Counter(item.scenario_id for item in calls)
    physical_by_role = {role: logical_by_role.get(role, 0) * physical_per_logical for role in sorted(MODEL_ROLES)}
    physical_by_scenario = {
        scenario_id: logical_by_scenario.get(scenario_id, 0) * physical_per_logical
        for scenario_id in resolved.scenario_ids
    }
    deterministic = {
        "synthesis_dprime",
        "searchos_fictional_acquisition_corpus",
        "sufficiency",
        "final_answer_packet",
        "author",
    }
    deterministic.update(MODEL_ROLES - set(resolved.selected_model_roles))
    return CallManifest(
        evaluation_pass=resolved.evaluation_pass,
        execution_mode=resolved.execution_mode,
        selected_model_roles=resolved.selected_model_roles,
        reasoning_effort=str(resolved.reasoning_effort),
        scenario_ids=resolved.scenario_ids,
        calls=tuple(calls),
        deterministic_roles=tuple(sorted(deterministic)),
        maximum_scryraven_runs=len(resolved.scenario_ids),
        total_maximum_physical_model_calls=sum(item.maximum_physical_calls for item in calls),
        retry_allowance=retry_allowance,
        calls_by_role=physical_by_role,
        calls_by_scenario=physical_by_scenario,
        calls_by_pass={resolved.evaluation_pass: sum(item.maximum_physical_calls for item in calls)},
        conditional_call_ids=tuple(item.call_id for item in calls if item.skip_after_fail_closed_conditions),
    )


def evaluation_id_for(
    *,
    authorization: LiveAuthorization,
    execution_identity: ExecutionIdentity,
    manifest: CallManifest,
) -> str:
    """Bind a compatibility ID to exact licensed call identity."""

    return _digest(
        {
            "execution_identity_digest": (execution_identity.execution_identity_digest),
            "license_reference": authorization.reference,
            "provider": authorization.provider,
            "model": authorization.model,
            "reasoning_effort": authorization.reasoning_effort,
            "call_manifest": manifest.to_packet(),
        }
    )


def build_planned_packet(
    request: EvaluationRequest,
    *,
    repository_sha: str,
) -> dict[str, Any]:
    """Build a zero-live owner and call manifest, never an evaluation."""

    resolved = resolve_request(request)
    if resolved.execution_mode != "plan_only":
        raise EvaluationConfigurationError("planned packet requires execution_mode=plan_only")
    manifest = build_call_manifest(resolved, retry_allowance=0)
    packet = {
        "schema_version": PLANNED_PACKET_SCHEMA_VERSION,
        "evaluation_id": _digest(
            {
                "repository_sha": repository_sha,
                "evaluation_pass": resolved.evaluation_pass,
                "scenario_ids": resolved.scenario_ids,
                "roles": resolved.selected_model_roles,
                "execution_mode": "plan_only",
            }
        ),
        "repository_sha": repository_sha,
        "evaluation_pass": resolved.evaluation_pass,
        "execution_mode": "plan_only",
        "scenario_ids": list(resolved.scenario_ids),
        "selected_model_roles": list(resolved.selected_model_roles),
        "responsibility_owners": dict(RESPONSIBILITY_OWNERS),
        "exact_role_call_manifest": manifest.to_packet(),
        "owner_results": {name: "NOT_RUN" for name in RESPONSIBILITY_OWNERS},
        "primary_failure_attribution": "NOT_RUN",
        "call_counts": {
            "model_calls": 0,
            "provider_calls": 0,
            "search_calls": 0,
            "retrieval_calls": 0,
            "external_calls": 0,
        },
        "transport_created": False,
        "credentials_accessed": False,
        "raw_material_retained": False,
        "former_combined_authority_retired": True,
        "execute_available": False,
    }
    reject_forbidden_packet_material(packet)
    return packet


def validate_live_authorization(
    request: EvaluationRequest,
    authorization: LiveAuthorization | None,
    *,
    repository_sha: str,
    execution_identity: ExecutionIdentity | None = None,
) -> CallManifest:
    """Validate licensed dimensions without constructing a transport."""

    resolved = resolve_request(request)
    if resolved.execution_mode != "execute":
        raise EvaluationConfigurationError("live authorization applies only to execute")
    if authorization is None:
        raise EvaluationConfigurationError("execute is unavailable without an exact live addendum")
    if execution_identity is None:
        raise EvaluationConfigurationError("execute is unavailable without an exact execution identity")
    if authorization.schema_version != LIVE_ADDENDUM_SCHEMA_VERSION:
        raise EvaluationConfigurationError("live addendum schema_version is invalid")
    for label, value in (
        ("live addendum reference", authorization.reference),
        ("repository SHA", authorization.repository_sha),
        ("provider", authorization.provider),
        ("model", authorization.model),
        ("reasoning effort", authorization.reasoning_effort),
        (
            "allowed evaluation_pass",
            authorization.allowed_evaluation_pass,
        ),
        ("output packet path", authorization.output_packet_path),
        ("decision", authorization.decision),
        ("stop condition", authorization.stop_condition),
        (
            "raw-retention posture",
            authorization.raw_retention_posture,
        ),
        (
            "transport factory spec",
            authorization.transport_factory_spec,
        ),
        (
            "canonical operator command",
            authorization.canonical_operator_command,
        ),
        (
            "canonical operator command digest",
            authorization.canonical_operator_command_digest,
        ),
    ):
        _nonempty(value, label)
    if authorization.repository_sha != repository_sha:
        raise EvaluationConfigurationError("live addendum repository SHA does not match the exact checkout")
    if authorization.allowed_evaluation_pass != resolved.evaluation_pass:
        raise EvaluationConfigurationError("live addendum does not license the requested evaluation_pass")
    if authorization.reasoning_effort != resolved.reasoning_effort:
        raise EvaluationConfigurationError("live addendum reasoning effort does not match the request")
    if authorization.model == GPT54_MODEL_ID and authorization.reasoning_effort not in GPT54_REASONING_EFFORTS:
        raise EvaluationConfigurationError("GPT-5.4 reasoning effort is unsupported")
    if tuple(authorization.allowed_model_roles) != resolved.selected_model_roles:
        raise EvaluationConfigurationError("live addendum role set/order must exactly match the selected roles")
    if tuple(authorization.allowed_scenario_ids) != resolved.scenario_ids:
        raise EvaluationConfigurationError("live addendum scenario set/order must exactly match the selected scenarios")
    if authorization.retry_cap < 0:
        raise EvaluationConfigurationError("live retry cap cannot be negative")
    if authorization.timeout_seconds <= 0 or authorization.timeout_seconds > 600:
        raise EvaluationConfigurationError("live timeout seconds must be within the installed broker bound")
    if authorization.maximum_input_tokens <= 0:
        raise EvaluationConfigurationError("maximum input tokens must be positive")
    if authorization.maximum_output_tokens <= 0:
        raise EvaluationConfigurationError("maximum output tokens must be positive")
    if authorization.cost_ceiling <= 0:
        raise EvaluationConfigurationError("cost ceiling must be positive")
    if authorization.raw_retention_posture != "sanitized_only":
        raise EvaluationConfigurationError("raw-retention posture must be exactly sanitized_only")
    if not resolved.output_packet_path:
        raise EvaluationConfigurationError("execute requires an explicit output packet path")
    normalized_output_path = _normalize_repository_relative_path(
        resolved.output_packet_path,
        label="output packet path",
    )
    if authorization.output_packet_path != normalized_output_path:
        raise EvaluationConfigurationError("live addendum output packet path must be normalized and exact")
    if execution_identity.repository_sha != repository_sha:
        raise EvaluationConfigurationError("execution identity repository SHA does not match the exact checkout")
    if execution_identity.evaluation_pass != resolved.evaluation_pass:
        raise EvaluationConfigurationError("execution identity evaluation_pass does not match the request")
    if execution_identity.execution_mode != resolved.execution_mode:
        raise EvaluationConfigurationError("execution identity execution_mode does not match the request")
    if execution_identity.reasoning_effort != resolved.reasoning_effort:
        raise EvaluationConfigurationError("execution identity reasoning effort does not match the request")
    if execution_identity.selected_model_roles != resolved.selected_model_roles:
        raise EvaluationConfigurationError("execution identity roles do not match the exact ordered request")
    if execution_identity.scenario_ids != resolved.scenario_ids:
        raise EvaluationConfigurationError("execution identity scenarios do not match the exact ordered request")
    if execution_identity.output_packet_path != normalized_output_path:
        raise EvaluationConfigurationError("execution identity output path does not match the request")
    if authorization.output_packet_path != execution_identity.output_packet_path:
        raise EvaluationConfigurationError("live addendum output path is not normalized or execution-bound")
    if authorization.transport_factory_spec != execution_identity.transport_factory_spec:
        raise EvaluationConfigurationError("transport factory spec differs from the exact live addendum")
    if authorization.canonical_operator_command != execution_identity.canonical_operator_command:
        raise EvaluationConfigurationError("canonical operator command differs from the exact live addendum")
    if authorization.canonical_operator_command_digest != execution_identity.canonical_operator_command_digest:
        raise EvaluationConfigurationError("canonical operator command digest differs from the exact live addendum")
    if (
        authorization.canonical_operator_command_digest
        != sha256(authorization.canonical_operator_command.encode("utf-8")).hexdigest()
    ):
        raise EvaluationConfigurationError("canonical operator command digest does not cover the licensed command")
    manifest = build_call_manifest(resolved, retry_allowance=authorization.retry_cap)
    if authorization.maximum_model_calls != manifest.total_maximum_physical_model_calls:
        raise EvaluationConfigurationError("maximum model calls must exactly match the computed call manifest")
    if authorization.maximum_scryraven_runs != manifest.maximum_scryraven_runs:
        raise EvaluationConfigurationError("maximum ScryRaven runs must exactly match the scenario count")
    return manifest


def reject_forbidden_packet_material(value: Any) -> None:
    """Recursively reject raw or secret-bearing packet field names."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).strip().casefold().replace("-", "_")
            if key in FORBIDDEN_PACKET_KEYS:
                raise EvaluationConfigurationError(f"forbidden evaluation packet field: {key}")
            reject_forbidden_packet_material(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            reject_forbidden_packet_material(child)


def _write_packet(path: str, packet: Mapping[str, Any]) -> None:
    normalized = _normalize_repository_relative_path(path, label="output packet path")
    target = ROOT / normalized
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_evaluation(
    request: EvaluationRequest,
    *,
    repository_sha: str | None = None,
    authorization: LiveAuthorization | None = None,
    execution_identity: ExecutionIdentity | None = None,
    transport_factory: Any | None = None,
) -> dict[str, Any]:
    """Return only a sanitized plan; legacy combined execute is retired."""

    resolved = resolve_request(request)
    if resolved.execution_mode != "plan_only":
        raise EvaluationConfigurationError(
            "legacy combined evaluator execute path is retired; owner-specific live orchestration is not installed"
        )
    if authorization is not None or execution_identity is not None or transport_factory is not None:
        raise EvaluationConfigurationError(
            "plan_only rejects live authorization, execution identity, and transport factory"
        )
    packet = build_planned_packet(
        resolved,
        repository_sha=repository_sha or current_repository_sha(),
    )
    if resolved.output_packet_path:
        _write_packet(resolved.output_packet_path, packet)
    return packet


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Plan the split AnalystOS model-origination evaluation owners."))
    parser.add_argument(
        "--evaluation-pass",
        choices=sorted(EVALUATION_PASSES),
        required=True,
    )
    parser.add_argument(
        "--execution-mode",
        choices=sorted(EXECUTION_MODES),
        default="plan_only",
    )
    parser.add_argument("--repository-sha")
    parser.add_argument(
        "--reasoning-effort",
        choices=sorted(GPT54_REASONING_EFFORTS),
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=tuple(item.scenario_id for item in SCENARIOS),
        dest="scenario_ids",
    )
    parser.add_argument(
        "--role",
        action="append",
        choices=sorted(MODEL_ROLES),
        dest="selected_model_roles",
    )
    parser.add_argument("--output", dest="output_packet_path")
    parser.add_argument("--live-addendum")
    parser.add_argument("--transport-factory")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    actual_argv = (
        tuple(argv)
        if argv is not None
        else (
            _normalize_repository_relative_path(
                sys.argv[0],
                label="evaluator entrypoint",
            ),
            *sys.argv[1:],
        )
    )
    if not actual_argv:
        raise EvaluationConfigurationError("CLI invocation must include the evaluator entrypoint")
    args = _parse_args(actual_argv[1:])
    request = EvaluationRequest(
        evaluation_pass=args.evaluation_pass,
        execution_mode=args.execution_mode,
        scenario_ids=tuple(args.scenario_ids or ()),
        selected_model_roles=tuple(args.selected_model_roles or ()),
        reasoning_effort=args.reasoning_effort,
        output_packet_path=args.output_packet_path,
    )
    if args.execution_mode == "execute":
        raise EvaluationConfigurationError(
            "legacy combined evaluator execute path is retired before addendum "
            "or transport access; owner-specific live orchestration is not installed"
        )
    if args.repository_sha or args.live_addendum or args.transport_factory:
        raise EvaluationConfigurationError("plan_only rejects execute-only live addendum and transport options")
    packet = run_evaluation(request)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvaluationConfigurationError, EvaluationTransportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


__all__ = [
    "EVALUATION_PASSES",
    "EXECUTION_MODES",
    "LIVE_ADDENDUM_SCHEMA_VERSION",
    "CallManifest",
    "EvaluationConfigurationError",
    "EvaluationRequest",
    "EvaluationTransport",
    "EvaluationTransportError",
    "EvaluationTransportResponse",
    "ExecutionIdentity",
    "LiveAuthorization",
    "PlannedCall",
    "RESPONSIBILITY_OWNERS",
    "build_call_manifest",
    "build_execution_identity",
    "build_planned_packet",
    "current_repository_sha",
    "evaluation_id_for",
    "reject_forbidden_packet_material",
    "resolve_request",
    "run_evaluation",
    "validate_canonical_cli_invocation",
    "validate_live_authorization",
]
