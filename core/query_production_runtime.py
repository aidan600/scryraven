"""Converged SearchOS initial strategy and QueryPlan admission boundaries.

The ordinary chain is SearchPlanner -> initial AnswerContract acceptance ->
optional Scout/revision -> contract-bound SearchWorkPlan -> QueryPlan.  This
module has no live planner/recon/provider fallback and does not own provider
selection, READ, evidence, citation, or post-result follow-up dispatch.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any

from core.anchor_resolution import build_shadow_anchor_packet
from core.initial_query_allocation_policy import (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
    InitialQueryAllocationPolicy,
)
from core.initial_query_strategy_failure import (
    InitialQueryStrategyFailureError,
    invoke_run_kernel_initial_planning,
    scout_disambiguation_runtime_failure,
    search_planner_revision_runtime_failure,
)
from core.nutrition_lookup import detect_nutrition_lookup_telemetry
from core.query_plan import (
    QUERY_PLAN_TRACE_KEY,
    InitialQueryAdmissionResult,
    QueryPlanRole,
)
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.router_query_preparation_contract import (
    RouterQueryPreparationState,
    with_router_query_runtime_posture,
)
from core.run_authority_contract import contract_query_hints_from_projection
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)
from core.scout_disambiguation_runtime import (
    ScoutDisambiguationAdapter,
    ScoutDisambiguationInput,
    ScoutDisambiguationRuntimeError,
    execute_scout_disambiguation_action,
    planner_ref_from_search_planner_state,
)
from core.scout_disambiguation_runtime import (
    contract_ref_from_contract as scout_contract_ref_from_contract,
)
from core.search_planner_revision_runtime import (
    SearchPlannerRevisionAdapter,
    SearchPlannerRevisionInput,
    SearchPlannerRevisionRuntimeError,
    execute_search_planner_revision_action,
    revision_ref_from_revision_state,
    scout_ref_from_scout_report_state,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerAdapter,
    SearchPlannerInput,
    execute_search_planner_action,
    initial_query_strategies_from_planner_state,
    normalize_provider_neutral_query_strategy_candidate,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)
from core.search_work_plan_construction import (
    observe_contract_bound_search_work_plan_construction,
)
from core.search_work_provider_job_execution import (
    build_provider_job_execution_handoff,
)


@dataclass(frozen=True, slots=True)
class QueryProductionAdmissionInputs:
    """Reduced query-production projection consumed by QueryPlan admission."""

    candidate_queries: list[str]
    candidate_strategies: list[dict[str, Any]]
    candidate_source: str
    effective_route_posture: dict[str, Any]
    contract_source_requirement_hints: list[dict[str, Any]]
    initial_query_allocation_policy: InitialQueryAllocationPolicy

    @property
    def query_type(self) -> str:
        return str(self.effective_route_posture["query_type"])

    @property
    def max_queries(self) -> int:
        return int(self.effective_route_posture["max_queries"])


@dataclass(frozen=True, slots=True)
class QueryProductionResult:
    """Query-production output plus the kernel observation to reduce."""

    candidate_queries: list[str]
    candidate_source: str
    effective_route_posture: dict[str, Any]
    include_domains: list[str]
    anchor_packet_telemetry: dict[str, Any]
    nutrition_lookup_telemetry: dict[str, Any]
    waste_flags: list[str]
    recon_fired: bool
    recon_confidence: str | None
    canonical_subject_resolved: str | None
    recon_seconds: float
    researcher_fallback_status: str
    empty_entity_flag: bool
    contract_source_requirement_hints: list[dict[str, Any]]
    candidate_strategies: list[dict[str, Any]]
    initial_query_allocation_policy: InitialQueryAllocationPolicy
    recon_summary: list[dict[str, Any]]
    observation: Observation

    @property
    def intent(self) -> str:
        return str(self.effective_route_posture["intent"])

    @property
    def report_type(self) -> str:
        return str(self.effective_route_posture["report_type"])

    @property
    def image_mode(self) -> str:
        return str(self.effective_route_posture["image_mode"])

    @property
    def core_topic(self) -> str:
        return str(self.effective_route_posture["core_topic"])

    @property
    def query_type(self) -> str:
        return str(self.effective_route_posture["query_type"])

    @property
    def primary_entity(self) -> str:
        return str(self.effective_route_posture["primary_entity"])

    @property
    def entities_list(self) -> list[str]:
        return list(self.effective_route_posture["entities_list"])

    @property
    def is_academic(self) -> bool:
        return bool(self.effective_route_posture["is_academic"])

    @property
    def routing_override_applied(self) -> bool:
        return bool(self.effective_route_posture["routing_override_applied"])

    @property
    def routing_override_reason(self) -> str | None:
        reason = self.effective_route_posture["routing_override_reason"]
        return None if reason is None else str(reason)

    @property
    def complexity(self) -> str:
        return str(self.effective_route_posture["complexity"])

    @property
    def max_queries(self) -> int:
        return int(self.effective_route_posture["max_queries"])

    @property
    def results_per_query(self) -> int:
        return int(self.effective_route_posture["results_per_query"])

    @property
    def search_depth(self) -> str:
        return str(self.effective_route_posture["search_depth"])

    @property
    def top_chunks(self) -> int:
        return int(self.effective_route_posture["top_chunks"])

    @property
    def max_iterations(self) -> int:
        return int(self.effective_route_posture["max_iterations"])


class QueryStrategyConvergenceFailureCode(str, Enum):
    """Closed owner-authored safe code for ordinary initial convergence failures."""

    REQUIRED_SCOUT_ADAPTER_UNAVAILABLE = "required_scout_adapter_unavailable"
    REVISION_ADAPTER_REQUIRED_WITH_SCOUT = "revision_adapter_required_with_scout"
    RECON_COMPONENT_BINDING_MISSING = "recon_component_binding_missing"
    RECON_DIMENSION_DUPLICATE = "recon_dimension_duplicate"
    RECON_STRATEGY_MALFORMED = "recon_strategy_malformed"
    RECON_CEILING_EXCEEDED = "recon_ceiling_exceeded"
    RECON_COMPONENT_NOT_IN_CONTRACT = "recon_component_not_in_contract"
    RECON_SEMANTIC_SLOT_BINDING_MISSING = "recon_semantic_slot_binding_missing"
    RECON_CANDIDATE_MISSING = "recon_candidate_missing"
    REQUIRED_SCOUT_EXECUTION_EMPTY = "required_scout_execution_empty"
    REVISION_AMENDMENT_COUNT_INVALID = "revision_amendment_count_invalid"
    REVISION_AMENDMENT_IDENTITY_MISSING = "revision_amendment_identity_missing"
    MULTIPLE_CONTRACTUAL_REVISIONS_UNSUPPORTED = (
        "multiple_contractual_revisions_unsupported"
    )
    BASE_STRATEGY_STALE = "base_strategy_stale"
    REVISION_CONTRACTUAL_EFFECT_PENDING = "revision_contractual_effect_pending"
    REVISION_COMPONENT_ABSENT = "revision_component_absent"
    REVISION_COMPONENT_IDENTITY_STALE = "revision_component_identity_stale"
    REVISION_SOURCE_OBLIGATION_UNACCEPTED = "revision_source_obligation_unaccepted"
    ANSWER_CONTRACT_BINDING_MISSING = "answer_contract_binding_missing"
    SEARCH_WORK_PLAN_MISSING = "search_work_plan_missing"
    SEARCH_WORK_PLAN_CONTRACT_STALE = "search_work_plan_contract_stale"
    SEARCH_WORK_PLAN_IDENTITY_MISSING = "search_work_plan_identity_missing"
    ALLOCATION_POLICY_REQUIRED = "allocation_policy_required"
    QUESTION_MEANING_RECORD_MISSING = "question_meaning_record_missing"
    INITIAL_STRATEGIES_EMPTY = "initial_strategies_empty"
    INITIAL_STRATEGY_TEXT_UNBOUNDED = "initial_strategy_text_unbounded"


class QueryStrategyConvergenceError(ValueError):
    """Raised before dispatch when the required initial chain cannot converge."""

    SAFE_FAILURE_ORIGIN = "query_strategy_convergence"
    __slots__ = ("_failure_code",)

    def __init__(
        self,
        message: str,
        *,
        failure_code: QueryStrategyConvergenceFailureCode,
    ) -> None:
        if not isinstance(failure_code, QueryStrategyConvergenceFailureCode):
            raise TypeError("failure_code must be a QueryStrategyConvergenceFailureCode")
        super().__init__(message)
        self._failure_code = failure_code

    @property
    def failure_code(self) -> QueryStrategyConvergenceFailureCode:
        return self._failure_code


@dataclass(frozen=True, slots=True)
class InitialQueryStrategyConvergenceResult:
    query_production_action: AuthorizedAction
    query_production_result: QueryProductionResult
    search_work_plan: Mapping[str, Any]
    recon_summary: tuple[Mapping[str, Any], ...]
    revision_projections: tuple[Mapping[str, Any], ...]


def _recon_unavailable_summary(
    strategies: Sequence[Mapping[str, Any]],
    *,
    policy: InitialQueryAllocationPolicy,
) -> list[dict[str, Any]]:
    """Record optional recon absence and fail closed on required identity work."""

    summaries: list[dict[str, Any]] = []
    work = _recon_work_by_component(strategies, policy=policy)
    for component_id, component_work in work.items():
        required = bool(component_work["required_for_truthful_targeting"])
        if required:
            raise QueryStrategyConvergenceError(
                f"component {component_id} requires Scout identity resolution "
                "before truthful query targeting; no Scout adapter was composed",
                failure_code=(
                    QueryStrategyConvergenceFailureCode.REQUIRED_SCOUT_ADAPTER_UNAVAILABLE
                ),
            )
        summaries.append(
            {
                "component_id": component_id,
                "posture": component_work["posture"],
                "status": "optional_unavailable_primary_strategy_retained",
                "unresolved_dimension_ids": list(component_work["unresolved_dimension_ids"]),
                "candidate_count": len(component_work["candidate_queries"]),
                "per_affected_component_ceiling": (policy.recon_candidate_ceiling_per_affected_component),
                "required_for_truthful_targeting": False,
                "evidence_admitted": False,
                "source_obligation_satisfied": False,
                "citation_eligible": False,
            }
        )
    return summaries


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _recon_work_by_component(
    strategies: Sequence[Mapping[str, Any]],
    *,
    policy: InitialQueryAllocationPolicy,
) -> dict[str, dict[str, Any]]:
    work: dict[str, dict[str, Any]] = {}
    for strategy in strategies:
        recon = strategy.get("recon_requirement")
        recon = dict(recon) if isinstance(recon, Mapping) else {}
        posture = str(recon.get("posture") or strategy.get("recon_posture") or "not_needed").strip()
        if posture == "not_needed":
            continue
        component_id = str(strategy.get("component_id") or "").strip()
        if not component_id:
            raise QueryStrategyConvergenceError(
                "recon requirement is missing its accepted component binding",
                failure_code=(
                    QueryStrategyConvergenceFailureCode.RECON_COMPONENT_BINDING_MISSING
                ),
            )
        component_work = work.setdefault(
            component_id,
            {
                "component_id": component_id,
                "posture": posture,
                "required_for_truthful_targeting": False,
                "unresolved_dimension_ids": [],
                "candidate_queries": [],
            },
        )
        if posture == "required":
            component_work["posture"] = "required"
        component_work["required_for_truthful_targeting"] = bool(
            component_work["required_for_truthful_targeting"]
            or posture == "required"
            or recon.get("required_for_truthful_targeting")
            or strategy.get("recon_required_for_truthful_targeting")
        )
        for dimension_id in (
            recon.get("unresolved_dimension_ids") or strategy.get("recon_unresolved_dimension_ids") or ()
        ):
            clean_id = str(dimension_id or "").strip()
            if clean_id and clean_id not in component_work["unresolved_dimension_ids"]:
                component_work["unresolved_dimension_ids"].append(clean_id)
        known_candidate_dimensions = {
            str(item.get("dimension_id") or "").strip() for item in component_work["candidate_queries"]
        }
        for raw_candidate in recon.get("candidate_queries") or ():
            if not isinstance(raw_candidate, Mapping):
                continue
            candidate = dict(raw_candidate)
            dimension_id = str(candidate.get("dimension_id") or "").strip()
            if not dimension_id or dimension_id in known_candidate_dimensions:
                raise QueryStrategyConvergenceError(
                    f"component {component_id} recon candidates must address distinct unresolved dimensions",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.RECON_DIMENSION_DUPLICATE
                    ),
                )
            known_candidate_dimensions.add(dimension_id)
            if dimension_id not in component_work["unresolved_dimension_ids"]:
                component_work["unresolved_dimension_ids"].append(dimension_id)
            component_work["candidate_queries"].append(candidate)
        query_text_by_dimension = (
            dict(strategy.get("recon_candidate_queries_by_dimension") or {})
            if isinstance(strategy.get("recon_candidate_queries_by_dimension"), Mapping)
            else {}
        )
        query_kind_by_dimension = (
            dict(strategy.get("recon_query_kinds_by_dimension") or {})
            if isinstance(strategy.get("recon_query_kinds_by_dimension"), Mapping)
            else {}
        )
        for dimension_id, query_text in query_text_by_dimension.items():
            clean_dimension_id = str(dimension_id or "").strip()
            clean_query_text = str(query_text or "").strip()
            if not clean_dimension_id or not clean_query_text:
                raise QueryStrategyConvergenceError(
                    f"component {component_id} has malformed flattened recon strategy",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.RECON_STRATEGY_MALFORMED
                    ),
                )
            if clean_dimension_id in known_candidate_dimensions:
                continue
            known_candidate_dimensions.add(clean_dimension_id)
            if clean_dimension_id not in component_work["unresolved_dimension_ids"]:
                component_work["unresolved_dimension_ids"].append(clean_dimension_id)
            component_work["candidate_queries"].append(
                {
                    "dimension_id": clean_dimension_id,
                    "candidate_query_text": clean_query_text,
                    "query_kind": str(
                        query_kind_by_dimension.get(clean_dimension_id) or "disambiguation_probe"
                    ).strip(),
                }
            )

    for component_id, component_work in work.items():
        ceiling = policy.recon_candidate_ceiling_per_affected_component
        if (
            len(component_work["candidate_queries"]) > ceiling
            or len(component_work["unresolved_dimension_ids"]) > ceiling
        ):
            raise QueryStrategyConvergenceError(
                f"component {component_id} exceeds the policy-owned per-affected-component recon ceiling",
                failure_code=QueryStrategyConvergenceFailureCode.RECON_CEILING_EXCEEDED,
            )
    return work


def _dimension_kind(dimension_id: str) -> str:
    lowered = dimension_id.casefold()
    if "jurisdiction" in lowered:
        return "jurisdiction"
    if "alias" in lowered or "rename" in lowered:
        return "rename_alias"
    if "current" in lowered or "date" in lowered or "time" in lowered:
        return "time_version_currentness"
    if "official" in lowered or "domain" in lowered or "publication" in lowered:
        return "official_target_direction"
    if "entity" in lowered or "identity" in lowered:
        return "entity_identity"
    return "unknown_or_other"


def _scout_query_kind(dimension_id: str) -> str:
    kind = _dimension_kind(dimension_id)
    return {
        "jurisdiction": "jurisdiction_probe",
        "rename_alias": "alias_probe",
        "time_version_currentness": "recent_current",
        "official_target_direction": "official_domain_probe",
        "entity_identity": "all_time",
    }.get(kind, "unknown_or_other")


def _component_and_slot_refs(
    *,
    planner_state: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    component_id: str,
) -> tuple[dict[str, Any], list[str]]:
    accepted_component = next(
        (
            dict(item)
            for item in accepted_contract.get("accepted_answer_component_refs") or ()
            if isinstance(item, Mapping) and str(item.get("component_id") or "").strip() == component_id
        ),
        {},
    )
    if not accepted_component:
        raise QueryStrategyConvergenceError(
            f"recon component {component_id} is not in the accepted contract",
            failure_code=(
                QueryStrategyConvergenceFailureCode.RECON_COMPONENT_NOT_IN_CONTRACT
            ),
        )
    qmr = (
        dict(planner_state.get("question_meaning_record") or {})
        if isinstance(planner_state.get("question_meaning_record"), Mapping)
        else {}
    )
    proposed_component = next(
        (
            dict(item)
            for item in qmr.get("answer_components") or ()
            if isinstance(item, Mapping) and str(item.get("component_id") or "").strip() == component_id
        ),
        {},
    )
    slot_ids = [str(item).strip() for item in proposed_component.get("semantic_slot_ids") or () if str(item).strip()]
    if not slot_ids:
        slot_ids = [
            str(item.get("slot_id") or "").strip()
            for item in qmr.get("semantic_slots") or ()
            if isinstance(item, Mapping) and str(item.get("slot_id") or "").strip()
        ][:1]
    if not slot_ids:
        raise QueryStrategyConvergenceError(
            f"recon component {component_id} has no semantic-slot binding",
            failure_code=(
                QueryStrategyConvergenceFailureCode.RECON_SEMANTIC_SLOT_BINDING_MISSING
            ),
        )
    return accepted_component, slot_ids


def _scout_hint_ids(report: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in (
        "scout_result_hints",
        "likely_official_target_hints",
        "currentness_hints",
    ):
        for item in report.get(key) or ():
            if not isinstance(item, Mapping):
                continue
            hint_id = str(item.get("hint_id") or "").strip()
            if hint_id and hint_id not in ids:
                ids.append(hint_id)
    return ids


def _revision_lineage_inputs(revision: Mapping[str, Any]) -> dict[str, Any]:
    planner_ref = dict(revision.get("parent_search_planner_proposal_ref") or {})
    scout_ref = dict(revision.get("parent_scout_disambiguation_report_ref") or {})
    return {
        "search_planner_revision_lineage_required": True,
        "amendment_origin": "search_planner_revision",
        "planner_revision_id": revision.get("revision_id"),
        "parent_search_planner_proposal_id": planner_ref.get("proposal_id"),
        "parent_search_planner_proposal_digest": planner_ref.get("proposal_digest"),
        "parent_question_meaning_record_id": planner_ref.get("question_meaning_record_id"),
        "parent_question_meaning_record_digest": planner_ref.get("question_meaning_record_digest"),
        "parent_scout_disambiguation_report_id": scout_ref.get("report_id"),
        "parent_scout_disambiguation_report_digest": scout_ref.get("report_digest"),
        "component_id": revision.get("component_id"),
        "consumed_ambiguity_dimension_ids": list(revision.get("consumed_ambiguity_dimension_ids") or ()),
        "consumed_scout_hint_ids": list(revision.get("consumed_scout_hint_ids") or ()),
    }


def _admit_and_apply_revision_amendment(
    run_kernel: Any,
    revision: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = [dict(item) for item in revision.get("amendment_candidates") or () if isinstance(item, Mapping)]
    if len(candidates) != 1:
        raise QueryStrategyConvergenceError(
            "ordinary initial convergence supports exactly one monotonic "
            "revision amendment candidate per affected component",
            failure_code=(
                QueryStrategyConvergenceFailureCode.REVISION_AMENDMENT_COUNT_INVALID
            ),
        )
    record = dict(candidates[0].get("contract_amendment_record") or {})
    record_id = str(record.get("amendment_record_id") or "").strip()
    record_digest = str(record.get("record_digest") or "").strip()
    if not record_id or not record_digest:
        raise QueryStrategyConvergenceError(
            "revision amendment candidate is missing record identity",
            failure_code=(
                QueryStrategyConvergenceFailureCode.REVISION_AMENDMENT_IDENTITY_MISSING
            ),
        )
    admission_action = invoke_run_kernel_initial_planning(
        "contract_amendment_admission",
        lambda: run_kernel.authorize_contract_amendment_admission(
            amendment_record_id=record_id,
            amendment_record_digest=record_digest,
            inputs=_revision_lineage_inputs(revision),
        ),
    )
    invoke_run_kernel_initial_planning(
        "contract_amendment_admission",
        lambda: run_kernel.reduce(
            Observation.from_action(
                admission_action,
                observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
                status=RunStageStatus.COMPLETED,
                payload={"contract_amendment_record": record},
            )
        ),
    )
    admission = run_kernel.state.contract_amendment_admission_projection
    application_action = invoke_run_kernel_initial_planning(
        "contract_amendment_application",
        lambda: run_kernel.authorize_contract_amendment_application(
            amendment_record_id=record_id,
            amendment_record_digest=record_digest,
            admission_digest=str(admission.get("admission_digest") or ""),
        ),
    )
    invoke_run_kernel_initial_planning(
        "contract_amendment_application",
        lambda: run_kernel.reduce(
            Observation.from_action(
                application_action,
                observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        ),
    )
    return {
        **dict(revision),
        "revision_effect_class": "contractual_admitted_and_applied",
        "contractual_effect_admitted_and_applied": True,
        "contractual_revision_blocks_planning": False,
        "query_direction_authorized_for_planning": True,
        "answer_contract_mutated": True,
        "amendment_admission_digest": admission.get("admission_digest"),
        "applied_contract_ref": _accepted_contract_ref(
            run_kernel.state.initial_answer_contract,
            run_kernel.state.current_answer_contract,
        ),
    }


def _execute_recon_and_revisions(
    *,
    run_kernel: Any,
    candidate_strategies: Sequence[Mapping[str, Any]],
    policy: InitialQueryAllocationPolicy,
    scout_adapter: ScoutDisambiguationAdapter | None,
    revision_adapter: SearchPlannerRevisionAdapter | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    work = _recon_work_by_component(candidate_strategies, policy=policy)
    if not work:
        return [], []
    if scout_adapter is None:
        return _recon_unavailable_summary(candidate_strategies, policy=policy), []
    if revision_adapter is None:
        raise QueryStrategyConvergenceError(
            "Scout composition requires an explicit SearchPlannerRevision adapter",
            failure_code=(
                QueryStrategyConvergenceFailureCode.REVISION_ADAPTER_REQUIRED_WITH_SCOUT
            ),
        )

    summaries: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    contractual_revision_applied = False
    for component_id, component_work in work.items():
        required = bool(component_work["required_for_truthful_targeting"])
        candidates = list(component_work["candidate_queries"])
        dimensions = list(component_work["unresolved_dimension_ids"])
        if not candidates:
            if required:
                raise QueryStrategyConvergenceError(
                    f"component {component_id} requires recon but has no bounded dimension-specific candidate",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.RECON_CANDIDATE_MISSING
                    ),
                )
            summaries.append(
                {
                    "component_id": component_id,
                    "posture": component_work["posture"],
                    "status": "optional_not_run_no_candidate",
                    "unresolved_dimension_ids": dimensions,
                    "candidate_count": 0,
                    "executed_query_count": 0,
                    "evidence_admitted": False,
                    "source_obligation_satisfied": False,
                    "citation_eligible": False,
                }
            )
            continue

        accepted_contract = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
        accepted_component, slot_ids = _component_and_slot_refs(
            planner_state=run_kernel.state.search_planner_proposal_state,
            accepted_contract=accepted_contract,
            component_id=component_id,
        )
        dimension_records = [
            {
                "dimension_id": dimension_id,
                "dimension_kind": _dimension_kind(dimension_id),
                "summary": f"Resolve {dimension_id} for truthful query targeting.",
                "related_semantic_slot_ids": slot_ids,
                "priority": index,
                "status": "open",
                "materiality": "material" if required else "contextual",
            }
            for index, dimension_id in enumerate(dimensions, start=1)
        ]
        scout_candidates = [
            {
                "query_id": f"scout-query:{component_id}:{index}",
                "safe_query_text": str(candidate.get("candidate_query_text") or "").strip(),
                "query_kind": _scout_query_kind(str(candidate.get("dimension_id") or "")),
                "priority": index,
                "related_dimension_ids": [candidate.get("dimension_id")],
                "not_live": True,
            }
            for index, candidate in enumerate(candidates, start=1)
        ]
        scout_input = ScoutDisambiguationInput(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            parent_search_planner_proposal_ref=(
                planner_ref_from_search_planner_state(run_kernel.state.search_planner_proposal_state)
            ),
            parent_initial_contract_ref=scout_contract_ref_from_contract(
                run_kernel.state.initial_answer_contract,
                source="initial_answer_contract",
            ),
            parent_current_contract_ref=scout_contract_ref_from_contract(
                run_kernel.state.current_answer_contract,
                source="current_answer_contract",
            ),
            component_id=component_id,
            answer_component_ref=accepted_component,
            ambiguity_dimensions=dimension_records,
            query_budget={
                "max_queries_per_component": (policy.recon_candidate_ceiling_per_affected_component),
                "max_dimensions_per_component": (policy.recon_candidate_ceiling_per_affected_component),
                "authorized_query_count": len(scout_candidates),
            },
            candidate_queries=scout_candidates,
            safe_context={
                "adapter_policy": "explicit_response_only",
                "policy_version": policy.policy_version,
                "non_evidence": True,
            },
        )
        scout_action = invoke_run_kernel_initial_planning(
            "scout_disambiguation",
            lambda: run_kernel.authorize_scout_disambiguation(
                component_id=component_id,
                ambiguity_dimension_ids=dimensions,
                max_queries_per_component=(policy.recon_candidate_ceiling_per_affected_component),
                max_dimensions_per_component=(policy.recon_candidate_ceiling_per_affected_component),
                inputs={"allocation_policy_version": policy.policy_version},
            ),
        )
        try:
            scout_result = execute_scout_disambiguation_action(
                action=scout_action,
                scout_input=scout_input,
                adapter=scout_adapter,
            )
        except ScoutDisambiguationRuntimeError as exc:
            raise InitialQueryStrategyFailureError(
                scout_disambiguation_runtime_failure()
            ) from exc
        invoke_run_kernel_initial_planning(
            "scout_disambiguation",
            lambda: run_kernel.reduce(
                Observation.from_action(
                    scout_action,
                    observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
                    status=RunStageStatus.COMPLETED,
                    payload=scout_result.observation_payload,
                )
            ),
        )
        report = dict(run_kernel.state.scout_disambiguation_report_projection)
        executed_count = int(report.get("executed_query_count") or 0)
        if executed_count == 0:
            if required:
                raise QueryStrategyConvergenceError(
                    f"required Scout recon for component {component_id} returned no executed offline response",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.REQUIRED_SCOUT_EXECUTION_EMPTY
                    ),
                )
            summaries.append(
                {
                    "component_id": component_id,
                    "posture": component_work["posture"],
                    "status": "optional_unavailable_primary_strategy_retained",
                    "unresolved_dimension_ids": dimensions,
                    "candidate_count": len(candidates),
                    "executed_query_count": 0,
                    "evidence_admitted": False,
                    "source_obligation_satisfied": False,
                    "citation_eligible": False,
                }
            )
            continue

        hint_ids = _scout_hint_ids(report)
        revision_input = SearchPlannerRevisionInput(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            parent_search_planner_proposal_ref=(
                planner_ref_from_search_planner_state(run_kernel.state.search_planner_proposal_state)
            ),
            parent_scout_disambiguation_report_ref=(
                scout_ref_from_scout_report_state(run_kernel.state.scout_disambiguation_report_state)
            ),
            parent_initial_contract_ref=planner_contract_ref_from_contract(
                run_kernel.state.initial_answer_contract,
                source="initial_answer_contract",
            ),
            parent_current_contract_ref=planner_contract_ref_from_contract(
                run_kernel.state.current_answer_contract,
                source="current_answer_contract",
            ),
            component_id=component_id,
            consumed_ambiguity_dimension_ids=dimensions,
            consumed_scout_hint_ids=hint_ids,
            safe_revision_context={
                "answer_component_ref": accepted_component,
                "parent_question_meaning_record": dict(
                    run_kernel.state.search_planner_proposal_state.get("question_meaning_record") or {}
                ),
                "user_query_ref": dict(run_kernel.state.search_planner_proposal_state.get("user_query_ref") or {}),
                "scout_report_ref": scout_ref_from_scout_report_state(
                    run_kernel.state.scout_disambiguation_report_state
                ),
                "non_evidence": True,
                "allocation_policy_version": policy.policy_version,
            },
        )
        revision_action = invoke_run_kernel_initial_planning(
            "search_planner_revision",
            lambda: run_kernel.authorize_search_planner_revision(
                component_id=component_id,
                consumed_ambiguity_dimension_ids=dimensions,
                consumed_scout_hint_ids=hint_ids,
                inputs={"allocation_policy_version": policy.policy_version},
            ),
        )
        try:
            revision_result = execute_search_planner_revision_action(
                action=revision_action,
                revision_input=revision_input,
                adapter=revision_adapter,
            )
        except SearchPlannerRevisionRuntimeError as exc:
            raise InitialQueryStrategyFailureError(
                search_planner_revision_runtime_failure()
            ) from exc
        invoke_run_kernel_initial_planning(
            "search_planner_revision",
            lambda: run_kernel.reduce(
                Observation.from_action(
                    revision_action,
                    observation_type=ObservationType.SEARCH_PLANNER_REVISED,
                    status=RunStageStatus.COMPLETED,
                    payload=revision_result.observation_payload,
                )
            ),
        )
        revision = dict(run_kernel.state.search_planner_revision_projection)
        if revision.get("amendment_candidates"):
            if contractual_revision_applied:
                raise QueryStrategyConvergenceError(
                    "multiple contractual recon revisions require a later contract-mutation phase",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.MULTIPLE_CONTRACTUAL_REVISIONS_UNSUPPORTED
                    ),
                )
            revision = _admit_and_apply_revision_amendment(run_kernel, revision)
            contractual_revision_applied = True
            status = "contractual_revision_admitted_applied"
        else:
            revision = {
                **revision,
                "revision_effect_class": "query_direction_only_non_contractual",
                "contractual_effect_admitted_and_applied": False,
                "contractual_revision_blocks_planning": False,
                "query_direction_authorized_for_planning": True,
                "answer_contract_mutated": False,
            }
            status = "query_direction_revised"
        revisions.append(revision)
        summaries.append(
            {
                "component_id": component_id,
                "posture": component_work["posture"],
                "status": status,
                "unresolved_dimension_ids": dimensions,
                "candidate_count": len(candidates),
                "executed_query_count": executed_count,
                "consumed_scout_hint_ids": hint_ids,
                "revision_ref": revision_ref_from_revision_state(revision),
                "revision_effect_class": revision.get("revision_effect_class"),
                "evidence_admitted": False,
                "source_obligation_satisfied": False,
                "citation_eligible": False,
            }
        )
    return summaries, revisions


def _strategies_with_authorized_revisions(
    *,
    base_strategies: Sequence[Mapping[str, Any]],
    revision_projections: Sequence[Mapping[str, Any]],
    accepted_contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    accepted_components = {
        str(item.get("component_id") or "").strip(): dict(item)
        for item in accepted_contract.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping) and str(item.get("component_id") or "").strip()
    }
    strategies_by_component: dict[str, list[dict[str, Any]]] = {
        component_id: [] for component_id in accepted_components
    }
    for raw_strategy in base_strategies:
        strategy = dict(raw_strategy)
        component_id = str(strategy.get("component_id") or "").strip()
        accepted = accepted_components.get(component_id)
        if not accepted:
            raise QueryStrategyConvergenceError(
                "base planner strategy became stale against the current contract",
                failure_code=QueryStrategyConvergenceFailureCode.BASE_STRATEGY_STALE,
            )
        strategy["accepted_component_ref"] = {
            "component_id": component_id,
            "component_revision": accepted.get("component_revision"),
            "component_digest": accepted.get("component_digest"),
        }
        strategies_by_component[component_id].append(strategy)

    for raw_revision in revision_projections:
        revision = dict(raw_revision)
        updates = [
            dict(item)
            for item in revision.get("component_search_requirement_updates") or ()
            if isinstance(item, Mapping)
        ]
        if not updates:
            continue
        if not (
            revision.get("query_direction_authorized_for_planning") is True
            or revision.get("contractual_effect_admitted_and_applied") is True
        ):
            raise QueryStrategyConvergenceError(
                "revision query direction cannot affect planning before its contractual effect is admitted and applied",
                failure_code=(
                    QueryStrategyConvergenceFailureCode.REVISION_CONTRACTUAL_EFFECT_PENDING
                ),
            )
        component_id = str(revision.get("component_id") or "").strip()
        accepted = accepted_components.get(component_id)
        if not accepted:
            raise QueryStrategyConvergenceError(
                "planner revision references a component absent from current contract",
                failure_code=(
                    QueryStrategyConvergenceFailureCode.REVISION_COMPONENT_ABSENT
                ),
            )
        accepted_source_ids = {
            str(item).strip()
            for item in accepted.get("source_obligation_candidate_ids")
            or accepted.get("source_obligation_candidate_refs")
            or ()
            if str(item).strip()
        }
        revised_strategies: list[dict[str, Any]] = []
        for update in updates:
            update_component_id = str(update.get("component_id") or "").strip()
            requirement_id = str(update.get("requirement_id") or "").strip()
            if update_component_id != component_id or not requirement_id:
                raise QueryStrategyConvergenceError(
                    "revision search requirement has stale component identity",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.REVISION_COMPONENT_IDENTITY_STALE
                    ),
                )
            source_ids = {
                str(item).strip() for item in update.get("source_obligation_candidate_ids") or () if str(item).strip()
            }
            if not source_ids.issubset(accepted_source_ids):
                raise QueryStrategyConvergenceError(
                    "revision search requirement references an unaccepted source obligation",
                    failure_code=(
                        QueryStrategyConvergenceFailureCode.REVISION_SOURCE_OBLIGATION_UNACCEPTED
                    ),
                )
            metadata = dict(update.get("metadata") or {}) if isinstance(update.get("metadata"), Mapping) else {}
            requirement_ref = {
                "requirement_id": requirement_id,
                "component_id": component_id,
                "source_obligation_candidate_ids": sorted(source_ids),
                "requirement_digest": _canonical_digest(
                    {
                        "requirement_id": requirement_id,
                        "component_id": component_id,
                        "source_obligation_candidate_ids": sorted(source_ids),
                        "requirement_summary": update.get("requirement_summary"),
                        "recency_requirement": update.get("recency_requirement"),
                    }
                ),
            }
            for raw_candidate in metadata.get("query_strategy_candidates") or ():
                if not isinstance(raw_candidate, Mapping):
                    continue
                strategy = normalize_provider_neutral_query_strategy_candidate(
                    raw_candidate,
                    component_id=component_id,
                    requirement_id=requirement_id,
                )
                strategy_source_ids = {
                    str(item).strip()
                    for item in strategy.get("source_obligation_candidate_ids") or ()
                    if str(item).strip()
                }
                if not strategy_source_ids.issubset(accepted_source_ids):
                    raise QueryStrategyConvergenceError(
                        "revision query strategy references an unaccepted source obligation",
                        failure_code=(
                            QueryStrategyConvergenceFailureCode.REVISION_SOURCE_OBLIGATION_UNACCEPTED
                        ),
                    )
                revised_strategies.append(
                    {
                        **strategy,
                        "accepted_component_ref": {
                            "component_id": component_id,
                            "component_revision": accepted.get("component_revision"),
                            "component_digest": accepted.get("component_digest"),
                        },
                        "search_requirement_ref": requirement_ref,
                        "parent_search_planner_proposal_ref": dict(
                            revision.get("parent_search_planner_proposal_ref") or {}
                        ),
                        "parent_search_planner_revision_ref": (revision_ref_from_revision_state(revision)),
                        "revision_effect_class": revision.get("revision_effect_class"),
                    }
                )
        if revised_strategies:
            if any(item.get("candidate_kind") == "primary" for item in revised_strategies):
                strategies_by_component[component_id] = revised_strategies
            else:
                strategies_by_component[component_id].extend(revised_strategies)

    return [
        strategy for component_id in accepted_components for strategy in strategies_by_component.get(component_id, ())
    ]


def _clean_query_projection(queries: Sequence[str]) -> list[str]:
    return [" ".join(str(query or "").split())[:300] for query in queries if str(query or "").strip()]


def _complexity_for_strategy(strategy: str) -> str:
    if strategy == "Fast":
        return "low"
    if strategy == "Balanced":
        return "medium"
    return "high"


def _budget_for_complexity(complexity: str) -> dict[str, int | str]:
    if complexity == "high":
        return {
            "max_queries": 3,
            "results_per_query": 8,
            "search_depth": "advanced",
            "top_chunks": 40,
            "max_iterations": 3,
        }
    if complexity == "medium":
        return {
            "max_queries": 2,
            "results_per_query": 6,
            "search_depth": "basic",
            "top_chunks": 20,
            "max_iterations": 2,
        }
    return {
        "max_queries": 2,
        "results_per_query": 5,
        "search_depth": "basic",
        "top_chunks": 8,
        "max_iterations": 1,
    }


def _effective_route_posture(
    *,
    intent: str,
    report_type: str,
    image_mode: str,
    core_topic: str,
    primary_entity: str,
    entities_list: Sequence[str],
    is_academic: bool,
    query_type: str,
    routing_override_applied: bool,
    routing_override_reason: str | None,
    focus_academic: bool,
    force_intent_news: bool,
    complexity: str,
    max_queries: int,
    results_per_query: int,
    search_depth: str,
    top_chunks: int,
    max_iterations: int,
    run_contract_ref: Mapping[str, Any] | None = None,
    contract_source_requirement_hints: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "report_type": report_type,
        "query_type": query_type,
        "image_mode": image_mode,
        "core_topic": core_topic,
        "primary_entity": primary_entity,
        "entities_list": list(entities_list),
        "is_academic": bool(is_academic),
        "routing_override_applied": bool(routing_override_applied),
        "routing_override_reason": routing_override_reason,
        "focus_academic": bool(focus_academic),
        "force_intent_news": bool(force_intent_news),
        "complexity": complexity,
        "max_queries": int(max_queries),
        "results_per_query": int(results_per_query),
        "search_depth": search_depth,
        "top_chunks": int(top_chunks),
        "max_iterations": int(max_iterations),
        "run_contract_ref": dict(run_contract_ref or {}),
        "contract_source_requirement_hints": [
            dict(item) for item in (contract_source_requirement_hints or ()) if isinstance(item, Mapping)
        ],
        "contract_consumed_by_query_production": bool(run_contract_ref),
    }


def _build_query_production_payload(
    *,
    action: AuthorizedAction,
    effective_route_posture: Mapping[str, Any],
    candidate_source: str,
    candidate_queries: Sequence[str],
    candidate_strategies: Sequence[Mapping[str, Any]],
    recon_summary: Sequence[Mapping[str, Any]],
    entity_update_projection: Mapping[str, Any],
    anchor_packet_telemetry: Mapping[str, Any],
    nutrition_lookup_telemetry: Mapping[str, Any],
    include_domains: Sequence[str],
    provider_diagnostics: Sequence[Mapping[str, Any]],
    contract_source_requirement_hints: Sequence[Mapping[str, Any]],
    initial_query_allocation_policy: InitialQueryAllocationPolicy,
    accepted_contract_ref: Mapping[str, Any],
    search_work_plan_ref: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "run_id": action.run_id,
        "stage": action.stage,
        "observation_type": ObservationType.QUERY_CANDIDATES_PRODUCED.value,
        "status": RunStageStatus.COMPLETED.value,
        "effective_route_posture": dict(effective_route_posture),
        "candidate_source": candidate_source,
        "candidate_query_count": len(list(candidate_queries)),
        "candidate_query_projection": _clean_query_projection(candidate_queries),
        "candidate_strategy_projection": [dict(item) for item in candidate_strategies],
        "initial_query_allocation_policy": (initial_query_allocation_policy.to_dict()),
        "accepted_contract_ref": dict(accepted_contract_ref),
        "search_work_plan_ref": dict(search_work_plan_ref),
        "recon": {
            "affected_component_count": len(list(recon_summary)),
            "component_postures": [dict(item) for item in recon_summary],
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligible": False,
        },
        "entity_update_projection": dict(entity_update_projection),
        "researcher_fallback_status": "retired_not_reachable",
        "legacy_initial_producer_execution": {
            "brave_reconnaissance_executed": False,
            "recon_rewriter_executed": False,
            "researcher_model_executed": False,
            "core_topic_fallback_executed": False,
        },
        "contract_source_requirement_hints": [
            dict(item) for item in contract_source_requirement_hints if isinstance(item, Mapping)
        ],
        "diagnostics": {
            "anchor_packet_present": bool(anchor_packet_telemetry.get("anchor_packet_present")),
            "nutrition_lookup_detected": bool(nutrition_lookup_telemetry.get("nutrition_lookup_detected")),
            "news_domain_augmentation_applied": (str(effective_route_posture.get("intent") or "") == "news"),
            "include_domain_count": len(list(include_domains)),
            "provider_diagnostic_count": len(list(provider_diagnostics)),
            "small_global_initial_query_cap_applied": False,
        },
        "provenance": {
            "query_production_owner": "RunKernel",
            "executor": "core.query_production_runtime.execute_query_production_action",
            "query_order_owner": "QueryPlan",
            "initial_candidate_owner": "SearchPlanner",
            "search_work_owner": "contract-bound SearchWorkPlan",
            "raw_prompts_retained": False,
            "raw_model_responses_retained": False,
            "raw_provider_payloads_retained": False,
        },
    }


def query_plan_admission_inputs_from_query_production_projection(
    projection: Mapping[str, Any],
) -> QueryProductionAdmissionInputs:
    """Return the reduced query-production facts that QueryPlan admission consumes."""

    candidate_queries = list(projection.get("candidate_query_projection") or [])
    candidate_strategies = [
        dict(item) for item in projection.get("candidate_strategy_projection") or [] if isinstance(item, Mapping)
    ]
    candidate_source = str(projection.get("candidate_source") or "").strip()
    effective_route_posture = dict(projection.get("effective_route_posture") or {})
    if not candidate_source:
        raise ValueError("query production projection missing candidate_source")
    if candidate_source not in {"search_planner", "search_planner_revision"}:
        raise ValueError(f"unsupported query production candidate source: {candidate_source}")
    if not candidate_queries:
        raise ValueError("query production projection missing candidate queries")
    if not effective_route_posture:
        raise ValueError("query production projection missing effective route posture")
    if not candidate_strategies:
        raise ValueError("query production projection missing candidate strategies")
    if [item.get("candidate_query_text") for item in candidate_strategies] != (candidate_queries):
        raise ValueError("query production candidate strategy/text projection does not match")
    policy = _policy_from_projection(projection.get("initial_query_allocation_policy"))
    return QueryProductionAdmissionInputs(
        candidate_queries=[str(query) for query in candidate_queries],
        candidate_strategies=candidate_strategies,
        candidate_source=candidate_source,
        effective_route_posture=effective_route_posture,
        contract_source_requirement_hints=[
            dict(item) for item in projection.get("contract_source_requirement_hints", []) if isinstance(item, Mapping)
        ],
        initial_query_allocation_policy=policy,
    )


def _policy_from_projection(value: Any) -> InitialQueryAllocationPolicy:
    if isinstance(value, InitialQueryAllocationPolicy):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("query production projection missing initial-query allocation policy")
    field_names = (
        "policy_version",
        "primary_query_target_per_required_component",
        "initial_candidate_ceiling_per_required_component",
        "immediate_dispatch_target_per_required_component",
        "recon_candidate_ceiling_per_affected_component",
        "redundancy_rejection_enabled",
        "required_component_floor_enabled",
    )
    kwargs = {name: value[name] for name in field_names if name in value}
    return InitialQueryAllocationPolicy(**kwargs)


def _accepted_contract_ref(
    initial_contract: Mapping[str, Any] | None,
    current_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    current = dict(current_contract or {})
    initial = dict(initial_contract or {})
    contract = current or initial
    version = str(contract.get("accepted_contract_version") or "").strip()
    digest = str(contract.get("accepted_contract_digest") or "").strip()
    if not version or not digest:
        raise QueryStrategyConvergenceError(
            "query production requires an accepted AnswerContract version/digest",
            failure_code=(
                QueryStrategyConvergenceFailureCode.ANSWER_CONTRACT_BINDING_MISSING
            ),
        )
    return {
        "contract_version": version,
        "contract_digest": digest,
        "parent_kind": ("current_answer_contract" if current else "initial_answer_contract"),
    }


def _search_work_plan_ref(
    search_work_plan: Mapping[str, Any] | None,
    *,
    accepted_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    plan = dict(search_work_plan or {})
    metadata = dict(plan.get("metadata") or {}) if isinstance(plan.get("metadata"), Mapping) else {}
    plan_contract_ref = (
        dict(metadata.get("accepted_contract_ref") or {})
        if isinstance(metadata.get("accepted_contract_ref"), Mapping)
        else {}
    )
    if not plan or plan.get("passive") is not False:
        raise QueryStrategyConvergenceError(
            "query production requires an active contract-bound SearchWorkPlan",
            failure_code=QueryStrategyConvergenceFailureCode.SEARCH_WORK_PLAN_MISSING,
        )
    if plan_contract_ref != dict(accepted_contract_ref):
        raise QueryStrategyConvergenceError(
            "SearchWorkPlan accepted-contract binding became stale",
            failure_code=(
                QueryStrategyConvergenceFailureCode.SEARCH_WORK_PLAN_CONTRACT_STALE
            ),
        )
    plan_id = str(metadata.get("search_work_plan_id") or metadata.get("construction_id") or "").strip()
    if not plan_id:
        raise QueryStrategyConvergenceError(
            "contract-bound SearchWorkPlan requires stable identity",
            failure_code=(
                QueryStrategyConvergenceFailureCode.SEARCH_WORK_PLAN_IDENTITY_MISSING
            ),
        )
    return {
        "search_work_plan_id": plan_id,
        "schema_version": plan.get("schema_version"),
        "accepted_contract_ref": plan_contract_ref,
        "runtime_consumed": True,
    }


def execute_initial_query_strategy_convergence(
    *,
    run_kernel: Any,
    router_query_preparation_contract: RouterQueryPreparationState,
    query: str,
    strategy: str,
    current_date: str,
    focus_academic: bool,
    force_intent_news: bool,
    include_domains: Sequence[str],
    exclude_domains: Sequence[str] = (),
    news_preferred_domains: Sequence[str],
    route_projection: Mapping[str, Any],
    run_contract_projection: Mapping[str, Any],
    supplied_context: Mapping[str, Any] | None = None,
    planner_adapter: SearchPlannerAdapter,
    scout_adapter: ScoutDisambiguationAdapter | None = None,
    revision_adapter: SearchPlannerRevisionAdapter | None = None,
    provider_diagnostics: MutableSequence[dict[str, Any]],
    waste_flags: Sequence[str] | None = None,
    initial_query_allocation_policy: InitialQueryAllocationPolicy = (DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY),
) -> InitialQueryStrategyConvergenceResult:
    """Run the one ordinary initial semantic-planning producer chain.

    Every reduction happens before query production is authorized.  Therefore
    a malformed planner proposal, stale contract ref, missing required recon
    adapter, or invalid SearchWorkPlan yields no retrieval-dispatchable query.
    """

    if not isinstance(initial_query_allocation_policy, InitialQueryAllocationPolicy):
        raise QueryStrategyConvergenceError(
            "initial strategy convergence requires the code-owned policy",
            failure_code=QueryStrategyConvergenceFailureCode.ALLOCATION_POLICY_REQUIRED,
        )
    route_facts = {
        "intent": router_query_preparation_contract.intent,
        "report_type": router_query_preparation_contract.report_type,
        "query_type": router_query_preparation_contract.query_type,
        "core_topic": router_query_preparation_contract.core_topic,
        "primary_entity": router_query_preparation_contract.primary_entity,
        "entities": list(router_query_preparation_contract.entities_list),
        "is_academic": router_query_preparation_contract.is_academic,
    }
    planner_input = SearchPlannerInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        user_query_text=query,
        requested_mode=strategy,
        safe_context={
            "phase": "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01",
            "product_path": True,
            "route_facts": route_facts,
            "run_contract_projection": dict(run_contract_projection),
            "current_date": current_date,
            "include_domains": list(include_domains),
            "exclude_domains": list(exclude_domains),
            "supplied_context": dict(supplied_context or {}),
            "supplied_context_posture": {
                "planning_context_only": True,
                "evidence_admitted": False,
                "source_obligation_satisfied": False,
                "citation_eligible": False,
            },
            "initial_query_allocation_policy_version": (initial_query_allocation_policy.policy_version),
        },
        route_context_ref={
            "route_id": route_projection.get("route_id"),
        },
        run_context_ref={
            "run_contract_id": run_contract_projection.get("contract_id"),
        },
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )
    planner_action = invoke_run_kernel_initial_planning(
        "search_planner_production",
        lambda: run_kernel.authorize_search_planner_production(
            user_query_digest=planner_input.user_query_digest,
            planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
            inputs={
                "route_id": route_projection.get("route_id"),
                "run_contract_id": run_contract_projection.get("contract_id"),
                "allocation_policy_version": (initial_query_allocation_policy.policy_version),
            },
        ),
    )
    planner_result = execute_search_planner_action(
        action=planner_action,
        planner_input=planner_input,
        adapter=planner_adapter,
    )
    invoke_run_kernel_initial_planning(
        "search_planner_production",
        lambda: run_kernel.reduce(
            Observation.from_action(
                planner_action,
                observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
                status=RunStageStatus.COMPLETED,
                payload=planner_result.observation_payload,
            )
        ),
    )

    qmr = dict(run_kernel.state.search_planner_proposal_state.get("question_meaning_record") or {})
    if not qmr:
        raise QueryStrategyConvergenceError(
            "SearchPlanner reduction did not produce a QuestionMeaningRecord",
            failure_code=(
                QueryStrategyConvergenceFailureCode.QUESTION_MEANING_RECORD_MISSING
            ),
        )
    acceptance_action = invoke_run_kernel_initial_planning(
        "initial_answer_contract_acceptance",
        lambda: run_kernel.authorize_initial_answer_contract_acceptance(
            parent_question_meaning_record_id=str(qmr.get("record_id") or ""),
            parent_proposal_digest=str(qmr.get("record_digest") or ""),
            inputs={
                "planner_action_id": planner_action.action_id,
                "allocation_policy_version": (initial_query_allocation_policy.policy_version),
            },
        ),
    )
    invoke_run_kernel_initial_planning(
        "initial_answer_contract_acceptance",
        lambda: run_kernel.reduce(
            Observation.from_action(
                acceptance_action,
                observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
                status=RunStageStatus.COMPLETED,
                payload={"question_meaning_record": qmr},
            )
        ),
    )
    accepted_contract = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    base_candidate_strategies = initial_query_strategies_from_planner_state(
        planner_state=run_kernel.state.search_planner_proposal_state,
        accepted_contract=accepted_contract,
        policy=initial_query_allocation_policy,
    )
    recon_summary, revision_projections = _execute_recon_and_revisions(
        run_kernel=run_kernel,
        candidate_strategies=base_candidate_strategies,
        policy=initial_query_allocation_policy,
        scout_adapter=scout_adapter,
        revision_adapter=revision_adapter,
    )
    accepted_contract = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    candidate_strategies = _strategies_with_authorized_revisions(
        base_strategies=base_candidate_strategies,
        revision_projections=revision_projections,
        accepted_contract=accepted_contract,
    )

    search_work_action = invoke_run_kernel_initial_planning(
        "search_work_plan_construction",
        lambda: run_kernel.authorize_search_work_plan_construction(
            reason="contract_bound_search_work_plan_before_query_plan",
            inputs={
                "planner_proposal_digest": (run_kernel.state.search_planner_proposal_state.get("proposal_digest")),
                "accepted_contract_digest": accepted_contract.get("accepted_contract_digest"),
                "allocation_policy_version": (initial_query_allocation_policy.policy_version),
            },
        ),
    )
    search_work_observation = observe_contract_bound_search_work_plan_construction(
        search_work_action,
        construction_id=(f"search-work-plan:{run_kernel.state.request_id}:initial"),
        requested_mode=strategy,
        planner_state=run_kernel.state.search_planner_proposal_state,
        initial_contract=run_kernel.state.initial_answer_contract,
        current_contract=run_kernel.state.current_answer_contract,
        run_authority_contract=run_contract_projection,
        policy=initial_query_allocation_policy,
        revision_projections=revision_projections,
    )
    invoke_run_kernel_initial_planning(
        "search_work_plan_construction",
        lambda: run_kernel.reduce(search_work_observation),
    )

    query_production_action = invoke_run_kernel_initial_planning(
        "query_production",
        lambda: run_kernel.authorize_query_production(
            reason="search_planner_strategy_projection_before_queryplan_consumption",
            inputs={
                "planner_action_id": planner_action.action_id,
                "initial_contract_acceptance_action_id": acceptance_action.action_id,
                "search_work_action_id": search_work_action.action_id,
                "candidate_count": len(candidate_strategies),
                "required_component_count": len(accepted_contract.get("accepted_answer_component_refs") or ()),
                "allocation_policy_version": (initial_query_allocation_policy.policy_version),
                "small_global_initial_query_cap_applied": False,
            },
        ),
    )
    query_production_result = execute_query_production_action(
        query_production_action,
        router_query_preparation_contract=router_query_preparation_contract,
        query=query,
        strategy=strategy,
        current_date=current_date,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        include_domains=include_domains,
        news_preferred_domains=news_preferred_domains,
        candidate_strategies=candidate_strategies,
        initial_answer_contract=run_kernel.state.initial_answer_contract,
        current_answer_contract=run_kernel.state.current_answer_contract,
        search_work_plan=run_kernel.state.search_work_plan,
        recon_summary=recon_summary,
        initial_query_allocation_policy=initial_query_allocation_policy,
        provider_diagnostics=provider_diagnostics,
        waste_flags=waste_flags,
        run_contract_projection=run_contract_projection,
    )
    invoke_run_kernel_initial_planning(
        "query_production",
        lambda: run_kernel.reduce(query_production_result.observation),
    )
    return InitialQueryStrategyConvergenceResult(
        query_production_action=query_production_action,
        query_production_result=query_production_result,
        search_work_plan=dict(run_kernel.state.search_work_plan),
        recon_summary=tuple(recon_summary),
        revision_projections=tuple(revision_projections),
    )


def execute_query_production_action(
    action: AuthorizedAction,
    *,
    router_query_preparation_contract: RouterQueryPreparationState,
    query: str,
    strategy: str,
    current_date: str,
    focus_academic: bool,
    force_intent_news: bool,
    include_domains: Sequence[str],
    news_preferred_domains: Sequence[str],
    candidate_strategies: Sequence[Mapping[str, Any]] | None = None,
    initial_answer_contract: Mapping[str, Any] | None = None,
    current_answer_contract: Mapping[str, Any] | None = None,
    search_work_plan: Mapping[str, Any] | None = None,
    recon_summary: Sequence[Mapping[str, Any]] = (),
    initial_query_allocation_policy: InitialQueryAllocationPolicy = (DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY),
    provider_diagnostics: MutableSequence[dict[str, Any]],
    waste_flags: Sequence[str] | None = None,
    run_contract_projection: Mapping[str, Any] | None = None,
    **_retired_legacy_initial_producer_inputs: Any,
) -> QueryProductionResult:
    """Project already-converged SearchPlanner strategies for QueryPlan.

    The compatibility kwargs deliberately make old call sites fail closed
    without reaching a model, provider, recon rewriter, or core-topic fallback.
    """

    validate_authorized_action(
        action,
        action_type=ActionType.QUERY_PRODUCTION,
        stage=QUERY_PRODUCTION_STAGE,
        expected_observation_type=ObservationType.QUERY_CANDIDATES_PRODUCED,
    )

    intent = router_query_preparation_contract.intent
    report_type = router_query_preparation_contract.report_type
    image_mode = router_query_preparation_contract.image_mode
    core_topic = router_query_preparation_contract.core_topic
    is_academic = router_query_preparation_contract.is_academic
    query_type = router_query_preparation_contract.query_type
    primary_entity = router_query_preparation_contract.primary_entity
    entities_list = router_query_preparation_contract.entities_list
    router_entity_retry_used = router_query_preparation_contract.router_entity_retry_used
    router_original_report_type = router_query_preparation_contract.router_original_report_type
    router_original_query_type = router_query_preparation_contract.router_original_query_type
    routing_override_applied = False
    routing_override_reason: str | None = None
    active_waste_flags = list(waste_flags or [])
    policy = initial_query_allocation_policy
    if not isinstance(policy, InitialQueryAllocationPolicy):
        raise QueryStrategyConvergenceError(
            "query production requires the code-owned allocation policy",
            failure_code=QueryStrategyConvergenceFailureCode.ALLOCATION_POLICY_REQUIRED,
        )
    strategies = [dict(item) for item in (candidate_strategies or ()) if isinstance(item, Mapping)]
    if not strategies:
        raise QueryStrategyConvergenceError(
            "SearchPlanner produced no valid initial component query strategies; "
            "legacy initial producer fallback is retired",
            failure_code=QueryStrategyConvergenceFailureCode.INITIAL_STRATEGIES_EMPTY,
        )
    candidate_queries = [str(item.get("candidate_query_text") or "").strip() for item in strategies]
    if any(not query or len(query) > 300 for query in candidate_queries):
        raise QueryStrategyConvergenceError(
            "SearchPlanner initial query strategies require bounded exact text",
            failure_code=(
                QueryStrategyConvergenceFailureCode.INITIAL_STRATEGY_TEXT_UNBOUNDED
            ),
        )
    accepted_contract_ref = _accepted_contract_ref(
        initial_answer_contract,
        current_answer_contract,
    )
    search_work_plan_ref = _search_work_plan_ref(
        search_work_plan,
        accepted_contract_ref=accepted_contract_ref,
    )
    contract_source_requirement_hints = contract_query_hints_from_projection(run_contract_projection)
    run_contract_ref = {}
    if isinstance(run_contract_projection, Mapping) and run_contract_projection:
        run_contract_ref = {
            "owner": run_contract_projection.get("owner"),
            "contract_id": run_contract_projection.get("contract_id"),
            "synthesis_mode": run_contract_projection.get("synthesis_mode"),
            "selected_template_ids": run_contract_projection.get(
                "selected_template_ids",
                [],
            ),
            "source_requirement_count": run_contract_projection.get(
                "source_requirement_count",
                0,
            ),
        }

    nutrition_lookup_telemetry = detect_nutrition_lookup_telemetry(query)
    if nutrition_lookup_telemetry["nutrition_lookup_detected"]:
        report_type = "quantitative_comparison"
        routing_override_applied = True
        routing_override_reason = "nutrition_macro_per_100g_lookup"

    if focus_academic:
        is_academic = True
    if force_intent_news:
        intent = "news"

    anchor_packet_telemetry: dict[str, Any] = {}
    if strategy == "Balanced":
        anchor_packet_telemetry = build_shadow_anchor_packet(
            mode=strategy,
            query=query,
            current_date=current_date,
            intent=intent,
            report_type=report_type,
            router_original_report_type=router_original_report_type,
            query_type=query_type,
            router_original_query_type=router_original_query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            entities=entities_list,
            router_entity_retry_used=router_entity_retry_used,
        )

    active_include_domains = list(include_domains)
    if intent == "news":
        active_include_domains = list(set(active_include_domains + list(news_preferred_domains)))

    complexity = _complexity_for_strategy(strategy)
    budget = _budget_for_complexity(complexity)
    max_queries = int(budget["max_queries"])
    results_per_query = int(budget["results_per_query"])
    search_depth = str(budget["search_depth"])
    top_chunks = int(budget["top_chunks"])
    max_iterations = int(budget["max_iterations"])

    normalized_recon_summary = [dict(item) for item in recon_summary if isinstance(item, Mapping)]
    recon_fired = any(
        str(item.get("status") or "").strip() in {"completed", "revision_applied", "query_direction_revised"}
        for item in normalized_recon_summary
    )
    confidence_values = [
        str(item.get("confidence") or "").strip()
        for item in normalized_recon_summary
        if str(item.get("confidence") or "").strip()
    ]
    recon_confidence = confidence_values[-1] if confidence_values else None
    canonical_subject_resolved = None
    recon_seconds = sum(max(0.0, float(item.get("duration_seconds") or 0.0)) for item in normalized_recon_summary)

    entity_count_before = len(entities_list)
    canonical_inserted = False
    if entities_list:
        primary_entity = entities_list[0][:200]
    elif primary_entity.strip():
        entities_list = [primary_entity.strip()[:200]]
        primary_entity = entities_list[0][:200]
    empty_entity_flag = len(entities_list) == 0

    candidate_source = (
        "search_planner_revision"
        if any(item.get("parent_search_planner_revision_ref") for item in strategies)
        else "search_planner"
    )
    researcher_fallback_status = "retired_not_reachable"

    route_posture = _effective_route_posture(
        intent=intent,
        report_type=report_type,
        image_mode=image_mode,
        core_topic=core_topic,
        primary_entity=primary_entity,
        entities_list=entities_list,
        is_academic=is_academic,
        query_type=query_type,
        routing_override_applied=routing_override_applied,
        routing_override_reason=routing_override_reason,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        complexity=complexity,
        max_queries=max_queries,
        results_per_query=results_per_query,
        search_depth=search_depth,
        top_chunks=top_chunks,
        max_iterations=max_iterations,
        run_contract_ref=run_contract_ref,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    entity_update_projection = {
        "entity_count_before": entity_count_before,
        "entity_count_after": len(entities_list),
        "canonical_subject_inserted": canonical_inserted,
        "primary_entity": primary_entity,
    }
    payload = _build_query_production_payload(
        action=action,
        effective_route_posture=route_posture,
        candidate_source=candidate_source,
        candidate_queries=candidate_queries,
        candidate_strategies=strategies,
        recon_summary=normalized_recon_summary,
        entity_update_projection=entity_update_projection,
        anchor_packet_telemetry=anchor_packet_telemetry,
        nutrition_lookup_telemetry=nutrition_lookup_telemetry,
        include_domains=active_include_domains,
        provider_diagnostics=provider_diagnostics,
        contract_source_requirement_hints=contract_source_requirement_hints,
        initial_query_allocation_policy=policy,
        accepted_contract_ref=accepted_contract_ref,
        search_work_plan_ref=search_work_plan_ref,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.QUERY_CANDIDATES_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    return QueryProductionResult(
        candidate_queries=list(candidate_queries),
        candidate_source=candidate_source,
        effective_route_posture=route_posture,
        include_domains=active_include_domains,
        anchor_packet_telemetry=anchor_packet_telemetry,
        nutrition_lookup_telemetry=dict(nutrition_lookup_telemetry),
        waste_flags=active_waste_flags,
        recon_fired=recon_fired,
        recon_confidence=recon_confidence,
        canonical_subject_resolved=canonical_subject_resolved,
        recon_seconds=recon_seconds,
        researcher_fallback_status=researcher_fallback_status,
        empty_entity_flag=empty_entity_flag,
        contract_source_requirement_hints=list(contract_source_requirement_hints),
        candidate_strategies=strategies,
        initial_query_allocation_policy=policy,
        recon_summary=normalized_recon_summary,
        observation=observation,
    )


@dataclass(frozen=True, slots=True)
class QueryPlanAdmissionResult:
    """QueryPlan admission output plus the kernel observation to reduce."""

    queries: list[str]
    current_queries: list[str]
    recency_merge_used: bool
    recency_merge_query: str | None
    initial_query_admission: InitialQueryAdmissionResult
    router_query_preparation_contract: RouterQueryPreparationState
    observation: Observation


def _query_plan_projection(
    query_authority: QueryPlanRuntimeAdapter,
    *,
    query_source: str,
    recency_merge_used: bool,
    recency_merge_query: str | None,
    current_queries: Sequence[str],
    initial_query_admission: InitialQueryAdmissionResult,
    initial_query_allocation_policy: InitialQueryAllocationPolicy,
    contract_source_requirement_hints: Sequence[Mapping[str, Any]] | None = None,
    provider_job_execution_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    query_plan = query_authority.to_trace_fragment().get(QUERY_PLAN_TRACE_KEY, {})
    projection = {
        "query_plan_ref": query_plan,
        "query_source": query_source,
        "recency_merge_used": bool(recency_merge_used),
        "recency_merge_query": recency_merge_query,
        "current_query_count": len(list(current_queries)),
        "query_order_owner": "QueryPlan",
        "initial_query_admission": initial_query_admission.to_dict(),
        "initial_query_allocation_policy": (initial_query_allocation_policy.to_dict()),
        "small_global_initial_query_cap_applied": False,
        "required_component_globally_truncated": False,
        "post_result_followup_dispatched": False,
        "contract_source_requirement_hints": [
            dict(item) for item in (contract_source_requirement_hints or ()) if isinstance(item, Mapping)
        ],
    }
    if provider_job_execution_handoff:
        projection["provider_job_execution_handoff"] = dict(provider_job_execution_handoff)
        projection["provider_job_execution_handoff_present"] = True
    return projection


def execute_query_plan_admission_action(
    action: AuthorizedAction,
    *,
    query_authority: QueryPlanRuntimeAdapter,
    router_query_preparation_contract: RouterQueryPreparationState,
    candidate_queries: Sequence[str],
    candidate_strategies: Sequence[Mapping[str, Any]],
    candidate_source: str,
    query_type: str,
    current_date: str,
    max_queries: int,
    route_runtime_posture: Mapping[str, Any],
    search_work_projection: Mapping[str, Any] | None = None,
    initial_query_allocation_policy: InitialQueryAllocationPolicy = (DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY),
    search_judgment_projection: Mapping[str, Any] | None = None,
) -> QueryPlanAdmissionResult:
    """Admit component-bound planner strategies into the first DISCOVER wave."""

    validate_authorized_action(
        action,
        action_type=ActionType.QUERY_PLAN_ADMISSION,
        stage=QUERY_PLAN_ADMISSION_STAGE,
        expected_observation_type=ObservationType.QUERY_PLAN_ADMITTED,
    )
    if candidate_source not in {"search_planner", "search_planner_revision"}:
        raise ValueError(f"unsupported query admission candidate source: {candidate_source}")
    if search_judgment_projection:
        raise ValueError("initial QueryPlan admission cannot dispatch post-result SearchJudgment follow-up")
    strategies = [dict(item) for item in candidate_strategies if isinstance(item, Mapping)]
    strategy_queries = [str(item.get("candidate_query_text") or "").strip() for item in strategies]
    if strategy_queries != [str(query) for query in candidate_queries]:
        raise ValueError("QueryPlan admission requires exact SearchPlanner strategy/query order")
    if not isinstance(initial_query_allocation_policy, InitialQueryAllocationPolicy):
        raise ValueError("QueryPlan admission requires the code-owned policy")
    allocation = query_authority.admit_initial_component_strategies(
        strategies,
        search_work_projection=search_work_projection,
        policy=initial_query_allocation_policy,
        origin=candidate_source,
    )
    current_queries = list(allocation.immediate_dispatch_queries)
    # Only the immediate first wave crosses the ordinary retrieval-loop seam.
    # Prepared secondaries remain QueryPlan state for later SearchJudgment.
    queries = list(current_queries)
    immediate_set = set(current_queries)
    immediate_strategies = [
        item for item in strategies if str(item.get("candidate_query_text") or "").strip() in immediate_set
    ]
    recency_queries = [
        str(item.get("candidate_query_text") or "").strip()
        for item in immediate_strategies
        if str(item.get("requested_role") or "").strip() == QueryPlanRole.RECENCY.value
    ]
    recency_merge_used = bool(recency_queries)
    recency_merge_query = recency_queries[0] if len(recency_queries) == 1 else None
    official_bias_requested = any(
        str(item.get("requested_role") or "").strip()
        in {
            QueryPlanRole.OFFICIAL_BIAS.value,
            QueryPlanRole.CANONICAL_BIAS.value,
        }
        for item in immediate_strategies
    )
    contract_source_requirement_hints = [
        dict(item)
        for item in route_runtime_posture.get("contract_source_requirement_hints", [])
        if isinstance(item, Mapping)
    ]
    run_contract_ref = (
        dict(route_runtime_posture.get("run_contract_ref") or {})
        if isinstance(route_runtime_posture.get("run_contract_ref"), Mapping)
        else {}
    )
    if run_contract_ref or contract_source_requirement_hints:
        query_authority.plan = query_authority.plan.append(
            origin="run_authority_contract",
            role="initial",
            status="admitted",
            phase="run_contract_source_requirements",
            admission_reason="source_requirement_hints_consumed",
            metadata={
                "contract_ref": run_contract_ref,
                "contract_source_requirement_hints": contract_source_requirement_hints,
                "contract_changed_query_order": False,
            },
        )

    provider_job_execution_handoff = build_provider_job_execution_handoff(
        search_work_projection=search_work_projection,
        query_plan_trace=query_authority.to_trace_fragment().get(
            QUERY_PLAN_TRACE_KEY,
            {},
        ),
        current_queries=current_queries,
    )
    intent = str(route_runtime_posture["intent"])
    route_entities = route_runtime_posture.get(
        "entities_list",
        route_runtime_posture.get("entities"),
    )
    route_query_type = str(route_runtime_posture.get("query_type", query_type))
    router_query_preparation_contract = with_router_query_runtime_posture(
        router_query_preparation_contract,
        intent=intent,
        report_type=str(route_runtime_posture["report_type"]),
        query_type=route_query_type,
        primary_entity=str(route_runtime_posture["primary_entity"]),
        entities=route_entities,
        is_academic=bool(route_runtime_posture["is_academic"]),
        routing_override_applied=bool(route_runtime_posture["routing_override_applied"]),
        routing_override_reason=route_runtime_posture["routing_override_reason"],
        focus_academic=bool(route_runtime_posture["focus_academic"]),
        force_intent_news=bool(route_runtime_posture["force_intent_news"]),
        complexity=str(route_runtime_posture["complexity"]),
        max_queries=max_queries,
        results_per_query=int(route_runtime_posture["results_per_query"]),
        search_depth=str(route_runtime_posture["search_depth"]),
        top_chunks=int(route_runtime_posture["top_chunks"]),
        max_iterations=int(route_runtime_posture["max_iterations"]),
        recency_merge_used=recency_merge_used,
        recency_query=recency_merge_query,
        official_bias_requested=official_bias_requested,
        official_bias_phrase=None,
        finalized_queries=current_queries,
        current_queries=current_queries,
        query_source=candidate_source,
        run_contract_ref=run_contract_ref,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    payload = _query_plan_projection(
        query_authority,
        query_source=candidate_source,
        recency_merge_used=recency_merge_used,
        recency_merge_query=recency_merge_query,
        current_queries=current_queries,
        initial_query_admission=allocation,
        initial_query_allocation_policy=initial_query_allocation_policy,
        contract_source_requirement_hints=contract_source_requirement_hints,
        provider_job_execution_handoff=provider_job_execution_handoff,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.QUERY_PLAN_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    return QueryPlanAdmissionResult(
        queries=list(queries),
        current_queries=list(current_queries),
        recency_merge_used=recency_merge_used,
        recency_merge_query=recency_merge_query,
        initial_query_admission=allocation,
        router_query_preparation_contract=router_query_preparation_contract,
        observation=observation,
    )


__all__ = [
    "InitialQueryStrategyConvergenceResult",
    "QueryProductionAdmissionInputs",
    "QueryProductionResult",
    "QueryPlanAdmissionResult",
    "QueryStrategyConvergenceError",
    "QueryStrategyConvergenceFailureCode",
    "execute_initial_query_strategy_convergence",
    "execute_query_production_action",
    "execute_query_plan_admission_action",
    "query_plan_admission_inputs_from_query_production_projection",
]
