"""Fail-closed AnalystOS model-origination evaluation operator.

This is an offline-preparation harness. ``plan_only`` is the default and never
constructs a transport. ``execute`` requires a complete, exact live addendum
and an injected transport factory; this module contains no provider client,
credential lookup, route default, or environment-based permission.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed:
the merged SearchOS/AnalystOS ordinary-path fixture and
``core.pipeline_orchestrator.run_pipeline``.
Runtime consumer:
the next separately licensed bounded live-model origination evaluation.
Why direct product work is not done here:
the current phase is explicitly offline/no-live.
Integration deadline:
the next separately licensed bounded live-model origination evaluation.
Exit condition:
use once for the acceptance decision, then convert to a durable regression
guard or retire it.
Why this is not a shadow product path:
the default execute runner injects only at installed model boundaries and
re-enters the merged ordinary pipeline fixture; it owns no canonical state.
Forbidden interpretation:
plan-only or synthetic execution does not prove real-model capability.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import multicomponent_role_runtime as role_runtime  # noqa: E402
from core.multicomponent_role_runtime import (  # noqa: E402
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
)
from core.search_planner_model_adapter import (  # noqa: E402
    SearchPlannerModelAdapter,
    validate_and_sanitize_model_output,
)
from core.search_planner_model_prompt import (  # noqa: E402
    SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
)
from tests.fixtures.analystos_model_origination_expectations import (  # noqa: E402
    ANALYST_ROLES,
    MODEL_ROLES,
    ROLE_SEARCH_PLANNER,
    CrossCallExpectation,
    expectation_for,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (  # noqa: E402
    BOUNDED_LIMIT,
    SCENARIO_BY_ID,
    SCENARIOS,
    planner_payload,
)

PLANNED_PACKET_SCHEMA_VERSION = "analystos_model_origination_planned_packet_v1"
RESULT_PACKET_SCHEMA_VERSION = "analystos_model_origination_result_packet_v1"
LIVE_ADDENDUM_SCHEMA_VERSION = "analystos_model_origination_live_addendum_v1"

EVALUATION_PASSES = frozenset({"planner_only", "analyst_only", "combined"})
EXECUTION_MODES = frozenset({"plan_only", "execute"})
CLASSIFICATIONS = frozenset(
    {
        "PASS",
        "MODEL",
        "PACKET",
        "PROMPT",
        "PARSER_CONTRACT",
        "OPERATING_SYSTEM",
        "REVIEW_REQUIRED",
        "NOT_RUN",
    }
)

DETERMINISTIC_DOWNSTREAM_OWNERS = (
    "component_dprime",
    "synthesis_dprime",
    "searchos_fictional_acquisition_corpus",
    "runkernel_admission",
    "component_work_graph_v1",
    "sufficiency",
    "final_answer_packet",
    "author",
)
ALL_LIVE_LICENSE_FIELDS = (
    "reference",
    "repository_sha",
    "provider",
    "model",
    "allowed_evaluation_pass",
    "allowed_model_roles",
    "allowed_scenario_ids",
    "maximum_model_calls",
    "maximum_scryraven_runs",
    "retry_cap",
    "maximum_input_tokens",
    "maximum_output_tokens",
    "cost_ceiling",
    "output_packet_path",
    "decision",
    "stop_condition",
    "raw_retention_posture",
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
FORBIDDEN_MODEL_AUTHORITY_KEYS = frozenset(
    {
        "admit",
        "admitted",
        "admission",
        "author_output",
        "canonical_graph",
        "canonical_state",
        "dispatch_search",
        "execute_search",
        "final_answer",
        "graph_mutation",
        "mutate_graph",
        "run_kernel_action",
        "runkernel_action",
        "searchos_action",
    }
)


class EvaluationConfigurationError(ValueError):
    """Raised before any transport exists when an evaluation is unsafe."""


class EvaluationTransportError(RuntimeError):
    """Raised when an injected transport violates the licensed call envelope."""


class EvaluationTransport(Protocol):
    """Provider-neutral callable constructed only after license validation."""

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
    input_tokens: int
    output_tokens: int
    cost: float
    provider_request_attempt_count: int = 1
    raw_material_retained: bool = False
    credentials_accessed: bool | None = None


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    evaluation_pass: str
    execution_mode: str = "plan_only"
    scenario_ids: tuple[str, ...] = ()
    selected_model_roles: tuple[str, ...] = ()
    output_packet_path: str | None = None


@dataclass(frozen=True, slots=True)
class LiveAuthorization:
    reference: str
    repository_sha: str
    provider: str
    model: str
    allowed_evaluation_pass: str
    allowed_model_roles: tuple[str, ...]
    allowed_scenario_ids: tuple[str, ...]
    maximum_model_calls: int
    maximum_scryraven_runs: int
    retry_cap: int
    maximum_input_tokens: int
    maximum_output_tokens: int
    cost_ceiling: float
    output_packet_path: str
    decision: str
    stop_condition: str
    raw_retention_posture: str
    schema_version: str = LIVE_ADDENDUM_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LiveAuthorization":
        missing = [field for field in ALL_LIVE_LICENSE_FIELDS if field not in value]
        if missing:
            raise EvaluationConfigurationError("live addendum is incomplete: " + ", ".join(missing))
        try:
            return cls(
                schema_version=str(value.get("schema_version") or ""),
                reference=str(value["reference"] or ""),
                repository_sha=str(value["repository_sha"] or ""),
                provider=str(value["provider"] or ""),
                model=str(value["model"] or ""),
                allowed_evaluation_pass=str(value["allowed_evaluation_pass"] or ""),
                allowed_model_roles=tuple(str(item) for item in value["allowed_model_roles"]),
                allowed_scenario_ids=tuple(str(item) for item in value["allowed_scenario_ids"]),
                maximum_model_calls=int(value["maximum_model_calls"]),
                maximum_scryraven_runs=int(value["maximum_scryraven_runs"]),
                retry_cap=int(value["retry_cap"]),
                maximum_input_tokens=int(value["maximum_input_tokens"]),
                maximum_output_tokens=int(value["maximum_output_tokens"]),
                cost_ceiling=float(value["cost_ceiling"]),
                output_packet_path=str(value["output_packet_path"] or ""),
                decision=str(value["decision"] or ""),
                stop_condition=str(value["stop_condition"] or ""),
                raw_retention_posture=str(value["raw_retention_posture"] or ""),
            )
        except (TypeError, ValueError) as exc:
            raise EvaluationConfigurationError("live addendum contains a field with an invalid type") from exc


@dataclass(frozen=True, slots=True)
class PlannedCall:
    call_id: str
    evaluation_pass: str
    execution_mode: str
    scenario_id: str
    scryraven_mode: str
    model_role: str
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
            "scenario_ids": list(self.scenario_ids),
            "calls": [item.to_packet() for item in self.calls],
            "deterministic_roles": list(self.deterministic_roles),
            "maximum_scryraven_runs": self.maximum_scryraven_runs,
            "total_maximum_physical_model_calls": self.total_maximum_physical_model_calls,
            "retry_allowance": self.retry_allowance,
            "calls_by_role": dict(self.calls_by_role),
            "calls_by_scenario": dict(self.calls_by_scenario),
            "calls_by_pass": dict(self.calls_by_pass),
            "conditional_call_ids": list(self.conditional_call_ids),
        }


@dataclass(frozen=True, slots=True)
class ScoreCard:
    checks: Mapping[str, bool | None]
    passed: int
    failed: int
    review_required: int
    status: str

    @classmethod
    def from_checks(cls, checks: Mapping[str, bool | None]) -> "ScoreCard":
        passed = sum(value is True for value in checks.values())
        failed = sum(value is False for value in checks.values())
        review = sum(value is None for value in checks.values())
        status = "REVIEW_REQUIRED" if review else ("PASS" if not failed else "FAIL")
        return cls(dict(checks), passed, failed, review, status)

    def to_packet(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PairedProbeEvidence:
    scenario_id: str
    provider: str
    model: str
    semantic_input_facts_digest: str
    instruction_difference: str
    control_instruction_digest: str
    variant_instruction_digest: str
    control_semantic_status: str
    variant_semantic_status: str
    maximum_physical_calls_each: int
    retry_allowance_each: int
    deterministic_comparison_criteria: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassificationEvidence:
    call_ran: bool
    packet_complete: bool
    parser_consumable: bool
    semantic_status: str
    operating_system_transition_reached: bool
    paired_probe: PairedProbeEvidence | None = None
    not_run_reason: str | None = None


@dataclass(frozen=True, slots=True)
class BoundaryCallObservation:
    call_id: str
    role: str
    safe_input_packet_digest: str
    physical_calls: int
    retries: int
    packet_complete: bool
    parser_consumable: bool
    semantic_status: str
    safe_semantic_projection: Mapping[str, Any]
    proposal_only: bool
    authority_boundary_respected: bool
    parser_failure_kind: str | None = None

    def to_packet(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "role": self.role,
            "safe_input_packet_digest": self.safe_input_packet_digest,
            "physical_calls": self.physical_calls,
            "retries": self.retries,
            "packet_complete": self.packet_complete,
            "parser_consumable": self.parser_consumable,
            "semantic_status": self.semantic_status,
            "safe_semantic_projection": deepcopy(dict(self.safe_semantic_projection)),
            "proposal_only": self.proposal_only,
            "authority_boundary_respected": self.authority_boundary_respected,
            "parser_failure_kind": self.parser_failure_kind,
        }


@dataclass(frozen=True, slots=True)
class ScenarioRunResult:
    scenario_id: str
    ordinary_downstream_terminal_posture: str
    operating_system_transition_reached: bool
    safe_output_artifact_refs: tuple[Mapping[str, Any], ...] = ()
    deterministic_fixture_call_counts: Mapping[str, int] = field(default_factory=dict)
    execution: Any | None = field(default=None, repr=False, compare=False)


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(rendered.encode("utf-8")).hexdigest()


def _normalize_text(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


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
    return EvaluationRequest(
        evaluation_pass=evaluation_pass,
        execution_mode=execution_mode,
        scenario_ids=scenario_ids,
        selected_model_roles=roles,
        output_packet_path=request.output_packet_path,
    )


def build_call_manifest(
    request: EvaluationRequest,
    *,
    retry_allowance: int = 0,
) -> CallManifest:
    """Construct the exact logical/maximum-physical call manifest."""

    resolved = resolve_request(request)
    if retry_allowance < 0:
        raise EvaluationConfigurationError("retry allowance cannot be negative")
    calls: list[PlannedCall] = []
    physical_per_logical = 1 + retry_allowance
    for scenario_id in resolved.scenario_ids:
        scenario = SCENARIO_BY_ID[scenario_id]
        expectation = expectation_for(scenario_id)
        if ROLE_SEARCH_PLANNER in resolved.selected_model_roles:
            calls.append(
                PlannedCall(
                    call_id=f"{scenario_id}:search_planner:initial",
                    evaluation_pass=resolved.evaluation_pass,
                    execution_mode=resolved.execution_mode,
                    scenario_id=scenario_id,
                    scryraven_mode=scenario.mode,
                    model_role=ROLE_SEARCH_PLANNER,
                    logical_call_purpose="originate root-query meaning, components, dependencies, and search needs",
                    maximum_physical_calls=physical_per_logical,
                    retry_allowance=retry_allowance,
                    expected_input_packet_owner="core.search_planner_runtime.SearchPlannerInput",
                    expected_output_schema="core.search_planner_model_adapter validated planner proposal",
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
            for index, concept in enumerate(expectation.component_call_concepts, start=1):
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
                        call_id=f"{scenario_id}:component_analyst:{index}:{concept}",
                        evaluation_pass=resolved.evaluation_pass,
                        execution_mode=resolved.execution_mode,
                        scenario_id=scenario_id,
                        scryraven_mode=scenario.mode,
                        model_role=ROLE_COMPONENT_ANALYST,
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
                        expected_output_schema="multicomponent component_analyst semantic role artifact",
                        downstream_deterministic_owners=DETERMINISTIC_DOWNSTREAM_OWNERS,
                        skip_after_fail_closed_conditions=conditions,
                        expected_concept=concept,
                    )
                )
        if ROLE_CROSS_COMPONENT_ANALYST in resolved.selected_model_roles:
            for index, cross in enumerate(expectation.cross_calls, start=1):
                conditions = []
                if ROLE_SEARCH_PLANNER in resolved.selected_model_roles:
                    conditions.append("skip after planner failure")
                if cross.conditional_skip_reason:
                    conditions.append(cross.conditional_skip_reason)
                calls.append(
                    PlannedCall(
                        call_id=f"{scenario_id}:cross_component_analyst:{index}",
                        evaluation_pass=resolved.evaluation_pass,
                        execution_mode=resolved.execution_mode,
                        scenario_id=scenario_id,
                        scryraven_mode=scenario.mode,
                        model_role=ROLE_CROSS_COMPONENT_ANALYST,
                        logical_call_purpose=cross.purpose,
                        maximum_physical_calls=physical_per_logical,
                        retry_allowance=retry_allowance,
                        expected_input_packet_owner="ordinary current-state Cross-Component Analyst input packet",
                        expected_output_schema="multicomponent cross_component_analyst semantic role artifact",
                        downstream_deterministic_owners=DETERMINISTIC_DOWNSTREAM_OWNERS,
                        skip_after_fail_closed_conditions=tuple(conditions),
                        expected_concept=cross.target_concept,
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
        "component_dprime",
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


def _expected_semantic_projection(scenario_id: str) -> dict[str, Any]:
    scenario = SCENARIO_BY_ID[scenario_id]
    expectation = expectation_for(scenario_id)
    planned_components = planner_payload(scenario)["answer_components"]
    return {
        "root_query_digest": _digest(scenario.root_query),
        "required_components": [
            {
                "concept": item["component_id"],
                "component_purpose": item["component_purpose"],
                "allowed_support_kinds": list(item["allowed_support_kinds"]),
                "max_inference_depth": item["max_inference_depth"],
                "dependency_concepts": list(item.get("dependency_component_ids") or ()),
            }
            for item in planned_components
        ],
        "cross_component_calls": [
            {
                "classification": item.classification,
                "target_concept": item.target_concept,
                "dependency_concepts": list(item.dependency_concepts),
                "relationship_aliases": list(item.relationship_aliases),
                "support_kind": item.support_kind,
                "semantic_inference_depth": item.semantic_inference_depth,
            }
            for item in expectation.cross_calls
        ],
        "expected_terminal_posture": expectation.expected_terminal_posture,
        "expected_status": expectation.expected_status,
        "expected_search_generations": expectation.expected_search_generations,
        "rejected_search_generation": expectation.rejected_search_generation,
        "honest_nonclosure": expectation.honest_nonclosure,
    }


def build_planned_packet(
    request: EvaluationRequest,
    *,
    repository_sha: str,
) -> dict[str, Any]:
    """Build a sanitized zero-live packet for every plan-only invocation."""

    resolved = resolve_request(request)
    if resolved.execution_mode != "plan_only":
        raise EvaluationConfigurationError("planned packet requires execution_mode=plan_only")
    manifest = build_call_manifest(resolved, retry_allowance=0)
    per_scenario = []
    for scenario_id in resolved.scenario_ids:
        scenario_calls = [item.to_packet() for item in manifest.calls if item.scenario_id == scenario_id]
        per_scenario.append(
            {
                "repository_sha": repository_sha,
                "scenario_id": scenario_id,
                "scryraven_mode": SCENARIO_BY_ID[scenario_id].mode,
                "evaluation_pass": resolved.evaluation_pass,
                "execution_mode": resolved.execution_mode,
                "selected_model_roles": list(resolved.selected_model_roles),
                "expected_packet_owners": sorted({item["expected_input_packet_owner"] for item in scenario_calls}),
                "expected_output_schemas": sorted({item["expected_output_schema"] for item in scenario_calls}),
                "maximum_call_count": sum(item["maximum_physical_calls"] for item in scenario_calls),
                "retry_posture": "zero_retries",
                "deterministic_downstream_path": list(DETERMINISTIC_DOWNSTREAM_OWNERS),
                "missing_live_license_fields": list(ALL_LIVE_LICENSE_FIELDS),
                "expected_semantic_projection": _expected_semantic_projection(scenario_id),
                "transport_created": False,
                "credentials_accessed": False,
                "external_calls": 0,
            }
        )
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
        "scenario_ids": list(resolved.scenario_ids),
        "scryraven_modes": {scenario_id: SCENARIO_BY_ID[scenario_id].mode for scenario_id in resolved.scenario_ids},
        "evaluation_pass": resolved.evaluation_pass,
        "execution_mode": resolved.execution_mode,
        "selected_provider": None,
        "selected_model": None,
        "selected_model_roles": list(resolved.selected_model_roles),
        "exact_role_call_manifest": manifest.to_packet(),
        "planned_scenario_packets": per_scenario,
        "safe_input_packet_digests": [],
        "safe_output_artifact_refs": [],
        "structural_score": ScoreCard.from_checks({"not_run_in_plan_only": None}).to_packet(),
        "semantic_score": ScoreCard.from_checks({"not_run_in_plan_only": None}).to_packet(),
        "primary_failure_attribution": "NOT_RUN",
        "observed_safe_semantic_projection": [],
        "ordinary_downstream_terminal_posture": "planned_not_executed",
        "call_counts": {
            "model_calls": 0,
            "scryraven_runs": 0,
            "provider_calls": 0,
            "search_calls": 0,
            "retrieval_calls": 0,
            "read_calls": 0,
            "navigation_calls": 0,
            "map_calls": 0,
            "crawl_calls": 0,
            "external_calls": 0,
            "fictional_search_operations": 0,
            "fictional_read_operations": 0,
        },
        "retry_counts": {"total": 0},
        "token_counts": {"input": 0, "output": 0},
        "observed_cost": 0.0,
        "skipped_call_reasons": {item.call_id: "execution_mode=plan_only" for item in manifest.calls},
        "redaction_posture": {
            "sanitized_only": True,
            "raw_prompts_retained": False,
            "raw_model_responses_retained": False,
            "raw_provider_payloads_retained": False,
            "secrets_retained": False,
            "full_traces_retained": False,
            "private_logs_retained": False,
            "database_rows_retained": False,
            "reasoning_traces_retained": False,
        },
        "live_license_reference": None,
        "transport_created": False,
        "credentials_accessed": False,
        "external_calls": 0,
        "symbolic_cost_formula": (
            "maximum_physical_calls * "
            "((maximum_input_tokens * selected_input_token_price) + "
            "(maximum_output_tokens * selected_output_token_price))"
        ),
    }
    reject_forbidden_packet_material(packet)
    return packet


def validate_live_authorization(
    request: EvaluationRequest,
    authorization: LiveAuthorization | None,
    *,
    repository_sha: str,
) -> CallManifest:
    """Validate every licensed dimension before transport construction."""

    resolved = resolve_request(request)
    if resolved.execution_mode != "execute":
        raise EvaluationConfigurationError("live authorization applies only to execute")
    if authorization is None:
        raise EvaluationConfigurationError("execute is unavailable without an exact live addendum")
    if authorization.schema_version != LIVE_ADDENDUM_SCHEMA_VERSION:
        raise EvaluationConfigurationError("live addendum schema_version is invalid")
    for label, value in (
        ("live addendum reference", authorization.reference),
        ("repository SHA", authorization.repository_sha),
        ("provider", authorization.provider),
        ("model", authorization.model),
        ("allowed evaluation_pass", authorization.allowed_evaluation_pass),
        ("output packet path", authorization.output_packet_path),
        ("decision", authorization.decision),
        ("stop condition", authorization.stop_condition),
        ("raw-retention posture", authorization.raw_retention_posture),
    ):
        _nonempty(value, label)
    if authorization.repository_sha != repository_sha:
        raise EvaluationConfigurationError("live addendum repository SHA does not match the exact checkout")
    if authorization.allowed_evaluation_pass != resolved.evaluation_pass:
        raise EvaluationConfigurationError("live addendum does not license the requested evaluation_pass")
    if tuple(authorization.allowed_model_roles) != resolved.selected_model_roles:
        raise EvaluationConfigurationError("live addendum role set/order must exactly match the selected roles")
    if tuple(authorization.allowed_scenario_ids) != resolved.scenario_ids:
        raise EvaluationConfigurationError("live addendum scenario set/order must exactly match the selected scenarios")
    if authorization.retry_cap < 0:
        raise EvaluationConfigurationError("live retry cap cannot be negative")
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
    if authorization.output_packet_path != resolved.output_packet_path:
        raise EvaluationConfigurationError("live addendum output packet path must exactly match the request")
    manifest = build_call_manifest(
        resolved,
        retry_allowance=authorization.retry_cap,
    )
    if authorization.maximum_model_calls != manifest.total_maximum_physical_model_calls:
        raise EvaluationConfigurationError("maximum model calls must exactly match the computed call manifest")
    if authorization.maximum_scryraven_runs != manifest.maximum_scryraven_runs:
        raise EvaluationConfigurationError("maximum ScryRaven runs must exactly match the scenario count")
    return manifest


def paired_probe_demonstrates_prompt_causality(
    evidence: PairedProbeEvidence | None,
) -> bool:
    """Return true only for an exact controlled counterfactual."""

    if evidence is None:
        return False
    return bool(
        evidence.scenario_id
        and evidence.provider
        and evidence.model
        and evidence.semantic_input_facts_digest
        and evidence.instruction_difference
        and evidence.control_instruction_digest
        and evidence.variant_instruction_digest
        and evidence.control_instruction_digest != evidence.variant_instruction_digest
        and evidence.control_semantic_status == "wrong"
        and evidence.variant_semantic_status == "met"
        and evidence.maximum_physical_calls_each > 0
        and evidence.retry_allowance_each >= 0
        and evidence.deterministic_comparison_criteria
    )


def classify_result(evidence: ClassificationEvidence) -> str:
    """Apply the primary attribution rules without model-as-judge inference."""

    if not evidence.call_ran:
        return "NOT_RUN"
    if not evidence.packet_complete:
        return "PACKET"
    if evidence.semantic_status == "ambiguous":
        return "REVIEW_REQUIRED"
    if not evidence.parser_consumable:
        return "PARSER_CONTRACT" if evidence.semantic_status == "met" else "REVIEW_REQUIRED"
    if evidence.semantic_status == "wrong":
        return "PROMPT" if paired_probe_demonstrates_prompt_causality(evidence.paired_probe) else "MODEL"
    if evidence.semantic_status != "met":
        return "REVIEW_REQUIRED"
    if not evidence.operating_system_transition_reached:
        return "OPERATING_SYSTEM"
    return "PASS"


def _alias_matches(
    text: str,
    aliases: Mapping[str, tuple[str, ...]],
) -> tuple[set[str], bool]:
    normalized = _normalize_text(text)
    matches = {
        concept
        for concept, candidates in aliases.items()
        if any(_normalize_text(candidate) and _normalize_text(candidate) in normalized for candidate in candidates)
    }
    return matches, len(matches) > 1


def _planner_semantic_projection(
    normalized: Mapping[str, Any],
    *,
    scenario_id: str,
) -> tuple[dict[str, Any], str]:
    scenario = SCENARIO_BY_ID[scenario_id]
    expectation = expectation_for(scenario_id)
    expected_components = {item["component_id"]: item for item in planner_payload(scenario)["answer_components"]}
    observed_components = [dict(item) for item in normalized.get("answer_components") or ()]
    concept_to_observed: dict[str, dict[str, Any]] = {}
    ambiguous = False
    for item in observed_components:
        exact_component_id = str(item.get("component_id") or "")
        if exact_component_id in expected_components:
            matches, overlaps = {exact_component_id}, False
        else:
            candidate_text = " ".join(
                str(item.get(key) or "")
                for key in (
                    "component_id",
                    "user_facing_label",
                    "user_facing_question",
                )
            )
            matches, overlaps = _alias_matches(
                candidate_text,
                expectation.concept_aliases,
            )
        matches &= set(expected_components)
        ambiguous = ambiguous or overlaps or len(matches) > 1
        if len(matches) == 1:
            concept = next(iter(matches))
            if concept in concept_to_observed:
                ambiguous = True
            concept_to_observed[concept] = item

    checks: dict[str, bool | None] = {}
    for concept, expected in expected_components.items():
        observed = concept_to_observed.get(concept)
        checks[f"component:{concept}:recognized"] = observed is not None
        if observed is None:
            continue
        checks[f"component:{concept}:purpose"] = observed.get("component_purpose") == expected.get("component_purpose")
        checks[f"component:{concept}:support_kind"] = set(observed.get("allowed_support_kinds") or ()) == set(
            expected.get("allowed_support_kinds") or ()
        )
        checks[f"component:{concept}:depth"] = int(observed.get("max_inference_depth") or 0) == int(
            expected.get("max_inference_depth") or 0
        )
        expected_dependencies = set(expected.get("dependency_component_ids") or ())
        observed_dependencies: set[str] = set()
        for dependency in observed.get("dependency_component_ids") or ():
            dependency_text = str(dependency)
            if dependency_text in expected_components:
                matches, overlaps = {dependency_text}, False
            else:
                matches, overlaps = _alias_matches(
                    dependency_text,
                    expectation.concept_aliases,
                )
            ambiguous = ambiguous or overlaps or len(matches) > 1
            observed_dependencies.update(matches)
        checks[f"component:{concept}:dependencies"] = observed_dependencies == expected_dependencies
    target_concepts = {item.component_id for item in scenario.targets} or {
        item.component_id for item in scenario.direct_facts
    }
    root_matches, root_overlap = _alias_matches(
        " ".join(
            str(normalized.get(key) or "")
            for key in (
                "question_meaning_summary",
                "requested_output",
                "requested_synthesis_directive",
            )
        ),
        expectation.concept_aliases,
    )
    del root_overlap
    checks["root_query_interpretation"] = bool(root_matches & target_concepts)
    normalized_output_text = _normalize_text(json.dumps(normalized, sort_keys=True, default=str))
    distractor_hits = [
        concept for concept in expectation.distractor_concepts if _normalize_text(concept) in normalized_output_text
    ]
    checks["distractor_resistance"] = not distractor_hits
    if ambiguous:
        status = "ambiguous"
    elif all(value is True for value in checks.values()):
        status = "met"
    else:
        status = "wrong"
    safe_projection = {
        "matched_component_concepts": sorted(concept_to_observed),
        "expected_component_concepts": sorted(expected_components),
        "root_target_concepts_matched": sorted(root_matches & target_concepts),
        "distractor_concepts_matched": distractor_hits,
        "checks": checks,
    }
    return safe_projection, status


def _component_semantic_projection(
    normalized: Mapping[str, Any],
    *,
    scenario_id: str,
    expected_concept: str,
) -> tuple[dict[str, Any], str]:
    expectation = expectation_for(scenario_id)
    matches, overlap = _alias_matches(
        str(normalized.get("claim_text") or ""),
        expectation.concept_aliases,
    )
    matched_expected = expected_concept in matches
    status_value = str(normalized.get("support_status") or "")
    status_supported = status_value in {"supported", "supported_with_caveats"}
    if overlap or (matches and not matched_expected):
        semantic_status = "ambiguous"
    elif matched_expected and status_supported:
        semantic_status = "met"
    elif not matches and status_supported:
        semantic_status = "ambiguous"
    else:
        semantic_status = "wrong"
    return (
        {
            "expected_concept": expected_concept,
            "matched_concepts": sorted(matches),
            "support_status": status_value,
            "proposal_only": True,
            "blocker_count": len(normalized.get("blockers") or ()),
            "caveat_count": len(normalized.get("caveats") or ()),
        },
        semantic_status,
    )


def _cross_candidate_projection(
    normalized: Mapping[str, Any],
    expected: CrossCallExpectation,
    *,
    aliases: Mapping[str, tuple[str, ...]],
) -> tuple[dict[str, Any], str]:
    candidates = [dict(item) for item in normalized.get("query_resolution_proposals") or ()]
    matching = [item for item in candidates if item.get("classification") == expected.classification]
    if len(candidates) != 1 or len(matching) != 1:
        return (
            {
                "expected_classification": expected.classification,
                "candidate_count": len(candidates),
                "matching_candidate_count": len(matching),
            },
            "wrong",
        )
    item = matching[0]
    target_text = " ".join(
        str(item.get(key) or "")
        for key in (
            "local_target_key",
            "premise_semantics",
            "proposed_conclusion",
        )
    )
    target_matches, target_overlap = _alias_matches(target_text, aliases)
    target_ok = expected.target_concept in target_matches
    dependency_texts: list[str] = []
    for key in (
        "current_dependency_component_refs",
        "current_admitted_premise_node_refs",
    ):
        for ref in item.get(key) or ():
            if isinstance(ref, Mapping):
                dependency_texts.append(
                    " ".join(
                        str(ref.get(name) or "")
                        for name in (
                            "component_id",
                            "synthesis_key",
                            "user_facing_label",
                            "user_facing_question",
                        )
                    )
                )
            else:
                dependency_texts.append(str(ref))
    dependencies: set[str] = set()
    dependency_overlap = False
    for text in dependency_texts:
        matches, overlap = _alias_matches(text, aliases)
        dependencies.update(matches)
        dependency_overlap = dependency_overlap or overlap
    dependency_ok = set(expected.dependency_concepts) <= dependencies
    relationship_value = _normalize_text(item.get("relationship_type"))
    relationship_ok: bool | None = True
    if expected.relationship_aliases:
        relationship_ok = any(
            _normalize_text(alias) == relationship_value or _normalize_text(alias) in relationship_value
            for alias in expected.relationship_aliases
        )
        if not relationship_ok and target_ok and dependency_ok and relationship_value:
            relationship_ok = None
    depth_ok = int(item.get("proposed_semantic_inference_depth") or 0) == (expected.semantic_inference_depth)
    support_ok = str(item.get("support_kind") or expected.support_kind) == expected.support_kind
    checks = {
        "target_recognition": target_ok,
        "dependency_shape": dependency_ok,
        "relationship": relationship_ok,
        "semantic_inference_depth": depth_ok,
        "support_kind": support_ok,
    }
    ambiguous = target_overlap or dependency_overlap or relationship_ok is None
    if ambiguous:
        status = "ambiguous"
    elif all(value is True for value in checks.values()):
        status = "met"
    else:
        status = "wrong"
    return (
        {
            "classification": item.get("classification"),
            "expected_target_concept": expected.target_concept,
            "matched_target_concepts": sorted(target_matches),
            "expected_dependency_concepts": list(expected.dependency_concepts),
            "matched_dependency_concepts": sorted(dependencies),
            "relationship_type": relationship_value,
            "checks": checks,
        },
        status,
    )


def project_and_score_role_output(
    role: str,
    normalized: Mapping[str, Any],
    *,
    call: PlannedCall,
) -> tuple[dict[str, Any], str]:
    """Produce only a safe semantic projection and deterministic score."""

    if role == ROLE_SEARCH_PLANNER:
        return _planner_semantic_projection(
            normalized,
            scenario_id=call.scenario_id,
        )
    if role == ROLE_COMPONENT_ANALYST:
        return _component_semantic_projection(
            normalized,
            scenario_id=call.scenario_id,
            expected_concept=str(call.expected_concept or ""),
        )
    if role == ROLE_CROSS_COMPONENT_ANALYST:
        index = int(call.expected_cross_call_index or 0)
        expected = expectation_for(call.scenario_id).cross_calls[index - 1]
        return _cross_candidate_projection(
            normalized,
            expected,
            aliases=expectation_for(call.scenario_id).concept_aliases,
        )
    raise EvaluationConfigurationError(f"unsupported evaluation role: {role}")


def reject_forbidden_packet_material(value: Any) -> None:
    """Reject forbidden durable material recursively."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in FORBIDDEN_PACKET_KEYS:
                raise EvaluationConfigurationError(f"forbidden evaluation packet field: {key}")
            reject_forbidden_packet_material(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            reject_forbidden_packet_material(child)


def _model_output_respects_authority_boundary(value: Any) -> bool:
    """Reject explicit model claims to deterministic owner authority."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_MODEL_AUTHORITY_KEYS:
                return False
            if not _model_output_respects_authority_boundary(child):
                return False
    elif isinstance(value, (list, tuple)):
        return all(_model_output_respects_authority_boundary(item) for item in value)
    return True


def _installed_system_prompt_matches(role: str, system_prompt: str) -> bool:
    if role == ROLE_SEARCH_PLANNER:
        return system_prompt == SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
    if role == ROLE_COMPONENT_ANALYST:
        return system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
    if role == ROLE_CROSS_COMPONENT_ANALYST:
        return system_prompt in {
            ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST],
            SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
        }
    return False


def _input_packet_complete(
    role: str,
    prompt: str,
    *,
    scenario_id: str,
) -> bool:
    """Check only required packet context, without retaining prompt material."""

    scenario = SCENARIO_BY_ID[scenario_id]
    if role == ROLE_SEARCH_PLANNER:
        return "Sanitized planner input JSON:" in prompt and scenario.root_query in prompt
    try:
        payload = json.loads(prompt)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping):
        return False
    if role == ROLE_COMPONENT_ANALYST:
        return bool(
            payload.get("component_ref") and payload.get("accepted_contract_ref") and payload.get("component_evidence")
        )
    if role == ROLE_CROSS_COMPONENT_ANALYST:
        current_nodes = any(
            payload.get(key)
            for key in (
                "accepted_component_refs",
                "component_nodes",
                "licensed_current_component_refs",
                "current_synthesis_nodes",
                "preserved_boundary_synthesis_catalog",
            )
        )
        return bool(
            current_nodes
            and payload.get("graph_ref")
            and payload.get("requested_synthesis_directive") == scenario.root_query
        )
    return False


@dataclass(slots=True)
class ExecutionBudgetLedger:
    """One exact whole-evaluation budget shared by every scenario controller."""

    physical_calls: int = 0
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    credentials_accessed: bool | None = None


class BoundaryInjectionController:
    """Match selected installed model-boundary calls to one exact manifest."""

    def __init__(
        self,
        *,
        manifest: CallManifest,
        scenario_id: str,
        authorization: LiveAuthorization,
        transport: EvaluationTransport,
        budget_ledger: ExecutionBudgetLedger | None = None,
    ) -> None:
        self.manifest = manifest
        self.scenario_id = scenario_id
        self.authorization = authorization
        self.transport = transport
        self.budget_ledger = budget_ledger or ExecutionBudgetLedger(
            credentials_accessed=getattr(
                transport,
                "credentials_accessed",
                None,
            )
        )
        self._calls_by_role = {
            role: [item for item in manifest.calls if item.scenario_id == scenario_id and item.model_role == role]
            for role in MODEL_ROLES
        }
        self._role_indices = {role: 0 for role in MODEL_ROLES}
        self.observations: list[BoundaryCallObservation] = []
        self.total_physical_calls = 0
        self.total_retries = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    @property
    def credentials_accessed(self) -> bool | None:
        return self.budget_ledger.credentials_accessed

    @property
    def selected_roles(self) -> tuple[str, ...]:
        return self.manifest.selected_model_roles

    def _next_call(self, role: str) -> PlannedCall:
        index = self._role_indices[role]
        calls = self._calls_by_role[role]
        if index >= len(calls):
            raise EvaluationTransportError(f"unmanifested {role} call blocked before transport")
        self._role_indices[role] = index + 1
        return calls[index]

    def invoke(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
    ) -> Any:
        call = self._next_call(role)
        if provider != self.authorization.provider or model != self.authorization.model:
            raise EvaluationTransportError("selected route differs from the exact live addendum")
        if not _installed_system_prompt_matches(role, system_prompt):
            raise EvaluationTransportError("selected role did not reach its exact installed system prompt")
        prompt_digest = sha256(prompt.encode("utf-8")).hexdigest()
        if not _input_packet_complete(
            role,
            prompt,
            scenario_id=self.scenario_id,
        ):
            self.observations.append(
                BoundaryCallObservation(
                    call_id=call.call_id,
                    role=role,
                    safe_input_packet_digest=prompt_digest,
                    physical_calls=0,
                    retries=0,
                    packet_complete=False,
                    parser_consumable=False,
                    semantic_status="ambiguous",
                    safe_semantic_projection={
                        "packet_complete": False,
                        "expected_input_packet_owner": call.expected_input_packet_owner,
                    },
                    proposal_only=False,
                    authority_boundary_respected=False,
                    parser_failure_kind="incomplete_model_boundary_packet",
                )
            )
            raise EvaluationTransportError("required model-boundary packet context is incomplete")
        raw: Any = None
        attempts = 0
        last_exc: Exception | None = None
        while attempts <= self.authorization.retry_cap:
            if self.budget_ledger.physical_calls >= self.authorization.maximum_model_calls:
                raise EvaluationTransportError("model call cap exceeded before transport")
            attempts += 1
            self.total_physical_calls += 1
            self.budget_ledger.physical_calls += 1
            try:
                response = self.transport(
                    role=role,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    provider=provider,
                    model=model,
                    maximum_input_tokens=self.authorization.maximum_input_tokens,
                    maximum_output_tokens=self.authorization.maximum_output_tokens,
                )
                if not isinstance(response, EvaluationTransportResponse):
                    raise EvaluationTransportError("transport response omitted required safe accounting")
                if (
                    response.provider_request_attempt_count != 1
                    or response.input_tokens < 0
                    or response.output_tokens < 0
                    or response.cost < 0
                    or response.raw_material_retained
                ):
                    raise EvaluationTransportError("transport response safe accounting is invalid")
                if response.input_tokens > self.authorization.maximum_input_tokens:
                    raise EvaluationTransportError("input-token cap exceeded; stopping after the exact call")
                if response.output_tokens > self.authorization.maximum_output_tokens:
                    raise EvaluationTransportError("output-token cap exceeded; stopping after the exact call")
                self.total_input_tokens += response.input_tokens
                self.total_output_tokens += response.output_tokens
                self.total_cost += response.cost
                self.budget_ledger.input_tokens += response.input_tokens
                self.budget_ledger.output_tokens += response.output_tokens
                self.budget_ledger.cost += response.cost
                if self.budget_ledger.cost > self.authorization.cost_ceiling:
                    raise EvaluationTransportError("cost ceiling exceeded; stopping after the exact call")
                if response.credentials_accessed is not None:
                    self.budget_ledger.credentials_accessed = bool(self.budget_ledger.credentials_accessed) or bool(
                        response.credentials_accessed
                    )
                raw = response.output
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if isinstance(exc, EvaluationTransportError):
                    break
                if attempts > self.authorization.retry_cap:
                    break
                self.total_retries += 1
                self.budget_ledger.retries += 1
        if last_exc is not None:
            raise EvaluationTransportError(
                f"injected model transport failed closed: {type(last_exc).__name__}"
            ) from last_exc

        parser_consumable = True
        parser_failure_kind: str | None = None
        safe_projection: dict[str, Any] = {}
        semantic_status = "ambiguous"
        authority_boundary_respected = False
        try:
            if isinstance(raw, Mapping):
                parsed = deepcopy(dict(raw))
            else:
                parsed_value = json.loads(str(raw or ""))
                if not isinstance(parsed_value, Mapping):
                    raise ValueError("model output must be one JSON object")
                parsed = dict(parsed_value)
            authority_boundary_respected = _model_output_respects_authority_boundary(parsed)
            if role == ROLE_SEARCH_PLANNER:
                normalized = validate_and_sanitize_model_output(parsed)
            else:
                normalized = role_runtime._normalize_semantic_output(  # noqa: SLF001
                    role,
                    role_runtime._parse_role_output(  # noqa: SLF001
                        parsed,
                        clean_json_response=None,
                    ),
                )
            safe_projection, semantic_status = project_and_score_role_output(
                role,
                normalized,
                call=call,
            )
            if not authority_boundary_respected:
                semantic_status = "wrong"
                safe_projection = {
                    **safe_projection,
                    "authority_boundary_respected": False,
                }
        except Exception as exc:
            parser_consumable = False
            parser_failure_kind = type(exc).__name__
            known_safe_field_families = (
                sorted(
                    str(key)
                    for key in parsed
                    if str(key)
                    in {
                        "answer_components",
                        "blockers",
                        "caveats",
                        "claim_text",
                        "component_search_requirements",
                        "nonclaims",
                        "query_resolution_proposals",
                        "semantic_slots",
                        "source_obligation_candidates",
                        "support_status",
                        "synthesis_proposals",
                    }
                )
                if "parsed" in locals()
                else []
            )
            fallback_projection: dict[str, Any] = {}
            fallback_status = "ambiguous"
            if "parsed" in locals() and authority_boundary_respected:
                try:
                    fallback_projection, fallback_status = project_and_score_role_output(
                        role,
                        parsed,
                        call=call,
                    )
                except Exception:
                    fallback_projection = {}
                    fallback_status = "ambiguous"
            semantic_status = fallback_status
            safe_projection = {
                **fallback_projection,
                "parser_consumable": False,
                "known_safe_field_families": known_safe_field_families,
            }
        self.observations.append(
            BoundaryCallObservation(
                call_id=call.call_id,
                role=role,
                safe_input_packet_digest=prompt_digest,
                physical_calls=attempts,
                retries=max(0, attempts - 1),
                packet_complete=True,
                parser_consumable=parser_consumable,
                semantic_status=semantic_status,
                safe_semantic_projection=safe_projection,
                proposal_only=authority_boundary_respected,
                authority_boundary_respected=authority_boundary_respected,
                parser_failure_kind=parser_failure_kind,
            )
        )
        if isinstance(raw, Mapping):
            return json.dumps(raw)
        return raw


def _role_for_system_prompt(system_prompt: str) -> str | None:
    if system_prompt == SEARCH_PLANNER_MODEL_SYSTEM_PROMPT:
        return ROLE_SEARCH_PLANNER
    if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
        return ROLE_COMPONENT_ANALYST
    if system_prompt in {
        ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST],
        SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
    }:
        return ROLE_CROSS_COMPONENT_ANALYST
    return None


def _run_ordinary_fixture_scenario(
    *,
    scenario_id: str,
    controller: BoundaryInjectionController,
) -> ScenarioRunResult:
    """Inject selected roles into the exact merged ordinary-path fixture."""

    import pytest

    from tests.fixtures import searchos_analystos_offline_scenarios as corpus

    scenario = SCENARIO_BY_ID[scenario_id]
    base_harness = corpus.SearchOSAnalystOSHarness
    authorization = controller.authorization

    class EvaluationHarness(base_harness):
        def deps(self):
            dependencies = super().deps()
            if ROLE_SEARCH_PLANNER not in controller.selected_roles:
                return dependencies
            adapter = SearchPlannerModelAdapter(
                ask_model=self.ask_model,
                clean_json_response=lambda text: text,
                provider=authorization.provider,
                model=authorization.model,
                effort="low",
                use_reasoning=True,
                max_tokens=authorization.maximum_output_tokens,
                enabled=True,
                licensed=True,
            )
            return replace(dependencies, search_planner_adapter=adapter)

        def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
            role = _role_for_system_prompt(system_prompt)
            if role not in controller.selected_roles:
                return super().ask_model(prompt, system_prompt, **kwargs)
            if role == ROLE_COMPONENT_ANALYST:
                payload = json.loads(prompt)
                component = dict(payload.get("component_ref") or {})
                self.component_contexts.append(
                    {
                        "component_ref": {
                            key: component.get(key)
                            for key in (
                                "component_id",
                                "component_revision",
                                "component_digest",
                                "component_purpose",
                                "user_facing_label",
                                "user_facing_question",
                                "dependency_component_ids",
                                "acceptance_criteria",
                            )
                        },
                        "accepted_contract_ref": dict(payload.get("accepted_contract_ref") or {}),
                        "evidence_ref_id": dict(payload.get("component_evidence") or {}).get("evidence_ref_id"),
                    }
                )
            elif role == ROLE_CROSS_COMPONENT_ANALYST:
                payload = json.loads(prompt)
                self.cross_contexts.append(
                    {
                        "selective": (system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT),
                        "accepted_contract_ref": dict(
                            payload.get("accepted_contract_ref") or payload.get("current_contract_ref") or {}
                        ),
                        "graph_ref": dict(payload.get("graph_ref") or {}),
                        "requested_synthesis_directive": payload.get("requested_synthesis_directive"),
                        "component_ids": sorted(
                            str(item.get("component_id"))
                            for item in corpus._available_nodes(payload)  # noqa: SLF001
                            if item.get("component_id")
                        ),
                        "synthesis_keys": sorted(
                            str(item.get("synthesis_key"))
                            for item in corpus._available_nodes(payload)  # noqa: SLF001
                            if item.get("synthesis_key")
                        ),
                        "accepted_component_context": [
                            {
                                key: dict(item).get(key)
                                for key in (
                                    "component_id",
                                    "component_purpose",
                                    "user_facing_label",
                                    "user_facing_question",
                                    "dependency_component_ids",
                                    "acceptance_criteria",
                                )
                            }
                            for item in payload.get("accepted_component_refs") or ()
                        ],
                    }
                )
            return controller.invoke(
                role=role,
                prompt=prompt,
                system_prompt=system_prompt,
                provider=str(kwargs.get("provider") or authorization.provider),
                model=str(kwargs.get("model") or authorization.model),
            )

    with tempfile.TemporaryDirectory(prefix="analystos-evaluation-") as tmp:
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            corpus,
            "SearchOSAnalystOSHarness",
            EvaluationHarness,
        )
        try:
            execution = corpus.run_offline_integration_scenario(
                scenario,
                tmp_path=Path(tmp),
                monkeypatch=monkeypatch,
            )
            packet = deepcopy(execution.observation_packet)
        finally:
            monkeypatch.undo()
    expected = expectation_for(scenario_id)
    reached = packet.get("status") == expected.expected_status
    if expected.expected_status == BOUNDED_LIMIT:
        terminal = "bounded_limit_before_second_generation"
    elif expected.honest_nonclosure:
        terminal = "honest_nonclosure"
    else:
        terminal = expected.expected_terminal_posture
    refs = []
    for owner in ("component_analyst", "cross_component_analyst"):
        refs.extend(deepcopy(packet.get(owner, {}).get("output_refs") or []))
    return ScenarioRunResult(
        scenario_id=scenario_id,
        ordinary_downstream_terminal_posture=terminal,
        operating_system_transition_reached=reached,
        safe_output_artifact_refs=tuple(refs),
        deterministic_fixture_call_counts={
            "fictional_search_operations": len(execution.harness.search_calls),
            "fictional_read_operations": len(execution.harness.read_transport_calls),
        },
        execution=execution,
    )


def _aggregate_scores(
    observations: Sequence[BoundaryCallObservation],
) -> tuple[ScoreCard, ScoreCard]:
    structural: dict[str, bool | None] = {}
    semantic: dict[str, bool | None] = {}
    for item in observations:
        structural[f"{item.call_id}:packet_complete"] = item.packet_complete
        structural[f"{item.call_id}:parser_consumable"] = item.parser_consumable
        structural[f"{item.call_id}:proposal_only"] = item.proposal_only
        structural[f"{item.call_id}:authority_boundary"] = item.authority_boundary_respected
        semantic[f"{item.call_id}:semantic_origination"] = {
            "met": True,
            "wrong": False,
            "ambiguous": None,
        }.get(item.semantic_status)
    return ScoreCard.from_checks(structural), ScoreCard.from_checks(semantic)


def _classification_from_observations(
    observations: Sequence[BoundaryCallObservation],
    *,
    operating_system_transition_reached: bool,
    runner_failed: bool,
    paired_probe: PairedProbeEvidence | None = None,
) -> str:
    if not observations:
        return "PACKET" if runner_failed else "NOT_RUN"
    if any(not item.packet_complete for item in observations):
        return "PACKET"
    if any(not item.authority_boundary_respected for item in observations):
        return classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=True,
                semantic_status="wrong",
                operating_system_transition_reached=False,
                paired_probe=paired_probe,
            )
        )
    parser_failures = [item for item in observations if not item.parser_consumable]
    if parser_failures:
        semantic_statuses = {item.semantic_status for item in parser_failures}
        return classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=False,
                semantic_status=("met" if semantic_statuses == {"met"} else "ambiguous"),
                operating_system_transition_reached=False,
            )
        )
    if any(item.semantic_status == "ambiguous" for item in observations):
        return "REVIEW_REQUIRED"
    if any(item.semantic_status == "wrong" for item in observations):
        return classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=True,
                semantic_status="wrong",
                operating_system_transition_reached=False,
                paired_probe=paired_probe,
            )
        )
    return classify_result(
        ClassificationEvidence(
            call_ran=True,
            packet_complete=True,
            parser_consumable=True,
            semantic_status="met",
            operating_system_transition_reached=(operating_system_transition_reached and not runner_failed),
        )
    )


def _write_packet(path: str, packet: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    reject_forbidden_packet_material(packet)
    target.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_evaluation(
    request: EvaluationRequest,
    *,
    repository_sha: str | None = None,
    authorization: LiveAuthorization | None = None,
    transport_factory: Callable[[LiveAuthorization], EvaluationTransport] | None = None,
    scenario_runner: Callable[..., ScenarioRunResult] | None = None,
    paired_probe: PairedProbeEvidence | None = None,
) -> dict[str, Any]:
    """Plan or execute one exact evaluation without implicit authority."""

    resolved = resolve_request(request)
    exact_sha = repository_sha or current_repository_sha()
    if resolved.execution_mode == "plan_only":
        packet = build_planned_packet(resolved, repository_sha=exact_sha)
        if resolved.output_packet_path:
            _write_packet(resolved.output_packet_path, packet)
        return packet

    manifest = validate_live_authorization(
        resolved,
        authorization,
        repository_sha=exact_sha,
    )
    if transport_factory is None:
        raise EvaluationConfigurationError("execute requires an injected transport factory")
    assert authorization is not None
    # This is the first point at which construction is permitted.
    transport = transport_factory(authorization)
    if not callable(transport):
        raise EvaluationConfigurationError("transport factory did not return a callable transport")
    runner = scenario_runner or _run_ordinary_fixture_scenario
    scenario_packets = []
    budget_ledger = ExecutionBudgetLedger(
        credentials_accessed=getattr(
            transport,
            "credentials_accessed",
            None,
        )
    )
    deterministic_fixture_counts: Counter[str] = Counter()
    all_observations: list[BoundaryCallObservation] = []
    all_output_refs: list[Mapping[str, Any]] = []
    skipped: dict[str, str] = {}
    for scenario_id in resolved.scenario_ids:
        controller = BoundaryInjectionController(
            manifest=manifest,
            scenario_id=scenario_id,
            authorization=authorization,
            transport=transport,
            budget_ledger=budget_ledger,
        )
        runner_failed = False
        error_type: str | None = None
        try:
            result = runner(
                scenario_id=scenario_id,
                controller=controller,
            )
        except Exception as exc:
            runner_failed = True
            error_type = type(exc).__name__
            result = ScenarioRunResult(
                scenario_id=scenario_id,
                ordinary_downstream_terminal_posture="fail_closed_before_terminal",
                operating_system_transition_reached=False,
            )
        observations = tuple(controller.observations)
        observed_ids = {item.call_id for item in observations}
        for call in manifest.calls:
            if call.scenario_id == scenario_id and call.call_id not in observed_ids:
                skipped[call.call_id] = (
                    "conditionally skipped after fail-closed result"
                    if runner_failed
                    else "ordinary deterministic path did not require the conditional call"
                )
        structural_score, semantic_score = _aggregate_scores(observations)
        classification = _classification_from_observations(
            observations,
            operating_system_transition_reached=(result.operating_system_transition_reached),
            runner_failed=runner_failed,
            paired_probe=paired_probe,
        )
        scenario_packet = {
            "scenario_id": scenario_id,
            "scryraven_mode": SCENARIO_BY_ID[scenario_id].mode,
            "expected_semantic_projection": _expected_semantic_projection(scenario_id),
            "observed_safe_semantic_projection": [item.to_packet() for item in observations],
            "structural_score": structural_score.to_packet(),
            "semantic_score": semantic_score.to_packet(),
            "primary_failure_attribution": classification,
            "ordinary_downstream_terminal_posture": (result.ordinary_downstream_terminal_posture),
            "safe_output_artifact_refs": [deepcopy(dict(item)) for item in result.safe_output_artifact_refs],
            "runner_failure_type": error_type,
        }
        scenario_packets.append(scenario_packet)
        all_observations.extend(observations)
        all_output_refs.extend(result.safe_output_artifact_refs)
        deterministic_fixture_counts.update(result.deterministic_fixture_call_counts)

    if budget_ledger.physical_calls > authorization.maximum_model_calls:
        raise EvaluationTransportError("observed model calls exceeded the exact cap")
    classifications = {item["primary_failure_attribution"] for item in scenario_packets}
    if classifications == {"PASS"}:
        primary = "PASS"
    elif "REVIEW_REQUIRED" in classifications:
        primary = "REVIEW_REQUIRED"
    else:
        priority = (
            "PACKET",
            "PARSER_CONTRACT",
            "PROMPT",
            "MODEL",
            "OPERATING_SYSTEM",
            "NOT_RUN",
        )
        primary = next(
            (item for item in priority if item in classifications),
            "REVIEW_REQUIRED",
        )
    structural_score, semantic_score = _aggregate_scores(all_observations)
    packet = {
        "schema_version": RESULT_PACKET_SCHEMA_VERSION,
        "evaluation_id": _digest(
            {
                "repository_sha": exact_sha,
                "license_reference": authorization.reference,
                "evaluation_pass": resolved.evaluation_pass,
                "scenario_ids": resolved.scenario_ids,
                "roles": resolved.selected_model_roles,
            }
        ),
        "repository_sha": exact_sha,
        "scenario_ids": list(resolved.scenario_ids),
        "scryraven_modes": {scenario_id: SCENARIO_BY_ID[scenario_id].mode for scenario_id in resolved.scenario_ids},
        "evaluation_pass": resolved.evaluation_pass,
        "execution_mode": resolved.execution_mode,
        "selected_provider": authorization.provider,
        "selected_model": authorization.model,
        "selected_model_roles": list(resolved.selected_model_roles),
        "exact_role_call_manifest": manifest.to_packet(),
        "safe_input_packet_digests": [
            {
                "call_id": item.call_id,
                "digest": item.safe_input_packet_digest,
            }
            for item in all_observations
        ],
        "safe_output_artifact_refs": [deepcopy(dict(item)) for item in all_output_refs],
        "structural_score": structural_score.to_packet(),
        "semantic_score": semantic_score.to_packet(),
        "primary_failure_attribution": primary,
        "expected_semantic_projection": [_expected_semantic_projection(item) for item in resolved.scenario_ids],
        "observed_safe_semantic_projection": scenario_packets,
        "ordinary_downstream_terminal_posture": {
            item["scenario_id"]: item["ordinary_downstream_terminal_posture"] for item in scenario_packets
        },
        "call_counts": {
            "model_calls": budget_ledger.physical_calls,
            "scryraven_runs": len(resolved.scenario_ids),
            "provider_calls": budget_ledger.physical_calls,
            "search_calls": 0,
            "retrieval_calls": 0,
            "read_calls": 0,
            "navigation_calls": 0,
            "map_calls": 0,
            "crawl_calls": 0,
            "external_calls": budget_ledger.physical_calls,
            "fictional_search_operations": deterministic_fixture_counts.get(
                "fictional_search_operations",
                0,
            ),
            "fictional_read_operations": deterministic_fixture_counts.get(
                "fictional_read_operations",
                0,
            ),
        },
        "retry_counts": {"total": budget_ledger.retries},
        "token_counts": {
            "input": budget_ledger.input_tokens,
            "output": budget_ledger.output_tokens,
        },
        "observed_cost": budget_ledger.cost,
        "skipped_call_reasons": skipped,
        "redaction_posture": {
            "sanitized_only": True,
            "raw_retention_posture": authorization.raw_retention_posture,
            "raw_prompts_retained": False,
            "raw_model_responses_retained": False,
            "raw_provider_payloads_retained": False,
            "secrets_retained": False,
            "full_traces_retained": False,
            "private_logs_retained": False,
            "database_rows_retained": False,
            "reasoning_traces_retained": False,
        },
        "live_license_reference": authorization.reference,
        "transport_created": True,
        "credentials_accessed": budget_ledger.credentials_accessed,
        "symbolic_cost_formula": (
            "maximum_physical_calls * "
            "((maximum_input_tokens * selected_input_token_price) + "
            "(maximum_output_tokens * selected_output_token_price))"
        ),
    }
    reject_forbidden_packet_material(packet)
    assert resolved.output_packet_path is not None
    _write_packet(resolved.output_packet_path, packet)
    return packet


def sample_classification_packet(classification: str) -> dict[str, Any]:
    """Return one committed-fixture-safe sample result projection."""

    if classification not in CLASSIFICATIONS:
        raise EvaluationConfigurationError("unknown result classification")
    packet = {
        "schema_version": RESULT_PACKET_SCHEMA_VERSION,
        "evaluation_id": f"synthetic-sample-{classification.casefold()}",
        "repository_sha": "synthetic-repository-sha",
        "scenario_ids": ["case_03_pure_depth_two"],
        "scryraven_modes": {"case_03_pure_depth_two": "Deep"},
        "evaluation_pass": "analyst_only",
        "execution_mode": "execute",
        "selected_provider": "synthetic-provider",
        "selected_model": "synthetic-model",
        "selected_model_roles": [ROLE_CROSS_COMPONENT_ANALYST],
        "exact_role_call_manifest": {"synthetic_fixture_only": True},
        "safe_input_packet_digests": [{"call_id": "synthetic", "digest": "0" * 64}],
        "safe_output_artifact_refs": [],
        "structural_score": {"status": "PASS"},
        "semantic_score": {
            "status": ("PASS" if classification in {"PASS", "PARSER_CONTRACT", "OPERATING_SYSTEM"} else "FAIL")
        },
        "primary_failure_attribution": classification,
        "expected_semantic_projection": {"dependency_shape": ["active_certificate", "registry_designation"]},
        "observed_safe_semantic_projection": {
            "classification": classification,
            "synthetic_fixture_only": True,
        },
        "ordinary_downstream_terminal_posture": (
            "depth_two_inferred_closure" if classification == "PASS" else "synthetic_not_reached"
        ),
        "call_counts": {"model_calls": 0 if classification == "NOT_RUN" else 1},
        "retry_counts": {"total": 0},
        "skipped_call_reasons": ({"synthetic": "execution_mode=plan_only"} if classification == "NOT_RUN" else {}),
        "redaction_posture": {
            "sanitized_only": True,
            "raw_prompts_retained": False,
            "raw_model_responses_retained": False,
            "raw_provider_payloads_retained": False,
        },
        "live_license_reference": "synthetic-license",
    }
    reject_forbidden_packet_material(packet)
    return packet


def proposed_live_addendum_template(
    *,
    repository_sha: str,
    output_packet_path: str,
) -> dict[str, Any]:
    """Return a ready-to-approve template without granting or using authority."""

    return {
        "schema_version": LIVE_ADDENDUM_SCHEMA_VERSION,
        "reference": "<EXACT-LIVE-ADDENDUM-REFERENCE>",
        "repository_sha": repository_sha,
        "provider": "<EXACT-PROVIDER>",
        "model": "<EXACT-MODEL>",
        "allowed_evaluation_pass": "<planner_only|analyst_only|combined>",
        "allowed_model_roles": ["<EXACT-ROLE>"],
        "allowed_scenario_ids": ["<EXACT-SCENARIO-ID>"],
        "maximum_model_calls": "<EXACT-COMPUTED-CAP>",
        "maximum_scryraven_runs": "<EXACT-RUN-CAP>",
        "retry_cap": 0,
        "maximum_input_tokens": "<EXACT-INPUT-TOKEN-CAP>",
        "maximum_output_tokens": "<EXACT-OUTPUT-TOKEN-CAP>",
        "cost_ceiling": "<EXACT-COST-CEILING>",
        "operator_command": (
            "python scripts/evaluation/"
            "run_analystos_model_origination_evaluation.py "
            "--execution-mode execute <EXACT-SELECTORS>"
        ),
        "output_packet_path": output_packet_path,
        "raw_retention_posture": "sanitized_only",
        "decision": "<EXACT-DECISION-THE-RUN-WILL-MAKE>",
        "stop_condition": ("<STOP-IMMEDIATELY-WHEN-CALL-RUN-TOKEN-OR-COST-BUDGET-IS-EXHAUSTED>"),
    }


def _load_transport_factory(spec: str) -> Callable[[LiveAuthorization], EvaluationTransport]:
    module_name, separator, attribute = spec.partition(":")
    if not separator or not module_name or not attribute:
        raise EvaluationConfigurationError("transport factory must use module.path:callable syntax")
    module = importlib.import_module(module_name)
    factory = getattr(module, attribute, None)
    if not callable(factory):
        raise EvaluationConfigurationError("transport factory target is not callable")
    return factory


def _lazy_transport_factory(
    spec: str,
) -> Callable[[LiveAuthorization], EvaluationTransport]:
    """Defer even plugin import until after exact license validation."""

    def construct(
        authorization: LiveAuthorization,
    ) -> EvaluationTransport:
        return _load_transport_factory(spec)(authorization)

    return construct


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or execute the fail-closed AnalystOS origination evaluator.")
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
    args = _parse_args(argv)
    request = EvaluationRequest(
        evaluation_pass=args.evaluation_pass,
        execution_mode=args.execution_mode,
        scenario_ids=tuple(args.scenario_ids or ()),
        selected_model_roles=tuple(args.selected_model_roles or ()),
        output_packet_path=args.output_packet_path,
    )
    authorization = None
    transport_factory = None
    if args.execution_mode == "execute":
        if not args.live_addendum:
            raise EvaluationConfigurationError("execute requires --live-addendum")
        if not args.transport_factory:
            raise EvaluationConfigurationError("execute requires --transport-factory")
        addendum_value = json.loads(Path(args.live_addendum).read_text(encoding="utf-8"))
        if not isinstance(addendum_value, Mapping):
            raise EvaluationConfigurationError("live addendum must contain one JSON object")
        authorization = LiveAuthorization.from_mapping(addendum_value)
        transport_factory = _lazy_transport_factory(args.transport_factory)
    elif args.live_addendum or args.transport_factory:
        raise EvaluationConfigurationError("plan_only rejects execute-only live addendum and transport options")
    packet = run_evaluation(
        request,
        authorization=authorization,
        transport_factory=transport_factory,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvaluationConfigurationError, EvaluationTransportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


__all__ = [
    "CLASSIFICATIONS",
    "EVALUATION_PASSES",
    "EXECUTION_MODES",
    "LIVE_ADDENDUM_SCHEMA_VERSION",
    "BoundaryCallObservation",
    "BoundaryInjectionController",
    "CallManifest",
    "ClassificationEvidence",
    "EvaluationConfigurationError",
    "EvaluationRequest",
    "EvaluationTransportResponse",
    "EvaluationTransportError",
    "ExecutionBudgetLedger",
    "LiveAuthorization",
    "PairedProbeEvidence",
    "PlannedCall",
    "ScenarioRunResult",
    "ScoreCard",
    "build_call_manifest",
    "build_planned_packet",
    "classify_result",
    "paired_probe_demonstrates_prompt_causality",
    "project_and_score_role_output",
    "proposed_live_addendum_template",
    "reject_forbidden_packet_material",
    "resolve_request",
    "run_evaluation",
    "sample_classification_packet",
    "validate_live_authorization",
]
