import ast
import json
from pathlib import Path

import pytest

from core.search_work_plan import (
    AuditJob,
    AuditScope,
    BudgetValue,
    BudgetValuePosture,
    ComponentBudget,
    EffectiveContractDescriptor,
    EffectiveContractKind,
    FollowUpAuthority,
    FollowUpPermission,
    ModeDepthAllowance,
    ProviderJob,
    ProviderJobKind,
    QuantWorkUnit,
    QueryShapeDescriptor,
    QueryShapeKind,
    RemediationPermission,
    RequestedModeDescriptor,
    SearchMode,
    SearchWorkBudget,
    SearchWorkComponent,
    SearchWorkPlan,
    SourceObligation,
    SourceObligationKind,
    StopCondition,
    StopConditionKind,
    StopOutcome,
    SynthesisJob,
    SynthesisScope,
)


def _component_budget(minimum: int = 1, cap: int = 1) -> ComponentBudget:
    return ComponentBudget(
        minimum_viable=BudgetValue(
            value=minimum,
            posture=BudgetValuePosture.COMPONENT_MINIMUM,
            unit="provider_job",
        ),
        cap=BudgetValue(
            value=cap,
            posture=BudgetValuePosture.COMPONENT_CAP,
            unit="provider_job",
        ),
    )


def _official_obligation(obligation_id: str = "official-current") -> SourceObligation:
    return SourceObligation(
        obligation_id=obligation_id,
        kind=SourceObligationKind.OFFICIAL_CURRENT,
        search_constraint="answer-bearing official/current source required",
        currentness_requirement="current at answer time",
        satisfaction_rule="lower-tier sources can only provide bridge hints",
    )


def _base_plan(
    *,
    components: tuple[SearchWorkComponent, ...],
    provider_jobs: tuple[ProviderJob, ...] = (),
    quant_work_units: tuple[QuantWorkUnit, ...] = (),
    synthesis_jobs: tuple[SynthesisJob, ...] = (),
    audit_jobs: tuple[AuditJob, ...] = (),
    requested_mode: SearchMode = SearchMode.FAST,
    contract_kind: EffectiveContractKind = EffectiveContractKind.DIRECT_CONSTRAINED,
    query_kinds: tuple[QueryShapeKind, ...] = (QueryShapeKind.SIMPLE_LOOKUP,),
    follow_up_authority: FollowUpAuthority | None = None,
    stop_conditions: tuple[StopCondition, ...] = (),
) -> SearchWorkPlan:
    return SearchWorkPlan(
        requested_mode=RequestedModeDescriptor(mode=requested_mode),
        effective_contract=EffectiveContractDescriptor(
            contract_kind=contract_kind,
            depth_allowance=(
                ModeDepthAllowance.SHALLOW
                if contract_kind is EffectiveContractKind.DIRECT_CONSTRAINED
                else ModeDepthAllowance.MODERATE
            ),
            follow_up_posture=(
                FollowUpPermission.NOT_ALLOWED
                if contract_kind is EffectiveContractKind.DIRECT_CONSTRAINED
                else FollowUpPermission.CONDITIONAL
            ),
        ),
        query_shape=QueryShapeDescriptor(kinds=query_kinds, component_count_hint=len(components)),
        components=components,
        provider_jobs=provider_jobs,
        quant_work_units=quant_work_units,
        synthesis_jobs=synthesis_jobs,
        audit_jobs=audit_jobs,
        budget=SearchWorkBudget(base_mode_budget_posture=f"{requested_mode.value}_mode_bound"),
        follow_up_authority=follow_up_authority
        or FollowUpAuthority(permission=FollowUpPermission.NOT_ALLOWED),
        stop_conditions=stop_conditions,
    )


def test_simple_official_current_lookup_representation_is_json_safe() -> None:
    component = SearchWorkComponent(
        component_id="fee",
        user_facing_subquestion="Find the current filing fee.",
        source_obligations=(_official_obligation(),),
        required_provider_jobs=(ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,),
        per_component_budget=_component_budget(),
    )
    plan = _base_plan(
        components=(component,),
        provider_jobs=(
            ProviderJob(
                provider_job_id="official-acquisition",
                job_kind=ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,
                component_ids=("fee",),
                source_obligation_ids=("official-current",),
            ),
        ),
        query_kinds=(
            QueryShapeKind.SIMPLE_LOOKUP,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
            QueryShapeKind.TIME_SENSITIVE,
        ),
    ).require_valid()

    payload = plan.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["requested_mode"]["mode"] == "fast"
    assert payload["effective_contract"]["contract_kind"] == "direct_constrained"
    assert payload["components"][0]["source_obligations"][0]["kind"] == "official_current"
    assert payload["provider_jobs"][0]["job_kind"] == "official_candidate_acquisition"
    assert payload["runtime_consumed"] is False
    assert payload["prompt_behavior_changed"] is False
    assert payload["provider_search_behavior_changed"] is False
    assert encoded
    assert SearchWorkPlan.from_dict(payload).to_dict()["schema_version"] == payload["schema_version"]


def test_multipart_comparison_represents_component_breadth_without_crude_global_query_field() -> None:
    brave_component = SearchWorkComponent(
        component_id="brave-ios",
        user_facing_subquestion="Summarize Brave privacy defaults on iOS.",
        entities=("Brave", "iOS"),
        source_obligations=(
            SourceObligation(
                obligation_id="brave-docs",
                kind=SourceObligationKind.CANONICAL_DOCUMENTATION,
            ),
        ),
        required_provider_jobs=(ProviderJobKind.CANONICAL_EXTRACTION,),
        per_component_budget=_component_budget(minimum=1, cap=2),
    )
    safari_component = SearchWorkComponent(
        component_id="safari-ios",
        user_facing_subquestion="Summarize Safari privacy defaults on iOS.",
        entities=("Safari", "iOS"),
        source_obligations=(
            SourceObligation(
                obligation_id="safari-docs",
                kind=SourceObligationKind.CANONICAL_DOCUMENTATION,
            ),
        ),
        required_provider_jobs=(ProviderJobKind.CANONICAL_EXTRACTION,),
        per_component_budget=_component_budget(minimum=1, cap=2),
    )
    plan = _base_plan(
        components=(brave_component, safari_component),
        requested_mode=SearchMode.BALANCED,
        contract_kind=EffectiveContractKind.EXPLANATORY,
        query_kinds=(QueryShapeKind.MULTIPART, QueryShapeKind.COMPARATIVE),
    ).require_valid()

    payload = plan.to_dict()
    component_ids = [component["component_id"] for component in payload["components"]]

    assert component_ids == ["brave-ios", "safari-ios"]
    assert len(set(component_ids)) == 2
    assert all(component["per_component_budget"]["minimum_viable"]["value"] == 1 for component in payload["components"])
    assert "global_query" not in json.dumps(payload, sort_keys=True)


def test_quantitative_comparison_represents_source_bound_numeric_work_without_execution() -> None:
    component = SearchWorkComponent(
        component_id="aircraft-cost",
        user_facing_subquestion="Compare aircraft cost per passenger mile.",
        source_obligations=(
            SourceObligation(
                obligation_id="source-bound-values",
                kind=SourceObligationKind.SOURCE_BOUND_NUMERIC,
                satisfaction_rule="inputs must be source-bound before calculation",
            ),
        ),
        required_provider_jobs=(ProviderJobKind.DIRECT_CANDIDATE_SEARCH,),
        per_component_budget=_component_budget(minimum=2, cap=4),
    )
    quant_unit = QuantWorkUnit(
        quant_unit_id="cost-per-passenger-mile",
        component_ids=("aircraft-cost",),
        target_metric="cost per passenger mile",
        required_variables=("operating cost", "seat count", "load factor", "stage length"),
        source_bound_values_needed=("operating cost", "capacity", "utilization"),
        unsupported_values=("fuel price",),
        allowed_calculations=("divide source-bound cost by source-bound passenger miles",),
        assumptions_needed=("route profile", "configuration"),
        high_stakes_quant=True,
        direct_use_eligible=False,
        requires_synthesis=True,
    )
    plan = _base_plan(
        components=(component,),
        quant_work_units=(quant_unit,),
        requested_mode=SearchMode.BALANCED,
        contract_kind=EffectiveContractKind.EXPLANATORY,
        query_kinds=(
            QueryShapeKind.QUANTITATIVE_COMPARISON,
            QueryShapeKind.SOURCE_BOUND_NUMERIC,
            QueryShapeKind.NORMALIZATION_REQUIRED,
        ),
    ).require_valid()

    payload = plan.to_dict()
    unit = payload["quant_work_units"][0]

    assert "quantitative_comparison" in payload["query_shape"]["kinds"]
    assert unit["target_metric"] == "cost per passenger mile"
    assert "operating cost" in unit["required_variables"]
    assert "fuel price" in unit["unsupported_values"]
    assert unit["assumptions_needed"] == ["route profile", "configuration"]
    assert unit["executes_calculations"] is False
    assert unit["executes_code"] is False
    assert not hasattr(quant_unit, "execute")


def test_balanced_follow_up_gap_authority_points_to_canonical_judgments() -> None:
    component = SearchWorkComponent(
        component_id="generic-official-page-gap",
        user_facing_subquestion="Find the answer-bearing official page after a generic page is found.",
        source_obligations=(_official_obligation(),),
        per_component_budget=_component_budget(minimum=1, cap=3),
        stop_conditions=(
            StopCondition(
                condition=StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,
                outcome=StopOutcome.ESCALATE_SUGGESTION,
                description="Official page is generic, so follow-up requires judgment authorization.",
            ),
        ),
    )
    follow_up = FollowUpAuthority(
        permission=FollowUpPermission.CONDITIONAL,
        authorizers=("RunAuthority", "SearchJudgment", "SufficiencyJudgment"),
        allow_conditions=("named source gap", "mode budget remains"),
        block_conditions=("budget exhausted", "required inference exceeds Balanced"),
    )
    plan = _base_plan(
        components=(component,),
        requested_mode=SearchMode.BALANCED,
        contract_kind=EffectiveContractKind.EXPLANATORY,
        query_kinds=(QueryShapeKind.OFFICIAL_CURRENT_LOOKUP, QueryShapeKind.MODE_MISMATCH_POSSIBLE),
        follow_up_authority=follow_up,
        stop_conditions=(
            StopCondition(
                condition=StopConditionKind.MODE_MISMATCH,
                outcome=StopOutcome.QUALIFY,
            ),
        ),
    ).require_valid()

    payload = plan.to_dict()
    authorizers = payload["follow_up_authority"]["authorizers"]

    assert payload["follow_up_authority"]["permission"] == "conditional"
    assert set(authorizers) == {"RunAuthority", "SearchJudgment", "SufficiencyJudgment"}
    assert "Analyst" not in authorizers
    assert "Scout" not in authorizers
    assert payload["stop_conditions"][0]["condition"] == "mode_mismatch"


def test_deep_audit_reconciliation_job_is_bounded_and_passive() -> None:
    component = SearchWorkComponent(
        component_id="currentness-conflict",
        user_facing_subquestion="Reconcile conflicting currentness signals.",
        source_obligations=(
            SourceObligation(
                obligation_id="conflict-resolution",
                kind=SourceObligationKind.CONFLICT_RESOLUTION,
            ),
        ),
        per_component_budget=_component_budget(minimum=2, cap=5),
    )
    audit = AuditJob(
        audit_job_id="deep-currentness-audit",
        component_ids=("currentness-conflict",),
        audit_scope=AuditScope.SOURCE_CONFLICT_RECONCILIATION,
        claim_types=("effective date", "current fee"),
        assumptions_to_test=("newer page supersedes older notice",),
        source_conflict_checks=("official notice vs current table",),
        mode_allowed=(SearchMode.DEEP,),
        remediation_permission=RemediationPermission.CONDITIONAL_PASSIVE,
    )
    plan = _base_plan(
        components=(component,),
        audit_jobs=(audit,),
        requested_mode=SearchMode.DEEP,
        contract_kind=EffectiveContractKind.RESEARCH_RECONCILIATION,
        query_kinds=(QueryShapeKind.CONFLICT_LIKELY, QueryShapeKind.TIME_SENSITIVE),
    ).require_valid()

    audit_payload = plan.to_dict()["audit_jobs"][0]

    assert audit_payload["bounded"] is True
    assert audit_payload["passive"] is True
    assert audit_payload["open_ended_loop"] is False
    assert audit_payload["remediation_permission"] == "conditional_passive"


def test_invariants_report_duplicate_ids_missing_refs_bad_budgets_and_bad_authorizers() -> None:
    component = SearchWorkComponent(
        component_id="dup",
        user_facing_subquestion="A duplicate component.",
        per_component_budget=_component_budget(minimum=3, cap=1),
    )
    invalid = _base_plan(
        components=(component, component),
        provider_jobs=(
            ProviderJob(
                provider_job_id="missing-provider-ref",
                job_kind=ProviderJobKind.SEMANTIC_RECALL,
                component_ids=("missing",),
            ),
        ),
        quant_work_units=(
            QuantWorkUnit(
                quant_unit_id="missing-quant-ref",
                component_ids=("missing",),
                target_metric="metric",
            ),
        ),
        synthesis_jobs=(
            SynthesisJob(
                synthesis_job_id="missing-synthesis-ref",
                component_ids=("missing",),
                synthesis_scope=SynthesisScope.GAP_VISIBILITY,
            ),
        ),
        audit_jobs=(
            AuditJob(
                audit_job_id="missing-audit-ref",
                component_ids=("missing",),
                audit_scope=AuditScope.CLAIM_CHALLENGE,
            ),
        ),
        follow_up_authority=FollowUpAuthority(
            permission=FollowUpPermission.CONDITIONAL,
            authorizers=("Analyst", "Scout"),
        ),
    )

    errors = invalid.validate().errors

    assert any("duplicate component_id" in error for error in errors)
    assert any("provider job missing-provider-ref references missing component missing" in error for error in errors)
    assert any("quant work unit missing-quant-ref references missing component missing" in error for error in errors)
    assert any("synthesis job missing-synthesis-ref references missing component missing" in error for error in errors)
    assert any("audit job missing-audit-ref references missing component missing" in error for error in errors)
    assert any("minimum viable budget exceeds component cap" in error for error in errors)
    assert any("bounded executors cannot authorize follow-up" in error for error in errors)
    with pytest.raises(ValueError, match="duplicate component_id"):
        invalid.require_valid()


def test_provider_job_requires_no_provider_hierarchy_and_serialization_omits_raw_payload_fields() -> None:
    component = SearchWorkComponent(
        component_id="neutral-job",
        user_facing_subquestion="Use a provider-neutral candidate search job.",
        metadata={"raw_prompt": "do not serialize this"},
    )
    provider_job = ProviderJob(
        provider_job_id="neutral-direct-search",
        job_kind=ProviderJobKind.DIRECT_CANDIDATE_SEARCH,
        component_ids=("neutral-job",),
        provider_metadata={
            "inert_label": "candidate source can be selected later",
            "raw_provider_payload": {"private_marker": "never include"},
        },
    )
    plan = _base_plan(
        components=(component,),
        provider_jobs=(provider_job,),
    ).require_valid()

    payload = plan.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["provider_jobs"][0]["provider_name_neutral"] is True
    assert "provider_hierarchy" not in payload["provider_jobs"][0]
    assert "raw_prompt" not in encoded
    assert "raw_provider_payload" not in encoded
    assert "never include" not in encoded


def test_search_work_plan_module_has_passive_import_and_call_boundary() -> None:
    module_path = Path(__file__).parents[1] / "core" / "search_work_plan.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "pipeline_orchestrator",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.runtime_prompt_assembly",
        "core.prompts",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "brave_reconnaissance",
        "fetch_page",
        "fetch_url_text",
    }
    imported_names: set[str] = set()
    called_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint(forbidden_calls)
    assert "pipeline_orchestrator" not in source
    assert "prompt assembly" not in source.lower()
