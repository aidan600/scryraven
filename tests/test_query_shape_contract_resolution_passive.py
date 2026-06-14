from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.query_shape_contract_resolution import (
    AuditJobCandidate,
    ComponentCandidate,
    ContractResolutionRecord,
    FollowUpDepthPosture,
    OutputPosture,
    ProviderJobCandidate,
    QuantWorkCandidate,
    QueryShapeAssessment,
    SearchWorkPlanConstructionDesignRecord,
    SocialSignalCandidate,
    SourceObligationCandidate,
    StopEscalateRefusePosture,
)
from core.search_work_plan import (
    AuditScope,
    EffectiveContractKind,
    ModeMismatchPosture,
    ProviderJobKind,
    QueryShapeKind,
    RemediationPermission,
    SearchMode,
    SourceObligationKind,
    SourceObligationStrictness,
    StopConditionKind,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "query_shape_contract_resolution.py"


def _component(
    component_id: str = "primary-answer",
    *,
    candidate_id: str | None = None,
    subquestion: str = "Find the answer-bearing source.",
) -> ComponentCandidate:
    return ComponentCandidate(
        candidate_id=candidate_id or f"component:{component_id}",
        component_id=component_id,
        user_facing_subquestion=subquestion,
    )


def _official_obligation(
    component_id: str = "primary-answer",
    *,
    candidate_id: str = "obligation:official-current",
    strictness: SourceObligationStrictness = SourceObligationStrictness.REQUIRED,
    lower_tier_final_satisfaction_allowed: bool = False,
) -> SourceObligationCandidate:
    return SourceObligationCandidate(
        candidate_id=candidate_id,
        obligation_id="official-current",
        component_ids=(component_id,),
        kind=SourceObligationKind.OFFICIAL_CURRENT,
        strictness=strictness,
        required_source_class="official_current_rules",
        currentness_requirement="current at answer time",
        satisfaction_rule="lower-tier sources may provide bridge hints only",
        lower_tier_use="bridge_hint_only",
        lower_tier_final_satisfaction_allowed=lower_tier_final_satisfaction_allowed,
    )


def _official_provider(component_id: str = "primary-answer") -> ProviderJobCandidate:
    return ProviderJobCandidate(
        candidate_id="provider:official-acquisition",
        provider_job_id="official-acquisition",
        component_ids=(component_id,),
        job_kind=ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,
        source_obligation_candidate_ids=("obligation:official-current",),
    )


def test_simple_official_current_lookup_assessment_and_direct_contract_are_passive() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:official-current",
        requested_mode=SearchMode.FAST,
        query_shape_kinds=(
            QueryShapeKind.SIMPLE_LOOKUP,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
            QueryShapeKind.TIME_SENSITIVE,
        ),
        component_candidates=(_component(),),
        source_obligation_candidates=(_official_obligation(),),
        provider_job_candidates=(_official_provider(),),
        deterministic_signals=("current fee phrase", "official source cue"),
        stop_condition_candidates=(StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:direct-official",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
    ).require_valid()
    construction = SearchWorkPlanConstructionDesignRecord(
        design_id="construction:official-current"
    ).require_valid()

    payload = assessment.to_dict()
    encoded = json.dumps(
        {
            "assessment": payload,
            "resolution": resolution.to_dict(),
            "construction": construction.to_dict(),
        },
        sort_keys=True,
    )

    assert "official_current_lookup" in payload["query_shape_kinds"]
    assert payload["source_obligation_candidates"][0]["kind"] == "official_current"
    assert payload["provider_job_candidates"][0]["job_kind"] == "official_candidate_acquisition"
    assert resolution.to_dict()["effective_contract"] == "direct_constrained"
    assert payload["passive"] is True
    assert payload["constructs_search_work_plan"] is False
    assert construction.to_dict()["constructs_search_work_plan"] is False
    assert encoded


def test_balanced_can_downshift_to_fast_shaped_work_without_obligation_weakening() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:balanced-downshift",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(
            QueryShapeKind.SIMPLE_LOOKUP,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
        ),
        component_candidates=(_component(),),
        source_obligation_candidates=(_official_obligation(),),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:balanced-downshift",
        requested_mode=SearchMode.BALANCED,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        mode_mismatch_posture=ModeMismatchPosture.NONE,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
        output_posture=OutputPosture.DIRECT,
        rationale="Simple lookup can use Fast-shaped output while preserving official/current obligation.",
    ).require_valid()

    payload = assessment.to_dict()

    assert payload["requested_mode"] == "balanced"
    assert payload["source_obligation_candidates"][0]["strictness"] == "required"
    assert payload["source_obligation_candidates"][0]["lower_tier_final_satisfaction_allowed"] is False
    assert resolution.to_dict()["requested_mode"] == "balanced"
    assert resolution.to_dict()["effective_contract"] == "direct_constrained"


def test_fast_query_exceeds_fast_does_not_silently_choose_balanced_budget() -> None:
    invalid = ContractResolutionRecord(
        resolution_id="resolution:bad-fast-upshift",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.EXPLANATORY,
        mode_mismatch_posture=ModeMismatchPosture.NONE,
        allowed_follow_up_depth=FollowUpDepthPosture.CONDITIONAL_GAP_DRIVEN,
    )
    valid = ContractResolutionRecord(
        resolution_id="resolution:fast-insufficient",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        mode_mismatch_posture=ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
        output_posture=OutputPosture.INSUFFICIENT,
        stop_escalate_refuse_posture=StopEscalateRefusePosture.ESCALATE_SUGGESTED,
    ).require_valid()

    errors = invalid.validate().errors

    assert any("Fast cannot silently spend Balanced/Deep budget" in error for error in errors)
    assert valid.to_dict()["mode_mismatch_posture"] == "selected_mode_insufficient"
    assert valid.to_dict()["effective_contract"] == "direct_constrained"


def test_md80_vs_777_quantitative_comparison_is_represented_without_calculation_execution() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:aircraft-comparison",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(
            QueryShapeKind.QUANTITATIVE_COMPARISON,
            QueryShapeKind.SOURCE_BOUND_NUMERIC,
            QueryShapeKind.NORMALIZATION_REQUIRED,
            QueryShapeKind.COMPARATIVE,
        ),
        component_candidates=(
            _component("md80", subquestion="Find MD-80 cost and utilization inputs."),
            _component("777", subquestion="Find 777-300 cost and utilization inputs."),
        ),
        source_obligation_candidates=(
            SourceObligationCandidate(
                candidate_id="obligation:source-bound-values",
                obligation_id="source-bound-values",
                component_ids=("md80", "777"),
                kind=SourceObligationKind.SOURCE_BOUND_NUMERIC,
                strictness=SourceObligationStrictness.REQUIRED,
                satisfaction_rule="numeric inputs must come from admitted source-bound evidence",
            ),
        ),
        quant_work_candidates=(
            QuantWorkCandidate(
                candidate_id="quant:cost-per-passenger-mile",
                quant_unit_id="cost-per-passenger-mile",
                component_ids=("md80", "777"),
                target_metric="cost per passenger mile",
                required_variables=("operating cost", "capacity", "load factor", "stage length"),
                source_bound_values_needed=("cost", "seat count", "utilization"),
                allowed_calculations=("normalize cost by source-bound passenger miles",),
                assumptions_needed=("configuration", "route profile"),
            ),
        ),
        normalization_notes=("Units, load factor, route profile, and period must match.",),
    ).require_valid()

    payload = assessment.to_dict()
    quant = payload["quant_work_candidates"][0]

    assert "quantitative_comparison" in payload["query_shape_kinds"]
    assert "source_bound_numeric" in payload["query_shape_kinds"]
    assert "normalization_required" in payload["query_shape_kinds"]
    assert {item["component_id"] for item in payload["component_candidates"]} == {"md80", "777"}
    assert quant["target_metric"] == "cost per passenger mile"
    assert quant["executes_calculations"] is False
    assert quant["executes_code"] is False


def test_deep_conflict_currentness_case_represents_conditional_passive_audit() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:deep-conflict",
        requested_mode=SearchMode.DEEP,
        query_shape_kinds=(
            QueryShapeKind.CONFLICT_LIKELY,
            QueryShapeKind.TIME_SENSITIVE,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
        ),
        component_candidates=(_component("current-fee"),),
        source_obligation_candidates=(
            SourceObligationCandidate(
                candidate_id="obligation:conflict-currentness",
                obligation_id="conflict-currentness",
                component_ids=("current-fee",),
                kind=SourceObligationKind.CONFLICT_RESOLUTION,
                strictness=SourceObligationStrictness.REQUIRED,
            ),
        ),
        audit_job_candidates=(
            AuditJobCandidate(
                candidate_id="audit:currentness-conflict",
                audit_job_id="currentness-conflict",
                component_ids=("current-fee",),
                audit_scope=AuditScope.SOURCE_CONFLICT_RECONCILIATION,
                claim_types=("effective date", "current fee"),
                assumptions_to_test=("new table supersedes old notice",),
                remediation_permission=RemediationPermission.CONDITIONAL_PASSIVE,
            ),
        ),
        first_pass_evidence_needed={"confirm_actual_conflict": True},
    ).require_valid()

    audit = assessment.to_dict()["audit_job_candidates"][0]

    assert audit["audit_scope"] == "source_conflict_reconciliation"
    assert audit["remediation_permission"] == "conditional_passive"
    assert audit["bounded"] is True
    assert audit["passive"] is True
    assert audit["open_ended_loop"] is False


def test_social_perception_candidate_is_deferred_and_cannot_satisfy_source_obligations() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:social-perception",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(QueryShapeKind.MULTIPART,),
        component_candidates=(_component("community-reaction"),),
        social_signal_candidates=(
            SocialSignalCandidate(
                candidate_id="social:developer-sentiment",
                social_signal_id="developer-sentiment",
                component_ids=("community-reaction",),
                perception_need="Developer community reaction may be useful context.",
            ),
        ),
    ).require_valid()
    invalid = QueryShapeAssessment(
        assessment_id="assessment:social-invalid",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,),
        component_candidates=(_component("official-answer"),),
        social_signal_candidates=(
            SocialSignalCandidate(
                candidate_id="social:bad-official-satisfaction",
                social_signal_id="bad-official-satisfaction",
                component_ids=("official-answer",),
                perception_need="Bad attempt to satisfy an official fact.",
                satisfies_official_or_factual_obligations=True,
            ),
        ),
    )

    social = assessment.to_dict()["social_signal_candidates"][0]

    assert social["directional_perception_evidence_only"] is True
    assert social["deferred"] is True
    assert social["satisfies_official_or_factual_obligations"] is False
    assert "official" in social["disallowed_satisfaction_kinds"]
    assert any("cannot satisfy official/legal" in error for error in invalid.validate().errors)


def test_validation_invariants_duplicate_ids_missing_refs_forbidden_authorizers_and_redaction() -> None:
    invalid_assessment = QueryShapeAssessment(
        assessment_id="assessment:invalid",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,),
        component_candidates=(
            _component("dup", candidate_id="component:dup"),
            _component("dup", candidate_id="component:dup"),
        ),
        source_obligation_candidates=(
            _official_obligation(
                "missing",
                strictness=SourceObligationStrictness.PREFERRED,
                lower_tier_final_satisfaction_allowed=True,
            ),
        ),
        provider_job_candidates=(
            ProviderJobCandidate(
                candidate_id="provider:missing",
                provider_job_id="missing",
                component_ids=("missing",),
                job_kind=ProviderJobKind.SEMANTIC_RECALL,
            ),
        ),
        quant_work_candidates=(
            QuantWorkCandidate(
                candidate_id="quant:missing",
                quant_unit_id="missing",
                component_ids=("missing",),
                target_metric="metric",
            ),
        ),
        audit_job_candidates=(
            AuditJobCandidate(
                candidate_id="audit:missing",
                audit_job_id="missing",
                component_ids=("missing",),
                audit_scope=AuditScope.CLAIM_CHALLENGE,
            ),
        ),
        social_signal_candidates=(
            SocialSignalCandidate(
                candidate_id="social:missing",
                social_signal_id="missing",
                component_ids=("missing",),
                perception_need="sentiment",
            ),
        ),
        metadata={
            "raw_prompt": "SENTINEL_RAW_PROMPT",
            "raw_provider_payload": {"private": "SENTINEL_PROVIDER_PAYLOAD"},
            "safe_note": "visible",
        },
    )
    invalid_resolution = ContractResolutionRecord(
        resolution_id="resolution:invalid-authorizer",
        requested_mode=SearchMode.BALANCED,
        effective_contract=EffectiveContractKind.EXPLANATORY,
        authority_chain_owner="Analyst",
        runtime_authorizer="Author",
        follow_up_authorizers=("Analyst", "Scout"),
        metadata={"raw_model_response": "SENTINEL_MODEL"},
    )

    errors = invalid_assessment.validate().errors
    resolution_errors = invalid_resolution.validate().errors
    encoded = json.dumps(
        {
            "assessment": invalid_assessment.to_dict(),
            "resolution": invalid_resolution.to_dict(),
        },
        sort_keys=True,
    )

    assert any("duplicate component_id" in error for error in errors)
    assert any("duplicate component candidate_id" in error for error in errors)
    assert any("source obligation candidate" in error and "missing component" in error for error in errors)
    assert any("provider job candidate provider:missing references missing component missing" in error for error in errors)
    assert any("quant work candidate quant:missing references missing component missing" in error for error in errors)
    assert any("audit job candidate audit:missing references missing component missing" in error for error in errors)
    assert any("social signal candidate social:missing references missing component missing" in error for error in errors)
    assert any("cannot downgrade official_current below required strictness" in error for error in errors)
    assert any("cannot allow lower-tier final satisfaction" in error for error in errors)
    assert any("authority_chain_owner cannot be bounded executor Analyst" in error for error in resolution_errors)
    assert any("runtime_authorizer cannot be bounded executor Author" in error for error in resolution_errors)
    assert any("bounded executors cannot authorize follow-up" in error for error in resolution_errors)
    assert "SENTINEL_RAW_PROMPT" not in encoded
    assert "SENTINEL_PROVIDER_PAYLOAD" not in encoded
    assert "SENTINEL_MODEL" not in encoded
    assert "visible" in encoded
    with pytest.raises(ValueError, match="duplicate component_id"):
        invalid_assessment.require_valid()


def test_static_passive_boundary_for_new_module() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.runtime_prompt_assembly",
        "core.prompts",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "fetch_page",
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
    assert "core.pipeline_orchestrator" not in source
    assert "search_web_results" not in source
    assert "SearchWorkPlan(" not in source
