from __future__ import annotations

import ast
import json
from pathlib import Path

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
from core.search_work_plan_construction import (
    SearchWorkPlanConstructionInput,
    construct_search_work_plan_from_records,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "search_work_plan_construction.py"


def _component(
    component_id: str = "primary-answer",
    *,
    candidate_id: str | None = None,
    subquestion: str = "Find the answer-bearing source.",
    entities: tuple[str, ...] = (),
) -> ComponentCandidate:
    return ComponentCandidate(
        candidate_id=candidate_id or f"component:{component_id}",
        component_id=component_id,
        user_facing_subquestion=subquestion,
        entities=entities,
    )


def _official_obligation(
    component_id: str = "primary-answer",
    *,
    candidate_id: str = "obligation:official-current",
    obligation_id: str = "official-current",
) -> SourceObligationCandidate:
    return SourceObligationCandidate(
        candidate_id=candidate_id,
        obligation_id=obligation_id,
        component_ids=(component_id,),
        kind=SourceObligationKind.OFFICIAL_CURRENT,
        strictness=SourceObligationStrictness.REQUIRED,
        required_source_class="official_current",
        currentness_requirement="current at answer time",
        satisfaction_rule="lower-tier sources may provide bridge hints only",
        lower_tier_use="bridge_hint_only",
        lower_tier_final_satisfaction_allowed=False,
    )


def _official_provider(component_id: str = "primary-answer") -> ProviderJobCandidate:
    return ProviderJobCandidate(
        candidate_id="provider:official-acquisition",
        provider_job_id="official-acquisition",
        component_ids=(component_id,),
        job_kind=ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,
        source_obligation_candidate_ids=("obligation:official-current",),
    )


def _design() -> SearchWorkPlanConstructionDesignRecord:
    return SearchWorkPlanConstructionDesignRecord(
        design_id="design:ag96c6-passive-construction"
    )


def _input(
    *,
    construction_id: str,
    assessment: QueryShapeAssessment,
    resolution: ContractResolutionRecord,
    metadata: dict[str, object] | None = None,
) -> SearchWorkPlanConstructionInput:
    return SearchWorkPlanConstructionInput(
        construction_id=construction_id,
        requested_mode_source="unit_test_fixture",
        query_shape_assessment=assessment,
        contract_resolution=resolution,
        construction_design=_design(),
        safe_route_facts={"route_id": construction_id, "intent": "lookup"},
        run_authority_contract_ref={"contract_id": f"contract:{construction_id}"},
        current_date_ref={"id": "current-date:fixture"},
        passive_mode_policy_snapshot={"mode": resolution.requested_mode.value},
        safe_user_domain_hints={"include_domains": ["irs.gov"]},
        metadata=metadata or {},
    )


def test_official_current_simple_lookup_construction() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:official-current",
        requested_mode=SearchMode.FAST,
        query_shape_kinds=(
            QueryShapeKind.SIMPLE_LOOKUP,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
        ),
        component_candidates=(_component(),),
        source_obligation_candidates=(_official_obligation(),),
        provider_job_candidates=(_official_provider(),),
        stop_condition_candidates=(StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:direct-official",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
    ).require_valid()

    result = construct_search_work_plan_from_records(
        _input(
            construction_id="construction:official-current",
            assessment=assessment,
            resolution=resolution,
        )
    )
    plan = result.search_work_plan.require_valid()
    payload = result.to_dict()

    assert result.validation["ok"] is True
    assert len(plan.components) == 1
    assert plan.components[0].source_obligations[0].kind.value == "official_current"
    assert plan.provider_jobs[0].job_kind.value == "official_candidate_acquisition"
    assert payload["runtime_consumed"] is False
    assert payload["provider_search_behavior_changed"] is False


def test_balanced_downshift_preserves_official_current_obligation() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:balanced-downshift",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(
            QueryShapeKind.SIMPLE_LOOKUP,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
        ),
        component_candidates=(_component(),),
        source_obligation_candidates=(_official_obligation(),),
        provider_job_candidates=(_official_provider(),),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:balanced-downshift",
        requested_mode=SearchMode.BALANCED,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        mode_mismatch_posture=ModeMismatchPosture.NONE,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
        output_posture=OutputPosture.DIRECT,
    ).require_valid()

    result = construct_search_work_plan_from_records(
        _input(
            construction_id="construction:balanced-downshift",
            assessment=assessment,
            resolution=resolution,
        )
    )
    payload = result.search_work_plan.require_valid().to_dict()
    obligation = payload["components"][0]["source_obligations"][0]

    assert payload["requested_mode"]["mode"] == "balanced"
    assert payload["effective_contract"]["contract_kind"] == "direct_constrained"
    assert obligation["kind"] == "official_current"
    assert obligation["strictness"] == "required"
    assert "bridge_hint_only" in obligation["lower_tier_use"]
    assert payload["follow_up_authority"]["permission"] == "not_allowed"


def test_fast_insufficient_construction_does_not_upgrade_budget() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:fast-insufficient",
        requested_mode=SearchMode.FAST,
        query_shape_kinds=(
            QueryShapeKind.QUANTITATIVE_COMPARISON,
            QueryShapeKind.SOURCE_BOUND_NUMERIC,
            QueryShapeKind.MODE_MISMATCH_POSSIBLE,
        ),
        component_candidates=(_component("quant-gap"),),
        source_obligation_candidates=(
            SourceObligationCandidate(
                candidate_id="obligation:source-bound",
                obligation_id="source-bound-values",
                component_ids=("quant-gap",),
                kind=SourceObligationKind.SOURCE_BOUND_NUMERIC,
                strictness=SourceObligationStrictness.REQUIRED,
            ),
        ),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:fast-insufficient",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        mode_mismatch_posture=ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
        output_posture=OutputPosture.INSUFFICIENT,
        stop_escalate_refuse_posture=StopEscalateRefusePosture.ESCALATE_SUGGESTED,
    ).require_valid()

    result = construct_search_work_plan_from_records(
        _input(
            construction_id="construction:fast-insufficient",
            assessment=assessment,
            resolution=resolution,
        )
    )
    payload = result.search_work_plan.require_valid().to_dict()
    stop_conditions = {item["condition"] for item in payload["stop_conditions"]}

    assert payload["requested_mode"]["mode"] == "fast"
    assert payload["effective_contract"]["contract_kind"] == "direct_constrained"
    assert payload["effective_contract"]["depth_allowance"] == "shallow"
    assert payload["follow_up_authority"]["permission"] == "not_allowed"
    assert "mode_mismatch" in stop_conditions
    assert "required_inference_exceeds_selected_mode" in stop_conditions


def test_md80_vs_777_quantitative_construction_is_passive() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:aircraft-comparison",
        requested_mode=SearchMode.BALANCED,
        query_shape_kinds=(
            QueryShapeKind.COMPARATIVE,
            QueryShapeKind.QUANTITATIVE_COMPARISON,
            QueryShapeKind.SOURCE_BOUND_NUMERIC,
        ),
        component_candidates=(
            _component("md80", subquestion="Find MD-80 source-bound inputs."),
            _component("777", subquestion="Find 777 source-bound inputs."),
        ),
        source_obligation_candidates=(
            SourceObligationCandidate(
                candidate_id="obligation:source-bound",
                obligation_id="source-bound-values",
                component_ids=("md80", "777"),
                kind=SourceObligationKind.SOURCE_BOUND_NUMERIC,
                strictness=SourceObligationStrictness.REQUIRED,
            ),
        ),
        quant_work_candidates=(
            QuantWorkCandidate(
                candidate_id="quant:cost-per-passenger-mile",
                quant_unit_id="cost-per-passenger-mile",
                component_ids=("md80", "777"),
                target_metric="cost per passenger mile",
                required_variables=("operating cost", "seat count", "stage length"),
                source_bound_values_needed=("cost", "capacity", "distance"),
                allowed_calculations=("normalize using source-bound values",),
                assumptions_needed=("configuration", "load factor"),
            ),
        ),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:balanced-quant",
        requested_mode=SearchMode.BALANCED,
        effective_contract=EffectiveContractKind.EXPLANATORY,
        allowed_follow_up_depth=FollowUpDepthPosture.CONDITIONAL_GAP_DRIVEN,
    ).require_valid()

    result = construct_search_work_plan_from_records(
        _input(
            construction_id="construction:aircraft-comparison",
            assessment=assessment,
            resolution=resolution,
        )
    )
    payload = result.search_work_plan.require_valid().to_dict()
    quant = payload["quant_work_units"][0]

    assert {item["component_id"] for item in payload["components"]} == {"md80", "777"}
    assert payload["components"][0]["source_obligations"][0]["kind"] == "source_bound_numeric"
    assert quant["target_metric"] == "cost per passenger mile"
    assert quant["executes_calculations"] is False
    assert quant["executes_code"] is False


def test_deep_conflict_currentness_construction_creates_bounded_audit() -> None:
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
                candidate_id="obligation:conflict",
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
        stop_condition_candidates=(StopConditionKind.UNRESOLVED_CONFLICT_CURRENTNESS,),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:deep-conflict",
        requested_mode=SearchMode.DEEP,
        effective_contract=EffectiveContractKind.RESEARCH_RECONCILIATION,
        allowed_follow_up_depth=FollowUpDepthPosture.LARGER_BOUNDED_LOOP,
    ).require_valid()

    result = construct_search_work_plan_from_records(
        _input(
            construction_id="construction:deep-conflict",
            assessment=assessment,
            resolution=resolution,
        )
    )
    audit = result.search_work_plan.require_valid().to_dict()["audit_jobs"][0]

    assert audit["audit_scope"] == "source_conflict_reconciliation"
    assert audit["bounded"] is True
    assert audit["passive"] is True
    assert audit["open_ended_loop"] is False
    assert audit["remediation_permission"] == "conditional_passive"


def test_social_perception_candidate_remains_deferred_warning_only() -> None:
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
                perception_need="Developer sentiment may be useful context.",
            ),
        ),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:social-perception",
        requested_mode=SearchMode.BALANCED,
        effective_contract=EffectiveContractKind.EXPLANATORY,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
    ).require_valid()

    result = construct_search_work_plan_from_records(
        _input(
            construction_id="construction:social-perception",
            assessment=assessment,
            resolution=resolution,
        )
    )
    payload = result.search_work_plan.require_valid().to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert result.warnings
    assert "social" in result.warnings[0]
    assert "social_signal_jobs" not in encoded
    assert "official_current" not in encoded
    assert payload["provider_jobs"] == []


def test_sensitive_input_redaction_from_construction_serialization() -> None:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:redaction",
        requested_mode=SearchMode.FAST,
        query_shape_kinds=(QueryShapeKind.SIMPLE_LOOKUP,),
        component_candidates=(_component(),),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:redaction",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
    ).require_valid()
    input_record = _input(
        construction_id="construction:redaction",
        assessment=assessment,
        resolution=resolution,
        metadata={
            "raw_prompt": "SENTINEL_RAW_PROMPT",
            "raw_provider_payload": "SENTINEL_PROVIDER_PAYLOAD",
            "raw_model_response": "SENTINEL_MODEL_RESPONSE",
            "secret": "SENTINEL_SECRET",  # pragma: allowlist secret
            "token": "SENTINEL_TOKEN",
            "db_row": "SENTINEL_DB_ROW",
            "full_trace": "SENTINEL_TRACE",
            "safe_note": "visible-safe-note",
        },
    )

    result = construct_search_work_plan_from_records(input_record)
    encoded = json.dumps(
        {"input": input_record.to_dict(), "result": result.to_dict()},
        sort_keys=True,
    )

    assert "SENTINEL_RAW_PROMPT" not in encoded
    assert "SENTINEL_PROVIDER_PAYLOAD" not in encoded
    assert "SENTINEL_MODEL_RESPONSE" not in encoded
    assert "SENTINEL_SECRET" not in encoded
    assert "SENTINEL_TOKEN" not in encoded
    assert "SENTINEL_DB_ROW" not in encoded
    assert "SENTINEL_TRACE" not in encoded
    assert "visible-safe-note" in encoded


def test_passive_boundary_static_import_and_call_scan() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
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


def test_no_runtime_consumer_imports_construction_adapter() -> None:
    runtime_paths = (
        ROOT / "core" / "run_kernel.py",
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "pipeline_orchestrator.py",
    )
    forbidden_modules = {
        "core.search_work_plan_construction",
        "search_work_plan_construction",
    }

    for path in runtime_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
        assert imported_names.isdisjoint(forbidden_modules), path
