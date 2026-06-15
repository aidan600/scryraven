"""Runtime shadow SearchWorkPlan construction after RunAuthority contract synthesis.

This helper is a bounded projection adapter. It consumes only safe structured
runtime state that already exists after RunAuthority contract reduction and
returns a RunKernel observation through the AG-96C7 construction seam. It may
derive deterministic query-shape and contract-resolution records for shadow
projection, but it does not build executable QueryPlan entries, choose
providers, call search/retrieval/model APIs, or mutate RunKernel state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.query_shape_contract_resolution import (
    AssessmentConfidence,
    AssessmentPosture,
    ComponentCandidate,
    ContractResolutionRecord,
    FollowUpDepthPosture,
    OutputPosture,
    ProviderJobCandidate,
    QueryShapeAssessment,
    SearchWorkPlanConstructionDesignRecord,
    SourceObligationCandidate,
    StopEscalateRefusePosture,
)
from core.run_kernel import AuthorizedAction, Observation
from core.search_work_plan import (
    EffectiveContractKind,
    ModeMismatchPosture,
    ProviderJobKind,
    QueryShapeKind,
    SearchMode,
    SourceObligationKind,
    SourceObligationStrictness,
    StopConditionKind,
)
from core.search_work_plan_construction import (
    SearchWorkPlanConstructionInput,
    observe_search_work_plan_construction,
)
from core.search_work_query_shape_runtime import (
    DeterministicSearchWorkRuntimeInput,
    build_deterministic_search_work_runtime_records,
)

RUNTIME_SHADOW_SEARCH_WORK_PLAN_HELPER = "ag96c8_runtime_shadow_search_work_plan"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
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


@dataclass(frozen=True, slots=True)
class RuntimeShadowSearchWorkPlanInput:
    """Safe runtime inputs available after RunAuthority contract synthesis."""

    run_contract_projection: Mapping[str, Any]
    route_projection: Mapping[str, Any] | None = None
    requested_mode: str | None = None
    selected_depth: str | None = None
    safe_query_preview: str | None = None
    current_date_ref: str | Mapping[str, Any] | None = None
    safe_user_domain_hints: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None


def observe_runtime_shadow_search_work_plan_construction(
    action: AuthorizedAction,
    runtime_input: RuntimeShadowSearchWorkPlanInput,
) -> Observation:
    """Construct and observe a shadow SearchWorkPlan projection."""

    construction_input = build_runtime_shadow_search_work_plan_input(runtime_input)
    return observe_search_work_plan_construction(action, construction_input)


def build_runtime_shadow_search_work_plan_input(
    runtime_input: RuntimeShadowSearchWorkPlanInput,
) -> SearchWorkPlanConstructionInput:
    """Return AG-96C6 construction input from already-safe runtime state.

    AG-96E1 prefers deterministic real QueryShapeAssessment and
    ContractResolutionRecord construction. If validation fails, the helper
    falls back to the older conservative scaffold and records why.
    """
    contract = _safe_mapping(runtime_input.run_contract_projection)
    route_facts = _safe_route_facts(runtime_input.route_projection or {})
    contract_id = _clean_token(contract.get("contract_id")) or "contract:unavailable"
    try:
        records = build_deterministic_search_work_runtime_records(
            DeterministicSearchWorkRuntimeInput(
                contract_id=contract_id,
                run_contract_projection=contract,
                route_facts=route_facts,
                requested_mode=runtime_input.requested_mode,
                selected_depth=runtime_input.selected_depth
                or _clean_token(contract.get("selected_depth")),
                safe_query_preview=runtime_input.safe_query_preview,
                current_date_ref=runtime_input.current_date_ref,
                metadata=runtime_input.metadata,
            )
        )
        return _construction_input_from_records(
            runtime_input=runtime_input,
            contract=contract,
            route_facts=route_facts,
            contract_id=contract_id,
            assessment=records.query_shape_assessment,
            resolution=records.contract_resolution,
        )
    except Exception as exc:
        return _build_conservative_runtime_shadow_search_work_plan_input(
            runtime_input,
            contract=contract,
            route_facts=route_facts,
            contract_id=contract_id,
            fallback_reason=f"deterministic_ag96e1_failed:{type(exc).__name__}",
        )


def _construction_input_from_records(
    *,
    runtime_input: RuntimeShadowSearchWorkPlanInput,
    contract: Mapping[str, Any],
    route_facts: Mapping[str, Any],
    contract_id: str,
    assessment: QueryShapeAssessment,
    resolution: ContractResolutionRecord,
) -> SearchWorkPlanConstructionInput:
    selected_depth = _clean_token(runtime_input.selected_depth) or _clean_token(
        contract.get("selected_depth")
    )
    return SearchWorkPlanConstructionInput(
        construction_id=f"construction:{contract_id}:ag96e1",
        requested_mode_source="run_config_or_run_contract_projection",
        query_shape_assessment=assessment,
        contract_resolution=resolution,
        construction_design=SearchWorkPlanConstructionDesignRecord(
            design_id=f"design:{contract_id}:ag96e1",
            future_runtime_consumer="RunKernel.SearchWorkPlan shadow projection",
            closed_surfaces=(
                "QueryPlan behavior",
                "query generation/order/admission",
                "provider/search/retrieval behavior",
                "prompt behavior",
                "citation/final-answer behavior",
                "mode_policy.py",
            ),
            metadata={
                "runtime_shadow_scaffolding": False,
                "phase": "AG-96E1",
                "implements_query_shape_classifier": True,
                "implements_contract_resolver": True,
                "fallback_reason": None,
            },
        ).require_valid(),
        safe_route_facts=route_facts,
        run_authority_contract_ref={
            "contract_id": contract_id,
            "schema_version": contract.get("schema_version"),
        },
        current_date_ref=_safe_ref(runtime_input.current_date_ref),
        passive_mode_policy_snapshot={
            "requested_mode": resolution.requested_mode.value,
            "selected_depth": selected_depth,
            "source": "run_config_or_run_contract_projection",
            "runtime_mode_mutated": False,
        },
        safe_user_domain_hints=_safe_mapping(runtime_input.safe_user_domain_hints or {}),
        metadata=_safe_mapping(
            {
                "helper": RUNTIME_SHADOW_SEARCH_WORK_PLAN_HELPER,
                "phase": "AG-96E1",
                "runtime_shadow_scaffolding": False,
                "implements_query_shape_classifier": True,
                "implements_contract_resolver": True,
                "fallback_reason": None,
                "safe_structured_inputs_only": True,
                "safe_preview_used": bool(_clean_text(runtime_input.safe_query_preview)),
                "behavior_changed": False,
                "query_plan_behavior_changed": False,
                "provider_search_behavior_changed": False,
                **dict(runtime_input.metadata or {}),
            }
        ),
    )


def _build_conservative_runtime_shadow_search_work_plan_input(
    runtime_input: RuntimeShadowSearchWorkPlanInput,
    *,
    contract: Mapping[str, Any],
    route_facts: Mapping[str, Any],
    contract_id: str,
    fallback_reason: str | None,
) -> SearchWorkPlanConstructionInput:
    """Return the AG-96C8 conservative scaffold as an AG-96E1 fallback."""

    selected_depth = _clean_token(runtime_input.selected_depth) or _clean_token(
        contract.get("selected_depth")
    )
    requested_mode = _coerce_search_mode(runtime_input.requested_mode or selected_depth)
    effective_contract = _effective_contract_from_depth(selected_depth, requested_mode)
    requirements = _source_requirements(contract)
    component_id = "run-contract-shadow-primary"

    obligation_candidates = _source_obligation_candidates(requirements, component_id)
    provider_candidates = _provider_job_candidates(obligation_candidates)
    assessment = QueryShapeAssessment(
        assessment_id=f"assessment:{contract_id}:runtime-shadow",
        requested_mode=requested_mode,
        query_shape_kinds=_query_shape_kinds(contract, requirements),
        assessment_confidence=AssessmentConfidence.TENTATIVE,
        assessment_posture=AssessmentPosture.DETERMINISTIC_SIGNAL_ONLY,
        component_candidates=(
            ComponentCandidate(
                candidate_id=f"component:{component_id}",
                component_id=component_id,
                user_facing_subquestion=_component_subquestion(route_facts),
                entities=_route_entities(route_facts),
                source_obligation_candidate_ids=tuple(
                    candidate.candidate_id for candidate in obligation_candidates
                ),
                provider_job_candidate_ids=tuple(
                    candidate.candidate_id for candidate in provider_candidates
                ),
                metadata={
                    "runtime_shadow_scaffolding": True,
                    "basis": "run_authority_contract_projection_and_safe_route_facts",
                },
            ),
        ),
        source_obligation_candidates=obligation_candidates,
        provider_job_candidates=provider_candidates,
        first_pass_evidence_needed={
            "answer_bearing_source_custody": bool(obligation_candidates),
            "conflict_or_currentness_confirmation": _has_conflict_policy(contract),
        },
        deterministic_signals=(
            "contract_projection_only",
            "no_query_shape_classifier",
            "no_contract_resolver",
        ),
        stop_condition_candidates=_stop_conditions(requirements),
        metadata={
            "runtime_shadow_scaffolding": True,
            "implements_query_shape_classifier": False,
            "fallback_reason": fallback_reason,
            "uses_raw_query_text": False,
        },
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id=f"resolution:{contract_id}:runtime-shadow",
        requested_mode=requested_mode,
        effective_contract=effective_contract,
        mode_mismatch_posture=ModeMismatchPosture.NONE,
        allowed_follow_up_depth=_follow_up_depth(effective_contract),
        output_posture=_output_posture(effective_contract),
        stop_escalate_refuse_posture=StopEscalateRefusePosture.QUALIFY_IF_UNSATISFIED,
        rationale=(
            "Runtime shadow scaffolding derived from the reduced RunAuthority "
            "contract; this is not a real ContractResolver."
        ),
        metadata={
            "runtime_shadow_scaffolding": True,
            "implements_contract_resolver": False,
            "selected_depth": selected_depth,
            "fallback_reason": fallback_reason,
        },
    ).require_valid()
    return SearchWorkPlanConstructionInput(
        construction_id=f"construction:{contract_id}:runtime-shadow",
        requested_mode_source="run_config_or_run_contract_projection",
        query_shape_assessment=assessment,
        contract_resolution=resolution,
        construction_design=SearchWorkPlanConstructionDesignRecord(
            design_id=f"design:{contract_id}:runtime-shadow",
            future_runtime_consumer="RunKernel.SearchWorkPlan shadow projection",
            closed_surfaces=(
                "QueryPlan behavior",
                "query generation/order/admission",
                "provider/search/retrieval behavior",
                "prompt behavior",
                "citation/final-answer behavior",
                "mode_policy.py",
            ),
            metadata={
                "runtime_shadow_scaffolding": True,
                "phase": "AG-96E1",
                "fallback_reason": fallback_reason,
            },
        ).require_valid(),
        safe_route_facts=route_facts,
        run_authority_contract_ref={
            "contract_id": contract_id,
            "schema_version": contract.get("schema_version"),
        },
        current_date_ref=_safe_ref(runtime_input.current_date_ref),
        passive_mode_policy_snapshot={
            "requested_mode": requested_mode.value,
            "selected_depth": selected_depth,
            "source": "run_config_or_run_contract_projection",
        },
        safe_user_domain_hints=_safe_mapping(runtime_input.safe_user_domain_hints or {}),
        metadata=_safe_mapping(
            {
                "helper": RUNTIME_SHADOW_SEARCH_WORK_PLAN_HELPER,
                "phase": "AG-96E1",
                "runtime_shadow_scaffolding": True,
                "implements_query_shape_classifier": False,
                "implements_contract_resolver": False,
                "fallback_reason": fallback_reason,
                "safe_structured_inputs_only": True,
                "behavior_changed": False,
                "query_plan_behavior_changed": False,
                "provider_search_behavior_changed": False,
                **dict(runtime_input.metadata or {}),
            }
        ),
    )


def _source_requirements(contract: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    requirements = contract.get("source_requirements")
    if not isinstance(requirements, Sequence) or isinstance(requirements, str):
        requirements = contract.get("source_requirement_summary")
    if not isinstance(requirements, Sequence) or isinstance(requirements, str):
        return ()
    return tuple(item for item in requirements if isinstance(item, Mapping))


def _source_obligation_candidates(
    requirements: Sequence[Mapping[str, Any]],
    component_id: str,
) -> tuple[SourceObligationCandidate, ...]:
    candidates: list[SourceObligationCandidate] = []
    for index, requirement in enumerate(requirements, start=1):
        requirement_id = _clean_token(requirement.get("requirement_id")) or f"requirement-{index}"
        kind = _source_obligation_kind(requirement)
        strictness = _strictness(requirement, kind)
        candidates.append(
            SourceObligationCandidate(
                candidate_id=f"obligation:{requirement_id}",
                obligation_id=requirement_id,
                component_ids=(component_id,),
                kind=kind,
                strictness=strictness,
                required_source_class=_clean_token(
                    requirement.get("required_source_class")
                    or requirement.get("source_class")
                    or requirement.get("required_source_tier")
                ),
                currentness_requirement=_clean_token(
                    requirement.get("required_currentness")
                    or requirement.get("currentness_requirement")
                ),
                satisfaction_rule=_clean_text(requirement.get("satisfaction_rule")),
                lower_tier_use=_clean_text(
                    requirement.get("allowed_lower_tier_use")
                    or requirement.get("lower_tier_use")
                ),
                lower_tier_final_satisfaction_allowed=False,
                metadata={
                    "runtime_shadow_scaffolding": True,
                    "run_contract_requirement_kind": _clean_token(
                        requirement.get("requirement_kind")
                        or requirement.get("kind")
                        or requirement.get("source_class")
                    ),
                },
            )
        )
    return tuple(candidates)


def _provider_job_candidates(
    obligations: Sequence[SourceObligationCandidate],
) -> tuple[ProviderJobCandidate, ...]:
    return tuple(
        ProviderJobCandidate(
            candidate_id=f"provider:{obligation.obligation_id}",
            provider_job_id=f"shadow-{obligation.obligation_id}",
            component_ids=obligation.component_ids,
            job_kind=_provider_job_kind(obligation.kind),
            source_obligation_candidate_ids=(obligation.candidate_id,),
            provider_name_neutral=True,
            metadata={
                "runtime_shadow_scaffolding": True,
                "executes_search": False,
                "provider_selection_changed": False,
            },
        )
        for obligation in obligations
    )


def _query_shape_kinds(
    contract: Mapping[str, Any],
    requirements: Sequence[Mapping[str, Any]],
) -> tuple[QueryShapeKind, ...]:
    kinds: list[QueryShapeKind] = [QueryShapeKind.SIMPLE_LOOKUP]
    for requirement in requirements:
        obligation_kind = _source_obligation_kind(requirement)
        if obligation_kind is SourceObligationKind.OFFICIAL_CURRENT:
            kinds.append(QueryShapeKind.OFFICIAL_CURRENT_LOOKUP)
            kinds.append(QueryShapeKind.TIME_SENSITIVE)
        elif obligation_kind is SourceObligationKind.LEGAL_CURRENT_PRIMARY:
            kinds.append(QueryShapeKind.LEGAL_CURRENT_PRIMARY)
            kinds.append(QueryShapeKind.TIME_SENSITIVE)
        elif obligation_kind is SourceObligationKind.CANONICAL_DOCUMENTATION:
            kinds.append(QueryShapeKind.CANONICAL_DOCUMENTATION)
        elif obligation_kind is SourceObligationKind.SOURCE_BOUND_NUMERIC:
            kinds.append(QueryShapeKind.SOURCE_BOUND_NUMERIC)
        elif obligation_kind is SourceObligationKind.CONFLICT_RESOLUTION:
            kinds.append(QueryShapeKind.CONFLICT_LIKELY)
    if _has_conflict_policy(contract):
        kinds.append(QueryShapeKind.CONFLICT_LIKELY)
    return _dedupe(kinds)


def _source_obligation_kind(requirement: Mapping[str, Any]) -> SourceObligationKind:
    raw = str(
        requirement.get("requirement_kind")
        or requirement.get("kind")
        or requirement.get("source_class")
        or requirement.get("required_source_class")
        or ""
    ).casefold()
    if "official" in raw or "current_rules" in raw:
        return SourceObligationKind.OFFICIAL_CURRENT
    if "legal" in raw or "regulatory" in raw:
        return SourceObligationKind.LEGAL_CURRENT_PRIMARY
    if "canonical" in raw or "docs" in raw or "primary_source_documents" in raw:
        return SourceObligationKind.CANONICAL_DOCUMENTATION
    if "source_bound_numeric" in raw or "numeric" in raw:
        return SourceObligationKind.SOURCE_BOUND_NUMERIC
    if "academic" in raw or "peer" in raw:
        return SourceObligationKind.PEER_REVIEWED
    if "user_document" in raw:
        return SourceObligationKind.USER_DOCUMENT
    if "conflict" in raw:
        return SourceObligationKind.CONFLICT_RESOLUTION
    if "reputable" in raw or "secondary" in raw:
        return SourceObligationKind.REPUTABLE_SECONDARY
    return SourceObligationKind.NO_SPECIAL_OBLIGATION


def _strictness(
    requirement: Mapping[str, Any],
    kind: SourceObligationKind,
) -> SourceObligationStrictness:
    if kind in {
        SourceObligationKind.OFFICIAL_CURRENT,
        SourceObligationKind.LEGAL_CURRENT_PRIMARY,
        SourceObligationKind.CANONICAL_DOCUMENTATION,
        SourceObligationKind.SOURCE_BOUND_NUMERIC,
    }:
        return SourceObligationStrictness.REQUIRED
    raw = str(requirement.get("strictness") or "").casefold()
    if raw == SourceObligationStrictness.PREFERRED.value:
        return SourceObligationStrictness.PREFERRED
    if raw == SourceObligationStrictness.REQUIRED.value:
        return SourceObligationStrictness.REQUIRED
    return SourceObligationStrictness.CONTEXTUAL


def _provider_job_kind(kind: SourceObligationKind) -> ProviderJobKind:
    if kind is SourceObligationKind.OFFICIAL_CURRENT:
        return ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION
    if kind in {
        SourceObligationKind.LEGAL_CURRENT_PRIMARY,
        SourceObligationKind.CANONICAL_DOCUMENTATION,
    }:
        return ProviderJobKind.CANONICAL_EXTRACTION
    if kind is SourceObligationKind.SOURCE_BOUND_NUMERIC:
        return ProviderJobKind.FETCH_READ_EXTRACT
    if kind is SourceObligationKind.CONFLICT_RESOLUTION:
        return ProviderJobKind.CONFLICT_CURRENTNESS_CHECK
    return ProviderJobKind.DIRECT_CANDIDATE_SEARCH


def _stop_conditions(
    requirements: Sequence[Mapping[str, Any]],
) -> tuple[StopConditionKind, ...]:
    if requirements:
        return (StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,)
    return (StopConditionKind.COMPONENT_SUFFICIENT,)


def _effective_contract_from_depth(
    selected_depth: str | None,
    requested_mode: SearchMode,
) -> EffectiveContractKind:
    raw = str(selected_depth or requested_mode.value or "").strip().casefold()
    if raw == SearchMode.DEEP.value:
        return EffectiveContractKind.RESEARCH_RECONCILIATION
    if raw == SearchMode.BALANCED.value:
        return EffectiveContractKind.EXPLANATORY
    if raw == SearchMode.FAST.value:
        return EffectiveContractKind.DIRECT_CONSTRAINED
    return EffectiveContractKind.AUTO_UNRESOLVED


def _follow_up_depth(contract: EffectiveContractKind) -> FollowUpDepthPosture:
    if contract is EffectiveContractKind.RESEARCH_RECONCILIATION:
        return FollowUpDepthPosture.LARGER_BOUNDED_LOOP
    if contract is EffectiveContractKind.EXPLANATORY:
        return FollowUpDepthPosture.CONDITIONAL_GAP_DRIVEN
    return FollowUpDepthPosture.NONE_OR_MINIMAL


def _output_posture(contract: EffectiveContractKind) -> OutputPosture:
    if contract is EffectiveContractKind.RESEARCH_RECONCILIATION:
        return OutputPosture.RESOLVED_DEPTH
    if contract is EffectiveContractKind.EXPLANATORY:
        return OutputPosture.COMPACT_EXPLANATORY
    return OutputPosture.DIRECT


def _coerce_search_mode(value: str | None) -> SearchMode:
    raw = str(value or "").strip().casefold()
    for mode in SearchMode:
        if mode.value == raw:
            return mode
    return SearchMode.UNRESOLVED


def _component_subquestion(route_facts: Mapping[str, Any]) -> str:
    topic = _clean_text(
        route_facts.get("core_topic") or route_facts.get("primary_entity"),
        limit=160,
    )
    if topic:
        return f"Represent conservative source-obligation work for {topic}."
    return "Represent conservative source-obligation work after contract synthesis."


def _route_entities(route_facts: Mapping[str, Any]) -> tuple[str, ...]:
    entities: list[str] = []
    for value in (
        route_facts.get("primary_entity"),
        *(route_facts.get("entities") or ()),
    ):
        text = _clean_token(value, limit=120)
        if text and text not in entities:
            entities.append(text)
    return tuple(entities[:8])


def _safe_route_facts(route_projection: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "intent",
        "report_type",
        "image_mode",
        "core_topic",
        "is_academic",
        "query_type",
        "primary_entity",
        "entity_count",
        "router_entity_retry_used",
        "router_original_report_type",
        "router_original_query_type",
    }
    facts = {
        key: route_projection.get(key)
        for key in allowed
        if key in route_projection
    }
    route_ref = route_projection.get("router_query_preparation_ref")
    if isinstance(route_ref, Mapping):
        entities = route_ref.get("entities")
        if isinstance(entities, Sequence) and not isinstance(entities, str):
            facts["entities"] = list(entities)[:8]
    return _safe_mapping(facts)


def _has_conflict_policy(contract: Mapping[str, Any]) -> bool:
    policy = contract.get("conflict_policy")
    return isinstance(policy, Mapping) and any(bool(value) for value in policy.values())


def _safe_ref(value: str | Mapping[str, Any] | None) -> str | Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    return _clean_token(value)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _json_safe(dict(value or {}))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=100)
            if not key_text:
                continue
            normalized = key_text.casefold()
            if normalized in _SENSITIVE_KEYS or normalized.startswith("raw_"):
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:80]]
    return _clean_text(value, limit=300)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _dedupe(values: Sequence[QueryShapeKind]) -> tuple[QueryShapeKind, ...]:
    seen: set[QueryShapeKind] = set()
    out: list[QueryShapeKind] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return tuple(out)


__all__ = [
    "RUNTIME_SHADOW_SEARCH_WORK_PLAN_HELPER",
    "RuntimeShadowSearchWorkPlanInput",
    "build_runtime_shadow_search_work_plan_input",
    "observe_runtime_shadow_search_work_plan_construction",
]
