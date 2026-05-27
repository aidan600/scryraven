from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import core.source_class_recovery_executor as executor_module
from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    build_controller_loop_spine_result,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_LIFECYCLE_VISIBILITY_PATH = (
    _ROOT / "core" / "authority_lifecycle_candidate_visibility.py"
)

_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car "
    "in 2026, and what official source supports it?"
)
_RECOVERY_QUERIES = (
    "IRS 2026 standard mileage rate official current source",
)


def _authority_trace(
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=_RECOVERY_QUERIES,
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:official_current_rules"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [
                "official_current_rules"
            ],
            "active_source_class_recovery_attempt_count": 1,
            "active_source_class_recovery_result_count": result_count,
            "recovered_accepted_url_count": accepted_url_count,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": ["official_current_rules"],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    return trace


def _official_source(url: str = "https://www.irs.gov/ag69d-rate") -> dict[str, Any]:
    return {
        "title": "IRS official current 2026 standard mileage rate",
        "url": url,
        "text": (
            "Official IRS guidance states the current 2026 standard mileage "
            "rate rule for business use."
        ),
        "source_tier": "official",
        "source_class": "official_current_rules",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "score": 0.01,
    }


def _secondary_source() -> dict[str, Any]:
    return {
        "title": "Secondary mileage rate analysis",
        "url": "https://analysis.example/ag69d-rate",
        "text": "Secondary discussion of the IRS mileage rate.",
        "source_tier": "secondary",
        "source_class": "official_current_rules",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "score": 0.01,
    }


def _existing_secondary() -> dict[str, Any]:
    return {
        "title": "Existing secondary analysis",
        "url": "https://analysis.example/existing",
        "text": "Existing secondary discussion.",
        "source_tier": "secondary",
        "score": 0.8,
    }


def _run_visibility(
    recovered: list[dict[str, Any]],
    *,
    trace: dict[str, Any] | None = None,
    final: list[dict[str, Any]] | None = None,
    max_final_evidence: int = 4,
) -> tuple[list[Any], Any, dict[str, Any]]:
    lifecycle = trace or _authority_trace(result_count=len(recovered))
    final_evidence, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=final or [_existing_secondary()],
        recovered_passages=recovered,
        lifecycle_trace=lifecycle,
        max_final_evidence=max_final_evidence,
    )
    lifecycle.update(decision.to_trace_fields())
    return final_evidence, decision, lifecycle


def test_ag69d_returned_candidate_triggers_requirement_bound_fit_evaluation() -> None:
    _final, _decision, lifecycle = _run_visibility([_official_source()])

    authority = lifecycle["authority_lifecycle"]
    assert authority["execution_state"]["state"] == "attempted"
    assert authority["candidate_return_status"] == "candidates_returned"
    assert authority["candidate_fit"]["fit_state"] != "not_evaluated"
    assert lifecycle["authority_lifecycle_candidate_fit_state"] == "matched_selected"


def test_ag69d_accepted_url_alone_is_rejected_not_authority_fit() -> None:
    trace = _authority_trace(result_count=0, accepted_url_count=1)
    _final, _decision, lifecycle = _run_visibility([], trace=trace)
    fit = lifecycle["authority_lifecycle"]["candidate_fit"]

    assert lifecycle["authority_lifecycle_candidate_return_status"] == (
        "candidates_returned"
    )
    assert fit["fit_state"] == "rejected_with_reason"
    assert fit["selected_authority_evidence"] == []
    assert lifecycle["authority_lifecycle"]["satisfaction_state"] != "satisfied"


def test_ag69d_satisfying_candidate_becomes_selected_authority_evidence() -> None:
    final, decision, lifecycle = _run_visibility([_official_source()])
    fit = lifecycle["authority_lifecycle"]["candidate_fit"]

    assert final[-1]["url"] == "https://www.irs.gov/ag69d-rate"
    assert decision.used is True
    assert fit["fit_state"] == "matched_selected"
    assert fit["selected_authority_evidence"][0]["requirement_id"] == (
        "official_current_rules"
    )
    assert lifecycle["authority_lifecycle"]["final_evidence_state"] == "visible"
    assert lifecycle["authority_lifecycle"]["citation_eligibility_state"] == (
        "eligible"
    )


def test_ag69d_non_satisfying_candidate_records_structured_rejection() -> None:
    _final, decision, lifecycle = _run_visibility([_secondary_source()])
    rejection = lifecycle["authority_lifecycle"]["candidate_fit"][
        "structured_rejections"
    ][0]

    assert decision.used is False
    assert lifecycle["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "rejected_with_reason"
    )
    assert rejection["requirement_id"] == "official_current_rules"
    assert rejection["url"] == "https://analysis.example/ag69d-rate"
    assert rejection["required_authority"] == "official_current_rules"
    assert rejection["observed_source_class"] == "official_current_rules"
    assert rejection["rejection_owner"] == "controller/lifecycle"
    assert rejection["lower_tier_context_allowed"] is True
    assert rejection["final_evidence_must_be_explained_absent"] is True


def test_ag69d_recovered_result_without_visible_final_evidence_is_explained() -> None:
    _final, _decision, lifecycle = _run_visibility([_secondary_source()])
    authority = lifecycle["authority_lifecycle"]

    assert authority["execution_state"]["recovered_result_count"] > 0
    assert authority["final_evidence_state"] == "explained_absent"
    assert "official_current_rules" in authority["final_evidence_explanation"]
    assert authority["candidate_fit"]["fit_state"] == "rejected_with_reason"


def test_ag69d_lower_tier_context_remains_context_only() -> None:
    _final, _decision, lifecycle = _run_visibility([_secondary_source()])
    fit = lifecycle["authority_lifecycle"]["candidate_fit"]

    assert fit["selected_authority_evidence"] == []
    assert fit["structured_rejections"][0]["lower_tier_context_allowed"] is True
    assert lifecycle["authority_lifecycle"]["satisfaction_state"] == "partial"


def test_ag69d_legacy_visibility_fields_are_lifecycle_projections() -> None:
    _final, _decision, lifecycle = _run_visibility([_secondary_source()])
    fit = lifecycle["authority_lifecycle"]["candidate_fit"]
    export = build_official_canonical_recovery_visibility_export(lifecycle)

    assert lifecycle["recovered_visibility_source_fit_status"] == (
        "no_matching_source_fit"
    )
    assert lifecycle["recovered_visibility_source_fit_rejection_reasons"] == [
        item["rejection_reason"] for item in fit["structured_rejections"]
    ]
    assert export["recovered_candidate_source_fit_status"] == (
        "no_matching_source_fit"
    )
    assert export["recovered_candidate_rejection_reasons"] == (
        lifecycle["recovered_visibility_source_fit_rejection_reasons"]
    )


def test_ag69d_citation_eligibility_is_projected_without_final_answer_behavior() -> None:
    _final, _decision, lifecycle = _run_visibility([_secondary_source()])

    assert lifecycle["authority_lifecycle"]["citation_eligibility_state"] == (
        "explained_ineligible"
    )
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    assert "citation_eligibility_state" not in pipeline_source


def _recommendation() -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_queries": list(_RECOVERY_QUERIES),
        "source_class_recovery_query_count": len(_RECOVERY_QUERIES),
        "source_class_recovery_reason": "source_class_recovery:ag69d_gap",
        "source_class_recovery_trigger_fields": [
            "runtime_source_class_expectation"
        ],
    }


def _observability() -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {
            "official_current_rules": "expected_but_only_secondary"
        },
        "source_class_strong_satisfaction_counts": {
            "official_current_rules": 0
        },
        "source_class_gap_candidates": ["official_current_rules"],
    }


def _answer_contract_result() -> SimpleNamespace:
    contract = SimpleNamespace(
        family=SimpleNamespace(value="current_official_rules"),
        evidence_classes_needed=("official_current_rules",),
    )
    evidence_state = SimpleNamespace(
        source_classes_missing=("official_current_rules",),
    )
    return SimpleNamespace(
        adapter_result=SimpleNamespace(contract=contract),
        state=SimpleNamespace(evidence_state_summary=evidence_state),
        fulfillment_handoff=SimpleNamespace(
            unfulfilled_items=("official current source",),
            partial_items=("secondary source found",),
        ),
    )


def _orchestrator_state() -> dict[str, Any]:
    return {
        "query": _QUERY,
        "intent": "general",
        "report_type": "answer",
        "query_type": "official_current_status",
        "core_topic": "IRS 2026 standard mileage rate",
        "primary_entity": "IRS",
        "_source_class_recovery_lifecycle_recommendation": _recommendation(),
        "_source_class_recovery_answer_contract_observability": _observability(),
        "_source_tier_recovery_lifecycle": {
            "source_tier_counts": {"secondary": 2},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_recovery_lifecycle": {
            "source_domain_counts": {"analysis.example": 2},
            "top_source_domains": [{"domain": "analysis.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
        },
        "_pre_recovery_answer_contract_result": _answer_contract_result(),
        "corpus_state": "HEALTHY",
        "corpus_weak": False,
        "evidence_integration_checkpoint_trace": {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": 0,
        "max_iterations": 2,
        "waste_flags": [],
    }


def _execute_real_path_fixture(
    controller: RunController,
    lifecycle: dict[str, Any],
) -> tuple[dict[str, int | bool], list[str], list[dict[str, Any]]]:
    captured_queries: list[str] = []
    all_passages: list[dict[str, Any]] = []

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        source = _official_source("https://www.irs.gov/ag69d-real-path")
        seen_urls.add(source["url"])
        return [source]

    result = executor_module.execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=all_passages,
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[0.0],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=["offline-fixture"],
        exa_domain_filter=None,
        entity_hint="IRS",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )
    return result, captured_queries, all_passages


def test_ag69d_real_path_fixture_reaches_post_execution_candidate_visibility() -> None:
    controller = RunController()
    handoff = build_authoritative_source_action_orchestrator_handoff(
        controller,
        orchestrator_state=_orchestrator_state(),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    spine = build_controller_loop_spine_result(
        checkpoint_trace={"available": False, "reason": "checkpoint_unavailable"},
        source_class_lifecycle_trace=lifecycle,
    )

    execution, queries, passages = _execute_real_path_fixture(controller, lifecycle)
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_existing_secondary()],
        recovered_passages=passages,
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )
    lifecycle.update(decision.to_trace_fields())

    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert execution["attempted"] is True
    assert list(_RECOVERY_QUERIES)[0] in queries
    assert passages[0]["retrieval_stage"] == "source_class_recovery"
    assert lifecycle["authority_lifecycle"]["execution_state"]["state"] == (
        "attempted"
    )
    assert lifecycle["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "matched_selected"
    )
    assert final[-1]["url"] == "https://www.irs.gov/ag69d-real-path"


def test_ag69d_static_guard_keeps_pipeline_and_protected_surfaces_closed() -> None:
    lifecycle_source = _LIFECYCLE_VISIBILITY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(lifecycle_source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imported.isdisjoint(
        {
            "openai",
            "requests",
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.routing",
            "core.search_providers",
            "core.source_classifier",
            "core.author",
            "core.economist",
        }
    )
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert pipeline_source.count("apply_recovered_evidence_visibility_boundary(") == 1
    assert "authority_lifecycle_candidate_visibility" not in pipeline_source
    assert "standard mileage rate" not in pipeline_source.casefold()
    assert "taxable maximum" not in pipeline_source.casefold()
