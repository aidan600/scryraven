from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.query_shape_contract_resolution import (
    ComponentCandidate,
    ContractResolutionRecord,
    FollowUpDepthPosture,
    ProviderJobCandidate,
    QueryShapeAssessment,
    SearchWorkPlanConstructionDesignRecord,
    SourceObligationCandidate,
)
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.search_work_plan import (
    EffectiveContractKind,
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

ROOT = Path(__file__).resolve().parents[1]
CONSTRUCTION_MODULE = ROOT / "core" / "search_work_plan_construction.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"


def _contract_observation(kernel: RunKernel) -> Observation:
    action = kernel.authorize_run_contract_synthesis(
        inputs={"request_ref": "safe-request-ref"}
    )
    return Observation.from_action(
        action,
        observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
        status=RunStageStatus.COMPLETED,
        payload={
            "contract_projection": {
                "contract_id": "contract:ag96c7",
                "schema_version": "run_authority_contract_test_v1",
                "synthesis_mode": "fixture",
                "selected_depth": "fast",
                "source_requirement_summary": ["official_current"],
                "source_requirements": [
                    {
                        "requirement_id": "official-current",
                        "source_class": "official_current",
                    }
                ],
                "user_query_ref": {"request_id": kernel.state.request_id},
            },
            "validation": {"ok": True, "status": "ok"},
        },
    )


def _construction_input(
    *,
    construction_id: str = "construction:ag96c7",
    metadata: dict[str, object] | None = None,
) -> SearchWorkPlanConstructionInput:
    assessment = QueryShapeAssessment(
        assessment_id="assessment:ag96c7",
        requested_mode=SearchMode.FAST,
        query_shape_kinds=(
            QueryShapeKind.SIMPLE_LOOKUP,
            QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
        ),
        component_candidates=(
            ComponentCandidate(
                candidate_id="component:primary-answer",
                component_id="primary-answer",
                user_facing_subquestion="Find the official current answer.",
                source_obligation_candidate_ids=("obligation:official-current",),
                provider_job_candidate_ids=("provider:official-acquisition",),
            ),
        ),
        source_obligation_candidates=(
            SourceObligationCandidate(
                candidate_id="obligation:official-current",
                obligation_id="official-current",
                component_ids=("primary-answer",),
                kind=SourceObligationKind.OFFICIAL_CURRENT,
                strictness=SourceObligationStrictness.REQUIRED,
                required_source_class="official_current",
                currentness_requirement="current at answer time",
                satisfaction_rule="lower-tier sources may provide bridge hints only",
                lower_tier_use="bridge_hint_only",
                lower_tier_final_satisfaction_allowed=False,
            ),
        ),
        provider_job_candidates=(
            ProviderJobCandidate(
                candidate_id="provider:official-acquisition",
                provider_job_id="official-acquisition",
                component_ids=("primary-answer",),
                job_kind=ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,
                source_obligation_candidate_ids=("obligation:official-current",),
            ),
        ),
        stop_condition_candidates=(StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,),
    ).require_valid()
    resolution = ContractResolutionRecord(
        resolution_id="resolution:ag96c7",
        requested_mode=SearchMode.FAST,
        effective_contract=EffectiveContractKind.DIRECT_CONSTRAINED,
        allowed_follow_up_depth=FollowUpDepthPosture.NONE_OR_MINIMAL,
    ).require_valid()
    return SearchWorkPlanConstructionInput(
        construction_id=construction_id,
        requested_mode_source="unit_test_fixture",
        query_shape_assessment=assessment,
        contract_resolution=resolution,
        construction_design=SearchWorkPlanConstructionDesignRecord(
            design_id="design:ag96c7"
        ),
        safe_route_facts={"intent": "lookup", "route_ref": "safe-route-ref"},
        run_authority_contract_ref={"contract_id": "contract:ag96c7"},
        current_date_ref={"id": "current-date:fixture"},
        passive_mode_policy_snapshot={"mode": "Fast"},
        safe_user_domain_hints={"include_domains": ["irs.gov"]},
        metadata=metadata or {},
    )


def _kernel_after_contract() -> RunKernel:
    kernel = RunKernel.start(run_id="run-ag96c7", request_id="request-ag96c7")
    kernel.reduce(_contract_observation(kernel))
    return kernel


def test_run_kernel_authorizes_and_reduces_shadow_construction_after_contract() -> None:
    kernel = _kernel_after_contract()
    action = kernel.authorize_search_work_plan_construction(
        inputs={"input_record_ref": "construction-input:ag96c7"}
    )
    observation = observe_search_work_plan_construction(
        action,
        _construction_input(),
    )

    state = kernel.reduce(observation)
    projection = state.search_work_plan_projection
    trace = kernel.to_trace_fragment()["run_kernel"]

    assert state.search_work_plan
    assert projection["owner"] == "RunKernel.SearchWorkPlan"
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["storage_only"] is False
    assert projection["construction_id"] == "construction:ag96c7"
    assert projection["component_count"] == 1
    assert projection["provider_job_count"] == 1
    assert projection["quant_work_unit_count"] == 0
    assert projection["audit_job_count"] == 0
    assert projection["stop_condition_count"] == 1
    assert projection["follow_up_permission"] == "not_allowed"
    assert projection["validation_status"] == "ok"
    assert projection["search_work_plan_runtime_consumed"] is False
    assert projection["runtime_consumed_by_query_plan"] is False
    assert projection["provider_search_behavior_changed"] is False
    assert projection["query_plan_behavior_changed"] is False
    assert projection["prompt_behavior_changed"] is False
    assert projection["final_answer_behavior_changed"] is False
    assert trace["search_work_plan"]
    assert trace["search_work_plan_projection"] == projection
    assert trace["projections"][SEARCH_WORK_PLAN_CONSTRUCTION_STAGE] == projection


def test_cannot_authorize_shadow_construction_before_run_contract() -> None:
    kernel = RunKernel.start(run_id="run-no-contract", request_id="request")

    with pytest.raises(RunKernelTransitionError, match="RunAuthority contract"):
        kernel.authorize_search_work_plan_construction()


def test_observation_type_action_stage_mismatch_is_rejected() -> None:
    kernel = _kernel_after_contract()
    action = kernel.authorize_search_work_plan_construction()
    wrong_type = Observation(
        observation_id="wrong-type",
        run_id=kernel.state.run_id,
        action_id=action.action_id,
        stage=action.stage,
        observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
        status=RunStageStatus.COMPLETED,
        payload={"search_work_plan_projection": {"schema_version": "bad"}},
        sequence=action.sequence,
    )
    wrong_stage = Observation(
        observation_id="wrong-stage",
        run_id=kernel.state.run_id,
        action_id=action.action_id,
        stage="wrong_stage",
        observation_type=ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED,
        status=RunStageStatus.COMPLETED,
        payload={"search_work_plan_projection": {"schema_version": "bad"}},
        sequence=action.sequence,
    )

    with pytest.raises(RunKernelTransitionError, match="observation type"):
        kernel.reduce(wrong_type)
    with pytest.raises(RunKernelTransitionError, match="stage"):
        kernel.reduce(wrong_stage)


def test_construction_observation_requires_search_work_plan_projection() -> None:
    kernel = _kernel_after_contract()
    action = kernel.authorize_search_work_plan_construction()
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED,
        status=RunStageStatus.COMPLETED,
        payload={"validation": {"ok": True}},
    )

    with pytest.raises(RunKernelTransitionError, match="search_work_plan_projection"):
        kernel.reduce(observation)


def test_shadow_construction_does_not_authorize_query_or_provider_behavior() -> None:
    kernel = _kernel_after_contract()
    action = kernel.authorize_search_work_plan_construction()
    kernel.reduce(observe_search_work_plan_construction(action, _construction_input()))

    action_types = {item.action_type for item in kernel.state.issued_actions.values()}
    assert action_types == {
        ActionType.RUN_CONTRACT_SYNTHESIZE,
        ActionType.SEARCH_WORK_PLAN_CONSTRUCT,
    }
    assert QUERY_PLAN_ADMISSION_STAGE not in kernel.state.stage_statuses
    assert QUERY_PRODUCTION_STAGE not in kernel.state.stage_statuses
    assert "main_retrieval" not in kernel.state.stage_statuses
    assert set(kernel.state.stage_statuses) == {
        "run_contract",
        SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
    }
    assert all(
        action_type
        not in action_types
        for action_type in (
            ActionType.QUERY_PRODUCTION,
            ActionType.QUERY_PLAN_ADMISSION,
            ActionType.MAIN_RETRIEVAL_PASS,
        )
    )
    projection = kernel.state.search_work_plan_projection
    assert projection["provider_search_behavior_changed"] is False
    assert projection["query_plan_behavior_changed"] is False


def test_sensitive_projection_redaction_from_serialized_trace() -> None:
    kernel = _kernel_after_contract()
    action = kernel.authorize_search_work_plan_construction()
    observation = observe_search_work_plan_construction(
        action,
        _construction_input(
            construction_id="construction:redaction",
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
        ),
    )
    kernel.reduce(observation)
    encoded = json.dumps(kernel.to_trace_fragment(), sort_keys=True)

    for sentinel in (
        "SENTINEL_RAW_PROMPT",
        "SENTINEL_PROVIDER_PAYLOAD",
        "SENTINEL_MODEL_RESPONSE",
        "SENTINEL_SECRET",
        "SENTINEL_TOKEN",
        "SENTINEL_DB_ROW",
        "SENTINEL_TRACE",
    ):
        assert sentinel not in encoded
    assert "visible-safe-note" in encoded


def test_static_no_production_consumer_guard() -> None:
    runtime_paths = (
        ROOT / "core" / "pipeline_orchestrator.py",
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "mode_policy.py",
    )
    forbidden_modules = {
        "core.search_work_plan_construction",
        "search_work_plan_construction",
    }

    for path in runtime_paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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

        assert imported_names.isdisjoint(forbidden_modules), path
        assert "observe_search_work_plan_construction" not in called_names, path

    assert "core.search_work_plan_construction" not in RUN_KERNEL_MODULE.read_text(
        encoding="utf-8"
    )


def test_static_closed_surface_guard_for_construction_module() -> None:
    source = CONSTRUCTION_MODULE.read_text(encoding="utf-8")
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
