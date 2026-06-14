"""Passive SearchWorkPlan construction adapter for AG-96C6.

This module translates explicit safe passive records into a passive
SearchWorkPlan. It does not classify queries, generate query text, call models,
call providers, retrieve evidence, mutate RunKernel state, or expose a runtime
consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from core.query_shape_contract_resolution import (
    AuditJobCandidate,
    ComponentCandidate,
    ContractResolutionRecord,
    FollowUpDepthPosture,
    ProviderJobCandidate,
    QuantWorkCandidate,
    QueryShapeAssessment,
    SearchWorkPlanConstructionDesignRecord,
    SourceObligationCandidate,
    StopEscalateRefusePosture,
)
from core.run_kernel import (
    SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)
from core.search_work_plan import (
    AuditJob,
    AuthorityRef,
    BudgetExhaustedPosture,
    EffectiveContractDescriptor,
    EffectiveContractKind,
    FollowUpAuthority,
    FollowUpPermission,
    ModeDepthAllowance,
    ModeMismatchPosture,
    ProviderJob,
    ProviderJobKind,
    QuantWorkUnit,
    QueryShapeDescriptor,
    RemediationPermission,
    RequestedModeDescriptor,
    SearchMode,
    SearchWorkBudget,
    SearchWorkComponent,
    SearchWorkPlan,
    SourceObligation,
    StopCondition,
    StopConditionKind,
    StopOutcome,
)

SEARCH_WORK_PLAN_CONSTRUCTION_SCHEMA_VERSION = "search_work_plan_construction_ag96c6_v1"
SEARCH_WORK_PLAN_CONSTRUCTION_TRACE_KEY = "search_work_plan_construction"

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
_SENSITIVE_KEY_FRAGMENTS = ("api_key", "secret", "token", "password")


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return (
        normalized.startswith("raw_")
        or normalized in _SENSITIVE_KEYS
        or any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)
    )


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _text_tuple(value: Sequence[Any] | None, *, limit: int = 160) -> tuple[str, ...]:
    out: list[str] = []
    for item in value or ():
        text = _clean_token(item, limit=limit)
        if text:
            out.append(text)
    return tuple(out)


def _safe_metadata(*items: Mapping[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        if isinstance(item, Mapping):
            safe = _json_safe(item)
            if isinstance(safe, Mapping):
                merged.update(dict(safe))
    return merged


def _safe_metadata_values(
    metadata: Mapping[str, Any],
    key: str,
    *,
    limit: int = 160,
) -> tuple[str, ...]:
    if not isinstance(metadata, Mapping):
        return ()
    value = metadata.get(key)
    if isinstance(value, str):
        return _text_tuple((value,), limit=limit)
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return _text_tuple(value, limit=limit)
    return ()


def _depth_allowance(contract: EffectiveContractKind) -> ModeDepthAllowance:
    if contract is EffectiveContractKind.RESEARCH_RECONCILIATION:
        return ModeDepthAllowance.DEEP
    if contract is EffectiveContractKind.EXPLANATORY:
        return ModeDepthAllowance.MODERATE
    if contract is EffectiveContractKind.DIRECT_CONSTRAINED:
        return ModeDepthAllowance.SHALLOW
    return ModeDepthAllowance.UNRESOLVED


def _follow_up_permission(depth: FollowUpDepthPosture) -> FollowUpPermission:
    if depth is FollowUpDepthPosture.LARGER_BOUNDED_LOOP:
        return FollowUpPermission.CONDITIONAL
    if depth is FollowUpDepthPosture.CONDITIONAL_GAP_DRIVEN:
        return FollowUpPermission.CONDITIONAL
    return FollowUpPermission.NOT_ALLOWED


def _stop_outcome(posture: StopEscalateRefusePosture) -> StopOutcome:
    if posture is StopEscalateRefusePosture.ESCALATE_SUGGESTED:
        return StopOutcome.ESCALATE_SUGGESTION
    if posture is StopEscalateRefusePosture.REFUSE_OR_FAIL_CLOSED:
        return StopOutcome.FAIL_CLOSED
    if posture is StopEscalateRefusePosture.QUALIFY_IF_UNSATISFIED:
        return StopOutcome.QUALIFY
    return StopOutcome.STOP


def _safe_ref_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "contract_id",
            "run_authority_contract_id",
            "authority_id",
            "ref",
            "id",
            "schema_version",
        ):
            text = _clean_token(value.get(key), limit=180)
            if text and not _is_sensitive_key(key):
                return text
        return None
    return _clean_token(value, limit=180)


@dataclass(frozen=True, slots=True)
class SearchWorkPlanConstructionInput:
    construction_id: str
    requested_mode_source: str
    query_shape_assessment: QueryShapeAssessment
    contract_resolution: ContractResolutionRecord
    construction_design: SearchWorkPlanConstructionDesignRecord
    safe_route_facts: Mapping[str, Any] = field(default_factory=dict)
    run_authority_contract_ref: str | Mapping[str, Any] | None = None
    current_date_ref: str | Mapping[str, Any] | None = None
    passive_mode_policy_snapshot: Mapping[str, Any] = field(default_factory=dict)
    safe_user_domain_hints: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    schema_version: str = SEARCH_WORK_PLAN_CONSTRUCTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.construction_id):
            raise ValueError("construction input requires construction_id")
        object.__setattr__(
            self,
            "requested_mode_source",
            _clean_token(self.requested_mode_source) or "user_or_ui",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_key": SEARCH_WORK_PLAN_CONSTRUCTION_TRACE_KEY,
            "construction_id": _clean_token(self.construction_id),
            "requested_mode_source": _clean_token(self.requested_mode_source),
            "passive": bool(self.passive),
            "runtime_consumed": False,
            "constructs_search_work_plan": True,
            "safe_structured_inputs_only": True,
            "query_shape_assessment": self.query_shape_assessment.to_dict(),
            "contract_resolution": self.contract_resolution.to_dict(),
            "construction_design": self.construction_design.to_dict(),
            "safe_route_facts": _json_safe(self.safe_route_facts),
            "run_authority_contract_ref": _json_safe(_safe_ref_id(self.run_authority_contract_ref)),
            "current_date_ref": _json_safe(_safe_ref_id(self.current_date_ref)),
            "passive_mode_policy_snapshot": _json_safe(self.passive_mode_policy_snapshot),
            "safe_user_domain_hints": _json_safe(self.safe_user_domain_hints),
            "metadata": _json_safe(self.metadata),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SEARCH_WORK_PLAN_CONSTRUCTION_TRACE_KEY: self.to_dict()}


@dataclass(frozen=True, slots=True)
class SearchWorkPlanConstructionResult:
    construction_id: str
    search_work_plan: SearchWorkPlan
    validation: Mapping[str, Any]
    warnings: tuple[str, ...] = ()
    constructed: bool = True
    runtime_consumed: bool = False
    behavior_changed: bool = False
    prompt_behavior_changed: bool = False
    provider_search_behavior_changed: bool = False
    query_plan_behavior_changed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SEARCH_WORK_PLAN_CONSTRUCTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", _text_tuple(self.warnings, limit=300))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_key": SEARCH_WORK_PLAN_CONSTRUCTION_TRACE_KEY,
            "construction_id": _clean_token(self.construction_id),
            "constructed": bool(self.constructed),
            "runtime_consumed": bool(self.runtime_consumed),
            "behavior_changed": bool(self.behavior_changed),
            "prompt_behavior_changed": bool(self.prompt_behavior_changed),
            "provider_search_behavior_changed": bool(
                self.provider_search_behavior_changed
            ),
            "query_plan_behavior_changed": bool(self.query_plan_behavior_changed),
            "search_work_plan": self.search_work_plan.to_dict(),
            "validation": _json_safe(self.validation),
            "warnings": list(self.warnings),
            "metadata": _json_safe(self.metadata),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SEARCH_WORK_PLAN_CONSTRUCTION_TRACE_KEY: self.to_dict()}


def construct_search_work_plan_from_records(
    input_record: SearchWorkPlanConstructionInput,
) -> SearchWorkPlanConstructionResult:
    """Construct a passive SearchWorkPlan from already-safe structured records."""

    assessment = input_record.query_shape_assessment
    resolution = input_record.contract_resolution
    design = input_record.construction_design

    assessment_validation = assessment.validate()
    resolution_validation = resolution.validate()
    design_validation = design.validate()

    warnings: list[str] = []
    if assessment.social_signal_candidates:
        warnings.append(
            "social/perception candidates are deferred and do not satisfy "
            "official, legal, factual, canonical, or source-bound obligations"
        )

    components = _construct_components(
        assessment.component_candidates,
        assessment.source_obligation_candidates,
        assessment.provider_job_candidates,
        assessment.stop_condition_candidates,
        resolution,
    )
    provider_jobs = _construct_provider_jobs(
        assessment.provider_job_candidates,
        assessment.source_obligation_candidates,
    )
    quant_units = tuple(
        _construct_quant_work_unit(candidate)
        for candidate in assessment.quant_work_candidates
    )
    audit_jobs = tuple(
        _construct_audit_job(candidate, resolution)
        for candidate in assessment.audit_job_candidates
    )
    stop_conditions = _construct_stop_conditions(assessment, resolution)

    plan = SearchWorkPlan(
        requested_mode=RequestedModeDescriptor(
            mode=resolution.requested_mode,
            source=input_record.requested_mode_source,
            mode_mismatch_posture=resolution.mode_mismatch_posture,
            rationale=resolution.rationale,
        ),
        effective_contract=EffectiveContractDescriptor(
            contract_kind=resolution.effective_contract,
            governing_authority="RunKernel.RunAuthority",
            depth_allowance=_depth_allowance(resolution.effective_contract),
            follow_up_posture=_follow_up_permission(resolution.allowed_follow_up_depth),
            budget_posture=f"{resolution.effective_contract.value}_passive",
            output_depth_target=resolution.output_posture.value,
            mismatch_posture=resolution.mode_mismatch_posture,
        ),
        query_shape=QueryShapeDescriptor(
            kinds=assessment.query_shape_kinds,
            component_count_hint=len(assessment.component_candidates),
            normalization_notes=assessment.normalization_notes,
            ambiguity_notes=assessment.ambiguity_notes,
            metadata={
                "assessment_id": assessment.assessment_id,
                "assessment_confidence": assessment.assessment_confidence.value,
                "assessment_posture": assessment.assessment_posture.value,
                "first_pass_evidence_needed": assessment.first_pass_evidence_needed,
            },
        ),
        components=components,
        provider_jobs=provider_jobs,
        quant_work_units=quant_units,
        synthesis_jobs=(),
        audit_jobs=audit_jobs,
        budget=SearchWorkBudget(
            base_mode_budget_posture=f"{resolution.requested_mode.value}_mode_bound",
            budget_exhausted_posture=BudgetExhaustedPosture.QUALIFY,
            metadata={
                "passive_mode_policy_snapshot": input_record.passive_mode_policy_snapshot,
                "effective_contract": resolution.effective_contract.value,
            },
        ),
        follow_up_authority=_construct_follow_up_authority(resolution),
        stop_conditions=stop_conditions,
        authority_refs=_construct_authority_refs(input_record),
        planning_posture="passive_construction_adapter_skeleton",
        passive=True,
        metadata={
            "construction_id": input_record.construction_id,
            "assessment_id": assessment.assessment_id,
            "resolution_id": resolution.resolution_id,
            "design_id": design.design_id,
            "current_date_ref": _safe_ref_id(input_record.current_date_ref),
            "safe_route_facts": input_record.safe_route_facts,
            "safe_user_domain_hints": input_record.safe_user_domain_hints,
            "construction_metadata": input_record.metadata,
            "runtime_consumed": False,
        },
    )
    plan_validation = plan.validate()
    validation = {
        "ok": (
            assessment_validation.ok
            and resolution_validation.ok
            and design_validation.ok
            and plan_validation.ok
        ),
        "query_shape_assessment": assessment_validation.to_dict(),
        "contract_resolution": resolution_validation.to_dict(),
        "construction_design": design_validation.to_dict(),
        "search_work_plan": plan_validation.to_dict(),
    }
    return SearchWorkPlanConstructionResult(
        construction_id=input_record.construction_id,
        search_work_plan=plan,
        validation=validation,
        warnings=tuple(warnings),
        metadata={
            "input_schema_version": input_record.schema_version,
            "safe_structured_inputs_only": True,
            "runtime_integration": False,
        },
    )


def observe_search_work_plan_construction(
    action: AuthorizedAction,
    input_record: SearchWorkPlanConstructionInput,
) -> Observation:
    """Return the RunKernel observation for an authorized shadow construction."""

    validate_authorized_action(
        action,
        action_type=ActionType.SEARCH_WORK_PLAN_CONSTRUCT,
        stage=SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
        expected_observation_type=ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED,
    )
    result = construct_search_work_plan_from_records(input_record)
    return Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED,
        status=RunStageStatus.COMPLETED,
        payload={
            "construction_result": result.to_dict(),
            "search_work_plan_projection": result.search_work_plan.to_dict(),
            "validation": result.validation,
        },
    )


def _construct_components(
    component_candidates: Sequence[ComponentCandidate],
    obligation_candidates: Sequence[SourceObligationCandidate],
    provider_candidates: Sequence[ProviderJobCandidate],
    stop_condition_candidates: Sequence[StopConditionKind],
    resolution: ContractResolutionRecord,
) -> tuple[SearchWorkComponent, ...]:
    return tuple(
        SearchWorkComponent(
            component_id=candidate.component_id,
            user_facing_subquestion=candidate.user_facing_subquestion,
            entities=candidate.entities,
            anchors=candidate.entities,
            source_obligations=_obligations_for_component(
                candidate,
                obligation_candidates,
            ),
            required_provider_jobs=_provider_job_kinds_for_component(
                candidate,
                provider_candidates,
            ),
            mode_depth_allowance=_depth_allowance(resolution.effective_contract),
            stop_conditions=tuple(
                StopCondition(
                    condition=condition,
                    outcome=_stop_outcome(resolution.stop_escalate_refuse_posture),
                    component_id=candidate.component_id,
                )
                for condition in stop_condition_candidates
            ),
            metadata=_safe_metadata(
                candidate.metadata,
                {
                    "candidate_id": candidate.candidate_id,
                    "normalization_notes": candidate.normalization_notes,
                },
            ),
        )
        for candidate in component_candidates
    )


def _obligations_for_component(
    component: ComponentCandidate,
    obligation_candidates: Sequence[SourceObligationCandidate],
) -> tuple[SourceObligation, ...]:
    allowed_candidate_ids = set(component.source_obligation_candidate_ids)
    obligations: list[SourceObligation] = []
    for candidate in obligation_candidates:
        applies_by_component = component.component_id in candidate.component_ids
        applies_by_id = candidate.candidate_id in allowed_candidate_ids
        if not applies_by_component and not applies_by_id:
            continue
        obligations.append(
            SourceObligation(
                obligation_id=candidate.obligation_id,
                kind=candidate.kind,
                strictness=candidate.strictness,
                search_constraint=candidate.required_source_class,
                currentness_requirement=candidate.currentness_requirement,
                satisfaction_rule=candidate.satisfaction_rule,
                lower_tier_use=candidate.lower_tier_use,
                metadata=_safe_metadata(
                    candidate.metadata,
                    {
                        "candidate_id": candidate.candidate_id,
                        "lower_tier_final_satisfaction_allowed": (
                            candidate.lower_tier_final_satisfaction_allowed
                        ),
                    },
                ),
            )
        )
    return tuple(obligations)


def _provider_job_kinds_for_component(
    component: ComponentCandidate,
    provider_candidates: Sequence[ProviderJobCandidate],
) -> tuple[ProviderJobKind, ...]:
    allowed_candidate_ids = set(component.provider_job_candidate_ids)
    kinds: list[ProviderJobKind] = []
    seen: set[ProviderJobKind] = set()
    for candidate in provider_candidates:
        applies_by_component = component.component_id in candidate.component_ids
        applies_by_id = candidate.candidate_id in allowed_candidate_ids
        if (applies_by_component or applies_by_id) and candidate.job_kind not in seen:
            seen.add(candidate.job_kind)
            kinds.append(candidate.job_kind)
    return tuple(kinds)


def _construct_provider_jobs(
    provider_candidates: Sequence[ProviderJobCandidate],
    obligation_candidates: Sequence[SourceObligationCandidate],
) -> tuple[ProviderJob, ...]:
    obligation_id_by_candidate = {
        candidate.candidate_id: candidate.obligation_id
        for candidate in obligation_candidates
    }
    return tuple(
        ProviderJob(
            provider_job_id=candidate.provider_job_id,
            job_kind=candidate.job_kind,
            component_ids=candidate.component_ids,
            source_obligation_ids=tuple(
                obligation_id_by_candidate[candidate_id]
                for candidate_id in candidate.source_obligation_candidate_ids
                if candidate_id in obligation_id_by_candidate
            ),
            job_posture="planned_passive_not_executed",
            metadata=_safe_metadata(
                candidate.metadata,
                {
                    "candidate_id": candidate.candidate_id,
                    "provider_name_neutral": candidate.provider_name_neutral,
                    "executes_search": False,
                },
            ),
        )
        for candidate in provider_candidates
    )


def _construct_quant_work_unit(candidate: QuantWorkCandidate) -> QuantWorkUnit:
    return QuantWorkUnit(
        quant_unit_id=candidate.quant_unit_id,
        component_ids=candidate.component_ids,
        target_metric=candidate.target_metric,
        required_variables=candidate.required_variables,
        source_bound_values_needed=candidate.source_bound_values_needed,
        unsupported_values=_safe_metadata_values(candidate.metadata, "unsupported_values"),
        allowed_calculations=candidate.allowed_calculations,
        assumptions_needed=candidate.assumptions_needed,
        high_stakes_quant=bool(candidate.metadata.get("high_stakes_quant", False)),
        direct_use_eligible=False,
        requires_synthesis=True,
        metadata=_safe_metadata(
            candidate.metadata,
            {
                "candidate_id": candidate.candidate_id,
                "executes_calculations": False,
                "executes_code": False,
            },
        ),
    )


def _construct_audit_job(
    candidate: AuditJobCandidate,
    resolution: ContractResolutionRecord,
) -> AuditJob:
    mode_allowed = (SearchMode.DEEP,)
    if resolution.effective_contract is not EffectiveContractKind.RESEARCH_RECONCILIATION:
        mode_allowed = (resolution.requested_mode,)
    return AuditJob(
        audit_job_id=candidate.audit_job_id,
        component_ids=candidate.component_ids,
        audit_scope=candidate.audit_scope,
        claim_types=candidate.claim_types,
        assumptions_to_test=candidate.assumptions_to_test,
        source_conflict_checks=_safe_metadata_values(
            candidate.metadata,
            "source_conflict_checks",
            limit=220,
        ),
        mode_allowed=mode_allowed,
        remediation_permission=(
            candidate.remediation_permission
            if candidate.remediation_permission is RemediationPermission.CONDITIONAL_PASSIVE
            else RemediationPermission.CONDITIONAL_PASSIVE
        ),
        metadata=_safe_metadata(
            candidate.metadata,
            {
                "candidate_id": candidate.candidate_id,
                "bounded": True,
                "passive": True,
                "open_ended_loop": False,
            },
        ),
    )


def _construct_follow_up_authority(
    resolution: ContractResolutionRecord,
) -> FollowUpAuthority:
    permission = _follow_up_permission(resolution.allowed_follow_up_depth)
    allow_conditions: tuple[str, ...] = ()
    block_conditions = ("bounded executors cannot authorize follow-up",)
    if permission is FollowUpPermission.CONDITIONAL:
        allow_conditions = (
            "RunAuthority/SearchJudgment/SufficiencyJudgment authorize a named gap",
        )
        block_conditions = block_conditions + (
            "selected mode or budget does not authorize additional depth",
        )
    return FollowUpAuthority(
        permission=permission,
        authorizers=resolution.follow_up_authorizers,
        allow_conditions=allow_conditions,
        block_conditions=block_conditions,
        notes="Passive construction only; no follow-up search is authorized.",
    )


def _construct_stop_conditions(
    assessment: QueryShapeAssessment,
    resolution: ContractResolutionRecord,
) -> tuple[StopCondition, ...]:
    outcome = _stop_outcome(resolution.stop_escalate_refuse_posture)
    conditions: list[StopCondition] = [
        StopCondition(
            condition=condition,
            outcome=outcome,
            description="Passive stop condition candidate from query-shape assessment.",
        )
        for condition in assessment.stop_condition_candidates
    ]
    if resolution.mode_mismatch_posture is not ModeMismatchPosture.NONE:
        conditions.append(
            StopCondition(
                condition=StopConditionKind.MODE_MISMATCH,
                outcome=StopOutcome.QUALIFY,
                description=resolution.mode_mismatch_posture.value,
            )
        )
    if resolution.mode_mismatch_posture in {
        ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT,
        ModeMismatchPosture.QUALIFY_OR_REFUSE,
        ModeMismatchPosture.ESCALATE_SUGGESTED,
    }:
        conditions.append(
            StopCondition(
                condition=StopConditionKind.REQUIRED_INFERENCE_EXCEEDS_SELECTED_MODE,
                outcome=StopOutcome.ESCALATE_SUGGESTION,
                description="Selected mode must not silently spend a deeper budget.",
            )
        )
    return tuple(conditions)


def _construct_authority_refs(
    input_record: SearchWorkPlanConstructionInput,
) -> tuple[AuthorityRef, ...]:
    refs = [
        AuthorityRef(
            authority_id=input_record.construction_id,
            authority_name="SearchWorkPlanConstructionInput",
            role="passive construction input record",
        ),
        AuthorityRef(
            authority_id=input_record.query_shape_assessment.assessment_id,
            authority_name="QueryShapeAssessment",
            role="passive query-shape source record",
        ),
        AuthorityRef(
            authority_id=input_record.contract_resolution.resolution_id,
            authority_name="ContractResolutionRecord",
            role="passive RunAuthority contract-resolution source record",
        ),
        AuthorityRef(
            authority_id=input_record.construction_design.design_id,
            authority_name="SearchWorkPlanConstructionDesignRecord",
            role="passive construction design source record",
        ),
    ]
    contract_ref = _safe_ref_id(input_record.run_authority_contract_ref)
    if contract_ref:
        refs.append(
            AuthorityRef(
                authority_id=contract_ref,
                authority_name="RunAuthorityContract",
                role="safe inert contract reference only",
            )
        )
    return tuple(refs)


__all__ = [
    "SEARCH_WORK_PLAN_CONSTRUCTION_SCHEMA_VERSION",
    "SEARCH_WORK_PLAN_CONSTRUCTION_TRACE_KEY",
    "SearchWorkPlanConstructionInput",
    "SearchWorkPlanConstructionResult",
    "construct_search_work_plan_from_records",
    "observe_search_work_plan_construction",
]
