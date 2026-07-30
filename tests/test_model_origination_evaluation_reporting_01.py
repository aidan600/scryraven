"""Phase-focus proof for non-overriding evaluation coordination/reporting.

Proof class: CONTRACT-INVARIANT. Surface guarded: exact owner-status retention,
combined-result precedence, causal wording, and sanitized passive assembly.
Expected cost: tiny deterministic unit proof. Promotion posture: phase_focus
until a durable evaluator lane exists.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import scripts.evaluation.run_analystos_model_origination_evaluation as legacy
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
)
from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
    build_search_planner_model_prompt,
)
from scripts.evaluation.model_origination_evaluation_reporting import (
    EvaluationReportingError,
    ModelOriginationEvaluationDecisionCoordinator,
    ModelOriginationEvaluationReportAssembler,
)
from scripts.evaluation.model_origination_experiment_authority import (
    EXPERIMENT_AUTHORITY_SCHEMA_VERSION,
    AttributionResult,
)
from scripts.evaluation.search_planner_mechanical_validation import (
    validate_product_observation,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CanonicalProductSearchPlannerBoundaryObserver,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    EssentialRequirement,
    RequirementMapping,
    ScriptedSemanticJudgeAdapter,
    SemanticAmbiguity,
    SemanticIssue,
    SemanticPassJudgment,
    build_semantic_judgment_request,
)


def _product():
    observer = CanonicalProductSearchPlannerBoundaryObserver(lambda _prompt, _system, **_kwargs: "{}")
    prompt = build_search_planner_model_prompt(
        {
            "run_id": "run",
            "request_id": "request",
            "requested_mode": "balanced",
            "user_query_text_for_planning": "sanitized synthetic query",
            "user_query_ref": {"query_digest": "safe"},
            "safe_context": {},
            "route_context_ref": {},
            "run_context_ref": {},
            "parent_contract_refs": [],
            "closed_surface_flags": {},
        }
    )
    observer(
        prompt,
        SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        provider="synthetic-provider",
        model="synthetic-model",
        effort="fixed",
        require_json=True,
        cost_accumulator=object(),
        cost_phase="search_planner",
    )
    kernel = SimpleNamespace(
        state=SimpleNamespace(
            search_planner_proposal_state={"safe_ref": "proposal"},
            initial_answer_contract_projection={"safe_ref": "acceptance"},
            search_work_plan={"safe_ref": "work-plan"},
        )
    )
    return observer.finalize(run_kernel=kernel)


def _semantic(
    mechanical_result,
    status: str = "MET",
    *,
    diagnostic: bool = False,
):
    mechanical = mechanical_result.overall_posture
    request = build_semantic_judgment_request(
        normalized_user_request="Preserve the synthetic answer requirement.",
        planner_input={"requirements": ["answer"]},
        essential_requirements=(
            EssentialRequirement(
                requirement_id="answer",
                requirement_kind="ANSWER_CAPABILITY",
                normalized_requirement="The plan can answer the request.",
            ),
        ),
        proposed_plan={"safe_ref": "proposal"},
        mechanical_validation_summary={
            "result_id": mechanical_result.result_id,
            "owner": mechanical_result.owner,
            "product_proposal_digest": (
                mechanical_result.product_proposal_digest
            ),
            "overall_posture": mechanical,
            "blocking_failure_rule_ids": list(mechanical_result.blocking_failure_rule_ids),
        },
        evaluation_budget_identity="offline-reporting-contract-proof",
        essential_architecture_constraints=("RunKernel remains canonical.",),
        prohibited_upgrades_or_shortcuts=("Do not invent support.",),
        diagnostic_mode=diagnostic,
    )
    if status == "MET":
        supplied = SemanticPassJudgment(
            status="MET",
            requirement_mappings=(
                RequirementMapping(
                    requirement_id="answer",
                    proposal_paths=("/safe_ref",),
                    bounded_explanation="The requirement maps exactly.",
                ),
            ),
        )
    elif status == "NOT_MET":
        supplied = SemanticPassJudgment(
            status="NOT_MET",
            issues=(
                SemanticIssue(
                    requirement_id="answer",
                    issue_kind="MISSING",
                    proposal_paths=("/safe_ref",),
                    answer_blocking=True,
                    bounded_explanation="The answer requirement is absent.",
                ),
            ),
        )
    else:
        supplied = SemanticPassJudgment(
            status="REVIEW_REQUIRED",
            ambiguities=(
                SemanticAmbiguity(
                    requirement_id="answer",
                    precise_ambiguity="Two lawful readings remain.",
                    competing_interpretations=(
                        "The plan is sufficient.",
                        "The plan omits a material distinction.",
                    ),
                    proposal_paths=("/safe_ref",),
                    smallest_review_action=(
                        "Obtain one independent decision on the distinction."
                    ),
                ),
            ),
        )
    return ScriptedSemanticJudgeAdapter(
        primary=supplied,
        adversarial=supplied,
    ).judge(request)


def _attribution(status: str) -> AttributionResult:
    return AttributionResult(
        schema_version=EXPERIMENT_AUTHORITY_SCHEMA_VERSION,
        owner="ModelOriginationExperimentAuthority",
        status=status,
        design_kind="SINGLE_PAIR",
        design_digest="d" * 64,
        experiment_ids=("experiment:synthetic",),
        control_call_ids=("control:1",),
        variant_call_ids=("variant:1",),
        compared_instruction_variants=("control", "variant"),
        observed_effect=1.0,
        uncertainty_bound=(
            0.0
            if status == "CAUSAL_SUPPORT_ESTABLISHED"
            else None
        ),
        bounded_reasons=("Synthetic attribution posture.",),
        causal_language_allowed=(
            status == "CAUSAL_SUPPORT_ESTABLISHED"
        ),
    )


def test_passive_report_preserves_every_owner_status_and_owner_name() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET")
    attribution = _attribution("ASSOCIATION_ONLY")
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=attribution,
    )
    report = ModelOriginationEvaluationReportAssembler().assemble(
        combined=combined,
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=attribution,
        safe_usage_and_cost_metadata={
            "usage_observed": False,
            "cost_posture": "synthetic_offline",
        },
        execution_references=({"execution_id": "synthetic:1"},),
    )
    packet = report.to_packet()
    assert combined.overall_posture == "PASS"
    assert combined.product_status == product.boundary_status
    assert combined.mechanical_status == mechanical.overall_posture
    assert combined.semantic_status == semantic.final_status
    assert combined.experiment_status == attribution.status
    assert packet["combined_result"] == combined.to_packet()
    assert packet["product_boundary_result"] == product.to_packet()
    assert packet["mechanical_validation_result"] == mechanical.to_packet()
    assert packet["semantic_judgment_result"] == semantic.to_packet()
    assert packet["experiment_attribution_result"] == attribution.to_packet()
    assert set(combined.contributor_owners) == {
        "product",
        "mechanical",
        "semantic",
        "experiment",
        "combined",
    }


def test_product_boundary_not_reached_cannot_be_combined_pass() -> None:
    product = replace(
        _product(),
        boundary_status="NOT_REACHED",
        product_boundary_reached=False,
        model_call_count=0,
        prompt_identity=None,
        ask_model_argument_shape=None,
        output_digest=None,
        output_length=0,
        response_received=False,
        proposal_digest=None,
        response_cleaning_posture="NOT_REACHED",
        parser_posture="NOT_REACHED",
        validator_posture="NOT_REACHED",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        incomplete_generation_posture="NOT_REACHED",
    )
    mechanical = validate_product_observation(product)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=None,
        attribution=None,
    )
    assert combined.overall_posture == "NOT_REACHED"
    assert combined.semantic_status == "NOT_RUN"
    assert combined.mechanical_status == "NOT_REACHED"


def test_blocking_mechanical_failure_cannot_be_overridden_by_diagnostic_met() -> None:
    product = replace(
        _product(),
        boundary_status="FAIL",
        validator_posture="FAIL",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        canonical_failure_rule_ids=("M04",),
    )
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET", diagnostic=True)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
    )
    assert mechanical.overall_posture == "FAIL"
    assert semantic.final_status == "MET"
    assert combined.overall_posture == "FAIL"
    assert combined.semantic_status == "MET"


def test_semantic_review_required_cannot_be_upgraded_to_pass() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=_semantic(mechanical, "REVIEW_REQUIRED"),
        attribution=None,
    )
    assert combined.overall_posture == "REVIEW_REQUIRED"
    assert combined.semantic_status == "REVIEW_REQUIRED"


def test_association_only_never_enables_causal_language_or_winner() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=_semantic(mechanical, "MET"),
        attribution=_attribution("ASSOCIATION_ONLY"),
    )
    assert combined.overall_posture == "PASS"
    assert combined.experiment_status == "ASSOCIATION_ONLY"
    assert combined.causal_language_allowed is False
    assert combined.prompt_quality_winner is None


def test_confounded_comparison_has_no_prompt_quality_winner() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=_semantic(mechanical, "MET"),
        attribution=_attribution("CONFOUNDED"),
    )
    assert combined.overall_posture == "REVIEW_REQUIRED"
    assert combined.experiment_status == "CONFOUNDED"
    assert combined.prompt_quality_winner is None


def test_attribution_review_required_cannot_be_combined_pass() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=_semantic(mechanical, "MET"),
        attribution=_attribution("REVIEW_REQUIRED"),
    )
    assert combined.overall_posture == "REVIEW_REQUIRED"
    assert combined.causal_language_allowed is False


def test_incomplete_generation_prevents_combined_parser_or_semantic_pass() -> None:
    product = replace(
        _product(),
        boundary_status="FAIL",
        output_digest=None,
        output_length=0,
        response_received=False,
        proposal_digest=None,
        parser_posture="NOT_REACHED",
        validator_posture="NOT_REACHED",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        incomplete_generation_posture="INCOMPLETE",
    )
    mechanical = validate_product_observation(product)
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=None,
        attribution=None,
    )
    assert combined.overall_posture == "INCOMPLETE"
    assert combined.semantic_status == "NOT_RUN"


def test_report_assembler_rejects_any_silent_status_replacement() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET")
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
    )
    altered = replace(combined, semantic_status="REVIEW_REQUIRED")
    with pytest.raises(
        EvaluationReportingError,
        match="exact contributor statuses",
    ):
        ModelOriginationEvaluationReportAssembler().assemble(
            combined=altered,
            product=product,
            mechanical=mechanical,
            semantic=semantic,
            attribution=None,
            safe_usage_and_cost_metadata={},
            execution_references=(),
        )


def test_coordinator_rejects_results_bound_to_another_observation() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    different_product = replace(
        product,
        output_digest="f" * 64,
    )
    with pytest.raises(
        EvaluationReportingError,
        match="does not bind the supplied product observation",
    ):
        ModelOriginationEvaluationDecisionCoordinator().coordinate(
            product=different_product,
            mechanical=mechanical,
            semantic=None,
            attribution=None,
        )


def test_coordinator_rejects_semantic_result_for_another_proposal() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = replace(
        _semantic(mechanical, "MET"),
        proposal_digest="f" * 64,
    )
    with pytest.raises(
        EvaluationReportingError,
        match="canonical product proposal",
    ):
        ModelOriginationEvaluationDecisionCoordinator().coordinate(
            product=product,
            mechanical=mechanical,
            semantic=semantic,
            attribution=None,
        )


def test_coordinator_rejects_semantic_mechanical_posture_substitution() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = replace(
        _semantic(mechanical, "MET"),
        mechanical_posture_seen="FAIL",
        diagnostic_only=True,
    )
    with pytest.raises(
        EvaluationReportingError,
        match="preserve the mechanical posture",
    ):
        ModelOriginationEvaluationDecisionCoordinator().coordinate(
            product=product,
            mechanical=mechanical,
            semantic=semantic,
            attribution=None,
        )


def test_report_assembler_rejects_same_status_identity_replacement() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET")
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
    )
    identities = dict(combined.contributor_result_digests)
    identities["semantic"] = "0" * 64
    altered = replace(
        combined,
        contributor_result_digests=identities,
    )
    with pytest.raises(
        EvaluationReportingError,
        match="exact contributor identities",
    ):
        ModelOriginationEvaluationReportAssembler().assemble(
            combined=altered,
            product=product,
            mechanical=mechanical,
            semantic=semantic,
            attribution=None,
            safe_usage_and_cost_metadata={},
            execution_references=(),
        )


def test_report_assembler_rejects_raw_or_private_metadata() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET")
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
    )
    with pytest.raises(EvaluationReportingError, match="forbidden material"):
        ModelOriginationEvaluationReportAssembler().assemble(
            combined=combined,
            product=product,
            mechanical=mechanical,
            semantic=semantic,
            attribution=None,
            safe_usage_and_cost_metadata={"api_key": "forbidden"},
            execution_references=(),
        )


def test_serialized_report_retains_no_raw_prompt_or_response() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET")
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
    )
    report = ModelOriginationEvaluationReportAssembler().assemble(
        combined=combined,
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
        safe_usage_and_cost_metadata={"cost_posture": "offline"},
        execution_references=(),
    )
    packet = report.to_packet()
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False
    serialized = json.dumps(packet, sort_keys=True)
    assert "sanitized synthetic query" not in serialized


def test_report_packet_revalidates_after_nested_material_mutation() -> None:
    product = _product()
    mechanical = validate_product_observation(product)
    semantic = _semantic(mechanical, "MET")
    combined = ModelOriginationEvaluationDecisionCoordinator().coordinate(
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
    )
    report = ModelOriginationEvaluationReportAssembler().assemble(
        combined=combined,
        product=product,
        mechanical=mechanical,
        semantic=semantic,
        attribution=None,
        safe_usage_and_cost_metadata={"cost_posture": "offline"},
        execution_references=(),
    )
    metadata = report.safe_usage_and_cost_metadata
    assert isinstance(metadata, dict)
    metadata["cost_posture"] = "mutated"
    with pytest.raises(
        EvaluationReportingError,
        match="identity does not cover",
    ):
        report.to_packet()


def _legacy_request(*, execution_mode: str = "plan_only") -> legacy.EvaluationRequest:
    return legacy.EvaluationRequest(
        evaluation_pass="planner_only",
        execution_mode=execution_mode,
        scenario_ids=("case_03_pure_depth_two",),
        reasoning_effort=("medium" if execution_mode == "execute" else None),
    )


def test_former_evaluator_combined_authority_symbols_are_absent() -> None:
    for retired in (
        "BoundaryCallObservation",
        "BoundaryInjectionController",
        "ClassificationEvidence",
        "PairedProbeEvidence",
        "ScoreCard",
        "classify_result",
        "paired_probe_demonstrates_prompt_causality",
        "project_and_score_role_output",
    ):
        assert not hasattr(legacy, retired)


def test_former_evaluator_execute_fails_before_transport_construction() -> None:
    factory_calls: list[object] = []

    def forbidden_factory(*args: Any, **kwargs: Any) -> None:
        factory_calls.append((args, kwargs))

    with pytest.raises(
        legacy.EvaluationConfigurationError,
        match="combined evaluator execute path is retired",
    ):
        legacy.run_evaluation(
            _legacy_request(execution_mode="execute"),
            transport_factory=forbidden_factory,
        )
    with pytest.raises(
        legacy.EvaluationConfigurationError,
        match="retired before addendum or transport access",
    ):
        legacy.main(
            (
                "scripts/evaluation/run_analystos_model_origination_evaluation.py",
                "--evaluation-pass",
                "planner_only",
                "--execution-mode",
                "execute",
                "--live-addendum",
                "must-not-be-read.json",
            )
        )
    assert factory_calls == []


def test_plan_only_packet_exposes_separate_owners_without_verdicts() -> None:
    packet = legacy.run_evaluation(
        _legacy_request(),
        repository_sha="a" * 40,
    )
    assert set(packet["responsibility_owners"]) == {
        "product_boundary_observation",
        "mechanical_validation",
        "semantic_judgment",
        "experiment_identity_and_attribution",
        "decision_coordination",
        "passive_reporting",
    }
    assert set(packet["owner_results"].values()) == {"NOT_RUN"}
    assert packet["former_combined_authority_retired"] is True
    assert packet["execute_available"] is False
    assert "structural_score" not in packet
    assert "semantic_score" not in packet


def test_plan_only_packet_is_sanitized_and_makes_zero_calls() -> None:
    packet = legacy.run_evaluation(
        _legacy_request(),
        repository_sha="b" * 40,
    )
    serialized = json.dumps(packet, sort_keys=True).casefold()
    legacy.reject_forbidden_packet_material(packet)
    assert packet["call_counts"]["provider_calls"] == 0
    assert packet["call_counts"]["external_calls"] == 0
    assert packet["transport_created"] is False
    assert packet["credentials_accessed"] is False
    for forbidden in (
        "raw_prompt",
        "raw_response",
        "teacher_answer",
        "provider_payload",
    ):
        assert forbidden not in serialized


def test_superseded_direct_transport_source_is_deleted() -> None:
    assert not Path("scripts/evaluation/openai_responses_origination_transport.py").exists()


def test_narrow_call_manifest_uses_scenario_inputs_not_teacher_oracle() -> None:
    stages = (
        (
            "planner_only",
            ("search_planner",),
            (
                "case_03_pure_depth_two",
                "case_04_nested_serial_recovery",
                "case_06_root_query_retention",
                "case_07_honest_nonclosure",
            ),
            4,
        ),
        (
            "analyst_only",
            (
                ROLE_COMPONENT_ANALYST,
                ROLE_CROSS_COMPONENT_ANALYST,
            ),
            (
                "case_04_nested_serial_recovery",
                "case_07_honest_nonclosure",
            ),
            9,
        ),
        (
            "combined",
            (
                "search_planner",
                ROLE_COMPONENT_ANALYST,
                ROLE_CROSS_COMPONENT_ANALYST,
            ),
            ("case_06_root_query_retention",),
            7,
        ),
    )
    for evaluation_pass, roles, scenarios, expected_calls in stages:
        manifest = legacy.build_call_manifest(
            legacy.EvaluationRequest(
                evaluation_pass=evaluation_pass,
                execution_mode="execute",
                scenario_ids=scenarios,
                selected_model_roles=roles,
                reasoning_effort="medium",
            )
        )
        assert manifest.total_maximum_physical_model_calls == expected_calls

    source = Path("scripts/evaluation/run_analystos_model_origination_evaluation.py").read_text(encoding="utf-8")
    assert "analystos_model_origination_expectations" not in source
    assert "expectation_for" not in source
    assert "expected_status" not in source
    assert "BOUNDED_LIMIT" not in source
    assert "correct_basis" not in source
    assert "build_searchos_policy_snapshot" in source
